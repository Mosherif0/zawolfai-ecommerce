"""
Catalog service for the recommendation system.

Replaces the module-level loading in main.py. Three problems with loading at
import time, all of which bite in production:

  1. `main.py` read `data/processed/clean_catalog.csv` with a RELATIVE path, so
     the app only started if uvicorn happened to run from that directory.
  2. The 14k-row CSV and the BM25 index were built on every import, which also
     runs in every test and every worker process.
  3. A failure in loading killed the whole app with a stack trace instead of a
     health check.

Here everything is resolved from `Path(__file__)`, loaded once behind a cache,
and a load failure is recorded rather than raised, so `/health` can report it.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# This file lives in core/, so the project root is one level up. Using
# `parent` resolved data/ to core/data and the catalog silently failed
# to load with a path that looks correct in the source.
BASE = Path(__file__).resolve().parents[1]

# Prefer the shared workspace config when it is importable (single source of
# truth for every service); fall back to this project's own paths so the module
# still works if copied out on its own.
_SHARED_CONFIG = BASE.parents[1] / "zawolf_config.py"
if _SHARED_CONFIG.is_file():
    import sys as _sys
    _sys.path.insert(0, str(BASE.parents[1]))
    from zawolf_config import CATALOG_CSV as _SHARED_CSV, CATALOG_IMAGES_DIR as _SHARED_IMAGES
    CATALOG_CSV = Path(os.getenv("CATALOG_PATH", str(_SHARED_CSV)))
    IMAGES_DIR = Path(os.getenv("CATALOG_IMAGES_DIR", str(_SHARED_IMAGES)))
else:
    CATALOG_CSV = Path(
        os.getenv("CATALOG_PATH", str(BASE / "data" / "processed" / "clean_catalog.csv"))
    )
    IMAGES_DIR = Path(os.getenv("CATALOG_IMAGES_DIR", str(BASE / "data" / "images")))

STATIC_DIR = BASE / "static"

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")


# --------------------------------------------------------------------------
# BM25 (pure stdlib - the project has no rank_bm25 dependency in production)
# --------------------------------------------------------------------------

class BM25Index:
    """
    Minimal Okapi BM25, so the service has no third-party search dependency.

        score(D, Q) = SUM IDF(q) * f(q,D)(k1+1) / (f(q,D) + k1(1 - b + b|D|/avgdl))

    IDF uses the Robertson/Lucene variant with +0.5 smoothing and a +1 inside
    the log, which keeps it non-negative even for terms appearing everywhere.
    """

    K1 = 1.5
    B = 0.75

    def __init__(self, corpus: List[List[str]]):
        import math

        self._math = math
        self.corpus = corpus
        self.n_docs = len(corpus)
        self.doc_len = [len(d) for d in corpus]
        self.avgdl = (sum(self.doc_len) / self.n_docs) if self.n_docs else 0.0

        self.doc_freqs: List[Dict[str, int]] = []
        self.df: Dict[str, int] = {}
        for doc in corpus:
            freqs: Dict[str, int] = {}
            for token in doc:
                freqs[token] = freqs.get(token, 0) + 1
            self.doc_freqs.append(freqs)
            for token in freqs:
                self.df[token] = self.df.get(token, 0) + 1

        self._idf: Dict[str, float] = {}

    def idf(self, token: str) -> float:
        if token not in self._idf:
            n = self.df.get(token, 0)
            self._idf[token] = 0.0 if n == 0 else max(
                0.01, self._math.log(1.0 + (self.n_docs - n + 0.5) / (n + 0.5))
            )
        return self._idf[token]

    def scores(self, query_tokens: List[str]) -> np.ndarray:
        out = np.zeros(self.n_docs, dtype=float)
        if not self.n_docs:
            return out
        present = [t for t in query_tokens if t in self.df]
        if not present:
            return out
        for token in present:
            idf = self.idf(token)
            for i, freqs in enumerate(self.doc_freqs):
                f = freqs.get(token)
                if not f:
                    continue
                denom = f + self.K1 * (1 - self.B + self.B * self.doc_len[i] / self.avgdl)
                out[i] += idf * (f * (self.K1 + 1)) / denom
        return out

    def top(self, query_tokens: List[str], k: int) -> List[int]:
        scores = self.scores(query_tokens)
        order = np.argsort(-scores)
        return [int(i) for i in order[:k] if scores[i] > 0]


# --------------------------------------------------------------------------
# service
# --------------------------------------------------------------------------

class CatalogService:
    """Loads the catalog once and serves lookups, images and search."""

    def __init__(self, catalog_csv: Path = CATALOG_CSV, images_dir: Path = IMAGES_DIR):
        self.catalog_csv = Path(catalog_csv)
        self.images_dir = Path(images_dir)

        self.df: pd.DataFrame = pd.DataFrame()
        self._by_id: Dict[int, pd.Series] = {}
        self._image_files: Dict[int, str] = {}
        self._bm25: Optional[BM25Index] = None
        self.load_error: Optional[str] = None

        self._load()

    # -- loading ---------------------------------------------------------
    def _scan_images(self) -> Dict[int, str]:
        """
        Map product_id -> filename.

        Filenames are zero-padded to 10 digits ('0108775015.jpg') while the CSV
        stores integers (108775015), so both sides are parsed to int.
        """
        found: Dict[int, str] = {}
        if not self.images_dir.is_dir():
            return found
        for name in os.listdir(self.images_dir):
            stem, ext = os.path.splitext(name)
            if ext.lower() not in IMAGE_EXTENSIONS:
                continue
            try:
                found[int(stem)] = name
            except ValueError:
                continue
        return found

    def _load(self) -> None:
        try:
            if not self.catalog_csv.is_file():
                self.load_error = f"catalog not found: {self.catalog_csv}"
                return

            raw = pd.read_csv(self.catalog_csv)
            self._image_files = self._scan_images()

            if self._image_files:
                # Only products we can actually show: a card without a photo is
                # worse than no card.
                raw = raw[raw["product_id"].isin(self._image_files)]
            raw = raw.drop_duplicates(subset=["product_id"]).reset_index(drop=True)

            self.df = raw
            self._by_id = {int(r["product_id"]): r for _, r in raw.iterrows()}
            self._bm25 = BM25Index([self._tokens(r) for _, r in raw.iterrows()])

            if raw.empty:
                self.load_error = "no products matched the available images"
        except Exception as exc:
            self.load_error = f"{type(exc).__name__}: {exc}"
            self.df = pd.DataFrame()

    # -- accessors -------------------------------------------------------
    @staticmethod
    def _tokens(row) -> List[str]:
        parts = [
            str(row.get("product_name", "")),
            str(row.get("category", "")),
            str(row.get("subcategory", "")),
            str(row.get("colour_group_name", "")),
            str(row.get("brand", "")),
            str(row.get("description", "")),
        ]
        text = " ".join(parts).lower()
        return [t for t in "".join(c if c.isalnum() else " " for c in text).split() if len(t) > 1]

    @property
    def available(self) -> bool:
        return not self.df.empty

    @property
    def size(self) -> int:
        return len(self.df)

    def get(self, product_id: int):
        return self._by_id.get(int(product_id))

    def image_url(self, product_id: int) -> Optional[str]:
        """Static URL for the photo, or None when the product has none."""
        filename = self._image_files.get(int(product_id))
        if not filename:
            return None
        # The URL must live under the mounted /static dir, so it points at the
        # synced copy in static/images/ rather than at the original data dir.
        return f"/static/images/{filename}"

    def sync_images(self, static_images: Path) -> int:
        """
        Copy the product photos under the static dir so /static/images/... can
        serve them. Idempotent: only copies what is missing.
        """
        static_images = Path(static_images)
        static_images.mkdir(parents=True, exist_ok=True)
        copied = 0
        for filename in self._image_files.values():
            source = self.images_dir / filename
            target = static_images / filename
            if source.is_file() and not target.is_file():
                try:
                    target.write_bytes(source.read_bytes())
                    copied += 1
                except OSError:
                    pass
        return copied

    def image_bytes(self, filename: str) -> Optional[bytes]:
        """Read a photo from disk; the caller serves and caches it."""
        path = self.images_dir / filename
        if not path.is_file():
            return None
        try:
            return path.read_bytes()
        except OSError:
            return None

    # -- search ----------------------------------------------------------
    def search(self, query: str, top_k: int = 12) -> List[int]:
        if not self.available or self._bm25 is None:
            return []
        tokens = [t for t in query.lower().split() if len(t) > 1]
        return self._search_tokens(tokens, top_k)

    def _search_tokens(self, tokens: List[str], top_k: int) -> List[int]:
        """BM25 lookup for an already-tokenised query."""
        if not self.available or self._bm25 is None or not tokens:
            return []
        return [int(self.df.iloc[i]["product_id"]) for i in self._bm25.top(tokens, top_k)]

    def related(self, product_id: int, top_k: int = 6) -> Dict[str, List[int]]:
        """
        Complementary and similar items.

        "Complete the look" needs a DIFFERENT category (a top without trousers
        is not an outfit); "similar" needs the same one. Ranking uses BM25 over
        the product's own metadata, so textually close items float up.
        """
        origin = self.get(product_id)
        if origin is None:
            return {"complete_the_look": [], "similar": []}

        pid = int(product_id)
        origin_cat = str(origin.get("category", "")).lower()

        candidates = [i for i in self._search_tokens(self._tokens(origin), 40)
                      if i != pid]
        if not candidates:
            frame = self.df[self.df["product_id"] != pid]
            candidates = [int(x) for x in frame["product_id"].head(top_k)]

        complete, similar = [], []
        for other in candidates:
            row = self.get(other)
            if row is None:
                continue
            cat = str(row.get("category", "")).lower()
            if cat != origin_cat and len(complete) < top_k:
                complete.append(other)
            elif cat == origin_cat and len(similar) < top_k:
                similar.append(other)

        return {"complete_the_look": complete, "similar": similar}

    def facets(self) -> Dict:
        """Distinct values per facet with counts - what the UI needs to filter."""
        if not self.available:
            return {}
        return {
            "categories": self.df["category"].value_counts().to_dict(),
            "colours": self.df["colour_group_name"].value_counts().to_dict()
            if "colour_group_name" in self.df else {},
            "brands": self.df["brand"].value_counts().to_dict()
            if "brand" in self.df else {},
            "price_tiers": self.df["price_tier"].value_counts().to_dict()
            if "price_tier" in self.df else {},
        }


@lru_cache(maxsize=1)
def get_catalog_service() -> CatalogService:
    """Process-wide singleton; loading is not free."""
    return CatalogService()