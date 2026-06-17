# ProductGPT

AI-powered product recommendation system. **Phase 1** uses the HVAC system finder CSV as the knowledge base; Shopify and ProjectWorxStream integrations will be added later.

## Quick start

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/seed_hvac.py
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the app: http://127.0.0.1:5173  
API docs: http://127.0.0.1:8000/docs

The Vite dev server proxies `/api` to the backend on port 8000. Run both backend and frontend together.

On first startup, the API auto-seeds from `data/hvac_system_finder.csv` if the database is empty.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Service health + row counts |
| POST | `/api/v1/hvac/systems/search` | Structured HVAC search |
| GET | `/api/v1/hvac/systems/{ahri_number}` | Single AHRI-certified system |
| POST | `/api/v1/recommendations/hvac` | Ranked HVAC recommendations |
| POST | `/api/v1/ingest/upload` | Upload CSV (`source_type=hvac_system_finder`) |

## Example: get recommendations

```bash
curl -X POST http://127.0.0.1:8000/api/v1/recommendations/hvac \
  -H "Content-Type: application/json" \
  -d '{
    "tonnage": 2.0,
    "min_seer": 15,
    "config": "Horizontal Flow",
    "system_type_seer2": "Split System (SEER2) - Gas Heating 15.3 SEER",
    "limit": 5
  }'
```

## Example: structured search

```bash
curl -X POST http://127.0.0.1:8000/api/v1/hvac/systems/search \
  -H "Content-Type: application/json" \
  -d '{
    "tonnage": 1.5,
    "stage": "TWO STAGE",
    "query": "modulating",
    "limit": 10
  }'
```

## Project layout

```
ProductGPT/
├── LESSONS.md              # Read before any code change
├── data/
│   └── hvac_system_finder.csv
└── backend/
    ├── app/
    │   ├── api/v1/         # REST routes
    │   ├── ingestion/      # CSV ingest + schema registry
    │   ├── models/         # SQLAlchemy models
    │   ├── schemas/        # Pydantic request/response
    │   └── services/       # Search + recommendation logic
    └── scripts/seed_hvac.py
└── frontend/               # React + Vite + shadcn UI
    └── src/
        ├── components/     # AppHeader, SystemCard, ui/*
        ├── lib/api.ts        # API client
        └── types/api.ts      # TypeScript types
```

## Request flow

```
Client → main.py → api/v1/*.py → services/*.py → models (DB)
                              ↘ ingestion/*.py (on upload/seed)
```

## File reference

### Root level

| File | Purpose |
|------|---------|
| `LESSONS.md` | Living doc of architecture decisions, gotchas, and conventions. Read before changing code. |
| `README.md` | Setup instructions, API examples, and project overview. |
| `.gitignore` | Ignores `.venv`, `__pycache__`, SQLite DB, `node_modules`, etc. |
| `data/hvac_system_finder.csv` | Source knowledge base — AHRI-certified HVAC system combinations (~1,011 rows). |
| `data/productgpt.db` | Generated SQLite database (created on first run/seed). Not committed. |

### Backend config & entry

| File | Purpose |
|------|---------|
| `backend/requirements.txt` | Python dependencies: FastAPI, SQLAlchemy, Pydantic, pandas, etc. |
| `backend/app/main.py` | **App entry point.** Creates the FastAPI app, CORS, startup lifecycle (init DB + auto-seed CSV if empty). Run via `uvicorn app.main:app`. |
| `backend/app/config.py` | **Settings** — DB path, default CSV location, CORS origins. Loaded from env / `.env`. |
| `backend/app/database.py` | **DB wiring** — SQLAlchemy engine, session factory, `get_db()` dependency for routes, `init_db()` to create tables. |
| `backend/app/__init__.py` | Marks `app` as a Python package. |

### Models (database tables)

| File | Purpose |
|------|---------|
| `backend/app/models/knowledge_source.py` | Table `knowledge_sources` — tracks each ingested file (type, filename, row count, status). |
| `backend/app/models/hvac_system.py` | Table `hvac_systems` — one row per AHRI-certified system (tonnage, SEER, models, config, etc.). Unique key: `(source_id, source_row_id)`. |
| `backend/app/models/__init__.py` | Exports model classes for imports elsewhere. |

### Schemas (API request/response shapes)

