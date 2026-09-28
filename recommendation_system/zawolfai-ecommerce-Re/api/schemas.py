from pydantic import BaseModel
from typing import List, Optional, Dict

class ProductCardDTO(BaseModel):
    product_id: int
    product_name: str
    category: str
    color: str
    price_tier: str
    image_uri: str
    size_attr: Optional[str] = "standard"
    badge_text: Optional[str] = None
    relevance_score: Optional[float] = None

class ProductDetailResponse(BaseModel):
    product: ProductCardDTO
    description: str
    stock_status: str
    complete_the_look: List[ProductCardDTO]
    similar_alternatives: List[ProductCardDTO]

class CategorizedCatalogResponse(BaseModel):
    categories: Dict[str, List[ProductCardDTO]]