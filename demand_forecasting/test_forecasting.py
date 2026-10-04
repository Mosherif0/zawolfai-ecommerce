"""
Forecasting tests.

The tests that matter here are the LEAKAGE ones. A forecasting pipeline that
looks excellent and leaks will fail silently in production, and no metric will
tell you - the numbers will simply be too good. So each feature is checked
directly against a hand-built panel with a known answer.

Run:  pytest test_forecasting.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from forecast import (  # noqa: E402
    Config, build_features, build_panel, feature_columns, make_split, score,
)


@pytest.fixture(scope="module")
def cfg():
    return Config()


@pytest.fixture
def tiny_transactions():
    """Three articles over a long calendar with a known, hand-checkable plan."""
    rows = []
    # article 1 sells in week 0 only
    # article 2 sells in weeks 0 and 1
    # article 3 never sells in the first weeks
    plan = {1: [0], 2: [0, 1], 3: []}
    for article, weeks in plan.items():
        for week in weeks:
            for day in range(3):
                rows.append({
                    "t_dat": pd.Timestamp("2018-01-01") + pd.Timedelta(weeks=week, days=day),
                    "customer_id": f"c{day}",
                    "article_id": article,
                    "price": 0.01,
                    "sales_channel_id": 1,
                })
    # extend the calendar so make_split has enough weeks
    for week in range(40):
        rows.append({
            "t_dat": pd.Timestamp("2018-01-01") + pd.Timedelta(weeks=week, days=1),
            "customer_id": "cx",
            "article_id": 3,
            "price": 0.01,
            "sales_channel_id": 2,
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# the panel must be dense
# --------------------------------------------------------------------------

def test_panel_includes_zero_sales_weeks(tiny_transactions, cfg):
    """
    Regression: a groupby-only build drops every zero row, which is ~95% of the
    data. Every AUC and recall number then becomes meaningless.
    """
    panel = build_panel(tiny_transactions, cfg)
    assert (panel.y == 0).any(), "panel has no zero-sales rows"
    assert len(panel) == panel.week_start.nunique() * 3


def test_panel_counts_sales_not_revenue(tiny_transactions, cfg):
    panel = build_panel(tiny_transactions, cfg)
    assert panel.y.sum() == len(tiny_transactions)


def test_incomplete_final_week_is_dropped(tiny_transactions, cfg):
    df = tiny_transactions.copy()
    df.loc[len(df)] = {
        "t_dat": pd.Timestamp("2019-06-30"), "customer_id": "cz",
        "article_id": 1, "price": 0.01, "sales_channel_id": 1,
    }
    panel = build_panel(df, cfg)
    assert panel.week_start.max() < pd.Timestamp("2018-12-31")


# --------------------------------------------------------------------------
# leakage
# --------------------------------------------------------------------------

def test_features_never_use_the_current_week(tiny_transactions, cfg):
    """
    THE critical test. At horizon 1 a feature for week t may only use data up
    to week t-1. If any feature moves when only y[t] changes, it leaks.
    """
    panel = build_panel(tiny_transactions, cfg)
    features = build_features(panel, cfg)

    # perturb only the LAST week's target and confirm earlier features are unmoved
    perturbed = panel.copy()
    last_week = perturbed.week_start.max()
    mask = perturbed.week_start == last_week
    perturbed.loc[mask, "y"] = perturbed.loc[mask, "y"] + 1000

    p2 = build_features(perturbed, cfg)

    earlier = features.week_start < last_week
    for column in feature_columns(features):
        if column in ("sin_w", "cos_w"):
            continue
        a = features.loc[earlier, column].to_numpy(dtype=float)
        b = p2.loc[earlier, column].to_numpy(dtype=float)
        assert np.allclose(a, b, equal_nan=True), \
            f"'{column}' changed for EARLIER weeks when only the last week moved -> leakage"


def test_cum_sales_excludes_the_target_week(tiny_transactions, cfg):
    """
    cum_sales is the classic trap: a plain cumsum already contains the week's
    own sales, which is the value being predicted.
    """
    panel = build_panel(tiny_transactions, cfg)
    features = build_features(panel, cfg)

    # The fixture sells 3 units in week 0 and 3 in week 1 (one per day), so:
    #   week 0 -> y=3, cum=0   (nothing has happened yet)
    #   week 1 -> y=3, cum=3   (week 0 is now history)
    #   week 2 -> y=0, cum=6   (both weeks are history)
    # If cum_sales included the current week the first row would already be 3.
    solo = features[features.article_id == 2].sort_values("week_start").reset_index(drop=True)
    assert list(solo.y.astype(int))[:3] == [3, 3, 0]
    assert solo.cum_sales.iloc[0] == 0, "week 0 has no prior history"
    assert solo.cum_sales.iloc[1] == 3, "week 1 must see week 0 only"
    assert solo.cum_sales.iloc[2] == 6, "week 2 must see weeks 0 and 1"


def test_lag_1_is_previous_week(tiny_transactions, cfg):
    panel = build_panel(tiny_transactions, cfg)
    features = build_features(panel, cfg).sort_values(["article_id", "week_start"])
    solo = features[features.article_id == 2].reset_index(drop=True)
    for i in range(1, len(solo)):
        assert solo.lag_1.iloc[i] == solo.y.iloc[i - 1]


def test_horizon_two_shifts_further(tiny_transactions, cfg):
    """With H=2 the features must look two weeks back, not one."""
    two = Config()
    two.horizon = 2
    panel = build_panel(tiny_transactions, two)
    features = build_features(panel, two).sort_values(["article_id", "week_start"])
    solo = features[features.article_id == 2].reset_index(drop=True)
    for i in range(2, len(solo)):
        assert solo.lag_1.iloc[i] == solo.y.iloc[i - 2]


def test_ever_flag_is_not_peeking(tiny_transactions, cfg):
    """'ever sold before' must be 0 in the article's very first week."""
    panel = build_panel(tiny_transactions, cfg)
    features = build_features(panel, cfg).sort_values(["article_id", "week_start"])
    first = features[features.article_id == 2].reset_index(drop=True)
    assert first.ever.iloc[0] == 0


