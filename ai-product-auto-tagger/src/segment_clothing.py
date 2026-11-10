
from pathlib import Path
import json

import numpy as np
import colorsys
import torch
from PIL import Image
from fashn_human_parser import FashnHumanParser
from transformers import (
    AutoModelForZeroShotImageClassification,
    AutoProcessor,
)

INPUT_DIR = Path("input")
OUTPUT_DIR = Path("results")
JSON_PATH = OUTPUT_DIR / "products.json"

CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"

CLOTHING_LABELS = {
    3: "Top",
    4: "Dress",
    5: "Skirt",
    6: "Pants",
}

CATEGORIES = [
    "t-shirt", "polo shirt", "long sleeve shirt",
    "button-up shirt", "blouse", "tank top",
    "hoodie", "sweatshirt", "sweater", "cardigan",
    "jacket", "coat", "blazer", "dress", "skirt",
    "jeans", "trousers", "shorts",
]

CATEGORY_GROUPS = {
    "Top": [
        "t-shirt",
        "polo shirt",
        "long sleeve shirt",
        "button-up shirt",
        "blouse",
        "tank top",
        "hoodie",
        "sweatshirt",
        "sweater",
        "cardigan",
        "jacket",
        "coat",
        "blazer",
    ],
    "Pants": [
        "jeans",
        "trousers",
        "shorts",
    ],
    "Dress": ["dress"],
    "Skirt": ["skirt"],
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def rgb_to_color(rgb):
    r, g, b = [value / 255 for value in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    hue = h * 360

    # Very dark colors
    if v < 0.18:
        return "Black"

    if v > 0.85 and 15 <= hue < 45:
        return "Cream"
 
    # Neutral colors
    if s < 0.18:
        if v > 0.90:
            return "White"

        if v > 0.65 and 15 <= hue < 45:
            return "Off-white"
        
        if v > 0.72:
            return "Light Gray"
        
        return "Gray"

    

    # Olive Green: low saturation, green-yellow hue
    if 40 <= hue < 90 and s < 0.65:
        return "Olive Green"

    # Brown
    if 10 <= hue < 40 and v < 0.60:
        return "Brown"

    # Pink and Red
    if hue < 12 or hue >= 345:
        if v > 0.45 and s < 0.65:
            return "Pink"
        return "Red"

    # Orange
    if 12 <= hue < 35:
        return "Orange"

    # Yellow and Mustard
    if 35 <= hue < 65:
        if v < 0.70:
            return "Mustard"
        return "Yellow"

    # Green
    if 65 <= hue < 165:
        return "Green"

    # Blue
    if 165 <= hue < 255:
        return "Light Blue" if v > 0.65 else "Blue"

    # Purple
    if 255 <= hue < 345:
        return "Purple"

    return "Other"


def get_dominant_colors(image_array, mask, number_of_colors=3):
    pixels = image_array[mask]

    if len(pixels) == 0:
        return []

    if len(pixels) > 30000:
        indexes = np.linspace(
            0, len(pixels) - 1, 30000
        ).astype(int)
        pixels = pixels[indexes]

    pixel_image = Image.fromarray(
        pixels.reshape(1, -1, 3).astype(np.uint8)
    )

    quantized = pixel_image.quantize(
        colors=number_of_colors,
        method=Image.Quantize.MEDIANCUT
    )

    counts = sorted(
        quantized.getcolors(maxcolors=30000) or [],
        reverse=True
    )

    palette = quantized.getpalette()
    results = []
    seen_colors = set()

    for count, palette_index in counts:
        offset = palette_index * 3
        rgb = tuple(palette[offset:offset + 3])
        print(f"Dominant RGB: {rgb}, Pixel count: {count}")
        color_name = rgb_to_color(rgb)

        if color_name not in seen_colors:
            results.append({
                "name": color_name,
                "rgb": list(rgb),
                "pixel_count": count,
            })
            seen_colors.add(color_name)

        if len(results) == 1:
            break

    return results


def detect_pattern(image_array, mask):
    pixels = image_array[mask]

    if len(pixels) == 0:
        return "Unknown"

    pixels = pixels.astype(np.float32)
    color_std = np.mean(np.std(pixels, axis=0))

    if color_std < 25:
        return "Solid"

    return "Printed"


def classify_clothing(
    image,
    clothing_mask,
    processor,
    model,
    device,
    allowed_categories
):
    mask_image = Image.fromarray(
        (clothing_mask * 255).astype(np.uint8)
    )

    white_background = Image.new("RGB", image.size, "white")

    clothing_image = Image.composite(
        image,
        white_background,
        mask_image
    )

    prompts = [
        f"a clear clothing product photo of a {category}"
        for category in allowed_categories
    ]

    inputs = processor(
        text=prompts,
        images=clothing_image,
        return_tensors="pt",
        padding=True,
    ).to(device)

    with torch.no_grad():
        outputs = model(**inputs)
        scores = outputs.logits_per_image[0]

    best_index = scores.argmax().item()

    return (
        allowed_categories[best_index],
        scores[best_index].item()
    )


def select_clothing_mask(
    image,
    segmentation,
    processor,
    model,
    device
):
    candidates = []

    for label_id, label_name in CLOTHING_LABELS.items():
        candidate_mask = segmentation == label_id

        if not candidate_mask.any():
            continue

        mask_percentage = candidate_mask.mean() * 100

        allowed_categories = CATEGORY_GROUPS[label_name]

        category, confidence = classify_clothing(
            image,
            candidate_mask,
            processor,
            model,
            device,
            allowed_categories
        )

        print(
            f"  Candidate: {label_name} -> {category} | "
            f"Score: {confidence:.4f} | "
            f"Area: {mask_percentage:.2f}%"
        )

        candidates.append({
            "mask": candidate_mask,
            "category": category,
            "score": confidence,
            "label": label_name,
            "area": mask_percentage,
        })

    if not candidates:
        return None

    return max(candidates, key=lambda item: item["mask"].mean())

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    existing_products = {}

    if JSON_PATH.exists():
        try:
            old_data = json.loads(
                JSON_PATH.read_text(encoding="utf-8")
            )

            existing_products = {
                item["image"]: item
                for item in old_data
                if "image" in item
            }
        except (json.JSONDecodeError, TypeError):
            print("Could not read previous products.json")

    image_paths = sorted(
        path for path in INPUT_DIR.iterdir()
        if path.suffix.lower() in IMAGE_EXTENSIONS
    )

    if not image_paths:
        print("No images found in input/")
        return

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Device: {device}")

    print("\nLoading FASHN Human Parser...")
    parser = FashnHumanParser(device=device)

    print("\nLoading CLIP model...")
    processor = AutoProcessor.from_pretrained(CLIP_MODEL_NAME)

    model = AutoModelForZeroShotImageClassification.from_pretrained(
        CLIP_MODEL_NAME
    ).to(device)

    model.eval()

    all_results = []

    for image_path in image_paths:
        print(f"\nProcessing: {image_path.name}")

        try:
            image = Image.open(image_path).convert("RGB")
            image_array = np.asarray(image)

            segmentation = np.asarray(parser.predict(image))

            candidate = select_clothing_mask(
                image,
                segmentation,
                processor,
                model,
                device
            )

            if candidate is None:
                print("No clothing detected.")
                continue

            clothing_mask = candidate["mask"]

            mask_path = OUTPUT_DIR / f"{image_path.stem}_mask.png"

            Image.fromarray(
                (clothing_mask * 255).astype(np.uint8)
            ).save(mask_path)

            category = candidate["category"]
            confidence = candidate["score"]

            colors = get_dominant_colors(
                image_array,
                clothing_mask
            )

            pattern = detect_pattern(
                image_array,
                clothing_mask
            )

            old_product = existing_products.get(
                image_path.name, {}
            )

            result = {
                "image": image_path.name,
                "category": category,
                "category_score": round(confidence, 4),
                "colors": colors,
                "pattern": pattern,
                "mask": str(mask_path),
                "segmentation_label": candidate["label"],
            }

            if old_product.get("description"):
                result["description"] = old_product["description"]

            all_results.append(result)

            print(f"Selected mask: {candidate['label']}")
            print(f"Category: {category}")
            print(f"CLIP score: {confidence:.4f}")
            print(
                "Main colors:",
                ", ".join(color["name"] for color in colors)
            )

        except Exception as error:
            print(f"Could not process {image_path.name}: {error}")

    JSON_PATH.write_text(
        json.dumps(all_results, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"\nResults saved to: {JSON_PATH}")


if __name__ == "__main__":
    main()


