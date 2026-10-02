import re


def load_ocr_text(path):
    lines = []

    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split("\t")

            if len(parts) >= 2:
                text = parts[0]
                confidence = float(parts[1])

                # Ignore very low-confidence OCR results
                if confidence >= 0.3:
                    lines.append(text)

    return lines


def extract_product_info(lines):
    text = " ".join(lines)

    product_info = {
        "product_name": None,
        "brand": None,
        "price": None,
        "color": None,
        "size": None,
        "volume": None,
        "material": None,
        "ingredients": None,
    }

    # Product name
    for line in lines:
        if "MOISTURE SERUM" in line.upper():
            product_info["product_name"] = line
            break

    # Brand
    for line in lines:
        if "NIVEA" in line.upper():
            product_info["brand"] = "NIVEA"
            break

    # Volume
    volume_match = re.search(r"(\d+)\s*(ml|ML)", text)

    if volume_match:
        product_info["volume"] = volume_match.group(0)

    # Ingredients
    ingredient_keywords = [
        "Aqua",
        "Paraffinum",
        "Isohexadecane",
        "Glycerin",
        "Ingredients"
    ]

    ingredient_lines = []

    for line in lines:
        if any(keyword.lower() in line.lower() for keyword in ingredient_keywords):
            ingredient_lines.append(line)

    if ingredient_lines:
        product_info["ingredients"] = " ".join(ingredient_lines)

    return product_info


ocr_lines = load_ocr_text("output/ocr_raw.txt")

product_info = extract_product_info(ocr_lines)

print("\nExtracted Product Information:")
print("--------------------------------")

for key, value in product_info.items():
    print(f"{key}: {value}")