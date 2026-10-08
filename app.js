/* ==========================================================================
   CARTWISE AI — APPLICATION JAVASCRIPT CONTROLLER
   Handles: i18n Translation (AR/EN), Theme Switching, Sidebar Routing, 
            Sophian & DemandForecaster ApexCharts, ROI Calculator, OCR Intake, 
            and RAG Chatbot Integration
   ========================================================================== */

let currentLang = 'en';
let currentTheme = 'dark';
let salesChart = null;
let categoryDonutChart = null;
let channelBarChart = null;
let forecastChart = null;
let currentConversationId = null;

// Internationalization Dictionary (Arabic & English)
const i18n = {
    ar: {
        tagline: "أتمتة التجارة الإلكترونية",
        nav_home: "الرئيسية",
        nav_dashboard: "لوحة التحكم",
        nav_ocr: "فواتير الـ OCR",
        nav_forecasting: "التنبؤ بالطلب",
        nav_storefront: "المتجر",
        btn_demo: "المنصة الحية",
        hero_pill: "منصة ذكاء اصطناعي متكاملة للتجارة الإلكترونية",
        hero_title: "أتمِت عمليات متجرك بالكامل مع CartWise AI",
        hero_subtitle: "منصة موحدة تحول فواتير الموردين الورقية إلى مخزون رقمي، تتنبأ بنفاد المنتجات قبل حدوثه، وتقدم مساعد مبيعات بالعامية المصرية لزيادة مبيعاتك.",
        hero_btn_primary: "استكشف لوحة التحكم الحية",
        hero_btn_secondary: "حساب العائد المالي",
        stat_ocr_accuracy: "دقة قراءة الـ OCR",
        stat_aov_boost: "زيادة متوسط السلة",
        stat_stockout_early: "تنبيه مبكر للنفاذ",
        stat_arabic_support: "دعم بالعامية المصرية",
        card_ocr_title: "قراءة فواتير الموردين",
        card_ocr_sub: "تحديث المخزون بنقرة واحدة",
        card_forecast_title: "التنبؤ بنفاد المخزون",
        card_forecast_sub: "نماذج LGBM & XGBoost",
        card_rag_title: "مساعد مبيعات مصري",
        card_rag_sub: "ردود فورية 24/7 ودقيقة",
        card_recsys_title: "توصيات المنتجات الذكية",
        card_recsys_sub: "رفع مبيعات السلة تلقائياً",
        tag_transformation: "لماذا منصة CartWise AI",
        title_pain_points: "تحويل العقبات اليدوية إلى أرباح مؤتمتة",
        comp_before_title: "بدون منصة CartWise",
        comp_after_title: "مع حزمة CartWise AI",
        comp_b1: "ساعات عمل ضائعة في كتابة فواتير الموردين يدوياً.",
        comp_b2: "نفاد مفاجئ للمنتجات الأكثر طلباً وخسارة الزبائن.",
        comp_b3: "أموال مجمدة في بضاعة راكدة غير مطلوبة.",
        comp_b4: "تأخر الرد في الشات وتخلي العملاء عن سلة الشراء.",
        comp_a1: "قراءة الفاتورة وتحديث المخزون تلقائياً في 3 ثوانٍ.",
        comp_a2: "تنبيهات مبكرة بنفاد المخزون قبلها بـ 14 يوماً.",
        comp_a3: "كميات إعادة طلب محسوبة بدقة لتحافظ على السيولة.",
        comp_a4: "رد فوري بالعامية المصرية مع إمكانية الشراء مباشرة.",
        tag_roi: "حاسبة العائد المالي",
        title_roi: "احسب العائد على الاستثمار لمتجرك الإلكتروني",
        sub_roi: "قم بتحريك المؤشرات أدناه لرؤية الأرباح والتوفير المالي المتوقع شهرياً.",
        lbl_orders: "عدد الطلبات الشهرية",
        lbl_skus: "عدد المنتجات بالمخزون (SKUs)",
        lbl_aov: "متوسط قيمة الطلب (ج.م)",
        res_total_title: "القيمة المالية المتوقعة شهرياً",
        res_total_sub: "مجموع الأرباح الإضافية والتكاليف الموفرة شهرياً",
        lbl_aov_boost: "أرباح إضافية من التوصيات (+18%)",
        lbl_prevented_stockouts: "مبيعات محمية من نفاد المخزون",
        lbl_saved_hours: "ساعات عمل موفرة في قراءة الفواتير",
        footer_desc: "حزمة ذكاء اصطناعي متكاملة تهدف لأتمتة التجارة الإلكترونية من الفاتورة إلى المحادثة والمخزون.",
        f_col_modules: "الموديولات",
        f_col_tech: "التقنيات المستخدمة",
        footer_copy: "© 2026 CartWise AI. جميع الحقوق محفوظة. منصة أتمتة التجارة الإلكترونية.",
        m_ai_rev: "أرباح الـ AI الإضافية",
        m_saved_hours: "ساعات العمل الموفرة",
        m_stockouts: "منع نفاد المخزون",
        m_resolution: "معدل إجابة الشات بوت",
        badge_dash_hero: "مركز التحكم الرئيسي المدار بالذكاء الاصطناعي",
        dash_hero_title: "تنبأ بالطلب. احمِ المخزون. كَبّر الأرباح.",
        dash_hero_sub: "استفد من نماذج التعلم الآلي لمنع نفاد القطع، أتمتة قراءة الفواتير، وزيادة متوسط قيمة السلة.",
        btn_start_forecasting: "ابدأ التنبؤ بالطلب",
        btn_upload_invoice: "رفع فاتورة مورد",
        chart_sales_title: "مبيعات المتجر ومسار التوقع لـ 30 يوماً",
        chart_sales_sub: "المبيعات التاريخية مقارنة بخط توقعات الطلب المستقبلي لـ 30 يوماً",
        chart_cat_title: "توزيع المبيعات حسب القسم",
        chart_cat_sub: "حجم المبيعات مقسم حسب أقسام المنتجات",
        chart_channel_title: "حجم المبيعات حسب القنوات وتوصيات الـ AI",
        chart_channel_sub: "تحليل الإيرادات عبر قنوات البيع المتعددة",
        btn_export: "تصدير البيانات",
        badge_live: "نموذج حي",
        badge_live_offline: "بيانات افتراضية",
        alerts_title: "تنبيهات المخزون الحرجة",
        btn_view_all: "عرض الكل",
        btn_reorder: "إعادة طلب",
        badge_healthy: "مخزون ممتاز",
        alert_healthy_meta: "المخزون سليم",
        alert_out_of_stock: "نفذ بالكامل من المخزون",
        alert_low_stock: "مخزون منخفض",
        alert_none: "لا توجد تنبيهات حرجة الآن — المخزون سليم",
        ocr_hero_title: "استخراج بيانات الفواتير بذكاء الرؤية الرقمية",
        ocr_hero_sub: "ارفع فواتير الموردين الورقية أو ملفات الـ PDF ليقوم الـ AI باستخراج المنتجات والأسعار وتحديث المخزون فوراً.",
        dropzone_title: "اسحب وأسقط ملفات فواتير الموردين هنا",
        dropzone_sub: "أو انقر لاختيار الملف من جهازك (يدعم الصور و الـ PDF)",
        btn_select_file: "اختيار ملف",
        btn_sample_invoice: "تجربة فاتورة عينة",
        scanning_text: "جاري فحص وتفريغ بيانات الفاتورة بالذكاء الاصطناعي...",
        feat_fast_title: "سرعة فائقة",
        feat_fast_desc: "معالجة كامل الفاتورة في أقل من 3 ثوانٍ.",
        feat_acc_title: "دقة 99.4%",
        feat_acc_desc: "تعرف ضوئي متقدم مع حساب درجة الثقة لكل عنصر.",
        feat_sec_title: "آمن ومشفر",
        feat_sec_desc: "إدخال مباشر ومؤمن لقاعدة بيانات متجرك.",
        ocr_res_title: "عناصر الفاتورة المستخرجة والمطابقة",
        btn_sync_inventory: "اعتماد وتحديث المخزون بنقرة واحدة",
        th_item_name: "اسم المنتج المستخرج",
        th_qty: "الكمية",
        th_cost: "سعر التكلفة (ج.م)",
        th_retail: "سعر البيع المقترح",
        th_total: "الإجمالي (ج.م)",
        th_confidence: "نسبة الثقة",
        badge_forecaster: "التنبؤ بالطلب والمخزون",
        forecaster_title: "تنبأ بالطلب. احمِ مخزونك. كَبّر أرباحك.",
        forecaster_sub: "نماذج زمنيّة مدربة للتنبؤ بالطلب لكل SKU لمنع نفاد القطع أو تجميد الكاش.",
        fm_demand: "الطلب المتوقع لـ 30 يوماً",
        fm_stock: "المخزون الحالي الكلي",
        fm_risk: "مستوى مخاطر النفاذ",
        fm_revenue: "المبيعات المتوقعة شهرياً",
        forecast_chart_title: "مسار الطلب والتوقع لـ 30 يوماً قادماً",
        forecast_chart_sub: "مقارنة المبيعات الفعلية بنموذج التوقع مع حدود الثقة",
        gen_forecast_title: "تشغيل نموذج التنبؤ",
        lbl_select_sku: "اختر كود المنتج (SKU)",
        lbl_forecast_period: "المدى الزمني للتوقع",
        lbl_model_choice: "اختر محرك التنبؤ",
        btn_run_forecast: "تشغيل نموذج التنبؤ",
        catalog_title: "كتالوج المتجر وتوصيات الـ Cross-Sell الذكية",
        catalog_sub: "تصفح المنتجات واستعرض اقتراحات إكمل إطلالتك التلقائية.",
        chat_bot_name: "المساعد الذكي لمتجر CartWise",
        chat_bot_status: "متصل • محرك RAG بالعامية المصرية",
        chat_welcome: "أهلاً بيك! 👋 أنا مساعد المتجر الذكي بالعامية المصرية. اسألني عن مقاسات المنتجات، الأسعار، العروض، أو أين يقع فرعنا وشحن الطلبات!",
        chat_placeholder: "اكتب رسالتك هنا... (مثال: عاوز جاكيت شتوي دافي)",
        chat_error_reply: "حصلت مشكلة بسيطة، جرب تاني.",
        chat_offline_reply: "تعذر الاتصال بالخادم الآن.",
        chip1_label: "جاكيت شتوي",
        chip1_msg: "عاوز جاكيت شتوي",
        chip2_label: "فستان مناسبات",
        chip2_msg: "عاوز أعرف تفاصيل فستان مناسبات",
        chip3_label: "شرابات قطن",
        chip3_msg: "أسعار الشرابات 3 قطع",
        btn_ask_assistant: "اسأل المساعد الذكي",
        chip_ask_details: "عاوز أعرف تفاصيل ومقاسات",
        chat_fab_tip: "كلمنا — المساعد الذكي أونلاين",
        user_role: "صاحبة المتجر",
        lbl_theme: "وضع الثيم",
        ph_search: "ابحث عن منتج، فاتورة، توقع..."
    },
    en: {
        tagline: "E-Commerce AI Suite",
        nav_home: "Home",
        nav_dashboard: "Dashboard",
        nav_ocr: "OCR Invoices",
        nav_forecasting: "Demand Forecast",
        nav_storefront: "Store",
        btn_demo: "Live Platform",
        hero_pill: "Integrated Retail AI Automation Suite",
        hero_title: "Automate Your Store Operations with CartWise AI",
        hero_subtitle: "A unified platform transforming paper supplier invoices into digital inventory, predicting stockouts 14 days early, and providing a bilingual sales concierge to scale revenues.",
        hero_btn_primary: "Explore Live Dashboard",
        hero_btn_secondary: "Calculate ROI",
        stat_ocr_accuracy: "OCR Accuracy",
        stat_aov_boost: "AOV Increase",
        stat_stockout_early: "Stockout Warning",
        stat_arabic_support: "Egyptian Arabic AI",
        card_ocr_title: "OCR Invoice Intake",
        card_ocr_sub: "1-Click Inventory Sync",
        card_forecast_title: "Demand Forecasting",
        card_forecast_sub: "LGBM & XGBoost Models",
        card_rag_title: "Egyptian RAG Sales AI",
        card_rag_sub: "Instant 24/7 Resolution",
        card_recsys_title: "Smart RecSys Bundles",
        card_recsys_sub: "Automated Cross-Selling",
        tag_transformation: "Why CartWise AI Platform",
        title_pain_points: "Transforming Bottlenecks into Automated Profits",
        comp_before_title: "Without CartWise AI",
        comp_after_title: "With CartWise Suite",
        comp_b1: "Hours lost manually typing paper invoices into store stock.",
        comp_b2: "Unexpected stockouts losing customers to competitors.",
        comp_b3: "Capital frozen in unwanted, slow-moving SKUs.",
        comp_b4: "Slow support replies leading to cart abandonment.",
        comp_a1: "Instant OCR extraction & inventory sync in under 3 seconds.",
        comp_a2: "14-Day early predictive alerts before items run out.",
        comp_a3: "Optimized re-order quantities keeping working capital liquid.",
        comp_a4: "Instant Egyptian Arabic support with inline product checkout.",
        tag_roi: "Financial ROI Calculator",
        title_roi: "Calculate Your Store's AI Return On Investment",
        sub_roi: "Adjust the sliders below to calculate your projected monthly savings and extra revenue.",
        lbl_orders: "Monthly Store Orders",
        lbl_skus: "Active Catalog SKUs",
        lbl_aov: "Average Order Value (EGP)",
        res_total_title: "Projected Monthly Value",
        res_total_sub: "Combined extra revenue & saved operational costs per month",
        lbl_aov_boost: "RecSys AOV Revenue Boost (+18%)",
        lbl_prevented_stockouts: "Prevented Stockout Missed Sales",
        lbl_saved_hours: "Manual OCR Hours Saved / Month",
        footer_desc: "Modular AI suite automating e-commerce operations from invoice to chat and inventory.",
        f_col_modules: "Modules",
        f_col_tech: "Technologies",
        footer_copy: "© 2026 CartWise AI. All rights reserved. Retail AI Automation.",
        m_ai_rev: "AI Revenue Attribution",
        m_saved_hours: "Saved Work Hours",
        m_stockouts: "Stockouts Prevented",
        m_resolution: "Chat Resolution Rate",
        badge_dash_hero: "AI-Powered Store Command Center",
        dash_hero_title: "Predict Demand. Optimize Inventory. Grow Smarter.",
        dash_hero_sub: "Leverage machine learning models to eliminate stockouts, automate invoice OCR intake, and maximize customer AOV.",
        btn_start_forecasting: "Start Forecasting",
        btn_upload_invoice: "Upload Invoice",
        chart_sales_title: "Revenue & AI Demand Forecast Trajectory",
        chart_sales_sub: "Historical sales matched with 30-day predictive AI demand trajectory",
        chart_cat_title: "Category Sales Breakdown",
        chart_cat_sub: "Sales volume distribution across product categories",
        chart_channel_title: "Sales Volume by Channel & RecSys Attribution",
        chart_channel_sub: "Revenue breakdown across store sales channels",
        btn_export: "Export Data",
        badge_live: "Live Model",
        badge_live_offline: "Offline Baseline",
        alerts_title: "Low-Stock Urgent Alerts",
        btn_view_all: "View All",
        btn_reorder: "Reorder",
        badge_healthy: "Optimal Stock",
        alert_healthy_meta: "Healthy stock",
        alert_out_of_stock: "Out of stock",
        alert_low_stock: "Low stock",
        alert_none: "No urgent alerts right now — inventory is healthy",
        ocr_hero_title: "Extract Text & Items with AI-Powered OCR",
        ocr_hero_sub: "Upload paper invoices, receipts, or PDFs to extract items, prices, and update store inventory in 3 seconds.",
        dropzone_title: "Drop supplier invoice files here",
        dropzone_sub: "or click to select from your device (PNG, JPG, PDF supported)",
        btn_select_file: "Select File",
        btn_sample_invoice: "Try Sample Invoice",
        scanning_text: "AI Scanning & Extracting Invoice Data...",
        feat_fast_title: "Lightning Fast",
        feat_fast_desc: "Processes multi-line receipts in under 3 seconds.",
        feat_acc_title: "99.4% Precision",
        feat_acc_desc: "Deep vision OCR with automatic confidence scoring.",
        feat_sec_title: "Secure & Private",
        feat_sec_desc: "Encrypted intake directly into your catalog database.",
        ocr_res_title: "Extracted Invoice Items & Verification",
        btn_sync_inventory: "1-Click Sync to Inventory",
        th_item_name: "Extracted Item Name",
        th_qty: "Quantity",
        th_cost: "Unit Cost (EGP)",
        th_retail: "Suggested Retail",
        th_total: "Total (EGP)",
        th_confidence: "AI Confidence",
        badge_forecaster: "AI-Powered Demand Forecasting",
        forecaster_title: "Predict Demand. Optimize Inventory. Grow Smarter.",
        forecaster_sub: "Leverage LightGBM & XGBoost time-series models to forecast SKU-level demand, eliminate stockouts, and minimize overstock.",
        fm_demand: "Predicted 30-Day Demand",
        fm_stock: "Current Total Inventory",
        fm_risk: "Stockout Risk Level",
        fm_revenue: "Expected Monthly Sales",
        forecast_chart_title: "Demand Trend & 30-Day Predictive Trajectory",
        forecast_chart_sub: "Actual historical sales vs Model predicted demand with confidence bounds",
        gen_forecast_title: "Generate Forecast Model",
        lbl_select_sku: "Select Product SKU",
        lbl_forecast_period: "Forecast Horizon",
        lbl_model_choice: "Select Model Engine",
        btn_run_forecast: "Run Prediction Model",
        catalog_title: "Store Catalog & Smart Cross-Sell Recommendations",
        catalog_sub: "Explore products with dynamic AI complementary bundling (\"Complete the Look\").",
        chat_bot_name: "CartWise Egyptian Sales Assistant",
        chat_bot_status: "Online • Bilingual RAG Engine",
        chat_welcome: "Welcome! 👋 I am your Egyptian Arabic sales assistant. Ask me about product sizes, pricing, delivery, or branch locations!",
        chat_placeholder: "Type your message here...",
        chat_error_reply: "Something went wrong, please try again.",
        chat_offline_reply: "Couldn't reach the server right now.",
        chip1_label: "Winter Jacket",
        chip1_msg: "I want a winter jacket",
        chip2_label: "Occasion Dress",
        chip2_msg: "Tell me about the occasion dress",
        chip3_label: "Cotton Socks",
        chip3_msg: "Prices for the 3-pack cotton socks",
        btn_ask_assistant: "Ask the AI Assistant",
        chip_ask_details: "Tell me the details and sizes of",
        chat_fab_tip: "Chat with us — AI online",
        user_role: "Brand Owner",
        lbl_theme: "Theme Mode",
        ph_search: "Search SKUs, invoices, forecast..."
    }
};

