from typing import Any, Literal

from pydantic import BaseModel, Field

ShopifyGraphNodeType = Literal["product", "variant", "customer", "order", "line_item"]

ShopifyGraphEdgeType = Literal[
    "has_variant",
    "placed_order",
    "ordered_product",
    "ordered_variant",
    "ordered_line_item",
]


class ShopifyGraphNode(BaseModel):
    id: str
    label: str
    type: ShopifyGraphNodeType
    properties: dict[str, Any] = Field(default_factory=dict)


class ShopifyGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: ShopifyGraphEdgeType


class ShopifyGraphStats(BaseModel):
    node_count: int
    edge_count: int
    nodes_by_type: dict[str, int]
    edges_by_type: dict[str, int]
    product_count: int
    customer_count: int
    order_count: int


class ShopifyGraphExploreRequest(BaseModel):
    center: str = Field(..., min_length=1, description="Shopify id, SKU, email, or order id")
    depth: int = Field(default=2, ge=1, le=4)
    max_nodes: int = Field(default=150, ge=10, le=500)


class ShopifyGraphExploreResponse(BaseModel):
    center_node_ids: list[str]
    nodes: list[ShopifyGraphNode]
    edges: list[ShopifyGraphEdge]
    stats: ShopifyGraphStats
    truncated: bool = False


class ShopifyGraphExportResponse(BaseModel):
    backend: str
    nodes: list[ShopifyGraphNode]
    edges: list[ShopifyGraphEdge]
    stats: ShopifyGraphStats


class ShopifySyncResourceResult(BaseModel):
    resource: str
    fetched: int
    upserted: int
    details_fetched: int = 0
    total_in_db: int
    status: str
    error: str | None = None


class ShopifySyncResponse(BaseModel):
    results: list[ShopifySyncResourceResult]
    graph_rebuilt: bool
    graph_stats: ShopifyGraphStats | None = None


class ShopifySyncJobStatus(BaseModel):
    state: Literal["idle", "running", "completed", "failed"]
    started_at: str | None = None
    finished_at: str | None = None
    current_resource: str | None = None
    phase: str | None = None
    error: str | None = None
    results: list[ShopifySyncResourceResult] = Field(default_factory=list)
    graph_rebuilt: bool = False
    graph_stats: ShopifyGraphStats | None = None


class ShopifySyncStatusResponse(BaseModel):
    products: int
    customers: int
    orders: int
    job: ShopifySyncJobStatus


class ShopifySyncStartResponse(BaseModel):
    message: str
    job: ShopifySyncJobStatus


class ShopifyProductEnrichResponse(BaseModel):
    enriched: int
    failed: int = 0
    skipped: int = 0
    total_in_db: int
    product_ids: list[str]
    status: str
    graph_rebuilt: bool = False
    graph_stats: ShopifyGraphStats | None = None
    error: str | None = None
