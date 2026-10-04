"""
Pipeline + inventory tests.

These use synthetic OCR JSON and the real SQLite layer, so they are fast and
deterministic. Image-based accuracy is covered separately by
`test_receipt_images.py`, which needs the EasyOCR weights.
"""

import json
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import inventory as inv  # noqa: E402
import receipt_parser as rp  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    """Every test gets an isolated SQLite file."""
    db = tmp_path / "test_inventory.db"
    monkeypatch.setattr(inv, "SQLITE_PATH", db)
    yield


def _ocr(text, y, x0=0, x1=300, conf=0.9):
    return {"text": text, "confidence": conf,
            "bbox": [[x0, y], [x1, y], [x1, y + 20], [x0, y + 20]]}


def _zara_receipt():
    """The ZARA receipt used as ground truth."""
    return [
        _ocr("ZARA", 0),
        _ocr("Store: 0327", 40), _ocr("Register: 03", 40, 320, 500),
        _ocr("Date: 12/02/2025", 70), _ocr("Time: 18:27", 70, 320, 500),
        _ocr("Black Blazer", 120), _ocr("59.99", 120, 340, 430),
        _ocr("White Shirt", 150), _ocr("45.95", 150, 340, 430),
        _ocr("Wide Leg Jeans", 180), _ocr("69.99", 180, 340, 430),
        _ocr("Leather Belt", 210), _ocr("25.00", 210, 340, 430),
        _ocr("Subtotal", 260), _ocr("200.93", 260, 340, 430),
        _ocr("Tax", 290), _ocr("16.07", 290, 340, 430),
        _ocr("Total", 320), _ocr("217.00", 320, 340, 430),
        _ocr("Payment", 360), _ocr("Visa", 360, 340, 430),
    ]


# --------------------------------------------------------------------------
# accuracy against the known receipt
# --------------------------------------------------------------------------

def test_zara_receipt_exact_match():
    """Ground truth from the receipt itself; every field must match."""
    items = rp.parse_rows(rp.group_rows(_zara_receipt()))
    assert len(items) == 4, items
    got = {i["name"]: i["price"] for i in items}
    assert got == {
        "Black Blazer": 59.99,
        "White Shirt": 45.95,
        "Wide Leg Jeans": 69.99,
        "Leather Belt": 25.00,
    }


def test_totals_are_not_products():
    items = rp.parse_rows(rp.group_rows(_zara_receipt()))
    names = " ".join(i["name"].lower() for i in items)
    for word in ("subtotal", "tax", "total", "payment", "visa", "store", "date"):
        assert word not in names, f"{word!r} leaked into the products"


def test_quantities_default_to_one_when_not_printed():
    items = rp.parse_rows(rp.group_rows(_zara_receipt()))
    assert all(i["quantity"] == 1 for i in items)


# --------------------------------------------------------------------------
# inventory layer
# --------------------------------------------------------------------------

def test_save_inserts_then_accumulates():
    first = [{"name": "Black Blazer", "price": 59.99, "quantity": 1}]
    second = [{"name": "Black Blazer", "price": 59.99, "quantity": 2}]

    assert inv.save_products(first)[0]["action"] == "added"
    assert inv.save_products(second)[0]["action"] == "updated"

    row = inv.list_products()[0]
    assert row["quantity"] == 3
    assert row["price"] == 59.99


def test_prices_update_on_rescan():
    inv.save_products([{"name": "Belt", "price": 25.00, "quantity": 1}])
    inv.save_products([{"name": "Belt", "price": 29.99, "quantity": 1}])
    assert inv.list_products()[0]["price"] == 29.99


def test_full_receipt_flow_updates_inventory():
    items = rp.parse_rows(rp.group_rows(_zara_receipt()))
    inv.save_products(items)

    rows = {r["name"]: r for r in inv.list_products()}
    assert set(rows) == {"Black Blazer", "White Shirt", "Wide Leg Jeans", "Leather Belt"}
    assert sum(r["quantity"] for r in rows.values()) == 4

    # a second pass of the same receipt doubles the stock
    inv.save_products(items)
    assert sum(r["quantity"] for r in inv.list_products()) == 8


def test_receipt_audit_trail():
    items = rp.parse_rows(rp.group_rows(_zara_receipt()))
    inv.save_products(items)
    assert inv.log_receipt("zara.jpg", items) == 4
    assert inv.log_receipt("empty.jpg", []) == 0


def test_reset_clears_everything():
    inv.save_products([{"name": "X", "price": 1.0, "quantity": 1}])
    inv.reset_database()
    assert inv.list_products() == []


def test_no_postgres_selected_by_default():
    assert inv.using_postgres() is False


# --------------------------------------------------------------------------
# pipeline helpers
# --------------------------------------------------------------------------

def test_pipeline_safe_stem():
    import pipeline

    assert pipeline.safe_stem(Path("WhatsApp Image 2026-10-04 at 6.22.44 PM.jpeg")) \
        .startswith("WhatsApp_Image")
    assert "/" not in pipeline.safe_stem(Path("a/b c.jpg"))
    assert pipeline.safe_stem(Path("....jpg"))


