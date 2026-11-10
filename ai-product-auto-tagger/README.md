# AI Product Auto-Tagging & Description Generator

## 1. Project Overview

The **AI Product Auto-Tagging & Description Generator** is an AI-powered component developed for the Zawolf AI E-Commerce project.

Its main purpose is to automate clothing product data extraction and product description generation using computer vision and local Large Language Models (LLMs).

The system allows an e-commerce merchant to provide a clothing product image. It then analyzes the image to identify the clothing category, extract its dominant color, estimate its visual pattern, and generate an English marketing description.

The project is designed to support two types of input images:

- **Product Images:** Clothing items photographed individually, usually against a plain or simple background.
- **Person Images:** Clothing items worn by people.

The current implementation focuses exclusively on clothing products.

## 2. Main Features

### 2.1 Clothing Segmentation

The system uses **FASHN Human Parser** to identify clothing regions within an image.

It generates a segmentation map that assigns different labels to detected clothing regions.

The current implementation focuses on the following segmentation labels:

| Label ID | Clothing Region |
|---|---|
| 3 | Top |
| 4 | Dress |
| 5 | Skirt |
| 6 | Pants |

The system extracts candidate masks for these clothing regions and evaluates them to select a clothing item for further processing.

### 2.2 Clothing Category Classification

The system uses **CLIP (Contrastive Language–Image Pre-training)** with the model:

`openai/clip-vit-base-patch32`

CLIP performs zero-shot image classification by comparing the isolated clothing image against text prompts representing possible clothing categories.

The supported categories include:

- T-shirt
- Polo shirt
- Long sleeve shirt
- Button-up shirt
- Blouse
- Tank top
- Hoodie
- Sweatshirt
- Sweater
- Cardigan
- Jacket
- Coat
- Blazer
- Dress
- Skirt
- Jeans
- Trousers
- Shorts

Classification is performed within category groups corresponding to the segmentation labels.

For example, when the segmentation model detects a Top region, CLIP compares the isolated region against the supported Top categories.

### 2.3 Dominant Color Detection

The system extracts the dominant color from the selected clothing region.

The process includes:

1. Extracting image pixels belonging to the selected clothing mask.
2. Limiting the number of sampled pixels for processing efficiency.
3. Applying color quantization using Pillow's Median Cut algorithm.
4. Extracting the dominant RGB color.
5. Converting the RGB values into a human-readable color name using HSV-based rules.

The current color detection implementation supports names such as:

- Black
- White
- Off-white
- Cream
- Gray
- Light Gray
- Brown
- Red
- Pink
- Orange
- Yellow
- Mustard
- Green
- Olive Green
- Blue
- Light Blue
- Purple

### 2.4 Pattern Detection

The current implementation uses a simple RGB color-variation approach.

It calculates the average standard deviation of the RGB channels across the selected clothing pixels.

The classification logic is:

- Low color variation: `Solid`
- Higher color variation: `Printed`

This is a basic heuristic and does not identify specific pattern types such as floral, striped, plaid, or houndstooth.

### 2.5 AI Product Description Generation

The system uses a locally running Large Language Model through **Ollama**.

Current model:

`qwen2.5:3b`

The model receives the detected product category and color information and generates an English e-commerce product description.

The prompt guides the model to:

- Generate exactly two short sentences.
- Use attractive, professional marketing language.
- Mention the detected product category and color.
- Focus on style and wardrobe versatility.
- Avoid inventing fabric, material, size, fit, brand, or other unsupported product attributes.

The generated description is saved alongside the product's extracted attributes.

## 3. Technologies and Libraries

| Technology | Purpose |
|---|---|
| Python | Main programming language |
| FASHN Human Parser | Clothing segmentation |
| CLIP | Zero-shot clothing category classification |
| PyTorch | Deep learning model execution |
| Hugging Face Transformers | Loading CLIP and its processor |
| NumPy | Image array and pixel processing |
| Pillow (PIL) | Image manipulation, masks, and color quantization |
| Colorsys | RGB-to-HSV color conversion |
| Ollama | Local LLM inference |
| Qwen2.5:3b | Product description generation |
| Requests | Communication with the local Ollama API |
| JSON | Product metadata storage |

The project supports Apple Silicon GPU acceleration through PyTorch MPS when available, with CPU fallback.

## 4. Project Architecture

The system follows a sequential processing pipeline:

**Input Image → Clothing Segmentation → Mask Selection → Category Classification → Color Detection → Pattern Detection → Description Generation → JSON Output**

### Pipeline Details

**Step 1: Image Input**

The system reads supported image formats from the `input/` directory:

- JPG
- JPEG
- PNG
- WEBP

**Step 2: Clothing Segmentation**

FASHN Human Parser generates the segmentation map.

**Step 3: Clothing Mask Selection**

The system extracts candidate clothing masks and classifies each candidate using CLIP within its corresponding category group.

The current implementation selects the candidate with the largest mask area.

**Step 4: Category Classification**

CLIP predicts the most suitable clothing category for the selected mask.

**Step 5: Color Detection**

The selected clothing pixels are analyzed to extract the dominant RGB color and its corresponding color name.

**Step 6: Pattern Detection**

