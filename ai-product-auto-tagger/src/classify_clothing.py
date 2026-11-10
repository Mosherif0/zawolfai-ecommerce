
from pathlib import Path

import torch
from PIL import Image
from transformers import (
    AutoModelForZeroShotImageClassification,
    AutoProcessor,
)

MODEL_NAME = "openai/clip-vit-base-patch32"

IMAGE_PATH = Path("input/product.jpg")
MASK_PATH = Path("results/product_mask.png")

CATEGORIES = [
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
    "dress",
    "skirt",
    "jeans",
    "trousers",
    "shorts",
]


def main():
    if not IMAGE_PATH.exists():
        print(f"Image not found: {IMAGE_PATH}")
        return

    if not MASK_PATH.exists():
        print(f"Mask not found: {MASK_PATH}")
        return

    device = "mps" if torch.backends.mps.is_available() else "cpu"

    print(f"Loading model: {MODEL_NAME}")
    print(f"Device: {device}")

    processor = AutoProcessor.from_pretrained(MODEL_NAME)

    model = AutoModelForZeroShotImageClassification.from_pretrained(
        MODEL_NAME
    ).to(device)

    model.eval()

    image = Image.open(IMAGE_PATH).convert("RGB")
    mask = Image.open(MASK_PATH).convert("L")

    if mask.size != image.size:
        mask = mask.resize(image.size, Image.Resampling.NEAREST)

    # Replace background with white using the clothing mask
    white_background = Image.new("RGB", image.size, "white")
    clothing_image = Image.composite(
        image,
        white_background,
        mask
    )

    prompts = [
        f"a clear clothing product photo of a {category}"
        for category in CATEGORIES
    ]

    inputs = processor(
        text=prompts,
        images=clothing_image,
        return_tensors="pt",
        padding=True,
    ).to(device)

    with torch.no_grad():
        outputs = model(**inputs)
        scores = outputs.logits_per_image.softmax(dim=1)[0]

    top_indices = scores.argsort(descending=True)[:5]

    print("\nTop clothing category predictions using MASK:")

    for index in top_indices.tolist():
        category = CATEGORIES[index]
        score = scores[index].item()
        print(f"{category}: {score:.2%}")


if __name__ == "__main__":
    main()


