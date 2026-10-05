/* ==========================================================================
   CARTWISE AI — APPLICATION JAVASCRIPT CONTROLLER
   Handles: i18n Translation (AR/EN), Theme Switching, Sidebar Routing, 
            Sophian & DemandForecaster ApexCharts, ROI Calculator, OCR Intake, 
            and RAG Chatbot Integration
   ========================================================================== */

let currentLang = 'ar';
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
        nav_storefront: "المتجر والشات بوت",
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
        alerts_title: "تنبيهات المخزون الحرجة",
        btn_view_all: "عرض الكل",
        btn_reorder: "إعادة طلب",
        badge_healthy: "مخزون ممتاز",
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
        nav_storefront: "Store & Chatbot",
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
        alerts_title: "Low-Stock Urgent Alerts",
        btn_view_all: "View All",
        btn_reorder: "Reorder",
        badge_healthy: "Optimal Stock",
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
        user_role: "Brand Owner",
        lbl_theme: "Theme Mode",
        ph_search: "Search SKUs, invoices, forecast..."
    }
};

// Initialize Application
document.addEventListener("DOMContentLoaded", () => {
    updateLanguageDOM();
    updateROICalculator();
    initCharts();
    loadCatalogProducts();
});

// View Navigation Switcher
function switchView(viewId) {
    document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));
    document.querySelectorAll('.menu-item').forEach(btn => btn.classList.remove('active'));

    const targetSection = document.getElementById(`view-${viewId}`);
    if (targetSection) {
        targetSection.classList.add('active');
    }

    const activeNavBtn = document.querySelector(`.menu-item[data-view="${viewId}"]`);
    if (activeNavBtn) {
        activeNavBtn.classList.add('active');
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Refresh charts when entering dashboard or forecasting
    if (viewId === 'dashboard' || viewId === 'forecasting') {
        setTimeout(() => {
            if (salesChart) salesChart.render();
            if (categoryDonutChart) categoryDonutChart.render();
            if (channelBarChart) channelBarChart.render();
            if (forecastChart) forecastChart.render();
        }, 100);
    }
}

// Scroll Helper
function scrollToSection(id) {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
}

// Language Switcher Handler
function toggleLanguage() {
    currentLang = (currentLang === 'ar') ? 'en' : 'ar';
    document.documentElement.setAttribute('lang', currentLang);
    document.documentElement.setAttribute('dir', currentLang === 'ar' ? 'rtl' : 'ltr');
    document.getElementById('langText').innerText = currentLang === 'ar' ? 'English' : 'عربي';

    updateLanguageDOM();
    initCharts();
}

function updateLanguageDOM() {
    const langDict = i18n[currentLang];
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (langDict[key]) el.innerText = langDict[key];
    });

    document.querySelectorAll('[data-i18n-ph]').forEach(el => {
        const key = el.getAttribute('data-i18n-ph');
        if (langDict[key]) el.setAttribute('placeholder', langDict[key]);
    });
}

// Theme Switcher Handler
function toggleTheme() {
    currentTheme = (currentTheme === 'dark') ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', currentTheme);
    initCharts();
}

// Interactive Financial ROI Calculator
function updateROICalculator() {
    const orders = parseInt(document.getElementById('inputOrders').value);
    const skus = parseInt(document.getElementById('inputSKUs').value);
    const aov = parseInt(document.getElementById('inputAOV').value);

    document.getElementById('valOrders').innerText = orders.toLocaleString();
    document.getElementById('valSKUs').innerText = skus.toLocaleString();
    document.getElementById('valAOV').innerText = aov.toLocaleString() + ' EGP';

    // Calculations
    const extraRecSysRevenue = Math.round(orders * aov * 0.18);
    const preventedStockoutsLoss = Math.round(skus * 1200);
    const savedHours = Math.round((orders / 100) * 1.8);
    const totalVal = extraRecSysRevenue + preventedStockoutsLoss;

    document.getElementById('resTotalVal').innerText = totalVal.toLocaleString() + ' EGP';
    document.getElementById('resRecBoost').innerText = '+' + extraRecSysRevenue.toLocaleString() + ' EGP';
    document.getElementById('resStockout').innerText = preventedStockoutsLoss.toLocaleString() + ' EGP';
    document.getElementById('resHours').innerText = savedHours + ' Hours';
}

