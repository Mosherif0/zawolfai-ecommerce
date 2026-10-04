from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class ProductItem(BaseModel):
    """
    A product card rendered by the chat UI.

    Backed by the real catalog (`app/services/catalog_service.py`), NOT the
    old hardcoded mock list. `product_id` matches `clean_catalog.csv`.
    """

    product_id: int
    name: str
    price: float = Field(..., description="Price in EGP")
    category: Optional[str] = None
    category_ar: Optional[str] = Field(
        default=None, description="Arabic category label for display"
    )
    color: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = Field(
        default=None, description="Static URL served by this app, e.g. /static/images/123.jpg"
    )
    price_tier: Optional[str] = None
    reason: Optional[str] = Field(
        default=None, description="One-line, human explanation of why this was suggested"
    )


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Unique conversation session identifier"
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User message text"
    )

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Message cannot be empty or whitespace only.")
        return trimmed


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    products: Optional[List[ProductItem]] = None


class ResetRequest(BaseModel):
    conversation_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Conversation session identifier to reset"
    )


class ResetResponse(BaseModel):
    success: bool
    message: str



class KeyStatusResponse(BaseModel):
    """
    Tells the chat UI whether a visitor has to provide their own Gemini API key
    (shared / "bring your own key" mode) or whether the server already has one.
    """

    server_key_configured: bool = Field(
        ...,
        description="True when a server-side GEMINI_API_KEY is configured in .env",
    )
    byo_key_required: bool = Field(
        ...,
        description="True when the visitor must supply their own Gemini API key",
    )
    model: Optional[str] = Field(
        default=None,
        description="Primary Gemini model in use",
    )


class VerifyKeyResponse(BaseModel):
    """Result of validating a visitor-supplied Gemini API key."""

    valid: bool
    message: str
