#!/usr/bin/env python3
"""Sync HVAC data from SQLite into Neo4j."""

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal, init_db
from app.knowledge_graph.neo4j_client import neo4j_client
from app.knowledge_graph.neo4j_store import neo4j_graph_store
from app.knowledge_graph.store import graph_store


def main() -> None:
    init_db()
    if not graph_store.connect_neo4j():
        raise SystemExit("Could not connect to Neo4j. Start it with: docker compose up -d neo4j")

    db = SessionLocal()
    try:
        stats = neo4j_graph_store.rebuild(db)
        print(f"Neo4j sync complete: {stats.node_count:,} nodes, {stats.edge_count:,} edges")
        print(f"Certifications: {stats.certification_count:,}")
        print(f"Components: {stats.component_count:,}")
    finally:
        db.close()
        neo4j_client.close()


if __name__ == "__main__":
    main()
