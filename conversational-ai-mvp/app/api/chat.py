from typing import Optional

from fastapi import APIRouter, HTTPException, status

from app.models.chat import (
    ChatRequest,
    ChatResponse,
    ResetRequest,
    ResetResponse,
)
from app.services.gemini import gemini_service
from app.services.conversation import conversation_service

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def send_message(
    request: ChatRequest,
) -> ChatResponse:
    """
    Sends a user message to the Conversational AI Assistant.
    Maintains multi-turn context and uses mock business data.
    """
    try:
        cid, reply_text, products = gemini_service.chat(
            message=request.message,
            conversation_id=request.conversation_id,
        )
        return ChatResponse(
            conversation_id=cid,
            message=reply_text,
            products=products if products else None
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat message: {str(e)}"
        )


@router.post("/reset", response_model=ResetResponse, status_code=status.HTTP_200_OK)
async def reset_conversation(request: ResetRequest) -> ResetResponse:
    """
    Resets/clears the conversation history for a given conversation_id.
    """
    try:
        success = conversation_service.reset_conversation(request.conversation_id)
        return ResetResponse(
            success=success,
            message="Conversation history reset successfully." if success else "Conversation not found or already empty."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting conversation: {str(e)}"
        )

