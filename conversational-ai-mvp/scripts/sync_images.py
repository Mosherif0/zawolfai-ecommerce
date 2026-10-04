"""
Sync product images from the recommendation project into the chat app's
static folder, so the chat app is self-contained (no dependency on a second
running server, no base64 payloads in JSON responses).

Idempotent: only copies files that are missing or byte-size differs.

Usage:
    python scripts/sync_images.py
"""

from __future__ import annotations

import filecmp
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.catalog_service import IMAGE_EXTENSIONS, get_catalog_service  # noqa: E402


def main() -> int:
    svc = get_catalog_service()
    if not svc.available:
        print(f"[FAIL] catalog unavailable: {svc.load_error}")
        return 1

    out_dir = svc.images_dir  # source
    dest_dir = Path(__file__).resolve().parent.parent / "app" / "static" / "images"
    dest_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    skipped = 0
    for product in svc.all_products():
        if not product.image_file:
            continue
        src = out_dir / product.image_file
        dst = dest_dir / product.image_file
        if not src.is_file():
            print(f"[SKIP] missing source: {src}")
            skipped += 1
            continue
        if dst.is_file() and dst.stat().st_size == src.stat().st_size:
            skipped += 1
            continue
        shutil.copy2(src, dst)
        copied += 1

    total_bytes = sum(f.stat().st_size for f in dest_dir.glob("*") if f.is_file())
    print(f"[OK] copied={copied} skipped={skipped} "
          f"total_files={len(list(dest_dir.glob('*')))} "
          f"size={total_bytes / 1024 / 1024:.2f}MB")
    print(f"[OK] destination: {dest_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())