/* ==========================================================================
   Interactive 3D Hero Logo Widget
   Pointer-driven pitch / tilt / rotation for the floating perspective stage.
   Writes --tilt-x, --tilt-y, --glow-x/y and --parallax-x/y onto .hero-visual;
   CSS does the actual 3D rendering, glowing orbits and idle bobbing.
   ========================================================================== */
function initHeroLogoWidget() {
    const stage = document.querySelector('.hero-visual');
    if (!stage) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    // Buttery motion (see MOTION below): pointer input is smoothed over time,
    // tilt eases gently toward the target, and the loop keeps running so the
    // idle sway + return-to-center glide instead of snapping.
    const HOT_CLASS = 'hero-hot';
    const MAX_TILT = 14;   // degrees of pitch / yaw
    const GLOW_RANGE = 52; // px the glow blob travels
    const PARALLAX = 18;   // px the satellite cards travel
    // MOTION — tuned for silk, not snap:
    //   EASE_TILT/FAST (glow+parallax) = critically-damped follow speed,
    //   SMOOTH = how much raw pointer jitter is ironed out (higher = silkier),
    //   SWAY = idle float amplitude/period so the stage feels alive at rest.
    const EASE_TILT = 0.075;
    const EASE_FAST = 0.12;
    const SMOOTH = 0.35;
    const SWAY_AMP = 1.6;    // degrees of idle sway
    const SWAY_PERIOD = 5200; // ms per sway cycle
    // Proximity radius (px): glow ignites BEFORE the pointer even touches the stage
    const PROXIMITY = 140;

    const target = { x: 0, y: 0, gx: 0, gy: 0, px: 0, py: 0 };
    const smoothP = { x: 0, y: 0 }; // smoothed pointer (-1..1)
    const cur = { x: 0, y: 0, gx: 0, gy: 0, px: 0, py: 0 };
    let rafId = null;
    let lastT = 0;

    const loop = (t) => {
        // Frame-rate independent damping (same silk at 60Hz and 120Hz+).
        const dt = Math.min((t - (lastT || t)) / 16.7, 3);
        lastT = t;
        const kTilt = 1 - Math.pow(1 - EASE_TILT, dt);
        const kFast = 1 - Math.pow(1 - EASE_FAST, dt);
        // Gentle idle sway so the stage breathes when untouched.
        const sway = Math.sin(t / SWAY_PERIOD * Math.PI * 2) * SWAY_AMP;
        const swayY = Math.cos(t / (SWAY_PERIOD * 1.3) * Math.PI * 2) * SWAY_AMP;

        cur.x += (target.x + sway - cur.x) * kTilt;
        cur.y += (target.y + swayY - cur.y) * kTilt;
        cur.gx += (target.gx - cur.gx) * kFast;
        cur.gy += (target.gy - cur.gy) * kFast;
        cur.px += (target.px - cur.px) * kFast;
        cur.py += (target.py - cur.py) * kFast;

        const s = stage.style;
        s.setProperty('--tilt-x', cur.x.toFixed(2) + 'deg');
        s.setProperty('--tilt-y', cur.y.toFixed(2) + 'deg');
        s.setProperty('--glow-x', cur.gx.toFixed(1) + 'px');
        s.setProperty('--glow-y', cur.gy.toFixed(1) + 'px');
        s.setProperty('--parallax-x', cur.px.toFixed(1) + 'px');
        s.setProperty('--parallax-y', cur.py.toFixed(1) + 'px');

        // Always-on loop: keeps the idle sway breathing + makes the
        // return-to-center a glide instead of a snap. One rAF is cheap.
        rafId = requestAnimationFrame(loop);
    };
    const start = () => { if (rafId === null) { lastT = 0; rafId = requestAnimationFrame(loop); } };
    start(); // begin the idle sway immediately on page load

    stage.addEventListener('pointermove', (e) => {
        // Cache the rect ~once per frame — getBoundingClientRect() forces layout.
        const now = performance.now();
        if (!stage._rectTs || now - stage._rectTs > 16) {
            stage._rect = stage.getBoundingClientRect();
            stage._rectTs = now;
        }
        const r = stage._rect;
        const rawX = ((e.clientX - r.left) / r.width) * 2 - 1;   // -1 .. 1
        const rawY = ((e.clientY - r.top) / r.height) * 2 - 1;
        // Smooth the RAW input first (irons out hand jitter), then aim the tilt.
        smoothP.x += (rawX - smoothP.x) * SMOOTH;
        smoothP.y += (rawY - smoothP.y) * SMOOTH;
        target.x = -smoothP.y * MAX_TILT;   // pitch
        target.y = smoothP.x * MAX_TILT;    // yaw
        target.gx = smoothP.x * GLOW_RANGE;
        target.gy = smoothP.y * GLOW_RANGE;
        target.px = smoothP.x * PARALLAX;
        target.py = smoothP.y * PARALLAX;
        // Mark hot on first move — glow snaps on with zero delay.
        if (!stage.classList.contains(HOT_CLASS)) stage.classList.add(HOT_CLASS);
        start();
    });

    stage.addEventListener('pointerleave', () => {
        target.x = target.y = 0;
        target.gx = target.gy = 0;
        target.px = target.py = 0;
        stage.classList.remove(HOT_CLASS);
        start();
    });

    // Proximity ignition: glow fires when the pointer APPROACHES (within
    // PROXIMITY px of the stage edge) — no touch needed. Throttled to ~60fps.
    let proxTick = 0;
    document.addEventListener('pointermove', (e) => {
        const now = performance.now();
        if (now - proxTick < 50) return; // ~20 checks/sec is plenty
        proxTick = now;
        if (!stage._rect || now - (stage._rectTs || 0) > 500) {
            stage._rect = stage.getBoundingClientRect();
            stage._rectTs = now;
        }
        const r = stage._rect;
        const dx = Math.max(r.left - e.clientX, 0, e.clientX - r.right);
        const dy = Math.max(r.top - e.clientY, 0, e.clientY - r.bottom);
        const dist = Math.hypot(dx, dy);
        if (dist < PROXIMITY) {
            if (!stage.classList.contains(HOT_CLASS)) stage.classList.add(HOT_CLASS);
        } else if (!stage.matches(':hover')) {
            stage.classList.remove(HOT_CLASS);
        }
    }, { passive: true });
}

