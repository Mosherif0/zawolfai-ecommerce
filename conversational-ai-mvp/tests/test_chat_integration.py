"""
Chat-layer integration tests.

These exercise the full turn: retrieval -> grounding -> generation -> cards.
Gemini is mocked so the suite stays offline and deterministic; the retrieval
and grounding assertions are therefore testing OUR code, not the model's mood.

Run:  pytest tests/test_chat_integration.py -v
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.catalog_service import get_catalog_service  # noqa: E402
from app.services.conversation import conversation_service  # noqa: E402
from app.services.gemini import GeminiUnavailableError, gemini_service  # noqa: E402


@pytest.fixture(autouse=True)
def clean_state():
    conversation_service.clear_all()
    yield
    conversation_service.clear_all()


@pytest.fixture
def scripted_reply():
    """Replace generation with a fixed, inspectable reply."""
    with patch.object(gemini_service, "_generate_reply",
                      return_value="تمام، دي اختياراتك.") as m:
        yield m


# --------------------------------------------------------------------------
# 1) The turn returns real catalog products, not the old mock list
# --------------------------------------------------------------------------

def test_chat_returns_real_catalog_cards(scripted_reply):
    cid, reply, products = gemini_service.chat(message="عاوز جاكيت")
    assert products, "no product cards returned for an explicit request"
    svc = get_catalog_service()
    for card in products:
        row = svc.get(card.product_id)
        assert row is not None, f"{card.product_id} is not a real catalog row"
        assert card.price == float(row.egp_price)
        assert card.image_url == row.image_url


def test_prompt_contains_the_catalog_prices(scripted_reply):
    """The model must SEE the prices, otherwise it will invent them."""
    _cid, _reply, products = gemini_service.chat(message="فستان")
    instruction = scripted_reply.call_args[0][1].system_instruction
    assert products, "no cards returned"
    for card in products:
        assert f"{int(card.price)} جنيه" in instruction, \
            f"price {card.price} missing from the system instruction"


def test_every_shown_product_is_in_the_prompt(scripted_reply):
    """
    Grounding invariant: the UI can never show a card the model did not see.
    """
    _cid, _reply, products = gemini_service.chat(message="تحت 500")
    config = scripted_reply.call_args[0][1]
    instruction = config.system_instruction
    for card in products:
        assert card.name in instruction, f"{card.name} was shown but never grounded"


def test_catalog_block_has_guardrails(scripted_reply):
    gemini_service.chat(message="عاوز جاكيت")
    instruction = scripted_reply.call_args[0][1].system_instruction
    assert "REAL CATALOG" in instruction
    assert "ممنوع تخترع" in instruction


# --------------------------------------------------------------------------
# 2) Chit-chat must not return cards
# --------------------------------------------------------------------------

@pytest.mark.parametrize("message", [
    "اذيك يا باشا", "صباح الخير", "ماشي", "تمام", "شكرا",
])
def test_greetings_return_text_only(message, scripted_reply):
    _cid, reply, products = gemini_service.chat(message=message)
    assert products == [], f"{message} should not trigger product cards"
    assert reply


# --------------------------------------------------------------------------
# 3) Multi-turn memory: follow-ups resolve against shown cards
# --------------------------------------------------------------------------

def test_followup_reuses_shown_products(scripted_reply):
    cid, _r1, first = gemini_service.chat(message="عاوز جاكيت")
    assert first

    # "the second one" has no lexical overlap with the catalog
    _cid2, _r2, second = gemini_service.chat(message="التاني بكام؟", conversation_id=cid)

    shown = {c.product_id for c in first}
    assert {c.product_id for c in second} & shown, \
        "follow-up returned nothing related to what was on screen"


def test_explicit_request_wins_over_previous_cards(scripted_reply):
    """Regression: previous cards used to hijack a brand-new request."""
    cid, _r, jackets = gemini_service.chat(message="عاوز جاكيت")
    _cid2, _r2, dresses = gemini_service.chat(message="عاوز فستان", conversation_id=cid)
    jacket_ids = {c.product_id for c in jackets}
    assert not (jacket_ids & {c.product_id for c in dresses}), \
        "dress request was polluted with jackets"


# --------------------------------------------------------------------------
# 4) Failure handling: degrade honestly, never fabricate
# --------------------------------------------------------------------------

def test_generation_failure_returns_natural_retry():
    with patch.object(gemini_service, "_generate_reply",
                      side_effect=GeminiUnavailableError("simulated outage")):
        _cid, reply, products = gemini_service.chat(message="عاوز جاكيت")
    assert "مشكلة" in reply or "جرب" in reply
    assert products == [], "must not show product cards when generation failed"


def test_no_mock_products_ever_appear(scripted_reply):
    """Regression guard for the old fake catalog leaking into replies."""
    forbidden = ["Classic Product", "Premium Product", "Bundle Pack",
                 "Basic T-Shirt", "Socks Pack", "Premium Hoodie", "Everyday Cap"]
    for message in ("عاوز جاكيت", "فستان", "تحت 500", "بنطلون"):
        _cid, reply, products = gemini_service.chat(message=message)
        for name in forbidden:
            assert name not in reply, f"{name} leaked into the reply"
        svc = get_catalog_service()
        for card in products:
            assert card.product_id in {p.product_id for p in svc.all_products()}


def test_unavailable_client_raises_cleanly(scripted_reply):
    with patch.object(gemini_service, "client", None):
        _cid, reply, products = gemini_service.chat(message="اذيك")
    assert isinstance(reply, str) and reply

# --------------------------------------------------------------------------
# 5) Card quality: reasons must differentiate, not repeat
# --------------------------------------------------------------------------

def test_reasons_differ_across_cards(scripted_reply):
    """
    A reason repeated on every card ("من فئة جاكيت" x4) is wasted space;
    it must carry information the user does not already have.
    """
    _cid, _reply, products = gemini_service.chat(message="عاوز جاكيت")
    reasons = [c.reason for c in products]
    assert all(reasons), "every card should carry a reason"
    assert len(set(reasons)) > 1, f"all reasons identical: {reasons}"


def test_reason_mentions_the_price(scripted_reply):
    """When the user filtered by category, the reason should add the price."""
    _cid, _reply, products = gemini_service.chat(message="عاوز جاكيت")
    for card in products:
        assert f"{int(card.price)} جنيه" in card.reason, \
            f"reason {card.reason!r} omits the price {card.price}"


def test_cards_are_not_empty_strings(scripted_reply):
    _cid, reply, products = gemini_service.chat(message="فستان")
    assert reply.strip()
    for card in products:
        assert card.name.strip()
        assert card.image_url
