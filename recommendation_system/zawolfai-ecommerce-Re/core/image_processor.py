import os
import base64

CATEGORY_FALLBACK_URLS = {
    'jacket': 'https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=300&q=80',
    'coat': 'https://images.unsplash.com/photo-1539533018447-63fcce667883?auto=format&fit=crop&w=300&q=80',
    'dress': 'https://images.unsplash.com/photo-1595777457583-95e059d581b8?auto=format&fit=crop&w=300&q=80',
    'trousers': 'https://images.unsplash.com/photo-1541099649105-f69ad21f3246?auto=format&fit=crop&w=300&q=80',
    'top': 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=300&q=80',
    'default': 'https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?auto=format&fit=crop&w=300&q=80'
}

class ImageProcessor:
    def __init__(self, images_dir: str = "data/images"):
        self.images_dir = images_dir

    def resolve_image_uri(self, product_id: int, category: str) -> str:
        # بنجرب نقرأ الاسم بصفر في الأول (10 أرقام) أو بدون صفر
        pid_padded = str(product_id).zfill(10)
        pid_raw = str(product_id)

        for ext in ['.jpg', '.jpeg', '.png']:
            for name in [pid_padded, pid_raw]:
                path = os.path.join(self.images_dir, f"{name}{ext}")
                if os.path.exists(path):
                    try:
                        with open(path, "rb") as f:
                            encoded = base64.b64encode(f.read()).decode('utf-8')
                            return f"data:image/jpeg;base64,{encoded}"
                    except Exception:
                        pass
        
        # لو ملقاش الصورة يحط الرابط البديل للقسم
        cat_lower = str(category).lower()
        for key, url in CATEGORY_FALLBACK_URLS.items():
            if key in cat_lower:
                return url
        return CATEGORY_FALLBACK_URLS['default']