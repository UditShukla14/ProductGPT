from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.hvac_system import HvacSystem
from app.schemas.component_search import ComponentSearchRequest, ComponentSearchResponse
from app.schemas.hvac import HvacSearchRequest, HvacSearchResponse, HvacSystemOut
from app.services.component_search import search_by_component
from app.services.hvac_search import search_hvac_systems, system_to_schema

router = APIRouter(prefix="/hvac", tags=["hvac"])


@router.post("/components/search", response_model=ComponentSearchResponse)
def search_components(
    payload: ComponentSearchRequest, db: Session = Depends(get_db)
) -> ComponentSearchResponse:
    return search_by_component(db, payload)


@router.post("/systems/search", response_model=HvacSearchResponse)
def search_systems(payload: HvacSearchRequest, db: Session = Depends(get_db)) -> HvacSearchResponse:
    data, meta = search_hvac_systems(db, payload)
    return HvacSearchResponse(data=data, meta=meta)


@router.get("/systems/{ahri_number}", response_model=HvacSystemOut)
def get_system(ahri_number: str, db: Session = Depends(get_db)) -> HvacSystemOut:
    system = (
        db.query(HvacSystem)
        .filter(HvacSystem.ahri_number == ahri_number)
        .order_by(HvacSystem.id.desc())
        .first()
    )
    if system is None:
        raise HTTPException(status_code=404, detail="HVAC system not found")
    return system_to_schema(system)
