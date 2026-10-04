"""
Inventory storage.

Supports two backends behind one interface:

  * SQLite  - default, zero install, used by tests and local runs.
  * Postgres - used when DB_HOST is present in .env.

Why two: the parsing logic should be testable and demoable without a running
database server, and switching backends must not touch any caller.

`save_products` is an UPSERT: an existing product name has its quantity
incremented, a new one is inserted.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from typing import Iterable, List, Optional

from dotenv import load_dotenv

load_dotenv()

SQLITE_PATH = Path(os.getenv("SQLITE_PATH", "output/inventory.db"))

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    price      REAL    NOT NULL,
    quantity   INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS receipt_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT,
    product_id  INTEGER,
    name        TEXT,
    quantity    INTEGER,
    price       REAL,
    created_at  TEXT
);
"""

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    price      DOUBLE PRECISION NOT NULL,
    quantity   INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS receipt_items (
    id          SERIAL PRIMARY KEY,
    source_file TEXT,
    product_id  INTEGER,
    name        TEXT,
    quantity    INTEGER,
    price       DOUBLE PRECISION,
    created_at  TIMESTAMPTZ
);
"""


@contextmanager
def _cursor(conn):
    """
    Yield a cursor and close it afterwards.

    sqlite3.Cursor does NOT implement the context-manager protocol (psycopg's
    does), so `with conn.cursor()` raises TypeError on SQLite. This helper
    keeps one call site working on both backends.
    """
    cur = conn.cursor()
    try:
        yield cur
    finally:
        cur.close()


def _split_statements(schema: str):
    """Split a multi-statement DDL script into single statements."""
    return [s.strip() for s in schema.split(";") if s.strip()]


def using_postgres() -> bool:
    """Postgres is used only when a host is configured."""
    return bool(DB_HOST)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _placeholder() -> str:
    return "%s" if using_postgres() else "?"


def get_connection():
    """
    Open a database connection.

    Raises RuntimeError with an actionable message when misconfigured, instead
    of letting psycopg fail deep inside a save loop.
    """
    if using_postgres():
        try:
            import psycopg
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "DB_HOST is set but psycopg is not installed. Run "
                'pip install "psycopg[binary]" — or unset DB_HOST to use SQLite.'
            ) from exc

        missing = [k for k in ("DB_NAME", "DB_USER", "DB_PASSWORD") if not os.getenv(k)]
        if missing:
            raise RuntimeError(f"Postgres selected but missing: {', '.join(missing)}")

        return psycopg.connect(
            host=DB_HOST, port=DB_PORT or 5432,
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
        )

    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SQLITE_PATH))
    # Create tables inline rather than calling init_db(), which itself calls
    # get_connection() - that recursion would never terminate.
    conn.executescript(SQLITE_SCHEMA)
    conn.commit()
    return conn


def init_db() -> None:
    """Create tables if they do not exist (idempotent)."""
    if using_postgres():
        conn = get_connection()
        try:
            with _cursor(conn) as cur:
                for statement in _split_statements(POSTGRES_SCHEMA):
                    cur.execute(statement)
            conn.commit()
        finally:
            conn.close()
        return

    # sqlite3.Cursor.execute() accepts exactly ONE statement; passing the
    # whole two-table schema raises
    # "You can only execute one statement at a time".
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SQLITE_PATH))
    try:
        for statement in _split_statements(SQLITE_SCHEMA):
            conn.execute(statement)
        conn.commit()
    finally:
        conn.close()


def save_products(items: Iterable[dict]) -> List[dict]:
    """
    Upsert parsed receipt items into the inventory.

    Each item: {"name": str, "price": float, "quantity": int}

    Returns a per-item report ("added" / "updated") so callers and tests can
    assert what happened instead of guessing.
    """
    ph = _placeholder()
    report: List[dict] = []
    conn = get_connection()

    try:
        with _cursor(conn) as cur:
            for item in items:
                cur.execute(
                    f"SELECT id, quantity FROM products WHERE name = {ph}",
                    (item["name"],),
                )
                row = cur.fetchone()
                if row:
                    product_id, old_qty = row[0], row[1] or 0
                    new_qty = old_qty + item["quantity"]
                    cur.execute(
                        f"UPDATE products SET quantity = {ph}, price = {ph}, "
                        f"updated_at = {ph} WHERE id = {ph}",
                        (new_qty, item["price"], _now(), product_id),
                    )
                    report.append({"name": item["name"], "action": "updated",
                                   "quantity": new_qty, "product_id": product_id})
                else:
                    cur.execute(
                        f"INSERT INTO products (name, price, quantity, updated_at) "
                        f"VALUES ({ph}, {ph}, {ph}, {ph})",
                        (item["name"], item["price"], item["quantity"], _now()),
                    )
                    product_id = cur.lastrowid
                    if product_id is None:  # postgres has no cursor.lastrowid
                        cur.execute(
                            f"SELECT id FROM products WHERE name = {ph}", (item["name"],)
                        )
                        fetched = cur.fetchone()
                        product_id = fetched[0] if fetched else None
                    report.append({"name": item["name"], "action": "added",
                                   "quantity": item["quantity"], "product_id": product_id})
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return report


def log_receipt(source_file: Optional[str], items: Iterable[dict]) -> int:
    """
    Keep a per-receipt audit trail.

    Inventory answers "how many do we have?"; this answers "where did that
    number come from?", which is what makes a wrong count debuggable.
    """
    rows = list(items)
    if not rows:
        return 0

    ph = _placeholder()
    conn = get_connection()
    try:
        with _cursor(conn) as cur:
            for item in rows:
                cur.execute(
                    f"INSERT INTO receipt_items (source_file, name, quantity, price, created_at) "
                    f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph})",
                    (source_file, item["name"], item["quantity"], item["price"], _now()),
                )
        conn.commit()
        return len(rows)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_products() -> List[dict]:
    """Current inventory, for verification and the demo report."""
    conn = get_connection()
    try:
        with _cursor(conn) as cur:
            cur.execute("SELECT id, name, price, quantity, updated_at FROM products ORDER BY name")
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


def reset_database() -> None:
    """Delete all rows - used by tests so each run starts from zero."""
    conn = get_connection()
    try:
        with _cursor(conn) as cur:
            cur.execute("DELETE FROM products")
            cur.execute("DELETE FROM receipt_items")
        conn.commit()
    finally:
        conn.close()