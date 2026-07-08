"""Sync Shopify API resources into separate SQLite databases."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import settings
from app.shopify.client import ResourceName, ShopifyApiClient
from app.shopify.graph.store import shopify_graph_store
from app.shopify.storage import (
    ShopifySyncRun,
    count_records,
    get_shopify_session,
    list_shopify_ids,
    load_record_by_id,
    upsert_records,
)

logger = logging.getLogger(__name__)

ALL_RESOURCES: tuple[ResourceName, ...] = ("products", "customers", "orders")
BATCH_SIZE = 100


@dataclass
class ResourceSyncResult:
    resource: ResourceName
    fetched: int
    upserted: int
    total_in_db: int
    status: str
    details_fetched: int = 0
    error: str | None = None


@dataclass
class EnrichSummary:
    enriched: int = 0
    failed: int = 0
    skipped: int = 0


def _detail_resources_to_enrich(enrich_details: bool | None) -> set[ResourceName]:
    if enrich_details is False or not settings.shopify_enrich_details:
        return set()
    allowed = {name for name in settings.shopify_enrich_detail_resources if name in ALL_RESOURCES}
    return allowed  # type: ignore[return-value]


def _looks_enriched(resource: ResourceName, payload: dict) -> bool:
    """Heuristic: list rows are thin; detail rows carry resource-specific fuller fields."""
    if resource == "products":
        return bool(payload.get("description") or payload.get("options"))
    if resource == "customers":
        return "verified_email" in payload or isinstance(payload.get("addresses"), list)
    if resource == "orders":
        return (
            isinstance(payload.get("fulfillments"), list)
            or isinstance(payload.get("transactions"), list)
            or "subtotal_price" in payload
        )
    return False


def enrich_resource_details(
    client: ShopifyApiClient,
    resource: ResourceName,
    *,
    resource_ids: list[str] | None = None,
    skip_already_enriched: bool = False,
) -> EnrichSummary:
    """Fetch GET /{resource}/{id} for stored records (or explicit ids) and upsert full detail payloads.

    Continues past per-record failures so a timeout mid-run does not discard progress.
    """
    shopify_ids = resource_ids if resource_ids is not None else list_shopify_ids(resource)
    summary = EnrichSummary()
    if not shopify_ids:
        return summary

    logger.info(
        "Enriching %s: fetching detail for %s records (skip_already_enriched=%s)",
        resource,
        len(shopify_ids),
        skip_already_enriched,
    )
    batch: list[dict] = []

    for index, shopify_id in enumerate(shopify_ids, start=1):
        if skip_already_enriched:
            existing = load_record_by_id(resource, shopify_id)
            if existing is not None and _looks_enriched(resource, existing):
                summary.skipped += 1
                if index % 50 == 0 or index == len(shopify_ids):
                    logger.info(
                        "Enriching %s: %s/%s (enriched=%s failed=%s skipped=%s)",
                        resource,
                        index,
                        len(shopify_ids),
                        summary.enriched,
                        summary.failed,
                        summary.skipped,
                    )
                continue

        try:
            detail = client.fetch_detail(resource, shopify_id)
        except Exception as exc:
            summary.failed += 1
            logger.warning(
                "Failed enriching %s/%s: %s — continuing",
                resource,
                shopify_id,
                exc,
            )
            if index % 50 == 0 or index == len(shopify_ids):
                logger.info(
                    "Enriching %s: %s/%s (enriched=%s failed=%s skipped=%s)",
                    resource,
                    index,
                    len(shopify_ids),
                    summary.enriched,
                    summary.failed,
                    summary.skipped,
                )
            continue

        batch.append(detail)
        summary.enriched += 1
        if len(batch) >= BATCH_SIZE:
            upsert_records(resource, batch)
            batch.clear()
        if index % 50 == 0 or index == len(shopify_ids):
            logger.info(
                "Enriching %s: %s/%s (enriched=%s failed=%s skipped=%s)",
                resource,
                index,
                len(shopify_ids),
                summary.enriched,
                summary.failed,
                summary.skipped,
            )

    if batch:
        upsert_records(resource, batch)

    logger.info(
        "Finished enriching %s: enriched=%s failed=%s skipped=%s",
        resource,
        summary.enriched,
        summary.failed,
        summary.skipped,
    )
    return summary


def sync_resource(
    client: ShopifyApiClient,
    resource: ResourceName,
    *,
    enrich_details: bool = False,
) -> ResourceSyncResult:
    db = get_shopify_session(resource)
    run = ShopifySyncRun(
        resource=resource,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()

    fetched = 0
    upserted = 0
    details_fetched = 0
    batch: list[dict] = []

    try:
        for item in client.iter_resource(resource):
            batch.append(item)
            fetched += 1
            if len(batch) >= BATCH_SIZE:
                _, batch_upserted = upsert_records(resource, batch)
                upserted += batch_upserted
                batch.clear()

        if batch:
            _, batch_upserted = upsert_records(resource, batch)
            upserted += batch_upserted

        if enrich_details:
            enrich_summary = enrich_resource_details(client, resource)
            details_fetched = enrich_summary.enriched

        run.status = "completed"
        run.records_fetched = fetched
        run.records_upserted = upserted
        run.finished_at = datetime.now(timezone.utc)
        db.commit()

        total = count_records(resource)
        logger.info(
            "Synced %s: list=%s details=%s total=%s",
            resource,
            fetched,
            details_fetched,
            total,
        )
        return ResourceSyncResult(
            resource=resource,
            fetched=fetched,
            upserted=upserted,
            total_in_db=total,
            status="completed",
            details_fetched=details_fetched,
        )
    except Exception as exc:
        db.rollback()
        run.status = "failed"
        run.records_fetched = fetched
        run.records_upserted = upserted
        run.error_message = str(exc)
        run.finished_at = datetime.now(timezone.utc)
        db.add(run)
        db.commit()
        logger.exception("Failed syncing %s", resource)
        return ResourceSyncResult(
            resource=resource,
            fetched=fetched,
            upserted=upserted,
            total_in_db=count_records(resource),
            status="failed",
            details_fetched=details_fetched,
            error=str(exc),
        )
    finally:
        db.close()


def sync_resources(
    client: ShopifyApiClient,
    resources: tuple[ResourceName, ...] = ALL_RESOURCES,
    *,
    enrich_details: bool | None = None,
    rebuild_graph: bool = True,
) -> list[ResourceSyncResult]:
    detail_resources = _detail_resources_to_enrich(enrich_details)
    results = [
        sync_resource(
            client,
            resource,
            enrich_details=resource in detail_resources,
        )
        for resource in resources
    ]
    if rebuild_graph and all(result.status == "completed" for result in results):
        shopify_graph_store.rebuild()
    return results
