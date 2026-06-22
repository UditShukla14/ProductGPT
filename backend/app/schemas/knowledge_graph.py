from typing import Any, Literal

from pydantic import BaseModel, Field

GraphNodeType = Literal[
    "certification",
    "outdoor",
    "coil",
    "furnace",
    "category",
    "refrigerant",
    "accessory",
]

GraphEdgeType = Literal[
    "has_outdoor",
    "has_coil",
    "has_furnace",
    "in_category",
    "uses_refrigerant",
    "has_accessory",
]


class GraphNode(BaseModel):
    id: str
    label: str
    type: GraphNodeType
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: GraphEdgeType


class GraphStats(BaseModel):
    node_count: int
    edge_count: int
    nodes_by_type: dict[str, int]
    edges_by_type: dict[str, int]
    certification_count: int
    component_count: int


class GraphExploreRequest(BaseModel):
    center: str = Field(..., min_length=1, description="AHRI number or component model to explore from")
    depth: int = Field(default=2, ge=1, le=4)
    max_nodes: int = Field(default=150, ge=10, le=500)
    equipment_category: str | None = None
    refrigerant_type: str | None = None
    active_only: bool = True


class GraphExploreResponse(BaseModel):
    center_node_ids: list[str]
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    stats: GraphStats
    truncated: bool = False


class GraphExportResponse(BaseModel):
    backend: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    stats: GraphStats
