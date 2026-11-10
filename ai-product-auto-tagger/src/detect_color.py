
from pathlib import Path
from collections import Counter

from PIL import Image

IMAGE_PATH = Path("input/product.jpg")


def detect_color(image_path):
    image = Image.open(image_path).convert("RGB")

    # Resize the image to make processing faster
    image.thumbnail((200, 200))

    pixels = list(image.getdata())

    # Ignore very bright and very dark pixels when possible
    filtered_pixels = [
        pixel for pixel in pixels
        if not (
            max(pixel) - min(pixel) < 15
            and (max(pixel) > 235 or max(pixel) < 25)
        )
    ]

    if not filtered_pixels:
        filtered_pixels = pixels

    average = tuple(
        sum(pixel[i] for pixel in filtered_pixels)
        // len(filtered_pixels)
        for i in range(3)
    )

    r, g, b = average

    if max(r, g, b) < 60:
        color = "Black"
    elif min(r, g, b) > 200:
        color = "White"
    elif max(r, g, b) - min(r, g, b) < 25:
        color = "Gray"
    elif r > g * 1.25 and r > b * 1.2:
        color = "Red"
    elif r > g * 1.15 and g > b * 1.1:
        color = "Brown"
    elif g > r * 1.15 and g > b * 1.1:
        color = "Green"
    elif b > r * 1.15 and b > g * 1.1:
        color = "Blue"
    elif r > 150 and g > 120 and b < 120:
        color = "Yellow"
    else:
        color = "Other"

    return color, average


def main():
    if not IMAGE_PATH.exists():
        print(f"Image not found: {IMAGE_PATH}")
        return

    color, rgb = detect_color(IMAGE_PATH)

    print(f"Image: {IMAGE_PATH.name}")
    print(f"Detected color: {color}")
    print(f"Average RGB: {rgb}")


if __name__ == "__main__":
    main()
