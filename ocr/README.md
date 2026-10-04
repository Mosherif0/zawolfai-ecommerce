# OCR Receipt Processing & Inventory System

Receipt image -> structured products -> inventory database, with a parser built
for *damaged* OCR output rather than for clean text.

```text
input/<file>
   v  preprocessing.py     upscale x4 - grayscale - CLAHE - denoise
   v  ocr.py               EasyOCR (en), confidence-filtered
   v  receipt_parser.py    row grouping -> price / quantity -> name
   v  inventory.py         SQLite (default) or PostgreSQL
output/
   processed/<file>.jpg    enhanced image
   <file>.ocr.json         detections for that image
   report.json             per-image summary
   inventory.db            SQLite database
```

## Quick start

```powershell
pip install -r requirements.txt
Copy-Item .env.example .env        # optional; SQLite works with no config

python pipeline.py                 # every image in input/, writes to the DB
python pipeline.py --dry-run       # parse only, never touch the database
python pipeline.py --limit 1       # just the first image
python pipeline.py --no-ocr        # reuse existing *.ocr.json (fast)
python pipeline.py --lang ar       # Arabic mode
python pipeline.py "input/one.jpg" # one specific file

python app.py                      # web UI on http://127.0.0.1:8000
```

Checks:

```powershell
pytest -q                          # 77 tests, no EasyOCR or DB required
python diagnose.py                 # readable pass/fail report of the parser
```

## Language: English by default, Arabic on request

Arabic is a switch, not a second codebase. `language_config.py` holds the
vocabulary; everything else reads from it.

```powershell
$env:OCR_LANGUAGE = "ar"           # process-wide default
python pipeline.py --lang ar       # or per run
```

| | English | Arabic |
|---|---|---|
| OCR models | `["en"]` | `["ar", "en"]` - receipts mix Latin brand names with Arabic labels |
| Footer labels | subtotal, tax, payment | المجموع الفرعي, الضريبة, المدفوع (English always kept) |
| Metadata | date, store, receipt no | التاريخ, الفرع, رقم الفاتورة |
| Digits | `2,495.00` | `٢٤٩٥٫٠٠` normalised to ASCII before any rule runs |
| RTL in the UI | `dir="ltr"` | `dir="rtl"` |

`OCR_LANGUAGES` overrides the model list if you need something else.

## The receipt gate

A photo that is not a receipt produces confident nonsense: the Spotify
novelty receipts in this repo's own `input/` yielded products like
"ARCTIC MONKEYS 05 OLIVIA RODRIGO 8.00". The decision therefore happens
*before* rows are parsed - once parsed, nothing downstream can tell a real
line item from a track title.

`validation.py` scores three independent dimensions and needs structure plus
one supporting signal:

| Dimension | What it measures |
|---|---|
| **structure** | receipt furniture, weighted: `subtotal` (3.0) counts far more than `thank you` (1.5) |
| **numbers** | a column of plausible, varied prices |
| **shape** | tall, narrow, bright page - deliberately the weakest signal |

Two rules do most of the work:

* **At least two independent STRONG signals.** The Spotify receipts print
  "receipt", "thank you", "item count" and even "total" - every one of those
  is weak and cannot on its own accept anything.
* **One-edit tolerance on keywords.** EasyOCR read a real Lowe's receipt
  "slbtotal" instead of "subtotal"; without fuzzy matching that receipt was
  rejected as a non-receipt.

Measured on this repo's images: 7/7 real receipts accepted, 2/2 novelty
receipts rejected, ~90 ms per image.

## What the parser has to survive

EasyOCR on a photographed receipt produces damaged text. Each row below was a
real failure found by running the pipeline, and each has a regression test:

| OCR damage | Symptom before | Handling |
|---|---|---|
| `1,299.50` | priced as **1.29** | `normalize_price_text` strips a comma only when followed by exactly three digits |
| `Subtota/` | sold as a **product** | footer labels matched with 1-edit tolerance (Levenshtein) |
| `WOOL SOCKS 3X` | name became `WOOL SOCKX`, qty `1` | currency lookbehind + quantity markers at start **and** end |
| `Shirts USD9.99` | name became `Shirts USD` | currency-prefixed patterns run before the bare-decimal one |
| `s49,99` | name became `Denim Jeans 49.99` | orphan currency glyph removed, residual price stripped |
| merged rows | two items merged into one row | adaptive row threshold from median glyph height, nearest-row matching |
| whole receipt read as one blob | 60-word "product" rows | length and price sanity gate |

The last two matter most in practice: they are what stop a non-receipt photo
from polluting the inventory.

## Row grouping

`group_rows` derives its y-tolerance from the **median glyph height** in the
OCR output instead of a fixed pixel value. A fixed threshold merges adjacent
line items on a tightly-set receipt and splits one long name on a loosely-set
one; scaling with the text height makes it independent of how far away the
receipt was photographed. Each detection is matched to the **nearest** existing
row rather than the first one in range, so a tall row cannot swallow the line
between two others.

