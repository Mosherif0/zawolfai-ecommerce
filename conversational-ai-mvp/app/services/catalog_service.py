"""
Catalog service: loads the real product catalog (products that have actual
images on disk), assigns deterministic EGP prices, and serves BM25 retrieval.

Design notes
------------
* ZERO third-party dependencies (stdlib only: csv, re, math, os, random).
  The chatbot app must stay lightweight.
* BM25 is implemented from scratch so the ranking logic is auditable.
  Reference: Robertson & Zaragoza (2009) - "The Probabilistic Relevance
  Framework: BM25 and Beyond".
* Prices are DETERMINISTIC: seeded RNG where seed == product_id, so the
  same product always has the same price. This is required so we can assert
  in tests that the LLM quotes the exact catalog price (no hallucinated
  prices), and so the user never sees a product change price between turns.
* The upstream catalog `price` column is NOT a real currency amount
  (range 1..431, mean ~27.7) - it is an internal rank. We therefore derive
  a realistic EGP price from `price_tier` instead of trusting it.
"""

from __future__ import annotations

import csv
import math
import os
import random
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

DEFAULT_CATALOG_PATH = Path(
    r"D:\zawolf-project\recommendation_system\zawolfai-ecommerce-Re"
    r"\data\processed\clean_catalog.csv"
)
DEFAULT_IMAGES_DIR = Path(
    r"D:\zawolf-project\recommendation_system\zawolfai-ecommerce-Re"
    r"\data\images"
)

CATALOG_PATH = Path(os.getenv("CATALOG_PATH", str(DEFAULT_CATALOG_PATH)))
IMAGES_DIR = Path(os.getenv("CATALOG_IMAGES_DIR", str(DEFAULT_IMAGES_DIR)))
IMAGES_OUT_DIR = Path(__file__).resolve().parent.parent / "static" / "images"

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")

# English category -> readable folder under app/static/images/.
# Kept in sync with scripts/organize_images.py.
CATEGORY_SLUGS = {
    "Jacket": "jackets",
    "Coat": "coats",
    "Dress": "dresses",
    "Trousers": "trousers",
    "Top": "tops",
    "Vest top": "vest-tops",
}
DEFAULT_IMAGE_SLUG = "other"

# Realistic Egyptian fashion price bands (EGP) derived from `price_tier`.
TIER_PRICE_RANGES: Dict[str, Tuple[int, int]] = {
    "budget": (150, 350),
    "mid_range": (400, 800),
    "premium": (900, 1800),
}
DEFAULT_TIER = "mid_range"
DEFAULT_PRICE = 500

# Human-readable Arabic labels for the English `category` values.
CATEGORY_AR: Dict[str, str] = {
    "Trousers": "بنطلون",
    "Sweater": "سويتشر",
    "T-shirt": "تيشيرت",
    "Dress": "فستان",
    "Shirt": "قميص",
    "Jacket": "جاكيت",
    "Shorts": "شورت",
    "Vest top": "سترب توب",
    "Blouse": "بلوزة",
    "Top": "توب",
    "Hoodie": "هودي",
    "Hat/beanie": "طاقية",
    "Sneakers": "سنيكرز",
    "Skirt": "تنورة",
    "Cardigan": "كارديجان",
    "Bag": "شنطة",
    "Blazer": "بليزر",
    "Scarf": "شال",
    "Other accessories": "إكسسوارات",
    "Sunglasses": "نظارة شمس",
    "Boots": "بوت",
    "Jumpsuit/Playsuit": "جامبسوت",
    "Hair/alice band": "مندلة شعر",
    "Sandals": "صندل",
    "Pyjama jumpsuit/playsuit": "بيجاما",
    "Cap/peaked": "كاب",
    "Belt": "حزام",
    "Earring": "حلق",
    "Garment Set": "طقم",
    "Ballerinas": "باليرينا",
    "Coat": "كوت",
    "Polo shirt": "بولو شيرت",
    "Necklace": "قلادة",
    "Hat/brim": "قبعة",
    "Pumps": "حذاء كعب",
    "Gloves": "قفازات",
    "Hair string": "رباط شعر",
    "Other shoe": "حذاء",
    "Dungarees": "أوفرول",
    "Slippers": "شبشب",
    "Watch": "ساعة",
    "Outdoor trousers": "بنطلون outdoors",
    "Umbrella": "شمشة",
    "Hair clip": "كلبسة شعر",
    "Heeled sandals": "صندل بكعب",
    "Flat shoe": "حذاء مسطح",
    "Wedge": "wedge",
    "Flip flop": "شبشب",
    "Tie": "ربطة عنق",
    "Nightwear": "بيجاما",
    "Outdoor Waistcoat": "فست outdoors",
    "Tailored Waistcoat": "فست مفصّل",
    "Hair ties": "رباطات شعر",
    "Ring": "خاتم",
    "Sleeping sack": "كيس نوم",
    "Pyjama set": "طقم بيجاما",
    "Outdoor overall": "أوفرول جOutdoor",
    "Sleep Bag": "كيس نوم",
    "Felt hat": "قبعة صوف",
    "Beanie": "طاقية",
    "Waterbottle": "زجاجة مياه",
    "Costumes": "أزياء",
    "Alice band": "مندلة",
    "Straw hat": "قبعة قش",
    "Giftbox": "علبة هدايا",
    "Wallet": "محفظة",
    "Bootie": "بوت",
}
CATEGORY_AR["Outdoor overall"] = "أوفرول outdoors"