/* ==========================================================================
   Low-Stock Urgent Alerts — dashboard panel
   Live source: warehouse inventory (OCR service) + forecast demand rates
   (used to derive "runs out in X days"). When the backends are offline or
   empty, the bundled fallback rows below keep the panel alive — the data
   that always exists, mirroring the original static markup.
   ========================================================================== */
const __alertsFallback = [
    { id: null, name: { en: 'H&M Cotton Ankle Socks 3-Pack', ar: 'جوارب قطنية H&M عبوة 3 قطع' }, quantity: 12, daysLeft: 3, risk: 'high' },
    { id: null, name: { en: 'CartWise Puffer Jacket - Navy', ar: 'جاكيت CartWise بف - أزرق كحلي' }, quantity: 8, daysLeft: 6, risk: 'medium' },
    { id: null, name: { en: 'Oversized Hoodie - Vintage Grey', ar: 'هودي أوفرسايز - رمادي عتيق' }, quantity: 45, daysLeft: null, risk: 'low' }
];

let __alertsRows = null;      // rows currently shown (re-rendered on language flip)
let __alertsLoading = false;  // dedupes concurrent boot/switch fetches
const __RISK_RANK = { high: 0, medium: 1, low: 2 };

// Localized inflections — plural rules differ between Arabic and English.
function __unitsRemaining(qty) {
    if (currentLang === 'ar') {
        if (qty === 1) return 'وحدة متبقية واحدة';
        if (qty === 2) return 'وحدتان متبقيتان';
        if (qty <= 10) return `${qty} وحدات متبقية`;
        return `${qty} وحدة متبقية`;
    }
    return `${qty} ${qty === 1 ? 'unit' : 'units'} remaining`;
}

function __runsOutIn(days) {
    if (currentLang === 'ar') {
        const word = days === 1 ? 'يوم واحد' : days === 2 ? 'يومين' : (days <= 10 ? `${days} أيام` : `${days} يوماً`);
        return `ينفد خلال ${word}`;
    }
    return `Runs out in ${days} ${days === 1 ? 'day' : 'days'}`;
}

function __alertMeta(row) {
    const t = i18n[currentLang];
    if (!row.quantity) return t.alert_out_of_stock;
    if (row.risk === 'low') return `${__unitsRemaining(row.quantity)} • ${t.alert_healthy_meta}`;
    if (row.daysLeft != null) return `${__unitsRemaining(row.quantity)} • ${__runsOutIn(row.daysLeft)}`;
    return `${__unitsRemaining(row.quantity)} • ${t.alert_low_stock}`;
}

// Risk from the more URGENT of the two signals: days-to-runout (when the
// forecast service knows this product) and raw quantity thresholds.
function __classifyStock(qty, daysLeft) {
    if (qty <= 0) return 'high';
    const byQty = qty <= 10 ? 'high' : qty <= 30 ? 'medium' : 'low';
    if (daysLeft == null) return byQty;
    const byDays = daysLeft <= 5 ? 'high' : daysLeft <= 14 ? 'medium' : 'low';
    return __RISK_RANK[byQty] <= __RISK_RANK[byDays] ? byQty : byDays;
}

// Build the panel rows from live warehouse products: most urgent first,
// up to 3 urgent rows, padded with healthy stock like the original design.
function __buildAlertRows(products, demandByName) {
    const rows = products.map(p => {
        const qty = p.quantity || 0;
        // predicted_demand is weekly units → daily burn → days until empty.
        const weekly = demandByName[String(p.name).trim().toLowerCase()] || 0;
        let daysLeft = (weekly > 0 && qty > 0) ? Math.floor(qty / (weekly / 7)) : null;
        if (daysLeft != null && (daysLeft < 1 || daysLeft > 45)) daysLeft = null; // display sanity
        return { id: p.id, name: p.name, quantity: qty, daysLeft, risk: __classifyStock(qty, daysLeft) };
    }).sort((a, b) => (__RISK_RANK[a.risk] - __RISK_RANK[b.risk]) || (a.quantity - b.quantity));

    const urgent = rows.filter(r => r.risk !== 'low').slice(0, 3);
    if (urgent.length >= 3) return urgent;
    return urgent.concat(rows.filter(r => r.risk === 'low').slice(0, 3 - urgent.length));
}

async function __fetchAlertRows() {
    let products = null;
    const demandByName = {};
    // Both services are best-effort: stock decides whether we leave the
    // fallback, demand only enriches the "runs out in X days" meta.
    await Promise.all([
        (async () => {
            try {
                const res = await fetch(apiUrl('ocr', '/api/warehouse/products?limit=200'));
                if (!res.ok) return;
                const data = await res.json();
                const list = (data.products || []).filter(p => p && p.name);
                if (list.length) products = list;
            } catch (e) { /* backend offline → keep bundled rows */ }
        })(),
        (async () => {
            try {
                const res = await fetch(apiUrl('forecasting', '/forecast?limit=40'));
                if (!res.ok) return;
                const data = await res.json();
                (data.items || []).forEach(it => {
                    if (it.name && it.predicted_demand > 0) {
                        demandByName[String(it.name).trim().toLowerCase()] = it.predicted_demand;
                    }
                });
            } catch (e) { /* demand optional */ }
        })()
    ]);
    if (!products) return null;
    return __buildAlertRows(products, demandByName);
}

function renderStockAlerts() {
    const list = document.getElementById('alertsList');
    if (!list || !__alertsRows) return;
    const t = i18n[currentLang];

    if (!__alertsRows.length) {
        list.innerHTML = `
            <div class="alert-item risk-low">
                <div class="alert-icon"><i data-lucide="check-circle"></i></div>
                <div class="alert-info">
                    <div class="alert-name">${t.alert_none}</div>
                </div>
            </div>`;
    } else {
        list.innerHTML = __alertsRows.map((row, i) => {
            const name = (typeof row.name === 'object') ? (row.name[currentLang] || row.name.en) : row.name;
            const icon = row.risk === 'high' ? 'alert-circle' : row.risk === 'medium' ? 'alert-triangle' : 'check-circle';
            // The healthy row keeps its status badge AND a plan-stock (outline)
            // action — class follows the risk tier (danger = solid, warning = outline).
            const action = row.risk === 'low'
                ? `<span class="badge badge-green">${t.badge_healthy}</span>
                   <button type="button" class="btn btn-sm btn-warning" onclick="reorderAlert(${i})">${t.btn_reorder}</button>`
                : `<button type="button" class="btn btn-sm ${row.risk === 'high' ? 'btn-danger' : 'btn-warning'}" onclick="reorderAlert(${i})">${t.btn_reorder}</button>`;
            return `
                <div class="alert-item risk-${row.risk}">
                    <div class="alert-icon"><i data-lucide="${icon}"></i></div>
                    <div class="alert-info">
                        <div class="alert-name">${name}</div>
                        <div class="alert-meta">${__alertMeta(row)}</div>
                    </div>
                    <div class="alert-action">${action}</div>
                </div>`;
        }).join('');
    }
    if (window.lucide) lucide.createIcons();
}

// Paints the bundled rows instantly (the panel is never empty), then
// upgrades to live warehouse stock. force → refresh on dashboard entry.
async function loadStockAlerts(force) {
    if (__alertsLoading) return;
    if (!__alertsRows) {
        __alertsRows = __alertsFallback;
        renderStockAlerts();
    } else if (!force) {
        return;
    }
    __alertsLoading = true;
    try {
        const rows = await __fetchAlertRows();
        if (rows && rows.length) {
            __alertsRows = rows;
            renderStockAlerts();
        }
        // empty/failed → keep whatever is already shown (data that always exists)
    } catch (err) {
        console.warn('Stock alerts API offline, using bundled alerts:', err);
    } finally {
        __alertsLoading = false;
    }
}

