"""
Retrieval + grounding evaluation.

Retrieval and generation are measured SEPARATELY, because "the answer is
wrong" has two very different root causes:

  * RETRIEVAL failure  -> the right product never reached the prompt.
                           Fix the ranker/filters, not the model.
  * GROUNDING failure  -> the right product WAS in the prompt but the model
                           still invented a price/name. Fix the prompt.

Run:  pytest tests/test_evaluation.py -v
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.catalog_service import get_catalog_service, expand_query  # noqa: E402


# --------------------------------------------------------------------------
# Ground truth: hand-labelled queries with the expected category constraint.
# --------------------------------------------------------------------------

GROUND_TRUTH = [
    # (query, expected_category_fragment or None)
    ("عاوز جاكيت", "jacket"),
    ("جاكيت كده", "jacket"),
    ("عاوز بنطلون", "trousers"),
    ("بنطلون جينز", "trousers"),
    ("فستان", "dress"),
    ("عاوز فستان سواريه", "dress"),
    ("سترب توب", "vest"),
    ("عاوز توب", "top"),
    ("عاوز كوت", "coat"),
]

# Baseline: the naive substring matcher that used to power _detect_products.
MOCK_NAMES = [
    "classic product", "premium product", "bundle pack", "basic t-shirt",
    "oversized t-shirt", "premium cotton t-shirt", "graphic t-shirt",
    "sport t-shirt", "performance t-shirt", "classic hoodie",
    "premium hoodie", "classic socks pack", "premium socks pack",
    "sports socks pack", "everyday cap", "premium cap", "weekend bundle",
]


@pytest.fixture(scope="module")
def catalog():
    return get_catalog_service()


# --------------------------------------------------------------------------
# 1. Catalog integrity
# --------------------------------------------------------------------------

def test_catalog_loaded(catalog):
    assert catalog.available, f"catalog failed to load: {catalog.load_error}"
    assert catalog.size > 0


def test_every_product_has_an_image(catalog):
    missing = [p.product_id for p in catalog.all_products() if not p.image_file]
    assert not missing, f"products without images: {missing}"


def test_prices_are_deterministic(catalog):
    """Same product must always yield the same price (seed = product_id)."""
    for pid in (108775015, 282832001, 212629040):
        assert catalog.get(pid).egp_price == catalog.get(pid).egp_price


def test_prices_in_sane_range(catalog):
    for p in catalog.all_products():
        assert 100 <= p.egp_price <= 2000, f"{p.name}: implausible price {p.egp_price}"


def test_price_respects_tier_band(catalog):
    from app.services.catalog_service import TIER_PRICE_RANGES
    for p in catalog.all_products():
        low, high = TIER_PRICE_RANGES[p.price_tier]
        assert low <= p.egp_price <= high, f"{p.name} outside {p.price_tier} band"


# --------------------------------------------------------------------------
# 2. Retrieval quality (recall@k vs the old substring baseline)
# --------------------------------------------------------------------------

def _naive_baseline(message: str):
    """What the old substring matcher would have returned."""
    msg = message.lower()
    return [n for n in MOCK_NAMES if n in msg]


def _bm25_recall(catalog, queries, top_k=5):
    hits = 0
    for query, expected in queries:
        results = catalog.search(query, top_k=top_k)
        if expected and any(expected in p.metadata_soup for p in results):
            hits += 1
    return hits / len(queries)


def test_recall_at_5_meets_threshold(catalog):
    recall = _bm25_recall(catalog, GROUND_TRUTH, top_k=5)
    print(f"\nBM25 recall@5 = {recall:.2%}")
    assert recall >= 0.8, f"recall@5 too low: {recall:.2%}"


def test_bm25_beats_substring_baseline(catalog):
    """
    The whole point of adding retrieval. On Egyptian-Arabic queries the
    substring matcher scores ~0 because the catalog is English.
    """
    baseline = sum(1 for q, _ in GROUND_TRUTH if _naive_baseline(q)) / len(GROUND_TRUTH)
    bm25 = _bm25_recall(catalog, GROUND_TRUTH, top_k=5)
    print(f"\nbaseline(substring)={baseline:.2%}  bm25={bm25:.2%}")
    assert bm25 > baseline, f"retrieval did not beat baseline ({bm25:.2%} <= {baseline:.2%})"


def test_category_filter_actually_filters(catalog):
    for query in ("عاوز جاكيت", "عاوز فستان", "سترب توب"):
        results = catalog.search(query, top_k=5)
        assert results, f"no results for {query}"
        cats = {p.category for p in results}
        # every returned product should belong to the asked category cluster
        assert len(cats) <= 2, f"{query}: too many categories leaked: {cats}"


# --------------------------------------------------------------------------
# 3. Budget parsing
# --------------------------------------------------------------------------

@pytest.mark.parametrize("message,cap", [
    ("تحت 400 جنيه", 400),
    ("بحد 300", 300),
    ("حدود 250", 250),
    ("عاوز حاجة تحت 350", 350),
])
def test_ceiling_is_respected(message, cap, catalog):
    _, filters = expand_query(message)
    assert filters.get("max_price") == cap, f"{message} -> {filters}"
    for p in catalog.search(message, top_k=5):
        assert p.egp_price <= cap, f"{p.name} {p.egp_price} exceeds {cap}"


def test_floor_is_respected(catalog):
    _, filters = expand_query("فوق 1200")
    assert filters.get("min_price") == 1200
    for p in catalog.search("فوق 1200", top_k=5):
        assert p.egp_price >= 1200


def test_price_sentiment(catalog):
    _, cheap = expand_query("عايز حاجة رخيصه")
    assert cheap.get("tier_preference") == "budget"
    _, lux = expand_query("عاوز حاجة غالية")
    assert lux.get("tier_preference") == "premium"


# --------------------------------------------------------------------------
# 4. Chit-chat suppression (this is what makes it feel like a conversation)
# --------------------------------------------------------------------------

@pytest.mark.parametrize("message", [
    "اذيك يا باشا", "تمام", "ماشي", "شكرا", "صباح الخير", "يلا بينا",
])
def test_chitchat_returns_no_products(message, catalog):
    assert catalog.search(message, top_k=5) == [], f"{message} should not return cards"


def test_explicit_request_beats_chitchat_memory(catalog):
    """
    Regression: previously-shown products were injected at the front of the
    ranking and overrode a brand new explicit request.
    """
    previous = [282832001, 300908003, 393447015]  # jackets shown last turn
    results = catalog.search("عاوز فستان", top_k=5,
                             fallback_product_ids=previous)
    assert results, "no results"
    assert all("jacket" not in p.metadata_soup for p in results), \
        "explicit dress request was hijacked by previous jackets"


def test_vague_queries_do_not_repeat(catalog):
    """
    Non-chitchat vague messages must surface different cards on consecutive
    turns. (Pure chitchat like 'تمام' returns nothing by design — that is a
    separate test.)
    """
    vague = [
        "عاوز حاجة حلوة",
        "وريني حاجة كويسة",
        "عندكم أي حاجة؟",
        "ايه اللي عندكم؟",
    ]
    seen_sets = []
    for msg in vague:
        results = catalog.search(msg, top_k=3)
        # These queries DO carry shopping intent, so they must return cards.
        assert results, f"{msg} returned nothing"
        seen_sets.append({p.product_id for p in results})
    for i in range(1, len(seen_sets)):
        assert seen_sets[i] != seen_sets[i - 1], f"repeat at turn {i}"


# --------------------------------------------------------------------------
# 5. Grounding invariants the chat layer must never violate
# --------------------------------------------------------------------------

def test_cards_are_grounded_in_catalog(catalog):
    """Every card returned must be a real catalog row with a real image."""
    for query in ("عاوز جاكيت", "تحت 500", "فستان غالي", "بنطلون"):
        for p in catalog.search(query, top_k=5):
            assert catalog.get(p.product_id) is not None
            assert p.image_url and p.image_url.startswith("/static/images/")


def test_catalog_never_returns_mock_products(catalog):
    real_names = {p.name.lower() for p in catalog.all_products()}
    for mock in MOCK_NAMES:
        assert mock not in real_names, f"mock product leaked into catalog: {mock}"


def test_format_context_includes_price_and_id(catalog):
    ctx = catalog.format_context(catalog.all_products()[:3])
    for p in catalog.all_products()[:3]:
        assert str(p.product_id) in ctx
        assert f"{p.egp_price} جنيه" in ctx


# --------------------------------------------------------------------------
# 6. Coverage: every Arabic hint must be well-formed and reachable
# --------------------------------------------------------------------------

def test_arabic_hints_are_clean():
    """
    Regression guard. Arabic hint strings get corrupted surprisingly easily
    during edits, and a corrupted key silently breaks that category.

    A real corrupted key once shipped as 'مacket' -> jacket, which broke the
    jacket category while every other test still passed.
    """
    from app.services.catalog_service import ARABIC_CATEGORY_HINTS, COLOR_HINTS

    # 1) CATEGORY hints must be Arabic-only on the key side.
    for arabic, english in ARABIC_CATEGORY_HINTS.items():
        assert arabic.strip(), "empty arabic key"
        assert all("\u0600" <= ch <= "\u06FF" or ch.isspace() or ch == "-"
                   for ch in arabic), f"corrupted category key: {arabic!r}"
        assert english.strip(), f"{arabic}: empty english target"
        assert all(ord(ch) < 0x2000 for ch in english), \
            f"{arabic}: english target has non-latin chars: {english!r}"

    # 2) COLOR keys are intentionally bilingual (the user may type "navy").
    for arabic, english in COLOR_HINTS.items():
        assert arabic.strip(), "empty color key"
        assert english.strip().islower(), f"{arabic}: color target must be lowercase"
        assert english.strip().isascii(), f"{arabic}: color target must be ascii: {english!r}"


def test_no_duplicate_hint_keys():
    from app.services import catalog_service as cs
    import re as _re

    block = _re.search(r"ARABIC_CATEGORY_HINTS.*?\n\}", open(cs.__file__, encoding="utf-8").read(), _re.S).group()
    keys = _re.findall(r'^\s*"([^"]+)":', block, _re.M)
    dupes = {k for k in keys if keys.count(k) > 1}
    assert not dupes, f"duplicate hint keys: {dupes}"


@pytest.mark.parametrize("message,expected_fragment", [
    ("عاوز تيشيرت", "top"),
    ("عاوز كوت", "jacket"),
    ("عاوز هودي", "jacket"),
    ("عاوز شورت", "trousers"),
])
def test_out_of_catalog_asks_route_to_nearest(message, expected_fragment, catalog):
    """A customer asking for something unstocked still gets a useful answer."""
    results = catalog.search(message, top_k=5)
    assert results, f"{message} returned nothing"
    assert any(expected_fragment in p.metadata_soup for p in results), \
        f"{message} did not route to {expected_fragment}"


@pytest.mark.parametrize("message", [
    "تنورة", "قميص", "جاكيت", "فستان", "بنطلون", "تيشيرت", "هودي", "كوت",
])
def test_common_clothing_asks_return_results(message, catalog):
    assert catalog.search(message, top_k=4), f"{message} returned nothing"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "-s"]))