"""
Decides which business data a message needs, and fetches it.

Two separate decisions, deliberately in this order:

    1. INTENT  - does this message need stock or demand data at all?
    2. FETCH   - call only the services that intent asked for.

The split matters for latency and honesty. Calling both services on every
turn would double the wait on every message to answer a question about colour.
And calling them when the user just said "hi" would burn two HTTP round trips
to learn nothing.

Every fetch is best-effort. When a service is down the turn continues and the
model is told what it could not verify, so it says "I could not check the
stock right now" instead of inventing a number. Inventing stock levels is the
single worst failure this system could have.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.services.backends import (
    BackendResult,
    forecast_client,
    stock_client,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# intent detection
# --------------------------------------------------------------------------

# Arabic and English cues for "what do we have / is there stock", kept as
# word-level patterns so "in stock" does not match inside a longer word.
_STOCK_CUES = re.compile(
    r"(متاح|متوفر|موجود|في المخزن|في المخزن؟|عندك|عندنا|كام|كام في|كمان في)"
    r"|\b(in stock|available|availability|do you have|how many)\b",
    re.IGNORECASE,
)

# Cues for demand / forecasting questions.
_DEMAND_CUES = re.compile(
    r"(طلب|بيتباع|بيع|مبيعات| أتوقع|يتوقع|هيباع|ينزل)"
    r"|\b(demand|forecast|predict|likely to sell|sales)\b",
    re.IGNORECASE,
)

# Explicit product words, used to search the warehouse by name.
_PRODUCT_WORDS = re.compile(
    r"(جاكيت|بلوز|قميص|فسطلان|بنطلون|تيشيرت|فستان|áo|coat|jacket|shirt|dress|"
    r"trousers|pants|sweater|jeans|hoodie|t-?shirt|skirt|vest)",
    re.IGNORECASE,
)


@dataclass
class Intent:
    """What the turn is about, before any network call."""

    needs_stock: bool = False
    needs_demand: bool = False
    product_terms: List[str] = field(default_factory=list)
    is_smalltalk: bool = False

    def wants_anything(self) -> bool:
        return self.needs_stock or self.needs_demand


def detect_intent(message: str) -> Intent:
    """
    Classify the message from its text alone.

    Rule-based rather than model-based on purpose: this runs before the LLM, it
    has to be fast, and a wrong guess here only costs one wasted HTTP call,
    never a wrong answer. The model never sees this decision.
    """
    text = (message or "").strip()

    # Very short greetings carry no business intent; skipping the calls keeps
    # "hi" answering instantly.
    smalltalk = bool(re.fullmatch(
        r"(hi|hello|hey|سلام|اهلا|أهلا|ازيك|إزيك|صباح|مساء|good (morning|evening))[!?. ]*",
        text, re.IGNORECASE))

    if smalltalk:
        return Intent(is_smalltalk=True)

    terms = [m.group(0).strip() for m in _PRODUCT_WORDS.finditer(text)]

    return Intent(
        needs_stock=bool(_STOCK_CUES.search(text)) or (bool(terms) and len(text) < 60),
        needs_demand=bool(_DEMAND_CUES.search(text)),
        product_terms=terms,
    )


# --------------------------------------------------------------------------
# context building
# --------------------------------------------------------------------------

def _format_stock(products: List[dict]) -> str:
    lines = []
    for p in products[:6]:
        name = p.get("name") or "?"
        quantity = p.get("quantity")
        price = p.get("price")
        bits = [f"- {name}"]
        if quantity is not None:
            bits.append(f"in stock: {quantity}")
        if price is not None:
            try:
                bits.append(f"price: {float(price):.2f} EGP")
            except (TypeError, ValueError):
                pass
        lines.append(" ".join(bits))
    return "\n".join(lines)


def _format_demand(payload: dict) -> str:
    items = (payload or {}).get("items", [])
    week = (payload or {}).get("forecast_week", "next week")
    lines = [f"Week of {week}:"]
    for item in items[:6]:
        name = item.get("name") or f"article {item.get('article_id')}"
        demand = item.get("predicted_demand")
        if demand is None:
            continue
        lines.append(f"- {name}: predicted demand {float(demand):.2f}")
    return "\n".join(lines)


def collect_business_context(message: str) -> Tuple[str, Dict[str, Any]]:
    """
    Return (context_block, diagnostics).

    The context block is appended to the system instruction, so it must be
    short and factual. When a service is unavailable a line states that
    explicitly, which is what keeps the model honest instead of confident.
    """
    intent = detect_intent(message)
    diagnostics: Dict[str, Any] = {"intent": {
        "needs_stock": intent.needs_stock,
        "needs_demand": intent.needs_demand,
        "terms": intent.product_terms,
    }}

    if not intent.wants_anything():
        diagnostics["services"] = {}
        return "", diagnostics

    blocks: List[str] = []
    service_status: Dict[str, str] = {}

    # ---- stock ----
    if intent.needs_stock:
        term = " ".join(intent.product_terms) if intent.product_terms else ""
        result: BackendResult = (
            stock_client.search(term) if term else stock_client.stats()
        )
        service_status["stock"] = result.status

        if result.ok:
            if result.status == "empty" or not result.data:
                blocks.append("[STOCK] No matching item is currently in the warehouse.")
            elif intent.product_terms:
                text = _format_stock(result.data)
                if text:
                    blocks.append(f"[STOCK] Current warehouse records:\n{text}")
            else:
                stats = result.data or {}
                blocks.append(
                    "[STOCK] Warehouse totals: "
                    f"{stats.get('product_count', '?')} products, "
                    f"{stats.get('total_quantity', '?')} units, "
                    f"{stats.get('total_value', 0):.2f} EGP value."
                    if isinstance(stats, dict) and "product_count" in stats
                    else "[STOCK] Warehouse records available."
                )
        else:
            blocks.append(
                "[STOCK] The stock service is unavailable right now, so current "
                "stock levels are unknown. Do not state a quantity."
            )

    # ---- demand ----
    if intent.needs_demand:
        result = forecast_client.top_demand(limit=5)
        service_status["forecasting"] = result.status
        if result.ok and result.data:
            text = _format_demand(result.data)
            if text:
                blocks.append(f"[FORECAST] {text}")
        else:
            blocks.append(
                "[FORECAST] The forecasting service is unavailable, so demand "
                "predictions are unknown. Do not estimate."
            )

    diagnostics["services"] = service_status
    return "\n\n".join(blocks), diagnostics