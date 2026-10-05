import json
import re

import language_config as lang_config


# =========================================================
# Configuration / validation guards
# =========================================================

MAX_PRODUCT_NAME_LENGTH = 60
MAX_PLAUSIBLE_PRICE = 100_000.0

# Long digit runs are usually barcodes / SKUs / phone numbers.
_IDENTIFIER_RE = re.compile(r"\d{7,}")


# =========================================================
# Load OCR data
# =========================================================

def load_ocr_data(path="output/ocr_data.json"):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


# =========================================================
# OCR helper functions
# =========================================================

def _identifier_only(text):
    """
    Detect rows that are basically barcode / SKU / identifier lines.
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

    middle = n // 2

    if n % 2:
        return float(ordered[middle])

    return float(
        (ordered[middle - 1] + ordered[middle]) / 2
    )


def adaptive_row_threshold(ocr_data, default=35.0):
    """
    Estimate row grouping tolerance from OCR text height.
    """

    heights = []

    for item in ocr_data:
        bbox = item.get("bbox") or []

        if len(bbox) < 4:
            continue

        ys = [point[1] for point in bbox]

        height = max(ys) - min(ys)

        if height > 0:
            heights.append(height)

    if not heights:
        return default

    median_height = _median(heights)

    if median_height <= 0:
        return default

    return max(
        6.0,
        min(default, median_height * 0.6)
    )


# =========================================================
# Group OCR detections into receipt rows
# =========================================================

def group_rows(ocr_data, y_threshold=None):

    if y_threshold is None:
        y_threshold = adaptive_row_threshold(ocr_data)

    detections = []

    for item in ocr_data:

        text = item["text"].strip()
        bbox = item["bbox"]

        if not text:
            continue

        center_y = sum(
            point[1] for point in bbox
        ) / len(bbox)

        center_x = sum(
            point[0] for point in bbox
        ) / len(bbox)

        detections.append({
            "text": text,
            "x": center_x,
            "y": center_y
        })

    detections.sort(
        key=lambda item: (
            item["y"],
            item["x"]
        )
    )

    rows = []

    for detection in detections:

        best_index = None
        best_distance = None

        for index, row in enumerate(rows):

            row_y = _median(
                [item["y"] for item in row]
            )

            distance = abs(
                detection["y"] - row_y
            )

            if (
                distance <= y_threshold
                and (
                    best_distance is None
                    or distance < best_distance
                )
            ):
                best_index = index
                best_distance = distance

        if best_index is not None:
            rows[best_index].append(detection)
        else:
            rows.append([detection])

    rows.sort(
        key=lambda row: _median(
            [item["y"] for item in row]
        )
    )

    final_rows = []

    for row in rows:

        row.sort(
            key=lambda item: item["x"]
        )

        final_rows.append(
            [item["text"] for item in row]
        )

    return final_rows


# =========================================================
# Price normalization
# =========================================================

def normalize_price_text(text):
    """
    Normalize OCR price text.

    Examples:

        2,495.00 -> 2495.00
        19,99    -> 19.99
    """

    text = lang_config.normalize_arabic(text)

    # Thousands separator
    text = re.sub(
        r"(?<=\d),(?=\d{3}(?:\D|$))",
        "",
        text
    )

    # Decimal comma
    text = re.sub(
        r"(\d),(\d{2})(?!\d)",
        r"\1.\2",
        text
    )

    # Spaces around decimal point
    text = re.sub(
        r"\s*\.\s*",
        ".",
        text
    )

    return text


# =========================================================
# Extract price
# =========================================================

def extract_price(text):

    original = text

    text = normalize_price_text(text)

    # -----------------------------------------
    # Normal decimal prices
    # -----------------------------------------
    #
    # $19.99
    # S19.99
    # 19.99
    #

    match = re.search(
        r"(?:\$|S)?\s*(\d{1,7}\.\d{2})",
        text,
        flags=re.IGNORECASE
    )

    if match:
        price = float(match.group(1))

        if 0 < price <= MAX_PLAUSIBLE_PRICE:
            return price

    # -----------------------------------------
    # USD prices
    # -----------------------------------------

    match = re.search(
        r"USD\s*(\d+(?:\.\d{1,2})?)",
        text,
        flags=re.IGNORECASE
    )

    if match:
        price = float(match.group(1))

        if 0 < price <= MAX_PLAUSIBLE_PRICE:
            return price

    # -----------------------------------------
    # Whole prices with currency
    # -----------------------------------------

    match = re.search(
        r"(?:\$|S)\s*(\d{1,7})(?!\s*\.\s*\d)",
        text,
        flags=re.IGNORECASE
    )

    if match:
        price = float(match.group(1))

        if 0 < price <= MAX_PLAUSIBLE_PRICE:
            return price

    # -----------------------------------------
    # Fragmented OCR prices
    # -----------------------------------------

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
                price = float(
                    f"{integer_part}.{cents}"
                )

                if (
                    0 < price
                    <= MAX_PLAUSIBLE_PRICE
                ):
                    return price

            except ValueError:
                pass

    return None


# =========================================================
# Extract quantity
# =========================================================

def extract_quantity(text):

    # IMPORTANT:
    #
    # This logic intentionally follows the original
    # parser logic.
    #
    # Do NOT treat numbers inside product names
    # such as:
    #
    #     6FT HDMI CABLE
    #
    # as quantity.
    #
    # Quantity must be followed by:
    #     whitespace
    #     x
    #     hyphen

    match = re.match(
        r"^\s*(\d+)(?=\s+|x\b|-)",
        text,
        flags=re.IGNORECASE
    )

    if match:
        return int(match.group(1))

    return 1


# =========================================================
# Remove price from product name
# =========================================================

def remove_price(text):

    text = normalize_price_text(text)

    # -----------------------------------------
    # USD
    # -----------------------------------------

    text = re.sub(
        r"USD\s*\d+(?:\.\d{1,2})?",
        "",
        text,
        flags=re.IGNORECASE
    )

    # -----------------------------------------
    # Currency-prefixed prices
    # -----------------------------------------

    text = re.sub(
        r"(?<![A-Za-z0-9])\$\s*\d+(?:\.\d{1,2})?",
        "",
        text
    )

    text = re.sub(
        r"(?<![A-Za-z0-9])S\s*\d+(?:\.\d{1,2})?",
        "",
        text,
        flags=re.IGNORECASE
    )

    # -----------------------------------------
    # Decimal prices
    # -----------------------------------------

    text = re.sub(
        r"(?<![A-Za-z0-9.])\d+\.\d{1,2}",
        "",
        text
    )

    # -----------------------------------------
    # Fragmented OCR prices
    # -----------------------------------------

    text = re.sub(
        r"(?<![A-Za-z0-9])[Ss\$]"
        r"\s*\d{1,4}"
        r"(?:\s*[_\-]\s*\d+)?"
        r"(?:\s+\d{2})?",
        "",
        text
    )

    # -----------------------------------------
    # Quantity marker at the end
    #
    # Example:
    #     SOCKS 3X
    #
    # Only the explicit X marker is removed here.
    # We do NOT remove arbitrary numbers.
    # -----------------------------------------

    text = re.sub(
        r"(?<=\s)\d{1,3}\s*[xX]\s*$",
        "",
        text
    )

    # -----------------------------------------
    # Remove obvious leftover decimal prices
    # -----------------------------------------

    text = re.sub(
        r"(?<![A-Za-z0-9])\d+\.\d{1,2}(?!\d)",
        "",
        text
    )

    # -----------------------------------------
    # Currency symbol at beginning
    # -----------------------------------------

    text = re.sub(
        r"^[€£¥$]",
        "",
        text
    )

    # -----------------------------------------
    # Trailing separators
    # -----------------------------------------

    text = re.sub(
        r"\s*[,;|_]+\s*$",
        "",
        text
    )

    # -----------------------------------------
    # Printed bullet / index markers
    # -----------------------------------------

    text = re.sub(
        r"^[#*/\-\s]+(?=[A-Za-z])",
        "",
        text
    )

    return " ".join(
        text.split()
    ).strip()


# =========================================================
# Levenshtein / fuzzy matching
# =========================================================

def _levenshtein(a, b):

    if a == b:
        return 0

    if not a:
        return len(b)

    if not b:
        return len(a)

    previous = list(
        range(len(b) + 1)
    )

    for i, char_a in enumerate(a, 1):

        current = [i]

        for j, char_b in enumerate(b, 1):

            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1]
                    + (char_a != char_b)
                )
            )

        previous = current

    return previous[-1]


def _similar(a, b, tolerance=1):

    if a == b:
        return True

    if abs(len(a) - len(b)) > tolerance:
        return False

    return _levenshtein(a, b) <= tolerance


# =========================================================
# Detect summary / footer rows
# =========================================================

def is_summary_row(text, price=None):

    text_lower = (
        text or ""
    ).lower().strip()

    if not text_lower:
        return False

    summary_keywords = list(
        lang_config.summary_keywords()
    )

    first_word = (
        text_lower.split()[0]
        .rstrip(":")
    )

    first_word = re.sub(
        r"[^a-z]",
        "",
        first_word
    )

    # Exact / fuzzy first-word match

    for keyword in summary_keywords:

        keyword_clean = re.sub(
            r"[^a-z]",
            "",
            keyword.lower()
        )

        if _similar(
            first_word,
            keyword_clean
        ):
            return True

    # If a price exists, also inspect
    # the complete row.

    if price is not None:

        for keyword in summary_keywords:

            if keyword.lower() in text_lower:
                return True

    return False


# =========================================================
# Detect metadata rows
# =========================================================

def is_metadata_row(text):

    text_lower = text.lower()

    metadata_patterns = list(
        lang_config.metadata_patterns()
    )

    return any(
        re.search(
            pattern,
            text_lower
        )
        for pattern in metadata_patterns
    )


# =========================================================
# Parse receipt rows
# =========================================================

def parse_rows(rows):

    products = []

    current_product = None

    for row in rows:

        row_text = " ".join(
            row
        ).strip()

        if not row_text:
            continue

        # -----------------------------------------
        # Ignore metadata
        # -----------------------------------------

        if is_metadata_row(row_text):
            continue

        # -----------------------------------------
        # Extract price
        # -----------------------------------------

        price = extract_price(
            row_text
        )

        # -----------------------------------------
        # Ignore barcode / identifier rows
        # -----------------------------------------

        if _identifier_only(
            row_text
        ):
            current_product = None
            continue

        # -----------------------------------------
        # Ignore summary / footer rows
        # -----------------------------------------

        if is_summary_row(
            row_text,
            price
        ):
            current_product = None
            continue

        # -----------------------------------------
        # Product with price
        # -----------------------------------------

        if price is not None:

            # IMPORTANT:
            #
            # Keep the original quantity logic.
            #
            # No new rule here saying that a
            # trailing number is automatically
            # a quantity.

            quantity = extract_quantity(
                row_text
            )

            name = remove_price(
                row_text
            )

            # -------------------------------------
            # Remove leading quantity
            # -------------------------------------

            if quantity != 1:

                name = re.sub(
                    rf"^\s*{quantity}"
                    rf"(?=\s+|x\b|-)\s*",
                    "",
                    name,
                    flags=re.IGNORECASE
                )

            # -------------------------------------
            # Remove leftover explicit quantity
            # markers
            # -------------------------------------

            if quantity != 1:

                name = re.sub(
                    rf"(?<=\s){quantity}"
                    rf"\s*[xX*@]\s*$",
                    "",
                    name,
                    flags=re.IGNORECASE
                )

            # -------------------------------------
            # Remove leftover decimal price
            # -------------------------------------

            name = re.sub(
                r"(?<![A-Za-z0-9])"
                r"\d+\.\d{2}"
                r"(?!\d)",
                "",
                name
            )

            # -------------------------------------
            # Clean separators
            # -------------------------------------

            name = re.sub(
                r"\s*[xX*@]\s*$",
                "",
                name
            )

            name = re.sub(
                r"\s*[,;|_]+\s*$",
                "",
                name
            )

            name = re.sub(
                r"\s{2,}",
                " ",
                name
            )

            name = name.strip(
                " -:|,.\t"
            )

            # -------------------------------------
            # Empty name
            # -------------------------------------

            if not name:
                continue

            # -------------------------------------
            # Validation
            # -------------------------------------

            if len(name) > MAX_PRODUCT_NAME_LENGTH:
                continue

            if sum(
                char.isalpha()
                for char in name
            ) < 3:
                continue

            if (
                price <= 0
                or price > MAX_PLAUSIBLE_PRICE
            ):
                continue

            # -------------------------------------
            # Save product
            # -------------------------------------

            current_product = {
                "quantity": quantity,
                "name": name,
                "price": price
            }

            products.append(
                current_product
            )

            continue

        # -----------------------------------------
        # Continuation line
        # -----------------------------------------

        if current_product is not None:

            continuation = row_text.strip()

            if continuation:

                if is_metadata_row(
                    continuation
                ):
                    continue

                current_product["name"] = (
                    current_product["name"]
                    + " "
                    + continuation
                ).strip()

    return products


# =========================================================
# Save items
# =========================================================

def save_items(items, database=True):

    """
    Save parsed receipt items through the warehouse layer.

    warehouse.record_receipt() is imported lazily so that simply
    importing receipt_parser.py does not open a database connection.
    """

    if not database:
        return None

    from warehouse import record_receipt

    return record_receipt(items)


# =========================================================
# Backward compatibility
# =========================================================

def save_products(items):
    """
    Compatibility wrapper for the old parser API.

    New code should use save_items().
    """

    return save_items(items)


# =========================================================
# Parse complete receipt
# =========================================================

def parse_receipt(
    ocr_json_path="output/ocr_data.json",
    y_threshold=None
):

    """
    OCR JSON -> grouped rows -> parsed products.

    Returns:
        rows, items
    """

    ocr_data = load_ocr_data(
        ocr_json_path
    )

    rows = group_rows(
        ocr_data,
        y_threshold=y_threshold
    )

    items = parse_rows(
        rows
    )

    return rows, items


# =========================================================
# Print report
# =========================================================

def _print_report(rows, items):

    print("Grouped Receipt Rows:")
    print("---------------------")

    for row in rows:
        print(" | ".join(row))

    print("\nParsed Items:")
    print("----------------")

    for item in items:
        print(item)


# =========================================================
# Main
# =========================================================

if __name__ == "__main__":

    import sys

    rows, items = parse_receipt()

    _print_report(
        rows,
        items
    )

    if "--dry-run" in sys.argv:

        print(
            "\n[dry-run] "
            "skipping database write"
        )

    else:

        save_items(items)

        print(
            "\nSaved to database."
        )