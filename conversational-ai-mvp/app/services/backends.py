"""
Clients for the other backend services.

The chatbot does not own the data: stock lives in the OCR service and demand
forecasts live in the forecasting service. This module is the only place that
knows their URLs, so a change of port happens here and nowhere else.

Two rules shape the code:

1. Never raise into the chat path. Every call returns a result object carrying
   a status, because a chat request that raises while a downstream service is
   restarting must still return an answer. The user asking "what jackets do
   you have?" does not care that the stock service is down.

2. Timeouts are short and explicit. A chat reply that waits 30s for a stock
   lookup is a broken product; the catalogue half of the answer is still
   available in under a second, so failing fast beats waiting.

Nothing here is imported at module import time in a way that would start a
network call - clients are created lazily on first use.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# Short on purpose: see rule 2 above. The stock service answers in
# milliseconds when it is healthy, so anything near this means it is not.
DEFAULT_TIMEOUT = 2.5
RECOMMENDATION_TIMEOUT = 1.5


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value else default


OCR_URL = _env("OCR_SERVICE_URL", "http://127.0.0.1:8200").rstrip("/")
FORECASTING_URL = _env("FORECASTING_SERVICE_URL", "http://127.0.0.1:8400").rstrip("/")
RECOMMENDATION_URL = _env("RECOMMENDATION_SERVICE_URL", "http://127.0.0.1:8100").rstrip("/")


@dataclass
class BackendResult:
    """
    Outcome of one downstream call.

    `ok` says whether the data is usable, not whether the HTTP call succeeded:
    a 200 with an empty warehouse is ok=True with empty data, while a timeout
    is ok=False with an error message. The caller injects `note` into the
    prompt either way, so the model can be honest about it.
    """

    ok: bool
    data: Any = None
    status: str = "unknown"        # ok | empty | timeout | unreachable | error | disabled
    detail: str = ""
    elapsed_ms: int = 0

    @classmethod
    def failure(cls, status: str, detail: str, elapsed_ms: int = 0) -> "BackendResult":
        return cls(ok=False, status=status, detail=detail, elapsed_ms=elapsed_ms)


class _BaseClient:
    """Shared HTTP plumbing: one client, timeouts, and error translation."""

    def __init__(self, base_url: str, timeout: float, name: str):
        self.base_url = base_url
        self.timeout = timeout
        self.name = name
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        # A client per process, not per request: reusing the connection pool is
        # what keeps the per-request cost in the low milliseconds. Creating one
        # per call was the difference between a snappy answer and a visible lag.
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Accept": "application/json"},
            )
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _request(self, path: str, params: Optional[Dict[str, Any]] = None) -> BackendResult:
        started = time.perf_counter()

        try:
            response = self._get_client().get(path, params=params)
        except httpx.TimeoutException:
            elapsed = int((time.perf_counter() - started) * 1000)
            logger.warning("%s timed out after %sms on %s", self.name, elapsed, path)
            return BackendResult.failure("timeout", f"no answer in {self.timeout}s", elapsed)
        except httpx.RequestError as exc:
            elapsed = int((time.perf_counter() - started) * 1000)
            logger.warning("%s unreachable: %s", self.name, exc)
            return BackendResult.failure("unreachable", str(exc)[:120], elapsed)

        elapsed = int((time.perf_counter() - started) * 1000)

        if response.status_code >= 500:
            return BackendResult.failure("error", f"HTTP {response.status_code}", elapsed)
        if response.status_code == 404:
            return BackendResult.failure("error", "not found", elapsed)
        if response.status_code >= 400:
            return BackendResult.failure("error", f"HTTP {response.status_code}", elapsed)

        try:
            payload = response.json()
        except ValueError:
            return BackendResult.failure("error", "invalid JSON", elapsed)

        return BackendResult(ok=True, data=payload, status="ok", elapsed_ms=elapsed)


# --------------------------------------------------------------------------
# stock / warehouse (OCR service)
# --------------------------------------------------------------------------

class StockClient(_BaseClient):
    """Reads the warehouse the OCR service maintains."""

    def __init__(self):
        super().__init__(OCR_URL, DEFAULT_TIMEOUT, "stock")

    def search(self, term: str, limit: int = 5) -> BackendResult:
        """
        Find products by name.

        The warehouse endpoint paginates rather than filters, so the search is
        done here over a bounded fetch. Capping the scan matters: pulling the
        whole warehouse on every chat turn would grow without limit as stock
        accumulates.
        """
        result = self._request("/api/warehouse/products", {"limit": 500})
        if not result.ok:
            return result

        products = _extract_products(result.data)
        if not isinstance(products, list):
            return BackendResult.failure("error", "unexpected payload shape")

        needle = (term or "").strip().lower()
        if not needle:
            return BackendResult(ok=True, data=products[:limit], status="ok")

        # Expand Arabic category words into the English printed on receipts, so
        # "بلوز" matches "White Shirt" instead of reporting an empty warehouse.
        tokens = expand_search_terms([needle] + needle.split())

        matched = []
        for product in products:
            haystack = f"{product.get('name', '')} {product.get('category') or ''}".lower()
            if any(token in haystack for token in tokens):
                matched.append(product)

        return BackendResult(
            ok=True,
            data=matched[:limit],
            status="ok" if matched else "empty",
        )

    def stats(self) -> BackendResult:
        return self._request("/api/warehouse/stats")

    def low_stock(self, limit: int = 5) -> BackendResult:
        """Products at or below reorder level, most urgent first."""
        result = self._request("/api/warehouse/products", {"limit": 500})
        if not result.ok:
            return result

        products = _extract_products(result.data)
        at_risk = []
        for product in products:
            quantity = product.get("quantity") or 0
            reorder = product.get("reorder_level") or 0
            if reorder and quantity <= reorder:
                at_risk.append(product)

        at_risk.sort(key=lambda p: (p.get("quantity") or 0) - (p.get("reorder_level") or 0))
        return BackendResult(ok=True, data=at_risk[:limit], status="ok" if at_risk else "empty")


# --------------------------------------------------------------------------
# demand forecasting
# --------------------------------------------------------------------------

class ForecastClient(_BaseClient):
    """Reads next week's predicted demand."""

    def __init__(self):
        super().__init__(FORECASTING_URL, DEFAULT_TIMEOUT, "forecasting")

    def top_demand(self, limit: int = 5, above_threshold: bool = True) -> BackendResult:
        """
        Products predicted to sell next week.

        Defaults to above_threshold=True because roughly 95% of weeks have zero
        demand; without the cut the "top products" list is mostly noise.
        """
        params: Dict[str, Any] = {"limit": limit}
        if above_threshold:
            params["above_threshold"] = "true"
        return self._request("/forecast", params)

    def for_product(self, product_id: int) -> BackendResult:
        return self._request(f"/forecast/{product_id}")


