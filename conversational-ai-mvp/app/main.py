from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.chat import router as chat_router
from app.api.catalog import router as catalog_router

app = FastAPI(
    title="Conversational AI Assistant MVP",
    description="A clean, lightweight Conversational AI Assistant powered by Google Gemini with conversation memory and mock business data.",
    version="1.0.0"
)

# CORS configuration for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static directory setup
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    # Product images are ~290KB each and immutable (they are copied once by
    # scripts/sync_images.py), so a long cache avoids re-downloading them on
    # every conversation turn.
    class CachedStatic(StaticFiles):
        def file_response(self, *args, **kwargs):
            resp = super().file_response(*args, **kwargs)
            resp.headers["Cache-Control"] = "public, max-age=604800"
            return resp

    app.mount("/static", CachedStatic(directory=str(STATIC_DIR)), name="static")

# Include API Routers
app.include_router(chat_router)
app.include_router(catalog_router)


@app.get("/", include_in_schema=False)
async def serve_index():
    """
    Serves the chat user interface.
    """
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Chat UI static files not found."}


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check.

    Returns 200 even when the catalog failed to load, with status="degraded".
    A health endpoint that raises tells an operator nothing about WHICH
    dependency broke, so the load state is reported as data instead.

    The `dependencies` block reports the other services (stock, forecasting,
    recommendations) the way a load balancer needs: the chatbot can be healthy
    while one of them is down, and that is not a reason to restart this pod.
    """
    from app.services.catalog_service import get_catalog_service

    catalog = get_catalog_service()
    try:
        from app.services.backends import probe_all
        dependencies = probe_all()
    except Exception as exc:
        dependencies = {"error": str(exc)[:120]}

    return {
        "status": "ok" if catalog.available else "degraded",
        "service": "chatbot",
        "catalog_loaded": catalog.available,
        "product_count": catalog.size,
        "catalog_error": catalog.load_error,
        "dependencies": dependencies,
    }


@app.get("/health/catalog", tags=["Health"])
async def health_catalog():
    """Same shape as the other services, so one probe works everywhere."""
    return await health_check()