// Initialize ApexCharts (Colors Grounded in Customer Palette: #B5F2DB, #FFC933, #76D7B7, #042F34)
function initCharts() {
    const textColor = currentTheme === 'dark' ? '#B5F2DB' : '#16232B';
    const gridColor = currentTheme === 'dark' ? 'rgba(181, 242, 219, 0.1)' : 'rgba(4, 47, 52, 0.1)';

    // 1. Sales & AI Forecast Area Chart
    const salesOptions = {
        chart: { type: 'area', height: 320, toolbar: { show: false }, fontFamily: currentLang === 'ar' ? 'Cairo' : 'Inter' },
        colors: ['#B5F2DB', '#FFC933'],
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

    // 2. Category Breakdown Donut Chart
    const donutOptions = {
        chart: { type: 'donut', height: 320, fontFamily: currentLang === 'ar' ? 'Cairo' : 'Inter' },
        colors: ['#B5F2DB', '#FFC933', '#76D7B7', '#E4EEF0', '#042F34'],
        labels: currentLang === 'ar' 
            ? ['الملابس القطنية', 'الجاكيتات', 'الهوديز', 'البناطيل', 'الإكسسوارات'] 
            : ['Cotton Apparel', 'Outerwear', 'Hoodies', 'Pants', 'Accessories'],
        series: [40, 25, 20, 10, 5],
        legend: { position: 'bottom', labels: { colors: textColor } },
        stroke: { show: false }
    };

    if (categoryDonutChart) categoryDonutChart.destroy();
    const donutEl = document.getElementById('categoryDonutChart');
    if (donutEl) {
        categoryDonutChart = new ApexCharts(donutEl, donutOptions);
        categoryDonutChart.render();
    }

    // 3. Sales Volume by Channel Bar Chart
    const barOptions = {
        chart: { type: 'bar', height: 300, toolbar: { show: false }, fontFamily: currentLang === 'ar' ? 'Cairo' : 'Inter' },
        colors: ['#B5F2DB', '#FFC933'],
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

    // 4. Demand Trend & Confidence Forecast Chart
    const demandOptions = {
        chart: { type: 'line', height: 320, toolbar: { show: false }, fontFamily: currentLang === 'ar' ? 'Cairo' : 'Inter' },
        colors: ['#B5F2DB', '#FFC933'],
        stroke: { curve: 'smooth', width: [3, 2], dashArray: [0, 5] },
        series: [
            { name: currentLang === 'ar' ? 'الطلب التاريخي' : 'Historical Demand', data: [120, 135, 128, 142, 150, 165, 180] },
            { name: currentLang === 'ar' ? 'توقع Model LGBM' : 'LGBM Model Prediction', data: [null, null, null, null, null, 165, 195, 210, 230, 245] }
        ],
        xaxis: { categories: ['W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7', 'W8', 'W9', 'W10'], labels: { style: { colors: textColor } } },
        yaxis: { labels: { style: { colors: textColor } } },
        grid: { borderColor: gridColor }
    };

    if (forecastChart) forecastChart.destroy();
    const forecastEl = document.getElementById('demandTrendChart');
    if (forecastEl) {
        forecastChart = new ApexCharts(forecastEl, demandOptions);
        forecastChart.render();
    }
}

// OCR Upload & Verification Table Handler
function triggerFileSelect() {
    document.getElementById('ocrFileInput').click();
}

function handleFileSelected(event) {
    if (event.target.files && event.target.files[0]) {
        loadSampleOCRInvoice();
    }
}

function loadSampleOCRInvoice() {
    const overlay = document.getElementById('scanOverlay');
    overlay.style.display = 'flex';

    setTimeout(() => {
        overlay.style.display = 'none';

        const items = [
            { name: 'H&M Cotton Ankle Socks 3-Pack - Black / M', qty: 100, cost: 30, retail: 85, conf: 98.5, flag: false },
            { name: 'CartWise Heavyweight Cotton Tee - Off White / L', qty: 50, cost: 120, retail: 350, conf: 96.2, flag: false },
            { name: 'Raw Denim Overshirt - Indigo / XL', qty: 25, cost: 280, retail: 790, conf: 84.1, flag: true },
            { name: 'Fleece Jogger Pants - Charcoal / M', qty: 40, cost: 150, retail: 420, conf: 94.8, flag: false }
        ];

        const tbody = document.getElementById('ocrTableBody');
        tbody.innerHTML = items.map(item => `
            <tr class="${item.flag ? 'row-flagged' : ''}">
                <td><strong>${item.name}</strong></td>
                <td>${item.qty}</td>
                <td>${item.cost} EGP</td>
                <td>${item.retail} EGP</td>
                <td>${(item.qty * item.cost).toLocaleString()} EGP</td>
                <td>
                    <span class="badge ${item.flag ? 'badge-amber' : 'badge-green'}">
                        ${item.conf}% ${item.flag ? '⚠️ Review' : '✓'}
                    </span>
                </td>
            </tr>
        `).join('');

        document.getElementById('ocrResultsCard').style.display = 'block';
        document.getElementById('ocrResultsCard').scrollIntoView({ behavior: 'smooth' });
    }, 1500);
}

function confirmOCRToInventory() {
    alert(currentLang === 'ar' 
        ? 'تمت مطابقة المستند وتحديث مخزون المتجر بنجاح 🚀 (4 أصناف أضيفت للمخزون)' 
        : 'Invoice verified and 4 catalog items successfully synced to inventory! 🚀');
}

// Demand Forecasting Model Run Simulator
function runForecastModel() {
    const sku = document.getElementById('skuSelect').value;
    const model = document.getElementById('modelEngineSelect').value;
    alert(currentLang === 'ar'
        ? `تم تشغيل نموذج ${model.toUpperCase()} لكود المنتج ${sku} بنجاح! التوقع جاهز.`
        : `Forecast model ${model.toUpperCase()} executed successfully for SKU ${sku}!`);
}

// Catalog Products Loader
function loadCatalogProducts() {
    const sampleProducts = [
        { name: 'H&M Cotton Socks 3-Pack', price: '85 EGP', img: 'https://images.unsplash.com/photo-1586350977771-b3b0abd50c82?w=400&q=80', tag: 'Cross-Sell Ready' },
        { name: 'CartWise Puffer Jacket - Navy', price: '1,250 EGP', img: 'https://images.unsplash.com/photo-1544441893-675973e31985?w=400&q=80', tag: 'High Demand' },
        { name: 'Oversized Hoodie - Vintage Grey', price: '450 EGP', img: 'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=400&q=80', tag: 'Trending' },
        { name: 'Slim Fit Cargo Pants - Olive', price: '520 EGP', img: 'https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=400&q=80', tag: 'Healthy Stock' }
    ];

    const grid = document.getElementById('productsGrid');
    if (grid) {
        grid.innerHTML = sampleProducts.map(p => `
            <div class="product-card">
                <img src="${p.img}" class="product-img" alt="${p.name}">
                <div class="product-title">${p.name}</div>
                <div class="product-price">${p.price}</div>
                <span class="badge badge-purple">${p.tag}</span>
                <button class="btn btn-secondary btn-sm" onclick="sendChipMessage('عاوز أعرف تفاصيل ومقاسات ${p.name}')">
                    💬 اسأل المساعد الذكي
                </button>
            </div>
        `).join('');
    }
}

// RAG Chatbot Integration Handler
async function handleUserSubmit() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;

    appendChatMessage(msg, 'user');
    input.value = '';

    // Send POST /api/chat to FastAPI backend
    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: msg,
                conversation_id: currentConversationId
            })
        });

        const data = await res.json();
        if (data.conversation_id) {
            currentConversationId = data.conversation_id;
        }

        appendChatMessage(data.message || 'حصل مشكلة بسيطة، جرب مرة تانية.', 'bot');
    } catch (err) {
        appendChatMessage('تعذر الاتصال بالخادم الآن.', 'bot');
    }
}

function sendChipMessage(text) {
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
