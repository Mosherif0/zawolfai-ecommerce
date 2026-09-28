import re
import pandas as pd

EXCLUDED_KEYWORDS = [
    'bra', 'pantie', 'underwear', 'lingerie', 'thong', 'brief', 'boxer',
    'swimwear', 'bikini', 'swimsuit', 'nightwear', 'tights', 'bodysuit',
    'socks', 'corset', 'pajama', 'under'
]

class TextProcessor:
    @staticmethod
    def is_safe_product(row) -> bool:
        text = f"{row.get('product_name', '')} {row.get('category', '')} {row.get('subcategory', '')}".lower()
        return not any(bad_word in text for bad_word in EXCLUDED_KEYWORDS)

    @staticmethod
    def extract_size_attribute(text: str) -> str:
        text = str(text).lower()
        den_match = re.search(r'(\d{2,3})\s*den', text)
        if den_match:
            return f"{den_match.group(1)}den"
        pack_match = re.search(r'(\d+)\s*(p|pk|pack)', text)
        if pack_match:
            return f"{pack_match.group(1)}pack"
        return "standard"

    @classmethod
    def clean_catalog(cls, df: pd.DataFrame) -> pd.DataFrame:
        clean_df = df[df.apply(cls.is_safe_product, axis=1)].copy()
        
        price_cols = [c for c in clean_df.columns if 'price' in c.lower()]
        if price_cols:
            clean_df['price_tier'] = pd.qcut(
                clean_df[price_cols[0]].rank(method='first'), q=3, labels=['budget', 'mid_range', 'premium']
            )
        else:
            clean_df['price_tier'] = 'standard'

        for col in ['product_name', 'category', 'subcategory', 'brand', 'color', 'description']:
            if col in clean_df.columns:
                clean_df[col] = clean_df[col].fillna('').astype(str)

        clean_df['metadata_soup'] = (
            clean_df['product_name'] + " " +
            clean_df['category'] + " " +
            clean_df['subcategory'] + " " +
            clean_df['color'] + " " +
            clean_df['description']
        ).str.lower()

        clean_df['size_attr'] = clean_df['metadata_soup'].apply(cls.extract_size_attribute)
        return clean_df