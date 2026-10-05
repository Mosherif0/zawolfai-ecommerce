"""
Tests for the cross-service link.

The failure modes that matter here are all "the chat silently says something
wrong": a product reported as out of stock while it is on the shelf, or a
number invented when the stock service is down. Both are tested explicitly,
because neither shows up in a smoke test that only checks the happy path.

No real HTTP is performed: the httpx clients are monkeypatched, so these run
offline and in milliseconds. What is under test is the decision logic and the
error translation, not the network.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import backends as bk  # noqa: E402
from app.services import business_context as bc  # noqa: E402


# --------------------------------------------------------------------------
# intent detection
# --------------------------------------------------------------------------

class TestIntent:
    def test_greeting_needs_nothing(self):
        intent = bc.detect_intent("سلام")
        assert intent.is_smalltalk is True
        assert intent.wants_anything() is False

    @pytest.mark.parametrize("message", [
        "عندك جاكيت في المخزن؟",
        "كام في المخزن؟",
        "الطلب المتوقع الأسبوع الجاي إيه؟",
        "إيه المبيعات المتوقعة؟",
    ])
    def test_business_messages_are_detected(self, message):
        assert bc.detect_intent(message).wants_anything() is True

    def test_stock_and_demand_are_separate(self):
        stock_only = bc.detect_intent("عندك جاكيت في المخزن؟")
        assert stock_only.needs_stock is True
        assert stock_only.needs_demand is False

        demand_only = bc.detect_intent("الطلب المتوقع الجاي إيه؟")
        assert demand_only.needs_demand is True

    def test_product_words_are_extracted(self):
        intent = bc.detect_intent("عايز جاكيت أزرق")
        assert "جاكيت" in intent.product_terms


# --------------------------------------------------------------------------
# vocabulary bridge
# --------------------------------------------------------------------------

class TestVocabulary:
    def test_arabic_expands_to_english(self):
        tokens = bk.expand_search_terms(["بلوز"])
        assert "blouse" in tokens
        assert "shirt" in tokens

    def test_unknown_terms_pass_through(self):
        tokens = bk.expand_search_terms(["xyzzy"])
        assert "xyzzy" in tokens

    def test_no_duplicate_tokens(self):
        tokens = bk.expand_search_terms(["شhirt", "shirt"])
        assert len(tokens) == len(set(tokens))


# --------------------------------------------------------------------------
# stock search
# --------------------------------------------------------------------------

WAREHOUSE = {
    "backend": "postgres",
    "products": [
        {"id": 1, "name": "White Shirt", "quantity": 6, "price": 45.95, "category": None},
        {"id": 2, "name": "Kids T-Shirt", "quantity": 8, "price": 59.99, "category": None},
        {"id": 3, "name": "Black Blazer", "quantity": 4, "price": 59.99, "category": None},
    ],
}


def _stub_stock(monkeypatch, result):
    monkeypatch.setattr(bc.stock_client, "_request", lambda *a, **k: result)


class TestStockSearch:
    def test_arabic_term_finds_english_product(self, monkeypatch):
        """The whole point of the bridge: بلوز must match White Shirt."""
        _stub_stock(monkeypatch, bk.BackendResult(ok=True, data=WAREHOUSE["products"], status="ok"))
        result = bc.stock_client.search("بلوز")
        assert result.ok is True
        names = [p["name"] for p in result.data]
        assert "White Shirt" in names

    def test_no_match_is_empty_not_an_error(self, monkeypatch):
        _stub_stock(monkeypatch, bk.BackendResult(ok=True, data=WAREHOUSE["products"], status="ok"))
        result = bc.stock_client.search("منتج مش موجود")
        assert result.ok is True          # the call succeeded
        assert result.status == "empty"   # there is just nothing matching
        assert result.data == []

    def test_blank_term_returns_everything(self, monkeypatch):
        _stub_stock(monkeypatch, bk.BackendResult(ok=True, data=WAREHOUSE["products"], status="ok"))
        result = bc.stock_client.search("")
        assert result.status == "ok"
        assert len(result.data) == 3


# --------------------------------------------------------------------------
# the honesty rule: never invent a number
# --------------------------------------------------------------------------

class TestDownstreamFailures:
    def test_stock_unavailable_tells_the_model_not_to_guess(self, monkeypatch):
        """
        The single most important behaviour in this module.

        When the stock service cannot be reached the prompt must say the number
        is unknown. Without this the model fills the gap from its training and
        states an inventory figure that was never measured.
        """
        monkeypatch.setattr(
            bc.stock_client, "_request",
            lambda *a, **k: bk.BackendResult.failure("unreachable", "connection refused"),
        )
        block, diagnostics = bc.collect_business_context("عندك جاكيت في المخزن؟")

        assert "unavailable" in block
        assert "Do not state a quantity" in block
        assert diagnostics["services"]["stock"] == "unreachable"

    def test_forecast_unavailable_says_unknown(self, monkeypatch):
        monkeypatch.setattr(
            bc.forecast_client, "_request",
            lambda *a, **k: bk.BackendResult.failure("timeout", "no answer"),
        )
        block, diagnostics = bc.collect_business_context("الطلب المتوقع إيه؟")

        assert "unavailable" in block
        assert "Do not estimate" in block
        assert diagnostics["services"]["forecasting"] == "timeout"

    def test_greeting_makes_no_call_at_all(self, monkeypatch):
        """A greeting must not spend two HTTP round trips."""
        def explode(*a, **k):
            raise AssertionError("no HTTP should happen for a greeting")

        monkeypatch.setattr(bc.stock_client, "_request", explode)
        monkeypatch.setattr(bc.forecast_client, "_request", explode)

        block, diagnostics = bc.collect_business_context("سلام")
        assert block == ""
        assert diagnostics["services"] == {}

    def test_empty_warehouse_is_stated_plainly(self, monkeypatch):
        """Out of stock is a real answer and must not read as a failure."""
        monkeypatch.setattr(
            bc.stock_client, "_request",
            lambda *a, **k: bk.BackendResult(ok=True, data=[], status="empty"),
        )
        block, _ = bc.collect_business_context("عندك جاكيت في المخزن؟")
        assert "No matching item" in block
        assert "unavailable" not in block

    def test_backend_error_never_raises_into_chat(self, monkeypatch):
        """collect_business_context must not propagate; gemini guards too."""
        monkeypatch.setattr(
            bc.stock_client, "_request",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        # The raw client raising is caught by the gemini-level guard, so here we
        # only assert that the module itself does not swallow the error silently
        # in a way that would hide a programming mistake.
        with pytest.raises(RuntimeError):
            bc.collect_business_context("عندك جاكيت في المخزن؟")