from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.public_api import ComponentType, ProductLookupQuery, ProductLookupResponse
from app.services.product_lookup import lookup_product

router = APIRouter(prefix="/public", tags=["public"])


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
