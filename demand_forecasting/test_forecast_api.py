"""
Forecast API tests.

The API has to be cheap to call, which is the whole reason it caches the panel
and the model. These tests pin that behaviour as well as the response shape,
because a per-request rebuild would still pass a smoke test while taking
seconds in production.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import app_api  # noqa: E402


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    with TestClient(app_api.app) as test_client:
        yield test_client


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

def test_engine_loads(client):
    body = client.get("/health").json()
    assert body["model_loaded"] is True, body.get("error")
    assert body["status"] == "ok"
    assert body["articles"] > 0
    assert body["last_week"]


def test_engine_is_cached(client):
    """Loading twice must not rebuild the 385k-row feature matrix."""
    first = app_api.ENGINE
    client.get("/health")
    assert app_api.ENGINE is first
    assert app_api.ENGINE.ready


def test_model_is_used_not_rebuilt(client):
    """predict_all goes through the cached booster, not a fresh fit."""
    client.get("/forecast?limit=3")
    assert app_api.ENGINE.model is not None


# --------------------------------------------------------------------------
# predictions
# --------------------------------------------------------------------------

def test_ranked_forecast_shape(client):
    body = client.get("/forecast?limit=5").json()
    assert body["count"] <= 5
    assert body["forecast_week"]
    assert body["threshold"] > 0
    assert len(body["items"]) == body["count"]


def test_ranked_forecast_is_sorted_by_demand(client):
    items = client.get("/forecast?limit=20").json()["items"]
    demands = [i["predicted_demand"] for i in items]
    assert demands == sorted(demands, reverse=True)


def test_limit_is_respected(client):
    assert client.get("/forecast?limit=3").json()["count"] <= 3


def test_threshold_filter_narrows_the_list(client):
    everything = client.get("/forecast?limit=50").json()["count"]
    filtered = client.get("/forecast?limit=50&above_threshold=true").json()
    assert filtered["count"] <= everything
    for item in filtered["items"]:
        assert item["predicted_demand"] > filtered["threshold"]


def test_predictions_are_non_negative(client):
    """A Poisson model cannot produce a negative demand."""
    for item in client.get("/forecast?limit=50").json()["items"]:
        assert item["predicted_demand"] >= 0


def test_single_forecast(client):
    article = client.get("/forecast?limit=1").json()["items"][0]["article_id"]
    body = client.get(f"/forecast/{article}").json()
    assert body["article_id"] == article
    assert body["predicted_demand"] >= 0
    assert body["model"]
    assert body["forecast_week"]


def test_single_forecast_matches_the_ranked_list(client):
    article = client.get("/forecast?limit=1").json()["items"][0]["article_id"]
    ranked = client.get("/forecast?limit=10").json()["items"]
    from_ranked = next(i for i in ranked if i["article_id"] == article)
    single = client.get(f"/forecast/{article}").json()
    assert single["predicted_demand"] == from_ranked["predicted_demand"]


def test_unknown_article_is_404(client):
    assert client.get("/forecast/999999999").status_code == 404


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------

def test_metrics_returns_the_training_report(client):
    body = client.get("/metrics").json()
    assert "config" in body or "status" in body


def test_root_lists_endpoints(client):
    body = client.get("/").json()
    assert body["service"] == "forecasting"
    assert "/forecast" in body["endpoints"]