from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import networkx as nx
from sqlalchemy.orm import Session

from app.models.sales_line_item import SalesLineItem
from app.sales.graph.schemas import SalesGraphEdgeType, SalesGraphNodeType

EDGE_ATTR = "type"

REL_TYPE_MAP: dict[SalesGraphEdgeType, str] = {
    "belongs_to_division": "BELONGS_TO_DIVISION",
    "belongs_to_branch": "BELONGS_TO_BRANCH",
    "sold_in_region": "SOLD_IN_REGION",
    "from_vendor": "FROM_VENDOR",
    "in_line_of_business": "IN_LINE_OF_BUSINESS",
    "in_category": "IN_CATEGORY",
    "in_subcategory": "IN_SUBCATEGORY",
    "subcategory_in_category": "SUBCATEGORY_IN_CATEGORY",
}

CYPHER_REL_TO_EDGE: dict[str, SalesGraphEdgeType] = {v: k for k, v in REL_TYPE_MAP.items()}


@dataclass
class GraphElementNode:
    id: str
    label: str
    type: SalesGraphNodeType
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphElementEdge:
    source: str
    target: str
    type: SalesGraphEdgeType
    properties: dict[str, Any] = field(default_factory=dict)


def _slug(value: str) -> str:
    return " ".join(value.strip().split())


def _node_id(prefix: str, value: str) -> str:
    return f"{prefix}:{_slug(value).lower()}"


def extract_graph_elements(rows: list[SalesLineItem]) -> tuple[list[GraphElementNode], list[GraphElementEdge]]:
    nodes: dict[str, GraphElementNode] = {}
    edge_keys: set[tuple[str, str, str]] = set()
    edges: list[GraphElementEdge] = []
    sold_qty: dict[tuple[str, str], float] = defaultdict(float)
    sold_lines: dict[tuple[str, str], int] = defaultdict(int)

    def add_node(node_type: SalesGraphNodeType, value: str | None, *, extra: dict[str, Any] | None = None) -> str | None:
        if not value:
            return None
        label = _slug(value)
        node_key = _node_id(node_type, label)
        if node_key not in nodes:
            props = {"name": label}
            if extra:
                props.update(extra)
            nodes[node_key] = GraphElementNode(
                id=node_key,
                label=label,
                type=node_type,
                properties=props,
            )
        return node_key

    def add_edge(
        edge_type: SalesGraphEdgeType,
        source: str | None,
        target: str | None,
        *,
        properties: dict[str, Any] | None = None,
    ) -> None:
        if not source or not target:
            return
        key = (edge_type, source, target)
        if key in edge_keys:
            return
        edge_keys.add(key)
        edges.append(
            GraphElementEdge(
                source=source,
                target=target,
                type=edge_type,
                properties=properties or {},
            )
        )

    for row in rows:
        division_id = add_node("division", row.cod_division)
        branch_id = add_node("branch_division", row.branch_division)
        region_id = add_node("region", row.branch_region)
        vendor_id = add_node("vendor", row.vendor)
        lob_id = add_node("line_of_business", row.line_of_business)
        category_id = add_node("category", row.product_category)
        subcategory_id = add_node("subcategory", row.product_subcategory)
        sku_id = add_node(
            "sku",
            row.sku,
            extra={
                "sku": _slug(row.sku) if row.sku else None,
                "vendor": row.vendor,
                "category": row.product_category,
                "subcategory": row.product_subcategory,
            },
        )

        add_edge("belongs_to_division", branch_id, division_id)
        add_edge("belongs_to_branch", region_id, branch_id)
        add_edge("from_vendor", sku_id, vendor_id)
        add_edge("in_line_of_business", sku_id, lob_id)
        add_edge("in_category", sku_id, category_id)
        add_edge("in_subcategory", sku_id, subcategory_id)
        add_edge("subcategory_in_category", subcategory_id, category_id)

        if sku_id and region_id:
            sold_qty[(sku_id, region_id)] += float(row.quantity or 0)
            sold_lines[(sku_id, region_id)] += 1

    for (sku_id, region_id), qty in sold_qty.items():
        add_edge(
            "sold_in_region",
            sku_id,
            region_id,
            properties={
                "quantity": round(qty, 4),
                "line_count": sold_lines[(sku_id, region_id)],
            },
        )

    return list(nodes.values()), edges


def build_graph_from_rows(rows: list[SalesLineItem]) -> nx.Graph:
    nodes, edges = extract_graph_elements(rows)
    graph = nx.Graph()
    for node in nodes:
        graph.add_node(
            node.id,
            label=node.label,
            type=node.type,
            properties=node.properties,
        )
    for edge in edges:
        graph.add_edge(
            edge.source,
            edge.target,
            **{EDGE_ATTR: edge.type},
            properties=edge.properties,
        )
    return graph


def load_sales_rows(db: Session) -> list[SalesLineItem]:
    return db.query(SalesLineItem).all()
