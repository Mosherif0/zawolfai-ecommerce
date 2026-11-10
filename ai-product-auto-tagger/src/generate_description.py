
from pathlib import Path
import json
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:3b"

INPUT_JSON = Path("results/products.json")



def generate_description(category, colors):
    color_names = [
        color["name"] for color in colors if color.get("name")
    ]

    color_text = ", ".join(color_names[:3]) if color_names else "unspecified"

    prompt = f"""
You are an expert fashion e-commerce copywriter.

Write an attractive, natural, and professional product description.

Product category: {category}
Product color: {color_text}

Requirements:
1. Write exactly TWO short sentences.
2. Start with an engaging and natural marketing phrase.
3. Mention the exact product category and color.
4. Make the description catchy, elegant, and suitable for an online fashion store.
5. Focus on the product's style and wardrobe versatility.
6. Do NOT claim specific fabric, fit, material, quality, or design details.
7. Do NOT invent occasions or activities.
8. Avoid exaggerated words like "impeccable" and "unparalleled".
9. Avoid repetitive phrases like "elevate your wardrobe".
10. Return English only, without a title.

"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 120
            }
        },
        timeout=180
    )

    response.raise_for_status()

    description = response.json()["message"]["content"].strip()

    if not description:
        raise ValueError("Ollama returned an empty description.")

    return description



def main():
    if not INPUT_JSON.exists():
        print(f"File not found: {INPUT_JSON}")
        return

    products = json.loads(
        INPUT_JSON.read_text(encoding="utf-8")
    )

    for product in products:
        product["description"] = generate_description(
            product["category"],
            product.get("colors", [])
        )

        print(f"\nProcessing: {product['image']}")
        print(f"Description: {product['description']}")

    INPUT_JSON.write_text(
        json.dumps(products, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\nAll descriptions generated successfully!")


if __name__ == "__main__":
    main()

