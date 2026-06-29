from sqlalchemy.orm import Session

from app.schemas.component_search import ComponentSearchRequest
from app.schemas.hvac import HvacAccessory
from app.schemas.public_api import ProductLookupQuery, ProductLookupResponse
from app.services.accessories import (
    load_accessories_by_sku,
    load_engineering_product_map,
    resolve_accessories_for_models,
)
from app.services.component_search import search_by_component


def lookup_product(
    db: Session,
    product_id: str,
    params: ProductLookupQuery,
) -> ProductLookupResponse:
    query = product_id.strip()
    search_result = search_by_component(
        db,
        ComponentSearchRequest(
            model=query,
            component_type=params.component_type,
            equipment_category=params.equipment_category,
            refrigerant_type=params.refrigerant_type,
            flow=params.flow,
            coil_width=params.coil_width,
            furnace_width=params.furnace_width,
            limit=params.limit,
            offset=params.offset,
            prefer_higher_seer=params.prefer_higher_seer,
        ),
    )

    accessories_by_sku = load_accessories_by_sku(db)
    product_map = load_engineering_product_map(db)
    accessory_model = search_result.matched_model or query
    raw_accessories = resolve_accessories_for_models(
        [accessory_model],
        accessories_by_sku,
        product_map,
    )
    accessories = [
        HvacAccessory(
            sku=item["sku"],
            description=item.get("description"),
            source_model=item.get("source_model"),
        )
        for item in raw_accessories
    ]

    return ProductLookupResponse(
        product_id=query,
        matched_type=search_result.matched_type,
        matched_model=search_result.matched_model,
        similar_matchups=search_result.similar_matchups,
        accessories=accessories,
        meta=search_result.meta,
    )
