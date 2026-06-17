from pathlib import Path

from sqlalchemy.orm import Session

from app.ingestion.hvac_system_finder import SOURCE_TYPE, ingest_hvac_csv

HANDLERS = {
    SOURCE_TYPE: ingest_hvac_csv,
}


def ingest_file(db: Session, file_path: Path, source_type: str, replace: bool = True):
    handler = HANDLERS.get(source_type)
    if handler is None:
        raise ValueError(f"Unsupported source type: {source_type}")
    return handler(db, file_path, replace=replace)
