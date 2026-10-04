import numpy as np
import pandas as pd
from pathlib import Path
import joblib

DATA_DIR = Path(__file__).resolve().parent


def build_features(p, H=1):
    p = p.copy()
    G = p.groupby("article_id")

    for k in [1, 2, 3, 4, 8]:
        p[f"lag_{k}"] = G["y"].shift(k + H - 1)

    base = G["y"].shift(H)
    gb = base.groupby(p.article_id)

    for w in [4, 8, 12, 26]:
        p[f"roll_{w}"] = gb.transform(
            lambda x: x.rolling(w, min_periods=1).mean()
        )

    p["roll_4_max"] = gb.transform(
        lambda x: x.rolling(4, min_periods=1).max()
    )

    p["ewm_03"] = gb.transform(
        lambda x: x.ewm(alpha=0.3).mean()
    )

    p["cum_sales"] = gb.transform(
        lambda x: x.fillna(0).cumsum()
    )

    p["ever"] = (p.cum_sales > 0).astype(int)

    last = (
        p.week_start.where(base.fillna(0) > 0)
        .groupby(p.article_id)
        .ffill()
    )

    p["since_last"] = (
        (p.week_start - last).dt.days / 7
    ).fillna(99)

    p["rev_cum"] = p.groupby("article_id")["rev"].transform(
        lambda x: x.shift(H).fillna(0).cumsum()
    )

    p["price_mean"] = p.groupby("article_id")["pmean"].transform(
        lambda x: x.shift(H).ffill()
    )

    p["online_share"] = (
        p.groupby("article_id")["online"]
        .transform(lambda x: x.shift(H).fillna(0).cumsum())
        / p.cum_sales.replace(0, np.nan)
    )

    tot = p.groupby("week_start").y.sum().shift(H)

    p["tot_lag"] = p.week_start.map(tot)

    p["tot_roll4"] = p.week_start.map(
        tot.rolling(4, min_periods=1).mean()
    )

    p["sin_w"] = np.sin(
        2 * np.pi *
        p.week_start.dt.isocalendar().week.astype(int) / 52
    )

    p["cos_w"] = np.cos(
        2 * np.pi *
        p.week_start.dt.isocalendar().week.astype(int) / 52
    )

    return p

transactions = pd.read_csv(
    DATA_DIR / "transactions_forecasting.csv",
    parse_dates=["t_dat"]
)

# Last week only has Dec-31 (1 day) -> incomplete week, remove it
transactions = transactions[
    transactions["t_dat"] < "2018-12-31"
].copy()

transactions["week_start"] = (
    transactions["t_dat"]
    .dt.to_period("W-SUN")
    .dt.start_time
)

weeks = pd.date_range(
    transactions.week_start.min(),
    transactions.week_start.max(),
    freq="7D"
)

articles = transactions.article_id.unique()

panel = pd.MultiIndex.from_product(
    [weeks, articles],
    names=["week_start", "article_id"]
).to_frame(index=False)

g = transactions.groupby(
    ["week_start", "article_id"]
).agg(
    y=("price", "size"),
    rev=("price", "sum"),
    online=(
        "sales_channel_id",
        lambda s: (s == 1).sum()
    ),
    pmean=("price", "mean")
).reset_index()

p = panel.merge(
    g,
    on=["week_start", "article_id"],
    how="left"
)

for c in ["y", "rev", "online"]:
    p[c] = p[c].fillna(0)

p = p.sort_values(
    ["article_id", "week_start"]
).reset_index(drop=True)

H = 1

d = build_features(p, H)

NON_FEATURES = [
    "week_start",
    "y",
    "rev",
    "online",
    "pmean",
    "article_id"
]

FEATURES = [
    c for c in d.columns
    if c not in NON_FEATURES
]

print("Number of features:", len(FEATURES))
print("Features:", FEATURES)


MODEL_PATH = DATA_DIR / "lgbm_model.pkl"

model = joblib.load(MODEL_PATH)

print("Model loaded successfully!")

def forecast_article(article_id):
    # Get the latest available week
    last_week = p["week_start"].max()

    # Create the next week
    next_week = last_week + pd.Timedelta(weeks=1)

    # Create one future row for every article
    future = pd.DataFrame({
        "week_start": next_week,
        "article_id": p["article_id"].unique(),
        "y": 0,
        "rev": 0,
        "online": 0,
        "pmean": np.nan
    })

    # Add future rows to historical data
    p_extended = pd.concat(
        [p, future],
        ignore_index=True
    )

    p_extended = p_extended.sort_values(
        ["article_id", "week_start"]
    ).reset_index(drop=True)

    # Build features including the future week
    d_future = build_features(
        p_extended,
        H=1
    )

    # Get the future row for the requested article
    row = d_future[
        (d_future["article_id"] == article_id) &
        (d_future["week_start"] == next_week)
    ]

    if row.empty:
        raise ValueError(
            f"Article {article_id} not found."
        )

    # Predict demand
    prediction = model.predict(
        row[FEATURES]
    )[0]

    return {
        "article_id": int(article_id),
        "forecast_week": next_week.strftime("%Y-%m-%d"),
        "predicted_demand": float(prediction)
    }

