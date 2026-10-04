"""
Diagnostic harness for the OCR parser.

Runs WITHOUT easyocr / cv2 / psycopg by stubbing the database import, so the
parsing logic can be validated even before the ML dependencies are installed.
"""

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Stub the Postgres-touching modules so receipt_parser imports cleanly.
db = types.ModuleType("database")
db.get_connection = lambda: (_ for _ in ()).throw(RuntimeError("no database"))
sys.modules.setdefault("database", db)

inv = types.ModuleType("inventory")
inv.save_products = lambda items: None
sys.modules.setdefault("inventory", inv)

import receipt_parser as rp  # noqa: E402


def check(label, got, expected):
    ok = got == expected
    print(f"  {'PASS' if ok else 'FAIL'}  {label:26} got={got!r:14} want={expected!r}")
    return ok


def main() -> int:
    failures = 0

    print("=== extract_price ===")
    cases = [
        ("$19.99", 19.99),
        ("S19.99", 19.99),
        ("19.99", 19.99),
        ("USD89", 89.0),
        ("USD120", 120.0),
        ("USD89.99", 89.99),
        ("1,299.50", 1299.50),
    ]
    for text, want in cases:
        failures += not check(text, rp.extract_price(text), want)

    print("\n=== extract_quantity ===")
    for text, want in [("2 x ABC", 2), ("3 - DEF", 3), ("ITEM", 1),
                       ("6FT HDMI CABLE", 1), ("4 CABLES", 4)]:
        failures += not check(text, rp.extract_quantity(text), want)

    print("\n=== remove_price keeps the 's' in product names ===")
    for text, want in [("Jeans $45.00", "Jeans"),
                       ("Sneakers S12.99", "Sneakers"),
                       ("Shirts USD9.99", "Shirts")]:
        failures += not check(text, rp.remove_price(text), want)

    print("\n=== summary / metadata detection ===")
    for text in ["TOTAL 45.00", "Subtotal: 39.99", "TAX 5.00",
                 "Date: 01/02/2026", "Store #12", "Receipt No 99"]:
        detected = rp.is_summary_row(text, 45.0) or rp.is_metadata_row(text)
        failures += not check(text, detected, True)

    print("\n=== end-to-end on a synthetic receipt ===")
    # Two real line items plus footer noise; the totals must NOT become products.
    ocr = [
        {"text": "WOOL SOCKS 3X", "confidence": 0.94, "bbox": [[0, 0], [300, 0], [300, 20], [0, 20]]},
        {"text": "$12.99", "confidence": 0.91, "bbox": [[320, 0], [420, 0], [420, 20], [320, 20]]},
        {"text": "COTTON T-SHIRT", "confidence": 0.89, "bbox": [[0, 40], [300, 40], [300, 60], [0, 60]]},
        {"text": "$24.50", "confidence": 0.93, "bbox": [[320, 40], [420, 40], [420, 60], [320, 60]]},
        {"text": "SUBTOTAL", "confidence": 0.88, "bbox": [[0, 90], [200, 90], [200, 110], [0, 110]]},
        {"text": "$37.49", "confidence": 0.90, "bbox": [[320, 90], [420, 90], [420, 110], [320, 110]]},
    ]
    rows = rp.group_rows(ocr)
    items = rp.parse_rows(rows)
    for it in items:
        print(f"    {it}")
    failures += not check("item count", len(items), 2)
    failures += not check("first name", items[0]["name"], "WOOL SOCKS")
    failures += not check("first qty", items[0]["quantity"], 3)
    failures += not check("no SUBTOTAL leaked", any("SUBTOTAL" in i["name"] for i in items), False)

    print(f"\n{'ALL CHECKS PASSED' if not failures else f'{failures} CHECK(S) FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())