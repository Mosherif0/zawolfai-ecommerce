"""
Organize the product photos into readable, browsable structure.

Why
---
`0108775015.jpg` tells you nothing when you open the folder. This script
produces a tree you can actually read:

    app/static/images/
      catalog.json                 <- machine-readable manifest
      jackets/
        0282832001__kevin-softshell-jacket-1.jpg
        0300908003__freja-coat.jpg
        ...
      dresses/
      trousers/
      tops/
      vest-tops/

Filenames keep the numeric product_id as a PREFIX on purpose: the server
resolves images by id, and the id must stay the source of truth. The readable
slug is a human aid only.

Idempotent: safe to re-run.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.catalog_service import get_catalog_service  # noqa: E402

IMAGES_ROOT = Path(__file__).resolve().parent.parent / "app" / "static" / "images"
SOURCE_DIR = Path(
    r"D:\zawolf-project\recommendation_system\zawolfai-ecommerce-Re\data\images"
)

# English category -> folder name. Arabic folder names break URLs on some
# systems and make the paths hard to type, so we use ASCII slugs.
CATEGORY_SLUGS = {
    "Jacket": "jackets",
    "Coat": "coats",
    "Dress": "dresses",
    "Trousers": "trousers",
    "Top": "tops",
    "Vest top": "vest-tops",
    "Shirt": "shirts",
    "Sweater": "sweaters",
    "Skirt": "skirts",
    "Shorts": "shorts",
    "Hoodie": "hoodies",
    "Blouse": "blouses",
    "Cardigan": "cardigans",
    "Blazer": "blazers",
}
DEFAULT_SLUG = "other"

# Colour -> folder slug. Normalising "Light Blue" and "Dark Blue" into one
# "blue" bucket keeps the tree small and matches how customers actually ask
# ("عاوز حاجة زرقا"), not how the upstream dataset spells it.
COLOR_SLUGS = {
    "black": "black", "white": "white", "red": "red", "blue": "blue",
    "green": "green", "yellow": "yellow", "orange": "orange",
    "pink": "pink", "grey": "grey", "beige": "beige", "brown": "brown",
    "purple": "purple",
}

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")


def color_slug(catalog_color: str) -> str:
    """Normalise a catalog colour string ('Light Blue') to a folder slug."""
    from app.services.catalog_service import COLOR_FAMILIES, DEFAULT_IMAGE_SLUG

    haystack = (catalog_color or "").lower()
    for family, members in COLOR_FAMILIES.items():
        if any(m in haystack for m in members):
            return COLOR_SLUGS.get(family, family)
    return DEFAULT_IMAGE_SLUG


def slugify(text: str, max_len: int = 40) -> str:
    """Lowercase ascii slug; falls back to 'item' when nothing survives."""
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (s[:max_len].rstrip("-")) or "item"


def find_source_image(product_id: int, filename: str) -> Path | None:
    """Locate the original photo in the upstream project."""
    if not SOURCE_DIR.is_dir():
        return None
    ext = os.path.splitext(filename)[1] or ".jpg"
    for candidate in (
        SOURCE_DIR / filename,
        SOURCE_DIR / f"{product_id}{ext}",
        SOURCE_DIR / f"{product_id:010d}{ext}",
    ):
        if candidate.is_file():
            return candidate
    return None


def main() -> int:
    svc = get_catalog_service()
    if not svc.available:
        print(f"[FAIL] catalog unavailable: {svc.load_error}")
        return 1

    IMAGES_ROOT.mkdir(parents=True, exist_ok=True)

    manifest = []
    copied = 0
    reused = 0

    for product in svc.all_products():
        cat_slug = CATEGORY_SLUGS.get(product.category, DEFAULT_SLUG)
        col_slug = color_slug(product.color)
        folder = f"{cat_slug}/{col_slug}"
        target_dir = IMAGES_ROOT / folder
        target_dir.mkdir(parents=True, exist_ok=True)

        readable = slugify(product.name)
        pid_padded = str(product.product_id).zfill(10)
        new_name = f"{pid_padded}__{col_slug}__{readable}.jpg"
        target = target_dir / new_name

        src = find_source_image(product.product_id, product.image_file or "")
        if src is None:
            print(f"[SKIP] no source image for {product.product_id}")
            continue

        if target.is_file() and target.stat().st_size == src.stat().st_size:
            reused += 1
        else:
            shutil.copy2(src, target)
            copied += 1

        rel_url = f"/static/images/{folder}/{new_name}"
        manifest.append({
            "product_id": product.product_id,
            "name": product.name,
            "category": product.category,
            "category_ar": product.category_ar,
            "color": product.color,
            "color_slug": col_slug,
            "brand": product.brand,
            "price_tier": product.price_tier,
            "price_egp": product.egp_price,
            "description": product.description,
            "image_file": product.image_file,
            "organised_file": f"{folder}/{new_name}",
            "url": rel_url,
        })

    # Remove stale images left over from an earlier layout. A jpg is stale when
    # it is not referenced by the manifest we just wrote, which covers both the
    # old flat numeric copies and the older single-level category folders.
    keep = {entry["organised_file"] for entry in manifest}
    stale = 0
    for p in IMAGES_ROOT.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
            rel = p.relative_to(IMAGES_ROOT).as_posix()
            if rel not in keep:
                p.unlink()
                stale += 1
    # prune now-empty directories (keep the root)
    for d in sorted(IMAGES_ROOT.rglob("*"), key=lambda x: len(x.parts), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()

    (IMAGES_ROOT / "catalog.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[OK] copied={copied} reused={reused} stale_removed={stale}")
    print(f"[OK] manifest: {IMAGES_ROOT / 'catalog.json'} ({len(manifest)} entries)")
    print("[OK] layout:")
    for cat_dir in sorted(p for p in IMAGES_ROOT.iterdir() if p.is_dir()):
        cols = sorted(c for c in cat_dir.iterdir() if c.is_dir())
        if not cols:
            continue
        for c in cols:
            n = len(list(c.glob("*.jpg")))
            if n:
                print(f"       {cat_dir.name:12}/{c.name:10} -> {n:2} images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())