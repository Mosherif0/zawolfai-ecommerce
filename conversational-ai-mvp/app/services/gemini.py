import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

from google import genai
from google.genai import types

from app.services.conversation import conversation_service
from app.services.mock_data import get_business_context
from app.services.catalog_service import CatalogProduct, expand_query, get_catalog_service
from app.models.chat import ProductItem

# Default model + fallback candidates used when GEMINI_MODEL fails
# (e.g. 404 "no longer available to new users" or 503 "high demand").
DEFAULT_MODEL = "gemini-3.6-flash"
DEFAULT_FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3.7-flash", "gemini-2.5-flash-lite"]
DEFAULT_TIMEOUT_MS = 30000

# Default timeout in ms
DEFAULT_TIMEOUT_MS = 30000


# Load environment variables from .env
load_dotenv(override=True)


class GeminiUnavailableError(RuntimeError):
    """Raised when no candidate Gemini model could produce a reply."""


class GeminiService:
    """
    Service for managing interactions with Google Gemini API
    combining system instructions, mock business context, and multi-turn conversation memory.
    """

    def __init__(self):
        self.reload_config()

    def reload_config(self) -> None:
        load_dotenv(override=True)
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model_name = os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_MODEL

        # Optional comma-separated fallback models (used if the primary model is unavailable).
        raw_fallbacks = os.getenv("GEMINI_FALLBACK_MODELS", "").strip()
        fallback_candidates = (
            [m.strip() for m in raw_fallbacks.split(",") if m.strip()]
            if raw_fallbacks
            else DEFAULT_FALLBACK_MODELS
        )
        self.fallback_models = [m for m in fallback_candidates if m != self.model_name]

        # Request timeout (ms) so a stuck/unavailable model never freezes the chat.
        try:
            self.request_timeout_ms = int(os.getenv("GEMINI_TIMEOUT_MS", "").strip() or DEFAULT_TIMEOUT_MS)
        except ValueError:
            self.request_timeout_ms = DEFAULT_TIMEOUT_MS

        # HTTP options
        self._http_options = types.HttpOptions(
            timeout=self.request_timeout_ms,
            retry_options=types.HttpRetryOptions(
                attempts=2,
                initial_delay=0.5,
                http_status_codes=[408, 429, 500, 502, 503, 504],
            ),
        )

        # Last successfully used model (so we don't retry a broken model on every turn).
        self.active_model: Optional[str] = None

        self._load_system_prompt()
        self._init_client()

    def _load_system_prompt(self) -> None:
        """
        Build the system instruction.

        Two knowledge blocks exist:
          * CATALOG CONTEXT  - REAL products (price/color/image), injected
                               per-request by `_build_catalog_context`.
          * BUSINESS CONTEXT - shipping / returns / payments (demo data).

        The base instruction is cached so the 659-line policy prompt is not
        re-read from disk on every call.
        """
        if not getattr(self, "_base_instruction", None):
            base_dir = Path(__file__).resolve().parent.parent
            prompt_file = base_dir / "prompts" / "system_prompt.txt"

            base_prompt = ""
            if prompt_file.exists():
                base_prompt = prompt_file.read_text(encoding="utf-8-sig").strip()
            else:
                base_prompt = "أنت مساعد ذكي ودود وعملي لخدمة العملاء والمنتجات."

            business_context = get_business_context()
            self._base_instruction = f"{base_prompt}\n\n{business_context}"

        self.system_instruction = self._base_instruction

    @staticmethod
    def _catalog_rules() -> str:
        """
        Grounding rules shipped next to the per-request catalog block.

        The model cannot know that catalog prices are authoritative unless we
        say so explicitly; without this it blends the demo policies with the
        real catalog and invents prices.
        """
        return (
                    "\n\n--- قواعد الكتالوج (CATALOG RULES) ---\n"
                    "1) المنتجات تحت عنوان REAL CATALOG هي المتوفرة فعلياً في المتجر.\n"
                    "2) ممنوع تخترع منتج أو سعر أو لون أو ماركة غير مذكور في هذا القسم.\n"
                    "   لو المنتج المطلوب مش موجود، صرّح إنك مش لاقيه واعرض الأقرب.\n"
                    "3) استخدم السعر المذكور حرفياً بالجنيه، من غير تحويل ولا تقريب.\n"
                    "4) الـproduct_id هو المرجع الوحيد للمنتج، ومينفعش تخترع رقم.\n"
                    "5) راجع نفسك قبل الرد: لو ذكرت منتج، لازم يكون اسم من REAL CATALOG.\n"
                    "   أي اسم تاني (زي Classic Product أو Basic T-Shirt أو Socks Pack\n"
                    "   أو Premium Hoodie) بيانات قديمة مش موجودة في الكتالوج — ممنوع تنطقها.\n"
                )

    def _build_catalog_context(self, products: List[CatalogProduct]) -> str:
        if not products:
            return (
                "\n\n--- كتالوج المنتجات ---\n"
                "(مفيش منتجات مطابقة للرسالة دي)\n"
            )
        svc = get_catalog_service()
        return (
            "\n\n"
            "========== REAL CATALOG (المصدر الحقيقي الوحيد) ==========\n"
            "المنتجات دي هي اللي بيتم بيها البيع. منتج غير مذكور هنا = غير موجود.\n\n"
            + svc.format_context(products)
            + "\n\n"
            "=========================================================\n"
            + self._catalog_rules()
        )

    def _init_client(self) -> None:
        if self.api_key:
            try:
                self.client = genai.Client(
                    api_key=self.api_key,
                    http_options=self._http_options,
                )
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini Client: {e}")
                self.client = None
        else:
            self.client = None
    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    @staticmethod
    def _to_card(p: CatalogProduct, reason: Optional[str] = None) -> ProductItem:
        """Convert a catalog product into the API card shape."""
        return ProductItem(
            product_id=p.product_id,
            name=p.name,
            price=float(p.egp_price),
            category=p.category,
            category_ar=p.category_ar,
            color=p.color or None,
            description=p.description or None,
            image_url=p.image_url,
            price_tier=p.price_tier,
            reason=reason,
        )

    @staticmethod
    def _recent_product_ids(history: List[dict], limit: int = 6) -> List[int]:
        """
        Pull the product_ids of the cards we already showed, newest first.

        This is what makes follow-ups like "التاني بكام؟" resolve: BM25 on
        that query alone scores nothing, so we prepend the ids already on the
        user's screen.
        """
        import json as _json

        ids: List[int] = []
        for turn in reversed(history):
            if turn.get("role") != "model":
                continue
            raw = turn.get("cards_json")
            if not raw:
                continue
            try:
                for card in _json.loads(raw):
                    pid = card.get("product_id")
                    if isinstance(pid, int) and pid not in ids:
                        ids.append(pid)
                    if len(ids) >= limit:
                        return ids
            except (ValueError, TypeError):
                continue
        return ids


    def _retrieve(self, message: str, history: List[dict],
                  top_k: int = 4) -> List[CatalogProduct]:
        """
        Deterministic product retrieval.

        The LLM never picks which products to show; BM25 + filters decide that.
        The same results feed BOTH the prompt context and the UI cards, so the
        assistant can never talk about a product the user cannot see.
        """
        svc = get_catalog_service()
        if not svc.available:
            return []

        # "وريني كل المنتجات" genuinely wants the whole set, so widen the
        # window instead of silently showing four items.
        _, filters = expand_query(message)
        if filters.get("show_all"):
            top_k = 12

        results = svc.search(
            message,
            top_k=top_k,
            fallback_product_ids=self._recent_product_ids(history),
        )

        # Too few hits means the request over-specified (rare colour + tight
        # budget). Widen the band rather than showing one lonely item.
        if 0 < len(results) < 3 and not filters.get("show_all"):
            if filters.get("max_price") is not None or filters.get("min_price") is not None:
                wider = svc.search(message, top_k=top_k)
                if len(wider) > len(results):
                    return wider
        return results

    def _build_reason(self, product: CatalogProduct, message: str) -> Optional[str]:
        """
        A short, specific "why this one" line for a card.

        Generic reasons like "من فئة جاكيت" repeated on every card waste the
        space, so we mention the attribute the user did NOT filter on
        (colour, price band, material from the description) which is what
        actually differentiates one card from the next.
        """
        from app.services.catalog_service import expand_query

        _, filters = expand_query(message)

        # Never repeat the reason the user already knows.
        bits: List[str] = []
        if filters.get("category"):
            # price band is genuinely new information
            if filters.get("max_price") or filters.get("tier_preference"):
                bits.append(f"{product.egp_price} جنيه")
            else:
                bits.append(f"السعر {product.egp_price} جنيه")
        else:
            bits.append(product.category_ar)

        if product.color and not filters.get("color"):
            bits.append(product.color)

        if product.brand:
            bits.append(product.brand)

        return " · ".join(bits[:3])

    def _build_contents(self, history: List[dict], message: str) -> List[types.Content]:
        """Builds the multi-turn contents payload sent to Gemini."""
        contents = []
        for turn in history:
            contents.append(
                types.Content(
                    role=turn["role"],
                    parts=[types.Part.from_text(text=turn["content"])]
                )
            )
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=message)]
            )
        )
        return contents

    def _candidate_models(self) -> List[str]:
        """
        Ordered list of models to try: the last working one, the configured model, then the fallbacks.
        """
        candidates: List[str] = []
        for model in [getattr(self, "active_model", None), self.model_name, *self.fallback_models]:
            if model and model not in candidates:
                candidates.append(model)
        return candidates

        return candidates


    @staticmethod
    def _looks_like_key_error(error: Exception) -> bool:
        """Detects authentication/authorization failures caused by an invalid API key."""
        text = str(error).upper()
        return any(
            marker in text
            for marker in (
                "API_KEY_INVALID",
                "API KEY NOT VALID",
                "401",
                "PERMISSION_DENIED",
                "UNAUTHENTICATED",
            )
        )

    @staticmethod
    def _key_error_message(error: Exception) -> str:
        """User-facing (Arabic) explanation for a rejected key. Never includes the key itself."""
        text = str(error).upper()
        if "429" in text or "RESOURCE_EXHAUSTED" in text:
            return "المفتاح شغال بس وصل لحد الاستخدام (Quota). جرّب بعد شوية أو استخدم مفتاح تاني."
        if "403" in text or "PERMISSION_DENIED" in text:
            return "المفتاح مش مصرّح له بالوصول للـ Gemini API. راجع صلاحيات المفتاح في Google AI Studio."
        return "مفتاح الـ API غير صالح. اتأكد إنك نسخته كامل من https://aistudio.google.com/apikey"

    def _generate_reply(
        self,
        contents: List[types.Content],
        config: types.GenerateContentConfig,
    ) -> str:
        """
        Calls Gemini, trying each candidate model until one answers.
        Raises GeminiUnavailableError when every model fails.
        """
        active_client = self.client
        if active_client is None:
            raise GeminiUnavailableError("Gemini client is not initialised")
        last_error = "no candidate model configured"

        for model in self._candidate_models():
            try:
                response = active_client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                )
                text = (response.text or "").strip()
                if text:
                    self.active_model = model
                    return text
                last_error = f"model '{model}' returned an empty response"
            except Exception as e:
                last_error = f"model '{model}' failed ({e})"
                if self._looks_like_key_error(e):
                    print("Warning: the API key was rejected by Gemini.")
                    break
            print(f"Warning: {last_error}")

        raise GeminiUnavailableError(last_error)

    def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
    ) -> Tuple[str, List[ProductItem]]:
        """
        Handles one user turn end to end.

        Flow:
            1. retrieve products deterministically (BM25 + filters)
            2. inject them into the system instruction as the ONLY source
            3. generate the reply with Gemini
            4. return the SAME products as UI cards

        Returns (conversation_id, response_text, products).
        """
        if not self.client:
            self.reload_config()

        cid = conversation_service.get_or_create_conversation_id(conversation_id)
        history = conversation_service.get_history(cid)

        # 1) Deterministic retrieval - the LLM does not choose products.
        self._load_system_prompt()
        retrieved = self._retrieve(message, history)

        # 2) Ground the model on exactly these products.
        config = types.GenerateContentConfig(
            system_instruction=self.system_instruction
            + self._build_catalog_context(retrieved),
            temperature=0.7,
        )
        contents = self._build_contents(history, message)

        try:
            response_text = self._generate_reply(contents, config)
        except GeminiUnavailableError:
            # Never fabricate a reply: an honest "try again" beats a confident
            # lie about a product or an order that does not exist.
            response_text = (
                "حصلت مشكلة بسيطة في الاتصال دلوقتي، فمقدرتش أرد عليك. "
                "جرّب تبعت الرسالة تاني بعد ثانية واحدة."
            )
            retrieved = []

        # 3) Persist turn + the shown cards so follow-ups can reference them.
        conversation_service.add_user_message(cid, message)
        conversation_service.add_model_message(cid, response_text)

        products = [self._to_card(p, self._build_reason(p, message)) for p in retrieved]
        if products:
            conversation_service.attach_cards(
                cid, [{"product_id": c.product_id, "name": c.name} for c in products]
            )

        return cid, response_text, products



# Global singleton instance
gemini_service = GeminiService()