# --------------------------------------------------------------------------
# catalogue / recommendations
# --------------------------------------------------------------------------

class RecommendationClient(_BaseClient):
    """
    Optional: the chatbot already reads the catalogue locally.

    Kept because the recommendation service owns the better ranking (facets,
    related items, diversity); a future intent can route product questions
    here instead of the in-process BM25.
    """

    def __init__(self):
        super().__init__(RECOMMENDATION_URL, RECOMMENDATION_TIMEOUT, "recommendations")

    def search(self, query: str, limit: int = 5) -> BackendResult:
        return self._request("/api/v1/search", {"q": query, "limit": limit})


# --------------------------------------------------------------------------
# singletons + health
# --------------------------------------------------------------------------

stock_client = StockClient()
forecast_client = ForecastClient()
recommendation_client = RecommendationClient()


def probe_all() -> Dict[str, str]:
    """
    Status of every downstream service, for /health.

    Reported as data rather than raising: the chatbot itself is healthy even
    when the stock service is not, and a health check that fails wholesale
    would hide that.
    """
    statuses = {}
    for label, url in (
        ("stock", f"{OCR_URL}/health"),
        ("forecasting", f"{FORECASTING_URL}/health"),
        ("recommendations", f"{RECOMMENDATION_URL}/health"),
    ):
        try:
            response = httpx.get(url, timeout=1.0)
            statuses[label] = "ok" if response.status_code == 200 else f"http_{response.status_code}"
        except httpx.TimeoutException:
            statuses[label] = "timeout"
        except Exception:
            statuses[label] = "unreachable"
    return statuses


def close_all() -> None:
    for client in (stock_client, forecast_client, recommendation_client):
        client.close()


def _extract_products(payload: Any) -> List[dict]:
    """
    Pull the product list out of a warehouse response.

    The endpoint returns {"backend": ..., "products": [...]}, but tolerating a
    bare list keeps the client working if that envelope ever changes. Guessing
    the shape and calling .get() on a list raised AttributeError, which
    surfaced as a 500 on the chat endpoint instead of a degraded answer.
    """
    if isinstance(payload, dict):
        return payload.get("products") or []
    if isinstance(payload, list):
        return payload
    return []


# --------------------------------------------------------------------------
# Arabic <-> English product vocabulary
# --------------------------------------------------------------------------

# The catalogue speaks Arabic ("جاكيت") while OCR extracts whatever was printed
# on the receipt, which is usually English ("Jacket"). Matching one against the
# other by string containment therefore finds nothing, and the chatbot
# wrongly reports an empty warehouse for a product that is physically there.
#
# This maps the category words a user types to the words that appear on retail
# receipts. It is a vocabulary bridge, not fuzzy matching: a wrong guess would
# report a quantity for the wrong product, which is worse than saying nothing.
CATEGORY_SYNONYMS: Dict[str, List[str]] = {
    "جاكيت": ["jacket", "blazer", "coat", "parka", "windbreaker"],
    "بلوز":   ["blouse", "shirt", "top"],
    "قميص":   ["shirt"],
    "فسطلان": ["jeans", "trousers", "pants"],
    "بنطلون": ["jeans", "trousers", "pants"],
    "تيشيرت": ["t-shirt", "tshirt", "tee"],
    "فستان":  ["dress", "gown"],
    "جيacket": ["jacket", "blazer"],
    "سويت شيرت": ["sweater", "hoodie", "jumper"],
    "هودي":   ["hoodie", "sweatshirt"],
    "سترة":   ["jacket", "coat", "blazer"],
}


def expand_search_terms(terms: List[str]) -> List[str]:
    """
    Turn the Arabic words a user typed into every word worth matching.

    Returns a flat list of lowercase tokens: the original Arabic terms plus
    their English receipt equivalents, so a match can happen in either
    direction without embedding or a translation call.
    """
    tokens: List[str] = [t.strip().lower() for t in terms if t and t.strip()]
    for term in list(tokens):
        for english in CATEGORY_SYNONYMS.get(term, []):
            if english not in tokens:
                tokens.append(english)
    return tokens