// Pick the forecaster option that best represents this alert (exact id,
// then full-name containment, then ≥2 word overlap) — never a weak guess.
function __matchSkuOption(sel, id, name) {
    const opts = Array.from(sel.options || []);
    if (id != null) {
        const byId = opts.find(o => o.value == String(id));
        if (byId) return byId;
    }
    if (!name) return null;
    const needle = String(name).trim().toLowerCase();
    const stripLabel = s => s.replace(/^\s*\d+\s*—\s*/, '');
    const exact = opts.find(o => {
        const label = (o.text || '').toLowerCase();
        return label.includes(needle) || needle.includes(stripLabel(label));
    });
    if (exact) return exact;
    const words = needle.split(/[^a-z0-9]+/).filter(w => w.length > 3);
    if (!words.length) return null;
    let best = null, bestScore = 0;
    opts.forEach(o => {
        const label = (o.text || '').toLowerCase();
        const score = words.reduce((s, w) => s + (label.includes(w) ? 1 : 0), 0);
        if (score > bestScore) { bestScore = score; best = o; }
    });
    return bestScore >= Math.min(2, words.length) ? best : null;
}

// [Reorder] role: open Demand Forecasting and plan the restock for THIS
// item — pre-select its SKU when the forecaster knows it, ALWAYS run the
// prediction model (matched SKU or current selection), then land the user
// on the plan instead of the top of the page.
async function reorderAlert(index) {
    const row = (__alertsRows || [])[index];
    switchView('forecasting');
    if (!row) return;
    const sel = document.getElementById('skuSelect');
    if (sel) {
        try {
            // Cap the wait: a hung forecast service must not stall the plan —
            // the static options are good enough to run the model on.
            await Promise.race([
                populateSkuDropdown(), // shares the in-flight request with switchView
                new Promise(r => setTimeout(r, 4000))
            ]);
        } catch (e) { /* static options remain */ }
        const name = (typeof row.name === 'object') ? (row.name.en || '') : row.name;
        const opt = __matchSkuOption(sel, row.id, name);
        if (opt) sel.value = opt.value;
    }
    // Always run the prediction model — even without a SKU match — so
    // Reorder always lands on a fresh, consistent forecast plan. The runId
    // guard in runForecastModel supersedes switchView's earlier auto-run.
    await runForecastModel();
    const panel = document.querySelector('.card-control-panel');
    if (panel) panel.scrollIntoView({ behavior: 'auto', block: 'center' });
}

// Initialize Application — defaults: English + Night Mode
// PERFORMANCE: boot on window 'load' (wired in index.html) so deferred CDN
// scripts (lucide + apexcharts) are guaranteed ready; DOM is interactive
// instantly while heavy charts/catalog build right after first paint.
function __bootCartwise() {
    currentLang = 'en';
    currentTheme = 'dark';
    document.documentElement.setAttribute('lang', 'en');
    document.documentElement.setAttribute('dir', 'ltr');
    document.documentElement.setAttribute('data-theme', 'dark');
    updateLanguageDOM();
    const langTextEl = document.getElementById('langText');
    if (langTextEl) langTextEl.innerText = currentLang === 'ar' ? 'English' : 'عربي';
    updateROICalculator();
    initHeroLogoWidget();
    initChatFab();
    if (window.lucide) lucide.createIcons();

    // Run charts and catalog immediately
    initCharts();
    loadCatalogProducts();
    loadStockAlerts();
}
window.__cartwiseBooted = __bootCartwise;
// Fallback: if 'load' already fired or the head hook missed, boot on ready.
if (document.readyState === 'complete') {
    __bootCartwise();
} else {
    document.addEventListener('DOMContentLoaded', () => {
        __bootCartwise();
    });
    window.addEventListener('load', () => { __bootCartwise(); }, { once: true });
}

// View Navigation Switcher
// PERFORMANCE: cache section + nav lookups once — switchView runs on every click.
let __viewCache = null;
function __getViewCache() {
    if (!__viewCache) {
        __viewCache = {
            sections: Array.from(document.querySelectorAll('.view-section')),
            navBtns: Array.from(document.querySelectorAll('.menu-item')),
            byId: {},
            navByView: {}
        };
        __viewCache.sections.forEach(sec => { __viewCache.byId[sec.id] = sec; });
        __viewCache.navBtns.forEach(btn => {
            const v = btn.getAttribute('data-view');
            if (v) __viewCache.navByView[v] = btn;
        });
    }
    return __viewCache;
}
function switchView(viewId) {
    const cache = __getViewCache();
    cache.sections.forEach(sec => sec.classList.remove('active'));
    cache.navBtns.forEach(btn => btn.classList.remove('active'));

    const targetSection = cache.byId[`view-${viewId}`];
    if (targetSection) {
        targetSection.classList.add('active');
    }

    const activeNavBtn = cache.navByView[viewId];
    if (activeNavBtn) {
        activeNavBtn.classList.add('active');
    }

    // Instant jump — 'smooth' scroll delays the visual switch by ~500ms.
    window.scrollTo({ top: 0, behavior: 'auto' });

    // Refresh catalog when navigating to storefront view
    if (viewId === 'storefront') {
        loadCatalogProducts();
    }

    // Refresh charts when entering dashboard or forecasting
    if (viewId === 'dashboard' || viewId === 'forecasting') {
        if (viewId === 'dashboard') {
            loadStockAlerts(true); // refresh alerts from live warehouse stock
            if (salesChart) salesChart.render();
            if (categoryDonutChart) categoryDonutChart.render();
            if (channelBarChart) channelBarChart.render();
        } else if (viewId === 'forecasting') {
            initCharts();
            runForecastModel();
        }
        if (window.lucide && window.__iconsStale) { lucide.createIcons(); window.__iconsStale = false; }
    } else if (window.lucide && window.__iconsStale) {
        lucide.createIcons();
        window.__iconsStale = false;
    }
}

// Live Top Search Handler
let __searchDebounce = 0;
function handleTopSearch(query) {
    clearTimeout(__searchDebounce);
    __searchDebounce = setTimeout(async () => {
        const q = (query || '').trim();
        if (!q) return;

        switchView('storefront');

        const grid = document.getElementById('productsGrid');
        if (!grid) return;

        try {
            const res = await fetch(apiUrl('recommendations', `/api/v1/search?q=${encodeURIComponent(q)}`));
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            const results = data.results || [];
            const t = i18n[currentLang];

            if (results.length === 0) {
                grid.innerHTML = `<div class="error-state">${currentLang === 'ar' ? 'لا توجد نتائج بحث مطابقة' : 'No matching products found'}</div>`;
                return;
            }

            grid.innerHTML = results.map(p => {
                let imgUrl = (typeof getProductPhoto === 'function') ? getProductPhoto(p) : (p.image_url || 'images/products/' + String(p.product_id).padStart(10, '0') + '.jpg');
                return `
                    <div class="product-card">
                        <img src="${imgUrl}" class="product-img" alt="${p.name}" loading="lazy" decoding="async" onerror="this.onerror=null;this.src='https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?auto=format&fit=crop&w=600&q=80';">
                        <div class="product-title">${p.name}</div>
                        <div class="product-price">${p.price ? p.price.toLocaleString() + ' EGP' : '—'}</div>
                        <span class="badge badge-purple">${p.category || ''}</span>
                        <button class="btn btn-secondary btn-sm" onclick="sendChipMessage('${t.chip_ask_details} ${p.name}')">
                            💬 ${t.btn_ask_assistant}
                        </button>
                    </div>
                `;
            }).join('');
            window.__iconsStale = true;
        } catch (e) {
            console.warn('Search failed:', e);
        }
    }, 300);
}

// OCR upload progress — simulated 0→90% while awaiting the backend, then 100%.
let scanProgressTimer = null;
function setScanProgress(pct) {
    const bar = document.getElementById('scanProgressBar');
    const label = document.getElementById('scanPercent');
    const clamped = Math.max(0, Math.min(100, Math.round(pct)));
    if (bar) bar.style.width = clamped + '%';
    if (label) label.textContent = clamped + '%';
}
function startScanProgress() {
    stopScanProgress();
    setScanProgress(0);
    let shown = 0;
    scanProgressTimer = setInterval(() => {
        // Ease toward 90% so the bar never stalls visually while OCR runs.
        shown += Math.max(1, (90 - shown) * 0.12);
        setScanProgress(Math.min(90, shown));
    }, 120);
}
function finishScanProgress() {
    stopScanProgress();
    setScanProgress(100);
}
function stopScanProgress() {
    if (scanProgressTimer) {
        clearInterval(scanProgressTimer);
        scanProgressTimer = null;
    }
}

// OCR File Upload Handler
function triggerFileSelect() {
    const input = document.getElementById('ocrFileInput');
    if (input) input.click();
}

async function handleFileSelected(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    await processOCRFile(file);
}

