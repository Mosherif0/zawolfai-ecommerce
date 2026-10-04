"""
Recommendation system tests.

Run:  pytest test_recommendations.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.catalog_service import BM25Index, get_catalog_service  # noqa: E402


@pytest.fixture(scope="module")
def catalog():
    return get_catalog_service()


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

def test_catalog_loads():
    """Regression: BASE resolved to core/ so the CSV silently failed to load."""
    service = get_catalog_service()
    assert service.load_error is None, service.load_error
    assert service.available


def test_catalog_paths_are_absolute():
    """Relative paths only worked when uvicorn ran from this exact folder."""
    service = get_catalog_service()
    assert service.catalog_csv.is_absolute()
    assert service.images_dir.is_absolute()
    assert service.catalog_csv.is_file()


def test_only_products_with_images():
    """A card without a photo is worse than no card."""
    service = get_catalog_service()
    for pid in service.df["product_id"]:
        assert service.image_url(int(pid)), f"{pid} has no image"


def test_loading_is_cached():
    """Building the index twice would double startup cost for nothing."""
    assert get_catalog_service() is get_catalog_service()


# --------------------------------------------------------------------------
# search
# --------------------------------------------------------------------------

@pytest.mark.parametrize("query,expected_category", [
    ("jacket", "Jacket"),
    ("dress", "Dress"),
    ("trousers", "Trousers"),
])
def test_search_finds_the_right_category(query, expected_category, catalog):
    results = catalog.search(query, top_k=5)
    assert results, f"{query!r} returned nothing"
    categories = {catalog.get(i)["category"] for i in results}
    assert expected_category in categories


def test_search_handles_empty_query(catalog):
    assert catalog.search("", top_k=5) == []
    assert catalog.search("   ", top_k=5) == []


def test_search_never_returns_the_same_product_twice(catalog):
    ids = catalog.search("jacket", top_k=10)
    assert len(ids) == len(set(ids))


def test_search_ignores_unknown_terms(catalog):
    """No match is better than an arbitrary match."""
    assert catalog.search("zzzzqqqqxxxx", top_k=5) == []


# --------------------------------------------------------------------------
# BM25
# --------------------------------------------------------------------------

def test_bm25_ranks_the_matching_document_first():
    index = BM25Index([["black", "jacket"], ["red", "dress"], ["blue", "jacket"]])
    assert index.top(["jacket"], 2) == [0, 2]


def test_bm25_ignores_unknown_terms():
    index = BM25Index([["black", "jacket"], ["red", "dress"]])
    assert index.top(["nonexistent"], 2) == []


def test_bm25_handles_an_empty_corpus():
    assert BM25Index([]).top(["anything"], 3) == []


def test_bm25_idf_never_negative():
    """A term in every document must not subtract from the score."""
    import math
    index = BM25Index([["common", "a"], ["common", "b"]])
    assert index.idf("common") >= 0.0
    assert math.isfinite(index.idf("common"))


# --------------------------------------------------------------------------
# related items
# --------------------------------------------------------------------------

def test_related_excludes_the_origin(catalog):
    pid = catalog.search("jacket", top_k=1)[0]
    related = catalog.related(pid, top_k=4)
    assert pid not in related["complete_the_look"]
    assert pid not in related["similar"]


def test_similar_items_share_the_category(catalog):
    pid = catalog.search("jacket", top_k=1)[0]
    origin_category = catalog.get(pid)["category"]
    for other in catalog.related(pid, top_k=4)["similar"]:
        assert catalog.get(other)["category"] == origin_category


def test_complete_the_look_is_a_different_category(catalog):
    """A jacket paired with more jackets is not an outfit."""
    pid = catalog.search("jacket", top_k=1)[0]
    origin_category = catalog.get(pid)["category"]
    for other in catalog.related(pid, top_k=4)["complete_the_look"]:
        assert catalog.get(other)["category"] != origin_category


def test_related_on_unknown_product(catalog):
    assert catalog.related(999999999) == {"complete_the_look": [], "similar": []}


# --------------------------------------------------------------------------
# images + facets
# --------------------------------------------------------------------------

def test_image_bytes_are_readable(catalog):
    pid = catalog.search("jacket", top_k=1)[0]
    filename = catalog._image_files[pid]
    data = catalog.image_bytes(filename)
    assert data and data[:2] == b"\xff\xd8", "not a JPEG"


def test_missing_image_returns_none(catalog):
    assert catalog.image_bytes("does-not-exist.jpg") is None


def test_facets_cover_every_product(catalog):
    facets = catalog.facets()
    assert sum(facets["categories"].values()) == catalog.size


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    import app_api
    with TestClient(app_api.app) as test_client:
        yield test_client


def test_health_reports_state(client):
    body = client.get("/health/catalog").json()
    assert body["catalog_loaded"] is True
    assert body["product_count"] > 0
    assert body["load_error"] is None


def test_search_endpoint(client):
    body = client.get("/api/v1/search?q=jacket&limit=3").json()
    assert body["count"] > 0
    assert body["results"][0]["image_url"]


def test_product_detail_endpoint(client):
    pid = client.get("/api/v1/search?q=jacket&limit=1").json()["results"][0]["product_id"]
    body = client.get(f"/api/v1/products/{pid}").json()
    assert body["product"]["product_id"] == pid
    assert "complete_the_look" in body


def test_unknown_product_is_404(client):
    assert client.get("/api/v1/products/999999999").status_code == 404


def test_images_are_served(client):
    url = client.get("/api/v1/search?q=jacket&limit=1").json()["results"][0]["image_url"]
    response = client.get(url)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert len(response.content) > 1000


def test_facets_endpoint(client):
    body = client.get("/api/v1/facets").json()
    assert body["count"] > 0
    assert "categories" in body