# Arabic query hints -> English category tokens. The user writes Egyptian
# Arabic, the catalog is English. Without this mapping BM25 scores ~0.
ARABIC_CATEGORY_HINTS: Dict[str, str] = {
    "بنطلون": "trousers pants jeans trouser",
    "بنطلونات": "trousers pants jeans",
    "بنطلون جينز": "trousers jeans",
    "ترنج": "trousers",
    "قميص": "shirt",
    "جاكيت": "jacket",
    "جاكيتت": "jacket",
    "كوت": "coat",
    "معطف": "coat",
    "فستان": "dress",
    "فساتين": "dress dresses",
    "تيشيرت": "t-shirt tee shirt",
    "شورت": "shorts",
    "هودي": "hoodie",
    "سويتشر": "sweater",
    "كارديجان": "cardigan",
    "بلوزة": "blouse",
    "بلوز": "blouse",
    "توب": "top vest",
    "سترب": "vest top",
    "تنورة": "skirt",
    "بليزر": "blazer",
    "كاب": "cap",
    "طاقية": "beanie hat beanie",
    "شنطة": "bag",
    "باج": "bag",
    "سنيكرز": "sneakers",
    "بوت": "boots boot",
    "صندل": "sandals",
    "شبشب": "slippers",
    "نظارة": "sunglasses",
    "حزام": "belt",
    "حلق": "earring",
    "قلادة": "necklace",
    "ساعة": "watch",
    "شال": "scarf",
    "كلبسة": "hair clip",
    "مندلة": "hair alice band",
    "طقم": "garment set set",
    "بيجاما": "pyjama pajamas",
    "جامبسوت": "jumpsuit playsuit",
    "باليرينا": "ballerinas",
}

# Color hints (Arabic -> English catalog values)
COLOR_HINTS: Dict[str, str] = {
    # black
    "اسود": "black", "سود": "black", "بالك": "black", "كحل": "black",
    "اسود بالكامل": "black",
    # white / cream
    "ابيض": "white", "بيض": "white", "وايت": "white", "أبيض": "white",
    "كريمي": "white", "بيج فاتح": "white", "off white": "white",
    # red family
    "احمر": "red", "red": "red", "crimson": "red", "عنابي": "red",
    "خمري": "red", "burgundy": "red", "dark red": "red", "red wine": "red",
    # blue family
    "ازرق": "blue", "بلو": "blue", "blue": "blue", "navy": "blue",
    "كحلي": "blue", "dark blue": "blue", "سماوي": "blue",
    "light blue": "blue", "other blue": "blue", "تيرو": "blue",
    # green
    "اخضر": "green", "جرين": "green", "green": "green", "زيتي": "green",
    # yellow
    "اصفر": "yellow", "يلو": "yellow", "yellow": "yellow",
    # orange
    "برتقالي": "orange", "اورنج": "orange", "orange": "orange",
    "light orange": "orange",
    # pink
    "وردي": "pink", "بنفسجي فاتح": "pink", "pink": "pink",
    "light pink": "pink", "روز": "pink",
    # grey / beige
    "رمادي": "grey", "gray": "grey", "greige": "grey", "light grey": "grey",
    "بيج": "beige", "بيجيه": "beige", "beige": "beige", "light beige": "beige",
    "light brown": "beige", "بني فاتح": "beige",
    # brown
    "بني": "brown", "براون": "brown", "brown": "brown",
    "نبيتي": "brown", "dark brown": "brown",
    # purple
    "بنفسجي": "purple", "موف": "purple", "purple": "purple",
    "لافندر": "purple",
}