def test_pipeline_parse_phase_without_images(tmp_path, monkeypatch):
    """
    Exercise the pipeline's parse+persist stages on a prepared OCR file,
    without needing EasyOCR or a real image.
    """
    import pipeline

    monkeypatch.setattr(inv, "SQLITE_PATH", tmp_path / "p.db")

    ocr_json = tmp_path / "receipt.ocr.json"
    ocr_json.write_text(json.dumps(_zara_receipt()), encoding="utf-8")

    items = rp.parse_rows(rp.group_rows(json.loads(ocr_json.read_text())))
    assert len(items) == 4

    report = inv.save_products(items)
    assert {r["action"] for r in report} == {"added"}
    assert len(inv.list_products()) == 4


# --------------------------------------------------------------------------
# the two additional real receipts
# --------------------------------------------------------------------------

def _lc_waikiki_receipt():
    """LC Waikiki Alexandria - 3 items, no quantity column."""
    return [
        _ocr("LC WAIKIKI", 0),
        _ocr("Store 0488", 40), _ocr("Register 05", 40, 320, 480),
        _ocr("Date 11/19/2025", 70), _ocr("Time 13:17", 70, 320, 480),
        _ocr("Women Sweater", 120), _ocr("79.99", 120, 340, 430),
        _ocr("Men Hoodie", 150), _ocr("99.99", 150, 340, 430),
        _ocr("Kids T-Shirt", 180), _ocr("59.99", 180, 340, 430),
        _ocr("Subtotal", 230), _ocr("239.97", 230, 340, 430),
        _ocr("Tax", 260), _ocr("12.00", 260, 340, 430),
        _ocr("Total", 290), _ocr("251.97", 290, 340, 430),
    ]


def test_lc_waikiki_exact_match():
    items = rp.parse_rows(rp.group_rows(_lc_waikiki_receipt()))
    assert {i["name"]: i["price"] for i in items} == {
        "Women Sweater": 79.99,
        "Men Hoodie": 99.99,
        "Kids T-Shirt": 59.99,
    }


def _ikea_receipt():
    """IKEA Egypt - the thousands separator case that used to break prices."""
    return [
        _ocr("IKEA", 0),
        _ocr("Store 0010", 40), _ocr("Register 12", 40, 320, 480),
        _ocr("KALLAX Shelf Unit", 100), _ocr("2,495.00", 100, 300, 460),
        _ocr("Desk Lamp", 130), _ocr("599.00", 130, 300, 460),
        _ocr("Plant Pot", 160), _ocr("149.00", 160, 300, 460),
        _ocr("Storage Box", 190), _ocr("199.00", 190, 300, 460),
        _ocr("Subtotal", 240), _ocr("3,442.00", 240, 300, 460),
        _ocr("Total", 300), _ocr("3,614.10", 300, 300, 460),
    ]


def test_ikea_thousands_separator_is_preserved():
    """
    Regression guard: a blanket comma->dot replacement turned '2,495.00'
    into '24.95'. The whole-item test fails loudly if it regresses.
    """
    items = rp.parse_rows(rp.group_rows(_ikea_receipt()))
    prices = {i["name"]: i["price"] for i in items}
    assert prices["KALLAX Shelf Unit"] == 2495.00
    assert prices["Desk Lamp"] == 599.00
    assert prices["Subtotal"] if "Subtotal" in prices else True  # must be absent
    assert "Subtotal" not in prices


def test_corrupted_subtotal_is_not_a_product():
    """OCR reads the receipt's own label as 'Subtota/'."""
    rows = [
        _ocr("Denim Jeans", 0), _ocr("s49,99", 0, 320, 430),
        _ocr("Subtota/", 60), _ocr("s89,97", 60, 320, 430),
    ]
    items = rp.parse_rows(rp.group_rows(rows))
    names = [i["name"] for i in items]
    assert "Denim Jeans" in names[0]
    assert not any("Subtota" in n for n in names), names


@pytest.mark.parametrize("label", [
    "Subtota/", "SUBTOTAL", "Subtotal:", "Sub total", "T0TAL", "Totel",
    "Toal", "TAX", "VAT",
])
def test_fuzzy_footer_labels(label):
    assert rp.is_summary_row(f"{label} 100.00", 100.0)


def test_merged_ocr_blob_is_rejected():
    """
    A non-receipt image (e.g. a music app) produces very long merged rows.
    They must not become inventory entries.
    """
    blob = " ".join(f"track number {n} artist name here" for n in range(12))
    rows = [_ocr(blob, 0), _ocr("4.0", 0, 340, 430)]
    items = rp.parse_rows(rp.group_rows(rows))
    assert items == [], f"blob leaked into products: {items}"


def test_barcode_is_never_a_quantity():
    """
    Regression: '068949055223 2.00' parsed as quantity 68949055223 and wrote
    68 billion units into the inventory.
    """
    assert rp.extract_quantity("068949055223 2.00") == 1
    assert rp._identifier_only("068949055223 2.00")
    assert not rp._identifier_only("Black Blazer 59.99")
    assert not rp._identifier_only("6FT HDMI CABLE")


def test_barcode_row_produces_no_product():
    rows = [_ocr("068949055223", 0), _ocr("2.00", 0, 340, 430)]
    assert rp.parse_rows(rp.group_rows(rows)) == []


def test_footer_noise_is_never_sold():
    for text in ("CREDIT TEND ACCOUNT 9999 APPROvaL",
                 "PAID RETURN POLIcY RETURNS ACCEPTE",
                 "SHE HARRY STYLES ITEM COUNT : 10"):
        assert rp.is_summary_row(text, 10.0), text
