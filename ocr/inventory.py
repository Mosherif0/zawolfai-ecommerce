"""
Compatibility shim.

The warehouse layer (warehouse.py + schema.py) is the single source of
truth for inventory data.

This module delegates all database operations to warehouse.py so older
callers can continue to work without maintaining a second database layer.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

import warehouse as _warehouse


def backend() -> str:
    """Return the active database backend: 'postgres' or 'sqlite'."""
    return _warehouse.backend()


def using_postgres() -> bool:
    """Return True when PostgreSQL is the active backend."""
    return _warehouse.backend() == "postgres"


def init_db() -> None:
    """Ensure the warehouse schema exists."""
    _warehouse.init_db()


def save_products(items: Iterable[dict]) -> List[dict]:
    """
    Save OCR products through the warehouse layer.

    Each call records one receipt and its receipt items.
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


def log_receipt(
    source_file: Optional[str],
    items: Iterable[dict],
) -> int:
    """
    Compatibility function for older callers.

    Receipts are already recorded by save_products() through
    warehouse.record_receipt(), so this function must not create
    another receipt or double-count inventory.
    """

    _ = source_file

    return len(list(items))


def list_products() -> List[dict]:
    """Return all products."""
    return _warehouse.list_products()


def reset_database() -> None:
    """
    Clear all inventory tables.

    Child table receipt_items is cleared before its parent tables.
    """

    _warehouse.reset_table("receipt_items")
    _warehouse.reset_table("receipts")
    _warehouse.reset_table("products")