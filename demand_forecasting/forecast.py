"""
Weekly demand forecasting pipeline.

A production-shaped version of Forecasting_enhanced.ipynb: same features and
same models, but as importable functions with no hidden state, so it can be
re-run, tested and deployed.

Why a script and not only the notebook
---------------------------------------
The notebook holds the logic in execution order, which means a reviewer has
to read top-to-bottom and trust that cell 7 ran after cell 5. Here the panel
build, the feature build and the split are functions with explicit arguments,
so the test suite can pin the parts that are easy to get subtly wrong -
especially leakage.

Method
------
Target: weekly sales count per article. The data is ~95% zeros, so the models
use a Poisson objective rather than squared error, and evaluation separates
three questions a single MAE cannot answer:

  1. Is the COUNT right?             MAE / RMSE / Poisson deviance
  2. Will it sell AT ALL?            AUC / PR-AUC on (y > 0)
  3. Does it matter to the business? weekly totals, window totals, top-K lift

Run:
    python forecast.py                 # full pipeline, writes to output/
    python forecast.py --quick         # fewer trees, fast end-to-end check
"""

from __future__ import annotations

import argparse
import json
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE
OUTPUT_DIR = BASE / "output"
MODELS_DIR = BASE / "models"

TRANSACTIONS_CSV = DATA_DIR / "transactions_forecasting.csv"
INVENTORY_CSV = DATA_DIR / "inventory.csv"

#: Columns that must never reach the model as features.
NON_FEATURES = ["week_start", "y", "rev", "online", "pmean", "article_id"]

RANDOM_STATE = 42


# --------------------------------------------------------------------------
# configuration
# --------------------------------------------------------------------------

@dataclass
class Config:
    """Every knob in one place, so a run is reproducible from this object."""

    horizon: int = 1              # weeks ahead to predict
    test_weeks: int = 8           # length of the held-out window
    drop_last_week: bool = True   # the final week is incomplete
    incomplete_before: str = "2018-12-31"

    rolling_windows: Tuple[int, ...] = (4, 8, 12, 26)
    lag_weeks: Tuple[int, ...] = (1, 2, 3, 4, 8)
    ewm_alpha: float = 0.3

    lgb_params: Dict = field(default_factory=lambda: dict(
        objective="poisson", n_estimators=400, learning_rate=0.03,
        num_leaves=31, min_child_samples=100, subsample=0.8,
        subsample_freq=1, colsample_bytree=0.8, reg_lambda=5,
        random_state=RANDOM_STATE, verbose=-1,
    ))
    xgb_params: Dict = field(default_factory=lambda: dict(
        objective="count:poisson", n_estimators=400, learning_rate=0.03,
        max_depth=5, min_child_weight=20, subsample=0.8,
        colsample_bytree=0.8, reg_lambda=5, random_state=RANDOM_STATE,
        tree_method="hist",
    ))

    @classmethod
    def quick(cls) -> "Config":
        """Same pipeline, fewer trees - for a fast end-to-end check."""
        cfg = cls()
        cfg.lgb_params = {**cfg.lgb_params, "n_estimators": 60}
        cfg.xgb_params = {**cfg.xgb_params, "n_estimators": 60}
        return cfg


# --------------------------------------------------------------------------
# step 1: build the weekly panel
# --------------------------------------------------------------------------

