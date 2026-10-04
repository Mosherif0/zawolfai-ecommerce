import json
import re
import language_config as lang_config

# NOTE: `inventory` is imported lazily inside `save_items()`.
# Importing it here meant merely importing this module opened a PostgreSQL
# connection, which broke the test suite and any offline use of the parser.


# ---------------------------------------------------------
# Load OCR data
# ---------------------------------------------------------

def load_ocr_data(path="output/ocr_data.json"):

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


# ---------------------------------------------------------
# Group OCR detections into receipt rows
# ---------------------------------------------------------


# Guards against OCR blobs being mistaken for products.
MAX_PRODUCT_NAME_LENGTH = 60
MAX_PLAUSIBLE_PRICE = 100_000.0


# Seven consecutive digits is the shortest run that is unambiguously a
# barcode / card number / phone number rather than a quantity or a price.
_IDENTIFIER_RE = re.compile(r"\d{7,}")


def _identifier_only(text):
    """
    True when a row is essentially one long digit run (barcode / SKU line).

    A real product line contains words; an identifier line does not, so the
    letter count is what separates "068949055223" from "6FT HDMI CABLE".
    """
    if not _IDENTIFIER_RE.search(text):
        return False
    letters = sum(ch.isalpha() for ch in text)
    digits = sum(ch.isdigit() for ch in text)
    return letters <= digits


def _median(values):
    ordered = sorted(values)
    n = len(ordered)
    if not n:
        return 0.0
    mid = n // 2
    return float(ordered[mid] if n % 2 else (ordered[mid - 1] + ordered[mid]) / 2)


def adaptive_row_threshold(ocr_data, default=35.0):
    """
    Estimate a row-merge tolerance from the text height in the OCR output.

    Receipt line spacing is roughly one text height, so half of the median
    glyph height separates rows while still absorbing the vertical jitter the
    detector introduces. Clamped so an all-tiny or all-huge image cannot
    produce a degenerate threshold.
    """
    heights = []
    for item in ocr_data:
        bbox = item.get("bbox") or []
        if len(bbox) < 4:
            continue
        ys = [p[1] for p in bbox]
        height = max(ys) - min(ys)
        if height > 0:
            heights.append(height)

    if not heights:
        return default

    median_h = _median(heights)
    if median_h <= 0:
        return default

    return max(6.0, min(default, median_h * 0.6))



def group_rows(ocr_data, y_threshold=None):
    """
    Cluster detections into visual rows.

    `y_threshold` is ADAPTIVE. A fixed pixel value breaks as soon as the
    receipt is photographed at a different distance: 35px merged two adjacent
    line items on a tightly-set receipt and split one long product name on a
    loosely-set one. The threshold is now derived from the median glyph
    height, which is the only scale available in the OCR output.
    """
    if y_threshold is None:
        y_threshold = adaptive_row_threshold(ocr_data)

    detections = []

    for item in ocr_data:

        text = item["text"].strip()
        bbox = item["bbox"]

        if not text:
            continue

        center_y = sum(point[1] for point in bbox) / len(bbox)
        center_x = sum(point[0] for point in bbox) / len(bbox)

        detections.append({
            "text": text,
            "x": center_x,
            "y": center_y
        })

    detections.sort(key=lambda item: (item["y"], item["x"]))

    rows = []

    for detection in detections:

        # Compare against the NEAREST row, not the first row that happens to
        # be within range. Scanning top-down and taking the first match lets a
        # tall row swallow a line that sits between two rows, and the
        # mean-of-row centre drifts as items are appended.
        best_index = None
        best_distance = None

        for index, row in enumerate(rows):
            row_y = _median([item["y"] for item in row])
            distance = abs(detection["y"] - row_y)
            if distance <= y_threshold and (best_distance is None or distance < best_distance):
                best_index = index
                best_distance = distance

        if best_index is not None:
            rows[best_index].append(detection)
        else:
            rows.append([detection])

    rows.sort(key=lambda row: _median([item["y"] for item in row]))

    final_rows = []

    for row in rows:

        row.sort(key=lambda item: item["x"])

        final_rows.append(
            [item["text"] for item in row]
        )

    return final_rows


# ---------------------------------------------------------
# Extract price
# ---------------------------------------------------------

