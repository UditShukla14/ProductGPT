#!/usr/bin/env python3
"""Rebuild sales :SalesNode graph from SQLite sales_line_items."""

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal, init_db
from app.knowledge_graph.neo4j_client import neo4j_client
from app.sales.graph.store import sales_graph_store


def main() -> None:
    init_db()
    if not sales_graph_store.connect_neo4j():
        raise SystemExit("Could not connect to Neo4j. Start it with: npm run neo4j")

    db = SessionLocal()
    try:
        stats = sales_graph_store.rebuild(db)
        print(f"Sales Neo4j sync complete: {stats.node_count:,} nodes, {stats.edge_count:,} edges")
        print(f"SKUs: {stats.sku_count:,}")
        print(f"Regions: {stats.region_count:,}")
        print(f"Vendors: {stats.vendor_count:,}")
        print(f"Line items: {stats.line_item_count:,}")
    finally:
        db.close()
        neo4j_client.close()


if __name__ == "__main__":
    main()
