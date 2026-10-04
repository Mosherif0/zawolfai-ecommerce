PRODUCTS = [

    {
        "id": "P001",
        "name": "Classic Product",
        "category": "Everyday",
        "price": 350,
        "stock": 18,
        "description": "منتج كلاسيكي مناسب للاستخدام اليومي بجودة عالية وتصميم مريح."
    },

    {
        "id": "P002",
        "name": "Premium Product",
        "category": "Premium",
        "price": 650,
        "stock": 7,
        "description": "إصدار بريميوم بخامات ممتازة وتشطيب عالي ومزايا إضافية."
    },

    {
        "id": "P003",
        "name": "Bundle Pack",
        "category": "Bundles",
        "price": 900,
        "stock": 12,
        "description": "باقة توفيرية تحتوي على 3 قطع أساسية بسعر مخفض ومناسب للميزانية."
    },

    {
        "id": "P004",
        "name": "Pro Ultra Product",
        "category": "Professional",
        "price": 1200,
        "stock": 5,
        "description": "منتج فئة احترافية متقدمة لأعلى أداء وتجربة استثنائية."
    },

    {
        "id": "P005",
        "name": "Basic T-Shirt",
        "category": "T-Shirts",
        "price": 300,
        "stock": 25,
        "description": "تيشيرت أساسي مريح للاستخدام اليومي، بتصميم بسيط وسهل التنسيق."
    },

    {
        "id": "P006",
        "name": "Oversized T-Shirt",
        "category": "T-Shirts",
        "price": 450,
        "stock": 14,
        "description": "تيشيرت Oversized بقصة واسعة ومريحة مناسب للـ casual looks."
    },

    {
        "id": "P007",
        "name": "Premium Cotton T-Shirt",
        "category": "T-Shirts",
        "price": 600,
        "stock": 9,
        "description": "تيشيرت بخامة قطن Premium ناعمة ومريحة ومناسب للاستخدام اليومي."
    },

    {
        "id": "P008",
        "name": "Graphic T-Shirt",
        "category": "T-Shirts",
        "price": 500,
        "stock": 11,
        "description": "تيشيرت بتصميم Graphic عصري ومناسب للشباب والـ casual outfits."
    },

    {
        "id": "P009",
        "name": "Sport T-Shirt",
        "category": "Sports",
        "price": 550,
        "stock": 16,
        "description": "تيشيرت رياضي خفيف ومريح ومناسب للتمرين والأنشطة اليومية."
    },

    {
        "id": "P010",
        "name": "Performance T-Shirt",
        "category": "Sports",
        "price": 750,
        "stock": 6,
        "description": "تيشيرت رياضي Performance بخامة مناسبة للحركة والتمارين عالية النشاط."
    },

    {
        "id": "P011",
        "name": "Classic Hoodie",
        "category": "Hoodies",
        "price": 850,
        "stock": 8,
        "description": "هودي كلاسيك مريح ومناسب للجو البارد والاستخدام اليومي."
    },

    {
        "id": "P012",
        "name": "Premium Hoodie",
        "category": "Hoodies",
        "price": 1100,
        "stock": 4,
        "description": "هودي Premium بخامة عالية الجودة وتصميم أنيق ومريح."
    },

    {
        "id": "P013",
        "name": "Classic Socks Pack",
        "category": "Socks",
        "price": 250,
        "stock": 30,
        "description": "باقة من الجوارب الكلاسيكية المناسبة للاستخدام اليومي."
    },

    {
        "id": "P014",
        "name": "Premium Socks Pack",
        "category": "Socks",
        "price": 400,
        "stock": 20,
        "description": "باقة جوارب Premium بخامات ناعمة وتصميم مريح للاستخدام اليومي."
    },

    {
        "id": "P015",
        "name": "Sports Socks Pack",
        "category": "Socks",
        "price": 350,
        "stock": 17,
        "description": "جوارب رياضية مريحة ومناسبة للجيم والجري والأنشطة الرياضية."
    },

    {
        "id": "P016",
        "name": "Everyday Cap",
        "category": "Accessories",
        "price": 280,
        "stock": 13,
        "description": "كاب بسيط وأنيق مناسب للاستخدام اليومي والـ casual outfits."
    },

    {
        "id": "P017",
        "name": "Premium Cap",
        "category": "Accessories",
        "price": 450,
        "stock": 8,
        "description": "كاب Premium بتصميم أنيق وخامة عالية الجودة."
    },

    {
        "id": "P018",
        "name": "T-Shirt & Socks Bundle",
        "category": "Bundles",
        "price": 650,
        "stock": 10,
        "description": "باقة تجمع بين تيشيرت أساسي وجوارب بسعر أفضل من شراء كل منتج بشكل منفصل."
    },

    {
        "id": "P019",
        "name": "Weekend Bundle",
        "category": "Bundles",
        "price": 1000,
        "stock": 7,
        "description": "باقة متكاملة للـ weekend تحتوي على تيشيرتين وجوارب وإكسسوار بسعر موحد."
    },

    {
        "id": "P020",
        "name": "Ultimate Collection",
        "category": "Premium Bundles",
        "price": 1500,
        "stock": 3,
        "description": "مجموعة Premium متكاملة تحتوي على عدة قطع متنوعة لتجربة تسوق كاملة."
    }

]


