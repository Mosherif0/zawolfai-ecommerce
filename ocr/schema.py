"""
Warehouse schema.

The flat two-table version could answer "how many?" but not "why?", which is
the question that actually matters when stock is wrong. This schema records
provenance and movement instead of only a running total.

    suppliers          who we buy from
    categories         product taxonomy
    products           the item + current stock
    receipts           one row per scanned receipt (the source image)
    receipt_items      one row per line on that receipt
    stock_movements    append-only ledger of every quantity change

Why a movements ledger rather than a counter
--------------------------------------------
`products.quantity` is a cache. The ledger is the truth: it can answer "when
did this go from 12 to 3 and what caused it", survive a bad count, and be
replayed to rebuild the cache. Storing only a counter makes any correction
destructive and untraceable.

Works on SQLite and PostgreSQL; the DDL differences are the only branch.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List

try:
    import psycopg
except ImportError:  # postgres is optional; SQLite needs nothing
    psycopg = None

# --------------------------------------------------------------------------
# DDL
# --------------------------------------------------------------------------

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS suppliers (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    price       REAL NOT NULL DEFAULT 0,
    quantity    INTEGER NOT NULL DEFAULT 0,
    category_id INTEGER REFERENCES categories(id),
    supplier_id INTEGER REFERENCES suppliers(id),
    barcode     TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS receipts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file  TEXT,
    store        TEXT,
    receipt_date TEXT,
    total        REAL,
    language     TEXT,
    status       TEXT NOT NULL DEFAULT 'accepted',
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS receipt_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_id   INTEGER REFERENCES receipts(id) ON DELETE CASCADE,
    product_id   INTEGER REFERENCES products(id),
    name_raw     TEXT NOT NULL,
    quantity     INTEGER NOT NULL DEFAULT 1,
    unit_price   REAL NOT NULL,
    line_total   REAL,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stock_movements (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    delta      INTEGER NOT NULL,
    reason     TEXT NOT NULL,
    ref_type   TEXT,
    ref_id     INTEGER,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_items_receipt ON receipt_items(receipt_id);
CREATE INDEX IF NOT EXISTS idx_items_product ON receipt_items(product_id);
CREATE INDEX IF NOT EXISTS idx_moves_product ON stock_movements(product_id);
CREATE INDEX IF NOT EXISTS idx_products_cat   ON products(category_id);
"""

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS suppliers (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id   SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    price       DOUBLE PRECISION NOT NULL DEFAULT 0,
    quantity    INTEGER NOT NULL DEFAULT 0,
    category_id INTEGER REFERENCES categories(id),
    supplier_id INTEGER REFERENCES suppliers(id),
    barcode     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS receipts (
    id           SERIAL PRIMARY KEY,
    source_file  TEXT,
    store        TEXT,
    receipt_date TEXT,
    total        DOUBLE PRECISION,
    language     TEXT,
    status       TEXT NOT NULL DEFAULT 'accepted',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS receipt_items (
    id           SERIAL PRIMARY KEY,
    receipt_id   INTEGER REFERENCES receipts(id) ON DELETE CASCADE,
    product_id   INTEGER REFERENCES products(id),
    name_raw     TEXT NOT NULL,
    quantity     INTEGER NOT NULL DEFAULT 1,
    unit_price   DOUBLE PRECISION NOT NULL,
    line_total   DOUBLE PRECISION,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stock_movements (
    id         SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    delta      INTEGER NOT NULL,
    reason     TEXT NOT NULL,
    ref_type   TEXT,
    ref_id     INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_items_receipt  ON receipt_items(receipt_id);
CREATE INDEX IF NOT EXISTS idx_items_product ON receipt_items(product_id);
CREATE INDEX IF NOT EXISTS idx_moves_product ON stock_movements(product_id);
CREATE INDEX IF NOT EXISTS idx_products_cat   ON products(category_id);
"""

#: Reasons a stock movement can have. Constrained so the ledger stays queryable
#: ("everything that was a manual correction" is a real question).
MOVEMENT_REASONS = (
    "receipt_scan",   # stock received from a scanned receipt
    "sale",           # sold to a customer
    "return_in",      # customer returned it
    "return_out",     # we returned it to the supplier
    "adjustment",     # manual correction after a physical count
    "damage",         # written off
    "initial",        # opening balance
)


def apply_schema(conn, backend: str = "sqlite") -> None:
    """Create every table if it does not exist. Idempotent."""
    ddl = SQLITE_SCHEMA if backend == "sqlite" else POSTGRES_SCHEMA
    if backend == "sqlite":
        conn.executescript(ddl)
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
            'PostgreSQL selected but psycopg is not installed. Run: pip install "psycopg[binary]"'
        )
    conn = psycopg.connect(host=host, port=port or 5432,
                           dbname=dbname, user=user, password=password)
    apply_schema(conn, "postgres")
    return conn


def table_counts(conn, backend: str = "sqlite") -> Dict[str, int]:
    """Row counts per table - the fastest way to see what the DB holds."""
    names = ("suppliers", "categories", "products", "receipts",
             "receipt_items", "stock_movements")
    out: Dict[str, int] = {}
    for name in names:
        try:
            if backend == "sqlite":
                cur = conn.execute(f"SELECT COUNT(*) FROM {name}")
                out[name] = cur.fetchone()[0]
            else:
                # A fresh Postgres connection starts a transaction that a plain
                # SELECT leaves open; it must be committed (or rolled back)
                # or every later query on this connection fails.
                with conn.cursor() as cur:
                    cur.execute(f"SELECT COUNT(*) FROM {name}")
                    out[name] = cur.fetchone()[0]
                conn.commit()
        except Exception as exc:
            out[name] = -1
    return out


def describe(conn, backend: str = "sqlite") -> List[Dict]:
    """Column-level description, for a UI or a sanity check."""
    tables = ("products", "receipts", "receipt_items", "stock_movements",
              "suppliers", "categories")
    rows = []
    for table in tables:
        if backend == "sqlite":
            info = conn.execute(f"PRAGMA table_info({table})").fetchall()
        else:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT column_name, data_type, is_nullable "
                    "FROM information_schema.columns WHERE table_name = %s",
                    (table,),
                )
                info = cur.fetchall()
        for col in info:
            rows.append({
                "table": table,
                "column": col[1],
                "type": col[2],
                "nullable": col[3],
            })
    return rows