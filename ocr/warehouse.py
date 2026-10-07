"""
Warehouse API for the OCR inventory system.

Database source of truth:
    products
    receipts
    receipt_items

The implementation intentionally does not depend on:
    categories
    suppliers
    stock_movements
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


# --------------------------------------------------------------------------
# configuration
# --------------------------------------------------------------------------

_BASE_DIR = Path(__file__).resolve().parent
_DEFAULT_SQLITE = _BASE_DIR / "output" / "inventory.db"
SQLITE_PATH = Path(os.getenv("SQLITE_PATH", str(_DEFAULT_SQLITE)))
if not SQLITE_PATH.is_absolute():
    SQLITE_PATH = (_BASE_DIR / SQLITE_PATH).resolve()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


RESETTABLE_TABLES = (
    "receipt_items",
    "receipts",
    "products",
)


# --------------------------------------------------------------------------
# database helpers
# --------------------------------------------------------------------------

def using_postgres() -> bool:
    return bool(DB_HOST)


def backend() -> str:
    return "postgres" if using_postgres() else "sqlite"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db() -> None:
    """Ensure the warehouse database exists."""
    with connection():
        return


@contextmanager
def connection():
    """Open a database connection and close it afterwards."""

    if using_postgres():
        conn = schema_mod.postgres_connect(
            DB_HOST,
            DB_PORT,
            DB_NAME,
            DB_USER,
            DB_PASSWORD,
        )
    else:
        conn = schema_mod.sqlite_connect(SQLITE_PATH)

    try:
        yield conn
    finally:
        conn.close()


def ph() -> str:
    """Return the correct SQL parameter placeholder."""
    return "%s" if using_postgres() else "?"


@contextmanager
def cursor(conn):
    """Backend-independent cursor context manager."""

    cur = conn.cursor()

    try:
        yield cur
    finally:
        cur.close()


def _rows(cur) -> List[Dict[str, Any]]:
    """Convert cursor rows into dictionaries."""

    if not cur.description:
        return []

    columns = [description[0] for description in cur.description]

    return [
        dict(zip(columns, row))
        for row in cur.fetchall()
    ]


def _inserted_id(cur, table: str) -> int:
    """
    Return the ID of the row inserted by the immediately preceding INSERT.

    PostgreSQL uses RETURNING id directly.
    SQLite uses lastrowid.
    """

    if using_postgres():
        row = cur.fetchone()

        if not row:
            raise RuntimeError(
                f"Could not retrieve inserted id from {table}"
            )

        return int(row[0])

    return int(cur.lastrowid)


# --------------------------------------------------------------------------
# lookup helpers
# --------------------------------------------------------------------------

def find_product(
    conn,
    name: str,
) -> Optional[Dict[str, Any]]:
    """Find a product by its exact name."""

    p = ph()

    with cursor(conn) as cur:
        cur.execute(
            f"""
            SELECT
                id,
                name,
                price,
                quantity,
                created_at,
                updated_at
            FROM products
            WHERE name = {p}
            """,
            (name,),
        )

        row = cur.fetchone()

        if not row:
            return None

        return dict(
            zip(
                [description[0] for description in cur.description],
                row,
            )
        )


# --------------------------------------------------------------------------
# receipts
# --------------------------------------------------------------------------

def record_receipt(
    items: Iterable[dict],
    source_file: Optional[str] = None,
    store: Optional[str] = None,
    language: str = "en",
    status: str = "accepted",
) -> Dict[str, Any]:
    """
    Store one OCR receipt.

    For every scanned item:

    - If the product already exists, increase its quantity.
    - If it does not exist, create it.
    - Store the receipt.
    - Store the receipt item.

    The database schema does not contain source_file/store/language/status,
    so those arguments are kept only for API compatibility.
    """

    items = list(items)

    if not items:
        return {
            "receipt_id": None,
            "items": [],
            "total": 0.0,
        }

    p = ph()

    result: Dict[str, Any] = {
        "receipt_id": None,
        "items": [],
        "total": 0.0,
    }

    with connection() as conn:
        now = _now()

        try:
            with cursor(conn) as cur:

                # ----------------------------------------------------------
                # create receipt
                # ----------------------------------------------------------

                if using_postgres():
                    cur.execute(
                        """
                        INSERT INTO receipts (
                            receipt_date,
                            created_at
                        )
                        VALUES (%s, %s)
                        RETURNING id
                        """,
                        (now, now),
                    )
                else:
                    cur.execute(
                        f"""
                        INSERT INTO receipts (
                            receipt_date,
                            created_at
                        )
                        VALUES ({p}, {p})
                        """,
                        (now, now),
                    )

                receipt_id = _inserted_id(cur, "receipts")

                result["receipt_id"] = receipt_id

                # ----------------------------------------------------------
                # process receipt items
                # ----------------------------------------------------------

                for item in items:

                    name = str(item.get("name", "")).strip()

                    if not name:
                        continue

                    qty = int(item.get("quantity", 1))

                    if qty <= 0:
                        qty = 1

                    price = float(item.get("price", 0.0))

                    line_total = round(
                        qty * price,
                        2,
                    )

                    result["total"] = round(
                        result["total"] + line_total,
                        2,
                    )

                    # ------------------------------------------------------
                    # find existing product
                    # ------------------------------------------------------

                    existing = find_product(
                        conn,
                        name,
                    )

                    if existing:

                        product_id = int(existing["id"])

                        previous_quantity = int(
                            existing["quantity"]
                        )

                        new_quantity = (
                            previous_quantity + qty
                        )

                        cur.execute(
                            f"""
                            UPDATE products
                            SET
                                quantity = {p},
                                price = {p},
                                updated_at = {p}
                            WHERE id = {p}
                            """,
                            (
                                new_quantity,
                                price,
                                now,
                                product_id,
                            ),
                        )

                        action = "updated"

                    else:

                        # --------------------------------------------------
                        # create new product
                        # --------------------------------------------------

                        if using_postgres():

                            cur.execute(
                                """
                                INSERT INTO products (
                                    name,
                                    price,
                                    quantity,
                                    created_at,
                                    updated_at
                                )
                                VALUES (%s, %s, %s, %s, %s)
                                RETURNING id
                                """,
                                (
                                    name,
                                    price,
                                    qty,
                                    now,
                                    now,
                                ),
                            )

                        else:

                            cur.execute(
                                f"""
                                INSERT INTO products (
                                    name,
                                    price,
                                    quantity,
                                    created_at,
                                    updated_at
                                )
                                VALUES ({p}, {p}, {p}, {p}, {p})
                                """,
                                (
                                    name,
                                    price,
                                    qty,
                                    now,
                                    now,
                                ),
                            )

                        product_id = _inserted_id(
                            cur,
                            "products",
                        )

                        action = "added"

                    # ------------------------------------------------------
                    # store receipt item
                    # ------------------------------------------------------

                    cur.execute(
                        f"""
                        INSERT INTO receipt_items (
                            receipt_id,
                            product_id,
                            quantity,
                            price
                        )
                        VALUES ({p}, {p}, {p}, {p})
                        """,
                        (
                            receipt_id,
                            product_id,
                            qty,
                            price,
                        ),
                    )

                    result["items"].append(
                        {
                            "product_id": product_id,
                            "name": name,
                            "action": action,
                            "quantity": qty,
                            "price": price,
                            "line_total": line_total,
                        }
                    )

            conn.commit()

        except Exception:
            conn.rollback()
            raise

    return result


# --------------------------------------------------------------------------
# product queries
# --------------------------------------------------------------------------

def list_products(
    search: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Return products.

    `category` is kept for API compatibility, but the current database
    schema does not contain categories.
    """

    p = ph()

    clauses: List[str] = []
    params: List[Any] = []

    if search:
        if using_postgres():
            clauses.append(
                f"p.name ILIKE {p}"
            )
        else:
            clauses.append(
                f"p.name LIKE {p}"
            )

        params.append(f"%{search}%")

    # The current schema has no category column.
    # Keep the argument for backwards compatibility.
    _ = category

    where = ""

    if clauses:
        where = " WHERE " + " AND ".join(clauses)

    query = f"""
        SELECT
            p.id,
            p.name,
            p.price,
            p.quantity,
            p.created_at,
            p.updated_at
        FROM products p
        {where}
        ORDER BY p.name
        LIMIT {p}
        OFFSET {p}
    """

    params.extend(
        [
            int(limit),
            int(offset),
        ]
    )

    with connection() as conn:
        with cursor(conn) as cur:
            cur.execute(query, params)
            return _rows(cur)


