from __future__ import annotations

from collections import Counter, deque

import networkx as nx
from sqlalchemy.orm import Session

from app.knowledge_graph.neo4j_client import neo4j_client
from app.sales.graph.builder import (
    EDGE_ATTR,
    build_graph_from_rows,
    load_sales_rows,
)
from app.sales.graph.neo4j_store import sales_neo4j_graph_store
from app.sales.graph.schemas import (
    SalesGraphEdge,
    SalesGraphExploreRequest,
    SalesGraphExploreResponse,
    SalesGraphExportResponse,
    SalesGraphNode,
    SalesGraphStats,
)


class SalesNetworkxGraphStore:
    def __init__(self) -> None:
        self._graph: nx.Graph | None = None
        self._line_item_count = 0

    @property
    def is_ready(self) -> bool:
        return self._graph is not None

    def rebuild(self, db: Session) -> SalesGraphStats:
        rows = load_sales_rows(db)
        self._line_item_count = len(rows)
        self._graph = build_graph_from_rows(rows)
        return self.get_stats()

    def get_stats(self) -> SalesGraphStats:
        graph = self._require_graph()
        nodes_by_type: Counter[str] = Counter()
        for _, data in graph.nodes(data=True):
            nodes_by_type[str(data.get("type", "unknown"))] += 1

        edges_by_type: Counter[str] = Counter()
        for _, _, data in graph.edges(data=True):
            edges_by_type[str(data.get(EDGE_ATTR, "unknown"))] += 1

        return SalesGraphStats(
            node_count=graph.number_of_nodes(),
            edge_count=graph.number_of_edges(),
            nodes_by_type=dict(nodes_by_type),
            edges_by_type=dict(edges_by_type),
            sku_count=nodes_by_type.get("sku", 0),
            region_count=nodes_by_type.get("region", 0),
            vendor_count=nodes_by_type.get("vendor", 0),
            line_item_count=self._line_item_count,
        )

    def explore(self, params: SalesGraphExploreRequest) -> SalesGraphExploreResponse:
        graph = self._require_graph()
        center_ids = self._resolve_center_nodes(graph, params.center.strip())
        if not center_ids:
            raise ValueError(f"No sales graph nodes found matching '{params.center}'")

        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque((node_id, 0) for node_id in center_ids)
        truncated = False

        while queue and len(visited) < params.max_nodes:
            node_id, depth = queue.popleft()
            if node_id in visited:
                continue
            if node_id not in graph:
                continue
            visited.add(node_id)
            if depth >= params.depth:
                continue
            for neighbor in graph.neighbors(node_id):
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))

        if queue and len(visited) >= params.max_nodes:
            truncated = True

        nodes = [self._node_to_schema(node_id, graph.nodes[node_id]) for node_id in sorted(visited)]
        edge_ids: set[tuple[str, str]] = set()
        edges: list[SalesGraphEdge] = []
        for source in visited:
            for target in graph.neighbors(source):
                if target not in visited:
                    continue
                edge_key = tuple(sorted((source, target)))
                if edge_key in edge_ids:
                    continue
                edge_ids.add(edge_key)
                edge_data = graph.edges[source, target]
                edges.append(
                    SalesGraphEdge(
                        id=f"{edge_key[0]}--{edge_key[1]}",
                        source=source,
                        target=target,
                        type=edge_data[EDGE_ATTR],
                        properties=dict(edge_data.get("properties") or {}),
                    )
                )

        return SalesGraphExploreResponse(
            center_node_ids=center_ids,
            nodes=nodes,
            edges=edges,
            stats=self.get_stats(),
            truncated=truncated,
        )

    def export_graph(self, limit: int | None = None) -> SalesGraphExportResponse:
        graph = self._require_graph()
        node_items = list(graph.nodes(data=True))
        if limit is not None:
            node_items = node_items[:limit]
        nodes = [self._node_to_schema(node_id, data) for node_id, data in node_items]
        node_ids = {node.id for node in nodes}
        edges: list[SalesGraphEdge] = []
        seen: set[tuple[str, str]] = set()
        for source, target, data in graph.edges(data=True):
            if source not in node_ids or target not in node_ids:
                continue
            edge_key = tuple(sorted((source, target)))
            if edge_key in seen:
                continue
            seen.add(edge_key)
            edges.append(
                SalesGraphEdge(
                    id=f"{edge_key[0]}--{edge_key[1]}",
                    source=source,
                    target=target,
                    type=data[EDGE_ATTR],
                    properties=dict(data.get("properties") or {}),
                )
            )
        return SalesGraphExportResponse(
            backend="networkx",
            nodes=nodes,
            edges=edges,
            stats=self.get_stats(),
        )

    def _require_graph(self) -> nx.Graph:
        if self._graph is None:
            raise RuntimeError("Sales knowledge graph has not been built yet")
        return self._graph

    def _resolve_center_nodes(self, graph: nx.Graph, center: str) -> list[str]:
        if not center:
            return []
        direct = [
            center,
            f"sku:{center.lower()}",
            f"region:{center.lower()}",
            f"vendor:{center.lower()}",
            f"category:{center.lower()}",
            f"subcategory:{center.lower()}",
            f"division:{center.lower()}",
            f"branch_division:{center.lower()}",
            f"line_of_business:{center.lower()}",
        ]
        matches = [node_id for node_id in direct if graph.has_node(node_id)]
        if matches:
            return matches

        lowered = center.lower()
        partial: list[str] = []
        for node_id, data in graph.nodes(data=True):
            label = str(data.get("label", "")).lower()
            props = data.get("properties") or {}
            sku = str(props.get("sku", "")).lower()
            if lowered in label or lowered in node_id.lower() or (sku and lowered in sku):
                partial.append(node_id)
        return sorted(set(partial))[:5]

    def _node_to_schema(self, node_id: str, node_data: dict) -> SalesGraphNode:
        return SalesGraphNode(
            id=node_id,
            label=str(node_data.get("label", node_id)),
            type=node_data["type"],
            properties=dict(node_data.get("properties") or {}),
        )


