#!/usr/bin/env python3
"""Fetch GET /{resource}/{id} detail payloads for stored Shopify products, customers, or orders."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings
from app.shopify.client import ResourceName
from app.shopify.graph.store import shopify_graph_store
from app.shopify.service import is_shopify_configured, run_resource_enrichment
from app.shopify.storage import SHOPIFY_DATA_DIR, count_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enrich stored Shopify records via GET /{resource}/{id} detail API"
    )
    parser.add_argument(
        "resource",
        choices=["products", "customers", "orders"],
        help="Shopify resource to enrich",
    )
    parser.add_argument(
        "--id",
        action="append",
        dest="resource_ids",
        metavar="ID",
        help="Specific record id(s) to enrich (default: all stored in the resource DB)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch details even if the record already looks enriched",
    )
    parser.add_argument(
        "--skip-graph",
        action="store_true",
        help="Skip rebuilding the Shopify knowledge graph after enrichment",
    )
    args = parser.parse_args()

    if not is_shopify_configured():
        print("Missing Shopify configuration in backend/.env:", file=sys.stderr)
        print("  SHOPIFY_API_BASE_URL", file=sys.stderr)
        print("  SHOPIFY_API_TOKEN", file=sys.stderr)
        print("  SHOPIFY_API_SHOP_DOMAIN", file=sys.stderr)
        return 1

    resource: ResourceName = args.resource
    SHOPIFY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Shopify API: {settings.shopify_api_base_url}")
    print(f"Shop domain: {settings.shopify_api_shop_domain}")
    print(f"Timeout: {settings.shopify_api_timeout_seconds}s")
    print(f"Output: {SHOPIFY_DATA_DIR / f'{resource}.db'}")
    if args.resource_ids:
        print(f"Enriching {len(args.resource_ids)} specific {resource} record(s)")
    else:
        print(f"Enriching all stored {resource} records ({count_records(resource)} in DB)")
    if not args.force:
        print("Skipping records that already look enriched (use --force to re-fetch)")

    result = run_resource_enrichment(
        resource,
        resource_ids=args.resource_ids,
        rebuild_graph=not args.skip_graph,
        skip_already_enriched=not args.force,
    )

    ok = result.status in {"completed", "completed_with_errors"}
    status = "OK" if result.status == "completed" else ("PARTIAL" if ok else "FAILED")
    print(
        f"[{status}] {result.resource}: enriched={result.enriched} "
        f"failed={result.failed} skipped={result.skipped} total={result.total_in_db}"
    )
    if result.error:
        print(f"  note: {result.error}", file=sys.stderr)
        if not ok:
            return 1

    if not args.skip_graph and shopify_graph_store.is_ready and result.enriched > 0:
        stats = shopify_graph_store.get_stats()
        print(
            f"Shopify graph ({shopify_graph_store.backend}): "
            f"{stats.node_count} nodes, {stats.edge_count} edges "
            f"(products={stats.product_count}, customers={stats.customer_count}, "
            f"orders={stats.order_count})"
        )

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
