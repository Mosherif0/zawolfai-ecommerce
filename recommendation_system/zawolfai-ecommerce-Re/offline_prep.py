import os
import pandas as pd
from core.text_processor import TextProcessor

# 1. التأكد من إنشاء مجلد الحفظ المعالج
os.makedirs("data/processed", exist_ok=True)

# 2. تحديد مسار الملف الخام
raw_products_path = "data/raw/Product_modified.csv"

# 3. التحقق من وجود الملف وبدء التنظيف
if os.path.exists(raw_products_path):
    print("--> [INFO] Cleaning and processing raw catalog...")
    df_raw = pd.read_csv(raw_products_path)
    
    # استدعاء دالة التنظيف وحذف الأقسام غير المناسبة
    clean_df = TextProcessor.clean_catalog(df_raw)
    
    # حفظ النسخة النظيفة للاستخدام من قبل السيرفر ومحرك التوصيات
    clean_path = "data/processed/clean_catalog.csv"
    clean_df.to_csv(clean_path, index=False)
    print(f"--> [SUCCESS] Clean catalog saved to '{clean_path}' ({len(clean_df):,} products).")
else:
    print(f"--> [ERROR] File not found: {raw_products_path}")
    print("--> [WARNING] Please ensure 'Product_modified.csv' is placed inside 'data/raw/'")