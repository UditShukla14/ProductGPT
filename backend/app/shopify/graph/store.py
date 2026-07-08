from __future__ import annotations

from collections import Counter, deque
from typing import Any

import networkx as nx

from app.knowledge_graph.neo4j_client import neo4j_client
from app.shopify.graph.builder import (
    EDGE_ATTR,
    build_graph_from_shopify_data,
    load_shopify_graph_inputs,
)
from app.shopify.graph.neo4j_store import shopify_neo4j_graph_store
from app.shopify.graph.schemas import (
    ShopifyGraphEdge,
    ShopifyGraphExploreRequest,
    ShopifyGraphExploreResponse,
    ShopifyGraphExportResponse,
    ShopifyGraphNode,
    ShopifyGraphStats,
)


class ShopifyNetworkxGraphStore:
    def __init__(self) -> None:
        self._graph: nx.Graph | None = None

    @property
    def is_ready(self) -> bool:
        return self._graph is not None

    def rebuild(
        self,
        products: list[dict[str, Any]],
        customers: list[dict[str, Any]],
        orders: list[dict[str, Any]],
    ) -> ShopifyGraphStats:
        self._graph = build_graph_from_shopify_data(products, customers, orders)
        return self.get_stats()

    def get_stats(self) -> ShopifyGraphStats:
        graph = self._require_graph()
        nodes_by_type: Counter[str] = Counter()
        for _, data in graph.nodes(data=True):
            nodes_by_type[str(data.get("type", "unknown"))] += 1

        edges_by_type: Counter[str] = Counter()
        for _, _, data in graph.edges(data=True):
            edges_by_type[str(data.get(EDGE_ATTR, "unknown"))] += 1

        return ShopifyGraphStats(
            node_count=graph.number_of_nodes(),
            edge_count=graph.number_of_edges(),
            nodes_by_type=dict(nodes_by_type),
            edges_by_type=dict(edges_by_type),
            product_count=nodes_by_type.get("product", 0),
            customer_count=nodes_by_type.get("customer", 0),
            order_count=nodes_by_type.get("order", 0),
        )

    def explore(self, params: ShopifyGraphExploreRequest) -> ShopifyGraphExploreResponse:
        graph = self._require_graph()
        center_ids = self._resolve_center_nodes(graph, params.center.strip())
        if not center_ids:
            raise ValueError(f"No Shopify graph nodes found matching '{params.center}'")

        center_set = set(center_ids)
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque((node_id, 0) for node_id in center_ids)
        truncated = False

        while queue and len(visited) < params.max_nodes:
            node_id, depth = queue.popleft()
            if node_id in visited:
                continue

            node_data = graph.nodes.get(node_id)
            if node_data is None:
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
        edges: list[ShopifyGraphEdge] = []

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
                    ShopifyGraphEdge(
                        id=f"{edge_key[0]}--{edge_key[1]}",
                        source=source,
                        target=target,
                        type=edge_data[EDGE_ATTR],
                    )
                )

        return ShopifyGraphExploreResponse(
            center_node_ids=center_ids,
            nodes=nodes,
            edges=edges,
            stats=self.get_stats(),
            truncated=truncated,
        )

    def export_graph(self, limit: int | None = None) -> ShopifyGraphExportResponse:
        graph = self._require_graph()
        node_items = list(graph.nodes(data=True))
        if limit is not None:
            node_items = node_items[:limit]

        nodes = [self._node_to_schema(node_id, data) for node_id, data in node_items]
        node_ids = {node.id for node in nodes}
        edges: list[ShopifyGraphEdge] = []
        seen: set[tuple[str, str]] = set()

        for source, target, data in graph.edges(data=True):
            if source not in node_ids or target not in node_ids:
                continue
            edge_key = tuple(sorted((source, target)))
            if edge_key in seen:
                continue
            seen.add(edge_key)
            edges.append(
                ShopifyGraphEdge(
                    id=f"{edge_key[0]}--{edge_key[1]}",
                    source=source,
                    target=target,
                    type=data[EDGE_ATTR],
                )
            )

        return ShopifyGraphExportResponse(
            backend="networkx",
            nodes=nodes,
            edges=edges,
            stats=self.get_stats(),
        )

    def _require_graph(self) -> nx.Graph:
        if self._graph is None:
            raise RuntimeError("Shopify knowledge graph has not been built yet")
        return self._graph

    def _resolve_center_nodes(self, graph: nx.Graph, center: str) -> list[str]:
        normalized = center.strip()
        if not normalized:
            return []

        direct_candidates = [
            f"product:{normalized}",
            f"variant:{normalized}",
            f"customer:{normalized}",
            f"order:{normalized}",
            f"line_item:{normalized}",
        ]
        matches = [node_id for node_id in direct_candidates if graph.has_node(node_id)]
        if matches:
            return matches

        lowered = normalized.lower()
        partial: list[str] = []
        for node_id, data in graph.nodes(data=True):
            label = str(data.get("label", "")).lower()
            properties = data.get("properties") or {}
            sku = str(properties.get("sku", "")).lower()
            email = str(properties.get("email", "")).lower()
            if (
                lowered in label
                or lowered in node_id.lower()
                or (sku and lowered in sku)
                or (email and lowered in email)
            ):
                partial.append(node_id)

        return sorted(set(partial))[:5]

    def _node_to_schema(self, node_id: str, node_data: dict[str, Any]) -> ShopifyGraphNode:
        return ShopifyGraphNode(
            id=node_id,
            label=str(node_data.get("label", node_id)),
            type=node_data["type"],
            properties=dict(node_data.get("properties") or {}),
        )


class ShopifyKnowledgeGraphStore:
    def __init__(self) -> None:
        self._networkx = ShopifyNetworkxGraphStore()
        self._backend: str = "networkx"

    @property
    def backend(self) -> str:
        return self._backend

    @property
    def is_ready(self) -> bool:
        if self._backend == "neo4j":
            return shopify_neo4j_graph_store.is_ready()
        return self._networkx.is_ready

    def connect_neo4j(self) -> bool:
        if neo4j_client.connect():
            self._backend = "neo4j"
            return True
        self._backend = "networkx"
        return False

    def rebuild(self) -> ShopifyGraphStats:
        products, customers, orders = load_shopify_graph_inputs()
        networkx_stats = self._networkx.rebuild(products, customers, orders)

        if neo4j_client.enabled and neo4j_client.is_connected:
            return shopify_neo4j_graph_store.sync_records(products, customers, orders)

        if neo4j_client.enabled:
            connected = self.connect_neo4j()
            if connected:
                return shopify_neo4j_graph_store.sync_records(products, customers, orders)

        self._backend = "networkx"
        return networkx_stats

    def get_stats(self) -> ShopifyGraphStats:
        if self._backend == "neo4j" and shopify_neo4j_graph_store.is_ready():
            return shopify_neo4j_graph_store.get_stats()
        return self._networkx.get_stats()

    def explore(self, params: ShopifyGraphExploreRequest) -> ShopifyGraphExploreResponse:
        if self._backend == "neo4j" and shopify_neo4j_graph_store.is_ready():
            return shopify_neo4j_graph_store.explore(params)
        return self._networkx.explore(params)

    def export_graph(self, limit: int | None = None) -> ShopifyGraphExportResponse:
        if self._backend == "neo4j" and shopify_neo4j_graph_store.is_ready():
            return shopify_neo4j_graph_store.export_graph(limit=limit)
        return self._networkx.export_graph(limit=limit)


shopify_graph_store = ShopifyKnowledgeGraphStore()