def get_product_detail(
    product_id: int,
) -> Optional[Dict[str, Any]]:
    """Return one product and its receipt history."""

    p = ph()

    with connection() as conn:

        with cursor(conn) as cur:

            cur.execute(
                f"""
                SELECT
                    id,
                    name,
                    price,
                    quantity,
                    created_at,
                    updated_at
                FROM products
                WHERE id = {p}
                """,
                (product_id,),
            )

            row = cur.fetchone()

            if not row:
                return None

            detail = dict(
                zip(
                    [description[0] for description in cur.description],
                    row,
                )
            )

            # --------------------------------------------------------------
            # receipt history
            # --------------------------------------------------------------

            cur.execute(
                f"""
                SELECT
                    ri.receipt_id,
                    ri.quantity,
                    ri.price,
                    r.receipt_date,
                    r.created_at
                FROM receipt_items ri
                JOIN receipts r
                    ON r.id = ri.receipt_id
                WHERE ri.product_id = {p}
                ORDER BY r.created_at DESC
                """,
                (product_id,),
            )

            detail["receipts"] = _rows(cur)

            return detail


# --------------------------------------------------------------------------
# receipt queries
# --------------------------------------------------------------------------

def list_receipts(
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Return recent receipts and their item counts."""

    p = ph()

    with connection() as conn:

        with cursor(conn) as cur:

            cur.execute(
                f"""
                SELECT
                    r.id,
                    r.receipt_date,
                    r.created_at,

                    COUNT(ri.id) AS item_count,

                    COALESCE(
                        SUM(
                            ri.quantity * ri.price
                        ),
                        0
                    ) AS total

                FROM receipts r

                LEFT JOIN receipt_items ri
                    ON ri.receipt_id = r.id

                GROUP BY
                    r.id,
                    r.receipt_date,
                    r.created_at

                ORDER BY r.created_at DESC

                LIMIT {p}
                """,
                (int(limit),),
            )

            return _rows(cur)


# --------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------

def stats() -> Dict[str, Any]:
    """Return inventory dashboard statistics."""

    with connection() as conn:

        counts = schema_mod.table_counts(
            conn,
            backend(),
        )

        with cursor(conn) as cur:

            # Total units and products
            cur.execute(
                """
                SELECT
                    COALESCE(SUM(quantity), 0),
                    COUNT(*)
                FROM products
                """
            )

            units, products = cur.fetchone()

            # Total value of recorded receipts
            cur.execute(
                """
                SELECT
                    COALESCE(
                        SUM(
                            ri.quantity * ri.price
                        ),
                        0
                    )
                FROM receipt_items ri
                """
            )

            receipt_value = cur.fetchone()[0]

            # Out of stock
            cur.execute(
                """
                SELECT COUNT(*)
                FROM products
                WHERE quantity = 0
                """
            )

            out_of_stock = cur.fetchone()[0]

    return {
        "backend": backend(),
        "tables": counts,
        "total_units": int(units or 0),
        "total_products": int(products or 0),
        "receipts_value": round(
            float(receipt_value or 0),
            2,
        ),
        "out_of_stock": int(out_of_stock or 0),
    }


# --------------------------------------------------------------------------
# stock mutations
# --------------------------------------------------------------------------

def adjust_stock(
    product_id: int,
    delta: int,
    reason: str = "adjustment",
    note: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Manually adjust a product's quantity.

    The current database schema has no stock movement ledger, so only the
    products.quantity value is updated.
    """

    _ = note

    p = ph()

    with connection() as conn:

        try:

            with cursor(conn) as cur:

                cur.execute(
                    f"""
                    SELECT
                        name,
                        quantity
                    FROM products
                    WHERE id = {p}
                    """,
                    (product_id,),
                )

                row = cur.fetchone()

                if not row:
                    return None

                name = row[0]
                previous_quantity = int(row[1])

                new_quantity = max(
                    0,
                    previous_quantity + int(delta),
                )

                cur.execute(
                    f"""
                    UPDATE products
                    SET
                        quantity = {p},
                        updated_at = {p}
                    WHERE id = {p}
                    """,
                    (
                        new_quantity,
                        _now(),
                        product_id,
                    ),
                )

            conn.commit()

        except Exception:
            conn.rollback()
            raise

    return {
        "product_id": product_id,
        "name": name,
        "previous_quantity": previous_quantity,
        "quantity": new_quantity,
        "delta": int(delta),
        "reason": reason,
    }


# --------------------------------------------------------------------------
# delete operations
# --------------------------------------------------------------------------

def delete_product(
    product_id: int,
) -> bool:
    """
    Delete a product and its receipt-item references.

    Receipts themselves are preserved.
    """

    p = ph()

    with connection() as conn:

        try:

            with cursor(conn) as cur:

                # Remove child rows first because receipt_items references
                # products.
                cur.execute(
                    f"""
                    DELETE FROM receipt_items
                    WHERE product_id = {p}
                    """,
                    (product_id,),
                )

                cur.execute(
                    f"""
                    DELETE FROM products
                    WHERE id = {p}
                    """,
                    (product_id,),
                )

                deleted = cur.rowcount

            conn.commit()

        except Exception:
            conn.rollback()
            raise

    return deleted > 0


def delete_receipt(
    receipt_id: int,
) -> bool:
    """
    Delete a receipt.

    Before deleting the receipt, quantities added by that receipt are removed
    from the affected products.
    """

    p = ph()

    with connection() as conn:

        try:

            with cursor(conn) as cur:

                # ----------------------------------------------------------
                # Get all products affected by this receipt
                # ----------------------------------------------------------

                cur.execute(
                    f"""
                    SELECT
                        product_id,
                        quantity
                    FROM receipt_items
                    WHERE receipt_id = {p}
                    """,
                    (receipt_id,),
                )

                items = cur.fetchall()

                # ----------------------------------------------------------
                # Revert product quantities
                # ----------------------------------------------------------

                for product_id, qty in items:

                    cur.execute(
                        f"""
                        UPDATE products
                        SET
                            quantity = GREATEST(
                                0,
                                quantity - {p}
                            ),
                            updated_at = {p}
                        WHERE id = {p}
                        """,
                        (
                            qty,
                            _now(),
                            product_id,
                        ),
                    )

                # ----------------------------------------------------------
                # Delete receipt items
                # ----------------------------------------------------------

                cur.execute(
                    f"""
                    DELETE FROM receipt_items
                    WHERE receipt_id = {p}
                    """,
                    (receipt_id,),
                )

                # ----------------------------------------------------------
                # Delete receipt
                # ----------------------------------------------------------

                cur.execute(
                    f"""
                    DELETE FROM receipts
                    WHERE id = {p}
                    """,
                    (receipt_id,),
                )

                deleted = cur.rowcount

            conn.commit()

        except Exception:
            conn.rollback()
            raise

    return deleted > 0


# --------------------------------------------------------------------------
# reset
# --------------------------------------------------------------------------

def reset_table(
    table: str,
) -> Dict[str, Any]:
    """
    Clear one of the allowed inventory tables.

    Foreign-key children are removed first when necessary.
    """

    if table not in RESETTABLE_TABLES:
        raise ValueError(
            f"cannot reset {table!r}; "
            f"allowed: {RESETTABLE_TABLES}"
        )

    with connection() as conn:

        try:

            with cursor(conn) as cur:

                # ----------------------------------------------------------
                # receipts
                # ----------------------------------------------------------

                if table == "receipts":

                    cur.execute(
                        "DELETE FROM receipt_items"
                    )

                    cur.execute(
                        "DELETE FROM receipts"
                    )

                    removed = cur.rowcount

                # ----------------------------------------------------------
                # products
                # ----------------------------------------------------------

                elif table == "products":

                    # receipt_items references products.
                    cur.execute(
                        "DELETE FROM receipt_items"
                    )

                    cur.execute(
                        "DELETE FROM products"
                    )

                    removed = cur.rowcount

                # ----------------------------------------------------------
                # receipt_items
                # ----------------------------------------------------------

                else:

                    cur.execute(
                        "DELETE FROM receipt_items"
                    )

                    removed = cur.rowcount

            conn.commit()

        except Exception:
            conn.rollback()
            raise

    return {
        "table": table,
        "deleted": max(int(removed), 0),
    }


# --------------------------------------------------------------------------
# rebuild
# --------------------------------------------------------------------------

def rebuild_quantities() -> Dict[str, Any]:
    """
    Recalculate product quantities from receipt_items.

    Since the current schema has no stock_movements table, receipt_items is
    the available historical source for stock added through OCR receipts.

    This rebuild resets every product quantity to the sum of its receipt items.
    """

    with connection() as conn:

        try:

            with cursor(conn) as cur:

                # First set all quantities to zero.
                cur.execute(
                    """
                    UPDATE products
                    SET
                        quantity = 0,
                        updated_at = CURRENT_TIMESTAMP
                    """
                )

                updated = cur.rowcount

                # Then rebuild from receipt_items.
                cur.execute(
                    """
                    UPDATE products
                    SET
                        quantity = COALESCE(
                            (
                                SELECT SUM(ri.quantity)
                                FROM receipt_items ri
                                WHERE ri.product_id = products.id
                            ),
                            0
                        ),
                        updated_at = CURRENT_TIMESTAMP
                    """
                )

            conn.commit()

        except Exception:
            conn.rollback()
            raise

    return {
        "rebuilt": int(updated),
    }