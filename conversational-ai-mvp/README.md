# Conversational AI Assistant MVP

A lightweight, clean, and interactive **Conversational AI Assistant MVP** built with **FastAPI**, **Google Gemini** (google-genai SDK), in-memory conversation memory, mock business data, and a modern vanilla HTML/CSS/JavaScript chat interface.

---

## 🏗️ Architecture

`	ext
┌──────────────────────────────────────────────┐
│        Chat UI (HTML/CSS/JS)                 │
│  • Modern RTL UI  • Suggested Prompts        │
│  • Loading States • New Chat / Reset         │
└──────────────────────┬───────────────────────┘
                       │ HTTP JSON
                       ▼
┌──────────────────────────────────────────────┐
│        FastAPI (app/main.py)                 │
│  • GET / (serves Chat UI)                    │
│  • GET /health                               │
│  • POST /api/chat                            │
│  • POST /api/chat/reset                      │
└──────────────────────┬───────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
┌──────────────────┐       ┌──────────────────┐
│  Conversation    │       │  Mock Business   │
│  Memory Service  │       │  Data & Context  │
│  (In-memory dict)│       │  (Products/Orders│
└────────┬─────────┘       │   Policies/FAQs) │
         │                 └─────────┬────────┘
         └─────────────┬─────────────┘
                       ▼
┌──────────────────────────────────────────────┐
│        Gemini Service (google-genai)         │
│  • System Prompt (Egyptian Arabic + Rules)   │
│  • Context Injection                         │
│  • Multi-turn history handling               │
│  • Graceful fallback / API error handling    │
└──────────────────────────────────────────────┘
```

---

## 📁 Project Structure

`	ext
D:\My-Projects\conversational-ai-mvp
│
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application and routing
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── chat.py             # Chat and reset endpoints
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gemini.py           # Gemini API client & fallback handler
│   │   ├── conversation.py     # In-memory multi-turn session store
│   │   └── mock_data.py        # Generic mock business data & context
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── chat.py             # Pydantic request/response schemas
│   │
│   ├── prompts/
│   │   └── system_prompt.txt   # Egyptian Arabic persona and rules
│   │
│   └── static/
│       ├── index.html          # Interactive Chat UI
│       ├── style.css           # Modern RTL styles & animations
│       └── app.js              # Vanilla JS frontend client
│
├── tests/
│   └── test_chat.py            # Automated pytest suite (unit + API)
│
├── .env                        # Local environment configuration
├── .env.example                # Example environment template
├── .gitignore                  # Standard Python gitignore
├── requirements.txt            # Project dependencies
└── README.md                   # Documentation
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+ installed
- Windows PowerShell or terminal

### 2. Setup Virtual Environment & Install Dependencies

```powershell
cd D:\My-Projects\conversational-ai-mvp

# Create virtual environment (optional)
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Edit .env (or copy from .env.example):

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_FALLBACK_MODELS=gemini-3.5-flash,gemini-3.6-flash
GEMINI_TIMEOUT_MS=30000
```

*Variables: `GEMINI_MODEL` is the primary model. `GEMINI_FALLBACK_MODELS` (optional) is a comma-separated list tried automatically when the primary model is unavailable (e.g. `404` retired model or `503` high demand). `GEMINI_TIMEOUT_MS` (optional) is the per-request timeout in milliseconds so a stuck model never freezes the chat.*

*(Note: `GEMINI_2_5_FLASH` family models were retired by Google and now return 404 — the fallback list avoids them.)*

*Catalog paths are optional and have working defaults; override them if the recommendation project lives elsewhere:*

```env
CATALOG_PATH=D:\path\to\clean_catalog.csv
CATALOG_IMAGES_DIR=D:\path\to\data\images
```

### 3b. Prepare Product Images

The chat app serves its own copy of the product photos so it stays
self-contained (no dependency on a second server, no base64 payloads, and the
browser can cache them for 7 days).

```powershell
.\.venv\Scripts\python scripts\organize_images.py
```

This copies the photos into a **readable, browsable layout**:

```
app/static/images/
  catalog.json                                    <- manifest (id -> file + facets)
  jackets/black/   0282832001__black__kevin-softshell-jacket-1.jpg
  jackets/blue/    0300908003__blue__freja-coat.jpg
  dresses/red/     0212629040__red__alcazar-strap-dress.jpg
  trousers/blue/   0573085001__blue__madison-skinny-hw.jpg
  tops/black/      0237222001__black__helsinki.jpg
  vest-tops/white/ 0108775015__white__strap-top.jpg
```

Images are nested by **category / colour**, and the filename is
`product_id__colour__product-name.jpg`. The organiser is **idempotent** — drop
new photos into the upstream `data/images/` folder and re-run the script; it
picks up exactly what is new, rewrites the manifest, and prunes stale files.

The numeric `product_id` stays as the filename prefix because the server
resolves products by id; the readable slug after `__` is only for humans.
The script is idempotent — safe to re-run at any time.

(If you only want a flat copy with no folders, use `scripts/sync_images.py`
instead; the server falls back to the flat layout automatically.)

### 4. Run the Server

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 5. Open in Browser

- **Chat UI**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive API Docs (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### API endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/chat` | One chat turn (multi-turn memory + product cards) |
| POST | `/api/chat/reset` | Clear a conversation |
| GET | `/api/catalog` | All products grouped by Arabic category |
| GET | `/api/products/{id}` | One product + complementary / similar items |
| GET | `/api/facets` | Distinct category / colour / brand / tier values + counts |
| GET | `/api/health/catalog` | Catalog diagnostics (count, load errors) |
| GET | `/static/images/{id}.jpg` | Product photos (cached 7 days) |

