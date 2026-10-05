from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
import random
import json
from pathlib import Path

router = APIRouter(prefix="/api/platform", tags=["Platform Suite"])


class StatsResponse(BaseModel):
    ai_revenue_attribution_egp: float
    saved_work_hours: float
    stockouts_prevented_skus: int
    saved_stockout_value_egp: float
    chat_resolution_rate_percent: float
    processed_invoices_count: int


class ForecastingItem(BaseModel):
    sku: str
    product_name: str
    category: str
    current_stock: int
    predicted_demand_30d: int
    stockout_risk_percent: float
    suggested_reorder_qty: int
    estimated_reorder_cost_egp: float
    confidence_level_percent: float
    daily_trend: List[int]


class OCRParsedItem(BaseModel):
    id: str
    name: str
    quantity: int
    cost_price_egp: float
    suggested_retail_price_egp: float
    total_egp: float
    confidence_score: float
    flagged_for_review: bool


class OCRParseResponse(BaseModel):



    
    supplier_name: str
    invoice_number: str
    invoice_date: str
    items: List[OCRParsedItem]
    total_amount_egp: float
    average_confidence: float
    flagged_items_count: int


@router.get("/stats", response_model=StatsResponse)
async def get_executive_stats():
    """
    Returns executive ROI metrics for brand owners.
    """
    return StatsResponse(
        ai_revenue_attribution_egp=124500.00,
        saved_work_hours=42.5,
        stockouts_prevented_skus=18,
        saved_stockout_value_egp=65000.00,
        chat_resolution_rate_percent=92.4,
        processed_invoices_count=48
    )


@router.get("/forecasting", response_model=List[ForecastingItem])
async def get_forecasting_data():
    """
    Returns SKU-level demand forecasting data and replenishment alerts.
    """
    sample_forecasting = [
        ForecastingItem(
            sku="HM-SOCK-001",
            product_name="H&M Cotton Ankle Socks 3-Pack - Black",
            category="Socks & Underwear",
            current_stock=12,
            predicted_demand_30d=145,
            stockout_risk_percent=94.5,
            suggested_reorder_qty=150,
            estimated_reorder_cost_egp=4500.00,
            confidence_level_percent=95.0,
            daily_trend=[12, 10, 8, 5, 3, 1, 0, 0, 0, 0, 0, 0, 0, 0]
        ),
        ForecastingItem(
            sku="ZW-JKT-088",
            product_name="CartWise Waterproof Puffer Jacket - Navy",
            category="Jackets & Outerwear",
            current_stock=8,
            predicted_demand_30d=60,
            stockout_risk_percent=88.2,
            suggested_reorder_qty=65,
            estimated_reorder_cost_egp=32500.00,
            confidence_level_percent=91.5,
            daily_trend=[8, 7, 6, 4, 3, 2, 1, 0, 0, 0]
        ),
        ForecastingItem(
            sku="HM-HOOD-204",
            product_name="Oversized Hoodie - Vintage Grey",
            category="Hoodies & Sweatshirts",
            current_stock=45,
            predicted_demand_30d=110,
            stockout_risk_percent=42.0,
            suggested_reorder_qty=80,
            estimated_reorder_cost_egp=16000.00,
            confidence_level_percent=93.8,
            daily_trend=[45, 42, 39, 36, 33, 30, 27, 24, 21, 18]
        ),
        ForecastingItem(
            sku="ZW-PNT-102",
            product_name="Slim Fit Cargo Pants - Olive",
            category="Pants & Cargo",
            current_stock=110,
            predicted_demand_30d=75,
            stockout_risk_percent=12.0,
            suggested_reorder_qty=0,
            estimated_reorder_cost_egp=0.00,
            confidence_level_percent=96.2,
            daily_trend=[110, 108, 105, 103, 100, 98, 95]
        )
    ]
    return sample_forecasting


@router.post("/ocr/parse", response_model=OCRParseResponse)
async def parse_invoice_ocr(file: Optional[UploadFile] = File(None)):
    """
    Parses uploaded supplier invoice or returns sample parsed data.
    """
    sample_items = [
        OCRParsedItem(
            id="item-1",
            name="H&M Cotton Ankle Socks 3-Pack - Black / M",
            quantity=100,
            cost_price_egp=30.00,
            suggested_retail_price_egp=85.00,
            total_egp=3000.00,
            confidence_score=98.5,
            flagged_for_review=False
        ),
        OCRParsedItem(
            id="item-2",
            name="CartWise Heavyweight Cotton Tee - Off White / L",
            quantity=50,
            cost_price_egp=120.00,
            suggested_retail_price_egp=350.00,
            total_egp=6000.00,
            confidence_score=96.2,
            flagged_for_review=False
        ),
        OCRParsedItem(
            id="item-3",
            name="Raw Denim Overshirt - Indigo / XL",
            quantity=25,
            cost_price_egp=280.00,
            suggested_retail_price_egp=790.00,
            total_egp=7000.00,
            confidence_score=84.1,
            flagged_for_review=True
        ),
        OCRParsedItem(
            id="item-4",
            name="Fleece Jogger Pants - Charcoal / M",
            quantity=40,
            cost_price_egp=150.00,
            suggested_retail_price_egp=420.00,
            total_egp=6000.00,
            confidence_score=94.8,
            flagged_for_review=False
        )
    ]
    return OCRParseResponse(
        supplier_name="Al-Nassr Textile & Garment Co.",
        invoice_number="INV-2026-8941",
        invoice_date="2026-10-04",
        items=sample_items,
        total_amount_egp=22000.00,
        average_confidence=93.4,
        flagged_items_count=1
    )
