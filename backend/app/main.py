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


def seed_hvac_data_if_needed() -> None:
    db = SessionLocal()
    try:
        count = db.query(HvacSystem).count()
        if count == 0:
            xlsx_path = settings.default_goodman_ratings_xlsx
            if xlsx_path.exists():
                ingest_goodman_ratings(db, xlsx_path, replace=True)
        graph_store.connect_neo4j()
        graph_store.rebuild(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Path(settings.default_goodman_ratings_xlsx).parent.mkdir(parents=True, exist_ok=True)
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
    }