def normalize_price_text(text):
    """
    Canonical price-text normalisation, shared by extract_price and
    remove_price.

    ONE function matters: when each did its own thing, "2,495.00" was priced
    correctly but only "2," was stripped from the product name, so the item
    was saved as "KALLAX Shelf Unit 2". Normalise first, then both the
    extractor and the stripper see identical text.

      2,495.00  -> 2495.00   (thousands separator removed)
      19,99     -> 19.99     (decimal comma)
    """
    # Arabic-Indic digits ("٢٤٩٥٫٠٠") and the Arabic decimal separator must
    # become ASCII before any numeric rule runs, otherwise every price regex
    # silently fails on an Egyptian receipt.
    text = lang_config.normalize_arabic(text)

    text = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "", text)
    text = re.sub(r"(\d),(\d{2})(?!\d)", r"\1.\2", text)
    return re.sub(r"\s*\.\s*", ".", text)



def extract_price(text):

    original = text

    text = normalize_price_text(text)

    # Normal prices:
    # $19.99
    # S19.99
    # 19.99
    # 1,299.50

    match = re.search(
        r"(?:\$|S)?\s*(\d{1,7}\.\d{2})",
        text,
        flags=re.IGNORECASE
    )

    if match:
        return float(match.group(1))

    # Whole amounts with no decimals: $45, USD120
    match = re.search(
        r"(?:\$|USD|S)\s*(\d{1,7})(?!\s*\.\s*\d)",
        text,
        flags=re.IGNORECASE
    )

    if match:
        return float(match.group(1))

    # USD prices:
    # USD89
    # USD120
    # USD89.99

    match = re.search(
        r"USD\s*(\d+(?:\.\d{1,2})?)",
        text,
        flags=re.IGNORECASE
    )

    if match:
        return float(match.group(1))

    # Fragmented OCR prices.
    #
    # Example:
    # S39 _ I6 98
    #
    # OCR sometimes separates the decimal part.

    currency_match = re.search(
        r"[Ss\$]\s*(\d{1,4})",
        original
    )

    if currency_match:

        integer_part = currency_match.group(1)

        two_digit_matches = re.findall(
            r"(?<!\d)(\d{2})(?!\d)",
            original
        )

        if two_digit_matches:

            cents = two_digit_matches[-1]

            try:
                return float(
                    f"{integer_part}.{cents}"
                )

            except ValueError:
                pass

    return None


# ---------------------------------------------------------
# Extract quantity
# ---------------------------------------------------------

def extract_quantity(text):

    # Important:
    # Do NOT treat numbers inside product names
    # such as "6FT HDMI CABLE" as quantity.
    #
    # Quantity may appear at the START ("2 x CABLE") or at the END
    # ("WOOL SOCKS 3X"), which is the layout EasyOCR often produces.
    # It must be a standalone token followed/preceded by x, *, @ or a
    # space, so "6FT" and "SOCKX" are not mistaken for a quantity.

    # A LONG digit run (7+ consecutive digits) means this row is a barcode /
    # SKU / phone number, not a sale line. Without this, "068949055223 2.00"
    # parsed as quantity 68949055223 and wrote 68 billion units into the
    # database. "6FT HDMI CABLE" is untouched: its longest run is 1 digit.
    if re.search(r"\d{7,}", lang_config.normalize_arabic(text)):
        return 1


    # trailing form: "SOCKS 3X", "CABLE 2 @", "ITEM (4)"
    match = re.search(
        r"(?:^|[\s(])(\d{1,3})\s*[x*@]\s*(?=$|[\s)])",
        text,
        flags=re.IGNORECASE
    )

    if match:
        return int(match.group(1))

    # leading form: "2 x CABLE", "3 - CABLE"
    match = re.match(
        r"^\s*(\d+)(?=\s+|x\b|-)",
        text,
        flags=re.IGNORECASE
    )

    if match:
        return int(match.group(1))

    # "ITEM (4)" - a parenthesised count at the end of the line
    match = re.search(r"\((\d{1,3})\)\s*$", text)

    if match:
        return int(match.group(1))

    # "2 CABLE" - a bare count directly after a leading number.
    match = re.match(r"^\s*(\d{1,3})\s+(?=[A-Za-z])", text)

    if match:
        value = int(match.group(1))
        if value < 100:
            return value

    # No quantity printed: the receipt shows one unit per line.
    return 1


# ---------------------------------------------------------
# Remove price from product name
# ---------------------------------------------------------

