from pathlib import Path

from sqlalchemy.orm import Session

from app.ingestion.goodman_ratings import SOURCE_TYPE, ingest_goodman_ratings
from app.knowledge_graph.store import graph_store

HANDLERS = {
    SOURCE_TYPE: ingest_goodman_ratings,
}


def ingest_file(db: Session, file_path: Path, source_type: str, replace: bool = True):
    handler = HANDLERS.get(source_type)
    if handler is None:
        raise ValueError(f"Unsupported source type: {source_type}")
    source = handler(db, file_path, replace=replace)
    graph_store.rebuild(db)
    return source
