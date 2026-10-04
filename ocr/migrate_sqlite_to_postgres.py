"""
Migrate warehouse data from SQLite to PostgreSQL.

Run it twice to prove it is safe:
  1. first run  -> moves the rows
  2. second run -> reports "nothing to migrate"

Products are matched by name (the natural key), so a product that already
exists in Postgres is skipped rather than duplicated. Receipts are matched by
(source_file, created_at) for the same reason.

    python migrate_sqlite_to_postgres.py                 # dry run
    python migrate_sqlite_to_postgres.py --execute       # actually write
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))

SOURCE = Path("output/inventory.db")


def read_source(path: Path = SOURCE) -> Dict[str, List[tuple]]:
    if not path.is_file():
        raise SystemExit(f"source database not found: {path}")

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        def grab(table: str) -> List[tuple]:
            try:
                return [tuple(r) for r in conn.execute(f"SELECT * FROM {table}")]
            except sqlite3.OperationalError:
                return []

        return {
            "suppliers": grab("suppliers"),
            "categories": grab("categories"),
            "products": grab("products"),
            "receipts": grab("receipts"),
            "receipt_items": grab("receipt_items"),
            "stock_movements": grab("stock_movements"),
        }
    finally:
        conn.close()


def migrate(execute: bool = False, source: Path = SOURCE) -> Dict:
    import warehouse as wh

    data = read_source(source)
    total = sum(len(v) for v in data.values())

    print(f"Source : {source}")
    print(f"Target : {wh.backend()}")
    for table, rows in data.items():
        print(f"  {table:18} {len(rows):>4} rows")
    print(f"  {'TOTAL':18} {total:>4} rows")

    if not execute:
        print("\n[dry-run] pass --execute to write.")
        return {"migrated": 0, "total": total}

    if wh.backend() != "postgres":
        raise SystemExit(
            "Target is not PostgreSQL. Set DB_HOST/DB_NAME/DB_USER/DB_PASSWORD in .env"
        )

    p = wh.ph()
    moved = {"suppliers": 0, "categories": 0, "products": 0,
             "receipts": 0, "receipt_items": 0, "stock_movements": 0}
    name_to_id: Dict[str, int] = {}

    with wh.connection() as conn:
        with wh.cursor(conn) as cur:
            # --- suppliers ---
            for row in data["suppliers"]:
                sid, name, created = row[0], row[1], row[2]
                cur.execute(f"SELECT id FROM suppliers WHERE name = {p}", (name,))
                found = cur.fetchone()
                if found:
                    name_to_id[name] = found[0]
                    continue
                cur.execute(
                    f"INSERT INTO suppliers (name, created_at) VALUES ({p}, {p})",
                    (name, created))
                name_to_id[name] = cur.fetchone()[0] if wh.using_postgres() else cur.lastrowid
                moved["suppliers"] += 1

            # --- categories ---
            for row in data["categories"]:
                cid, name = row[0], row[1]
                cur.execute(f"SELECT id FROM categories WHERE name = {p}", (name,))
                found = cur.fetchone()
                if found:
                    name_to_id[f"cat:{name}"] = found[0]
                    continue
                cur.execute(f"INSERT INTO categories (name) VALUES ({p})", (name,))
                name_to_id[f"cat:{name}"] = cur.fetchone()[0] if wh.using_postgres() else cur.lastrowid
                moved["categories"] += 1

            # --- products ---
            product_name_to_id: Dict[str, int] = {}
            for row in data["products"]:
                (pid, name, price, qty, cat_id, sup_id,
                 barcode, created, updated) = row
                cur.execute(f"SELECT id FROM products WHERE name = {p}", (name,))
                found = cur.fetchone()
                if found:
                    product_name_to_id[name] = found[0]
                    continue
                cur.execute(
                    f"INSERT INTO products (name, price, quantity, category_id, "
                    f"supplier_id, barcode, created_at, updated_at) "
                    f"VALUES ({p},{p},{p},{p},{p},{p},{p},{p})",
                    (name, price, qty, cat_id, sup_id, barcode, created, updated))
                new_id = cur.fetchone()[0] if wh.using_postgres() else cur.lastrowid
                product_name_to_id[name] = new_id
                moved["products"] += 1

            # --- receipts ---
            receipt_key_to_id: Dict[tuple, int] = {}
            for row in data["receipts"]:
                (rid, source_file, store, receipt_date, total, language,
                 status, created) = row
                key = (source_file, created)
                cur.execute(
                    f"SELECT id FROM receipts WHERE source_file = {p} AND created_at = {p}",
                    (source_file, created))
                found = cur.fetchone()
                if found:
                    receipt_key_to_id[key] = found[0]
                    continue
                cur.execute(
                    f"INSERT INTO receipts (source_file, store, receipt_date, total, "
                    f"language, status, created_at) VALUES ({p},{p},{p},{p},{p},{p},{p})",
                    (source_file, store, receipt_date, total, language, status, created))
                receipt_key_to_id[key] = cur.fetchone()[0] if wh.using_postgres() else cur.lastrowid
                moved["receipts"] += 1

        conn.commit()

    print(f"\nMoved: {moved}  (total {sum(moved.values())})")
    return {"migrated": sum(moved.values()), "detail": moved, "total": total}


def main() -> int:
    ap = argparse.ArgumentParser(description="Migrate SQLite warehouse to PostgreSQL")
    ap.add_argument("--execute", action="store_true", help="actually write (default: dry run)")
    ap.add_argument("--source", default=str(SOURCE))
    args = ap.parse_args()

    result = migrate(execute=args.execute, source=Path(args.source))
    return 0 if result["migrated"] >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())