def remove_price(text):

    # Normalise FIRST so this function and extract_price see identical text
    # (see normalize_price_text for the bug this prevents).
    text = normalize_price_text(text)

    # Currency-prefixed amounts, removed whole.
    text = re.sub(r"\bUSD\s*\d+(?:\.\d{1,2})?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<![A-Za-z0-9])[\$]\s*\d+(?:\.\d{1,2})?", "", text)
    text = re.sub(r"(?<![A-Za-z0-9])S\s*\d+(?:\.\d{1,2})?", "", text)

    # Bare decimals: "199.00" -> 2495.00
    text = re.sub(r"(?<![A-Za-z0-9.])\d+\.\d{1,2}", "", text)

    # Genuinely fragmented OCR prices ("S39 _ I6 98"). The lookbehind stops the
    # leading "S" of a word from being read as a currency mark.
    text = re.sub(
        r"(?<![A-Za-z0-9])[S\$](?=\s*\d)\s*\d{1,4}"
        r"(?:\s*[_\-]\s*\d+)?(?:\s+\d{2})?",
        "",
        text
    )

    # Whole amounts with no decimals ("USD45", "45"). A quantity marker
    # immediately after the number ("SOCKS 3X") must go with it, otherwise the
    # stripper leaves a stray "X" in the product name.
    text = re.sub(r"(?<![A-Za-z0-9.])\d{1,7}\s*[xX](?!\d|\.\d)", "", text)
    text = re.sub(r"(?<![A-Za-z0-9.])\d{1,7}(?!\d|\.\d)", "", text)

    # A currency glyph split from its digits by the OCR ("s49,99" -> the "s"
    # became a standalone token). It is not a price, so it must not survive
    # into the product name.
    text = re.sub(r"(?<![A-Za-z])[sS](?=\s*\d)", "", text)

    # A stray currency symbol glued to the name means the OCR split the price
    # oddly ("€ 69 69 SILI) BRICKS"). Drop the symbol; the digits that follow
    # are removed by the leftover-number rule in parse_rows.
    text = re.sub(r"^[\u20ac\u00a3\u00a5$]", "", text)

    text = re.sub(r"\s*[_|,]\s*$", "", text)

    # Bullet / index markers a printed receipt puts in front of a line item
    # ("# Yogurt", "* MILK", "- Bread", "//"). They are layout, not product.
    text = re.sub(r"^[#*/\u2022\-\s]+(?=[A-Za-z])", "", text)

    return " ".join(text.split()).strip()



# Detect summary / footer rows
# ---------------------------------------------------------

def is_summary_row(text, price=None):
    """
    Decide whether a row is a footer total rather than a product line.

    OCR corrupts these labels constantly ("Subtota/", "T0TAL", "Totel"), so the
    first word is compared with an edit-distance tolerance instead of an exact
    match - that is what stops a corrupted "Subtotal" from being sold as a
    product.
    """
    text_lower = (text or "").lower().strip()
    if not text_lower:
        return False

    summary_keywords = list(lang_config.summary_keywords())


    first_word = text_lower.split()[0].rstrip(":")
    # Strip trailing punctuation OCR leaves behind ("subtota/", "subtotal.").
    first_word = re.sub(r"[^a-z]", "", first_word)

    for keyword in summary_keywords:
        if _similar(first_word, keyword.replace(" ", "")):
            return True

    # Footer noise can start with anything: "CREDIT TEND ACCOUNT 9999
    # APPROVED", "PAID RETURN POLICY RETURNS ACCEPTED". A price is present on
    # almost every one of these lines, so when the row carries an amount we
    # scan the WHOLE text for any footer token rather than only its first word.
    if price is not None:
        for keyword in summary_keywords:
            if keyword in text_lower:
                return True

    


def _similar(a, b, tolerance=1):
    """True when two short labels differ by at most `tolerance` edits."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > tolerance:
        return False
    return _levenshtein(a, b) <= tolerance


def _levenshtein(a, b):
    """Plain Levenshtein distance - short labels only, so O(n*m) is fine."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(
                previous[j] + 1,
                current[j - 1] + 1,
                previous[j - 1] + (ca != cb),
            ))
        previous = current
    return previous[-1]



def is_metadata_row(text):

    text_lower = text.lower()

    # Patterns, not just keywords: "Store 12" and "STORE #42" both appear on
    # receipts, and a bare keyword list missed them - the store line was then
    # parsed as a product named "Store #12".
    metadata_patterns = list(lang_config.metadata_patterns())

    return any(
        re.search(pattern, text_lower)
        for pattern in metadata_patterns
    )


