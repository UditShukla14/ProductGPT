import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import settings
from app.database import SessionLocal, init_db
from app.ingestion.goodman_ratings import ingest_goodman_ratings
from app.knowledge_graph.neo4j_client import neo4j_client
from app.knowledge_graph.store import graph_store
from app.models.hvac_system import HvacSystem

logger = logging.getLogger(__name__)


def seed_matchup_data_if_needed() -> None:
    """Seed Goodman matchup rows into productgpt.db and rebuild the HVAC graph when needed."""
    db = SessionLocal()
    try:
        seeded = False
        count = db.query(HvacSystem).count()
        if count == 0:
            xlsx_path = settings.default_goodman_ratings_xlsx
            if xlsx_path.exists():
                logger.info("Seeding HVAC matchup data from %s", xlsx_path)
                ingest_goodman_ratings(db, xlsx_path, replace=True)
                seeded = True
            else:
                logger.warning("No seed xlsx at %s — skipping ingest", xlsx_path)

        system_count = db.query(HvacSystem).count()
        if seeded or (system_count > 0 and not graph_store.is_ready):
            logger.info("Rebuilding HVAC knowledge graph (%s systems in DB)", system_count)
            graph_store.connect_neo4j()
            graph_store.rebuild(db)
            logger.info("HVAC knowledge graph ready (backend=%s)", graph_store.backend)
    finally:
        db.close()


def _run_background_startup_tasks() -> None:
    try:
        seed_matchup_data_if_needed()
    except Exception:
        logger.exception("HVAC matchup startup tasks failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Path(settings.default_goodman_ratings_xlsx).parent.mkdir(parents=True, exist_ok=True)
    logger.info("Initializing database")
    init_db()
    threading.Thread(
        target=_run_background_startup_tasks,
        name="hvac-startup",
        daemon=True,
    ).start()
    yield
    neo4j_client.close()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "health": "/api/v1/health",
        "recommendations": "/api/v1/recommendations/hvac",
        "chat": "/api/v1/chat/messages",
        "public_chat": "/api/v1/public/chat/messages",
        "public_product_lookup": "/api/v1/public/products/{product_id}",
        "public_shopify_recommendations": "/api/v1/public/shopify/products/{product_id}",
        "sales_graph": "/api/v1/sales/graph/stats",
    }