class SalesKnowledgeGraphStore:
    def __init__(self) -> None:
        self._networkx = SalesNetworkxGraphStore()
        self._backend = "networkx"

    @property
    def backend(self) -> str:
        return self._backend

    @property
    def is_ready(self) -> bool:
        if self._backend == "neo4j":
            return sales_neo4j_graph_store.is_ready()
        return self._networkx.is_ready

    def connect_neo4j(self) -> bool:
        if neo4j_client.connect():
            self._backend = "neo4j"
            return True
        self._backend = "networkx"
        return False

    def rebuild(self, db: Session) -> SalesGraphStats:
        networkx_stats = self._networkx.rebuild(db)
        if neo4j_client.enabled and neo4j_client.is_connected:
            stats = sales_neo4j_graph_store.rebuild(db)
            stats.line_item_count = networkx_stats.line_item_count
            self._backend = "neo4j"
            return stats
        if neo4j_client.enabled and self.connect_neo4j():
            stats = sales_neo4j_graph_store.rebuild(db)
            stats.line_item_count = networkx_stats.line_item_count
            return stats
        self._backend = "networkx"
        return networkx_stats

    def get_stats(self) -> SalesGraphStats:
        if self._backend == "neo4j" and sales_neo4j_graph_store.is_ready():
            stats = sales_neo4j_graph_store.get_stats()
            stats.line_item_count = self._networkx._line_item_count
            return stats
        return self._networkx.get_stats()

    def explore(self, params: SalesGraphExploreRequest) -> SalesGraphExploreResponse:
        # Explore uses NetworkX (same pattern as Shopify) for neighborhood search.
        if not self._networkx.is_ready:
            raise RuntimeError("Sales knowledge graph has not been built yet")
        return self._networkx.explore(params)

    def export_graph(self, limit: int | None = None) -> SalesGraphExportResponse:
        if not self._networkx.is_ready:
            raise RuntimeError("Sales knowledge graph has not been built yet")
        result = self._networkx.export_graph(limit=limit)
        result.backend = self._backend
        return result


sales_graph_store = SalesKnowledgeGraphStore()
