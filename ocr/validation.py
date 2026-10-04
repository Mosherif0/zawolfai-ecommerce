"""
Receipt validation gate.

Running the parser over a photo that is not a receipt produces confident
nonsense: a playlist screenshot yielded products like
"ARCTIC MONKEYS 05 OLIVIA RODRIGO 8.00". Nothing downstream can tell the
difference once rows have been parsed, so the decision has to happen here,
before a single row is produced.

How the score works
-------------------
Signal keywords are weighted (a "subtotal" is worth far more than "thanks")
and the evidence is spread across three independent dimensions:

  * STRUCTURE  - receipt furniture: totals, payment, merchant identity
  * NUMBERS    - a plausible column of money values
  * SHAPE      - tall, narrow, low-colour-variance page (paper on a desk)

A photo of a receipt can score badly on shape (crooked, on a patterned
table) and still be accepted; a screenshot can score well on numbers. Requiring
structure plus ONE other dimension keeps both false positives and false
negatives down, which a single threshold on one signal cannot do.

Arabic receipts are matched with the same weights via language_config.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import language_config as lang_config

try:
    import cv2
    import numpy as np
except ImportError:  # pragma: no cover - optional for pure-OCR tests
    cv2 = None
    np = None


ACCEPT_THRESHOLD = 0.55
STRUCTURE_WEIGHT = 0.55   # must be present on its own
SUPPORT_WEIGHT = 0.45     # split between numbers and shape


@dataclass
class ValidationResult:
    """Why an image was accepted or rejected - never a bare boolean."""

    is_receipt: bool
    score: float
    structure_score: float = 0.0
    numbers_score: float = 0.0
    shape_score: float = 0.0
    matched_signals: List[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> Dict:
        return {
            "is_receipt": self.is_receipt,
            "score": round(self.score, 3),
            "structure_score": round(self.structure_score, 3),
            "numbers_score": round(self.numbers_score, 3),
            "shape_score": round(self.shape_score, 3),
            "matched_signals": self.matched_signals,
            "reason": self.reason,
        }


# Money-looking token: 12.99 / 1,299.00 / 45 / ١٢٣ (after normalisation)
_MONEY_RE = re.compile(r"\d{1,3}(?:[,]\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?")


def _text_of(ocr_data: Sequence[Dict]) -> str:
    return " ".join(item.get("text", "") for item in ocr_data)



def _close(a: str, b: str, tolerance: int = 1) -> bool:
    """True when two short labels differ by at most `tolerance` edits."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > tolerance:
        return False
    return _levenshtein(a, b) <= tolerance


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1,
                               current[j - 1] + 1,
                               previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]



def score_structure(text: str, lang: Optional[str] = None):
    """
    Receipt furniture, weighted.

    Weak signals ("thanks", "receipt") are capped so that a single weak hit
    can never push a non-receipt over the line on its own.
    """
    lowered = text.lower()
    signals = lang_config.receipt_signals(lang)

    # OCR corrupts these labels constantly on thermal paper. A real Lowe's
    # receipt read "slbtotal" instead of "subtotal" and was therefore scored
    # zero structure and rejected. Whole-word matching with a one-edit
    # tolerance recovers those without loosening substring matching (which
    # would let "total" fire inside "subtotal").
    words = set(re.findall(r"[a-z]{4,}", lowered))

    total = 0.0
    matched: List[str] = []
    weak_total = 0.0
    strong_count = 0

    for needle, weight in signals:
        if " " in needle:
            found = needle in lowered
        else:
            found = needle in lowered or any(
                _close(needle, word) for word in words
            )
        if found:
            matched.append(needle)
            if needle.strip() in lang_config.WEAK_SIGNALS:
                weak_total += weight
            else:
                total += weight
                strong_count += 1

    # Weak evidence contributes at most a third of the structure weight.
    total += min(weak_total, 1.0)

    # COUNTRY, NOT A SINGLE KEYWORD. A playlist screenshot that happens to
    # print "total" and "receipt" scored 0.76 and was accepted; requiring at
    # least two independent strong signals is what separates a real till
    # receipt from any text-heavy page that mentions money.
    if strong_count < 2:
        return 0.0, matched

    # Saturating curve: five strong signals should be enough, and the tenth
    # should not keep adding, so a dense document cannot dominate.
    normalised = total / (total + 3.0)
    return min(1.0, normalised), matched


def score_numbers(text: str):
    """
    A receipt shows a column of prices. Count them and check they vary -
    a page of identical numbers is usually not a purchase list.
    """
    values = []
    for token in _MONEY_RE.findall(text):
        cleaned = token.replace(",", "")
        try:
            values.append(float(cleaned))
        except ValueError:
            continue

    # Tiny amounts and bare integers are far more likely to be IDs.
    prices = [v for v in values if 0.5 <= v <= 100000]

    if len(prices) < 3:
        return 0.0

    unique = len({round(v, 2) for v in prices})
    variety = unique / len(prices)

    count_score = min(1.0, len(prices) / 10.0)
    # Some variety is expected; zero variety means one repeated number.
    variety_score = min(1.0, variety * 2.0)

    return min(1.0, 0.65 * count_score + 0.35 * variety_score)


def score_shape(image_path):
    """
    Receipts are tall and narrow, mostly light with a white page. This is the
    weakest signal on purpose - it only breaks ties.
    """
    if cv2 is None or np is None:
        return 0.0

    try:
        image = cv2.imread(str(image_path))
        if image is None:
            return 0.0
    except Exception:
        return 0.0

    height, width = image.shape[:2]
    if height == 0 or width == 0:
        return 0.0

    aspect = height / width

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    brightness = float(gray.mean()) / 255.0
    contrast = float(gray.std()) / 255.0

    score = 0.0
    # Tall aspect ratio (a receipt is usually >= 1.3, often 2+).
    if aspect >= 1.8:
        score += 0.5
    elif aspect >= 1.3:
        score += 0.3

    # Bright page with printed (not photographic) contrast.
    if 0.45 <= brightness <= 0.98:
        score += 0.3
    if contrast >= 0.05:
        score += 0.2

    return min(1.0, score)


def validate(
    ocr_data: Sequence[Dict],
    image_path=None,
    lang: Optional[str] = None,
    threshold: float = ACCEPT_THRESHOLD,
) -> ValidationResult:
    """
    Decide whether the OCR output belongs to a receipt.

    Structure is mandatory: without it nothing is accepted, because a photo of
    a text-heavy page can look numeric and tall.
    """
    text = _text_of(ocr_data)
    if lang_config.normalize(lang or lang_config.DEFAULT_LANG) == "ar":
        text = lang_config.normalize_arabic(text)

    if not text.strip():
        return ValidationResult(False, 0.0, reason="no text detected")

    structure, matched = score_structure(text, lang)
    numbers = score_numbers(text)
    shape = score_shape(image_path) if image_path else 0.0

    support = max(numbers, shape)
    score = STRUCTURE_WEIGHT * structure + SUPPORT_WEIGHT * support

    if structure < 0.30:
        reason = (f"insufficient receipt structure "
                  f"(score {structure:.2f}; matched: {', '.join(matched[:5]) or 'none'})")
        return ValidationResult(False, score, structure, numbers, shape,
                                matched, reason)

    if score >= threshold:
        return ValidationResult(True, score, structure, numbers, shape, matched,
                                "accepted")

    reason = (f"score {score:.2f} below threshold {threshold:.2f} "
              f"(structure {structure:.2f}, numbers {numbers:.2f}, shape {shape:.2f})")
    return ValidationResult(False, score, structure, numbers, shape, matched, reason)