# The catalog stores colours as full strings ("Dark Blue", "Light Pink").
# A colour filter must therefore match on FAMILY, not on equality, otherwise
# asking for "blue" silently misses every "Light Blue" / "Dark Blue" row.
COLOR_FAMILIES: Dict[str, Tuple[str, ...]] = {
    "black": ("black",),
    "white": ("white", "ivory", "cream"),
    "red": ("red", "burgundy", "crimson", "wine", "maroon"),
    "blue": ("blue", "navy", "denim", "sky", "azure"),
    "green": ("green", "olive", "khaki"),
    "yellow": ("yellow", "mustard"),
    "orange": ("orange",),
    "pink": ("pink", "rose", "magenta"),
    "grey": ("grey", "gray", "greige"),
    "beige": ("beige", "sand", "taupe", "nude"),
    "brown": ("brown", "coffee", "chocolate"),
    "purple": ("purple", "violet", "lavender", "lilac"),
}


def color_matches(product_color: str, wanted: str) -> bool:
    """True when a catalog colour string belongs to the requested family."""
    haystack = (product_color or "").lower()
    needle = (wanted or "").lower()
    if not haystack:
        return False
    if needle in haystack:
        return True
    family = COLOR_FAMILIES.get(needle, ())
    return any(member in haystack for member in family)


# "Show me everything" phrases: the customer explicitly wants the full set,
# so we must not silently narrow it with a stray colour word.
SHOW_ALL_WORDS = ("كل المنتجات", "كل حاجة", "اعرض الكل", "وريني كل",
                  "all products", "everything", "كله", "الكل")


def _match_brand(message_lower: str) -> Optional[str]:
    """Return a brand name mentioned in the message, if any."""
    for brand in KNOWN_BRANDS:
        if brand and brand.lower() in message_lower:
            return brand
    return None


# Brands present in the curated catalog. Populated lazily from the data so
# adding a new brand to the CSV needs no code change.
KNOWN_BRANDS: Tuple[str, ...] = ()

# Budget regex: Egyptian numbers, optionally with "جنيه"/"ج"
_NUM = r"(\d{1,6}(?:[.,]\d{1,2})?)"
BUDGET_PATTERNS = [
    # Order matters: explicit "under/above" phrases are checked BEFORE the
    # bare-amount pattern, otherwise "تحت 400 جنيه" falls into the
    # tolerance-band branch and becomes a 500 ceiling.
    re.compile(r"(?:بحد|تحت|أقل|اقل|حدود)\s*" + _NUM),
    re.compile(r"(?:فوق|أكتر|اكتر)\s*" + _NUM),
    re.compile(r"(?:ميزاني|ميزانية|budget|بجميزانية|بميزانية)\s*" + _NUM),
    re.compile(_NUM + r"\s*(?:جنيه|ج\.?p|ج)\b"),
]

# "غالي / رخيص" sentiment -> price tier bias
CHEAP_WORDS = ("رخيص", "ارخص", "أرخص", "ميزانيه", "ميزانية", "بسيط", "خريف")
LUXURY_WORDS = ("غالي", "غلاء", "فخم", "بريميوم", "premium", "مميز", "افضل")

# The curated catalog only carries 5 categories (Trousers, Jacket, Dress,
# Vest top, Top). When the customer asks for something outside it, we route to
# the closest category we DO stock rather than returning nothing - that is what
# a real store assistant does ("we don't have shirts, but these tops are close").
NEAREST_CATEGORY: Dict[str, str] = {
    "t-shirt tee shirt": "top vest",
    "shirt": "top vest",
    "blouse": "top vest",
    "hoodie": "jacket",
    "coat": "jacket",
    "sweater": "jacket",
    "cardigan": "jacket",
    "blazer": "jacket",
    "shorts": "trousers",
    "skirt": "trousers",
    "garment set set": "dress",
    "jumpsuit playsuit": "dress",
}

STOPWORDS = {
    "the", "a", "an", "of", "and", "or", "in", "on", "for", "to", "with",
    "is", "are", "at", "be", "by", "this", "that", "it", "as", "from",
}

# Social / conversational openers that carry NO shopping intent. Returning
# product cards for "اذيك يا باشا" makes the bot feel like a catalogue, not
# a conversation, so we suppress retrieval for these entirely.
CHITCHAT_PHRASES = (
    "اذيك", "إزيك", "ازيك", "السلام عليكم", "صباح الخير", "مساء الخير",
    "صباح النور", "عامل ايه", "إزيك عامل", "تمام شكرا", "شكرا", "thank",
    "hello", "hi ", "hey", "كيف حالك", "الحمد لله", "يلا بينا", "يلا",
    "يلا نمشي", "ماشي", "تمام كده", "جميل", "حلو", "الله يسلمك",
    # bare acknowledgements - extremely common in Egyptian chat
        "تمام", "تماما", "اوك", "اوكي", "يوه", "اهو", "خلاص",
        "اشوف", "طيب كده", "طب كمان", "ماشي يلا", "يلا يلا",
    )
