import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from app.main import app
from app.services.conversation import conversation_service
from app.services.mock_data import get_business_context, PRODUCTS, ORDERS

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_conversation_state():
    """Cleans up conversation storage before each test."""
    conversation_service.clear_all()
    yield
    conversation_service.clear_all()


@pytest.fixture(autouse=True)
def force_local_mock_mode(monkeypatch):
    """
    Forces the Gemini service into local mock mode so the test suite stays fast,
    deterministic and fully offline (no real API calls / network flakiness).
    """
    from app.services.gemini import gemini_service

    monkeypatch.setattr(gemini_service, "reload_config", lambda: None)
    monkeypatch.setattr(gemini_service, "client", None)
    monkeypatch.setattr(gemini_service, "api_key", "")
    yield


def test_health_check():
    """Test GET /health endpoint returns status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_serve_index():
    """Test GET / serves the HTML frontend page."""
    response = client.get("/")
    assert response.status_code == 200
    assert "AI Assistant" in response.text
    assert "text/html" in response.headers.get("content-type", "")


def test_chat_validation_empty_message():
    """Test that empty or blank message produces 422 Unprocessable Entity."""
    # Empty string
    response = client.post("/api/chat", json={"message": ""})
    assert response.status_code == 422

    # Whitespace only
    response = client.post("/api/chat", json={"message": "   "})
    assert response.status_code == 422


def test_chat_multi_turn_conversation_memory():
    """Test multi-turn conversation memory persistence for a given conversation_id."""
    conv_id = "test_conv_123"

    # Step 1: User asks for a product
    res1 = client.post("/api/chat", json={"conversation_id": conv_id, "message": "عاوز منتج مناسب"})
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["conversation_id"] == conv_id
    assert len(data1["message"]) > 0

    # Step 2: User specifies budget
    res2 = client.post("/api/chat", json={"conversation_id": conv_id, "message": "ميزانيتي 1000 جنيه"})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["conversation_id"] == conv_id

    # Verify that conversation history has preserved both user turns and model replies
    history = conversation_service.get_history(conv_id)
    assert len(history) == 4  # 2 user messages + 2 model responses
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "عاوز منتج مناسب"
    assert history[1]["role"] == "model"
    assert history[2]["role"] == "user"
    assert history[2]["content"] == "ميزانيتي 1000 جنيه"
    assert history[3]["role"] == "model"


def test_chat_reset_conversation():
    """Test that resetting a conversation removes its memory."""
    conv_id = "test_conv_reset"

    # Send message
    res = client.post("/api/chat", json={"conversation_id": conv_id, "message": "مرحبا"})
    assert res.status_code == 200
    assert len(conversation_service.get_history(conv_id)) == 2

    # Reset conversation
    reset_res = client.post("/api/chat/reset", json={"conversation_id": conv_id})
    assert reset_res.status_code == 200
    assert reset_res.json()["success"] is True

    # Check history is cleared
    assert len(conversation_service.get_history(conv_id)) == 0


def test_mock_business_context_generation():
    """Test that get_business_context outputs formatted products, orders, and policies."""
    context = get_business_context()
    assert "BUSINESS CONTEXT" in context
    assert "Classic Product" in context
    assert "ORD-1001" in context
    assert "14 يوم" in context
    assert "الشحن المجاني" in context


def test_gemini_api_mock_call():
    """Test full chat pipeline with mocked Gemini client."""
    from app.services.gemini import gemini_service

    mock_client = MagicMock()
    mock_model_response = MagicMock()
    mock_model_response.text = "أهلاً بك! أرشح لك Classic Product بسعر 350 جنيه."
    mock_client.models.generate_content.return_value = mock_model_response

    original_client = gemini_service.client
    original_api_key = gemini_service.api_key
    try:
        gemini_service.client = mock_client
        gemini_service.api_key = "fake_test_key"

        response = client.post("/api/chat", json={"message": "رشحلي منتج كلاسيك"})
        assert response.status_code == 200
        data = response.json()
        assert "Classic Product" in data["message"]
        assert mock_client.models.generate_content.called
    finally:
        gemini_service.client = original_client
        gemini_service.api_key = original_api_key


def test_chat_still_works_without_visitor_key(monkeypatch):
    """Without the header the server-side (mock) flow is untouched."""
    response = client.post("/api/chat", json={"conversation_id": "no_key_conv", "message": "مرحبا"})
    assert response.status_code == 200
    assert len(response.json()["message"]) > 0
