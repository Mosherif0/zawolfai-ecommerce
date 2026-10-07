"""
EasyOCR wrapper.

Two things this fixes versus a naive script:

1. **Lazy reader.** EasyOCR downloads ~100MB of weights and takes several
   seconds to initialise. Constructing the Reader at import time (the old
   version) meant importing this module - for a test, or to reuse the config -
   paid the full cost. `_get_reader()` builds it once, on first use.
2. **Confidence filtering happens here**, not in the parser, so
   `ocr_data.json` is already clean.

Run directly:  python ocr.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv()

IMAGE_PATH = Path("output/processed_receipt.jpeg")
RAW_TEXT_PATH = Path("output/ocr_raw.txt")
JSON_PATH = Path("output/ocr_data.json")

MIN_CONFIDENCE = float(os.getenv("OCR_MIN_CONFIDENCE", "0.30"))
def _languages_for(lang=None):
    """Arabic mode also runs English: Egyptian receipts mix both scripts."""
    import language_config as lang_config

    forced = os.getenv("OCR_LANGUAGES")
    if forced:
        return [l.strip() for l in forced.split(",") if l.strip()]
    return lang_config.ocr_languages(lang)

_reader = None


def _get_reader(lang=None):
    """Build the EasyOCR Reader once, lazily with auto-recovery for corrupt cache."""
    global _reader
    if _reader is None:
        import easyocr

        try:
            _reader = easyocr.Reader(_languages_for(), download_enabled=True, verbose=False)
        except Exception:
            # Clear corrupt ~/.EasyOCR/model files automatically
            model_dir = os.path.expanduser("~/.EasyOCR/model")
            if os.path.exists(model_dir):
                for f in os.listdir(model_dir):
                    fp = os.path.join(model_dir, f)
                    if os.path.isfile(fp):
                        try:
                            os.remove(fp)
                        except Exception:
                            pass
            _reader = easyocr.Reader(_languages_for(), download_enabled=True, verbose=False)
    return _reader


def run_ocr(
    image_path: Path | str = IMAGE_PATH,
    raw_text_path: Path | str = RAW_TEXT_PATH,
    json_path: Path | str = JSON_PATH,
    min_confidence: float = MIN_CONFIDENCE,
) -> List[Dict[str, Any]]:
    """
    OCR one receipt image and persist the results.

    Returns the list of detections (each with text / confidence / bbox).
    """
    image_path = Path(image_path)
    raw_text_path = Path(raw_text_path)
    json_path = Path(json_path)

    if not image_path.is_file():
        raise FileNotFoundError(f"Receipt image not found: {image_path}")

    result = _get_reader().readtext(str(image_path))

    raw_text_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    ocr_data: List[Dict[str, Any]] = []
    with raw_text_path.open("w", encoding="utf-8") as fh:
        for bbox, text, confidence in result:
            fh.write(f"{text}\t{confidence:.4f}\n")
            if confidence < min_confidence:
                continue
            ocr_data.append({
                "text": text,
                "confidence": round(float(confidence), 4),
                "bbox": [[int(p[0]), int(p[1])] for p in bbox],
            })

    json_path.write_text(json.dumps(ocr_data, indent=2, ensure_ascii=False),
                         encoding="utf-8")
    return ocr_data


def main() -> int:
    data = run_ocr()
    print(f"OCR completed: {len(data)} detections kept.")
    print(f"Raw text : {RAW_TEXT_PATH}")
    print(f"JSON     : {JSON_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())