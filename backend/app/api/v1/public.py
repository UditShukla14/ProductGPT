from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth import verify_public_api_token
from app.database import get_db
from app.schemas.chat import ChatMessageRequest
from app.schemas.public_api import ComponentType, ProductLookupQuery, ProductLookupResponse
from app.schemas.shopify_catalog import ShopifyPublicProductResponse
from app.services.chat.stream import stream_chat_messages
from app.services.graph_component_search import GraphSearchUnavailableError, graph_search_is_ready
from app.services.product_graph_public import (
    ProductGraphUnavailableError,
    get_public_shopify_recommendations,
    product_graph_is_ready,
)
from app.services.product_lookup import lookup_product

router = APIRouter(
    prefix="/public",
    tags=["public"],
    dependencies=[Depends(verify_public_api_token)],
)


@router.get("/products/{product_id}", response_model=ProductLookupResponse)
def get_product_matchups(
    product_id: str,
    component_type: ComponentType = Query(default="auto"),
    equipment_category: str | None = None,
    refrigerant_type: str | None = None,
    flow: str | None = None,
    coil_width: str | None = None,
    furnace_width: str | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    prefer_higher_seer: bool = True,
    db: Session = Depends(get_db),
) -> ProductLookupResponse:
    query = product_id.strip()
    if not query:
        raise HTTPException(status_code=400, detail="product_id is required")

    params = ProductLookupQuery(
        component_type=component_type,
        equipment_category=equipment_category,
        refrigerant_type=refrigerant_type,
        flow=flow,
        coil_width=coil_width,
        furnace_width=furnace_width,
        limit=limit,
        offset=offset,
        prefer_higher_seer=prefer_higher_seer,
    )
    if not graph_search_is_ready():
        raise HTTPException(
            status_code=503,
            detail="Neo4j product graph is not available. Ensure Neo4j is running and synced.",
        )
    try:
        return lookup_product(db, query, params)
    except GraphSearchUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get(
    "/shopify/products/{product_id}",
    response_model=ShopifyPublicProductResponse,
    summary="People-also-bought, similar products & matchups (id + handle only)",
)
def get_shopify_product_recommendations(
    product_id: str,
    bought_together_limit: int = Query(default=8, ge=1, le=20),
    similar_products_per_brand: int = Query(
        default=8,
        ge=1,
        le=20,
        alias="other_options_per_brand",
    ),
    matchups_limit: int = Query(default=25, ge=1, le=100),
    prefer_higher_seer: bool = Query(default=True),
) -> ShopifyPublicProductResponse:
    """Serve public Shopify recommendations from ProductGraphNode only.

    Merged graph nodes already include Shopify product fields, HVAC
    MATCHES_COMPONENT links, and brand image_url — avoiding SQLite full-catalog scans.
    """
    del prefer_higher_seer  # kept for API compatibility; ranking uses shared components
    if not product_graph_is_ready():
        raise HTTPException(
            status_code=503,
            detail="ProductGraphNode is not available. Ensure Neo4j is running with the merged product graph.",
        )

    try:
        return get_public_shopify_recommendations(
            product_id,
            bought_together_limit=bought_together_limit,
            similar_products_per_brand=similar_products_per_brand,
            matchups_limit=matchups_limit,
        )
    except ProductGraphUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"Product '{product_id}' not found"
        ) from exc


@router.post(
    "/chat/messages",
    summary="Product-scoped Claude chat (SSE)",
    response_class=StreamingResponse,
)
def post_public_chat_message(
    payload: ChatMessageRequest, db: Session = Depends(get_db)
) -> StreamingResponse:
    """Bearer-authenticated product chat. Same behavior as internal `/chat/messages`.

    Requires `product_id`. Streams SSE events: `token`, `retrieval`, `done`, `error`.
    Never answers pricing questions.
    """
    return stream_chat_messages(db, payload)
