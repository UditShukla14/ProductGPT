from pathlib import Path

from sqlalchemy.orm import Session

from app.ingestion.goodman_ratings import SOURCE_TYPE as GOODMAN_SOURCE_TYPE, ingest_goodman_ratings
from app.ingestion.od_sales import SOURCE_TYPE as OD_SALES_SOURCE_TYPE, ingest_od_sales
from app.ingestion.r32_engineering import SOURCE_TYPE as R32_ENGINEERING_SOURCE_TYPE, ingest_r32_engineering
from app.knowledge_graph.store import graph_store
from app.sales.graph.store import sales_graph_store

HANDLERS = {
    GOODMAN_SOURCE_TYPE: ingest_goodman_ratings,
    R32_ENGINEERING_SOURCE_TYPE: ingest_r32_engineering,
    OD_SALES_SOURCE_TYPE: ingest_od_sales,
}


def ingest_file(db: Session, file_path: Path, source_type: str, replace: bool = True):
    handler = HANDLERS.get(source_type)
    if handler is None:
        raise ValueError(f"Unsupported source type: {source_type}")
    source = handler(db, file_path, replace=replace)
    if source_type == OD_SALES_SOURCE_TYPE:
        sales_graph_store.connect_neo4j()
        sales_graph_store.rebuild(db)
    else:
        graph_store.rebuild(db)
    return source