CHITCHAT_MAX_TOKENS = 4

_TOKEN_RE = re.compile(r"[a-z0-9]+")


# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class CatalogProduct:
    """A single sellable product from the real catalog."""

    product_id: int
    name: str
    category: str
    category_ar: str
    subcategory: str
    color: str
    brand: str
    description: str
    price_tier: str
    egp_price: int
    image_file: Optional[str] = None
    organised_file: Optional[str] = None

    @property
    def image_url(self) -> Optional[str]:
        """
        Static URL served by the chat app, or None when no image exists.

        Prefers the organised (readable) file written by
        scripts/organize_images.py and falls back to the flat numeric name so
        the app still works if the organiser has not been run.
        """
        if self.organised_file:
            return f"/static/images/{self.organised_file}"
        if self.image_file:
            return f"/static/images/{self.image_file}"
        return None

    @property
    def metadata_soup(self) -> str:
        return " ".join(
            p for p in (self.name, self.category, self.subcategory, self.color,
                        self.brand, self.description)
            if p
        ).lower()

    def to_card(self, reason: Optional[str] = None) -> Dict:
        """Shape used by the API response / frontend product cards."""
        return {
            "product_id": self.product_id,
            "name": self.name,
            "price": self.egp_price,
            "category": self.category,
            "category_ar": self.category_ar,
            "color": self.color,
            "description": self.description,
            "image_url": self.image_url,
            "price_tier": self.price_tier,
            "reason": reason,
        }


# --------------------------------------------------------------------------
# BM25 (Okapi) - pure stdlib implementation
# --------------------------------------------------------------------------

class BM25Index:
    """
    Minimal Okapi BM25 index.

    BM25(k1, b) formula:

        score(D, Q) = SUM_{q in Q} IDF(q) * f(q,D)*(k1+1)
                                            / (f(q,D) + k1*(1 - b + b*|D|/avgdl))

    IDF uses the Lucene/Robertson variant with +1 smoothing so that terms
    appearing in every document never produce a negative IDF.
    """

    K1 = 1.5
    B = 0.75

    def __init__(self, corpus: Sequence[Sequence[str]]):
        self.corpus = list(corpus)
        self.n_docs = len(self.corpus)
        self.doc_len = [len(d) for d in self.corpus]
        self.avgdl = (sum(self.doc_len) / self.n_docs) if self.n_docs else 0.0
        self.doc_freqs: List[Dict[str, int]] = []
        self.df: Dict[str, int] = {}
        for doc in self.corpus:
            freqs: Dict[str, int] = {}
            for token in doc:
                freqs[token] = freqs.get(token, 0) + 1
            self.doc_freqs.append(freqs)
            for token in freqs:
                self.df[token] = self.df.get(token, 0) + 1
        self._idf: Dict[str, float] = {}

    def idf(self, token: str) -> float:
        """
        Robertson/Lucene IDF with +0.5 smoothing:

            IDF(q) = ln( (N - n(q) + 0.5) / (n(q) + 0.5) + 1 )

        The `+ 1` inside the log keeps IDF non-negative even for terms that
        appear in every document (n(q) == N). We also floor it so a term can
        never subtract from the score.
        """
        if token not in self._idf:
            n = self.df.get(token, 0)
            if n == 0:
                self._idf[token] = 0.0
            else:
                self._idf[token] = max(
                    0.01,
                    math.log(1.0 + (self.n_docs - n + 0.5) / (n + 0.5)),
                )
        return self._idf[token]

    def score(self, query_tokens: Iterable[str]) -> List[float]:
        scores = [0.0] * self.n_docs
        if not self.n_docs:
            return scores
        q_tokens = [t for t in query_tokens if t in self.df]
        if not q_tokens:
            return scores
        for token in q_tokens:
            idf = self.idf(token)
            for i, freqs in enumerate(self.doc_freqs):
                f = freqs.get(token)
                if not f:
                    continue
                denom = f + self.K1 * (1 - self.B + self.B * self.doc_len[i] / self.avgdl)
                scores[i] += idf * (f * (self.K1 + 1)) / denom
        return scores

    def search(self, query_tokens: Iterable[str], top_k: int) -> List[Tuple[int, float]]:
        scores = self.score(query_tokens)
        ranked = sorted(
            range(self.n_docs), key=lambda i: (-scores[i], i)
        )[:top_k]
        return [(i, scores[i]) for i in ranked if scores[i] > 0]


# --------------------------------------------------------------------------
# Query understanding
# --------------------------------------------------------------------------