# ---------------------------------------------------------
# Parse receipt rows
# ---------------------------------------------------------

def parse_rows(rows):

    products = []

    current_product = None

    for row in rows:

        row_text = " ".join(row).strip()

        if not row_text:
            continue

        # -------------------------------------------------
        # Ignore metadata
        # -------------------------------------------------

        if is_metadata_row(row_text):
            continue

        # -------------------------------------------------
        # Extract price
        # -------------------------------------------------

        price = extract_price(row_text)


        # A barcode / SKU line carries no commercial meaning. When the row is
        # dominated by a long digit run, it is not a sale line.
        if _identifier_only(row_text):
            current_product = None
            continue

        # -------------------------------------------------
        # Ignore summary / footer rows
        # -------------------------------------------------

        if is_summary_row(row_text, price):
            current_product = None
            continue

        # -------------------------------------------------
        # Product with price on same row
        # -------------------------------------------------

        if price is not None:

            quantity = extract_quantity(row_text)

            name = remove_price(row_text)

            # Remove the quantity token wherever it sits (leading "2 x CABLE"
            # or trailing "CABLE 3X"); the name must not carry the count.
            if quantity != 1:

                name = re.sub(
                    rf"^\s*{quantity}(?:\s*[x*@])?\s*",
                    "",
                    name,
                    flags=re.IGNORECASE
                )

                name = re.sub(
                    rf"(?<=\s){quantity}\s*[x*@]\s*$",
                    "",
                    name,
                    flags=re.IGNORECASE
                )

            # A leftover number in the name means the price stripper could
            # not match the OCR'd currency form ("s49,99"). It is price, not
            # part of the product, so it goes.
            name = re.sub(r"(?<![A-Za-z0-9])\d{1,7}\.\d{2}(?!\d)", "", name)

            # Drop leftovers: the quantity mark plus any separator commas,
            # pipes or underscores the printer left behind.
            name = re.sub(r"\s*[x*@]\s*$", "", name)
            name = re.sub(r"\s*[,;|_]+\s*$", "", name)
            name = re.sub(r"\s{2,}", " ", name)
            name = name.strip(" -:|,.\t")

            # Ignore empty names

            if not name:
                continue

            # Sanity gate. A genuine line item is a short label with a
            # plausible price. Merged OCR blobs (a whole receipt read as one
            # row, track listings from a music app, ...) are far longer and
            # must never become inventory rows.
            if len(name) > MAX_PRODUCT_NAME_LENGTH:
                continue

            # A name must contain real letters. "///" or "()" survive the
            # price stripper as symbols and are layout noise, not products.
            if sum(ch.isalpha() for ch in name) < 3:
                continue

            if price <= 0 or price > MAX_PLAUSIBLE_PRICE:
                continue

            current_product = {
                "quantity": quantity,
                "name": name,
                "price": price
            }

            products.append(current_product)

            continue

        # -------------------------------------------------
        # Continuation line
        # -------------------------------------------------

        if current_product is not None:

            continuation = row_text.strip()

            if continuation:

                # Avoid adding obvious metadata/footer
                if is_metadata_row(continuation):
                    continue

                current_product["name"] = (
                    current_product["name"]
                    + " "
                    + continuation
                ).strip()

            continue

    return products


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def save_items(items, database=True):
    """
    Persist parsed items to Postgres.

    `database=False` keeps everything local, which is what the tests and any
    dry-run should use.
    """
    if not database:
        return None
    from inventory import save_products   # imported here, not at module load

    return save_products(items)


def parse_receipt(ocr_json_path="output/ocr_data.json", y_threshold=35):
    """
    End-to-end: OCR JSON file -> structured product list.

    Returns (rows, items) so callers can inspect the intermediate grouping.
    """
    ocr_data = load_ocr_data(ocr_json_path)
    rows = group_rows(ocr_data, y_threshold=y_threshold)
    return rows, parse_rows(rows)


def _print_report(rows, items):
    print("Grouped Receipt Rows:")
    print("---------------------")
    for row in rows:
        print(" | ".join(row))

    print("\nParsed Items:")
    print("----------------")
    for item in items:
        print(item)


if __name__ == "__main__":

    import sys

    rows, items = parse_receipt()

    _print_report(rows, items)

    # `--dry-run` (or a missing DB) keeps the result local.
    if "--dry-run" in sys.argv:
        print("\n[dry-run] skipping database write")
    else:
        save_items(items)
        print("\nSaved to database.")
