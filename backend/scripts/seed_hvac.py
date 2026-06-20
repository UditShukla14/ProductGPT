#!/usr/bin/env python3
"""Seed HVAC data from the Goodman AHRI ratings Excel file."""

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings
from app.database import SessionLocal, init_db
from app.ingestion.goodman_ratings import ingest_goodman_ratings
from app.knowledge_graph.neo4j_client import neo4j_client
from app.knowledge_graph.store import graph_store


def main() -> None:
    xlsx_path = settings.default_goodman_ratings_xlsx
    if not xlsx_path.exists():
        raise SystemExit(f"Excel file not found: {xlsx_path}")

    init_db()
    db = SessionLocal()
    try:
        source = ingest_goodman_ratings(db, xlsx_path, replace=True)
        graph_store.connect_neo4j()
        stats = graph_store.rebuild(db)
        print(f"Loaded {source.row_count:,} HVAC systems from {xlsx_path.name}")
        print(
            f"Knowledge graph ({graph_store.backend}): "
            f"{stats.node_count:,} nodes, {stats.edge_count:,} edges"
        )
    finally:
        db.close()
        neo4j_client.close()


if __name__ == "__main__":
    main()