def tokenize(text: str) -> List[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in STOPWORDS and len(t) > 1]


def expand_query(message: str) -> Tuple[List[str], Dict[str, object]]:
    """
    Translate an Egyptian-Arabic message into BM25 tokens.

    Returns (tokens, parsed_filters) where parsed_filters may contain:
      category: str|None   english category hint
      color:    str|None   english color
      max_price: int|None  upper bound in EGP
      min_price: int|None  lower bound in EGP
    """
    msg = message.lower()
    filters: Dict[str, object] = {}

    tokens: List[str] = []

    # 1) literal english words already in the message (brand, name, color...)
    tokens.extend(tokenize(message))

    # 2) arabic category hints
    for arabic, english in ARABIC_CATEGORY_HINTS.items():
        if arabic in message:
            filters["category"] = english
            tokens.extend(tokenize(english))
            break

    # 2b) Map asks for categories this catalog does not carry onto the nearest
    #     available one, so "تيشيرت" returns tops instead of nothing.
    nearest = NEAREST_CATEGORY.get(str(filters.get("category") or ""))
    if nearest:
        filters["category"] = nearest
        tokens.extend(tokenize(nearest))

    # 3) arabic color hints
    for arabic, english in COLOR_HINTS.items():
        if arabic in message:
            filters["color"] = english
            tokens.append(english)

    # 4) budget. Each pattern is checked in priority order so that an explicit
    #    ceiling ("تحت 400") is never mistaken for a soft budget statement.
    for pattern in BUDGET_PATTERNS:
        m = pattern.search(msg)
        if not m:
            continue
        raw = m.group(1).replace(",", "")
        try:
            value = float(raw)
        except ValueError:
            continue
        before = msg[max(0, m.start() - 14):m.start()]
        if re.search(r"(بحد|تحت|أقل|اقل|حدود)", before) or pattern is BUDGET_PATTERNS[0]:
            filters["max_price"] = int(value)
        elif re.search(r"(فوق|أكتر|اكتر)", before) or pattern is BUDGET_PATTERNS[1]:
            filters["min_price"] = int(value)
        else:
            # "بميزانية 500" -> soft budget, allow a small tolerance band
            filters["max_price"] = int(value * 1.3)
            filters["min_price"] = int(value * 0.5)
        break

    # 5) explicit "show me everything" beats any other reading
    if any(w in msg for w in SHOW_ALL_WORDS):
        filters["show_all"] = True
        return list(tokenize(message)), filters

    # 5b) brand hint (English brand tokens already in the message, or the
    #     customer asks "من ماركة X")
    brand = _match_brand(msg)
    if brand:
        filters["brand"] = brand

    # 6) price sentiment (no explicit number)
    if "max_price" not in filters and any(w in msg for w in CHEAP_WORDS):
        filters["tier_preference"] = "budget"
    elif "max_price" not in filters and any(w in msg for w in LUXURY_WORDS):
        filters["tier_preference"] = "premium"

    # 6) chit-chat gate: no product cards for greetings / acknowledgements.
    #
    #    A bare keyword match is not enough: "حلو" is an acknowledgement in
    #    "حلو كده" but a product modifier in "عاوز حاجة حلوة". So we only
    #    suppress when a chit-chat phrase appears AND nothing in the message
    #    expresses a shopping want (a product noun, a budget, a colour).
    stripped = message.strip().lower()
    has_chitchat_phrase = any(ph in stripped for ph in CHITCHAT_PHRASES)
    expresses_intent = bool(
        filters.get("category")
        or filters.get("color")
        or filters.get("max_price")
        or filters.get("min_price")
        or filters.get("tier_preference")
    )
    if not expresses_intent and has_chitchat_phrase:
        # A product noun anywhere ("حاجة", "منتج", "هدية", ...) also counts as
        # intent, so "عاوز حاجة حلوة" is a request, not an acknowledgement.
        shopping_noun = any(
            w in stripped for w in
            ("حاجة", "منتج", "منتجات", "هدية", "شغلة", "تشكيلة", "ترشيح",
             "اختيار", "جاكيت", "فستان", "بنطلون", "تيشيرت", "هودي",
             "كوت", "قميص")
        )
        if not shopping_noun and len(tokenize(message)) <= CHITCHAT_MAX_TOKENS:
            filters["_chitchat"] = True

    # dedupe preserving order
    seen = set()
    unique_tokens = [t for t in tokens if not (t in seen or seen.add(t))]
    return unique_tokens, filters


# --------------------------------------------------------------------------
# The service
# --------------------------------------------------------------------------

