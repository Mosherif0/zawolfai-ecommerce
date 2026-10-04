"""
End-to-end receipt pipeline.

    input/<file>  ->  preprocess  ->  OCR  ->  parse  ->  inventory DB

Every stage is optional at the CLI so a single step can be re-run while
debugging:

    python pipeline.py                 # process every image in input/
    python pipeline.py --dry-run       # no database writes
    python pipeline.py --limit 2       # first two images only
    python pipeline.py --no-ocr        # reuse an existing ocr_data.json
    python pipeline.py "input/one.jpg" # a single named file

Outputs land in output/:
    processed/<name>.jpg    enhanced image
    <name>.ocr.json         detections for that specific image
    report.json             per-image summary + final inventory snapshot
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

BASE = Path(__file__).resolve().parent
INPUT_DIR = BASE / "input"
OUTPUT_DIR = BASE / "output"
PROCESSED_DIR = OUTPUT_DIR / "processed"

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def find_images(folder: Path) -> List[Path]:
    if not folder.is_dir():
        return []
    return sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    )


def safe_stem(path: Path) -> str:
    """Filesystem-safe name so 'WhatsApp Image ... .jpeg' never breaks a path."""
    stem = path.stem
    cleaned = "".join(c if (c.isalnum() or c in "-_") else "_" for c in stem)
    return cleaned.strip("_")[:60] or "image"


def run_one(image_path: Path, do_ocr: bool = True, lang=None,
            validate: bool = True) -> Dict:
    """Run the full pipeline for a single image and return its summary."""
    import preprocessing as preprocessing_mod
    import receipt_parser as parser
    import language_config as lang_config
    import validation as validation_mod

    stem = safe_stem(image_path)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    lang = lang_config.normalize(lang or lang_config.DEFAULT_LANG)
    print(f"\n{'=' * 70}\n{image_path.name}   [lang={lang}]\n{'=' * 70}")

    # --- 1. preprocessing ---
    processed_path = PROCESSED_DIR / f"{stem}.jpg"
    try:
        preprocessing_mod.preprocess(image_path, processed_path)
        print(f"  preprocess -> {processed_path.name}")
    except Exception as exc:
        print(f"  preprocess FAILED: {exc}")
        return {"file": image_path.name, "status": "preprocess_failed",
                "error": str(exc)}

    # --- 2. OCR ---
    ocr_json = OUTPUT_DIR / f"{stem}.ocr.json"
    ocr_data: List[Dict] = []
    if do_ocr:
        try:
            import ocr as ocr_mod

            raw_txt = OUTPUT_DIR / f"{stem}.ocr.txt"
            ocr_data = ocr_mod.run_ocr(processed_path, raw_txt, ocr_json)
            print(f"  ocr        -> {len(ocr_data)} detections "
                  f"({raw_txt.name}, {ocr_json.name})")
        except Exception as exc:
            print(f"  ocr FAILED: {type(exc).__name__}: {exc}")
            return {"file": image_path.name, "status": "ocr_failed",
                    "error": str(exc), "processed": processed_path.name}
    else:
        if ocr_json.is_file():
            ocr_data = json.loads(ocr_json.read_text(encoding="utf-8"))
            print(f"  ocr        -> reusing {ocr_json.name} ({len(ocr_data)} detections)")
        else:
            print(f"  ocr        -> SKIPPED, {ocr_json.name} not found")
            return {"file": image_path.name, "status": "ocr_skipped"}

    # --- 3. reject gate ---
    # Runs BEFORE parsing: once rows exist, nothing downstream can tell a real
    # line item from a track title on a novelty receipt.
    if validate:
        verdict = validation_mod.validate(ocr_data, processed_path, lang)
        if not verdict.is_receipt:
            print(f"  gate       -> REJECTED ({verdict.reason})")
            return {"file": image_path.name, "status": "not_a_receipt",
                    "validation": verdict.to_dict()}
        print(f"  gate       -> accepted (score {verdict.score:.2f}, "
              f"signals: {', '.join(verdict.matched_signals[:4])})")

    # --- 4. parse ---
    try:
        rows = parser.group_rows(ocr_data)
        items = parser.parse_rows(rows)
    except Exception as exc:
        print(f"  parse FAILED: {exc}")
        return {"file": image_path.name, "status": "parse_failed", "error": str(exc)}

    print(f"  rows       -> {len(rows)}")
    for item in items:
        print(f"               qty={item['quantity']}  {item['name']}  @ {item['price']}")

    return {
        "file": image_path.name,
        "status": "ok",
        "detections": len(ocr_data),
        "rows": len(rows),
        "items": items,
        "ocr_json": ocr_json.name,
        "processed": processed_path.name,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser_args = argparse.ArgumentParser(description="Receipt OCR pipeline")
    parser_args.add_argument("files", nargs="*", help="specific image(s) to process")
    parser_args.add_argument("--dry-run", action="store_true",
                             help="parse but do not write to the database")
    parser_args.add_argument("--no-ocr", action="store_true",
                             help="reuse existing OCR output")
    parser_args.add_argument("--limit", type=int, default=0,
                             help="process at most N images")
    parser_args.add_argument("--input", default=str(INPUT_DIR))
    parser_args.add_argument("-l", "--lang", default=None,
                             choices=["en", "ar"],
                             help="document language (default: OCR_LANGUAGE env)")
    parser_args.add_argument("--no-validate", action="store_true",
                             help="skip the receipt gate (debugging only)")
    args = parser_args.parse_args(argv)

    images = [Path(f) for f in args.files] if args.files else find_images(Path(args.input))
    if args.limit:
        images = images[:args.limit]

    if not images:
        print(f"No images found in {args.input}")
        print("Put receipt images there first (see input/).")
        return 1

    print(f"Processing {len(images)} image(s)"
          f"{' [dry-run]' if args.dry_run else ''}\n")

    summaries = [run_one(img, do_ocr=not args.no_ocr, lang=args.lang,
                         validate=not args.no_validate) for img in images]

    ok = [s for s in summaries if s["status"] == "ok"]
    total_items = sum(len(s["items"]) for s in ok)

    print(f"\n{'=' * 70}")
    print(f"SUMMARY: {len(ok)}/{len(summaries)} images parsed, "
          f"{total_items} line items")
    print(f"{'=' * 70}")

    if not ok or args.dry_run:
        if ok:
            print("\n[dry-run] database not touched.")
        return 0 if ok else 1

    # --- 4. persist ---
    # Write through warehouse, not the flat inventory module: warehouse keeps
    # the stock_movements ledger, so a rebuild can always reconstruct the
    # quantities from source.
    import warehouse as wh

    wh.init_db()
    print("\nWriting to database...")
    grand_total = 0
    for summary in ok:
        if not summary["items"]:
            continue
        result = wh.record_receipt(summary["items"], source_file=summary["file"])
        grand_total += sum(i["quantity"] for i in summary["items"])
        print(f"\n  {summary['file']}")
        for entry in result["items"]:
            icon = "+" if entry["action"] == "added" else "="
            print(f"    {icon} {entry['name']:34} qty={entry['quantity']}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "report.json").write_text(
        json.dumps(summaries, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'=' * 70}")
    print(f"INVENTORY AFTER {len(ok)} RECEIPT(S)  (total units: {grand_total})")
    print(f"{'=' * 70}")
    for row in wh.list_products():
        print(f"  #{row['id']:<4} {row['name'][:34]:36} "
              f"{row['price']:>9.2f}  x{row['quantity']}")

    print(f"\nReport: {OUTPUT_DIR / 'report.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())