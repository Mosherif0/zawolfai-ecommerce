"""
Language configuration.

English is the default and the fully-supported path. Arabic is opt-in: the
same pipeline, the same parser, but Arabic-aware vocabulary.

Why a single switch rather than two code paths
-----------------------------------------------
The parser already matches keywords case-insensitively on the raw OCR text.
Adding Arabic words to the same tables makes bilingual support a data change
instead of a branch, so a document containing both (common in Egypt:
English brand names, Arabic labels) is handled by one pass.

`active` is derived once at import; nothing else in the codebase needs to know
which language is in play.
"""

from __future__ import annotations

import os
import unicodedata
from typing import Dict, List, Tuple

from dotenv import load_dotenv

load_dotenv()

SUPPORTED = ("en", "ar")
DEFAULT_LANG = os.getenv("OCR_LANGUAGE", "en").strip().lower() or "en"


def normalize(lang: str) -> str:
    return lang.strip().lower()[:2]


def active() -> str:
    return DEFAULT_LANG if DEFAULT_LANG in SUPPORTED else "en"


def is_rtl(lang: str | None = None) -> bool:
    return normalize(lang or DEFAULT_LANG) == "ar"


def ocr_languages(lang: str | None = None) -> List[str]:
    """
    Model languages for EasyOCR. Always load both Arabic and English so any
    receipt (Arabic, English, or Bilingual) is recognized seamlessly.
    """
    return ["ar", "en"]


# --------------------------------------------------------------------------
# Arabic normalisation
# --------------------------------------------------------------------------

# Arabic receipts print prices with the Eastern Arabic-Indic digits and
# sometimes the Arabic decimal separator. Normalising them means the parser's
# numeric rules work unchanged.
_DIGIT_MAP = {chr(0x0660 + i): str(i) for i in range(10)}
_DIGIT_MAP.update({chr(0x06F0 + i): str(i) for i in range(10)})

_ARABIC_MARKS = {
    "٫": ".",  # ARABIC DECIMAL SEPARATOR
    "٬": ",",  # ARABIC THOUSANDS SEPARATOR
    "٭": "*",
    "×": "x",
    "ٙ": "'",
}


def normalize_arabic(text: str) -> str:
    """
    Fold Arabic-Indic digits, decimal separators and tatweel into ASCII.

    Without this, "٢٤٩٥٫٠٠" fails every price regex in the parser. Doing it at
    the entry point means no parsing rule has to know about Arabic.
    """
    if not text:
        return text
    out = []
    for ch in text:
        if ch in _DIGIT_MAP:
            out.append(_DIGIT_MAP[ch])
        elif ch in _ARABIC_MARKS:
            out.append(_ARABIC_MARKS[ch])
        elif ch == "ـ":  # TATWEEL, purely typographic
            continue
        elif unicodedata.combining(ch):
            continue
        else:
            out.append(ch)
    return "".join(out)


# --------------------------------------------------------------------------
# Vocabulary (English is the base; Arabic entries are additive)
# --------------------------------------------------------------------------

#: Footer / summary labels. Matched against the first word (edit-distance
#: tolerant) and against the whole row when it carries a price.
SUMMARY_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "en": (
        "subtotal", "sub total", "sub-total", "total", "totals", "grand total",
        "net total", "total due", "amount due", "balance due",
        "tax", "vat", "gst", "sales tax", "taxable", "duty", "duty paid",
        "payment", "paid", "cash", "change", "tender", "tendered",
        "card", "visa", "mastercard", "amex", "credit", "debit",
        "approval", "approved", "auth", "authorization", "transaction",
        "ref no", "reference", "receipt no", "invoice no", "invoice",
        "terminal", "cashier", "operator", "merchant", "store",
        "account", "acct", "amount", "amount paid", "amount tendered",
        "tota1", "subtota",
        "return", "returns", "policy", "refund", "exchange",
        "warranty", "guarantee", "points", "reward", "savings",
        "discount", "coupon", "promo", "shipping", "delivery",
        "rounding", "tip", "gratuity", "item count", "items",
        "thank you", "www", "http", "customer", "copy", "survey",
    ),
    "ar": (
        "المجموع", "المجموع الفرعي", "اجمالي", "اجمالي الفاتورة", "الإجمالي", "الصافي",
        "الضريبة", "ضريبة القيمة المضافة", "القيمة المضافة",
        "المدفوع", "دفع", "نقدا", "نقد", "الباقي", "التغيير", "المتبقي",
        "فيزا", "ماستركارد", "بطاقة", "ائتمان",
        "موافق", "معتمد", "المعاملة", "رقم الفاتورة", "فاتورة", "فاتورة بيع",
        "رقم ايصال", "الفرع", "الكاشير", "الموظف", "رقم العملية", "رقم الوردية",
        "الاسترجاع", "استبدال", "سياسة", "ضمان",
        "شكرا", "شكرا لحسن زيارتكم", "اتصل", "استفسار",
        "خصم", "كوبون", "شحن", "توصيل", "النقاط",
        "عدد الاغراض", "الاغراض", "عدد الاصناف", "عدد الاصناف المباعة",
    ),
}

