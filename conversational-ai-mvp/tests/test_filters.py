"""
Facet filtering tests: colour, price, category, brand and "show everything".

The catalog only has 50 rows, so these assertions are exhaustive rather than
sampled - every returned product is checked against every facet the user
asked for.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.catalog_service import (  # noqa: E402
    COLOR_FAMILIES,
    color_matches,
    expand_query,
    get_catalog_service,
)


@pytest.fixture(scope="module")
def catalog():
    return get_catalog_service()


# --------------------------------------------------------------------------
# Colour families: "blue" must match "Light Blue" and "Dark Blue"
# --------------------------------------------------------------------------

def test_colour_family_matching():
    assert color_matches("Light Blue", "blue")
    assert color_matches("Dark Blue", "blue")
    assert color_matches("Other Blue", "blue")
    assert color_matches("Black", "black")
    assert color_matches("Dark Red", "red")
    assert color_matches("Light Pink", "pink")
    # negatives
    assert not color_matches("Black", "blue")
    assert not color_matches("", "blue")


def test_every_catalog_colour_maps_to_a_family(catalog):
    """A colour in the data with no family entry would be unfilterable."""
    for p in catalog.all_products():
        found = any(
            any(m in p.color.lower() for m in members)
            for members in COLOR_FAMILIES.values()
        )
        assert found, f"{p.name}: colour {p.color!r} matches no family"


@pytest.mark.parametrize("message,expected_family", [
    ("عاوز حاجة سودا", "black"),
    ("جاكيت ازرق", "blue"),
    ("فستان احمر", "red"),
    ("بنطلون ابيض", "white"),
    ("عاوز حاجة كحلي", "blue"),
    ("جاكيت عنابي", "red"),
])
def test_colour_filter_returns_only_that_family(message, expected_family, catalog):
    results = catalog.search(message, top_k=5)
    assert results, f"{message} returned nothing"
    for p in results:
        assert color_matches(p.color, expected_family), \
            f"{p.name} has colour {p.color} which is not {expected_family}"


# --------------------------------------------------------------------------
# Combined facets
# --------------------------------------------------------------------------

def test_category_plus_colour(catalog):
    results = catalog.search("جاكيت ازرق", top_k=6)
    assert results
    for p in results:
        assert "jacket" in p.metadata_soup
        assert color_matches(p.color, "blue")


def test_colour_plus_budget(catalog):
    results = catalog.search("بنطلون ازرق تحت 700", top_k=6)
    assert results
    for p in results:
        assert color_matches(p.color, "blue")
        assert p.egp_price <= 700


def test_colour_is_respected_before_category(catalog):
    """
    Regression: filtering category-then-colour let a colour request degrade
    into "any tee" and then return a black one.
    """
    results = catalog.search("عاوز تيشيرت احمر تحت 600", top_k=6)
    assert results
    for p in results:
        assert color_matches(p.color, "red"), \
            f"{p.name} ({p.color}) was returned for a RED request"


def test_budget_only(catalog):
    for p in catalog.search("تحت 400", top_k=8):
        assert p.egp_price <= 400


def test_no_result_still_offers_something(catalog):
    """
    An impossible combination must not return an empty card grid - the shop
    assistant offers the nearest match instead.
    """
    results = catalog.search("فستان بنفسجي غالي تحت 200", top_k=5)
    assert results, "impossible query returned nothing"


# --------------------------------------------------------------------------
# "Show me everything"
# --------------------------------------------------------------------------

@pytest.mark.parametrize("message", [
    "كل المنتجات", "وريني كل حاجة", "اعرض الكل", "show me everything",
])
def test_show_all_detected(message):
    _, filters = expand_query(message)
    assert filters.get("show_all") is True


def test_show_all_is_diverse(catalog):
    """
    A full sweep must span categories, otherwise the grid is 12 pairs of
    trousers and the customer still cannot see the shop.
    """
    results = catalog.search("وريني كل المنتجات", top_k=12)
    assert len(results) >= 10
    assert len({p.category_ar for p in results}) >= 3
    assert len({p.color for p in results}) >= 4


# --------------------------------------------------------------------------
# Brand
# --------------------------------------------------------------------------

def test_brand_filter(catalog):
    from app.services.catalog_service import KNOWN_BRANDS

    brand = KNOWN_BRANDS[0]
    results = catalog.search(f"من ماركة {brand}", top_k=6)
    assert results
    for p in results:
        assert brand.lower() in p.brand.lower()


def test_brands_were_discovered(catalog):
    from app.services.catalog_service import KNOWN_BRANDS

    assert len(KNOWN_BRANDS) > 3, "brands should be discovered from the data"


# --------------------------------------------------------------------------
# Cards stay complete
# --------------------------------------------------------------------------

@pytest.mark.parametrize("message", [
    "جاكيت ازرق", "تحت 500", "فستان", "بنطلون كحلي", "كل المنتجات",
    "عاوز حاجة سودا", "من ماركة Silaley",
])
def test_every_result_has_photo_and_price(message, catalog):
    for p in catalog.search(message, top_k=12):
        assert p.image_url and p.image_url.endswith(".jpg")
        assert p.egp_price > 0
        assert p.name