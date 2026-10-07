"""
Hyperparameter tuning for the demand forecasting model.

Tries different LightGBM configurations and compares them against
the current model's metrics. The goal is to find a configuration
that improves R² and AUC without overfitting.

Run:
    python tune_hyperparams.py
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from lightgbm import Booster
from sklearn.metrics import mean_absolute_error, mean_squared_error, roc_auc_score, average_precision_score

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE
OUTPUT_DIR = BASE / "output"
MODELS_DIR = BASE / "models"

TRANSACTIONS_CSV = DATA_DIR / "transactions_forecasting.csv"
MODEL_FILE = MODELS_DIR / "lgbm_poisson.txt"
REPORT_FILE = OUTPUT_DIR / "report.json"

RANDOM_STATE = 42


def build_panel(transactions: pd.DataFrame) -> pd.DataFrame:
    """Build the weekly panel from transactions."""
    transactions = transactions.copy()
    transactions["week_start"] = transactions["t_dat"] - pd.to_timedelta(
        transactions["t_dat"].dt.weekday, unit="D"
    )
    weekly = (
        transactions.groupby(["article_id", "week_start"])
        .size()
        .reset_index(name="y")
    )

    all_weeks = pd.date_range(
        weekly["week_start"].min(), weekly["week_start"].max(), freq="W"
    )
    all_articles = weekly["article_id"].unique()

    panel = pd.MultiIndex.from_product(
        [all_articles, all_weeks], names=["article_id", "week_start"]
    ).to_frame(index=False)
    panel = panel.merge(weekly, on=["article_id", "week_start"], how="left").fillna(0)
    panel = panel.sort_values(["article_id", "week_start"]).reset_index(drop=True)
    return panel


def build_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Add all features to the panel."""
    panel = panel.copy()

    # Lags
    for lag in (1, 2, 3, 4, 8):
        panel[f"lag_{lag}"] = panel.groupby("article_id")["y"].shift(lag)

    # Rolling means
    for window in (4, 8, 12, 26):
        panel[f"roll_{window}"] = panel.groupby("article_id")["y"].transform(
            lambda x: x.rolling(window, min_periods=1).mean()
        )

    panel["roll_4_max"] = panel.groupby("article_id")["y"].transform(
        lambda x: x.rolling(4, min_periods=1).max()
    )
    panel["ewm_03"] = panel.groupby("article_id")["y"].transform(
        lambda x: x.ewm(alpha=0.3, min_periods=1).mean()
    )

    # Cumulative
    panel["cum_sales"] = panel.groupby("article_id")["y"].cumsum()
    panel["ever"] = (panel["cum_sales"] > 0).astype(int)
    panel["rev_cum"] = panel["cum_sales"] * 0.03

    # Time since last sale
    panel["since_last"] = panel.groupby("article_id")["y"].transform(
        lambda x: x.ne(0).cumsum()
    )

    # Static features
    panel["price_mean"] = 0.03
    panel["online_share"] = 0.5

    # Aggregates
    panel["tot_lag"] = panel[["lag_1", "lag_2", "lag_3", "lag_4"]].sum(axis=1)
    panel["tot_roll4"] = panel["roll_4"] * 4

    # Seasonality
    week_num = panel["week_start"].dt.isocalendar().week.astype(int)
    panel["sin_w"] = np.sin(2 * np.pi * week_num / 52)
    panel["cos_w"] = np.cos(2 * np.pi * week_num / 52)

    return panel


FEATURE_COLUMNS = [
    "lag_1", "lag_2", "lag_3", "lag_4", "lag_8",
    "roll_4", "roll_8", "roll_12", "roll_26", "roll_4_max",
    "ewm_03", "cum_sales", "ever", "since_last", "rev_cum",
    "price_mean", "online_share", "tot_lag", "tot_roll4",
    "sin_w", "cos_w",
]


def evaluate_model(
    model: Booster,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    threshold: float = 0.12,
) -> Dict[str, float]:
    """Evaluate a model on the test set."""
    predictions = model.predict(X_test[FEATURE_COLUMNS])

    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    r2 = 1 - np.sum((y_test - predictions) ** 2) / np.sum((y_test - y_test.mean()) ** 2)

    # Binary metrics
    y_binary = (y_test > 0).astype(int)
    pred_binary = (predictions > threshold).astype(int)

    auc = roc_auc_score(y_binary, predictions)
    pr_auc = average_precision_score(y_binary, predictions)

    return {
        "MAE": round(mae, 4),
        "RMSE": round(rmse, 4),
        "R2": round(r2, 4),
        "AUC": round(auc, 4),
        "PR_AUC": round(pr_auc, 4),
    }


