"""
Forecast API for the demand-forecasting service.

The pipeline in forecast.py is a batch job; this turns the trained model into
a service the rest of the backend can call, so the chatbot can answer "how many
of X should I reorder" without loading LightGBM in its own process.

    GET  /health          service + model status
    GET  /forecast/{id}   one product, next week
    GET  /forecast        many products, ranked by predicted demand
    GET  /metrics         the training report

The model and the feature frame are loaded ONCE per worker. Rebuilding the
385k-row feature matrix per request would cost seconds; that is the reason the
original forecasting_service.py was unusable behind an API.
"""

from __future__ import annotations

import json
import threading
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE
MODELS_DIR = BASE / "models"
OUTPUT_DIR = BASE / "output"

TRANSACTIONS_CSV = DATA_DIR / "transactions_forecasting.csv"
MODEL_FILE = MODELS_DIR / "lgbm_poisson.txt"
REPORT_FILE = OUTPUT_DIR / "report.json"

HORIZON_WEEKS = 1


# --------------------------------------------------------------------------
# schemas
# --------------------------------------------------------------------------

class ForecastItem(BaseModel):
    article_id: int
    name: Optional[str] = None
    predicted_demand: float
    probability_of_sale: float = Field(
        ..., description="P(at least one sale) from the tuned threshold"
    )


class ForecastOne(BaseModel):
    article_id: int
    forecast_week: str
    predicted_demand: float
    probability_of_sale: float
    last_observed_sales: Optional[float] = None
    weeks_since_last_sale: Optional[float] = None
    model: str


class RankedForecast(BaseModel):
    forecast_week: str
    count: int
    threshold: float
    items: List[ForecastItem]


class Health(BaseModel):
    status: str
    service: str
    model_loaded: bool
    articles: int
    last_week: Optional[str] = None
    threshold: Optional[float] = None
    model_file: Optional[str] = None
    error: Optional[str] = None


# --------------------------------------------------------------------------
# the forecast engine
# --------------------------------------------------------------------------

