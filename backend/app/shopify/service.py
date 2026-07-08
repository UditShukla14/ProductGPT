"""Orchestrate a full Shopify fetch into SQLite DBs and the knowledge graph."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import settings
from app.shopify.client import ResourceName, ShopifyApiClient
from app.shopify.graph.schemas import ShopifyGraphStats
from app.shopify.graph.store import shopify_graph_store
from app.shopify.storage import SHOPIFY_DATA_DIR, count_records, list_shopify_ids
from app.shopify.sync import ALL_RESOURCES, ResourceSyncResult, enrich_resource_details, sync_resources

logger = logging.getLogger(__name__)


@dataclass
class ResourceEnrichResult:
    resource: ResourceName
    enriched: int
    failed: int
    skipped: int
    total_in_db: int
    resource_ids: list[str]
    status: str
    error: str | None = None


@dataclass
class ProductEnrichResult:
    enriched: int
    failed: int
    skipped: int
    total_in_db: int
    product_ids: list[str]
    status: str
    error: str | None = None


def is_shopify_configured() -> bool:
    return bool(
        settings.shopify_api_base_url
        and settings.shopify_api_token
        and settings.shopify_api_shop_domain
    )


def shopify_data_is_empty() -> bool:
    return all(count_records(resource) == 0 for resource in ALL_RESOURCES)


def build_shopify_client() -> ShopifyApiClient:
    if not is_shopify_configured():
        raise RuntimeError(
            "Shopify API is not configured. Set SHOPIFY_API_BASE_URL, "
            "SHOPIFY_API_TOKEN, and SHOPIFY_API_SHOP_DOMAIN in backend/.env"
        )
    return ShopifyApiClient(
        base_url=settings.shopify_api_base_url,
        token=settings.shopify_api_token,
        shop_domain=settings.shopify_api_shop_domain,
        page_limit=settings.shopify_api_page_limit,
        requests_per_minute=settings.shopify_api_requests_per_minute,
        timeout_seconds=settings.shopify_api_timeout_seconds,
    )


def run_full_shopify_sync(*, rebuild_graph: bool = True) -> list[ResourceSyncResult]:
    """Fetch all products, customers, and orders (every page) and rebuild the Shopify graph."""
    SHOPIFY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(
        "Starting full Shopify sync (resources=%s, page_limit=%s, enrich_details=%s)",
        ", ".join(ALL_RESOURCES),
        settings.shopify_api_page_limit or "server default",
        settings.shopify_enrich_details,
    )

    with build_shopify_client() as client:
        results = sync_resources(client, ALL_RESOURCES, rebuild_graph=rebuild_graph)

    for result in results:
        if result.status == "completed":
            logger.info(
                "Shopify %s sync complete: fetched=%s details=%s total_in_db=%s",
                result.resource,
                result.fetched,
                result.details_fetched,
                result.total_in_db,
            )
        else:
            logger.error("Shopify %s sync failed: %s", result.resource, result.error)

    if rebuild_graph and shopify_graph_store.is_ready:
        stats = shopify_graph_store.get_stats()
        logger.info(
            "Shopify knowledge graph ready (%s): %s nodes, %s edges",
            shopify_graph_store.backend,
            stats.node_count,
            stats.edge_count,
        )

    return results


def run_full_shopify_pipeline(
    *,
    skip_already_enriched: bool = True,
) -> tuple[list[ResourceSyncResult], list[ResourceEnrichResult], ShopifyGraphStats | None]:
    """List-sync all resources, enrich all detail APIs, then rebuild the Shopify graph once."""
    SHOPIFY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(
        "Starting full Shopify pipeline (list sync → enrich all → graph rebuild, page_limit=%s)",
        settings.shopify_api_page_limit or "server default",
    )

    with build_shopify_client() as client:
        sync_results = sync_resources(
            client,
            ALL_RESOURCES,
            enrich_details=False,
            rebuild_graph=False,
        )

    if any(result.status != "completed" for result in sync_results):
        failed = [result.resource for result in sync_results if result.status != "completed"]
        raise RuntimeError(f"Shopify list sync failed for: {', '.join(failed)}")

    enrich_results: list[ResourceEnrichResult] = []
    for resource in ALL_RESOURCES:
        enrich_results.append(
            run_resource_enrichment(
                resource,
                rebuild_graph=False,
                skip_already_enriched=skip_already_enriched,
            )
        )

    stats = shopify_graph_store.rebuild()
    logger.info(
        "Shopify pipeline complete: graph=%s nodes=%s edges=%s",
        shopify_graph_store.backend,
        stats.node_count,
        stats.edge_count,
    )
    return sync_results, enrich_results, stats


def run_resource_enrichment(
    resource: ResourceName,
    *,
    resource_ids: list[str] | None = None,
    rebuild_graph: bool = True,
    skip_already_enriched: bool = True,
) -> ResourceEnrichResult:
    """Fetch GET /{resource}/{id} for stored records (or explicit ids) and upsert detail payloads."""
    SHOPIFY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    ids_to_enrich = resource_ids if resource_ids is not None else list_shopify_ids(resource)
    logger.info(
        "Starting Shopify %s enrichment (count=%s, skip_already_enriched=%s, rebuild_graph=%s)",
        resource,
        len(ids_to_enrich),
        skip_already_enriched,
        rebuild_graph,
    )

    if not ids_to_enrich:
        return ResourceEnrichResult(
            resource=resource,
            enriched=0,
            failed=0,
            skipped=0,
            total_in_db=count_records(resource),
            resource_ids=[],
            status="completed",
        )

    try:
        with build_shopify_client() as client:
            summary = enrich_resource_details(
                client,
                resource,
                resource_ids=ids_to_enrich,
                skip_already_enriched=skip_already_enriched,
            )

        total = count_records(resource)
        if rebuild_graph and summary.enriched > 0:
            shopify_graph_store.rebuild()

        status = "completed" if summary.failed == 0 else "completed_with_errors"
        logger.info(
            "Shopify %s enrichment complete: enriched=%s failed=%s skipped=%s total_in_db=%s",
            resource,
            summary.enriched,
            summary.failed,
            summary.skipped,
            total,
        )
        return ResourceEnrichResult(
            resource=resource,
            enriched=summary.enriched,
            failed=summary.failed,
            skipped=summary.skipped,
            total_in_db=total,
            resource_ids=ids_to_enrich,
            status=status,
            error=(
                f"{summary.failed} detail request(s) failed after retries"
                if summary.failed
                else None
            ),
        )
    except Exception as exc:
        logger.exception("Shopify %s enrichment failed", resource)
        return ResourceEnrichResult(
            resource=resource,
            enriched=0,
            failed=0,
            skipped=0,
            total_in_db=count_records(resource),
            resource_ids=ids_to_enrich,
            status="failed",
            error=str(exc),
        )


def run_product_enrichment(
    *,
    product_ids: list[str] | None = None,
    rebuild_graph: bool = True,
    skip_already_enriched: bool = True,
) -> ProductEnrichResult:
    """Fetch GET /products/{id} for all stored products (or explicit ids) and upsert detail payloads."""
    result = run_resource_enrichment(
        "products",
        resource_ids=product_ids,
        rebuild_graph=rebuild_graph,
        skip_already_enriched=skip_already_enriched,
    )
    return ProductEnrichResult(
        enriched=result.enriched,
        failed=result.failed,
        skipped=result.skipped,
        total_in_db=result.total_in_db,
        product_ids=result.resource_ids,
        status=result.status,
        error=result.error,
    )


def sync_shopify_if_needed() -> ShopifyGraphStats | None:
    """Rebuild the Shopify graph from existing DBs; never run a full API sync unless opted in."""
    if not is_shopify_configured():
        logger.debug("Shopify sync skipped — API credentials not configured")
        return None

    if shopify_data_is_empty():
        if settings.shopify_sync_on_startup:
            logger.info("SHOPIFY_SYNC_ON_STARTUP enabled — running full sync")
            results = run_full_shopify_sync(rebuild_graph=True)
            if any(result.status != "completed" for result in results):
                failed = [result.resource for result in results if result.status != "completed"]
                raise RuntimeError(f"Shopify sync failed for: {', '.join(failed)}")
            return shopify_graph_store.get_stats() if shopify_graph_store.is_ready else None

        logger.info(
            "Shopify DBs empty — skipping auto-sync on startup. "
            "Run: python scripts/sync_shopify.py"
        )
        return None

    if settings.shopify_sync_on_startup:
        logger.info("SHOPIFY_SYNC_ON_STARTUP enabled — running full sync")
        results = run_full_shopify_sync(rebuild_graph=True)
        if any(result.status != "completed" for result in results):
            failed = [result.resource for result in results if result.status != "completed"]
            raise RuntimeError(f"Shopify sync failed for: {', '.join(failed)}")
        return shopify_graph_store.get_stats() if shopify_graph_store.is_ready else None

    logger.info("Shopify data already present — rebuilding graph from SQLite DBs")
    if shopify_graph_store.is_ready:
        return shopify_graph_store.get_stats()
    return shopify_graph_store.rebuild()
