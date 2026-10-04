import os
import sys
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.schemas import ProductDetailResponse, CategorizedCatalogResponse, ProductCardDTO
from engines.dual_recommender import DualRecommender
from core.image_processor import ImageProcessor

# Forecasting service
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from demand_forecasting.forecasting_service import forecast_article

app = FastAPI(title="Zawolf AI — Production System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
async def serve_home():
    return FileResponse("static/index.html")

CATALOG_PATH = "data/processed/clean_catalog.csv"
IMAGES_DIR = "data/images"

# 1. بنجمع أرقام الـ 50 صورة الفعلية
def load_valid_image_ids(images_path):
    valid_ids = set()
    if os.path.exists(images_path):
        for f in os.listdir(images_path):
            name, ext = os.path.splitext(f)
            if ext.lower() in ['.jpg', '.jpeg', '.png']:
                try:
                    valid_ids.add(int(name))
                except ValueError:
                    pass
    return valid_ids

valid_pids = load_valid_image_ids(IMAGES_DIR)

# 2. فلترة الكتالوج كله للـ 50 منتج فقط لا غير
raw_catalog = pd.read_csv(CATALOG_PATH)
if len(valid_pids) > 0:
    catalog_df = raw_catalog[raw_catalog['product_id'].isin(valid_pids)].copy().reset_index(drop=True)
else:
    catalog_df = raw_catalog.copy().reset_index(drop=True)

recommender = DualRecommender(catalog_df, images_dir=IMAGES_DIR)
img_processor = ImageProcessor(images_dir=IMAGES_DIR)

@app.get("/api/v1/catalog", response_model=CategorizedCatalogResponse)
async def get_categorized_catalog():
    categories_map = {
        "Trousers & Jeans": catalog_df[catalog_df['category'].str.contains('trousers|pants|jeans', case=False, na=False)],
        "Jackets & Outerwear": catalog_df[catalog_df['category'].str.contains('jacket|coat', case=False, na=False)],
        "Dresses & Sets": catalog_df[catalog_df['category'].str.contains('dress', case=False, na=False)],
        "Tops & Tees": catalog_df[catalog_df['category'].str.contains('top|t-shirt|shirt', case=False, na=False)]
    }
    
    result = {}
    for cat_name, df_sub in categories_map.items():
        cards = []
        for _, row in df_sub.iterrows():
            cards.append(ProductCardDTO(
                product_id=int(row['product_id']),
                product_name=str(row['product_name']),
                category=str(row['category']),
                color=str(row.get('color', 'N/A')),
                price_tier=str(row.get('price_tier', 'STANDARD')).upper(),
                image_uri=img_processor.resolve_image_uri(row['product_id'], row['category']),
                size_attr=str(row.get('size_attr', 'standard'))
            ))
        result[cat_name] = cards
        
    return CategorizedCatalogResponse(categories=result)

@app.get("/api/v1/product/{product_id}", response_model=ProductDetailResponse)
async def get_product_detail(product_id: int):
    matched = catalog_df[catalog_df['product_id'] == product_id]
    if matched.empty:
        raise HTTPException(status_code=404, detail="Product not found in curated images")

    prod = matched.iloc[0]
    comp_recs, sim_recs = recommender.get_recommendations(product_id, top_k=3)

    main_card = ProductCardDTO(
        product_id=int(prod['product_id']),
        product_name=str(prod['product_name']),
        category=str(prod['category']),
        color=str(prod.get('color', 'N/A')),
        price_tier=str(prod.get('price_tier', 'STANDARD')).upper(),
        image_uri=img_processor.resolve_image_uri(prod['product_id'], prod['category']),
        size_attr=str(prod.get('size_attr', 'standard'))
    )

    return ProductDetailResponse(
        product=main_card,
        description=str(prod.get('description', 'High quality fashion essential.')),
        stock_status="IN_STOCK",
        complete_the_look=comp_recs,
        similar_alternatives=sim_recs
    )

@app.get("/api/v1/forecast/{article_id}")
async def get_forecast(article_id: int):
    try:
        return forecast_article(article_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))