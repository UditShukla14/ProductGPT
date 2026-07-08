#!/usr/bin/env python3
"""Full Shopify pipeline: list sync → enrich all resources → rebuild knowledge graph."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings
from app.shopify import ALL_RESOURCES
from app.shopify.service import is_shopify_configured, run_full_shopify_pipeline
from app.shopify.storage import SHOPIFY_DATA_DIR, count_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Sync all Shopify list pages (products, customers, orders), "
            "enrich every record via GET /{resource}/{id}, then rebuild the graph"
        )
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch details even if records already look enriched",
    )
    args = parser.parse_args()

    if not is_shopify_configured():
        print("Missing Shopify configuration:", file=sys.stderr)
        print("  SHOPIFY_API_BASE_URL", file=sys.stderr)
        print("  SHOPIFY_API_TOKEN", file=sys.stderr)
        print("  SHOPIFY_API_SHOP_DOMAIN", file=sys.stderr)
        return 1

    SHOPIFY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Shopify API: {settings.shopify_api_base_url}")
    print(f"Shop domain: {settings.shopify_api_shop_domain}")
    print(f"Page limit: {settings.shopify_api_page_limit or 'omitted (API default 20)'}")
    print(f"Output: {SHOPIFY_DATA_DIR}")
    print(f"Pipeline: list sync → enrich ({', '.join(ALL_RESOURCES)}) → graph rebuild")
    if args.force:
        print("Force mode: re-fetching all detail records")

    try:
        sync_results, enrich_results, stats = run_full_shopify_pipeline(
            skip_already_enriched=not args.force,
        )
    except Exception as exc:
        print(f"Pipeline failed: {exc}", file=sys.stderr)
        return 1

    print("\n=== List sync ===")
    for result in sync_results:
        print(
            f"[OK] {result.resource}: fetched={result.fetched} "
            f"upserted={result.upserted} total={result.total_in_db}"
        )

    print("\n=== Detail enrichment ===")
    failed = False
    for result in enrich_results:
        status = "OK" if result.status == "completed" else "PARTIAL"
        if result.status == "failed":
            status = "FAILED"
            failed = True
        print(
            f"[{status}] {result.resource}: enriched={result.enriched} "
            f"failed={result.failed} skipped={result.skipped} total={result.total_in_db}"
        )
        if result.error:
            print(f"  note: {result.error}", file=sys.stderr)

    if stats is not None:
        print(
            f"\n=== Graph ===\n"
            f"nodes={stats.node_count} edges={stats.edge_count} "
            f"(products={stats.product_count}, customers={stats.customer_count}, "
            f"orders={stats.order_count})"
        )

    print("\nDatabase counts:")
    for resource in ALL_RESOURCES:
        print(f"  {resource}.db: {count_records(resource)} records")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
