"""
Receipt gate + language tests.

The gate's job is to keep non-receipts out of the inventory, so most of these
assert REJECTION for real non-receipt files that were captured from the
project's own input/ folder.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import language_config as lc  # noqa: E402
import receipt_parser as rp  # noqa: E402
import validation as v  # noqa: E402

# this file sits next to the project root, so output/ is a direct child
OUTPUT = Path(__file__).resolve().parent / "output"


def load(stem):
    path = OUTPUT / f"{stem}.ocr.json"
    if not path.is_file():
        pytest.skip(f"{path.name} not present")
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# Real files: what MUST be accepted
# --------------------------------------------------------------------------

REAL_RECEIPTS = [
    "WhatsApp_Image_2026-10-04_at_6_22_44_PM",   # ZARA
    "WhatsApp_Image_2026-10-04_at_6_39_59_PM",   # LC Waikiki
    "WhatsApp_Image_2026-10-04_at_6_44_14_PM",   # IKEA
    "images",                                     # Lowe's (OCR: "slbtotal")
    "images__1",
    "images__2",
    "download",
]


@pytest.mark.parametrize("stem", REAL_RECEIPTS)
def test_real_receipts_are_accepted(stem):
    result = v.validate(load(stem))
    assert result.is_receipt, f"{stem}: {result.reason}"


# --------------------------------------------------------------------------
# Real files: what MUST be rejected
# --------------------------------------------------------------------------

NON_RECEIPTS = [
    "spotify",
    "aes_receiptify__spotify",
]


@pytest.mark.parametrize("stem", NON_RECEIPTS)
def test_non_receipts_are_rejected(stem):
    """A playlist screenshot printed 'receipt', 'thank you' and 'total'."""
    result = v.validate(load(stem))
    assert not result.is_receipt, f"{stem} wrongly accepted ({result.score:.2f})"


def test_weak_signals_alone_never_accept():
    """The exact trap: every weak word, nothing structural."""
    ocr = [{"text": t, "confidence": 0.9,
            "bbox": [[0, 0], [200, 0], [200, 20], [0, 20]]}
           for t in ("RECEIPT", "THANK YOU", "TOTAL", "ITEM COUNT : 10",
                     "12.00", "4.50", "9.99")]
    result = v.validate(ocr)
    assert not result.is_receipt
    assert result.structure_score == 0.0


def test_corrupted_keyword_still_counts():
    """'slbtotal' is what EasyOCR produced for a real Lowe's receipt."""
    ocr = [{"text": t, "confidence": 0.9,
            "bbox": [[0, i * 30], [200, i * 30], [200, i * 30 + 20], [0, i * 30 + 20]]}
           for i, t in enumerate(["slbtotal : 203.61", "TAX 11.30",
                                   "DEBIT TEND 213.84", "APPROVED"])]
    result = v.validate(ocr)
    assert result.is_receipt, result.reason


def test_empty_ocr_is_rejected():
    assert not v.validate([]).is_receipt


def test_numbers_alone_never_accept():
    """A price table with no receipt furniture is not a receipt."""
    ocr = [{"text": t, "confidence": 0.9,
            "bbox": [[0, i * 30], [200, i * 30], [200, i * 30 + 20], [0, i * 30 + 20]]}
           for i, t in enumerate(["12.00", "45.99", "7.50", "99.99", "3.25"])]
    assert not v.validate(ocr).is_receipt


def test_validation_result_explains_itself():
    r = v.validate(load("spotify"))
    assert r.reason, "a rejection must say why"
    d = r.to_dict()
    assert set(d) >= {"is_receipt", "score", "structure_score", "numbers_score",
                      "shape_score", "matched_signals", "reason"}


# --------------------------------------------------------------------------
# Arabic
# --------------------------------------------------------------------------

def test_arabic_digits_are_normalised():
    assert lc.normalize_arabic("٢٤٩٥٫٠٠") == "2495.00"
    assert lc.normalize_arabic("price 45.50") == "price 45.50"


def test_arabic_price_parses():
    assert rp.extract_price("قميص ٢٤٩٥٫٠٠") == 2495.0
    assert rp.extract_price("تي شيرت ١٥٩٫٩٩") == 159.99


def test_arabic_footer_is_not_a_product(monkeypatch):
    monkeypatch.setattr(lc, "DEFAULT_LANG", "ar")
    for label in ("المجموع الفرعي", "اجمالي الفاتورة", "الضريبة", "المدفوع"):
        assert rp.is_summary_row(f"{label} 200.00", 200.0), label


def test_arabic_metadata_is_not_a_product(monkeypatch):
    monkeypatch.setattr(lc, "DEFAULT_LANG", "ar")
    for text in ("التاريخ 01/02/2026", "الكاشير احمد", "رقم الفاتورة 12345",
                 "الفرع 12"):
        assert rp.is_metadata_row(text), text


def test_arabic_receipt_passes_the_gate(monkeypatch):
    monkeypatch.setattr(lc, "DEFAULT_LANG", "ar")
    ocr = [{"text": t, "confidence": 0.9,
            "bbox": [[0, i * 30], [200, i * 30], [200, i * 30 + 20], [0, i * 30 + 20]]}
           for i, t in enumerate(["قميص ٢٤٩٥٫٠٠", "بنطلون ٥٩٩٫٠٠",
                                   "المجموع الفرعي ٣٠٩٤٫٠٠",
                                   "الضريبة ١٥٤٫٧٠",
                                   "المدفوع ٣٢٤٨٫٧٠"])]
    assert v.validate(ocr).is_receipt


def test_english_still_works_in_arabic_mode(monkeypatch):
    """Egyptian receipts mix Latin brand names with Arabic labels."""
    monkeypatch.setattr(lc, "DEFAULT_LANG", "ar")
    assert rp.extract_price("ZARA SHIRT 59.99") == 59.99
    assert rp.is_summary_row("TOTAL 100.00", 100.0)


def test_language_switching():
    assert lc.ocr_languages("en") == ["en"]
    assert lc.ocr_languages("ar") == ["ar", "en"]
    assert lc.is_rtl("ar") and not lc.is_rtl("en")
    assert lc.normalize("AR-EG") == "ar"
    assert len(lc.summary_keywords("ar")) > len(lc.summary_keywords("en"))
    # English keywords are always available, even in Arabic mode.
    assert "subtotal" in lc.summary_keywords("ar")
    assert "المجموع" in lc.summary_keywords("ar")