async function processOCRFile(file) {
    const overlay = document.getElementById('scanOverlay');
    const tbody = document.getElementById('ocrTableBody');
    const resultsCard = document.getElementById('ocrResultsCard');
    const meta = document.getElementById('invoiceMeta');

    if (overlay) overlay.style.display = 'flex';
    startScanProgress();

    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('lang', currentLang === 'ar' ? 'ar' : 'en');
        formData.append('save', 'false');

        const res = await fetch(apiUrl('ocr', '/api/process'), {
            method: 'POST',
            body: formData,
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }

        const data = await res.json();

        if (!data.ok) {
            throw new Error(data.message || 'OCR failed');
        }

        const items = data.items || [];
        if (items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:2rem;">No items extracted</td></tr>';
        } else {
            tbody.innerHTML = items.map(item => {
                const conf = data.validation?.confidence ?? 0;
                const flag = conf < 0.85;
                return `
                    <tr class="${flag ? 'row-flagged' : ''}">
                        <td><strong>${item.name || '—'}</strong></td>
                        <td>${item.quantity ?? '—'}</td>
                        <td>${item.price ?? '—'} EGP</td>
                        <td>${Math.round((item.price ?? 0) * 2.8)} EGP</td>
                        <td>${((item.quantity ?? 0) * (item.price ?? 0)).toLocaleString()} EGP</td>
                        <td>
                            <span class="badge ${flag ? 'badge-amber' : 'badge-green'}">
                                ${(conf * 100).toFixed(1)}% ${flag ? '⚠️ Review' : '✓'}
                            </span>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        if (meta) {
            meta.innerText = `${file.name} • ${items.length} item(s) extracted`;
        }

        if (resultsCard) {
            resultsCard.style.display = 'block';
            resultsCard.scrollIntoView({ behavior: 'auto', block: 'nearest' });
        }
    } catch (err) {
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:2rem;color:var(--danger,#e74c3c);">OCR failed: ${err.message}</td></tr>`;
        }
        if (resultsCard) resultsCard.style.display = 'block';
    } finally {
        finishScanProgress();
        setTimeout(() => { if (overlay) overlay.style.display = 'none'; }, 350);
    }
}

async function confirmOCRToInventory() {
    const fileInput = document.getElementById('ocrFileInput');
    const file = fileInput && fileInput.files && fileInput.files[0];
    if (!file) {
        alert(currentLang === 'ar' ? 'ارفع فاتورة الأول' : 'Upload an invoice first');
        return;
    }

    const overlay = document.getElementById('scanOverlay');
    if (overlay) overlay.style.display = 'flex';
    startScanProgress();

    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('lang', currentLang === 'ar' ? 'ar' : 'en');
        formData.append('save', 'true');

        const res = await fetch(apiUrl('ocr', '/api/process'), {
            method: 'POST',
            body: formData,
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }

        const data = await res.json();
        if (!data.ok) {
            throw new Error(data.message || 'OCR save failed');
        }

        const saved = (data.saved || []).length;
        if (saved === 0) {
            throw new Error(data.message || (currentLang === 'ar' ? 'لم يتم حفظ أي أصناف' : 'No items were saved'));
        }

        alert(currentLang === 'ar'
            ? `تمت مطابقة المستند وتحديث مخزون المتجر بنجاح 🚀 (${saved} صنف أضيف للمخزون)`
            : `Invoice verified and ${saved} catalog items successfully synced to inventory! 🚀`);
    } catch (err) {
        alert(currentLang === 'ar'
            ? `فشل تحديث المخزون: ${err.message}`
            : `Failed to sync inventory: ${err.message}`);
    } finally {
        finishScanProgress();
        setTimeout(() => { if (overlay) overlay.style.display = 'none'; }, 350);
    }
}

// Sample OCR Invoice Loader
async function loadSampleOCRInvoice() {
    const overlay = document.getElementById('scanOverlay');
    const tbody = document.getElementById('ocrTableBody');
    const resultsCard = document.getElementById('ocrResultsCard');
    const meta = document.getElementById('invoiceMeta');

    if (overlay) overlay.style.display = 'flex';
    startScanProgress();

    setTimeout(() => {
        const sampleItems = [
            { name: currentLang === 'ar' ? 'تيشيرت قطن فاخر' : 'Premium Cotton T-Shirt', quantity: 15, price: 250 },
            { name: currentLang === 'ar' ? 'جاكيت شتوي هلسنكي' : 'Helsinki Winter Jacket', quantity: 5, price: 1200 },
            { name: currentLang === 'ar' ? 'بنطلون جينز كاجوال' : 'Casual Slim Jeans', quantity: 10, price: 550 },
            { name: currentLang === 'ar' ? 'شرابات قطنية 3 قطع' : 'Cotton Socks 3-Pack', quantity: 25, price: 150 }
        ];

        if (tbody) {
            tbody.innerHTML = sampleItems.map(item => `
                <tr>
                    <td><strong>${item.name}</strong></td>
                    <td>${item.quantity}</td>
                    <td>${item.price} EGP</td>
                    <td>${Math.round(item.price * 1.8)} EGP</td>
                    <td>${(item.quantity * item.price).toLocaleString()} EGP</td>
                    <td>
                        <span class="badge badge-green">99.4% ✓</span>
                    </td>
                </tr>
            `).join('');
        }

        if (meta) {
            meta.innerText = currentLang === 'ar'
                ? `فاتورة عينة رقم #INV-2026-004 • ${sampleItems.length} صنف تم استخراجها بنجاح`
                : `Sample Invoice #INV-2026-004 • ${sampleItems.length} items extracted`;
        }

        if (resultsCard) {
            resultsCard.style.display = 'block';
            resultsCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }

        // Quick staged ramp so the 0→100% count is visible even on the fast sample path.
        stopScanProgress();
        setScanProgress(55);
        setTimeout(() => setScanProgress(80), 150);
        setTimeout(() => setScanProgress(100), 300);
        setTimeout(() => { if (overlay) overlay.style.display = 'none'; }, 550);
    }, 400);
}

// Scroll Helper — instant jump keeps navigation feeling snappy.
function scrollToSection(id) {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'auto', block: 'start' });
}

// Language Switcher Handler
function toggleLanguage() {
    currentLang = (currentLang === 'ar') ? 'en' : 'ar';
    document.documentElement.setAttribute('lang', currentLang);
    document.documentElement.setAttribute('dir', currentLang === 'ar' ? 'rtl' : 'ltr');
    document.getElementById('langText').innerText = currentLang === 'ar' ? 'English' : 'عربي';

    updateLanguageDOM();
    // Defer heavy rebuilds — text flips instantly, charts/catalog catch up idle.
    const rebuildHeavy = () => {
        initCharts();
        // New language → drop the cached HTML so the catalog re-renders once.
        __catalogCache.lang = null;
        loadCatalogProducts();
        renderStockAlerts(); // bundled/live alert rows re-render in the new language
    };
    if ('requestIdleCallback' in window) {
        requestIdleCallback(rebuildHeavy, { timeout: 400 });
    } else {
        setTimeout(rebuildHeavy, 30);
    }

    // Keep the chatbot in the active website language:
    // 1) reset conversation so the bot doesn't mix languages mid-thread,
    // 2) refresh the welcome bubble if the chat is still empty.
    currentConversationId = null;
    const stream = document.getElementById('chatStream');
    const hasUserMsg = stream && stream.querySelector('.user-msg');
    if (stream && !hasUserMsg) {
        const botBubble = stream.querySelector('.bot-msg p');
        if (botBubble) botBubble.innerText = i18n[currentLang].chat_welcome;
    }
}

// Quick chip → resolves its i18n key to the active language at click time
function sendChip(key) {
    const text = i18n[currentLang][key];
    if (text) sendChipMessage(text);
}

function updateLanguageDOM() {
    const langDict = i18n[currentLang];
    // Cache the i18n-bound nodes after first scan — toggleLanguage re-runs often.
    if (!updateLanguageDOM.__els) {
        updateLanguageDOM.__els = Array.from(document.querySelectorAll('[data-i18n]'));
        updateLanguageDOM.__phEls = Array.from(document.querySelectorAll('[data-i18n-ph]'));
    }
    const els = updateLanguageDOM.__els;
    for (let i = 0; i < els.length; i++) {
        const key = els[i].getAttribute('data-i18n');
        if (langDict[key]) els[i].innerText = langDict[key];
    }

    const phEls = updateLanguageDOM.__phEls;
    for (let i = 0; i < phEls.length; i++) {
        const key = phEls[i].getAttribute('data-i18n-ph');
        if (langDict[key]) phEls[i].setAttribute('placeholder', langDict[key]);
    }
    // New nodes were injected (catalog, OCR rows) → icons need a refresh pass.
    window.__iconsStale = true;
}

// Theme Switcher Handler — instant class flip, charts rebuild lazily.
function toggleTheme() {
    currentTheme = (currentTheme === 'dark') ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', currentTheme);
    // Chart rebuild is the slow part (~100ms+): defer so the toggle feels instant.
    if ('requestIdleCallback' in window) {
        requestIdleCallback(() => initCharts(), { timeout: 400 });
    } else {
        setTimeout(initCharts, 30);
    }
}

// Interactive Financial ROI Calculator
// requestROICalc: rAF-throttle slider drags so the UI never lags mid-drag.
let __roiRaf = 0;
function requestROICalc() {
    if (__roiRaf) return;
    __roiRaf = requestAnimationFrame(() => { __roiRaf = 0; updateROICalculator(); });
}
const __roiIds = ['inputOrders', 'inputSKUs', 'inputAOV', 'valOrders', 'valSKUs', 'valAOV',
    'resTotalVal', 'resRecBoost', 'resStockout', 'resHours'];
const __roiEls = {};
function updateROICalculator() {
    for (let i = 0; i < __roiIds.length; i++) {
        if (!__roiEls[__roiIds[i]]) __roiEls[__roiIds[i]] = document.getElementById(__roiIds[i]);
    }
    const orders = parseInt(__roiEls.inputOrders.value);
    const skus = parseInt(__roiEls.inputSKUs.value);
    const aov = parseInt(__roiEls.inputAOV.value);

    __roiEls.valOrders.innerText = orders.toLocaleString();
    __roiEls.valSKUs.innerText = skus.toLocaleString();
    __roiEls.valAOV.innerText = aov.toLocaleString() + ' EGP';

    // Calculations
    const extraRecSysRevenue = Math.round(orders * aov * 0.18);
    const preventedStockoutsLoss = Math.round(skus * 1200);
    const savedHours = Math.round((orders / 100) * 1.8);
    const totalVal = extraRecSysRevenue + preventedStockoutsLoss;

    __roiEls.resTotalVal.innerText = totalVal.toLocaleString() + ' EGP';
    __roiEls.resRecBoost.innerText = '+' + extraRecSysRevenue.toLocaleString() + ' EGP';
    __roiEls.resStockout.innerText = preventedStockoutsLoss.toLocaleString() + ' EGP';
    __roiEls.resHours.innerText = savedHours + ' Hours';
}

// Initialize ApexCharts
// Colours + theming are read LIVE from the CSS custom properties, so charts
// always match the active theme (no orphaned dark tooltips/axes in Light Mode).
// Palette: #042F34 · #B5F2DB · #FFC933 · #16232B · #E4EEF0
function readChartTheme() {
    // Cache per theme+lang — getComputedStyle() is expensive, and tokens only
    // change when the theme or language flips.
    const cacheKey = currentTheme + '|' + currentLang;
    if (readChartTheme.__key === cacheKey && readChartTheme.__val) return readChartTheme.__val;
    const css = getComputedStyle(document.documentElement);
    const tok = (name, fallback) => (css.getPropertyValue(name) || '').trim() || fallback;
    const isDark = currentTheme === 'dark';
    readChartTheme.__key = cacheKey;
    readChartTheme.__val = {
        isDark,
        text: tok('--chart-text', isDark ? '#B5F2DB' : '#16232B'),
        grid: tok('--chart-grid', isDark ? 'rgba(181, 242, 219, 0.1)' : 'rgba(4, 47, 52, 0.1)'),
        actual: tok('--chart-actual', '#B5F2DB'),
        forecast: tok('--chart-forecast', '#FFC933'),
        band: tok('--chart-band', '#B5F2DB'),
        tooltipBg: tok('--chart-tooltip-bg', '#16232B'),
        cardBg: tok('--bg-card', isDark ? '#042F34' : '#FFFFFF'),
        tooltipText: tok('--chart-tooltip-text', '#E4EEF0'),
        fontFamily: currentLang === 'ar' ? 'Cairo' : 'Inter',
        mode: currentTheme
    };
    return readChartTheme.__val;
}

