from pathlib import Path

from sqlalchemy.orm import Session

from app.ingestion.goodman_ratings import SOURCE_TYPE as GOODMAN_SOURCE_TYPE, ingest_goodman_ratings
from app.ingestion.r32_engineering import SOURCE_TYPE as R32_ENGINEERING_SOURCE_TYPE, ingest_r32_engineering
from app.ingestion.shopify_products import SOURCE_TYPE as SHOPIFY_SOURCE_TYPE, ingest_shopify_products
from app.knowledge_graph.store import graph_store

HANDLERS = {
    GOODMAN_SOURCE_TYPE: ingest_goodman_ratings,
    SHOPIFY_SOURCE_TYPE: ingest_shopify_products,
    R32_ENGINEERING_SOURCE_TYPE: ingest_r32_engineering,
}


def ingest_file(db: Session, file_path: Path, source_type: str, replace: bool = True):
    handler = HANDLERS.get(source_type)
    if handler is None:
        raise ValueError(f"Unsupported source type: {source_type}")
    source = handler(db, file_path, replace=replace)
    graph_store.rebuild(db)
    return source