def build_panel(transactions: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """
    Aggregate transactions into a dense article x week panel.

    The panel must be DENSE. An article that did not sell in a given week is a
    real observation with y = 0, and it is ~95% of them. Building it as a
    left-join onto the full cross-product is what makes those zeros exist;
    a groupby alone would silently drop them and make every recall number a
    lie.
    """
    df = transactions.copy()
    df["t_dat"] = pd.to_datetime(df["t_dat"])

    if cfg.drop_last_week:
        df = df[df["t_dat"] < cfg.incomplete_before]

    df["week_start"] = df["t_dat"].dt.to_period("W-SUN").dt.start_time

    weeks = pd.date_range(df.week_start.min(), df.week_start.max(), freq="7D")
    articles = df.article_id.unique()

    panel = pd.MultiIndex.from_product(
        [weeks, articles], names=["week_start", "article_id"]
    ).to_frame(index=False)

    agg = df.groupby(["week_start", "article_id"]).agg(
        y=("price", "size"),
        rev=("price", "sum"),
        online=("sales_channel_id", lambda s: (s == 1).sum()),
        pmean=("price", "mean"),
    ).reset_index()

    panel = panel.merge(agg, on=["week_start", "article_id"], how="left")
    for column in ("y", "rev", "online"):
        panel[column] = panel[column].fillna(0)

    panel = panel.sort_values(["article_id", "week_start"]).reset_index(drop=True)
    return panel


# --------------------------------------------------------------------------
# step 2: features
# --------------------------------------------------------------------------

def build_features(panel: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """
    Create the forecasting features, all shifted so nothing from the
    prediction window can leak backwards into the training window.

    With horizon H every aggregate is taken over `shift(H)` - the value as it
    was known H weeks before the row being predicted. `lag_1` is `shift(H)`,
    `lag_2` is `shift(H + 1)`, and so on.
    """
    df = panel.copy()
    H = cfg.horizon
    grouped = df.groupby("article_id")

    for k in cfg.lag_weeks:
        df[f"lag_{k}"] = grouped["y"].shift(k + H - 1)

    base = grouped["y"].shift(H)
    base_by_article = base.groupby(df.article_id)

    for window in cfg.rolling_windows:
        df[f"roll_{window}"] = base_by_article.transform(
            lambda x: x.rolling(window, min_periods=1).mean()
        )

    df["roll_4_max"] = base_by_article.transform(
        lambda x: x.rolling(4, min_periods=1).max()
    )
    df["ewm_03"] = base_by_article.transform(lambda x: x.ewm(alpha=cfg.ewm_alpha).mean())

    # Cumsums MUST use the shifted series, not the raw one: the raw cumsum at
    # week t already contains week t's sales, which is the target.
    df["cum_sales"] = base_by_article.transform(lambda x: x.fillna(0).cumsum())
    df["ever"] = (df.cum_sales > 0).astype(int)

    last_sale = df.week_start.where(base.fillna(0) > 0).groupby(df.article_id).ffill()
    df["since_last"] = ((df.week_start - last_sale).dt.days / 7).fillna(99)

    df["rev_cum"] = df.groupby("article_id")["rev"].transform(
        lambda x: x.shift(H).fillna(0).cumsum()
    )
    df["price_mean"] = df.groupby("article_id")["pmean"].transform(
        lambda x: x.shift(H).ffill()
    )
    df["online_share"] = (
        df.groupby("article_id")["online"].transform(lambda x: x.shift(H).fillna(0).cumsum())
        / df.cum_sales.replace(0, np.nan)
    )

    # Global demand level: lets the model learn the pre-Christmas rise without
    # anyone hard-coding a date.
    totals = df.groupby("week_start").y.sum().shift(H)
    df["tot_lag"] = df.week_start.map(totals)
    df["tot_roll4"] = df.week_start.map(totals.rolling(4, min_periods=1).mean())

    week_of_year = df.week_start.dt.isocalendar().week.astype(int)
    df["sin_w"] = np.sin(2 * np.pi * week_of_year / 52)
    df["cos_w"] = np.cos(2 * np.pi * week_of_year / 52)

    return df


def feature_columns(frame: pd.DataFrame) -> List[str]:
    return [c for c in frame.columns if c not in NON_FEATURES]


# --------------------------------------------------------------------------
# step 3: split
# --------------------------------------------------------------------------

@dataclass
class Split:
    train: pd.DataFrame
    validation_train: pd.DataFrame   # what the threshold model is fitted on
    validation: pd.DataFrame
    test: pd.DataFrame
    test_start: pd.Timestamp
    description: str = ""


def make_split(data: pd.DataFrame, cfg: Config) -> Split:
    """
    Chronological split - never random.

    A random split would let the model learn week 50 to predict week 5, which
    is impossible in production and inflates every metric. Validation sits
    immediately before the test window so a threshold can be tuned without
    touching the test set.
    """
    weeks = np.array(sorted(data.week_start.unique()))
    needed = 3 * cfg.test_weeks + 5
    if len(weeks) < needed:
        raise ValueError(
            f"only {len(weeks)} weeks available; need at least {needed} for an "
            f"{cfg.test_weeks}-week test window"
        )

    test_start = weeks[-cfg.test_weeks]
    val_start = weeks[-2 * cfg.test_weeks]

    # Early weeks are kept: min_periods=1 makes them computable, and dropping
    # them would lose the training data that teaches the model what "no history
    # yet" looks like.
    base = data[data.week_start >= weeks[4]]

    # The three windows must be strictly ordered and must not overlap. The
    # horizon gap exists because a row at week t is only predictable from
    # information available H weeks earlier; with H=1 the gap is zero, and the
    # original `< test_start - gap` bound silently let train run INTO the
    # validation window.
    test = base[base.week_start >= test_start].copy()
    validation = base[(base.week_start >= val_start) & (base.week_start < test_start)]
    train = base[base.week_start < val_start]
    validation_train = train

    if not (train.week_start.max() < validation.week_start.min()
            < test.week_start.min()):
        raise AssertionError(
            "split windows overlap or are out of order: "
            f"train<={train.week_start.max()}, "
            f"val={validation.week_start.min()}..{validation.week_start.max()}, "
            f"test>={test.week_start.min()}"
        )

    return Split(
        train=train, validation_train=validation_train,
        validation=validation, test=test, test_start=test_start,
        description=(f"train {len(train):,} | val {len(validation):,} | "
                     f"test {len(test):,} from {test_start.date()}"),
    )


# --------------------------------------------------------------------------
# step 4: metrics
# --------------------------------------------------------------------------

def score(y, pred, name: str) -> Dict:
    """Regression metrics + a demand-classification view of the same scores."""
    from sklearn.metrics import (
        average_precision_score, mean_absolute_error, mean_poisson_deviance,
        mean_squared_error, r2_score, roc_auc_score,
    )

    pred = np.asarray(pred, dtype=float)
    truth = np.asarray(y)

    return {
        "model": name,
        "MAE": mean_absolute_error(truth, pred),
        "RMSE": float(np.sqrt(mean_squared_error(truth, pred))),
        "R2": r2_score(truth, pred),
        "PoisDev": mean_poisson_deviance(truth, np.clip(pred, 1e-6, None)),
        "AUC": roc_auc_score(truth > 0, pred),
        "PR_AUC": average_precision_score(truth > 0, pred),
    }


def business_metrics(test: pd.DataFrame, top_k: int = 100) -> Dict:
    """
    The numbers a merchandiser actually acts on.

    Article-week R2 is capped near zero because the data is ~95% zeros; these
    aggregate views are what tell you whether the forecast is usable.
    """
    from sklearn.metrics import r2_score, roc_auc_score

    out: Dict = {}

    weekly = test.groupby("week_start")[["y", "pred"]].sum()
    out["weekly_mape"] = float((abs(weekly.y - weekly.pred) / weekly.y).mean() * 100)

    article = test.groupby("article_id")[["y", "pred"]].sum()
    out["window_r2"] = float(r2_score(article.y, article.pred))
    out["window_auc"] = float(roc_auc_score(article.y > 0, article.pred))

    hits = [
        (group.sort_values("pred", ascending=False).head(top_k).y > 0).mean()
        for _, group in test.groupby("week_start")
    ]
    hit_rate = float(np.mean(hits))
    base_rate = float((test.y > 0).mean())
    out["top100_sell_rate"] = hit_rate * 100
    out["base_rate"] = base_rate * 100
    out["lift"] = hit_rate / base_rate if base_rate else float("nan")

    return out


def tune_threshold(validation: pd.DataFrame, pred: np.ndarray) -> Tuple[float, Dict]:
    """
    Pick a sales-probability threshold on VALIDATION only.

    0.5 is meaningless here: with 95% zeros almost nothing clears it, so the
    operating point has to be chosen against the precision/recall trade-off
    that matters - flagging articles to reorder.
    """
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

    best_threshold, best_f1 = 0.5, -1.0
    rows = []
    for threshold in np.linspace(0.02, 0.6, 59):
        predicted = pred > threshold
        truth = validation.y > 0
        f1 = f1_score(truth, predicted)
        rows.append({
            "threshold": float(threshold),
            "accuracy": accuracy_score(truth, predicted),
            "precision": precision_score(truth, predicted, zero_division=0),
            "recall": recall_score(truth, predicted),
            "f1": f1,
        })
        if f1 > best_f1:
            best_f1, best_threshold = f1, float(threshold)

    return best_threshold, {"best_f1": best_f1, "curve": rows}


# --------------------------------------------------------------------------
# step 5: the run
# --------------------------------------------------------------------------

def run(cfg: Optional[Config] = None, save_models: bool = True) -> Dict:
    from lightgbm import LGBMRegressor
    from xgboost import XGBRegressor

    cfg = cfg or Config()
    OUTPUT_DIR.mkdir(exist_ok=True)
    MODELS_DIR.mkdir(exist_ok=True)

    print("[1/6] loading data")
    transactions = pd.read_csv(TRANSACTIONS_CSV, parse_dates=["t_dat"])

    print("[2/6] building weekly panel")
    panel = build_panel(transactions, cfg)
    zero_share = (panel.y == 0).mean() * 100
    print(f"      {len(panel):,} article-weeks | "
          f"mean weekly sales {panel.y.mean():.3f} | zeros {zero_share:.1f}%")

    print("[3/6] building features")
    data = build_features(panel, cfg)
    features = feature_columns(data)
    print(f"      {len(features)} features")

    print("[4/6] splitting")
    split = make_split(data, cfg)
    print(f"      {split.description}")

    print("[5/6] fitting and scoring")
    train, test = split.train, split.test
    results: List[Dict] = []

    results.append(score(test.y, test.roll_4, "Naive: rolling-4 mean"))
    results.append(score(test.y, test.roll_12, "Naive: rolling-12 mean"))

    m_lgb = LGBMRegressor(**cfg.lgb_params).fit(train[features], train.y)
    test = test.copy()
    test["p_lgb"] = m_lgb.predict(test[features])
    results.append(score(test.y, test.p_lgb, "LightGBM Poisson + features"))

    m_xgb = XGBRegressor(**cfg.xgb_params).fit(train[features], train.y)
    test["p_xgb"] = m_xgb.predict(test[features])
    results.append(score(test.y, test.p_xgb, "XGBoost Poisson + features"))

    test["pred"] = 0.5 * test.p_lgb + 0.5 * test.p_xgb
    results.append(score(test.y, test.pred, "Blend (LGBM + XGB)"))

    # The threshold model is fitted ONLY on validation_train and scored on
    # validation, so neither the threshold nor its reported score has ever seen
    # the test window.
    m_val = LGBMRegressor(**cfg.lgb_params).fit(
        split.validation_train[features], split.validation_train.y
    )
    val_pred = m_val.predict(split.validation[features])
    threshold, tuning = tune_threshold(split.validation, val_pred)
    print(f"      threshold tuned on validation: {threshold:.3f}")

    print("[6/6] business metrics")
    business = business_metrics(test)

    table = pd.DataFrame(results).set_index("model").round(4)
    print()
    print(table.to_string())

    importance = pd.Series(m_lgb.booster_.feature_importance("gain"),
                           index=features).sort_values(ascending=False)

    report = {
        "config": {
            "horizon": cfg.horizon,
            "test_weeks": cfg.test_weeks,
            "panel_rows": int(len(panel)),
            "articles": int(panel.article_id.nunique()),
            "weeks": int(panel.week_start.nunique()),
            "zero_share_pct": round(float(zero_share), 2),
            "mean_weekly_sales": round(float(panel.y.mean()), 4),
            "features": features,
        },
        "split": split.description,
        "metrics": results,
        "business": {k: round(v, 4) for k, v in business.items()},
        "threshold": threshold,
        "threshold_best_f1": round(tuning["best_f1"], 4),
        "feature_importance": {k: round(float(v), 1) for k, v in importance.items()},
    }

    table.to_csv(OUTPUT_DIR / "metrics.csv")
    test[["week_start", "article_id", "y", "pred", "p_lgb", "p_xgb"]].to_csv(
        OUTPUT_DIR / "predictions.csv", index=False)
    importance.to_csv(OUTPUT_DIR / "feature_importance.csv", header=["gain"])
    pd.DataFrame(tuning["curve"]).to_csv(OUTPUT_DIR / "threshold_curve.csv", index=False)
    (OUTPUT_DIR / "report.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8")

    if save_models:
        m_lgb.booster_.save_model(str(MODELS_DIR / "lgbm_poisson.txt"))
        m_xgb.save_model(MODELS_DIR / "xgb_poisson.json")
        print(f"      models saved to {MODELS_DIR}")

    print(f"\nreport -> {OUTPUT_DIR / 'report.json'}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Weekly demand forecasting")
    parser.add_argument("--quick", action="store_true",
                        help="fewer trees, for a fast end-to-end check")
    parser.add_argument("--no-save", action="store_true",
                        help="do not write model files")
    args = parser.parse_args()

    cfg = Config.quick() if args.quick else Config()
    run(cfg, save_models=not args.no_save)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())