"""
Warehouse API over the normalised schema.

Design rules
------------
* The stock ledger is append-only. `products.quantity` is a cache that can be
  rebuilt from `stock_movements` at any time (`rebuild_quantities`), so a bad
  count is repairable rather than destructive.
* Every write runs in one transaction. A receipt that inserts 3 items but
  fails on the 4th must leave nothing behind.
* Deletion is explicit and audited: `delete_product` removes the product and
  its movements, which is why the UI confirms before calling it.
* SQL is parameterised everywhere, including identifiers that come from the
  schema module's own constant list (never from user input).
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from dotenv import load_dotenv

import schema as schema_mod

load_dotenv()

SQLITE_PATH = Path(os.getenv("SQLITE_PATH", "output/inventory.db"))

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

#: Tables a caller may clear from the UI. Whitelisted so a DELETE endpoint can
#: never be pointed at `products` with a forged name.
RESETTABLE_TABLES = ("stock_movements", "receipt_items", "receipts", "products")


def using_postgres() -> bool:
    return bool(DB_HOST)


def backend() -> str:
    return "postgres" if using_postgres() else "sqlite"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db() -> None:
    """
    Create the warehouse schema.

    Opening a connection already applies the schema, so this exists for
    callers that want to ensure the tables exist before doing anything else
    (the CLI, a health probe, a fresh deployment).
    """
    with connection():
        return


@contextmanager
def connection():
    """Open a connection with the schema applied, and always close it."""
    if using_postgres():
        conn = schema_mod.postgres_connect(DB_HOST, DB_PORT, DB_NAME,
                                            DB_USER, DB_PASSWORD)
    else:
        conn = schema_mod.sqlite_connect(SQLITE_PATH)
    try:
        yield conn
    finally:
        conn.close()


def ph() -> str:
    """Parameter placeholder for the active backend."""
    return "%s" if using_postgres() else "?"



@contextmanager
def cursor(conn):
    """
    Yield a cursor and close it.

    sqlite3.Cursor does NOT implement the context-manager protocol (psycopg's
    does), so `with conn.cursor()` raises TypeError on SQLite. One helper keeps
    a single call style working on both backends.
    """
    cur = conn.cursor()
    try:
        yield cur
    finally:
        cur.close()


def _rows(cur) -> List[Dict[str, Any]]:
    columns = [d[0] for d in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]


# --------------------------------------------------------------------------
# lookup helpers
# --------------------------------------------------------------------------

def get_or_create_category(conn, name: Optional[str]) -> Optional[int]:
    if not name:
        return None
    with cursor(conn) as cur:
        cur.execute(f"SELECT id FROM categories WHERE name = {ph()}", (name,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(f"INSERT INTO categories (name) VALUES ({ph()})", (name,))
        if using_postgres():
            cur.execute(f"SELECT id FROM categories WHERE name = {ph()}", (name,))
            return cur.fetchone()[0]
        return cur.lastrowid


def get_or_create_supplier(conn, name: Optional[str]) -> Optional[int]:
    if not name:
        return None
    with cursor(conn) as cur:
        cur.execute(f"SELECT id FROM suppliers WHERE name = {ph()}", (name,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(f"INSERT INTO suppliers (name, created_at) VALUES ({ph()}, {ph()})",
                    (name, _now()))
        if using_postgres():
            cur.execute(f"SELECT id FROM suppliers WHERE name = {ph()}", (name,))
            return cur.fetchone()[0]
        return cur.lastrowid


def find_product(conn, name: str) -> Optional[Dict]:
    with cursor(conn) as cur:
        cur.execute(f"SELECT * FROM products WHERE name = {ph()}", (name,))
        row = cur.fetchone()
        if not row:
            return None
        return dict(zip([d[0] for d in cur.description], row))


# --------------------------------------------------------------------------
# receipts
# --------------------------------------------------------------------------

def record_receipt(items: Iterable[dict], source_file: Optional[str] = None,
                   store: Optional[str] = None, language: str = "en",
                   status: str = "accepted") -> Dict:
    """
    Store one scanned receipt with full provenance.

    Returns a summary: the receipt id, per-item outcomes (added / updated) and
    the movement ids that were written, so a caller can show exactly what
    changed instead of only "OK".
    """
    items = list(items)
    p = ph()
    result: Dict[str, Any] = {"receipt_id": None, "items": [], "total": 0.0}

    with connection() as conn:
        now = _now()
        supplier_id = get_or_create_supplier(conn, store)

        with cursor(conn) as cur:
            cur.execute(
                f"INSERT INTO receipts (source_file, store, language, status, created_at) "
                f"VALUES ({p}, {p}, {p}, {p}, {p})",
                (source_file, store, language, status, now),
            )
            if using_postgres():
                cur.execute("SELECT lastval()")
                receipt_id = cur.fetchone()[0]
            else:
                receipt_id = cur.lastrowid
            result["receipt_id"] = receipt_id

            for item in items:
                name = item["name"]
                qty = int(item.get("quantity", 1))
                price = float(item.get("price", 0.0))
                line_total = round(qty * price, 2)
                result["total"] = round(result["total"] + line_total, 2)

                existing = find_product(conn, name)

                if existing:
                    product_id = existing["id"]
                    new_qty = int(existing["quantity"]) + qty
                    cur.execute(
                        f"UPDATE products SET quantity = {p}, price = {p}, "
                        f"supplier_id = COALESCE({p}, supplier_id), updated_at = {p} "
                        f"WHERE id = {p}",
                        (new_qty, price, supplier_id, now, product_id),
                    )
                    action = "updated"
                else:
                    cur.execute(
                        f"INSERT INTO products (name, price, quantity, supplier_id, "
                        f"created_at, updated_at) VALUES ({p}, {p}, {p}, {p}, {p}, {p})",
                        (name, price, qty, supplier_id, now, now),
                    )
                    if using_postgres():
                        cur.execute("SELECT lastval()")
                        product_id = cur.fetchone()[0]
                    else:
                        product_id = cur.lastrowid
                    action = "added"

                cur.execute(
                    f"INSERT INTO receipt_items (receipt_id, product_id, name_raw, "
                    f"quantity, unit_price, line_total, created_at) "
                    f"VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p})",
                    (receipt_id, product_id, name, qty, price, line_total, now),
                )

                cur.execute(
                    f"INSERT INTO stock_movements (product_id, delta, reason, "
                    f"ref_type, ref_id, created_at) VALUES ({p}, {p}, {p}, {p}, {p}, {p})",
                    (product_id, qty, "receipt_scan", "receipt", receipt_id, now),
                )
                if using_postgres():
                    cur.execute("SELECT lastval()")
                    movement_id = cur.fetchone()[0]
                else:
                    movement_id = cur.lastrowid

                result["items"].append({
                    "product_id": product_id,
                    "name": name,
                    "action": action,
                    "quantity": qty,
                    "price": price,
                    "line_total": line_total,
                    "movement_id": movement_id,
                })

            cur.execute(f"UPDATE receipts SET total = {p} WHERE id = {p}",
                        (result["total"], receipt_id))

        conn.commit()

    return result


# --------------------------------------------------------------------------
# queries
# --------------------------------------------------------------------------

def list_products(search: Optional[str] = None, category: Optional[str] = None,
                  limit: int = 200, offset: int = 0) -> List[Dict]:
    p = ph()
    clauses: List[str] = []
    params: List[Any] = []

    if search:
        clauses.append(f"p.name ILIKE {p}" if using_postgres() else f"p.name LIKE {p}")
        params.append(f"%{search}%")
    if category:
        clauses.append(f"c.name = {p}")
        params.append(category)

    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    query = (
        "SELECT p.id, p.name, p.price, p.quantity, p.barcode, p.updated_at, "
        "c.name AS category, s.name AS supplier "
        "FROM products p "
        "LEFT JOIN categories c ON c.id = p.category_id "
        "LEFT JOIN suppliers s ON s.id = p.supplier_id"
        f"{where} ORDER BY p.name LIMIT {p} OFFSET {p}"
    )
    params += [limit, offset]

    with connection() as conn:
        with cursor(conn) as cur:
            cur.execute(query, params)
            return _rows(cur)


def get_product_detail(product_id: int) -> Optional[Dict]:
    p = ph()
    with connection() as conn:
        with cursor(conn) as cur:
            cur.execute(
                "SELECT p.id, p.name, p.price, p.quantity, p.barcode, "
                "p.created_at, p.updated_at, c.name AS category, s.name AS supplier "
                "FROM products p "
                "LEFT JOIN categories c ON c.id = p.category_id "
                "LEFT JOIN suppliers s ON s.id = p.supplier_id "
                f"WHERE p.id = {p}",
                (product_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            detail = dict(zip([d[0] for d in cur.description], row))

            cur.execute(
                "SELECT delta, reason, ref_type, created_at "
                f"FROM stock_movements WHERE product_id = {p} ORDER BY created_at DESC",
                (product_id,),
            )
            detail["movements"] = _rows(cur)
            return detail


def list_receipts(limit: int = 50) -> List[Dict]:
    p = ph()
    with connection() as conn:
        with cursor(conn) as cur:
            cur.execute(
                "SELECT r.id, r.source_file, r.store, r.total, r.language, "
                "r.status, r.created_at, COUNT(i.id) AS item_count "
                "FROM receipts r LEFT JOIN receipt_items i ON i.receipt_id = r.id "
                f"GROUP BY r.id ORDER BY r.created_at DESC LIMIT {p}",
                (limit,),
            )
            return _rows(cur)


def stats() -> Dict:
    """Dashboard counters."""
    with connection() as conn:
        counts = schema_mod.table_counts(conn, backend())
        with cursor(conn) as cur:
            cur.execute("SELECT COALESCE(SUM(quantity), 0), COUNT(*) FROM products")
            units, products = cur.fetchone()
            cur.execute("SELECT COALESCE(SUM(total), 0) FROM receipts")
            receipt_value = cur.fetchone()[0]
            cur.execute(
                f"SELECT COUNT(*) FROM products WHERE quantity = 0")
            out_of_stock = cur.fetchone()[0]

    return {
        "backend": backend(),
        "tables": counts,
        "total_units": int(units or 0),
        "total_products": int(products or 0),
        "receipts_value": round(float(receipt_value or 0), 2),
        "out_of_stock": int(out_of_stock),
    }


# --------------------------------------------------------------------------
# mutations
# --------------------------------------------------------------------------

def adjust_stock(product_id: int, delta: int, reason: str = "adjustment",
                 note: Optional[str] = None) -> Optional[Dict]:
    """
    Change stock and record why.

    The reason is constrained to MOVEMENT_REASONS: an unbounded free-text
    reason makes the ledger unqueryable ("show me every manual correction").
    """
    if reason not in schema_mod.MOVEMENT_REASONS:
        raise ValueError(f"reason must be one of {schema_mod.MOVEMENT_REASONS}")

    p = ph()
    with connection() as conn:
        now = _now()
        with cursor(conn) as cur:
            cur.execute(f"SELECT name, quantity FROM products WHERE id = {p}",
                        (product_id,))
            row = cur.fetchone()
            if not row:
                return None
            new_qty = max(0, int(row[1]) + int(delta))

            cur.execute(
                f"UPDATE products SET quantity = {p}, updated_at = {p} WHERE id = {p}",
                (new_qty, now, product_id))
            cur.execute(
                f"INSERT INTO stock_movements (product_id, delta, reason, "
                f"ref_type, created_at) VALUES ({p}, {p}, {p}, {p}, {p})",
                (product_id, int(delta), reason, "manual", now))
            conn.commit()

        return {"product_id": product_id, "name": row[0],
                "previous_quantity": int(row[1]), "quantity": new_qty,
                "delta": int(delta), "reason": reason}


def delete_product(product_id: int) -> bool:
    """Remove a product and its movement history."""
    p = ph()
    with connection() as conn:
        with cursor(conn) as cur:
            cur.execute(f"DELETE FROM stock_movements WHERE product_id = {p}", (product_id,))
            cur.execute(f"DELETE FROM receipt_items WHERE product_id = {p}", (product_id,))
            cur.execute(f"DELETE FROM products WHERE id = {p}", (product_id,))
            deleted = cur.rowcount
            conn.commit()
    return deleted > 0


def delete_receipt(receipt_id: int) -> bool:
    """
    Remove a receipt.

    Its items and the stock they added are reverted first, otherwise deleting
    a receipt would leave stock that no longer has a source.
    """
    p = ph()
    with connection() as conn:
        with cursor(conn) as cur:
            cur.execute(
                f"SELECT product_id, quantity FROM receipt_items WHERE receipt_id = {p}",
                (receipt_id,))
            for product_id, qty in cur.fetchall():
                cur.execute(
                    f"UPDATE products SET quantity = MAX(0, quantity - {p}) WHERE id = {p}",
                    (qty, product_id))
                cur.execute(
                    f"DELETE FROM stock_movements WHERE ref_type = 'receipt' AND ref_id = {p}",
                    (receipt_id,))

            cur.execute(f"DELETE FROM receipt_items WHERE receipt_id = {p}", (receipt_id,))
            cur.execute(f"DELETE FROM receipts WHERE id = {p}", (receipt_id,))
            deleted = cur.rowcount
            conn.commit()
    return deleted > 0


def reset_table(table: str) -> Dict:
    """Clear a table. Only whitelisted tables are accepted."""
    if table not in RESETTABLE_TABLES:
        raise ValueError(f"cannot reset {table!r}; allowed: {RESETTABLE_TABLES}")
    p = ph()
    with connection() as conn:
        with cursor(conn) as cur:
            # children first so foreign keys stay satisfied
            if table == "receipts":
                cur.execute("DELETE FROM stock_movements")
                cur.execute("DELETE FROM receipt_items")
            elif table == "products":
                cur.execute("DELETE FROM stock_movements")
                cur.execute("DELETE FROM receipt_items")
            cur.execute(f"DELETE FROM {table}")
            removed = cur.rowcount
            conn.commit()
    return {"table": table, "deleted": max(removed, 0)}


def rebuild_quantities() -> Dict:
    """
    Recompute every `products.quantity` from the ledger.

    This is what makes the movements table worth having: the cache can always
    be thrown away and rebuilt.
    """
    p = ph()
    with connection() as conn:
        with cursor(conn) as cur:
            cur.execute(
                f"UPDATE products SET quantity = COALESCE(("
                f"  SELECT SUM(m.delta) FROM stock_movements m WHERE m.product_id = products.id"
                f"), 0)"
            )
            updated = cur.rowcount
            conn.commit()
    return {"rebuilt": updated}