---

## 🧠 How the assistant decides what to show

The catalog is **not** dumped into the prompt. Retrieval is deterministic so
the model never invents a product or a price.

```
user message
    │
    ├─► chit-chat gate ──────► no product cards (greetings / acknowledgements)
    │
    ├─► intent parsing (expand_query)
    │     Egyptian Arabic → English tokens
    │     category · colour · brand · budget ceiling/floor · price sentiment
    │     + "show me everything" short-circuit
    │     + routing for items we do not stock (tee → top, hoodie → jacket)
    │
    ├─► facet narrowing (most specific first, never empty)
    │     colour family → category → brand → price band
    │     Each step is skipped rather than returning nothing, so an
    │     impossible request still gets the nearest match instead of a
    │     broken-looking empty grid.
    │
    ├─► BM25 ranking over the catalog  (pure-stdlib Okapi BM25)
    │
    ├─► hard filters (never allowed to empty the result set)
    │
    ├─► follow-up resolution
    │     "التاني بكام؟" has no lexical overlap, so the ids currently shown
    │     on screen are merged in — but ONLY when the user has no explicit
    │     new intent, otherwise a stale request hijacks the turn
    │
    └─► ONE result set feeds BOTH
          • the system instruction  (REAL CATALOG block + grounding rules)
          • the product cards in the UI
```

Because the same retrieved rows drive the prompt and the cards, the assistant
cannot talk about a product the customer cannot see, and cannot quote a price
that is not on the card.

### Prices are deterministic

The upstream `price` column is an internal rank (range 1–431, mean ≈27.7), not
a currency amount. Prices are therefore derived from `price_tier`:

| tier | EGP range |
|---|---|
| budget | 150 – 350 |
| mid_range | 400 – 800 |
| premium | 900 – 1800 |

Each product is seeded with `Random(f"{product_id}:{tier}")`, so a product
always has the same price across restarts and turns — which is what makes the
grounding assertions in the test suite meaningful.

### Retrieval quality

Measured on a hand-labelled ground-truth set of Egyptian-Arabic queries
(`tests/test_evaluation.py`):

| ranker | recall@5 |
|---|---|
| substring matching (previous behaviour) | 0% |
| BM25 + intent filters (current) | **100%** |

Retrieval and generation are measured separately: a wrong answer either means
retrieval missed the product (fix the ranker) or the model ignored a grounded
prompt (fix the prompt).

### When Gemini is unavailable

The service raises `GeminiUnavailableError` and the user gets a natural retry
message with **no product cards**. It never fabricates a reply: an invented
order status is worse than an honest pause.

Colour matching is done by **family**, not equality: asking for "blue" matches
`Light Blue`, `Dark Blue` and `Navy`, because the customer says "أزرق" and does
not know how the upstream dataset spells it.

```bash
python scripts/organize_images.py  # copy + sort photos, write the manifest
pytest tests/ -q                   # 91 tests
```

---

## 🧪 Running Automated Tests

Run the full automated test suite using pytest:

```powershell
pytest -v
```

---

## 💡 Conversational Demo Flow

Try the following multi-turn sequence in the Chat UI to test context awareness:

1. **User**: عاوز منتج مناسب
   - *Assistant recommends products from mock business data.*
2. **User**: ميزانيتي 1000 جنيه
   - *Assistant understands the budget relates to previous product recommendation.*
3. **User**: طب لو عاوز 3 قطع؟
   - *Assistant suggests Bundle Pack (900 EGP) or combination calculations.*
4. **User**: والشحن؟
   - *Assistant clarifies shipping fees and free shipping over 1000 EGP.*
5. **User**: طب طلبي ORD-1001 وصل لفين؟
   - *Assistant looks up order status from mock business data.*

---

## 🔮 Future Extension Points

The codebase is designed with clean separation of concerns, making it easy to replace mock services with production integrations:

- **Mock Data**: Replace app/services/mock_data.py with SQL databases, REST APIs, or ERP systems.
- **Conversation Memory**: Replace ConversationService with Redis or PostgreSQL session stores.
- **Tool Calling & Agents**: Expand GeminiService with function calling to dynamically query live inventory or create real orders.

---

## 🛠️ Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Nothing happens in the UI when clicking Send or a suggestion chip | A JavaScript syntax error in `app/static/app.js` stops the whole script from running | Validate with `node --check app/static/app.js`, fix the error and hard-refresh the page (Ctrl+F5) |
| The assistant always replies with the canned local text | Missing/invalid `GEMINI_API_KEY`, or every candidate model failed | Check the server console output — it prints which model failed and why — and verify the key at <https://aistudio.google.com/apikey> |
| `404 ... is no longer available to new users` | The configured model was retired for new API keys | Point `GEMINI_MODEL` to a current model (e.g. `gemini-3.6-flash`) |
| `503 UNAVAILABLE ... experiencing high demand` | Temporary capacity spike on that model | The service retries once and then automatically tries `GEMINI_FALLBACK_MODELS` |
| Requests take very long / appear to hang | Slow or blocked network path to the API | Tune `GEMINI_TIMEOUT_MS` (default `30000`) and check `/health` |