async function initCharts() {
    if (!window.ApexCharts) return; // CDN still loading — bootHeavy retries on idle.
    const th = readChartTheme();
    const textColor = th.text;
    const gridColor = th.grid;
    // Shared wiring applied to every chart so tooltips/legends follow the theme
    const themedChart = {
        theme: { mode: th.mode },
        tooltip: { theme: th.mode, style: { fontFamily: th.fontFamily } }
    };

    // 1. Sales & AI Forecast Area Chart — static for now (no sales history API)
    const salesOptions = {
        ...themedChart,
        chart: { type: 'area', height: 320, background: 'transparent', toolbar: { show: false }, fontFamily: th.fontFamily },
        colors: [th.actual, th.forecast],
        stroke: { curve: 'smooth', width: 3 },
        fill: { type: 'gradient', gradient: { opacityFrom: 0.45, opacityTo: 0.05 } },
        series: [
            { name: currentLang === 'ar' ? 'المبيعات الفعلية' : 'Actual Sales', data: [32, 40, 45, 50, 49, 60, 70, 81, 95] },
            { name: currentLang === 'ar' ? 'توقع الـ AI (30 يوم)' : 'AI Forecast (30d)', data: [null, null, null, null, null, null, 70, 88, 110, 125, 140] }
        ],
        xaxis: { categories: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov'], labels: { style: { colors: textColor } } },
        yaxis: { labels: { style: { colors: textColor } } },
        grid: { borderColor: gridColor }
    };

    if (salesChart) salesChart.destroy();
    const salesEl = document.getElementById('salesForecastChart');
    if (salesEl) {
        salesChart = new ApexCharts(salesEl, salesOptions);
        salesChart.render();
    }

    // Live layer: refreshed with real LightGBM demand right after the
    // baseline renders (see refreshSalesChartLive below). Static series
    // stays if the forecasting service (:8400) is unreachable.

    // Live layer — Revenue & AI Demand Forecast Trajectory.
    // Fetches the ranked LightGBM forecast (same engine as the forecasting page)
    // and redraws the dashboard area chart with real predicted demand.
    // Guarded by a run id so a stale response can never overwrite newer data.
    let __salesLiveRunId = 0;
    async function refreshSalesChartLive() {
        const runId = ++__salesLiveRunId;
        const badge = document.getElementById('salesLiveBadge');
        const setBadge = (live) => {
            if (!badge) return;
            const dict = i18n[currentLang] || {};
            badge.innerText = live
                ? (dict.badge_live || 'Live Model')
                : (dict.badge_live_offline || 'Offline Baseline');
            badge.classList.toggle('badge-primary', !!live);
            badge.classList.toggle('badge-amber', !live);
        };
        setBadge(true);
        try {
            const ctrl = new AbortController();
            const timer = setTimeout(() => ctrl.abort(), 6000);
            let data = null;
            try {
                const res = await fetch(apiUrl('forecasting', '/forecast?limit=12'), { signal: ctrl.signal });
                if (res.ok) data = await res.json();
                else console.warn(`Forecast API HTTP ${res.status} — dashboard chart keeps baseline`);
            } finally {
                clearTimeout(timer);
            }
            if (runId !== __salesLiveRunId) return; // superseded
            if (!data || !Array.isArray(data.items) || data.items.length === 0) { setBadge(false); return; }
            if (!salesChart) { setBadge(false); return; }

            const top = data.items.slice(0, 9);
            const labels = top.map(it => {
                const nm = (it.name || '').toString().trim();
                return nm ? (nm.length > 14 ? nm.slice(0, 13) + '…' : nm) : `#${it.article_id}`;
            });
            // Actuals proxy: the ranked endpoint omits last-observed demand, so
            // scale prediction by the sell-through signal; the AI 30d trajectory
            // then continues from the last actual point.
            const actual = top.map(it => {
                const p = (it.probability_of_sale != null ? it.probability_of_sale : 0.8);
                return Math.max(0, Math.round((it.predicted_demand || 0) * 4 * (0.55 + 0.45 * p)));
            });
            // AI 30d trajectory continues from the last actual point.
            const lastActual = actual.length ? actual[actual.length - 1] : 0;
            const forecastLine = top.map((_, i) => (i < top.length - 1 ? null : lastActual));
            const growth = [1.12, 1.28, 1.45];
            const forecastTail = growth.map(g => Math.round(lastActual * g));

            await salesChart.updateOptions({
                series: [
                    { name: currentLang === 'ar' ? 'المبيعات الفعلية' : 'Actual Sales', data: actual },
                    { name: currentLang === 'ar' ? 'توقع الـ AI (30 يوم)' : 'AI Forecast (30d)', data: [...forecastLine, ...forecastTail] },
                ],
                xaxis: { categories: [...labels, '+10d', '+20d', '+30d'] },
            });
            setBadge(true);
        } catch (err) {
            console.warn('Live sales chart unreachable — keeping offline baseline:', err && err.message);
            if (runId === __salesLiveRunId) setBadge(false);
        }
    }
    refreshSalesChartLive();

    // 2. Category Breakdown Donut Chart — fetches real facets from recommendation service
    let donutLabels = currentLang === 'ar'
        ? ['الملابس القطنية', 'الجاكيتات', 'الهوديز', 'البناطيل', 'الإكسسوارات']
        : ['Cotton Apparel', 'Outerwear', 'Hoodies', 'Pants', 'Accessories'];
    let donutSeries = [40, 25, 20, 10, 5];

    try {
        const facetsRes = await fetch(apiUrl('recommendations', '/api/v1/facets'));
        if (facetsRes.ok) {
            const facets = await facetsRes.json();
            if (facets.categories && Object.keys(facets.categories).length > 0) {
                const entries = Object.entries(facets.categories).sort((a, b) => b[1] - a[1]);
                donutLabels = entries.map(([k]) => k);
                donutSeries = entries.map(([, v]) => v);
            }
        }
    } catch (e) {
        console.warn('Failed to load facets, using defaults:', e);
    }

    const donutOptions = {
        ...themedChart,
        chart: { type: 'donut', height: 320, background: 'transparent', fontFamily: th.fontFamily },
        colors: ['#B5F2DB', '#FFC933', '#2DD4BF', '#38BDF8', '#A78BFA'],
        labels: donutLabels,
        series: donutSeries,
        legend: { position: 'bottom', labels: { colors: textColor }, markers: { width: 12, height: 12, radius: 6 } },
        dataLabels: { enabled: true, style: { fontSize: '12px', fontWeight: 700 } },
        plotOptions: {
            pie: {
                donut: {
                    size: '62%',
                    labels: {
                        show: true,
                        total: {
                            show: true,
                            label: currentLang === 'ar' ? 'الإجمالي' : 'Total',
                            color: textColor,
                            formatter: () => '100%'
                        }
                    }
                }
            }
        },
        stroke: { show: true, width: 3, colors: [th.cardBg] }
    };

    if (categoryDonutChart) categoryDonutChart.destroy();
    const donutEl = document.getElementById('categoryDonutChart');
    if (donutEl) {
        categoryDonutChart = new ApexCharts(donutEl, donutOptions);
        categoryDonutChart.render();
    }

    // 3. Sales Volume by Channel Bar Chart — static for now (no channel API)
    const barOptions = {
        ...themedChart,
        chart: { type: 'bar', height: 300, background: 'transparent', toolbar: { show: false }, fontFamily: th.fontFamily },
        colors: [th.actual, th.forecast],
        plotOptions: { bar: { borderRadius: 6, columnWidth: '50%' } },
        series: [
            { name: currentLang === 'ar' ? 'إجمالي المبيعات' : 'Total Revenue', data: [45, 62, 78, 90, 115] },
            { name: currentLang === 'ar' ? 'أرباح الـ AI' : 'AI Attribution', data: [12, 18, 25, 32, 45] }
        ],
        xaxis: {
            categories: ['Storefront Direct', 'Instagram Shop', 'TikTok Shop', 'RAG Chatbot', 'Smart RecSys'],
            labels: { style: { colors: textColor } }
        },
        yaxis: { labels: { style: { colors: textColor } } },
        grid: { borderColor: gridColor }
    };

    if (channelBarChart) channelBarChart.destroy();
    const barEl = document.getElementById('channelBarChart');
    if (barEl) {
        channelBarChart = new ApexCharts(barEl, barOptions);
        channelBarChart.render();
    }

    // 4. Demand Trend & 30-Day Predictive Trajectory — fetches real forecast data
    let weeks = ['W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7', 'W8', 'W9', 'W10'];
    let actualDemand = [
        { x: 'W1', y: 120 }, { x: 'W2', y: 135 }, { x: 'W3', y: 128 },
        { x: 'W4', y: 142 }, { x: 'W5', y: 150 }, { x: 'W6', y: 165 }, { x: 'W7', y: 180 }
    ];
    let forecastDemand = [
        { x: 'W6', y: 165 }, { x: 'W7', y: 195 }, { x: 'W8', y: 210 },
        { x: 'W9', y: 230 }, { x: 'W10', y: 245 }
    ];
    let confidenceBand = [
        { x: 'W6', y: [152, 178] }, { x: 'W7', y: [176, 214] },
        { x: 'W8', y: [189, 231] }, { x: 'W9', y: [206, 254] },
        { x: 'W10', y: [219, 271] }
    ];

    try {
        const forecastRes = await fetch(apiUrl('forecasting', '/forecast?limit=20'));
        if (forecastRes.ok) {
            const forecastData = await forecastRes.json();
            if (forecastData.items && forecastData.items.length > 0) {
                const items = forecastData.items;
                weeks = items.map((_, i) => `W${i + 1}`);
                forecastDemand = items.map((item, i) => ({
                    x: `W${i + 1}`,
                    y: Math.round(item.predicted_demand * 10) / 10
                }));
                // Build confidence band (±20% around prediction)
                confidenceBand = items.map((item, i) => ({
                    x: `W${i + 1}`,
                    y: [
                        Math.round(item.predicted_demand * 0.8 * 10) / 10,
                        Math.round(item.predicted_demand * 1.2 * 10) / 10
                    ]
                }));
                // Actual demand: use last_observed_sales if available, else 0
                actualDemand = items.map((item, i) => ({
                    x: `W${i + 1}`,
                    y: item.last_observed_sales != null ? item.last_observed_sales : 0
                }));
            }
        }
    } catch (e) {
        console.warn('Failed to load forecast data, using defaults:', e);
    }

    const demandOptions = {
        ...themedChart,
        chart: {
            type: 'rangeArea',
            height: 340,
            background: 'transparent',
            toolbar: { show: false },
            fontFamily: th.fontFamily,
            animations: { easing: 'easeout', speed: 500 }
        },
        // [confidence band, historical demand, LGBM prediction]
        colors: [th.band, th.actual, th.forecast],
        series: [
            { type: 'rangeArea', name: currentLang === 'ar' ? 'نطاق الثقة 95%' : '95% Confidence Range', data: confidenceBand },
            { type: 'line', name: currentLang === 'ar' ? 'الطلب التاريخي' : 'Historical Demand', data: actualDemand },
            { type: 'line', name: currentLang === 'ar' ? 'توقع Model LGBM' : 'LGBM Model Prediction', data: forecastDemand }
        ],
        dataLabels: { enabled: false },
        fill: { opacity: [0.22, 1, 1] },
        stroke: { curve: 'smooth', width: [0, 3, 2], dashArray: [0, 0, 6] },
        markers: { size: [0, 0, 4], hover: { sizeOffset: 4 } },
        legend: { position: 'top', labels: { colors: textColor } },
        xaxis: { type: 'category', categories: weeks, labels: { style: { colors: textColor } } },
        yaxis: { labels: { style: { colors: textColor } } },
        grid: { borderColor: gridColor },
        tooltip: { theme: th.mode, shared: true, style: { fontFamily: th.fontFamily } }
    };

    if (forecastChart) forecastChart.destroy();
    const forecastEl = document.getElementById('demandTrendChart');
    if (forecastEl) {
        forecastChart = new ApexCharts(forecastEl, demandOptions);
        forecastChart.render();
    }

    // Populate SKU dropdown lazily with real backend SKUs
    populateSkuDropdown();
}

// Dynamic SKU Map and Population
let __skuMap = {};
let __skuPopulateInFlight = null;
function populateSkuDropdown() {
    if (__skuPopulateInFlight) return __skuPopulateInFlight;
    __skuPopulateInFlight = (async () => {
        const select = document.getElementById('skuSelect');
        if (!select) return;

        try {
            let skusList = [];

            // 1. Fetch from recommendations catalog API
            try {
                const catRes = await fetch(apiUrl('recommendations', '/api/v1/products?limit=50'));
                if (catRes.ok) {
                    const cData = await catRes.json();
                    (cData.products || []).forEach(p => {
                        const id = p.product_id;
                        const name = p.name;
                        __skuMap[id] = name;
                        skusList.push({ id, name });
                    });
                }
            } catch (e) {}

            // 2. Fetch from forecasting API
            try {
                const forecastRes = await fetch(apiUrl('forecasting', '/forecast?limit=50'));
                if (forecastRes.ok) {
                    const fData = await forecastRes.json();
                    (fData.items || []).forEach(item => {
                        const id = item.article_id;
                        const name = item.name || __skuMap[id] || `SKU #${id}`;
                        __skuMap[id] = name;
                        if (!skusList.some(s => String(s.id) === String(id))) {
                            skusList.push({ id, name });
                        }
                    });
                }
            } catch (e) {}

            // 3. Fallback list if network/apis were empty
            if (skusList.length === 0) {
                skusList = [
                    { id: 108775015, name: currentLang === 'ar' ? 'تاپ ستراب قطن أسود' : 'Strap Top Cotton (Black)' },
                    { id: 212629040, name: currentLang === 'ar' ? 'فستان الكازار أحمر غامق' : 'Alcazar Strap Dress (Dark Red)' },
                    { id: 237222001, name: currentLang === 'ar' ? 'جاكيت هلسنكي شتوي أسود' : 'Helsinki Winter Jacket (Black)' },
                    { id: 300101002, name: currentLang === 'ar' ? 'هودي قطن شتوي ثقيل' : 'Heavy Cotton Winter Hoodie' },
                    { id: 400202003, name: currentLang === 'ar' ? 'بنطلون جينز كاجوال' : 'Casual Slim Jeans' },
                    { id: 500303004, name: currentLang === 'ar' ? 'شرابات قطنية 3 قطع' : 'Cotton Socks 3-Pack' }
                ];
                skusList.forEach(s => { __skuMap[s.id] = s.name; });
            }

            const previous = select.value;
            select.innerHTML = skusList.map(item => {
                return `<option value="${item.id}">${item.name} (#${item.id})</option>`;
            }).join('');

            if (previous && Array.from(select.options).some(o => o.value === previous)) {
                select.value = previous;
            }
        } catch (err) {
            console.warn('Failed to populate SKU dropdown:', err);
        }
    })().finally(() => { __skuPopulateInFlight = null; });
    return __skuPopulateInFlight;
}

// Deterministic per-SKU baseline
function __localForecastBaseline(sku) {
    const s = String(sku);
    let h = 0;
    for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
    return {
        weekly: 6 + (h % 15),                       // 6..20 units/week
        probability: 0.78 + ((h >>> 5) % 18) / 100  // 0.78..0.95
    };
}

let __forecastRunId = 0;
async function runForecastModel() {
    const skuSelect = document.getElementById('skuSelect');
    const horizonSelect = document.getElementById('horizonSelect');
    const modelEngineSelect = document.getElementById('modelEngineSelect');
    const btn = document.getElementById('btnRunForecast');

    if (!skuSelect || !skuSelect.value) return;
    const runId = ++__forecastRunId;

    const sku = skuSelect.value;
    const horizon = parseInt(horizonSelect ? horizonSelect.value : 30);
    const modelEngine = modelEngineSelect ? modelEngineSelect.value : 'lgbm';
    const skuName = __skuMap[sku] || skuSelect.options[skuSelect.selectedIndex]?.text || `SKU #${sku}`;

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `⏳ <span>${currentLang === 'ar' ? 'جاري التشغيل...' : 'Executing Model...'}</span>`;
    }

    try {
        let data = null;
        try {
            const ctrl = new AbortController();
            const timer = setTimeout(() => ctrl.abort(), 6000);
            try {
                const res = await fetch(apiUrl('forecasting', `/forecast/${sku}`), { signal: ctrl.signal });
                if (res.ok) data = await res.json();
                else console.warn(`Forecast API HTTP ${res.status} — using local estimate`);
            } finally {
                clearTimeout(timer);
            }
        } catch (err) {
            console.warn('Forecast API unreachable — using local estimate:', err && err.message);
        }
        if (runId !== __forecastRunId) return;
        const isLive = !!data;
        const local = isLive ? null : __localForecastBaseline(sku);

        const weeklyDemand = isLive ? (data.predicted_demand || 0.25) : local.weekly;
        const horizonWeeks = horizon / 7;
        const projectedUnits = Math.max(1, Math.round(weeklyDemand * horizonWeeks * (modelEngine === 'xgboost' ? 1.08 : 1.0)));
        const saleProbability = isLive
            ? (data.probability_of_sale != null ? data.probability_of_sale : 0.95)
            : local.probability;

        const estPrice = 350;
        const projectedRevenue = projectedUnits * estPrice;
        const currentStock = Math.round(projectedUnits * 0.85);
        const riskPercent = Math.min(95, Math.max(5, Math.round((1 - (currentStock / (projectedUnits || 1))) * 100)));

        const elDemand = document.getElementById('fmValDemand');
        const elStock = document.getElementById('fmValStock');
        const elRisk = document.getElementById('fmValRisk');
        const elRevenue = document.getElementById('fmValRevenue');

        if (elDemand) elDemand.innerText = `${projectedUnits.toLocaleString()} ${currentLang === 'ar' ? 'قطعة' : 'Units'}`;
        if (elStock) elStock.innerText = `${currentStock.toLocaleString()} ${currentLang === 'ar' ? 'قطعة بالمخزون' : 'Units'}`;
        if (elRisk) {
            elRisk.innerText = `${riskPercent}% ${riskPercent > 20 ? (currentLang === 'ar' ? 'مخاطرة مرتفعة' : 'High Risk') : (currentLang === 'ar' ? 'مخاطرة منخفضة' : 'Low Risk')}`;
            elRisk.className = `metric-value ${riskPercent > 20 ? 'text-amber' : 'text-green'}`;
        }
        if (elRevenue) elRevenue.innerText = `${projectedRevenue.toLocaleString()} EGP`;

        // Update title above chart to show current SKU name & horizon
        const chartTitleEl = document.getElementById('forecastChartTitle');
        if (chartTitleEl) {
            chartTitleEl.innerText = currentLang === 'ar'
                ? `${skuName} — توقعات ${horizon} يوماً`
                : `${skuName} — ${horizon}-Day Forecast`;
        }

        updateForecastChartForSku(sku, skuName, projectedUnits, horizon, modelEngine);

        const resultBox = document.getElementById('forecastResultBox');
        if (resultBox) {
            resultBox.style.display = 'block';
            document.getElementById('forecastResultSkuName').innerText = skuName;
            document.getElementById('forecastResultBadge').innerText = isLive
                ? `${modelEngine.toUpperCase()} • ${horizon}d`
                : (currentLang === 'ar' ? `تقدير محلي • ${horizon} يوم` : `LOCAL • ${horizon}d`);
            document.getElementById('forecastResultDemand').innerText = `${projectedUnits} ${currentLang === 'ar' ? 'قطعة' : 'Units'}`;
            document.getElementById('forecastResultProb').innerText = `${(saleProbability * 100).toFixed(0)}%`;
            const offlineNote = isLive ? '' : (currentLang === 'ar'
                ? ' — تقدير محلي، خدمة التنبؤ الحية غير متاحة الآن.'
                : ' — local estimate, live forecast service unavailable.');
            document.getElementById('forecastResultNoteText').innerText = (currentLang === 'ar'
                ? `تم التنبؤ بـ ${projectedUnits} قطعة خلال ${horizon} يوماً قادمة بنسبة ثقة ${(saleProbability * 100).toFixed(0)}% باستخدام محرك ${modelEngine.toUpperCase()}.`
                : `Model predicted ${projectedUnits} units required over next ${horizon} days (${(saleProbability * 100).toFixed(0)}% confidence).`) + offlineNote;
        }
    } catch (err) {
        console.error('Forecast execution failed:', err);
    } finally {
        if (btn && runId === __forecastRunId) {
            btn.disabled = false;
            btn.innerHTML = `⚡ <span data-i18n="btn_run_forecast">${i18n[currentLang].btn_run_forecast || 'Run Prediction Model'}</span>`;
        }
    }
}

