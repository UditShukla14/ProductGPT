from typing import Any, Literal

from pydantic import BaseModel, Field

SalesGraphNodeType = Literal[
    "division",
    "branch_division",
    "region",
    "vendor",
    "line_of_business",
    "category",
    "subcategory",
    "sku",
]

SalesGraphEdgeType = Literal[
    "belongs_to_division",
    "belongs_to_branch",
    "sold_in_region",
    "from_vendor",
    "in_line_of_business",
    "in_category",
    "in_subcategory",
    "subcategory_in_category",
]


class SalesGraphNode(BaseModel):
    id: str
    label: str
    type: SalesGraphNodeType
    properties: dict[str, Any] = Field(default_factory=dict)


class SalesGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: SalesGraphEdgeType
    properties: dict[str, Any] = Field(default_factory=dict)


class SalesGraphStats(BaseModel):
    node_count: int
    edge_count: int
    nodes_by_type: dict[str, int]
    edges_by_type: dict[str, int]
    sku_count: int
    region_count: int
    vendor_count: int
    line_item_count: int = 0


class SalesGraphExploreRequest(BaseModel):
    center: str = Field(..., min_length=1, description="SKU, region, vendor, or node id")
    depth: int = Field(default=2, ge=1, le=4)
    max_nodes: int = Field(default=150, ge=10, le=500)


class SalesGraphExploreResponse(BaseModel):
    center_node_ids: list[str]
    nodes: list[SalesGraphNode]
    edges: list[SalesGraphEdge]
    stats: SalesGraphStats
    truncated: bool = False


class SalesGraphExportResponse(BaseModel):
    backend: str
    nodes: list[SalesGraphNode]
    edges: list[SalesGraphEdge]
    stats: SalesGraphStats
