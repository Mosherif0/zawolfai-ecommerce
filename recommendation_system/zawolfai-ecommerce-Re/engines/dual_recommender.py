import os
import pandas as pd
import numpy as np
from rank_bm25 import BM25Okapi
from core.image_processor import ImageProcessor
from api.schemas import ProductCardDTO

class DualRecommender:
    def __init__(self, catalog_df: pd.DataFrame, images_dir: str):
        self.images_dir = images_dir
        self.image_proc = ImageProcessor(images_dir)
        
        # 1. بنعرف أرقام الـ 50 منتج اللي صورهم موجودة فعلياً في الفولدر
        available_ids = set()
        if os.path.exists(images_dir):
            for f in os.listdir(images_dir):
                name, ext = os.path.splitext(f)
                if ext.lower() in ['.jpg', '.jpeg', '.png']:
                    try:
                        available_ids.add(int(name))
                    except ValueError:
                        pass

        # 2. بنقص الكتالوج ونخليه يشتغل على الـ 50 منتج دول وبس
        filtered = catalog_df[catalog_df['product_id'].isin(available_ids)].copy()
        if len(filtered) > 0:
            self.catalog = filtered.reset_index(drop=True)
        else:
            self.catalog = catalog_df.copy().reset_index(drop=True)
        
        # 3. بناء فهرس BM25 على الـ 50 منتج الحقيقيين فقط
        self.tokenized_corpus = [str(doc).split() for doc in self.catalog['metadata_soup']]
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        self.id_to_idx = pd.Series(self.catalog.index, index=self.catalog['product_id']).drop_duplicates()
        
        # خريطة التنسيق للأطقم المكملة
        self.complementary_map = {
            'trousers': ['jacket', 'coat', 'top', 'vest top'],
            'jacket': ['trousers', 'top', 'dress'],
            'coat': ['trousers', 'top'],
            'top': ['trousers', 'jacket', 'coat'],
            'vest top': ['trousers', 'jacket'],
            'dress': ['jacket', 'coat']
        }

    def _to_card_dto(self, item: dict, badge: str = "", score: float = None) -> ProductCardDTO:
        return ProductCardDTO(
            product_id=int(item['product_id']),
            product_name=str(item['product_name']),
            category=str(item['category']),
            color=str(item.get('color', 'N/A')),
            price_tier=str(item.get('price_tier', 'STANDARD')).upper(),
            image_uri=self.image_proc.resolve_image_uri(item['product_id'], item['category']),
            size_attr=str(item.get('size_attr', 'standard')),
            badge_text=badge,
            relevance_score=score
        )

    def get_recommendations(self, target_pid: int, top_k: int = 3):
        if target_pid not in self.id_to_idx:
            return [], []

        idx = self.id_to_idx[target_pid]
        origin = self.catalog.iloc[idx]
        origin_cat = str(origin['category']).lower()
        origin_color = str(origin.get('color', '')).lower()
        origin_name = str(origin['product_name'])

        query_tokens = origin['metadata_soup'].split()
        scores = self.bm25.get_scores(query_tokens)
        sorted_indices = np.argsort(scores)[::-1]

        target_comps = []
        for k, v in self.complementary_map.items():
            if k in origin_cat:
                target_comps.extend(v)
                break
        if not target_comps:
            target_comps = ['jacket', 'top', 'trousers', 'dress']

        complete_look = []
        similar_styles = []
        seen = {origin_name}

        for c_idx in sorted_indices:
            if c_idx == idx:
                continue
            cand = self.catalog.iloc[c_idx]
            c_name = str(cand['product_name'])
            c_cat = str(cand['category']).lower()
            c_color = str(cand.get('color', '')).lower()

            if c_name in seen:
                continue

            # Complete the Look: صنف مكمل بصورة حقيقية
            if len(complete_look) < top_k:
                if (c_cat != origin_cat) and any(tc in c_cat for tc in target_comps):
                    seen.add(c_name)
                    complete_look.append(self._to_card_dto(cand.to_dict(), "Outfit Match", round(float(scores[c_idx]), 2)))
                    continue

            # Similar Styles: بدائل من نفس الصنف بصورة حقيقية
            if len(similar_styles) < top_k:
                if (c_cat == origin_cat):
                    seen.add(c_name)
                    similar_styles.append(self._to_card_dto(cand.to_dict(), "Alternative", round(float(scores[c_idx]), 2)))

            if len(complete_look) >= top_k and len(similar_styles) >= top_k:
                break

        return complete_look, similar_styles