ORDERS = [

    {
        "order_id": "ORD-1001",
        "customer_name": "أحمد محمود",
        "status": "Shipped (تم الشحن مع مندوب التوصيل)",
        "items": ["Classic Product (P001) x 2"],
        "total": 700,
        "estimated_delivery": "غداً خلال الفترة المسائية (Tomorrow)"
    },

    {
        "order_id": "ORD-1002",
        "customer_name": "سارة علي",
        "status": "Processing (قيد التجهيز في المخزن)",
        "items": ["Bundle Pack (P003) x 1"],
        "total": 900,
        "estimated_delivery": "خلال يومين إلى 3 أيام عمل"
    },

    {
        "order_id": "ORD-1003",
        "customer_name": "محمد حسن",
        "status": "Delivered (تم الاستلام بنجاح)",
        "items": ["Premium Product (P002) x 1"],
        "total": 650,
        "estimated_delivery": "تم التوصيل أمس"
    }

]


POLICIES = {

    "return_window": "14 يوم من تاريخ استلام الطلب",

    "conditions": "المنتج يكون بحالته الأصلية وفي عبوته الأصلية غير مستخدم",

    "exchange": "الاستبدال مجاني في حالة وجود عيب صناعة أو خطأ في المقاس/المواصفات",

    "refund_method": "استرجاع المبلغ بنفس طريقة الدفع الأصلية أو كاش للمندوب خلال 3-5 أيام عمل"

}


SHIPPING_INFO = {

    "cairo_giza_fee": 40,

    "cairo_giza_delivery": "خلال 24 إلى 48 ساعة (1-2 يوم)",

    "other_governorates_fee": 60,

    "other_governorates_delivery": "خلال 2 إلى 4 أيام عمل",

    "free_shipping_threshold": 1000,

    "payment_methods": "الدفع عند الاستلام (COD)، بطاقات الائتمان (Visa / Mastercard)، محافظ إلكترونية (فودافون كاش ومثيلاتها)"

}


FAQS = [

    {
        "q": "هل في شحن مجاني؟",
        "a": "نعم، الشحن مجاني لأي طلب قيمته 1000 جنيه أو أكثر."
    },

    {
        "q": "إيه طرق الدفع المتاحة؟",
        "a": "كاش عند الاستلام، فيزا/ماستركارد، ومحافظ إلكترونية."
    },

    {
        "q": "هل ممكن أعاين المنتج قبل الاستلام؟",
        "a": "نعم، تقدر تفتح الشحنة وتتأكد منها مع مندوب التوصيل قبل الدفع."
    }

]


def get_business_context() -> str:
    """
    Converts mock business data into a compact context string for Gemini prompt.
    """

    products_text = "\n".join([
        f"- [{p['id']}] {p['name']} | تصنيف: {p['category']} | السعر: {p['price']} جنيه | المخزون المتاح: {p['stock']} | الوصف: {p['description']}"
        for p in PRODUCTS
    ])

    orders_text = "\n".join([
        f"- كود الطلب: {o['order_id']} | العميل: {o['customer_name']} | الحالة: {o['status']} | المنتجات: {', '.join(o['items'])} | الإجمالي: {o['total']} ج | موعد التوصيل: {o['estimated_delivery']}"
        for o in ORDERS
    ])

    policies_text = (
        f"- فترة الاسترجاع: {POLICIES['return_window']}\n"
        f"- الشروط: {POLICIES['conditions']}\n"
        f"- الاستبدال: {POLICIES['exchange']}\n"
        f"- طريقة الاسترداد: {POLICIES['refund_method']}"
    )

    shipping_text = (
        f"- شحن القاهرة والجيزة: {SHIPPING_INFO['cairo_giza_fee']} جنيه "
        f"(توصيل: {SHIPPING_INFO['cairo_giza_delivery']})\n"
        f"- شحن المحافظات: {SHIPPING_INFO['other_governorates_fee']} جنيه "
        f"(توصيل: {SHIPPING_INFO['other_governorates_delivery']})\n"
        f"- الشحن المجاني: متاح للطلبات من "
        f"{SHIPPING_INFO['free_shipping_threshold']} جنيه فأكثر.\n"
        f"- طرق الدفع: {SHIPPING_INFO['payment_methods']}"
    )

    faqs_text = "\n".join([
        f"- س: {f['q']}\n  ج: {f['a']}"
        for f in FAQS
    ])

    context = f"""
--- BUSINESS CONTEXT (بيانات العمل المتاحة في النظام) ---

المنتجات المتاحة (Products):

{products_text}

الطلبات الحالية (Orders):

{orders_text}

سياسات الاسترجاع والاستبدال (Policies):

{policies_text}

معلومات وتكاليف الشحن والتوصيل (Shipping & Payment):

{shipping_text}

الأسئلة الشائعة (FAQs):

{faqs_text}

-------------------------------------------------------
"""

    return context.strip()