"""
Image preprocessing for receipt OCR.

Why each step exists (OpenCV pipeline)
---------------------------------------
1. Upscale x4        - EasyOCR's detector is trained on ~32px glyph height;
                       receipts photographed at arm's length land far below
                       that, so small text is simply not detected.
2. Grayscale         - removes colour noise from thermal paper and lighting.
3. CLAHE             - local contrast equalisation. Receipts are lit unevenly
                       (glare on one side, shadow on the other); CLAHE fixes
                       that locally where a global histogram stretch would
                       blow out the already-bright areas.
4. Gaussian blur     - removes sensor grain before binarisation-style
                       thresholding inside the OCR detector.

Run directly:  python preprocessing.py
"""

from __future__ import annotations

from pathlib import Path

import cv2

INPUT_PATH = Path("input/receipt.jpeg")
OUTPUT_PATH = Path("output/processed_receipt.jpeg")

UPSCALE_FACTOR = 4
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID = (8, 8)
BLUR_KERNEL = (3, 3)


def preprocess(
    input_path: Path | str = INPUT_PATH,
    output_path: Path | str = OUTPUT_PATH,
    upscale: int = UPSCALE_FACTOR,
) -> Path:
    """
    Run the enhancement pipeline and write the processed image.

    Returns the output path so callers can chain without guessing.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    image = cv2.imread(str(input_path))
    if image is None:
        raise FileNotFoundError(f"Could not read image: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Upscale - the single biggest win for small receipt text.
    resized = cv2.resize(
        image, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_CUBIC
    )

    # 2. Grayscale.
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    # 3. CLAHE - uneven lighting is the norm on receipts.
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=CLAHE_TILE_GRID)
    enhanced = clahe.apply(gray)

    # 4. Light denoise.
    denoised = cv2.GaussianBlur(enhanced, BLUR_KERNEL, 0)

    if not cv2.imwrite(str(output_path), denoised):
        raise IOError(f"Failed to write processed image: {output_path}")

    return output_path


def main() -> int:
    out = preprocess()
    print("Preprocessing completed.")
    print(f"Input : {INPUT_PATH}")
    print(f"Output: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())