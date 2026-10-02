import easyocr
import json


reader = easyocr.Reader(["en"])

result = reader.readtext("output/processed_receipt.jpeg")


# Save raw OCR text
with open("output/ocr_raw.txt", "w", encoding="utf-8") as file:

    for bbox, text, confidence in result:
        file.write(
            f"{text}\t{confidence:.4f}\n"
        )


# Save structured OCR data
ocr_data = []

for bbox, text, confidence in result:

    ocr_data.append({
        "text": text,
        "confidence": round(float(confidence), 4),
        "bbox": [
            [int(point[0]), int(point[1])]
            for point in bbox
        ]
    })


with open(
    "output/ocr_data.json",
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        ocr_data,
        file,
        indent=4
    )


print("OCR completed successfully.")
print("Saved to: output/ocr_raw.txt")
print("Saved to: output/ocr_data.json")