class CatalogService:
    """Loads the catalog once and serves retrieval + lookups."""

    def __init__(self, catalog_path: Path = CATALOG_PATH,
                 images_dir: Path = IMAGES_DIR):
        self.catalog_path = Path(catalog_path)
        self.images_dir = Path(images_dir)
        self.products: List[CatalogProduct] = []
        self._by_id: Dict[int, CatalogProduct] = {}
        self._bm25: Optional[BM25Index] = None
        self.load_error: Optional[str] = None
        self._load()

    # -- loading ---------------------------------------------------------
    def _available_image_ids(self) -> Dict[int, str]:
        """Map product_id -> filename for every image actually on disk.

        Image filenames are zero-padded to 10 digits ('0108775015.jpg') while
        the CSV stores the integer (108775015). We parse to int on both sides.
        """
        available: Dict[int, str] = {}
        if not self.images_dir.is_dir():
            return available
        for fname in os.listdir(self.images_dir):
            stem, ext = os.path.splitext(fname)
            if ext.lower() not in IMAGE_EXTENSIONS:
                continue
            try:
                pid = int(stem)
            except ValueError:
                continue
            available[pid] = fname
        return available

    @staticmethod
    def _deterministic_price(product_id: int, tier: str) -> int:
        """Same product_id + tier always yields the same EGP price."""
        low, high = TIER_PRICE_RANGES.get(tier, (DEFAULT_PRICE, DEFAULT_PRICE))
        if high <= low:
            return low
        rng = random.Random(f"{product_id}:{tier}")
        price = rng.randint(low, high)
        # Round to a natural retail ending (…, 49 / 95 / 00).
        price = (price // 10) * 10 - 1 if price % 10 > 0 else price
        return max(low, min(high, price))

    @staticmethod
    def _load_manifest(images_root: Path) -> Dict[int, str]:
        """
        Read the organised-image manifest written by
        scripts/organize_images.py: product_id -> relative path.

        The manifest is what keeps readable filenames working while the server
        still resolves products by their numeric id.
        """
        manifest_path = images_root / "catalog.json"
        if not manifest_path.is_file():
            return {}
        try:
            import json

            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return {}
        out: Dict[int, str] = {}
        for entry in data:
            pid = entry.get("product_id")
            organised = entry.get("organised_file")
            if isinstance(pid, int) and organised:
                out[pid] = organised
        return out

    def _load(self) -> None:
        try:
            if not self.catalog_path.is_file():
                self.load_error = f"catalog file not found: {self.catalog_path}"
                return

            image_map = self._available_image_ids()
            manifest = self._load_manifest(IMAGES_OUT_DIR)

            products: List[CatalogProduct] = []
            seen_ids = set()
            with self.catalog_path.open("r", encoding="utf-8-sig", newline="") as fh:
                for row in csv.DictReader(fh):
                    raw_pid = (row.get("product_id") or "").strip()
                    try:
                        pid = int(float(raw_pid))
                    except (TypeError, ValueError):
                        continue
                    # Only products with a real image are sellable here.
                    # A product qualifies if it appears in the flat image dir
                    # OR in the organised manifest (the two are alternatives,
                    # not requirements - after organize_images.py the flat
                    # directory is empty by design).
                    if not (manifest or image_map):
                        pass  # no image source at all: keep every row
                    elif pid not in image_map and pid not in manifest:
                        continue
                    if pid in seen_ids:
                        continue
                    seen_ids.add(pid)

                    tier = (row.get("price_tier") or DEFAULT_TIER).strip().lower()
                    category = (row.get("category") or "Unknown").strip()
                    products.append(
                        CatalogProduct(
                            product_id=pid,
                            name=(row.get("product_name") or f"Product {pid}").strip(),
                            category=category,
                            category_ar=CATEGORY_AR.get(category, category),
                            subcategory=(row.get("subcategory") or "").strip(),
                            color=(row.get("color") or "").strip(),
                            brand=(row.get("brand") or "").strip(),
                            description=(row.get("description") or "").strip(),
                            price_tier=tier,
                            egp_price=self._deterministic_price(pid, tier),
                            image_file=image_map.get(pid) or f"{pid:010d}.jpg",
                            organised_file=manifest.get(pid),
                        )
                    )

            self.products = products
            global KNOWN_BRANDS
            KNOWN_BRANDS = tuple(sorted({
                p.brand for p in products if p.brand
            }))
            self._by_id = {p.product_id: p for p in products}
            self._bm25 = BM25Index([tokenize(p.metadata_soup) for p in products])
            if not products:
                self.load_error = "no products matched the available images"
        except Exception as exc:  # pragma: no cover - defensive
            self.load_error = f"{type(exc).__name__}: {exc}"
            self.products = []

    # -- accessors -------------------------------------------------------
    @property
    def size(self) -> int:
        return len(self.products)

    @property
    def available(self) -> bool:
        return bool(self.products)

    def all_products(self) -> List[CatalogProduct]:
        return list(self.products)

    def get(self, product_id: int) -> Optional[CatalogProduct]:
        return self._by_id.get(product_id)

    def price_map(self) -> Dict[str, int]:
        """name(lower) -> EGP price, for hallucination checks in tests."""
        return {p.name.lower(): p.egp_price for p in self.products}

    def categories(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for p in self.products:
            out[p.category_ar] = out.get(p.category_ar, 0) + 1
        return out

    # -- retrieval -------------------------------------------------------
    def _filter_pass(self, products: Iterable[CatalogProduct],
                     filters: Dict[str, object]) -> List[CatalogProduct]:
        """
        Narrow the candidate set one facet at a time.

        Order matters: the most specific facet runs first so that a request
        like "red tee under 600" cannot degrade into "any tee" and then show a
        black one. Each step is skipped when it would empty the result set,
        because a shop assistant should offer the nearest match rather than
        nothing at all.
        """
        result = list(products)
        if filters.get("show_all"):
            return result

        def narrow(predicate) -> None:
            nonlocal result
            hits = [p for p in result if predicate(p)]
            if hits:
                result = hits

        # 1) colour - the most explicit constraint a customer gives
        color = filters.get("color")
        if isinstance(color, str):
            narrow(lambda p: color_matches(p.color, color))

        # 2) category
        category = filters.get("category")
        if isinstance(category, str):
            narrow(lambda p: category in p.metadata_soup)

        # 3) brand
        brand = filters.get("brand")
        if isinstance(brand, str):
            narrow(lambda p: brand.lower() in p.brand.lower())

        # 4) price band
        max_price = filters.get("max_price")
        if isinstance(max_price, int):
            narrow(lambda p: p.egp_price <= max_price)
        min_price = filters.get("min_price")
        if isinstance(min_price, int):
            narrow(lambda p: p.egp_price >= min_price)
        tier_pref = filters.get("tier_preference")
        if isinstance(tier_pref, str):
            narrow(lambda p: p.price_tier == tier_pref)
        return result
        return result

    def _full_sweep(self, top_k: int) -> List[CatalogProduct]:
        """Round-robin across category/colour buckets for "show me everything"."""
        buckets: Dict[str, List[CatalogProduct]] = {}
        for p in self.products:
            buckets.setdefault(f"{p.category_ar}/{p.color.lower()}", []).append(p)

        picked: List[CatalogProduct] = []
        depth = 0
        keys = sorted(buckets)
        while len(picked) < top_k and depth < 50:
            added = False
            for key in keys:
                bucket = buckets[key]
                if depth < len(bucket):
                    picked.append(bucket[depth])
                    added = True
                    if len(picked) >= top_k:
                        break
            if not added:
                break
            depth += 1
        return picked

    def _showcase(self, top_k: int, exclude: Sequence[int] = ()) -> List[CatalogProduct]:
        """
        Diverse fallback for vague/contextual messages ('تمام', 'التاني بكام?').

        Returning the same 3 products on every turn is the #1 thing that makes
        a chatbot feel broken. Instead we walk one product per category (in a
        deterministic round-robin) so consecutive vague messages surface new
        items, then skip anything already excluded.
        """
        by_cat: Dict[str, List[CatalogProduct]] = {}
        for p in self.products:
            if p.product_id in exclude:
                continue
            by_cat.setdefault(p.category_ar, []).append(p)

        if not by_cat:
            return []

        # Rotate the starting category per call so results differ turn to turn.
        self._showcase_cursor = getattr(self, "_showcase_cursor", 0) + top_k
        cats = sorted(by_cat)
        if cats:
            self._showcase_cursor %= len(cats)
            rotation = cats[self._showcase_cursor:] + cats[:self._showcase_cursor]
            self._showcase_cursor = (self._showcase_cursor + top_k) % len(cats)
        else:
            rotation = cats

        picked: List[CatalogProduct] = []
        depth = 0
        while len(picked) < top_k and depth < 50:
            added = False
            for cat in rotation:
                bucket = by_cat[cat]
                if depth < len(bucket):
                    picked.append(bucket[depth])
                    added = True
                    if len(picked) >= top_k:
                        break
            if not added:
                break
            depth += 1
        return picked

    def search(self, message: str, top_k: int = 5,
               fallback_product_ids: Optional[Sequence[int]] = None
               ) -> List[CatalogProduct]:
        """
        Retrieve products for a user message.

        Strategy (in order):
          1. Interpret the message (category / color / budget filters).
          2. BM25 rank the catalog with the expanded query.
          3. Apply hard filters, then re-rank so filtered results come first.
          4. If the query is contextual/vague ('the second one', 'ok?') and we
             have the recently shown product ids from conversation history,
             merge those in at the top.
        """
        if not self.products or not self._bm25:
            return []

        tokens, filters = expand_query(message)

        # Greetings and acknowledgements get a conversational reply, not cards.
        if filters.get("_chitchat"):
            return []

        # "وريني كل المنتجات" means the whole shop, so return one item from
        # every category/colour bucket instead of the BM25 head of the list
        # (which would otherwise be dominated by whichever term repeats most).
        if filters.get("show_all"):
            return self._full_sweep(min(top_k, self.size))
        ranked = self._bm25.search(tokens, top_k=self.size)

        allowed = self._filter_pass(self.products, filters)
        allowed_ids = {p.product_id for p in allowed}
        filtered_rank = [i for i, _ in ranked if self.products[i].product_id in allowed_ids]

        ordered_ids = [self.products[i].product_id for i in filtered_rank]

        # Contextual follow-up ("التاني بكام؟") has no lexical overlap, so we
        # surface what is already on screen. This MUST NOT override an
        # explicit request: if the user said "عاوز جاكيت" we return jackets,
        # not the trousers shown two turns ago.
        has_explicit_intent = bool(
            filters.get("category") or filters.get("color")
            or filters.get("max_price") or filters.get("min_price")
            or filters.get("tier_preference")
        )
        if fallback_product_ids and not has_explicit_intent:
            for pid in fallback_product_ids:
                if pid in self._by_id and pid not in ordered_ids:
                    ordered_ids.append(pid)

        if not ordered_ids:
            # Nothing matched (short/vague query). Respect any explicit budget,
            # then fall back to a diverse rotating showcase so the user never
            # sees the identical cards twice in a row.
            pool = self._filter_pass(self.products, filters)
            if not pool:
                pool = self.products
            buckets: Dict[str, List[CatalogProduct]] = {}
            for p in pool:
                buckets.setdefault(p.category_ar, []).append(p)
            cats = sorted(buckets)
            if cats:
                # Advance the cursor by exactly ONE category each turn and keep
                # a bounded memory of the last returned ids. This guarantees
                # consecutive vague messages surface *different* products, even
                # when top_k and the number of categories share a factor.
                recent = list(getattr(self, "_recent_showcase_ids", []))
                cursor = getattr(self, "_showcase_cursor", 0)
                start = cursor % len(cats)
                rotation = cats[start:] + cats[:start]
                self._showcase_cursor = (cursor + 1) % len(cats)

                picks: List[int] = []
                # pass 1: prefer products not shown recently
                for cat in rotation:
                    for p in buckets[cat]:
                        if len(picks) >= top_k:
                            break
                        if p.product_id not in recent and p.product_id not in picks:
                            picks.append(p.product_id)
                    if len(picks) >= top_k:
                        break
                # pass 2: top up with anything if we ran short
                for p in pool:
                    if len(picks) >= top_k:
                        break
                    if p.product_id not in picks:
                        picks.append(p.product_id)

                ordered_ids = picks
                self._recent_showcase_ids = (recent + picks)[-10:]

            # Last resort: stable slice so the UI is never empty.
            if not ordered_ids:
                ordered_ids = [p.product_id for p in pool][:top_k]

        return [self._by_id[pid] for pid in ordered_ids[:top_k] if pid in self._by_id]

    # -- prompt context --------------------------------------------------
    def format_context(self, products: Sequence[CatalogProduct]) -> str:
        """Compact catalog block injected into the system prompt."""
        if not products:
            return ""
        lines = []
        for p in products:
            bits = [
                f"[ID {p.product_id}] {p.name}",
                f"الفئة: {p.category_ar} ({p.category})",
                f"السعر: {p.egp_price} جنيه",
                f"اللون: {p.color or 'غير محدد'}",
                f"الماركة: {p.brand or 'غير محددة'}",
            ]
            if p.description:
                bits.append(f"الوصف: {p.description}")
            lines.append("- " + " | ".join(bits))
        return "\n".join(lines)


@lru_cache(maxsize=1)
def get_catalog_service() -> CatalogService:
    """Process-wide singleton (loading the CSV is not free)."""
    return CatalogService()


__all__ = [
    "CatalogProduct",
    "CatalogService",
    "BM25Index",
    "get_catalog_service",
    "expand_query",
    "tokenize",
    "TIER_PRICE_RANGES",
]