#: Store / transaction metadata that must never become a product.
METADATA_PATTERNS: Dict[str, Tuple[str, ...]] = {
    "en": (
        r"\bdate\b", r"\btime\b", r"\bstore\b", r"\bregister\b",
        r"\bmember\s+since\b", r"\breceipt\b", r"\binvoice\b",
        r"\btransaction\b", r"\bterminal\b", r"\boperator\b",
        r"\bthank\s+you\b", r"\bwww\.", r"\bhttps?://",
        r"\bcashier\b", r"\bcard\b", r"\bvisa\b", r"\bchange\b",
    ),
    "ar": (
        r"التاريخ", r"الوقت", r"الفرع", r"الكاشير", r"المتجر",
        r"الفاتورة", r"ايصال", r"رقم", r"شكرا", r"اتصل",
        r"تليفون", r"رقم الهاتف", r"الرمز", r"رقم العملية", r"رقم الوردية", r"العميل",
    ),
}

#: Signals that an image really is a receipt (used by the reject gate).
RECEIPT_SIGNALS: Dict[str, Tuple[Tuple[str, float], ...]] = {
    # (substring, weight)
    "en": (
        ("subtotal", 3.0), ("sub total", 3.0), ("total due", 3.0), ("total", 2.5),
        ("grand total", 3.0), ("amount due", 3.0), ("balance due", 2.5), ("amount", 2.0),
        ("vat", 3.0), ("tax", 2.0), ("sales tax", 3.0), ("egp", 2.5), ("le", 2.0), ("l.e.", 2.0),
        ("payment", 2.0), ("cash", 1.5), ("change", 1.5), ("tendered", 2.0), ("price", 2.0),
        ("visa", 2.0), ("mastercard", 2.0), ("amex", 2.0), ("qty", 2.0), ("quantity", 2.0),
        ("approved", 2.0), ("authorization", 2.0), ("auth code", 2.5), ("item", 1.5),
        ("receipt no", 2.5), ("invoice no", 2.5), ("invoice", 2.0), ("receipt", 2.0),
        ("cashier", 2.5), ("terminal", 2.0), ("register", 1.0), ("bill", 2.0),
        ("thank you", 1.5), ("www.", 1.0), ("http", 1.0),
        ("item count", 2.0), ("order number", 2.0), ("order", 1.5), ("unit", 1.5),
    ),
    "ar": (
        ("المجموع الفرعي", 3.0), ("المجموع", 2.5), ("اجمالي", 2.5), ("إجمالي", 2.5),
        ("الضريبة", 3.0), ("القيمة المضافة", 3.0), ("ج.م", 3.0), ("جنيه", 2.5),
        ("المدفوع", 2.0), ("الباقي", 2.0), ("التغيير", 1.5), ("سعر", 2.0), ("السعر", 2.0),
        ("فيزا", 2.0), ("ماستركارد", 2.0), ("بطاقة", 1.5), ("الكمية", 2.0), ("كمية", 2.0),
        ("موافق", 2.0), ("معتمد", 1.5), ("صنف", 2.0), ("منتج", 1.5), ("مشتريات", 2.0),
        ("رقم الفاتورة", 2.5), ("فاتورة", 2.0), ("ايصال", 2.0), ("إيصال", 2.0), ("فاتورة بيع", 3.0),
        ("الكاشير", 2.5), ("الفرع", 2.0), ("تاريخ", 1.5), ("مبلغ", 2.0), ("المبلغ", 2.0),
        ("شكرا", 1.5), ("عدد الاغراض", 2.0), ("حساب", 1.5), ("طلب", 1.5), ("كاش", 2.0),
        ("الصافي", 3.0), ("المتبقي", 2.0), ("رقم العملية", 2.5), ("رقم الوردية", 2.0), ("الوحدة", 1.5),
        ("الاصناف", 2.0), ("المباعة", 1.5), ("تيك اواي", 1.5), ("unit", 1.5),
    ),
}

#: Words that appear on non-receipt images but mention receipts. A single one
#: of these is NOT evidence — a playlist screenshot says "receipt" once.
#: Signals that a NON-receipt can also contain. A playlist screenshot printed
#: "receipt", "thank you", "item count" and even "total" - every one of those
#: is therefore worthless on its own and only counts once other evidence
#: supports it.
WEAK_SIGNALS = frozenset({
    "receipt", "thank you", "item count", "www.", "http",
    "store", "total", "invoice", "copy", "survey", "customer",
    "points", "reward", "items", "promo", "tip",
})


def summary_keywords(lang: str | None = None) -> Tuple[str, ...]:
    """Summary labels for a language, Arabic always additive."""
    return tuple(set(SUMMARY_KEYWORDS["en"] + SUMMARY_KEYWORDS["ar"]))


def metadata_patterns(lang: str | None = None) -> Tuple[str, ...]:
    return tuple(set(METADATA_PATTERNS["en"] + METADATA_PATTERNS["ar"]))


def receipt_signals(lang: str | None = None) -> Tuple[Tuple[str, float], ...]:
    return tuple(RECEIPT_SIGNALS["en"] + RECEIPT_SIGNALS["ar"])