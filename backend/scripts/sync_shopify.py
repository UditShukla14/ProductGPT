#!/usr/bin/env python3
"""Fetch all Shopify products, customers, and orders into SQLite DBs and rebuild the knowledge graph."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings
from app.shopify import ALL_RESOURCES, run_full_shopify_sync
from app.shopify.graph.store import shopify_graph_store
from app.shopify.service import is_shopify_configured
from app.shopify.storage import SHOPIFY_DATA_DIR, count_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync all Shopify list APIs (products, customers, orders) into separate SQLite DBs"
    )
    parser.add_argument(
        "--skip-graph",
        action="store_true",
        help="Skip rebuilding the Shopify knowledge graph after sync",
    )
    args = parser.parse_args()

    if not is_shopify_configured():
        print("Missing Shopify configuration in backend/.env:", file=sys.stderr)
        print("  SHOPIFY_API_BASE_URL", file=sys.stderr)
        print("  SHOPIFY_API_TOKEN", file=sys.stderr)
        print("  SHOPIFY_API_SHOP_DOMAIN", file=sys.stderr)
        return 1

    SHOPIFY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Shopify API: {settings.shopify_api_base_url}")
    print(f"Shop domain: {settings.shopify_api_shop_domain}")
    print(f"Output: {SHOPIFY_DATA_DIR}")
    print(f"Resources: {', '.join(ALL_RESOURCES)} (all pages)")

    results = run_full_shopify_sync(rebuild_graph=not args.skip_graph)

    failed = False
    for result in results:
        status = "OK" if result.status == "completed" else "FAILED"
        print(
            f"[{status}] {result.resource}: fetched={result.fetched} "
            f"details={result.details_fetched} upserted={result.upserted} "
            f"total={result.total_in_db}"
        )
        if result.error:
            print(f"  error: {result.error}", file=sys.stderr)
            failed = True

    if not args.skip_graph and shopify_graph_store.is_ready:
        stats = shopify_graph_store.get_stats()
        print(
            f"Shopify graph ({shopify_graph_store.backend}): "
            f"{stats.node_count} nodes, {stats.edge_count} edges "
            f"(products={stats.product_count}, customers={stats.customer_count}, "
            f"orders={stats.order_count})"
        )

    print("Database counts:")
    for resource in ALL_RESOURCES:
        print(f"  {resource}.db: {count_records(resource)} records")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