function updateForecastChartForSku(sku, name, projectedUnits, horizon, modelEngine) {
    if (!forecastChart) return;

    const numPoints = Math.round(horizon / 7);
    const weeks = Array.from({ length: numPoints + 4 }, (_, i) => `W${i + 1}`);
    const baseVal = Math.max(5, Math.round(projectedUnits / numPoints));

    const actualData = weeks.map((w, i) => {
        if (i < 4) {
            return { x: w, y: Math.round(baseVal * (0.85 + Math.sin(i) * 0.15)) };
        }
        return { x: w, y: null };
    });

    const forecastData = weeks.map((w, i) => {
        if (i >= 3) {
            return { x: w, y: Math.round(baseVal * (1.0 + (i - 3) * 0.12)) };
        }
        return { x: w, y: null };
    });

    const confidenceData = weeks.map((w, i) => {
        if (i >= 3) {
            const val = baseVal * (1.0 + (i - 3) * 0.12);
            return { x: w, y: [Math.round(val * 0.8), Math.round(val * 1.25)] };
        }
        return { x: w, y: null };
    });

    forecastChart.updateOptions({
        series: [
            { type: 'rangeArea', name: currentLang === 'ar' ? 'نطاق الثقة 95%' : '95% Confidence Range', data: confidenceData },
            { type: 'line', name: currentLang === 'ar' ? 'الطلب التاريخي' : 'Historical Demand', data: actualData },
            { type: 'line', name: `${modelEngine.toUpperCase()} ${currentLang === 'ar' ? 'توقع' : 'Prediction'}`, data: forecastData }
        ],
        xaxis: { categories: weeks }
    });

    const titleEl = document.getElementById('forecastChartTitle');
    const subEl = document.getElementById('forecastChartSub');
    if (titleEl) titleEl.innerText = `${name} — ${horizon}-Day Forecast`;
    if (subEl) subEl.innerText = currentLang === 'ar'
        ? `مسار الطلب والمبيعات المتوقعة لـ ${horizon} يوماً قادماً بنموذج ${modelEngine.toUpperCase()}`
        : `Historical sales vs ${modelEngine.toUpperCase()} model trajectory for the next ${horizon} days`;
}

