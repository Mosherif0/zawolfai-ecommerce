import uuid
from typing import Dict, List, Optional


class ConversationService:
    """
    In-memory conversation store for managing multi-turn chat sessions.
    """

    def __init__(self):
        # Maps conversation_id -> list of message dicts: [{"role": "user"|"model", "content": str}]
        self._conversations: Dict[str, List[Dict[str, str]]] = {}

    def get_or_create_conversation_id(self, conversation_id: Optional[str] = None) -> str:
        """
        Returns existing conversation_id if valid/present, or generates a new unique ID.
        """
        if conversation_id and conversation_id.strip():
            cid = conversation_id.strip()
            if cid not in self._conversations:
                self._conversations[cid] = []
            return cid
        new_id = uuid.uuid4().hex[:12]
        self._conversations[new_id] = []
        return new_id

    def get_history(self, conversation_id: str) -> List[Dict[str, str]]:
        """
        Returns the conversation message history.
        """
        return self._conversations.get(conversation_id, [])

    def add_user_message(self, conversation_id: str, message: str) -> None:
        """
        Appends a user message to the conversation history.
        """
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = []
        self._conversations[conversation_id].append({
            "role": "user",
            "content": message
        })

    def add_model_message(self, conversation_id: str, message: str) -> None:
        """
        Appends an assistant/model response to the conversation history.
        """
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = []
        self._conversations[conversation_id].append({
            "role": "model",
            "content": message
        })

    def attach_cards(self, conversation_id: str, cards: list) -> None:
        """
        Store the product cards shown with the last assistant turn.

        Retrieval for a follow-up like "التاني بكام؟" has no lexical overlap
        with the catalog, so we remember what is currently on the user's
        screen. The payload is stored as JSON text inside the same dict that
        holds the message history, keeping the conversation self-describing.
        """
        import json

        history = self._conversations.get(conversation_id)
        if not history:
            return
        for turn in reversed(history):
            if turn.get("role") == "model":
                turn["cards_json"] = json.dumps(cards, ensure_ascii=False)
                return

    def reset_conversation(self, conversation_id: str) -> bool:
        """
        Clears the conversation history for a given conversation_id.
        """
        if conversation_id in self._conversations:
            self._conversations[conversation_id] = []
            return True
        return False

    def clear_all(self) -> None:
        """
        Clears all active conversations.
        """
        self._conversations.clear()


# Global singleton instance for application runtime
conversation_service = ConversationService()
