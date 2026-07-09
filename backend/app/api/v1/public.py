from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import verify_public_api_token
from app.database import get_db
from app.schemas.public_api import ComponentType, ProductLookupQuery, ProductLookupResponse
from app.schemas.shopify_catalog import (
    ShopifyCategoryBrandGroup,
    ShopifyProductDetail,
    ShopifyProductRecommendation,
    ShopifyProductSummary,
    ShopifyPublicProductResponse,
    ShopifySameCategoryByBrandResponse,
)
from app.services.product_lookup import lookup_product
from app.shopify.catalog import (
    get_product_detail,
    products_bought_together,
    products_same_category_by_brand,
)
from app.shopify.storage import count_records

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
    return lookup_product(db, query, params)


@router.get(
    "/shopify/products/{product_id}",
    response_model=ShopifyPublicProductResponse,
    summary="People-also-bought & other-options for a Shopify product",
)
def get_shopify_product_recommendations(
    product_id: str,
    bought_together_limit: int = Query(default=8, ge=1, le=20),
    other_options_per_brand: int = Query(default=8, ge=1, le=20),
) -> ShopifyPublicProductResponse:
    if count_records("products") == 0:
        raise HTTPException(
            status_code=503,
            detail="Shopify products database is empty. Data has not been synced yet.",
        )

    detail = get_product_detail(product_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")

    bought_items = (
        products_bought_together(product_id, limit=bought_together_limit)
        if count_records("orders") > 0
        else []
    )

    grouped = products_same_category_by_brand(product_id, per_brand_limit=other_options_per_brand)

    return ShopifyPublicProductResponse(
        product_id=product_id,
        product=ShopifyProductDetail(**detail),
        bought_together=[ShopifyProductRecommendation(**item) for item in bought_items],
        other_options=ShopifySameCategoryByBrandResponse(
            product_id=product_id,
            category=grouped["category"],
            current_vendor=grouped["current_vendor"],
            match_keywords=grouped["match_keywords"],
            brands=[
                ShopifyCategoryBrandGroup(
                    vendor=brand["vendor"],
                    products=[ShopifyProductSummary(**p) for p in brand["products"]],
                )
                for brand in grouped["brands"]
            ],
        ),
    )
