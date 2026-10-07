"""
Shared configuration for the Zawolf AI backend.

All four services read from here so a path is defined once. Today each
project hard-codes its own copy of the catalog location, which is how the
recommendation service ended up resolving `data/` relative to `core/` and
failing to load - a silent bug that only appears when the working directory
changes.

Environment variables (all optional, all have working defaults):

    CATALOG_CSV        path to clean_catalog.csv
    CATALOG_IMAGES_DIR product photos
    INVENTORY_CSV      product attributes
    TRANSACTIONS_CSV   transaction history
    DB_HOST            set to switch the warehouse to PostgreSQL
    DB_NAME / DB_USER / DB_PASSWORD
    OCR_LANGUAGE       en (default) or ar
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env files so a single file - or per-service files - can configure the
# whole backend. Order matters:
#
#   1. workspace root  (ZAWOLF_WORKSPACE/.env)  - shared settings
#   2. each service dir (.../ocr/.env)          - service-specific overrides
#
# A service file is loaded AFTER the root and with override=True so it wins;
# loading the root alone would silently miss ocr/.env and report SQLite even
# while the OCR service is talking to PostgreSQL.
_HERE = Path(__file__).resolve()
_ROOT_ENV = _HERE.parent / ".env"
if _ROOT_ENV.is_file():
    load_dotenv(_ROOT_ENV, override=False)

for _service in ("ocr", "demand_forecasting",
                 "recommendation_system/zawolfai-ecommerce-Re",
                 "conversational-ai-mvp"):
    _service_env = _HERE.parent / _service / ".env"
    if _service_env.is_file():
        load_dotenv(_service_env, override=True)

# --------------------------------------------------------------------------
# workspace layout
# --------------------------------------------------------------------------

WORKSPACE = Path(os.getenv("ZAWOLF_WORKSPACE", str(_HERE.parent)))
RECOMMENDATION_DIR = WORKSPACE / "recommendation_system" / "zawolfai-ecommerce-Re"
FORECASTING_DIR = WORKSPACE / "demand_forecasting"
OCR_DIR = WORKSPACE / "ocr"
CHATBOT_DIR = Path(os.getenv("CHATBOT_DIR", str(WORKSPACE / "conversational-ai-mvp")))

# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------

def _path(env_name: str, default: Path) -> Path:
    return Path(os.getenv(env_name, str(default)))


CATALOG_CSV = _path("CATALOG_CSV", RECOMMENDATION_DIR / "data" / "processed" / "clean_catalog.csv")
CATALOG_IMAGES_DIR = _path("CATALOG_IMAGES_DIR", RECOMMENDATION_DIR / "data" / "images")
INVENTORY_CSV = _path("INVENTORY_CSV", FORECASTING_DIR / "inventory.csv")
TRANSACTIONS_CSV = _path("TRANSACTIONS_CSV", FORECASTING_DIR / "transactions_forecasting.csv")

FORECAST_MODELS_DIR = FORECASTING_DIR / "models"
FORECAST_OUTPUT_DIR = FORECASTING_DIR / "output"
OCR_OUTPUT_DIR = OCR_DIR / "output"

# --------------------------------------------------------------------------
# warehouse
# --------------------------------------------------------------------------

DB_HOST: Optional[str] = os.getenv("DB_HOST")
DB_PORT: str = os.getenv("DB_PORT", "5432")
DB_NAME: str = os.getenv("DB_NAME", "zawolf_ocr")
DB_USER: str = os.getenv("DB_USER", "postgres")
DB_PASSWORD: Optional[str] = os.getenv("DB_PASSWORD")
SQLITE_PATH: Path = _path("SQLITE_PATH", OCR_OUTPUT_DIR / "inventory.db")

def warehouse_backend() -> str:
    return "postgres" if DB_HOST else "sqlite"


# --------------------------------------------------------------------------
# OCR
# --------------------------------------------------------------------------

OCR_LANGUAGE: str = os.getenv("OCR_LANGUAGE", "en")
OCR_MIN_CONFIDENCE: float = float(os.getenv("OCR_MIN_CONFIDENCE", "0.30"))

RECEIPT_ACCEPT_THRESHOLD: float = float(os.getenv("RECEIPT_ACCEPT_THRESHOLD", "0.55"))


# --------------------------------------------------------------------------
# services
# --------------------------------------------------------------------------

#: name -> (directory, module:app, default port)
SERVICES = {
    "recommendations": (RECOMMENDATION_DIR, "app_api:app", 8100),
    "ocr":            (OCR_DIR, "app:app", 8200),
    "chatbot":        (CHATBOT_DIR, "app.main:app", 8300),
    "forecasting":    (FORECASTING_DIR, "app_api:app", 8400),
}


def describe() -> dict:
    """Snapshot of the configuration - useful as a /health payload."""
    return {
        "workspace": str(WORKSPACE),
        "catalog_csv": {"path": str(CATALOG_CSV), "exists": CATALOG_CSV.is_file()},
        "catalog_images": {"path": str(CATALOG_IMAGES_DIR),
                           "exists": CATALOG_IMAGES_DIR.is_dir()},
        "transactions_csv": {"path": str(TRANSACTIONS_CSV),
                             "exists": TRANSACTIONS_CSV.is_file()},
        "inventory_csv": {"path": str(INVENTORY_CSV), "exists": INVENTORY_CSV.is_file()},
        "warehouse": {
            "backend": warehouse_backend(),
            "database": DB_NAME if DB_HOST else str(SQLITE_PATH),
        },
        "ocr": {"language": OCR_LANGUAGE, "min_confidence": OCR_MIN_CONFIDENCE},
        "services": {name: {"dir": str(d), "target": t, "port": p}
                     for name, (d, t, p) in SERVICES.items()},
    }


def validate() -> list:
    """Return a list of human-readable problems; empty means all good."""
    problems = []
    if not CATALOG_CSV.is_file():
        problems.append(f"catalog CSV missing: {CATALOG_CSV}")
    if not CATALOG_IMAGES_DIR.is_dir():
        problems.append(f"catalog images missing: {CATALOG_IMAGES_DIR}")
    if DB_HOST and not DB_PASSWORD:
        problems.append("DB_HOST is set but DB_PASSWORD is not")
    return problems


if __name__ == "__main__":
    import json
    print(json.dumps(describe(), indent=2))
    issues = validate()
    if issues:
        print("\nPROBLEMS:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\nconfiguration OK")