"""
Minimal web UI for the receipt pipeline.

English is the default; Arabic is a toggle. The UI is intentionally a single
static file - no build step, no framework - because the point is to make the
gate and the language switch visible, not to demo a design system.

Run:
    python app.py            # then open http://127.0.0.1:8000
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

BASE = Path(__file__).resolve().parent
UPLOAD_DIR = Path(tempfile.gettempdir()) / "zawolf_ocr_uploads"

app = FastAPI(title="OCR Receipt Pipeline", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Item(BaseModel):
    quantity: int
    name: str
    price: float


class ProcessResponse(BaseModel):
    ok: bool
    file: str
    lang: str
    status: str
    message: str
    items: List[Item] = []
    validation: Optional[Dict] = None
    saved: List[Dict] = []


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html_path = BASE / "static" / "index.html"
    if html_path.is_file():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>static/index.html missing</h1>", status_code=500)


@app.get("/api/languages")
async def languages() -> Dict:
    import language_config as lc

    return {
        "supported": list(lc.SUPPORTED),
        "active": lc.active(),
        "ocr_models": lc.ocr_languages(),
        "is_rtl": lc.is_rtl(),
    }


@app.post("/api/process", response_model=ProcessResponse)
async def process(
    file: UploadFile = File(...),
    lang: str = Form("en"),
    save: bool = Form("false"),
) -> ProcessResponse:
    """
    Run the whole pipeline on one uploaded image.

    `save=false` (the default) keeps the result local, which is what the UI
    uses for the preview-then-commit flow: a rejected image must never reach
    the inventory just because someone dropped it in.
    """
    import language_config as lc
    import validation as validation_mod

    chosen = lc.normalize(lang)
    if chosen not in lc.SUPPORTED:
        raise HTTPException(status_code=400, detail=f"unsupported language: {lang}")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "upload.jpg").suffix or ".jpg"
    target = UPLOAD_DIR / f"{Path(file.filename or 'upload').stem}{suffix}"

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="empty upload")
    target.write_bytes(content)

    work = UPLOAD_DIR / "work"
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)

    try:
        import ocr as ocr_mod
        import preprocessing as preprocessing_mod
        import receipt_parser as parser

        processed = work / "processed.jpg"
        preprocessing_mod.preprocess(target, processed)

        ocr_json = work / "ocr.json"
        ocr_data = ocr_mod.run_ocr(processed, work / "ocr.txt", ocr_json)

        verdict = validation_mod.validate(ocr_data, processed, chosen)
        if not verdict.is_receipt:
            return ProcessResponse(
                ok=False, file=target.name, lang=chosen,
                status="not_a_receipt",
                message=verdict.reason, validation=verdict.to_dict(),
            )

        items = parser.parse_rows(parser.group_rows(ocr_data))
        message = f"{len(items)} item(s) extracted"

        saved: List[Dict] = []
        if save and items:
            # Write through warehouse so the stock movements ledger is kept in
            # step with the scan, not only the flat products table.
            import warehouse as wh

            result = wh.record_receipt(items, source_file=target.name, language=chosen)
            saved = result["items"]
            message = f"{len(items)} item(s) extracted and saved"

        return ProcessResponse(
            ok=True, file=target.name, lang=chosen, status="ok",
            message=message,
            items=[Item(**i) for i in items],
            validation=verdict.to_dict(), saved=saved,
        )

    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@app.get("/api/inventory")
async def inventory() -> Dict:
    """
    Current stock, read from the warehouse layer.

    Read via warehouse rather than the older inventory module so this endpoint
    and /api/warehouse/* always agree; reading two different modules against
    the same database is how the numbers quietly drift apart.
    """
    import warehouse as wh

    return {"backend": wh.backend(), "products": wh.list_products()}


# --------------------------------------------------------------------------
# Warehouse API
#
# The receipt upload endpoint above is the "scan" side. These are the
# "manage the warehouse" side: browse, adjust, delete, audit.
# --------------------------------------------------------------------------

@app.get("/api/warehouse/products")
async def warehouse_products(search: Optional[str] = None,
                             category: Optional[str] = None,
                             limit: int = 200, offset: int = 0) -> Dict:
    import warehouse as wh

    return {"backend": wh.backend(),
            "products": wh.list_products(search=search, category=category,
                                          limit=limit, offset=offset)}


@app.get("/api/warehouse/products/{product_id}")
async def warehouse_product(product_id: int) -> Dict:
    import warehouse as wh

    detail = wh.get_product_detail(product_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="product not found")
    return detail


@app.get("/api/warehouse/receipts")
async def warehouse_receipts(limit: int = 50) -> Dict:
    import warehouse as wh

    return {"receipts": wh.list_receipts(limit=limit)}


@app.get("/api/warehouse/stats")
async def warehouse_stats() -> Dict:
    import warehouse as wh

    return wh.stats()


@app.post("/api/warehouse/products/{product_id}/adjust")
async def adjust(product_id: int, payload: Dict) -> Dict:
    import warehouse as wh

    try:
        delta = int(payload.get("delta", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="delta must be an integer")
    if delta == 0:
        raise HTTPException(status_code=400, detail="delta must not be zero")

    try:
        result = wh.adjust_stock(product_id, delta,
                                 reason=payload.get("reason", "adjustment"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if result is None:
        raise HTTPException(status_code=404, detail="product not found")
    return result


@app.delete("/api/warehouse/products/{product_id}")
async def remove_product(product_id: int) -> Dict:
    import warehouse as wh

    if not wh.delete_product(product_id):
        raise HTTPException(status_code=404, detail="product not found")
    return {"deleted": product_id}


@app.delete("/api/warehouse/receipts/{receipt_id}")
async def remove_receipt(receipt_id: int) -> Dict:
    import warehouse as wh

    if not wh.delete_receipt(receipt_id):
        raise HTTPException(status_code=404, detail="receipt not found")
    return {"deleted": receipt_id, "note": "stock from this receipt was reverted"}


@app.post("/api/warehouse/reset/{table}")
async def reset_table(table: str) -> Dict:
    import warehouse as wh

    try:
        return wh.reset_table(table)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/warehouse/rebuild")
async def rebuild() -> Dict:
    import warehouse as wh

    return wh.rebuild_quantities()


@app.get("/health")
async def health() -> Dict:
    """
    Standard health endpoint.

    `/health/catalog` exists on the recommendation service, so a load balancer
    or run_all.py probing every service on the same path got a 404 from this
    one. One shape across all three services means one probe works everywhere.
    """
    import schema as schema_mod
    import warehouse as wh

    # The warehouse layer is warehouse.py; inventory.py is the older flat
    # table module and has no connection() or backend().
    backend = wh.backend()
    try:
        with wh.connection() as conn:
            counts = schema_mod.table_counts(conn, backend)
        warehouse_ok = True
    except Exception as exc:
        warehouse_ok = False
        counts = {"error": f"{type(exc).__name__}: {exc}"}

    return {
        "status": "ok" if warehouse_ok else "degraded",
        "service": "ocr",
        "warehouse": {
            "backend": backend,
            "available": warehouse_ok,
            "tables": counts,
        },
        "endpoints": ["/api/process", "/api/languages", "/api/inventory",
                      "/api/warehouse/products", "/api/warehouse/receipts",
                      "/api/warehouse/stats"],
    }


@app.get("/health/catalog")
async def health_catalog() -> Dict:
    """Same shape as the recommendation service, for uniform probing."""
    body = await health()
    body["catalog_loaded"] = body["warehouse"]["available"]
    body["product_count"] = body["warehouse"]["tables"].get("products", 0)
    body["backend"] = body["warehouse"]["backend"]
    return body
