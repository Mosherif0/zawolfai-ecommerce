"""
PostgreSQL / SQLite schema for the OCR inventory system.

The database consists of three tables:

    products
    receipts
    receipt_items

PostgreSQL is the source of truth for the warehouse data.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List

try:
    import psycopg
except ImportError:
    psycopg = None


# --------------------------------------------------------------------------
# DDL
# --------------------------------------------------------------------------

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    price      REAL NOT NULL DEFAULT 0,
    quantity   INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS receipts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_date TEXT,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS receipt_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_id INTEGER NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity   INTEGER NOT NULL DEFAULT 1,
    price      REAL NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_items_receipt
    ON receipt_items(receipt_id);

CREATE INDEX IF NOT EXISTS idx_items_product
    ON receipt_items(product_id);
"""


POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    price      DOUBLE PRECISION NOT NULL DEFAULT 0,
    quantity   INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS receipts (
    id           SERIAL PRIMARY KEY,
    receipt_date TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS receipt_items (
    id         SERIAL PRIMARY KEY,
    receipt_id INTEGER NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity   INTEGER NOT NULL DEFAULT 1,
    price      DOUBLE PRECISION NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_items_receipt
    ON receipt_items(receipt_id);

CREATE INDEX IF NOT EXISTS idx_items_product
    ON receipt_items(product_id);
"""


# --------------------------------------------------------------------------
# Connection / schema
# --------------------------------------------------------------------------

def apply_schema(conn, backend: str = "sqlite") -> None:
    """
    Ensure the required tables exist.

    Existing tables and data are not deleted or replaced.
    """
    ddl = SQLITE_SCHEMA if backend == "sqlite" else POSTGRES_SCHEMA

    if backend == "sqlite":
        conn.executescript(ddl)
        try:
            cur = conn.execute("PRAGMA table_info(receipt_items)")
            cols = [r[1] for r in cur.fetchall()]
            if cols and "receipt_id" not in cols:
                conn.execute("ALTER TABLE receipt_items ADD COLUMN receipt_id INTEGER NOT NULL DEFAULT 1 REFERENCES receipts(id) ON DELETE CASCADE")
        except Exception:
            pass
    else:
        with conn.cursor() as cur:
            cur.execute(ddl)

    conn.commit()


def sqlite_connect(path: Path | str):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row

    apply_schema(conn, "sqlite")
    return conn


def postgres_connect(host, port, dbname, user, password):
    if psycopg is None:
        raise RuntimeError(
            'PostgreSQL selected but psycopg is not installed. '
            'Run: pip install "psycopg[binary]"'
        )

    conn = psycopg.connect(
        host=host,
        port=port or 5432,
        dbname=dbname,
        user=user,
        password=password,
    )

    apply_schema(conn, "postgres")
    return conn


# --------------------------------------------------------------------------
# Inspection helpers
# --------------------------------------------------------------------------

def table_counts(conn, backend: str = "sqlite") -> Dict[str, int]:
    """Return row counts for the three inventory tables."""

    names = (
        "products",
        "receipts",
        "receipt_items",
    )

    out: Dict[str, int] = {}

    for name in names:
        try:
            if backend == "sqlite":
                cur = conn.execute(f"SELECT COUNT(*) FROM {name}")
                out[name] = cur.fetchone()[0]
            else:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT COUNT(*) FROM {name}")
                    out[name] = cur.fetchone()[0]

                conn.commit()

        except Exception:
            out[name] = -1

    return out


def describe(conn, backend: str = "sqlite") -> List[Dict]:
    """Return column-level information for the three inventory tables."""

    tables = (
        "products",
        "receipts",
        "receipt_items",
    )

    rows = []

    for table in tables:

        if backend == "sqlite":
            info = conn.execute(
                f"PRAGMA table_info({table})"
            ).fetchall()

            for col in info:
                rows.append({
                    "table": table,
                    "column": col[1],
                    "type": col[2],
                    "nullable": not bool(col[3]),
                })

        else:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        column_name,
                        data_type,
                        is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    (table,),
                )

                info = cur.fetchall()

            for col in info:
                rows.append({
                    "table": table,
                    "column": col[0],
                    "type": col[1],
                    "nullable": col[2] == "YES",
                })

    return rows