# --------------------------------------------------------------------------
# split
# --------------------------------------------------------------------------

def test_split_is_chronological(tiny_transactions, cfg):
    panel = build_panel(tiny_transactions, cfg)
    data = build_features(panel, cfg)
    small = Config()
    small.test_weeks = 3
    split = make_split(data, small)

    assert split.train.week_start.max() < split.validation.week_start.min()
    assert split.validation.week_start.max() < split.test.week_start.min()


def test_test_window_is_the_requested_length(tiny_transactions, cfg):
    panel = build_panel(tiny_transactions, cfg)
    data = build_features(panel, cfg)
    small = Config()
    small.test_weeks = 3
    split = make_split(data, small)
    assert split.test.week_start.nunique() == 3


def test_split_refuses_a_short_history(cfg):
    """Better to fail loudly than to silently produce a meaningless test set."""
    weeks = pd.date_range("2018-01-01", periods=6, freq="7D")
    tiny = pd.DataFrame({
        "week_start": np.repeat(weeks, 2),
        "article_id": [1, 2] * len(weeks),
        "y": 0, "rev": 0.0, "online": 0.0, "pmean": 0.0,
    })
    with pytest.raises(ValueError):
        make_split(tiny, Config(test_weeks=8))


def test_validation_train_precedes_validation(tiny_transactions, cfg):
    panel = build_panel(tiny_transactions, cfg)
    data = build_features(panel, cfg)
    small = Config()
    small.test_weeks = 3
    split = make_split(data, small)
    assert split.validation_train.week_start.max() < split.validation.week_start.min()


# --------------------------------------------------------------------------
# features + metrics
# --------------------------------------------------------------------------

def test_no_target_or_identifier_in_features(tiny_transactions, cfg):
    """article_id is an identifier; as a feature it memorises instead of generalising."""
    panel = build_panel(tiny_transactions, cfg)
    data = build_features(panel, cfg)
    feats = feature_columns(data)
    for forbidden in ("y", "rev", "article_id", "week_start", "pmean", "online"):
        assert forbidden not in feats


def test_expected_feature_count(tiny_transactions, cfg):
    panel = build_panel(tiny_transactions, cfg)
    data = build_features(panel, cfg)
    assert len(feature_columns(data)) == 21


def test_score_separates_count_from_classification():
    """MAE answers 'how many'; AUC answers 'will it sell at all'."""
    truth = np.array([0, 0, 0, 1, 2, 3])
    good = np.array([0.1, 0.2, 0.1, 1.1, 1.9, 2.8])
    flat = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5])

    good_scores = score(truth, good, "good")
    flat_scores = score(truth, flat, "flat")

    assert good_scores["MAE"] < flat_scores["MAE"]
    # a flat predictor has no ranking power at all
    assert flat_scores["AUC"] == pytest.approx(0.5, abs=0.01)
    assert good_scores["AUC"] > 0.9


def test_poisson_deviance_rejects_negative_predictions():
    """Poisson deviance is undefined for negatives, which is why we clip."""
    from sklearn.metrics import mean_poisson_deviance

    with pytest.raises(ValueError):
        mean_poisson_deviance([0, 1], [-0.5, 1.0])
    # our scorer must not raise
    assert score([0, 1], [-0.5, 1.0], "negative")["PoisDev"] > 0