The system estimates whether the clothing item is solid or printed using RGB color variation.

**Step 7: Description Generation**

The detected category and color are sent to the local Qwen2.5:3b model through Ollama.

**Step 8: Output Storage**

The extracted attributes and generated description are saved in:

`results/products.json`

A separate segmentation mask image is also saved for each processed input image.

## 5. Project Structure

```text
ai-product-auto-tagger/
│
├── input/
│   └── Clothing images used as input
│
├── results/
│   ├── products.json
│   └── Generated segmentation masks
│
├── src/
│   ├── segment_clothing.py
│   └── generate_description.py
│
├── experiments/
│   └── Experimental model and attribute testing
│
├── run_pipeline.py
├── requirements.txt
├── .gitignore
└── README.md
```

### Main Files

**`src/segment_clothing.py`**

Responsible for:
- Loading FASHN Human Parser.
- Loading the CLIP model and processor.
- Running clothing segmentation.
- Selecting clothing masks.
- Classifying clothing categories.
- Extracting dominant colors.
- Detecting solid or printed patterns.
- Saving segmentation masks and product attributes.

**`src/generate_description.py`**

Responsible for:
- Reading product information from `results/products.json`.
- Extracting category and color information.
- Sending prompts to the local Ollama API.
- Generating product descriptions using Qwen2.5:3b.
- Updating the JSON file with generated descriptions.

**`run_pipeline.py`**

Acts as the main entry point and orchestrates the execution of the two processing stages.

It runs the segmentation and classification script first, followed by the description generation script.

If a processing stage fails, the pipeline stops and returns the corresponding error code.

## 6. Input and Output

### Input

The merchant provides clothing images inside the `input/` directory.

### Output

For each successfully processed image, the system generates a JSON object containing:

| Field | Description |
|---|---|
| `image` | Original input image filename |
| `category` | Predicted clothing category |
| `category_score` | CLIP classification score |
| `colors` | Detected dominant color and RGB values |
| `pattern` | Estimated pattern classification |
| `mask` | Path to the generated segmentation mask |
| `segmentation_label` | Selected FASHN segmentation label |
| `description` | AI-generated product description |

Example:

```json
{
  "image": "product.jpg",
  "category": "polo shirt",
  "category_score": 34.8192,
  "colors": [
    {
      "name": "Light Blue",
      "rgb": [134, 174, 209],
      "pixel_count": 15252
    }
  ],
  "pattern": "Solid",
  "mask": "results/product_mask.png",
  "segmentation_label": "Top",
  "description": "Generated English product description."
}
```

## 7. Installation and Setup

### Prerequisites

- Python 3.12 recommended for the tested development environment.
- Git.
- Ollama installed locally.
- Sufficient memory and storage for the deep learning models.

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd ai_product_auto_tagger
```

### Step 2: Create a Virtual Environment

```bash
python3.12 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Set Up Ollama

Install Ollama and download the required model:

```bash
ollama pull qwen2.5:3b
```

Make sure the Ollama service is running before generating descriptions.

### Step 5: Add Input Images

Place clothing images inside:

```text
input/
```

### Step 6: Run the Pipeline

```bash
python run_pipeline.py
```

The generated product information will be saved in:

```text
results/products.json
```

## 8. Current Implementation and Limitations

The current version is a working prototype that demonstrates the integration of computer vision and local language models for clothing product enrichment.

Known limitations:

1. **Mask Selection:** Selecting the largest segmentation mask is a heuristic. It may not always select the intended garment when multiple clothing items are present.
2. **Category Classification:** CLIP classification is zero-shot and can occasionally confuse similar categories, such as jeans and trousers.
3. **Color Detection:** The RGB-to-color mapping uses predefined HSV thresholds and may misclassify complex patterns or mixed colors.
4. **Pattern Detection:** The current Solid/Printed classification is based on color variation and may mistake shadows, textures, or lighting differences for patterns.
5. **Description Generation:** LLM-generated descriptions may occasionally contain generic marketing statements or unsupported details. Generated descriptions should be reviewed before publication.
6. **Multiple Clothing Items:** The current pipeline selects one clothing mask per image rather than generating separate product records for every detected garment.

These limitations provide opportunities for future improvements.

## 9. Future Improvements

Potential next development steps include:

- Improving clothing mask selection for images containing multiple garments.
- Improving category classification accuracy.
- Supporting multiple dominant colors.
- Improving color recognition for patterned and textured garments.
- Replacing basic pattern detection with a dedicated visual pattern classifier.
- Distinguishing all-over fabric patterns from localized graphic prints.
- Improving description generation with stricter attribute grounding.
- Adding confidence thresholds and manual review.
- Integrating the component with the main e-commerce backend and product upload workflow.
- Adding automated tests and API integration.

## 10. Project Status

The current prototype successfully processes a test set of 10 clothing images.

The tested pipeline includes:

- Clothing segmentation.
- Zero-shot clothing category classification.
- Dominant color extraction.
- Basic pattern detection.
- Local AI-generated product descriptions.
- JSON-based output storage.

The component is intended to serve as an independent product-enrichment module within the larger Zawolf AI E-Commerce system.
