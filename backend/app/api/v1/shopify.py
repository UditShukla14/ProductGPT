from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.shopify import ALL_RESOURCES
from app.shopify.graph.store import shopify_graph_store
from app.shopify.graph.schemas import (
    ShopifyGraphExploreRequest,
    ShopifyGraphExploreResponse,
    ShopifyGraphExportResponse,
    ShopifyGraphStats,
    ShopifyProductEnrichResponse,
    ShopifySyncResourceResult,
    ShopifySyncResponse,
)
from app.shopify.service import (
    build_shopify_client,
    is_shopify_configured,
    run_full_shopify_sync,
    run_product_enrichment,
)
from app.shopify.storage import count_records

router = APIRouter(prefix="/shopify", tags=["shopify"])


def _missing_shopify_config() -> list[str]:
    missing: list[str] = []
    if not settings.shopify_api_token:
        missing.append("SHOPIFY_API_TOKEN")
    if not settings.shopify_api_shop_domain:
        missing.append("SHOPIFY_API_SHOP_DOMAIN")
    if not settings.shopify_api_base_url:
        missing.append("SHOPIFY_API_BASE_URL")
    return missing


@router.get("/sync/status")
def sync_status() -> dict[str, int]:
    return {resource: count_records(resource) for resource in ALL_RESOURCES}


@router.get("/health")
def shopify_health() -> dict:
    if not is_shopify_configured():
        missing = _missing_shopify_config()
        raise HTTPException(
            status_code=400,
            detail=f"Missing Shopify configuration: {', '.join(missing)}",
        )
    try:
        with build_shopify_client() as client:
            return client.verify_connection()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/sync", response_model=ShopifySyncResponse)
def run_sync(rebuild_graph: bool = True) -> ShopifySyncResponse:
    if not is_shopify_configured():
        missing = _missing_shopify_config()
        raise HTTPException(
            status_code=400,
            detail=f"Missing Shopify configuration: {', '.join(missing)}",
        )

    results = run_full_shopify_sync(rebuild_graph=rebuild_graph)

    graph_stats = shopify_graph_store.get_stats() if shopify_graph_store.is_ready else None
    return ShopifySyncResponse(
        results=[
            ShopifySyncResourceResult(
                resource=result.resource,
                fetched=result.fetched,
                upserted=result.upserted,
                details_fetched=result.details_fetched,
                total_in_db=result.total_in_db,
                status=result.status,
                error=result.error,
            )
            for result in results
        ],
        graph_rebuilt=rebuild_graph and all(result.status == "completed" for result in results),
        graph_stats=graph_stats,
    )


@router.post("/products/enrich", response_model=ShopifyProductEnrichResponse)
def enrich_products(
    product_ids: list[str] | None = Query(
        default=None,
        description="Specific Shopify product ids to enrich (e.g. 9785832472867). Omit to enrich all stored products.",
    ),
    rebuild_graph: bool = True,
    skip_already_enriched: bool = True,
) -> ShopifyProductEnrichResponse:
    if not is_shopify_configured():
        missing = _missing_shopify_config()
        raise HTTPException(
            status_code=400,
            detail=f"Missing Shopify configuration: {', '.join(missing)}",
        )

    result = run_product_enrichment(
        product_ids=product_ids,
        rebuild_graph=rebuild_graph,
        skip_already_enriched=skip_already_enriched,
    )
    if result.status == "failed":
        raise HTTPException(status_code=502, detail=result.error or "Product enrichment failed")

    graph_stats = shopify_graph_store.get_stats() if shopify_graph_store.is_ready else None
    return ShopifyProductEnrichResponse(
        enriched=result.enriched,
        failed=result.failed,
        skipped=result.skipped,
        total_in_db=result.total_in_db,
        product_ids=result.product_ids,
        status=result.status,
        graph_rebuilt=rebuild_graph and result.enriched > 0,
        graph_stats=graph_stats,
        error=result.error,
    )


@router.post("/graph/rebuild", response_model=ShopifyGraphStats)
def rebuild_graph() -> ShopifyGraphStats:
    try:
        return shopify_graph_store.rebuild()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/graph/stats", response_model=ShopifyGraphStats)
def graph_stats() -> ShopifyGraphStats:
    if not shopify_graph_store.is_ready:
        raise HTTPException(status_code=503, detail="Shopify knowledge graph is not built yet")
    return shopify_graph_store.get_stats()


@router.post("/graph/explore", response_model=ShopifyGraphExploreResponse)
def explore_graph(payload: ShopifyGraphExploreRequest) -> ShopifyGraphExploreResponse:
    if not shopify_graph_store.is_ready:
        raise HTTPException(status_code=503, detail="Shopify knowledge graph is not built yet")
    try:
        return shopify_graph_store.explore(payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/graph/export", response_model=ShopifyGraphExportResponse)
def export_graph(limit: int | None = None) -> ShopifyGraphExportResponse:
    if not shopify_graph_store.is_ready:
        raise HTTPException(status_code=503, detail="Shopify knowledge graph is not built yet")
    if limit is not None and limit < 1:
        raise HTTPException(status_code=400, detail="limit must be >= 1")
    return shopify_graph_store.export_graph(limit=limit)
