from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.knowledge_graph.store import graph_store
from app.models.hvac_system import HvacSystem
from app.schemas.component_search import (
    ComponentSearchRequest,
    ComponentSearchResponse,
    PairedMatchupsRequest,
    PairedMatchupsResponse,
)
from app.schemas.hvac import HvacSearchRequest, HvacSearchResponse, HvacSystemOut
from app.schemas.knowledge_graph import (
    GraphExploreRequest,
    GraphExploreResponse,
    GraphExportResponse,
    GraphStats,
)
from app.services.component_search import search_by_component, search_paired_matchups
from app.services.hvac_search import search_hvac_systems, system_to_schema

router = APIRouter(prefix="/hvac", tags=["hvac"])


@router.post("/components/search", response_model=ComponentSearchResponse)
def search_components(
    payload: ComponentSearchRequest, db: Session = Depends(get_db)
) -> ComponentSearchResponse:
    return search_by_component(db, payload)


@router.post("/components/matchups", response_model=PairedMatchupsResponse)
def search_paired_components(
    payload: PairedMatchupsRequest, db: Session = Depends(get_db)
) -> PairedMatchupsResponse:
    return search_paired_matchups(db, payload)


@router.post("/systems/search", response_model=HvacSearchResponse)
def search_systems(payload: HvacSearchRequest, db: Session = Depends(get_db)) -> HvacSearchResponse:
    data, meta = search_hvac_systems(db, payload)
    return HvacSearchResponse(data=data, meta=meta)


@router.get("/graph/stats", response_model=GraphStats)
def graph_stats() -> GraphStats:
    if not graph_store.is_ready:
        raise HTTPException(status_code=503, detail="Knowledge graph is not built yet")
    return graph_store.get_stats()


@router.post("/graph/explore", response_model=GraphExploreResponse)
def explore_graph(payload: GraphExploreRequest) -> GraphExploreResponse:
    if not graph_store.is_ready:
        raise HTTPException(status_code=503, detail="Knowledge graph is not built yet")
    try:
        return graph_store.explore(payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/graph/export", response_model=GraphExportResponse)
def export_graph(limit: int | None = None) -> GraphExportResponse:
    if not graph_store.is_ready:
        raise HTTPException(status_code=503, detail="Knowledge graph is not built yet")
    if limit is not None and (limit < 1 or limit > 500_000):
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500000")
    return graph_store.export_graph(limit=limit)


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
