"""
Warehouse tests: schema, upsert, ledger, deletion, rebuild.

Every test runs against an isolated SQLite file, so the suite needs neither
EasyOCR nor a PostgreSQL server. The same code path is exercised on Postgres
in production; only the DDL and the placeholder differ.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import schema as schema_mod  # noqa: E402
import warehouse as wh  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(wh, "SQLITE_PATH", tmp_path / "wh.db")
    yield


def items(*rows):
    return [{"name": n, "price": p, "quantity": q} for n, p, q in rows]


# --------------------------------------------------------------------------
# schema
# --------------------------------------------------------------------------

def test_all_tables_created():
    with wh.connection() as conn:
        counts = schema_mod.table_counts(conn, "sqlite")
    for table in ("suppliers", "categories", "products", "receipts",
                  "receipt_items", "stock_movements"):
        assert counts[table] == 0, f"{table} missing or pre-populated"


def test_schema_is_idempotent():
    for _ in range(3):
        with wh.connection():
            pass


# --------------------------------------------------------------------------
# recording
# --------------------------------------------------------------------------

def test_first_scan_inserts():
    r = wh.record_receipt(items(("Blazer", 59.99, 1)), source_file="a.jpg", store="ZARA")
    assert r["receipt_id"]
    assert r["items"][0]["action"] == "added"
    assert r["total"] == 59.99


def test_second_scan_accumulates():
    wh.record_receipt(items(("Shirt", 45.0, 2)))
    r = wh.record_receipt(items(("Shirt", 45.0, 3)))
    assert r["items"][0]["action"] == "updated"
    assert wh.list_products()[0]["quantity"] == 5


def test_line_total_and_receipt_total():
    r = wh.record_receipt(items(("A", 10.0, 3), ("B", 5.5, 2)))
    assert r["items"][0]["line_total"] == 30.0
    assert r["items"][1]["line_total"] == 11.0
    assert r["total"] == 41.0


def test_supplier_is_recorded_and_reused():
    wh.record_receipt(items(("X", 1.0, 1)), store="ZARA")
    wh.record_receipt(items(("Y", 2.0, 1)), store="ZARA")
    with wh.connection() as conn:
        counts = schema_mod.table_counts(conn, "sqlite")
    assert counts["suppliers"] == 1, "the same supplier must not be duplicated"


def test_language_is_stored_on_the_receipt():
    wh.record_receipt(items(("X", 1.0, 1)), language="ar")
    assert wh.list_receipts()[0]["language"] == "ar"


# --------------------------------------------------------------------------
# the ledger
# --------------------------------------------------------------------------

def test_every_scan_writes_a_movement():
    wh.record_receipt(items(("A", 1.0, 1), ("B", 2.0, 2)))
    with wh.connection() as conn:
        counts = schema_mod.table_counts(conn, "sqlite")
    assert counts["stock_movements"] == 2


def test_adjust_records_reason():
    wh.record_receipt(items(("A", 1.0, 5)))
    pid = wh.list_products()[0]["id"]
    r = wh.adjust_stock(pid, -2, "sale")
    assert r["previous_quantity"] == 5 and r["quantity"] == 3
    movements = wh.get_product_detail(pid)["movements"]
    assert any(m["reason"] == "sale" and m["delta"] == -2 for m in movements)


def test_adjust_rejects_unknown_reason():
    wh.record_receipt(items(("A", 1.0, 1)))
    pid = wh.list_products()[0]["id"]
    with pytest.raises(ValueError):
        wh.adjust_stock(pid, 1, "because_i_said_so")


def test_quantity_never_goes_negative():
    wh.record_receipt(items(("A", 1.0, 1)))
    pid = wh.list_products()[0]["id"]
    r = wh.adjust_stock(pid, -99, "sale")
    assert r["quantity"] == 0


def test_rebuild_recomputes_from_the_ledger():
    """The cache can always be thrown away; the ledger is the truth."""
    wh.record_receipt(items(("A", 1.0, 4)))
    pid = wh.list_products()[0]["id"]
    wh.adjust_stock(pid, -1, "sale")

    with wh.connection() as conn:
        with wh.cursor(conn) as cur:
            cur.execute("UPDATE products SET quantity = 999")
        conn.commit()

    wh.rebuild_quantities()
    assert wh.list_products()[0]["quantity"] == 3


# --------------------------------------------------------------------------
# deletion
# --------------------------------------------------------------------------

def test_delete_product_removes_its_movements():
    wh.record_receipt(items(("A", 1.0, 1)))
    pid = wh.list_products()[0]["id"]
    assert wh.delete_product(pid)
    assert wh.list_products() == []
    with wh.connection() as conn:
        counts = schema_mod.table_counts(conn, "sqlite")
    assert counts["stock_movements"] == 0


def test_delete_missing_product_returns_false():
    assert wh.delete_product(9999) is False


def test_delete_receipt_reverts_its_stock():
    """Deleting a receipt must not leave stock with no source."""
    r1 = wh.record_receipt(items(("A", 1.0, 5)))
    wh.record_receipt(items(("A", 1.0, 2)))
    assert wh.list_products()[0]["quantity"] == 7

    wh.delete_receipt(r1["receipt_id"])
    assert wh.list_products()[0]["quantity"] == 2


def test_delete_receipt_removes_its_items():
    r = wh.record_receipt(items(("A", 1.0, 1), ("B", 2.0, 1)))
    wh.delete_receipt(r["receipt_id"])
    with wh.connection() as conn:
        counts = schema_mod.table_counts(conn, "sqlite")
    assert counts["receipt_items"] == 0
    assert counts["receipts"] == 0


# --------------------------------------------------------------------------
# safety
# --------------------------------------------------------------------------

def test_reset_rejects_a_forged_table_name():
    """A DELETE endpoint must never be pointable at an arbitrary table."""
    for name in ("sqlite_master", "products; DROP TABLE products", "suppliers"):
        with pytest.raises(ValueError):
            wh.reset_table(name)


def test_reset_allows_the_whitelisted_tables():
    wh.record_receipt(items(("A", 1.0, 1)))
    result = wh.reset_table("products")
    assert result["table"] == "products"
    assert wh.list_products() == []


def test_search_is_parameterised():
    """A quote in the search box must not break or hijack the query."""
    wh.record_receipt(items(("Normal Item", 1.0, 1)))
    assert wh.list_products(search="Normal")          # works
    assert wh.list_products(search="' OR '1'='1") == []  # no injection


def test_stats_reflects_state():
    # A: 3 x 1.00 = 3.00.  B: qty 0 -> line total 0, and the product is
    # therefore out of stock. Total scanned value is 3.00, not 5.00.
    wh.record_receipt(items(("A", 1.0, 3), ("B", 2.0, 0)), store="ZARA")
    s = wh.stats()
    assert s["total_products"] == 2
    assert s["total_units"] == 3
    assert s["out_of_stock"] == 1
    assert s["receipts_value"] == 3.0
    assert s["tables"]["receipts"] == 1


def test_detail_404s_cleanly():
    assert wh.get_product_detail(4242) is None