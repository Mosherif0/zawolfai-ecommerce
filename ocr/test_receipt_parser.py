"""
Regression tests for the receipt parser.

Each test below corresponds to a bug found by diagnose.py:
  1. thousands separators turned 1,299.50 into 1.29
  2. a trailing "3X" quantity was read as quantity=1
  3. "Shirts USD9.99" left "USD" inside the product name
  4. "WOOL SOCKS 3X" lost its final S  ->  "WOOL SOCKX"
  5. "Store #12" was not recognised as metadata and became a product

These run without easyocr / cv2 / psycopg: the database module is stubbed.
"""

import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

if "database" not in sys.modules:
    db = types.ModuleType("database")
    db.get_connection = lambda: (_ for _ in ()).throw(RuntimeError("no database"))
    sys.modules["database"] = db

if "inventory" not in sys.modules:
    inv = types.ModuleType("inventory")
    inv.save_products = lambda items: None
    sys.modules["inventory"] = inv

import receipt_parser as rp  # noqa: E402


# --------------------------------------------------------------------------
# 1. prices
# --------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("$19.99", 19.99),
    ("19.99", 19.99),
    ("USD89", 89.0),
    ("USD89.99", 89.99),
])
def test_simple_prices(text, expected):
    assert rp.extract_price(text) == expected


def test_thousands_separator_is_preserved():
    """Regression: '1,299.50' used to be read as 1.29."""
    assert rp.extract_price("1,299.50") == 1299.50
    assert rp.extract_price("TOTAL 1,299.50") == 1299.50


def test_decimal_comma_is_still_supported():
    assert rp.extract_price("19,99") == 19.99


# --------------------------------------------------------------------------
# 2. quantity in leading and trailing position
# --------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("2 x CABLE", 2),
    ("3 - DEF", 3),
    ("COTTON T-SHIRT", 1),
    ("6FT HDMI CABLE", 1),          # a measurement, not a count
])
def test_leading_quantity(text, expected):
    assert rp.extract_quantity(text) == expected


def test_trailing_quantity():
    """Regression: 'WOOL SOCKS 3X' used to report quantity 1."""
    assert rp.extract_quantity("WOOL SOCKS 3X") == 3
    assert rp.extract_quantity("CABLE 2 @") == 2
    assert rp.extract_quantity("ITEM (4)") == 4


# --------------------------------------------------------------------------
# 3+4. name cleaning
# --------------------------------------------------------------------------

def test_usd_token_removed_fully():
    assert rp.remove_price("Shirts USD9.99") == "Shirts"


def test_trailing_s_is_not_eaten():
    """
    Regression: the currency regex matched the "S" in "SOCKS" (a letter S
    followed by " 3") and deleted it, turning "WOOL SOCKS" into "WOOL SOCKX".
    The quantity token itself IS price-like and is stripped; the WORD must
    survive intact.
    """
    cleaned = rp.remove_price("WOOL SOCKS 3X")
    assert "SOCKX" not in cleaned, f"the final S was eaten: {cleaned!r}"
    assert cleaned == "WOOL SOCKS", cleaned


def test_thousands_separator_is_stripped_with_the_price():
    """Regression: only '2,' was removed, leaving 'KALLAX Shelf Unit 2'."""
    assert rp.remove_price("KALLAX Shelf Unit 2,495.00") == "KALLAX Shelf Unit"


def test_orphan_currency_glyph_is_removed():
    """OCR split the currency mark from the digits: 's49,99'."""
    assert rp.remove_price("Denim Jeans s49,99") == "Denim Jeans 49.99"


def test_trailing_quantity_is_stripped_from_the_final_name():
    """The count token is removed from the name in parse_rows, not here."""
    ocr = [_ocr("WOOL SOCKS 3X", 0), _ocr("$12.99", 0, 320, 420)]
    items = rp.parse_rows(rp.group_rows(ocr))
    assert items[0]["name"] == "WOOL SOCKS"
    assert items[0]["quantity"] == 3


def test_plural_names_survive():
    for name in ("Jeans", "Sneakers", "Shirts"):
        assert rp.remove_price(f"{name} $45.00") == name


# --------------------------------------------------------------------------
# 5. metadata detection
# --------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "Store #12",
    "Store 12",
    "STORE 42",
    "Date: 01/02/2026",
    "Receipt No 99",
    "Terminal 3",
    "Cashier: Ahmed",
    "Thank you",
    "www.example.com",
])
def test_metadata_rows(text):
    assert rp.is_metadata_row(text), f"{text!r} should be metadata"


# --------------------------------------------------------------------------
# end-to-end on a synthetic receipt
# --------------------------------------------------------------------------

def _ocr(text, y, x0=0, x1=300):
    return {"text": text, "confidence": 0.9,
            "bbox": [[x0, y], [x1, y], [x1, y + 20], [x0, y + 20]]}


def test_end_to_end_two_items():
    ocr = [
        _ocr("WOOL SOCKS 3X", 0), _ocr("$12.99", 0, 320, 420),
        _ocr("COTTON T-SHIRT", 40), _ocr("$24.50", 40, 320, 420),
        _ocr("SUBTOTAL", 90, 0, 200), _ocr("$37.49", 90, 320, 420),
    ]
    items = rp.parse_rows(rp.group_rows(ocr))

    assert len(items) == 2, items
    assert items[0]["name"] == "WOOL SOCKS", items[0]
    assert items[0]["quantity"] == 3, items[0]
    assert items[0]["price"] == 12.99
    assert items[1]["name"] == "COTTON T-SHIRT"
    assert items[1]["price"] == 24.50


def test_subtotal_never_becomes_a_product():
    ocr = [
        _ocr("SUBTOTAL", 0), _ocr("$37.49", 0, 320, 420),
        _ocr("TAX 5.00", 40), _ocr("$2.50", 40, 320, 420),
        _ocr("TOTAL", 80), _ocr("$39.99", 80, 320, 420),
    ]
    items = rp.parse_rows(rp.group_rows(ocr))
    assert items == [], f"footer rows leaked into products: {items}"


def test_multiline_name_is_joined():
    ocr = [
        _ocr("DENIM JACKET", 0),
        _ocr("REGULAR FIT", 25),
        _ocr("$89.99", 0, 320, 420),
    ]
    items = rp.parse_rows(rp.group_rows(ocr))
    assert len(items) == 1
    assert "DENIM JACKET" in items[0]["name"]
    assert "REGULAR FIT" in items[0]["name"]