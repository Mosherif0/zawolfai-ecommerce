# E-Commerce Sales Forecasting

A machine learning project for forecasting weekly product-level sales from historical e-commerce transaction data.

## Project Overview

This project builds a time-series forecasting pipeline at the **article-week** level. The goal is to use historical demand patterns to estimate future product sales and provide useful signals for inventory planning, product prioritization, and demand monitoring.

Because weekly product demand is highly sparse (about **95.2% zero-sales observations**), the project evaluates both standard forecasting metrics and business-oriented metrics.

## Objectives

- Aggregate transaction-level data into weekly product sales.
- Build a complete product-week panel, including zero-sales weeks.
- Create leakage-free time-series features.
- Establish rolling-demand baselines.
- Compare LightGBM and XGBoost forecasting models.
- Evaluate predictions using regression and demand-classification metrics.
- Assess model usefulness at aggregated and ranking levels.

## Data Preparation

Transaction data is aggregated by:

- `article_id`
- `week_start`

The target is:

```text
y = weekly sales count
```

The final weekly panel contains **385,060 product-week observations**, with an average weekly sales count of **0.052** and approximately **95.2% zero-sales observations**.

The final incomplete week was removed before modeling so that the test period would not contain an artificial drop caused by missing days.

## Feature Engineering

The enhanced pipeline creates 21 forecasting features, including:

### Lag Features
- `lag_1`
- `lag_2`
- `lag_3`
- `lag_4`
- `lag_8`

### Rolling Demand Features
- `roll_4`
- `roll_8`
- `roll_12`
- `roll_26`
- `roll_4_max`

### Additional Features
- Exponentially weighted demand (`ewm_03`)
- Cumulative sales
- Whether the article has sold before
- Weeks since last sale
- Cumulative revenue
- Historical mean price
- Online sales share
- Global lagged demand
- Global rolling demand
- Seasonal sine/cosine features

All forecasting features are constructed using information available before the prediction period to avoid future-data leakage.

## Forecasting Setup

A chronological split is used instead of a random train/test split.

- **Forecast horizon:** 1 week
- **Test period:** last 8 complete weeks
- **Validation period:** 8 weeks before the test period
- **Test set:** 59,240 observations
- **Training set:** 296,200 observations

The improved models use a **Poisson objective**, which is appropriate for the sparse count nature of weekly sales.

## Models Evaluated

### Baselines
- Rolling 4-week mean
- Rolling 12-week mean

### Machine Learning Models
- Original LightGBM using squared-error loss
- LightGBM with Poisson objective and enhanced features
- XGBoost with Poisson objective and enhanced features
- 50/50 LightGBM + XGBoost blend

## Model Performance

Lower MAE, RMSE, and Poisson Deviance are better. Higher R², AUC, and PR-AUC are better.

| Model | MAE | RMSE | R² | Poisson Deviance | AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| Naive: Rolling-4 Mean | 0.1097 | 0.2849 | -0.0722 | 1.2189 | 0.5702 | 0.1021 |
| Naive: Rolling-12 Mean | 0.1066 | 0.2650 | 0.0720 | 0.9020 | 0.5954 | 0.1321 |
| Original LightGBM (L2) | 0.1062 | 0.2612 | 0.0986 | 0.3386 | 0.6199 | 0.1493 |
| **LightGBM Poisson + New Features** | **0.1031** | **0.2573** | **0.1253** | **0.3140** | **0.7358** | 0.1923 |
| XGBoost Poisson + New Features | 0.1032 | 0.2576 | 0.1236 | 0.3126 | 0.7413 | **0.1944** |
| Blend (LightGBM + XGBoost) | **0.1031** | 0.2574 | 0.1251 | 0.3132 | 0.7385 | 0.1931 |

### Model Selection

The **LightGBM Poisson model with enhanced time-series features** was selected as the final forecasting model because it achieved the lowest MAE and the highest R² among the individual forecasting models.

However, LightGBM and XGBoost performed very similarly. XGBoost achieved a slightly higher AUC and PR-AUC, while LightGBM achieved slightly better MAE, RMSE, and R².

## Business-Oriented Evaluation

Since article-level weekly demand is extremely sparse, the project also evaluates predictions at more useful business levels.

### Weekly Total Demand
The final blended prediction achieved:

**MAPE: 16.3%**

for weekly total sales.

### 8-Week Article Totals

After aggregating predictions and actual sales across the full 8-week test period:

- **R²: 0.558**
- **AUC: 0.819**

### Top-100 Weekly Product Ranking

Selecting the 100 products with the highest predicted demand each week resulted in:

- **40.2%** of selected products actually sold
- **5.9%** overall weekly sell rate
- **6.8× lift** over the base rate

This shows why ranking and aggregated demand evaluation are useful complements to article-week regression metrics.

## Key Insights

- Weekly article-level demand is highly sparse, with approximately 95% zero-sales observations.
- Individual article-level R² is therefore relatively limited.
- Adding richer lag, rolling, recency, cumulative, global-demand, and seasonal features improved forecasting performance.
- The Poisson objective produced better results than the original squared-error LightGBM setup.
- LightGBM and XGBoost are very close in predictive performance on this dataset.
- Aggregated and ranking-based evaluation provides a more informative business perspective than relying on article-level R² alone.

## Dataset Limitations

- Each article sells approximately 2.7 times per year, with a median of 1 sale, making weekly article-level forecasting very sparse.
- Only about 38% of sold articles are present in the available `inventory.csv`, so product attributes were not sufficiently available for useful forecasting features.
- `inventory.sales_count` represents full-year sales and would leak future information, so it was not used as a forecasting feature.
- The article universe contains products with at least one sale during 2018, which introduces selection bias compared with a live production catalogue.

## Project Structure

```text
E-Commerce-Forecasting/
│
├── data/
│   └── transactions_forecasting.csv
│
├── notebooks/
│   ├── Forcasting_original.ipynb
│   └── Forecasting_enhanced.ipynb
│
├── models/
│   ├── lightgbm_poisson.pkl
│   └── xgboost_poisson.pkl
│
├── README.md
└── requirements.txt
```

## Technologies

- Python
- Pandas
- NumPy
- Scikit-learn
- LightGBM
- XGBoost
- Matplotlib
- Seaborn
- Plotly

## Future Improvements

- Forecast the live product catalogue rather than only products with historical sales.
- Incorporate richer product metadata.
- Add promotion and price-change information.
- Include customer-level behavior.
- Explore multi-step and probabilistic forecasting.
- Deploy the forecasting pipeline as an inventory-planning application.

## Author

**Nada Rashad**

Data Science & AI Projects
