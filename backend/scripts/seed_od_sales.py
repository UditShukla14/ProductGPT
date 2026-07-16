#!/usr/bin/env python3
"""Ingest OD Sales Excel into SQLite and rebuild the sales Neo4j graph."""

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings
from app.database import SessionLocal, init_db
from app.ingestion.od_sales import ingest_od_sales
from app.knowledge_graph.neo4j_client import neo4j_client
from app.sales.graph.store import sales_graph_store


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed OD Sales data and rebuild :SalesNode graph")
    parser.add_argument(
        "--file",
        type=Path,
        default=settings.default_od_sales_xlsx,
        help="Path to OD Sales Excel file",
    )
    parser.add_argument(
        "--skip-graph",
        action="store_true",
        help="Only ingest SQLite rows; skip Neo4j/NetworkX rebuild",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append rows instead of replacing existing sales_line_items",
    )
    args = parser.parse_args()

    if not args.file.exists():
        raise SystemExit(f"Sales file not found: {args.file}")

    init_db()
    db = SessionLocal()
    try:
        source = ingest_od_sales(db, args.file, replace=not args.append)
        print(f"Ingested {source.row_count:,} sales rows from {source.filename}")

        if args.skip_graph:
            return

        sales_graph_store.connect_neo4j()
        stats = sales_graph_store.rebuild(db)
        print(
            f"Sales graph ({sales_graph_store.backend}): "
            f"{stats.node_count:,} nodes, {stats.edge_count:,} edges, "
            f"{stats.sku_count:,} SKUs, {stats.region_count:,} regions"
        )
    finally:
        db.close()
        neo4j_client.close()


if __name__ == "__main__":
    main()
