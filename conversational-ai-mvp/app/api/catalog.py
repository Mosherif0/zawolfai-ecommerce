"""
Catalog API: exposes the real product catalog to the frontend and to the
chat service.

Endpoints
---------
GET /api/catalog
    All catalog products grouped by Arabic category.
GET /api/products/{product_id}
    One product plus complementary / similar items (BM25 based).
GET /api/health/catalog
    Diagnostics: is the catalog loaded, how many products, any load error.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.catalog_service import (
    CatalogProduct,
    get_catalog_service,
)

router = APIRouter(prefix="/api", tags=["Catalog"])


class CatalogProductOut(BaseModel):
    product_id: int
    name: str
    price: float
    category: str
    category_ar: str
    color: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    price_tier: Optional[str] = None


class CatalogResponse(BaseModel):
    count: int
    categories: Dict[str, List[CatalogProductOut]] = Field(default_factory=dict)
    products: List[CatalogProductOut] = Field(default_factory=list)


class ProductDetailOut(BaseModel):
    product: CatalogProductOut
    complete_the_look: List[CatalogProductOut] = Field(default_factory=list)
    similar_items: List[CatalogProductOut] = Field(default_factory=list)


class CatalogHealthOut(BaseModel):
    available: bool
    product_count: int
    category_count: int
    load_error: Optional[str] = None


def _to_out(p: CatalogProduct) -> CatalogProductOut:
    return CatalogProductOut(
        product_id=p.product_id,
        name=p.name,
        price=p.egp_price,
        category=p.category,
        category_ar=p.category_ar,
        color=p.color or None,
        description=p.description or None,
        image_url=p.image_url,
        price_tier=p.price_tier,
    )


def _require_catalog():
    svc = get_catalog_service()
    if not svc.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Catalog is unavailable.",
        )
    return svc


@router.get("/catalog", response_model=CatalogResponse)
async def get_catalog() -> CatalogResponse:
    svc = _require_catalog()
    products = svc.all_products()

    grouped: Dict[str, List[CatalogProductOut]] = {}
    for p in products:
        grouped.setdefault(p.category_ar, []).append(_to_out(p))

    return CatalogResponse(
        count=len(products),
        categories=grouped,
        products=[_to_out(p) for p in products],
    )


@router.get("/products/{product_id}", response_model=ProductDetailOut)
async def get_product(product_id: int) -> ProductDetailOut:
    svc = _require_catalog()
    product = svc.get(product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found in catalog.",
        )

    same_cat = [p for p in svc.all_products()
                if p.category == product.category and p.product_id != product_id]
    other_cat = [p for p in svc.all_products()
                 if p.category != product.category and p.product_id != product_id]

    return ProductDetailOut(
        product=_to_out(product),
        complete_the_look=[_to_out(p) for p in other_cat[:4]],
        similar_items=[_to_out(p) for p in same_cat[:4]],
    )


@router.get("/health/catalog", response_model=CatalogHealthOut)
async def catalog_health() -> CatalogHealthOut:
    svc = get_catalog_service()
    return CatalogHealthOut(
        available=svc.available,
        product_count=svc.size,
        category_count=len(svc.categories()),
        load_error=svc.load_error,
    )

# --------------------------------------------------------------------------
# Facets - what the customer can filter on, and how much stock there is
# --------------------------------------------------------------------------

@router.get("/facets")
async def get_facets():
    """
    Distinct values per facet with stock counts.

    Exposing this lets the UI (and the LLM) know the real shape of the shop
    instead of guessing, and makes it obvious when a facet has only one item.
    """
    svc = _require_catalog()
    products = svc.all_products()

    def tally(attr: str) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for p in products:
            key = getattr(p, attr) or "غير محدد"
            out[key] = out.get(key, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    return {
        "total": len(products),
        "categories": tally("category_ar"),
        "colors": tally("color"),
        "brands": tally("brand"),
        "price_tiers": tally("price_tier"),
        "price_range": {
            "min": min(p.egp_price for p in products),
            "max": max(p.egp_price for p in products),
        },
    }