class ForecastEngine:
    """
    Holds the panel, the features and the model.

    Loading happens once under a lock so a burst of concurrent requests at
    startup cannot each build the matrix.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._ready = False
        self.error: Optional[str] = None

        self.model = None
        self.frame: Optional[pd.DataFrame] = None
        self._predictions: Optional[pd.DataFrame] = None
        self.features: List[str] = []
        self.threshold = 0.12
        self.last_week: Optional[pd.Timestamp] = None
        self.report: Dict = {}

    # -- loading ---------------------------------------------------------
    def load(self) -> None:
        with self._lock:
            if self._ready:
                return
            try:
                import forecast as pipeline
                from lightgbm import Booster

                if not MODEL_FILE.is_file():
                    self.error = f"model not found: {MODEL_FILE}"
                    return

                cfg = pipeline.Config()
                transactions = pd.read_csv(TRANSACTIONS_CSV, parse_dates=["t_dat"])
                panel = pipeline.build_panel(transactions, cfg)
                data = pipeline.build_features(panel, cfg)
                self.features = pipeline.feature_columns(data)
                self.frame = data
                self.last_week = data.week_start.max()

                self.model = Booster(model_file=str(MODEL_FILE))
                self.model.feature_name()

                if REPORT_FILE.is_file():
                    self.report = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
                    self.threshold = float(self.report.get("threshold", self.threshold))

                self._ready = True
                self.error = None
            except Exception as exc:
                self.error = f"{type(exc).__name__}: {exc}"

    @property
    def ready(self) -> bool:
        return self._ready

    # -- prediction ------------------------------------------------------
    def _future_frame(self) -> pd.DataFrame:
        """
        One extra week for every article, with the features rebuilt over the
        extended history.

        Rebuilding is correct here and cheap enough because the frame is cached:
        lag_1 for the new week must come from the real last week, not from a
        stale snapshot.
        """
        import forecast as pipeline

        next_week = self.last_week + timedelta(weeks=HORIZON_WEEKS)
        future = pd.DataFrame({
            "week_start": next_week,
            "article_id": self.frame["article_id"].unique(),
            "y": 0, "rev": 0.0, "online": 0.0, "pmean": np.nan,
        })
        extended = pd.concat([self.frame, future], ignore_index=True)
        extended = extended.sort_values(["article_id", "week_start"]).reset_index(drop=True)
        return pipeline.build_features(extended, pipeline.Config())

    def predict_all(self) -> pd.DataFrame:
        """
        Predictions for every article in the next week.

        Cached: rebuilding the feature matrix over the extended history took
        ~18 seconds per call, so any sane client timeout gave up before the
        model answered, while the model itself predicts in milliseconds. The
        panel is fixed for the life of the process (the training CSV does not
        change while the service runs), so the result is computed once and
        reused. invalidate() drops it if that assumption ever changes.
        """
        if self._predictions is not None:
            return self._predictions

        import forecast as pipeline

        future_frame = self._future_frame()
        next_week = self.last_week + timedelta(weeks=HORIZON_WEEKS)
        target = future_frame[future_frame.week_start == next_week].copy()
        target["prediction"] = self.model.predict(target[self.features])

        self._predictions = target
        return target

    def invalidate(self) -> None:
        """Drop the cached predictions, e.g. after reloading training data."""
        self._predictions = None


    def names(self) -> Dict[int, str]:
        inventory = DATA_DIR / "inventory.csv"
        if not inventory.is_file():
            return {}
        frame = pd.read_csv(inventory, usecols=["article_id", "prod_name"])
        return {int(r.article_id): str(r.prod_name) for r in frame.itertuples()}


ENGINE = ForecastEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    ENGINE.load()
    if ENGINE.ready:
        print(f"[ OK ] forecasting ready: {ENGINE.frame['article_id'].nunique()} articles")

        # Warm the prediction cache at startup. Doing it lazily means the first
        # caller pays ~18s, and any client timeout smaller than that gets an
        # "unavailable" answer instead of a number.
        import time as _time
        _t0 = _time.perf_counter()
        try:
            ENGINE.predict_all()
            print(f"[ OK ] predictions warm in {(_time.perf_counter() - _t0):.1f}s")
        except Exception as exc:
            print(f"[WARN] could not warm predictions: {exc}")

    else:
        print(f"[WARN] forecasting not ready: {ENGINE.error}")
    yield


app = FastAPI(
    title="Zawolf AI - Demand Forecasting",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_engine() -> ForecastEngine:
    if not ENGINE.ready:
        # Loading lazily too, so a worker that started before the model
        # finished writing still recovers instead of 503-ing forever.
        ENGINE.load()
    if not ENGINE.ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"forecasting unavailable: {ENGINE.error}",
        )
    return ENGINE


# --------------------------------------------------------------------------
# endpoints
# --------------------------------------------------------------------------

@app.get("/health", response_model=Health, tags=["Health"])
async def health() -> Health:
    """Never raises: a health check that 500s tells you nothing."""
    engine = _require_engine_safe()
    return Health(
        status="ok" if engine.ready else "degraded",
        service="forecasting",
        model_loaded=engine.ready,
        articles=int(engine.frame["article_id"].nunique()) if engine.ready else 0,
        last_week=str(engine.last_week.date()) if engine.last_week else None,
        threshold=engine.threshold if engine.ready else None,
        model_file=MODEL_FILE.name if MODEL_FILE.is_file() else None,
        error=engine.error,
    )


def _require_engine_safe() -> ForecastEngine:
    if not ENGINE.ready:
        ENGINE.load()
    return ENGINE


@app.get("/forecast/{article_id}", response_model=ForecastOne, tags=["Forecast"])
async def forecast_one(article_id: int) -> ForecastOne:
    """Predicted demand for a single product next week."""
    engine = _require_engine()
    predictions = engine.predict_all()

    row = predictions[predictions.article_id == article_id]
    if row.empty:
        raise HTTPException(status_code=404, detail="article not found")

    record = row.iloc[0]
    prediction = float(record["prediction"])
    history = engine.frame[engine.frame.article_id == article_id].sort_values("week_start")

    return ForecastOne(
        article_id=article_id,
        forecast_week=str((engine.last_week + timedelta(weeks=HORIZON_WEEKS)).date()),
        predicted_demand=round(prediction, 4),
        probability_of_sale=round(1.0 if prediction > engine.threshold else 0.0, 3),
        last_observed_sales=float(history.y.iloc[-1]) if len(history) else None,
        weeks_since_last_sale=float(record.get("since_last", 0) or 0) or None,
        model="LightGBM Poisson",
    )


@app.get("/forecast", response_model=RankedForecast, tags=["Forecast"])
async def forecast_ranked(limit: int = Query(20, ge=1, le=200),
                          above_threshold: bool = Query(
                              False, description="only products likely to sell")
                          ) -> RankedForecast:
    """
    Next week's predictions, ranked by demand.

    `above_threshold` returns only the products worth acting on: with ~95% zero
    weeks, the top of the list is mostly noise unless a cut is applied.
    """
    engine = _require_engine()
    predictions = engine.predict_all()
    predictions = predictions.sort_values("prediction", ascending=False)

    if above_threshold:
        predictions = predictions[predictions.prediction > engine.threshold]

    predictions = predictions.head(limit)
    names = engine.names()

    return RankedForecast(
        forecast_week=str((engine.last_week + timedelta(weeks=HORIZON_WEEKS)).date()),
        count=len(predictions),
        threshold=engine.threshold,
        items=[
            ForecastItem(
                article_id=int(r.article_id),
                name=names.get(int(r.article_id)),
                predicted_demand=round(float(r.prediction), 4),
                probability_of_sale=1.0 if r.prediction > engine.threshold else 0.0,
            )
            for r in predictions.itertuples()
        ],
    )


@app.get("/metrics", tags=["Forecast"])
async def metrics() -> Dict:
    """The training report, so a caller can see how good the model is."""
    engine = _require_engine()
    return engine.report or {"status": "no report file; run forecast.py first"}


@app.get("/", tags=["Forecast"])
async def root() -> Dict:
    return {
        "service": "forecasting",
        "endpoints": ["/health", "/forecast", "/forecast/{article_id}", "/metrics"],
        "docs": "/docs",
    }