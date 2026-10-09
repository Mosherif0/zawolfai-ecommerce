# Zawolf AI — Intelligent E-Commerce Engine

A modular e-commerce AI system with recommendation, OCR, chatbot, and demand-forecasting services.

## Repository layout

```text
zawolfai-ecommerce/
├── index.html / app.js / style.css / config.js  # static frontend
├── recommendation_system/                       # recommendations API
├── ocr/                                         # OCR and warehouse API
├── conversational-ai-mvp/                       # chatbot API
├── demand_forecasting/                          # forecasting API
├── data/ and images/                             # shared assets
└── run_all.py                                   # backend launcher/checker
```

## Requirements

- Python 3.11 or newer
- No Node.js, Vite, or bundler is needed: the frontend is plain HTML/CSS/JavaScript.

Install the backend dependencies. Each service has its own requirements file:

```bat
python -m pip install -r recommendation_system/zawolfai-ecommerce-Re/requirements.txt
python -m pip install -r ocr/requirements.txt
python -m pip install -r conversational-ai-mvp/requirements.txt
python -m pip install -r demand_forecasting/requirements.txt
```

> The chatbot can also run in its own virtual environment; the other three
> services run from the same interpreter.

## Local setup

1. Go to the repository root (adjust the path to wherever you cloned it):

   ```bat
   cd /d path\to\zawolfai-ecommerce
   ```

2. Create a local environment file. Do not commit it:

   ```bat
   copy .env.example .env
   ```

   Add local-only API keys or database credentials to `.env` when needed.

3. Check paths and configuration:

   ```bat
   python run_all.py --check
   ```

## Run the backend

Start all backend services from the repository root:

```bat
python run_all.py
```

The services use separate ports:

| Service | URL |
|---|---|
| Recommendations | http://127.0.0.1:8100 |
| OCR | http://127.0.0.1:8200 |
| Chatbot | http://127.0.0.1:8300 |
| Forecasting | http://127.0.0.1:8400 |

Each service exposes `/health`; FastAPI docs are available at `/docs`.

## Run the frontend

The frontend is plain HTML/CSS/JavaScript, so Vite is not required. Run the static server on the requested port:

```bat
python -m http.server 5173
```

Or double-click `run_static.bat`.

Open the application at:

```text
http://127.0.0.1:5173/
```

The frontend API configuration is in `config.js`. It points to the four backend ports above. The frontend and backend therefore use different ports intentionally; they cannot all bind to `5173` at the same time.

## Git and secrets

- `.env`, `outputs/`, `.work/`, caches, and generated local files are ignored.
- Never commit API keys, database passwords, or private credentials.
- Review changes before publishing:

  ```bat
  git status
  git diff
  git add .
  git commit -m "Prepare local frontend and backend setup"
  git push origin main
  ```
