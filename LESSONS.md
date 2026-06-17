# Lessons

Living document for ProductGPT — architectural decisions, conventions, and gotchas. **Read this before any code change.**

## Architecture

- **Phase 1 implemented (CSV-only recs)**: FastAPI + SQLAlchemy + SQLite (`data/productgpt.db`) for local dev. HVAC `hvac_system_finder` CSV is ingested into `hvac_systems` table; recommendations use constraint filtering + scoring. Postgres/Redis/Celery come in later phases.
- **REST over gRPC (v1)**: Browser and external integrations (Shopify, ProjectWorxStream) are HTTP-native. LLM and retrieval dominate latency, not transport. Use REST + SSE for chat streaming; revisit gRPC only for high-QPS internal service-to-service calls later.
- **Stack**: Python **FastAPI** backend, **React** frontend, **PostgreSQL** (structured data), **pgvector** or dedicated vector DB for embeddings, **Redis** for cache, **Celery** (or similar) for async ingest/sync jobs.
- **Canonical data model first**: Normalize all sources (Shopify, ProjectWorxStream, manual uploads) into shared entities (`Product`, `Customer`, `Estimate`, `Invoice`, `Document`) with `source`, `source_id`, and `updated_at` before indexing or recommending.
- **Two retrieval paths**: (1) **Structured** — SQL filters, business rules, purchase history for recommendations; (2) **Semantic** — vector search for natural-language chat (RAG). Do not conflate them.
- **Phased rollout**: (1) **Done** — HVAC CSV ingest + structured recommendations API; (2) CSV upload endpoint + RAG chat; (3) Shopify sync + model→SKU crosswalk; (4) ProjectWorxStream + customer-scoped recs; (5) Webhooks, hybrid recs, eval/monitoring.

## API

- **Base path**: `/api/v1`. Auth via `Authorization: Bearer <jwt>`. Standard error shape: `{ "error": { "code", "message" } }`.
- **Chat streaming**: SSE (`text/event-stream`) on `POST /api/v1/chat/sessions/{id}/messages` — events: `token`, `retrieval`, `recommendation`, `done`.
- **Recommendations**: `POST /api/v1/recommendations` with hybrid strategy (history + similarity + rules). Domain-specific routes OK (e.g. `POST /api/v1/recommendations/hvac`).
- **Ingestion**: Multipart upload + async jobs (`POST /api/v1/ingest/upload`, `GET /api/v1/ingest/jobs/{id}`). Shopify webhooks at `POST /api/v1/webhooks/shopify`.
- **Latency wins**: SSE streaming, Redis cache, precomputed embeddings at ingest, small retrieval top-k (5–10), parallel async fetches — not protocol choice.

## Knowledge Base

- **Two-layer KB**: **Structured tables** (Postgres) for rule/compatibility data; **vector index** for NL chat. For domain matrix files (e.g. HVAC AHRI certs), structured query is **primary**; embeddings are **secondary** for fuzzy language.
- **Schema registry**: Register CSV/file types (`hvac_system_finder`, `product_catalog`, `pricing`, `generic`) so ingest uses the correct handler — do not treat all uploads as generic documents.
- **HVAC / compatibility files**: Store in typed tables (e.g. `hvac_systems` keyed by `ahri_number`). Filter on `tonnage`, `seer`, `config`, `system_type_seer2`, `model_status`, model fields. Recommend **certified system bundles**, not isolated components.
- **HVAC CSV gotcha**: `outdoor_model` is often NULL; use `outdoor_model_revision` as the outdoor model. Always filter `model_status = 'Active'`. Normalize model numbers (trim whitespace) on ingest.
- **HVAC component search**: `POST /api/v1/hvac/components/search` — partial model match on outdoor/coil/furnace fields; returns certified **similar matchups** (full systems) and **bought together** (aggregated compatible parts excluding the searched component type).
- **Duplicate AHRI rows in CSV**: `hvac_system_finder.csv` has duplicate `ahri_number` values (~97 rows). Ingest keeps **all CSV rows** (unique key is `source_row_id`). Recommendations no longer dedupe by AHRI — increase `limit` to see more matches.
- **Embeddings per row**: Build a canonical text summary per structured row for chat RAG, with metadata (`entity_type`, `ahri_number`, `tonnage`, `source_type`) for filtered vector search.
- **Model → SKU crosswalk**: AHRI/model numbers (e.g. `GSXN402410`) must map to Shopify/canonical `product_id` via `product_model_xref` — compatibility KB alone is not sellable inventory.

## Data Sources

- **Shopify**: Webhooks (products, inventory, orders) + scheduled full sync. Map to canonical `Product`, optionally `Customer`/`Order`.
- **ProjectWorxStream**: Pull estimates, invoices, customers on schedule. Line items link to products by SKU or fuzzy match. Store raw API payloads in JSONB for audit.
- **Manual CSV/Excel**: Validate → staging → merge into canonical or typed domain tables → chunk/embed → index. Version uploads; support replace vs append.

## Recommendations

- **v1 strategy (`constraint_scoring`)**: Filter active systems → score by matched constraints + optional SEER boost → dedupe by AHRI → return top N with reasons. No LLM rerank yet.
- **Hybrid engine (future)**: Collaborative (customer invoice/estimate history) + content-based (embeddings) + business rules (in stock, margin, exclude discontinued) + optional LLM rerank of top-N.
- **Constraint-first for domain data**: Parse user intent into structured slots (tonnage, SEER min, config) before vector search. LLM helps map NL → slots; SQL/rules produce authoritative matches.
- **Output must cite sources**: SKU, AHRI number, invoice #, and data source. Never let LLM invent prices or SKUs without retrieval backing.

## Chat / RAG

- **Flow**: User message → intent/slots → parallel structured + vector retrieval → context window with citations only → stream LLM response.
- **Guardrails**: Low retrieval score → say insufficient data; scope customer PII by auth; require citations in responses.

## Frontend

- **React + Vite + TypeScript** in `frontend/`. shadcn-style UI components in `src/components/ui/`.
- **TanStack Query** for health check + recommendation mutations.
- **Vite proxy** forwards `/api` → `http://127.0.0.1:8000` in dev (`vite.config.ts`).
- **Main UI**: filter form (tonnage, SEER, config, etc.) + ranked `SystemCard` results with click-to-open detail modal; product search by outdoor/coil/furnace model with similar matchups + bought-together sections.

## Repo Layout (target)

```
productgpt/
├── LESSONS.md
├── data/hvac_system_finder.csv
├── backend/
│   ├── app/api/v1/       # health, hvac, recommendations, ingest
│   ├── services/         # hvac_search, recommender
│   ├── ingestion/        # hvac_system_finder (+ shopify, projectworxstream later)
│   └── scripts/seed_hvac.py
└── frontend/             # React + Vite + shadcn (recommendation UI)
```

## Gotchas

- **Do not embed-only HVAC finder data**: Queries like "2 ton horizontal flow SEER2 ≥ 15" need SQL filters, not similarity search alone.
- **Do not skip crosswalk**: Compatibility rows reference manufacturer model numbers, not Shopify SKUs.
- **Re-index on embedding model change**: Track `embedding_version` on records and batch re-index when chunking or model changes.
- **Read LESSONS.md first**: Before any implementation or refactor, scan this file for decisions that already apply.
