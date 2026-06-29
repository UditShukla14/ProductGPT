import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import settings
from app.database import SessionLocal, init_db
from app.ingestion.goodman_ratings import ingest_goodman_ratings
from app.ingestion.r32_engineering import ingest_r32_engineering
from app.ingestion.shopify_products import ingest_shopify_products
from app.knowledge_graph.neo4j_client import neo4j_client
from app.knowledge_graph.store import graph_store
from app.models.engineering_product import EngineeringProduct
from app.models.hvac_system import HvacSystem
from app.models.shopify_product import ShopifyProduct

logger = logging.getLogger(__name__)


def seed_hvac_data_if_needed() -> None:
    db = SessionLocal()
    try:
        count = db.query(HvacSystem).count()
        if count == 0:
            xlsx_path = settings.default_goodman_ratings_xlsx
            if xlsx_path.exists():
                logger.info("Seeding HVAC data from %s", xlsx_path)
                ingest_goodman_ratings(db, xlsx_path, replace=True)
            else:
                logger.warning("No seed xlsx at %s — skipping ingest", xlsx_path)

        shopify_count = db.query(ShopifyProduct).count()
        shopify_csv = settings.default_shopify_products_csv
        if shopify_count == 0 and shopify_csv.exists():
            logger.info("Seeding Shopify product images from %s", shopify_csv)
            ingest_shopify_products(db, shopify_csv, replace=True)

        engineering_count = db.query(EngineeringProduct).count()
        engineering_xlsx = settings.default_r32_engineering_xlsx
        if engineering_count == 0 and engineering_xlsx.exists():
            logger.info("Seeding R-32 engineering accessories from %s", engineering_xlsx)
            ingest_r32_engineering(db, engineering_xlsx, replace=True)

        logger.info("Rebuilding knowledge graph (%s systems in DB)", db.query(HvacSystem).count())
        graph_store.connect_neo4j()
        graph_store.rebuild(db)
        logger.info("Knowledge graph ready (backend=%s)", graph_store.backend)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Path(settings.default_goodman_ratings_xlsx).parent.mkdir(parents=True, exist_ok=True)
    logger.info("Initializing database")
    init_db()
    seed_hvac_data_if_needed()
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
        "public_product_lookup": "/api/v1/public/products/{product_id}",
    }