## Inventory semantics

`save_products` is an upsert:

* unknown product name -> inserted
* known product name -> `quantity += n`, price refreshed

`log_receipt` additionally records every parsed line in `receipt_items`, so
"why is stock 47?" is answerable - `products` holds the current state,
`receipt_items` holds the provenance.

## Database backends

Postgres is used only when `DB_HOST` is set in `.env`; otherwise SQLite at
`output/inventory.db`. Both go through the same code path, and the tests always
run against an isolated SQLite file.

```sql
CREATE TABLE products (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    price      REAL    NOT NULL,
    quantity   INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT    NOT NULL
);
```

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `DB_HOST` | *(unset)* | set to switch to PostgreSQL |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | - | required when Postgres is selected |
| `SQLITE_PATH` | `output/inventory.db` | SQLite file location |
| `OCR_LANGUAGES` | `en` | comma-separated; add `ar` for Arabic receipts |
| `OCR_MIN_CONFIDENCE` | `0.30` | detections below this are discarded |

## Verified against real receipts

| Receipt | Items parsed |
|---|---|
| ZARA, City Stars | Black Blazer 59.99 - White Shirt 45.95 - Wide Leg Jeans 69.99 - Leather Belt 25.00 |
| LC Waikiki, Alexandria | Women Sweater 79.99 - Men Hoodie 99.99 - Kids T-Shirt 59.99 |
| IKEA, Cairo Festival City | KALLAX Shelf Unit 2495.00 - Desk Lamp 599.00 - Plant Pot 149.00 - Storage Box 199.00 |

## Known limitations

* No Arabic receipts yet - `OCR_LANGUAGES=ar` needs an Arabic model plus
  Arabic-aware footer/quantity keywords (the current lists are English).
* No currency detection: prices are stored as bare numbers.
* `extract_product_info.py` is a hard-coded NIVEA / moisture-serum extractor
  and is not wired into this pipeline.
* Barcode decoding is not implemented, so receipts are matched by content only.


---

## Warehouse

The pipeline produces items; the warehouse stores them with enough context to
answer "why is stock wrong?" months later.

```
suppliers        who we buy from
categories       product taxonomy
products         item + current stock (a cache)
receipts         one row per scanned receipt, with its image filename
receipt_items    one row per line on that receipt
stock_movements  append-only ledger of every quantity change
```

### Why a movements ledger

`products.quantity` is a **cache**. `stock_movements` is the truth:

```sql
-- when did this product change, and what caused it?
SELECT m.created_at, m.delta, m.reason, r.source_file
FROM stock_movements m
LEFT JOIN receipts r ON r.id = m.ref_id
WHERE m.product_id = $1
ORDER BY m.created_at DESC;
```

Because every change is recorded, `rebuild_quantities()` can throw the cache
away and recompute it. A bad count becomes repairable instead of destructive:

```sql
UPDATE products SET quantity = COALESCE((
    SELECT SUM(delta) FROM stock_movements WHERE product_id = products.id), 0);
```

### Operations

| | |
|---|---|
| `adjust_stock(id, -1, "sale")` | change stock, constrained to a fixed set of reasons |
| `delete_product(id)` | remove the product and its history |
| `delete_receipt(id)` | remove a receipt **and revert the stock it added** |
| `reset_table(t)` | clear a table (whitelisted - `sqlite_master` is rejected) |
| `rebuild_quantities()` | recompute stock from the ledger |

Movement reasons are a fixed enum (`receipt_scan`, `sale`, `return_in`,
`return_out`, `adjustment`, `damage`, `initial`) so "show me every manual
correction" stays answerable.

### SQLite and PostgreSQL

Both run through the same code. Postgres is selected by setting `DB_HOST` in
`.env`; the schema is applied on first connection.

```powershell
# switch to Postgres
DB_HOST=localhost
DB_NAME=zawolf_ocr
DB_USER=postgres
DB_PASSWORD=...

python migrate_sqlite_to_postgres.py --execute   # move existing rows
```

The migration matches products by name and receipts by
`(source_file, created_at)`, so running it twice does not duplicate anything.

### Warehouse API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/warehouse/products?search=&category=` | browse stock |
| GET | `/api/warehouse/products/{id}` | one product + its movement history |
| POST | `/api/warehouse/products/{id}/adjust` | `{delta, reason}` |
| DELETE | `/api/warehouse/products/{id}` | delete a product |
| GET | `/api/warehouse/receipts` | scanned receipts |
| DELETE | `/api/warehouse/receipts/{id}` | delete and revert its stock |
| GET | `/api/warehouse/stats` | dashboard counters |
| POST | `/api/warehouse/rebuild` | rebuild quantities from the ledger |
| POST | `/api/warehouse/reset/{table}` | clear a table |

The web UI has a **Stock** and a **Receipts** tab for all of it, including the
delete buttons.

