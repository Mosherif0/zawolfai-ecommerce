"""
FastAPI application for the recommendation system.

Rebuilt from main.py. What changed and why:

  * Loading moved out of import time into core.catalog_service, cached behind
    an lru_cache. main.py read the 14k-row CSV and built a BM25 index at import,
    which meant every test, every worker and every reload paid for it.
  * Paths are absolute (resolved from __file__). main.py used relative paths
    ('data/processed/...'), so the app only started when uvicorn happened to
    run from this exact directory.
  * Images are served as files with cache headers instead of base64. The old
    ImageProcessor base64-encoded every photo into the JSON response, turning a
    5-card page into megabytes of payload.
  * The forecasting integration is optional. main.py did
    `sys.path.insert` + a top-level import of another project, so this service
    could not start if demand_forecasting was missing.
  * /health/catalog reports load failures instead of the app dying at import.
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from core.catalog_service import (  # noqa: E402
    STATIC_DIR,
    get_catalog_service,
)

CATALOG_PATH = BASE / "data" / "processed" / "clean_catalog.csv"
IMAGES_DIR = BASE / "data" / "images"

STATIC_PATH = BASE / "static"


# --------------------------------------------------------------------------
# schemas
# --------------------------------------------------------------------------

class ProductCard(BaseModel):
    product_id: int
    name: str
    category: str
    color: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    badge: Optional[str] = None


class ProductDetail(BaseModel):
    product: ProductCard
    description: Optional[str] = None
    complete_the_look: List[ProductCard] = []
    similar: List[ProductCard] = []


class CatalogResponse(BaseModel):
    count: int
    products: List[ProductCard]
    categories: Dict[str, int] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    count: int
    results: List[ProductCard]


class HealthResponse(BaseModel):
    status: str
    backend: str
    catalog_loaded: bool
    product_count: int
    forecasting_available: bool
    load_error: Optional[str] = None


# --------------------------------------------------------------------------
# forecasting integration (optional)
# --------------------------------------------------------------------------

_FORECASTER = None
_FORECASTER_ERROR: Optional[str] = None


def _load_forecaster():
    """
    Load demand_forecasting.forecasting_service if the sibling project exists.

    Imported lazily inside a try/except on purpose: the recommendation service
    must start even when forecasting is unavailable, and /health then reports
    forecasting_available=false instead of the whole app failing to import.
    """
    global _FORECASTER, _FORECASTER_ERROR
    if _FORECASTER is not None or _FORECASTER_ERROR is not None:
        return _FORECASTER

    project_root = BASE.parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    try:
        from demand_forecasting.forecasting_service import forecast_article
        _FORECASTER = forecast_article
        _FORECASTER_ERROR = None
    except Exception as exc:
        _FORECASTER = None
        _FORECASTER_ERROR = f"{type(exc).__name__}: {exc}"
    return _FORECASTER


# --------------------------------------------------------------------------
# app
# --------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm the catalog once so the first request is not the slow one.
    service = get_catalog_service()
    if not service.available:
        print(f"[WARN] catalog not loaded: {service.load_error}")
    else:
        # The photos live in data/images but must be served from /static, so
        # sync them on startup. Idempotent, so this costs nothing after the
        # first run.
        copied = service.sync_images(STATIC_PATH / "images")
        print(f"[ OK ] catalog ready: {service.size} products "
              f"({copied} images synced)")
    _load_forecaster()
    yield


app = FastAPI(
    title="Zawolf AI - Recommendation System",
    description="Product recommendations over a real fashion catalog.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_PATH.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_PATH)), name="static")


def _card(product_id: int, badge: Optional[str] = None) -> Optional[ProductCard]:
    service = get_catalog_service()
    row = service.get(product_id)
    if row is None:
        return None
    price = row.get("price")
    try:
        price = float(price)
    except (TypeError, ValueError):
        price = None
    return ProductCard(
        product_id=int(row["product_id"]),
        name=str(row.get("product_name", "")),
        category=str(row.get("category", "")),
        color=str(row.get("colour_group_name")) if row.get("colour_group_name") else None,
        brand=str(row.get("brand")) if row.get("brand") else None,
        price=price,
        image_url=service.image_url(int(row["product_id"])),
        badge=badge,
    )


def _require_catalog():
    service = get_catalog_service()
    if not service.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"catalog unavailable: {service.load_error}",
        )
    return service


# --------------------------------------------------------------------------
# endpoints
# --------------------------------------------------------------------------

@app.get("/health/catalog", response_model=HealthResponse, tags=["Health"])
async def health() -> HealthResponse:
    """Load state of every dependency. Never raises - a health check that 500s
    tells you nothing."""
    service = get_catalog_service()
    return HealthResponse(
        status="ok" if service.available else "degraded",
        backend="bm25",
        catalog_loaded=service.available,
        product_count=service.size,
        forecasting_available=_load_forecaster() is not None,
        load_error=service.load_error,
    )


@app.get("/api/v1/products", response_model=CatalogResponse, tags=["Catalog"])
async def list_products(limit: int = Query(50, ge=1, le=200)) -> CatalogResponse:
    service = _require_catalog()
    ids = [int(x) for x in service.df["product_id"].head(limit)]
    cards = [c for c in (_card(i) for i in ids) if c]
    return CatalogResponse(
        count=len(cards),
        products=cards,
        categories={k: int(v) for k, v in service.facets()["categories"].items()},
    )


@app.get("/api/v1/search", response_model=SearchResponse, tags=["Catalog"])
async def search(q: str = Query(..., min_length=1), limit: int = Query(12, ge=1, le=50)
                 ) -> SearchResponse:
    service = _require_catalog()
    ids = service.search(q, top_k=limit)
    cards = [c for c in (_card(i) for i in ids) if c]
    return SearchResponse(query=q, count=len(cards), results=cards)


@app.get("/api/v1/facets", tags=["Catalog"])
async def facets() -> Dict:
    service = _require_catalog()
    return {"count": service.size,
            **{k: {str(a): int(b) for a, b in v.items()}
               for k, v in service.facets().items()}}


@app.get("/api/v1/products/{product_id}", response_model=ProductDetail, tags=["Catalog"])
async def product_detail(product_id: int) -> ProductDetail:
    service = _require_catalog()
    card = _card(product_id)
    if card is None:
        raise HTTPException(status_code=404, detail="product not found")

    row = service.get(product_id)
    related = service.related(product_id, top_k=4)

    def cards(ids: List[int], badge: str) -> List[ProductCard]:
        return [c for c in (_card(i, badge) for i in ids) if c]

    return ProductDetail(
        product=card,
        description=str(row.get("description")) if row.get("description") else None,
        complete_the_look=cards(related["complete_the_look"], "Complete the look"),
        similar=cards(related["similar"], "Similar"),
    )


@app.get("/api/v1/images/{filename}", tags=["Media"])
async def product_image(filename: str) -> Response:
    """
    Serve a photo as a file.

    The previous ImageProcessor base64-encoded every image INTO the JSON, so a
    page with five cards carried megabytes of image data. Serving the file
    lets the browser cache it and keeps responses small.
    """
    service = _require_catalog()
    data = service.image_bytes(filename)
    if data is None:
        raise HTTPException(status_code=404, detail="image not found")
    return Response(
        content=data,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=604800"},
    )


@app.get("/api/v1/forecast/{product_id}", tags=["Forecasting"])
async def forecast(product_id: int) -> Dict:
    """
    Predicted demand for one product next week.

    Returns 503 with the reason when forecasting is unavailable, so the caller
    can tell "not installed" apart from "prediction failed".
    """
    forecaster = _load_forecaster()
    if forecaster is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"forecasting unavailable: {_FORECASTER_ERROR}",
        )
    try:
        return forecaster(product_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"forecast failed: {type(exc).__name__}: {exc}")


@app.get("/", include_in_schema=False)
async def home():
    index = STATIC_PATH / "index.html"
    if index.is_file():
        return Response(content=index.read_bytes(), media_type="text/html")
    return {"service": "zawolf-recommendations", "docs": "/docs"}


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_root() -> HealthResponse:
    """
    Alias of /health/catalog.

    All three services expose the same path so run_all.py and any load
    balancer can probe them with one rule.
    """
    return await health()