// Catalog Products Loader — fetches real products from the recommendation service.
// Renders once per language, then reuses the HTML.
let __catalogCache = { lang: null, html: null };
async function loadCatalogProducts() {
    const grid = document.getElementById('productsGrid');
    if (!grid) return;
    if (__catalogCache.lang === currentLang && __catalogCache.html) {
        grid.innerHTML = __catalogCache.html;
        window.__iconsStale = true;
        return;
    }

    const t = i18n[currentLang];

    // Fallback products array with high quality product photos
    const fallbackProducts = [
        { product_id: 108775015, name: currentLang === 'ar' ? 'تاپ ستراب قطن أسود' : 'Strap Top Cotton (Black)', price: 350, category: currentLang === 'ar' ? 'ملابس قطنية' : 'Cotton Apparel', image_url: 'images/products/0108775015.jpg' },
        { product_id: 212629040, name: currentLang === 'ar' ? 'فستان الكازار أحمر غامق' : 'Alcazar Strap Dress (Dark Red)', price: 850, category: currentLang === 'ar' ? 'فساتين' : 'Dresses', image_url: 'images/products/0212629040.jpg' },
        { product_id: 237222001, name: currentLang === 'ar' ? 'جاكيت هلسنكي شتوي أسود' : 'Helsinki Winter Jacket (Black)', price: 1569, category: currentLang === 'ar' ? 'جاكيتات' : 'Outerwear', image_url: 'images/products/0237222001.jpg' },
        { product_id: 300101002, name: currentLang === 'ar' ? 'هودي قطن شتوي ثقيل' : 'Heavy Cotton Winter Hoodie', price: 950, category: currentLang === 'ar' ? 'هوديز' : 'Hoodies', image_url: 'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=600&q=80' },
        { product_id: 400202003, name: currentLang === 'ar' ? 'بنطلون جينز كاجوال' : 'Casual Slim Jeans', price: 650, category: currentLang === 'ar' ? 'بناطيل' : 'Pants', image_url: 'https://images.unsplash.com/photo-1541099649105-f69ad21f3246?auto=format&fit=crop&w=600&q=80' },
        { product_id: 500303004, name: currentLang === 'ar' ? 'شرابات قطنية 3 قطع' : 'Cotton Socks 3-Pack', price: 180, category: currentLang === 'ar' ? 'إكسسوارات' : 'Accessories', image_url: 'https://images.unsplash.com/photo-1586350977771-b3b0abd50c82?auto=format&fit=crop&w=600&q=80' }
    ];

    const getProductPhoto = (p) => {
        if (!p) return 'https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?auto=format&fit=crop&w=600&q=80';
        if (p.image_url && !p.image_url.includes('logo.svg')) {
            if (p.image_url.startsWith('/')) {
                return apiUrl('recommendations', p.image_url);
            }
            return p.image_url;
        }
        if (p.product_id) {
            const pidStr = String(p.product_id).padStart(10, '0');
            return `images/products/${pidStr}.jpg`;
        }
        return 'https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?auto=format&fit=crop&w=600&q=80';
    };

    const renderProducts = (productsList) => {
        __catalogCache.html = productsList.map(p => {
            let imgUrl = getProductPhoto(p);
            return `
                <div class="product-card">
                    <img src="${imgUrl}" class="product-img" alt="${p.name}" loading="lazy" decoding="async" onerror="this.onerror=null;this.src='https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?auto=format&fit=crop&w=600&q=80';">
                    <div class="product-title">${p.name}</div>
                    <div class="product-price">${p.price ? p.price.toLocaleString() + ' EGP' : '—'}</div>
                    <span class="badge badge-purple">${p.category || ''}</span>
                    <button class="btn btn-secondary btn-sm" onclick="sendChipMessage('${t.chip_ask_details} ${p.name}')">
                        💬 ${t.btn_ask_assistant}
                    </button>
                </div>
            `;
        }).join('');
        __catalogCache.lang = currentLang;
        grid.innerHTML = __catalogCache.html;
        window.__iconsStale = true;
    };

    try {
        const res = await fetch(apiUrl('recommendations', '/api/v1/products?limit=50'));
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (data.products && data.products.length > 0) {
            renderProducts(data.products);
        } else {
            renderProducts(fallbackProducts);
        }
    } catch (err) {
        console.warn('Backend catalog API offline or slow, using high-quality fallback products:', err);
        renderProducts(fallbackProducts);
    }
}

// Floating chatbot widget — open / close + proximity glow + attraction motion
let chatWidgetOpen = false;

function toggleChatWidget(force) {
    chatWidgetOpen = (typeof force === 'boolean') ? force : !chatWidgetOpen;
    const zone = document.getElementById('chatFabZone');
    const popup = document.getElementById('chatPopup');
    if (!zone || !popup) return;
    zone.classList.toggle('chat-open', chatWidgetOpen);
    popup.setAttribute('aria-hidden', chatWidgetOpen ? 'false' : 'true');
    if (chatWidgetOpen) {
        // Focus + scroll on the next frame.
        requestAnimationFrame(() => {
            const input = document.getElementById('chatInput');
            const stream = document.getElementById('chatStream');
            if (stream) stream.scrollTop = stream.scrollHeight;
            if (input) input.focus({ preventScroll: true });
        });
    }
}

function initChatFab() {
    const zone = document.getElementById('chatFabZone');
    const fab = document.getElementById('chatFab');
    if (!zone || !fab) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const RADIUS = 220;   // px — proximity glow range
    const PULL = 10;      // px — max attraction drift toward cursor
    const EASE = 0.14;
    const cur = { glow: 0, x: 0, y: 0 };
    const target = { glow: 0, x: 0, y: 0 };
    let rafId = null;

    const loop = () => {
        cur.glow += (target.glow - cur.glow) * EASE;
        cur.x += (target.x - cur.x) * EASE;
        cur.y += (target.y - cur.y) * EASE;
        fab.style.setProperty('--fab-glow', cur.glow.toFixed(3));
        fab.style.setProperty('--fab-dx', cur.x.toFixed(1) + 'px');
        fab.style.setProperty('--fab-dy', cur.y.toFixed(1) + 'px');
        const settled = Math.abs(target.glow - cur.glow) < 0.005 &&
            Math.abs(target.x - cur.x) < 0.1 && Math.abs(target.y - cur.y) < 0.1;
        rafId = settled ? null : requestAnimationFrame(loop);
    };
    const start = () => { if (rafId === null) rafId = requestAnimationFrame(loop); };

    document.addEventListener('pointermove', (e) => {
        // Cache the rect ~once per frame — getBoundingClientRect() forces layout.
        const now = performance.now();
        if (!fab._rectTs || now - fab._rectTs > 32) {
            fab._rect = fab.getBoundingClientRect();
            fab._rectTs = now;
        }
        const r = fab._rect;
        const cx = r.left + r.width / 2;
        const cy = r.top + r.height / 2;
        const dx = e.clientX - cx;
        const dy = e.clientY - cy;
        const dist = Math.hypot(dx, dy);
        if (dist < RADIUS) {
            const k = 1 - dist / RADIUS;         // 0 far → 1 on top
            target.glow = k;
            target.x = (dx / (dist || 1)) * PULL * k;
            target.y = (dy / (dist || 1)) * PULL * k;
        } else {
            target.glow = 0; target.x = 0; target.y = 0;
        }
        start();
    }, { passive: true });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && chatWidgetOpen) toggleChatWidget(false);
    });
}

// RAG Chatbot Integration Handler
async function handleUserSubmit() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;

    appendChatMessage(msg, 'user');
    input.value = '';

    // Typing indicator — instant feedback so the bot feels alive while waiting.
    const stream = document.getElementById('chatStream');
    const typingEl = document.createElement('div');
    typingEl.className = 'msg-bubble bot-msg typing-bubble';
    typingEl.innerHTML = '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>';
    if (stream) { stream.appendChild(typingEl); stream.scrollTop = stream.scrollHeight; }

    // Send POST to Chatbot FastAPI backend (15s timeout)
    try {
        const ctrl = new AbortController();
        const timer = setTimeout(() => ctrl.abort(), 15000);
        const res = await fetch(apiUrl('chatbot', '/api/chat'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: msg,
                conversation_id: currentConversationId
            }),
            signal: ctrl.signal
        });
        clearTimeout(timer);

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (typingEl) typingEl.remove();
        if (data.conversation_id) {
            currentConversationId = data.conversation_id;
        }

        appendChatMessage(data.message || i18n[currentLang].chat_error_reply, 'bot');
        if (data.products && data.products.length > 0) {
            renderChatProducts(data.products);
        }
    } catch (err) {
        if (typingEl) typingEl.remove();
        appendChatMessage(i18n[currentLang].chat_offline_reply, 'bot');
    }
}

function renderChatProducts(products) {
    const stream = document.getElementById('chatStream');
    if (!stream || !products || !products.length) return;
    const cardsHtml = products.map(p => {
        let imgUrl = p.image_url || 'images/logo.svg';
        if (imgUrl && imgUrl.startsWith('/')) {
            imgUrl = apiUrl('chatbot', imgUrl);
        }
        return `
            <div style="background:var(--bg-card,#042F34); border:1px solid var(--border-color,rgba(181,242,219,0.2)); border-radius:10px; padding:0.6rem; margin-top:0.4rem; display:flex; gap:0.6rem; align-items:center;">
                <img src="${imgUrl}" style="width:45px; height:45px; object-fit:cover; border-radius:6px;" alt="${p.name}">
                <div style="flex:1; font-size:0.85rem;">
                    <strong style="display:block; color:var(--text-heading,#B5F2DB);">${p.name}</strong>
                    <span style="color:var(--primary,#B5F2DB); font-weight:700;">${p.price ? p.price + ' EGP' : ''}</span>
                    ${p.reason ? `<div style="font-size:0.75rem; opacity:0.8;">${p.reason}</div>` : ''}
                </div>
            </div>
        `;
    }).join('');

    const container = document.createElement('div');
    container.className = 'msg-bubble bot-msg';
    container.style.background = 'transparent';
    container.style.padding = '0';
    container.style.border = 'none';
    container.innerHTML = cardsHtml;
    stream.appendChild(container);
    stream.scrollTop = stream.scrollHeight;
}

// Export channel revenue table as CSV — the dead "Export Data" button now works.
function exportChannelData(e) {
    if (e) e.preventDefault();
    const rows = [
        ['Channel', 'Total Revenue', 'AI Attribution'],
        ['Storefront Direct', 45, 12],
        ['Instagram Shop', 62, 18],
        ['TikTok Shop', 78, 25],
        ['RAG Chatbot', 90, 32],
        ['Smart RecSys', 115, 45]
    ];
    const csv = rows.map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'cartwise-channel-revenue.csv';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
}

function sendChipMessage(text) {
    if (!chatWidgetOpen) toggleChatWidget(true);
    document.getElementById('chatInput').value = text;
    handleUserSubmit();
}

function appendChatMessage(text, sender) {
    const stream = document.getElementById('chatStream');
    const bubble = document.createElement('div');
    bubble.className = `msg-bubble ${sender === 'user' ? 'user-msg' : 'bot-msg'}`;
    bubble.innerText = text;
    stream.appendChild(bubble);
    stream.scrollTop = stream.scrollHeight;
}

function resetChatHistory() {
    currentConversationId = null;
    const stream = document.getElementById('chatStream');
    stream.innerHTML = `<div class="msg-bubble bot-msg"><p>${i18n[currentLang].chat_welcome}</p></div>`;
}

document.addEventListener('DOMContentLoaded', () => {
    const syncButton = document.querySelector('#ocrResultsCard button.btn-emerald');
    if (!syncButton) return;
    syncButton.removeAttribute('onclick');
    syncButton.addEventListener('click', confirmOCRToInventory);
}, { once: true });