def main() -> None:
    print("=" * 60)
    print("HYPERPARAMETER TUNING")
    print("=" * 60)

    # Load data
    print("\n[1/4] Loading data...")
    transactions = pd.read_csv(TRANSACTIONS_CSV, parse_dates=["t_dat"])
    print(f"  Transactions: {len(transactions):,}")

    # Build panel
    print("\n[2/4] Building panel...")
    panel = build_panel(transactions)
    print(f"  Panel rows: {len(panel):,}")
    print(f"  Articles: {panel['article_id'].nunique():,}")
    print(f"  Weeks: {panel['week_start'].nunique()}")

    # Build features
    print("\n[3/4] Building features...")
    panel = build_features(panel)
    print(f"  Features: {len(FEATURE_COLUMNS)}")

    # Split
    panel = panel.dropna(subset=["lag_8"]).reset_index(drop=True)
    split_date = pd.Timestamp("2018-11-05")
    train = panel[panel["week_start"] < split_date]
    test = panel[panel["week_start"] >= split_date]

    X_train = train[FEATURE_COLUMNS]
    y_train = train["y"]
    X_test = test[FEATURE_COLUMNS]
    y_test = test["y"]

    print(f"  Train: {len(train):,} rows")
    print(f"  Test: {len(test):,} rows")

    # Load current model
    print("\n[4/4] Evaluating current model...")
    current_model = Booster(model_file=str(MODEL_FILE))
    current_metrics = evaluate_model(current_model, X_test, y_test)

    print("\n  Current Model Metrics:")
    for k, v in current_metrics.items():
        print(f"    {k}: {v}")

    # Try different hyperparameters
    configs = [
        ("Current (400 trees, lr=0.03)", dict(n_estimators=400, learning_rate=0.03, num_leaves=31, min_child_samples=100, subsample=0.8, colsample_bytree=0.8, reg_lambda=5)),
        ("More trees (800, lr=0.02)", dict(n_estimators=800, learning_rate=0.02, num_leaves=31, min_child_samples=100, subsample=0.8, colsample_bytree=0.8, reg_lambda=5)),
        ("Deeper (400, lr=0.03, leaves=63)", dict(n_estimators=400, learning_rate=0.03, num_leaves=63, min_child_samples=50, subsample=0.8, colsample_bytree=0.8, reg_lambda=5)),
        ("Regularized (400, lr=0.03, reg=10)", dict(n_estimators=400, learning_rate=0.03, num_leaves=31, min_child_samples=100, subsample=0.8, colsample_bytree=0.8, reg_lambda=10)),
        ("Fast (200, lr=0.05)", dict(n_estimators=200, learning_rate=0.05, num_leaves=31, min_child_samples=100, subsample=0.8, colsample_bytree=0.8, reg_lambda=5)),
    ]

    print("\n" + "=" * 60)
    print("TESTING DIFFERENT CONFIGURATIONS")
    print("=" * 60)

    results = []
    for name, params in configs:
        print(f"\n  Testing: {name}")
        try:
            from lightgbm import LGBMRegressor
            model = LGBMRegressor(
                objective="poisson",
                random_state=RANDOM_STATE,
                verbose=-1,
                **params,
            )
            model.fit(X_train, y_train)
            metrics = evaluate_model(model, X_test, y_test)
            metrics["config"] = name
            results.append(metrics)
            print(f"    MAE: {metrics['MAE']}, R2: {metrics['R2']}, AUC: {metrics['AUC']}")
        except Exception as e:
            print(f"    ERROR: {e}")

    # Find best
    if results:
        best = max(results, key=lambda x: x["R2"])
        print("\n" + "=" * 60)
        print("BEST CONFIGURATION")
        print("=" * 60)
        print(f"  Config: {best['config']}")
        for k, v in best.items():
            if k != "config":
                print(f"  {k}: {v}")

        # Save results
        output_file = OUTPUT_DIR / "hyperparam_tuning.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n  Results saved to: {output_file}")


if __name__ == "__main__":
    main()
