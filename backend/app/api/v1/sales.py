from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.sales.graph.schemas import (
    SalesGraphExploreRequest,
    SalesGraphExploreResponse,
    SalesGraphExportResponse,
    SalesGraphStats,
)
from app.sales.graph.store import sales_graph_store

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post("/graph/rebuild", response_model=SalesGraphStats)
def rebuild_sales_graph(db: Session = Depends(get_db)) -> SalesGraphStats:
    sales_graph_store.connect_neo4j()
    return sales_graph_store.rebuild(db)


@router.get("/graph/stats", response_model=SalesGraphStats)
def sales_graph_stats() -> SalesGraphStats:
    if not sales_graph_store.is_ready:
        raise HTTPException(status_code=503, detail="Sales knowledge graph is not built yet")
    return sales_graph_store.get_stats()


@router.post("/graph/explore", response_model=SalesGraphExploreResponse)
def explore_sales_graph(payload: SalesGraphExploreRequest) -> SalesGraphExploreResponse:
    if not sales_graph_store.is_ready:
        raise HTTPException(status_code=503, detail="Sales knowledge graph is not built yet")
    try:
        return sales_graph_store.explore(payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/graph/export", response_model=SalesGraphExportResponse)
def export_sales_graph(
    limit: int | None = Query(default=None, ge=1, le=50_000),
) -> SalesGraphExportResponse:
    if not sales_graph_store.is_ready:
        raise HTTPException(status_code=503, detail="Sales knowledge graph is not built yet")
    return sales_graph_store.export_graph(limit=limit)
