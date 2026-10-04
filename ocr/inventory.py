"""
Compatibility shim.

The warehouse layer (warehouse.py + schema.py) is the single source of
truth for stock. This module previously held its own flat 'products' table
implementation, which meant two modules writing the same database through
different code paths - the split that let a receipt write to one table while
/api/warehouse read another.

Everything here delegates to warehouse.py, so any remaining caller (older
notebooks, the CLI, third-party scripts) keeps working and produces the same
numbers. The flat table is no longer used.

Prefer importing warehouse directly in new code.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

import warehouse as _warehouse


def backend() -> str:
    """'postgres' or 'sqlite'."""
    return _warehouse.backend()


def using_postgres() -> bool:
    return _warehouse.backend() == "postgres"


def init_db() -> None:
    """Create the warehouse schema if it does not exist."""
    if hasattr(_warehouse, "init_db"):
        _warehouse.init_db()


def save_products(items: Iterable[dict]) -> List[dict]:
    """
    Upsert items and record the movement.

    Returns a flat per-item report so older callers expecting
    [{'action': ..., 'name': ..., 'quantity': ...}] keep working.
    """
    result = _warehouse.record_receipt(list(items))
    return [
        {
            "name": entry["name"],
            "action": entry["action"],
            "quantity": entry["quantity"],
            "product_id": entry["product_id"],
        }
        for entry in result["items"]
    ]


def log_receipt(source_file: Optional[str], items: Iterable[dict]) -> int:
    """
    NOTE: receipts are recorded by save_products via warehouse.record_receipt,
    which already writes the receipt and its items in one transaction. Calling
    this separately would double-count. It is kept only so existing callers do
    not crash; it returns the number of items it was handed.
    """
    return len(list(items))


def list_products() -> List[dict]:
    return _warehouse.list_products()


def reset_database() -> None:
    """Clear every table (used by tests)."""
    for table in ("stock_movements", "receipt_items", "receipts", "products"):
        _warehouse.reset_table(table)
