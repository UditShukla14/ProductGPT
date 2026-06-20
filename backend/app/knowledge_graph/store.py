from __future__ import annotations

from collections import Counter, deque
from typing import Any

import networkx as nx
from sqlalchemy.orm import Session

from app.knowledge_graph.builder import (
    EDGE_ATTR,
    _cert_id,
    _component_id,
    build_graph_from_systems,
)
from app.knowledge_graph.neo4j_client import neo4j_client
from app.knowledge_graph.neo4j_store import neo4j_graph_store
from app.models.hvac_system import HvacSystem
from app.schemas.knowledge_graph import (
    GraphEdge,
    GraphExploreRequest,
    GraphExploreResponse,
    GraphExportResponse,
    GraphNode,
    GraphStats,
)


class NetworkxGraphStore:
    def __init__(self) -> None:
        self._graph: nx.Graph | None = None

    @property
    def is_ready(self) -> bool:
        return self._graph is not None

    def rebuild_from_systems(self, systems: list[HvacSystem]) -> GraphStats:
        self._graph = build_graph_from_systems(systems)
        return self.get_stats()

    def get_stats(self) -> GraphStats:
        graph = self._require_graph()
        nodes_by_type: Counter[str] = Counter()
        for _, data in graph.nodes(data=True):
            nodes_by_type[str(data.get("type", "unknown"))] += 1

        edges_by_type: Counter[str] = Counter()
        for _, _, data in graph.edges(data=True):
            edges_by_type[str(data.get(EDGE_ATTR, "unknown"))] += 1

        component_count = (
            nodes_by_type.get("outdoor", 0)
            + nodes_by_type.get("coil", 0)
            + nodes_by_type.get("furnace", 0)
        )

        return GraphStats(
            node_count=graph.number_of_nodes(),
            edge_count=graph.number_of_edges(),
            nodes_by_type=dict(nodes_by_type),
            edges_by_type=dict(edges_by_type),
            certification_count=nodes_by_type.get("certification", 0),
            component_count=component_count,
        )

    def explore(self, params: GraphExploreRequest) -> GraphExploreResponse:
        graph = self._require_graph()
        center_ids = self._resolve_center_nodes(graph, params.center.strip())
        if not center_ids:
            raise ValueError(f"No graph nodes found matching '{params.center}'")

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

            is_center = node_id in center_set
            if not is_center and not self._node_passes_filters(node_data, params):
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
        edge_ids: set[str] = set()
        edges: list[GraphEdge] = []

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
                    GraphEdge(
                        id=f"{edge_key[0]}--{edge_key[1]}",
                        source=source,
                        target=target,
                        type=edge_data[EDGE_ATTR],
                    )
                )

        return GraphExploreResponse(
            center_node_ids=center_ids,
            nodes=nodes,
            edges=edges,
            stats=self.get_stats(),
            truncated=truncated,
        )

    def export_graph(self, limit: int | None = None) -> GraphExportResponse:
        graph = self._require_graph()
        node_items = list(graph.nodes(data=True))
        if limit is not None:
            node_items = node_items[:limit]

        nodes = [self._node_to_schema(node_id, data) for node_id, data in node_items]
        node_ids = {node.id for node in nodes}
        edges: list[GraphEdge] = []
        seen: set[tuple[str, str]] = set()

        for source, target, data in graph.edges(data=True):
            if source not in node_ids or target not in node_ids:
                continue
            edge_key = tuple(sorted((source, target)))
            if edge_key in seen:
                continue
            seen.add(edge_key)
            edges.append(
                GraphEdge(
                    id=f"{edge_key[0]}--{edge_key[1]}",
                    source=source,
                    target=target,
                    type=data[EDGE_ATTR],
                )
            )

        return GraphExportResponse(
            backend="networkx",
            nodes=nodes,
            edges=edges,
            stats=self.get_stats(),
        )

    def _require_graph(self) -> nx.Graph:
        if self._graph is None:
            raise RuntimeError("Knowledge graph has not been built yet")
        return self._graph

    def _resolve_center_nodes(self, graph: nx.Graph, center: str) -> list[str]:
        normalized = center.strip()
        if not normalized:
            return []

        direct_candidates = [
            _cert_id(normalized),
            _component_id("outdoor", normalized),
            _component_id("coil", normalized),
            _component_id("furnace", normalized),
        ]
        matches = [node_id for node_id in direct_candidates if graph.has_node(node_id)]
        if matches:
            return matches

        lowered = normalized.lower()
        partial: list[str] = []
        for node_id, data in graph.nodes(data=True):
            label = str(data.get("label", "")).lower()
            if lowered in label or lowered in node_id.lower():
                partial.append(node_id)

        return sorted(set(partial))[:5]

    def _node_passes_filters(self, node_data: dict[str, Any], params: GraphExploreRequest) -> bool:
        node_type = node_data.get("type")
        properties = node_data.get("properties") or {}

        if node_type != "certification":
            return True

        if params.active_only and properties.get("model_status") not in (None, "Active"):
            return False
        if params.equipment_category and properties.get("equipment_category") != params.equipment_category:
            return False
        if params.refrigerant_type and properties.get("refrigerant_type") != params.refrigerant_type:
            return False
        return True

    def _node_to_schema(self, node_id: str, node_data: dict[str, Any]) -> GraphNode:
        return GraphNode(
            id=node_id,
            label=str(node_data.get("label", node_id)),
            type=node_data["type"],
            properties=dict(node_data.get("properties") or {}),
        )


class KnowledgeGraphStore:
    def __init__(self) -> None:
        self._networkx = NetworkxGraphStore()
        self._backend: str = "networkx"

    @property
    def backend(self) -> str:
        return self._backend

    @property
    def is_ready(self) -> bool:
        if self._backend == "neo4j":
            return neo4j_graph_store.is_ready()
        return self._networkx.is_ready

    def connect_neo4j(self) -> bool:
        if neo4j_client.connect():
            self._backend = "neo4j"
            return True
        self._backend = "networkx"
        return False

    def rebuild(self, db: Session) -> GraphStats:
        systems = db.query(HvacSystem).all()
        networkx_stats = self._networkx.rebuild_from_systems(systems)

        if neo4j_client.enabled and neo4j_client.is_connected:
            return neo4j_graph_store.sync_systems(systems)

        if neo4j_client.enabled:
            connected = self.connect_neo4j()
            if connected:
                return neo4j_graph_store.sync_systems(systems)

        self._backend = "networkx"
        return networkx_stats

    def get_stats(self) -> GraphStats:
        if self._backend == "neo4j" and neo4j_graph_store.is_ready():
            return neo4j_graph_store.get_stats()
        return self._networkx.get_stats()

    def explore(self, params: GraphExploreRequest) -> GraphExploreResponse:
        if self._backend == "neo4j" and neo4j_graph_store.is_ready():
            return neo4j_graph_store.explore(params)
        return self._networkx.explore(params)

    def export_graph(self, limit: int | None = None) -> GraphExportResponse:
        if self._backend == "neo4j" and neo4j_graph_store.is_ready():
            return neo4j_graph_store.export_graph(limit=limit)
        return self._networkx.export_graph(limit=limit)


graph_store = KnowledgeGraphStore()
