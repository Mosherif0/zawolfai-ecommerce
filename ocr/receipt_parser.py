import json
import re

from inventory import save_products


# ---------------------------------------------------------
# Load OCR data
# ---------------------------------------------------------

def load_ocr_data(path="output/ocr_data.json"):

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


# ---------------------------------------------------------
# Group OCR detections into receipt rows
# ---------------------------------------------------------

def group_rows(ocr_data, y_threshold=35):

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

        added = False

        for row in rows:

            row_y = sum(item["y"] for item in row) / len(row)

            if abs(detection["y"] - row_y) <= y_threshold:

                row.append(detection)
                added = True
                break

        if not added:
            rows.append([detection])

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

def extract_price(text):

    original = text

    text = text.replace(",", ".")
    text = re.sub(r"\s*\.\s*", ".", text)

    # Normal prices:
    # $19.99
    # S19.99
    # 19.99

    match = re.search(
        r"(?:\$|S)?\s*(\d+\.\d{2})",
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
    # Quantity must be followed by:
    # whitespace
    # x
    # hyphen

    match = re.match(
        r"^\s*(\d+)(?=\s+|x\b|-)",
        text,
        flags=re.IGNORECASE
    )

    if match:
        return int(match.group(1))

    return 1


# ---------------------------------------------------------
# Remove price from product name
# ---------------------------------------------------------

def remove_price(text):

    # Normal decimal prices:
    # $19.99
    # S19.99
    # 19.99

    text = re.sub(
        r"(?:\$|S)?\s*\d+\s*\.\s*\d{2}",
        "",
        text,
        flags=re.IGNORECASE
    )

    # USD prices:
    # USD89
    # USD120
    # USD89.99

    text = re.sub(
        r"USD\s*\d+(?:\.\d{1,2})?",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Fragmented OCR prices.
    #
    # Example:
    # S39 _ I6 98
    #
    # Only remove S when it is actually attached
    # to a number.
    #
    # This prevents words such as:
    # Jeans
    # Shirts
    # Sneakers
    #
    # from losing their final "s".

    text = re.sub(
    r"[Ss\$](?=\s*\d)\s*\d{1,4}(?:\s*[_\-]\s*\d+)?(?:\s+\d{2})?",
    "",
    text
)

    return " ".join(text.split()).strip()


# ---------------------------------------------------------
# Detect summary / footer rows
# ---------------------------------------------------------

def is_summary_row(text, price=None):

    text_lower = text.lower().strip()

    summary_keywords = [
        "subtotal",
        "total",
        "tax",
        "savings",
        "change",
        "payment",
        "amount",
        "balance",
        "transaction"
    ]

    # Exact summary labels should always be ignored.

    first_word = text_lower.split()[0] if text_lower else ""

    if first_word.rstrip(":") in summary_keywords:
        return True

    # Fuzzy matching is only used when the row
    # actually contains a price.
    #
    # This avoids incorrectly treating OCR continuation
    # text such as "ABOUT )" as a summary.

    if price is not None:

        for keyword in summary_keywords:

            if keyword in text_lower:
                return True

    return False


# ---------------------------------------------------------
# Detect metadata rows
# ---------------------------------------------------------

def is_metadata_row(text):

    text_lower = text.lower()

    metadata_keywords = [
        "date:",
        "time:",
        "store:",
        "register:",
        "member since:",
        "receipt no",
        "receipt #",
        "invoice",
        "transaction"
    ]

    return any(
        keyword in text_lower
        for keyword in metadata_keywords
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

            # Remove quantity from beginning of name
            if quantity != 1:

                name = re.sub(
                    rf"^\s*{quantity}(?=\s+|x\b|-)\s*",
                    "",
                    name,
                    flags=re.IGNORECASE
                )

            name = name.strip(" -:|")

            # Ignore empty names

            if not name:
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

if __name__ == "__main__":

    ocr_data = load_ocr_data()

    rows = group_rows(ocr_data)

    print("Grouped Receipt Rows:")
    print("---------------------")

    for row in rows:
        print(" | ".join(row))

    items = parse_rows(rows)

    print("\nParsed Items:")
    print("----------------")

    for item in items:
        print(item)

    save_products(items)