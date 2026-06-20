from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.knowledge_graph.neo4j_client import neo4j_client
from app.knowledge_graph.store import graph_store
from app.models.hvac_system import HvacSystem
from app.models.knowledge_source import KnowledgeSource
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    hvac_count = db.query(HvacSystem).count()
    source_count = db.query(KnowledgeSource).count()
    graph_stats = graph_store.get_stats() if graph_store.is_ready else None
    return HealthResponse(
        status="ok",
        hvac_system_count=hvac_count,
        knowledge_sources=source_count,
        graph_node_count=graph_stats.node_count if graph_stats else 0,
        graph_edge_count=graph_stats.edge_count if graph_stats else 0,
        graph_backend=graph_store.backend,
        neo4j_connected=neo4j_client.is_connected,
    )