| File | Purpose |
|------|---------|
| `backend/app/schemas/hvac.py` | Pydantic models for HVAC search: `HvacSearchRequest`, `HvacSystemOut`, `HvacComponent`, `HvacSearchResponse`. Validates API input/output. |
| `backend/app/schemas/recommendations.py` | Pydantic models for recommendations: `HvacRecommendationRequest`, `HvacRecommendation`, `HvacRecommendationResponse`. |
| `backend/app/schemas/common.py` | Shared schemas: `HealthResponse`, `IngestUploadResponse`. |

Schemas define the **API contract**; they are separate from DB models so the API can evolve independently.

### Ingestion (CSV → database)

| File | Purpose |
|------|---------|
| `backend/app/ingestion/hvac_system_finder.py` | **HVAC CSV parser.** Reads CSV with pandas, normalizes fields (`outdoor_model_revision` when `outdoor_model` is NULL), dedupes duplicate AHRI rows, builds `search_text`, writes to `hvac_systems`. |
| `backend/app/ingestion/registry.py` | **Plugin registry** for file types. Maps `hvac_system_finder` → ingest handler. Future: `shopify`, `product_catalog`, etc. |

### Services (business logic)

| File | Purpose |
|------|---------|
| `backend/app/services/hvac_search.py` | **Structured search.** Applies SQL filters (tonnage, SEER, config, free-text), paginates, converts DB rows → `HvacSystemOut` with component bundles. |
| `backend/app/services/recommender.py` | **Recommendation engine.** Filters candidates → scores by constraint match + SEER preference → dedupes by AHRI → returns top N with reasons. |

API routes stay thin; logic lives here.

### API routes (HTTP layer)

| File | Purpose |
|------|---------|
| `backend/app/api/v1/router.py` | Combines all v1 routers under `/api/v1`. |
| `backend/app/api/v1/health.py` | `GET /api/v1/health` — service status + row counts. |
| `backend/app/api/v1/hvac.py` | `POST /api/v1/hvac/systems/search` — structured search. `GET /api/v1/hvac/systems/{ahri_number}` — single system. |
| `backend/app/api/v1/recommendations.py` | `POST /api/v1/recommendations/hvac` — ranked recommendations. |
| `backend/app/api/v1/ingest.py` | `POST /api/v1/ingest/upload` — multipart CSV upload, routes through registry. |

### Scripts & tests

| File | Purpose |
|------|---------|
| `backend/scripts/seed_hvac.py` | CLI to manually load/reload the CSV into the DB. Run: `python scripts/seed_hvac.py`. |
| `backend/tests/test_recommendations.py` | Integration test: seed CSV → search → recommend. Run: `python tests/test_recommendations.py`. |

### Layer responsibilities

| Layer | Files | Responsibility |
|-------|-------|----------------|
| Entry | `main.py`, `config.py` | Boot app, settings, lifecycle |
| Persistence | `database.py`, `models/*` | DB connection & table definitions |
| Contract | `schemas/*` | Request/response validation |
| Ingestion | `ingestion/*` | External data → DB |
| Logic | `services/*` | Search, scoring, recommendations |
| HTTP | `api/v1/*` | REST endpoints, thin handlers |

### Example: recommendation request path

`POST /api/v1/recommendations/hvac` with `{ "tonnage": 2.0, "min_seer": 15 }`:

1. `recommendations.py` — receives request, validates with `HvacRecommendationRequest`
2. `recommender.py` — builds filters, queries `hvac_systems`, scores & ranks
3. `hvac_search.py` — shared filter logic + `system_to_schema()` for output
4. `hvac_system.py` — ORM model read from SQLite
5. Response serialized as `HvacRecommendationResponse`

### Example: startup path

1. `main.py` → `init_db()` creates tables
2. `main.py` → `seed_hvac_data_if_needed()` if DB empty
3. `hvac_system_finder.py` → loads `data/hvac_system_finder.csv`

## How recommendations work (v1)

1. **Filter** active HVAC systems by structured constraints (tonnage, SEER, config, etc.)
2. **Score** candidates by constraint match + SEER preference
3. **Dedupe** by AHRI number so certified bundles are not repeated
4. **Return** top N with human-readable reasons and component models (outdoor, coil, furnace)

Future phases will add Shopify inventory/pricing via `product_model_xref` and ProjectWorxStream purchase history.



Factor	Points
Tonnage match
+30
Meets min SEER
+20
Config match
+15
System type match
+15
Stage match
+10
Indoor unit match
+5
Furnace BTU match
+5
Query text match
up to +15
Prefer higher SEER (when ON)
+SEER value (max 20)