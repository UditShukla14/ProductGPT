from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.knowledge_graph.builder import (
    CYPHER_REL_TO_EDGE,
    GraphElementEdge,
    GraphElementNode,
    REL_TYPE_MAP,
    _cert_id,
    _component_id,
    extract_graph_elements,
)
from app.knowledge_graph.neo4j_client import neo4j_client
from app.models.hvac_system import HvacSystem
from app.services.product_images import load_sku_image_map
from app.services.width_resolution import normalize_width
from app.schemas.component_search import ComponentSearchRequest
from app.schemas.knowledge_graph import (
    GraphEdge,
    GraphExploreRequest,
    GraphExploreResponse,
    GraphExportResponse,
    GraphNode,
    GraphStats,
)

BATCH_SIZE = 2_000

COMPONENT_REL_TYPES = ("HAS_OUTDOOR", "HAS_COIL", "HAS_FURNACE")

SCHEMA_QUERIES = [
    "CREATE CONSTRAINT graph_node_id IF NOT EXISTS FOR (n:GraphNode) REQUIRE n.id IS UNIQUE",
    "CREATE INDEX graph_node_type IF NOT EXISTS FOR (n:GraphNode) ON (n.type)",
    "CREATE INDEX graph_node_label IF NOT EXISTS FOR (n:GraphNode) ON (n.label)",
]


def _flatten_properties(properties: dict[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in properties.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            flat[key] = value
        else:
            flat[key] = str(value)
    return flat


def _node_record(node: GraphElementNode) -> dict[str, Any]:
    return {
        "id": node.id,
        "label": node.label,
        "type": node.type,
        **_flatten_properties(node.properties),
    }


class Neo4jGraphStore:
    def is_ready(self) -> bool:
        return neo4j_client.is_connected

    def ensure_schema(self) -> None:
        with neo4j_client.session() as session:
            for query in SCHEMA_QUERIES:
                session.run(query)

    def clear(self) -> None:
        with neo4j_client.session() as session:
            session.run("MATCH (n:GraphNode) DETACH DELETE n")

    def sync_systems(
        self,
        systems: list[HvacSystem],
        model_images: dict[str, str] | None = None,
    ) -> GraphStats:
        nodes, edges = extract_graph_elements(systems, model_images=model_images)
        self.ensure_schema()
        self.clear()
        self._write_nodes(nodes)
        self._write_edges(edges)
        return self.get_stats()

    def rebuild(self, db: Session) -> GraphStats:
        systems = db.query(HvacSystem).all()
        model_images = load_sku_image_map(db)
        return self.sync_systems(systems, model_images=model_images)

    def _write_nodes(self, nodes: list[GraphElementNode]) -> None:
        query = """
        UNWIND $rows AS row
        MERGE (n:GraphNode {id: row.id})
        SET n.label = row.label,
            n.type = row.type,
            n += row.props
        """
        with neo4j_client.session() as session:
            for offset in range(0, len(nodes), BATCH_SIZE):
                batch = nodes[offset : offset + BATCH_SIZE]
                rows = [
                    {
                        "id": node.id,
                        "label": node.label,
                        "type": node.type,
                        "props": _flatten_properties(node.properties),
                    }
                    for node in batch
                ]
                session.run(query, rows=rows)

    def _write_edges(self, edges: list[GraphElementEdge]) -> None:
        edges_by_type: dict[str, list[dict[str, str]]] = {}
        for edge in edges:
            rel_type = REL_TYPE_MAP[edge.type]
            edges_by_type.setdefault(rel_type, []).append(
                {"source": edge.source, "target": edge.target}
            )

        with neo4j_client.session() as session:
            for rel_type, rels in edges_by_type.items():
                query = f"""
                UNWIND $rows AS row
                MATCH (source:GraphNode {{id: row.source}})
                MATCH (target:GraphNode {{id: row.target}})
                MERGE (source)-[:{rel_type}]->(target)
                """
                for offset in range(0, len(rels), BATCH_SIZE):
                    session.run(query, rows=rels[offset : offset + BATCH_SIZE])

    def get_stats(self) -> GraphStats:
        with neo4j_client.session() as session:
            node_rows = session.run(
                "MATCH (n:GraphNode) RETURN n.type AS type, count(*) AS count"
            ).data()
            edge_rows = session.run(
                "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count"
            ).data()

        nodes_by_type = {row["type"]: row["count"] for row in node_rows}
        edges_by_type = {
            CYPHER_REL_TO_EDGE.get(row["type"], row["type"]): row["count"] for row in edge_rows
        }
        component_count = (
            nodes_by_type.get("outdoor", 0)
            + nodes_by_type.get("coil", 0)
            + nodes_by_type.get("furnace", 0)
        )
        node_count = sum(nodes_by_type.values())
        edge_count = sum(row["count"] for row in edge_rows)

        return GraphStats(
            node_count=node_count,
            edge_count=edge_count,
            nodes_by_type=nodes_by_type,
            edges_by_type=edges_by_type,
            certification_count=nodes_by_type.get("certification", 0),
            component_count=component_count,
        )

    def explore(self, params: GraphExploreRequest) -> GraphExploreResponse:
        center_ids = self._resolve_center_nodes(params.center.strip())
        if not center_ids:
            raise ValueError(f"No graph nodes found matching '{params.center}'")

        depth = params.depth
        query = f"""
        MATCH (start:GraphNode)
        WHERE start.id IN $center_ids
        MATCH (start)-[*0..{depth}]-(n:GraphNode)
        RETURN DISTINCT n
        LIMIT $max_nodes
        """
        with neo4j_client.session() as session:
            node_records = session.run(
                query,
                center_ids=center_ids,
                max_nodes=params.max_nodes,
            ).data()

        nodes: list[GraphNode] = []
        node_ids: list[str] = []
        for record in node_records:
            neo_node = record["n"]
            node = self._neo4j_node_to_schema(neo_node)
            if not self._node_passes_filters(node, params, center_ids):
                continue
            nodes.append(node)
            node_ids.append(node.id)

        if len(node_records) >= params.max_nodes:
            truncated = True
        else:
            truncated = False

        edges = self._fetch_edges_for_nodes(node_ids)
        return GraphExploreResponse(
            center_node_ids=center_ids,
            nodes=nodes,
            edges=edges,
            stats=self.get_stats(),
            truncated=truncated,
        )

    def export_graph(self, limit: int | None = None) -> GraphExportResponse:
        node_query = "MATCH (n:GraphNode) RETURN n"
        if limit is not None:
            node_query += " LIMIT $limit"

        with neo4j_client.session() as session:
            node_records = session.run(node_query, limit=limit).data() if limit else session.run(node_query).data()
            nodes = [self._neo4j_node_to_schema(record["n"]) for record in node_records]
            node_ids = [node.id for node in nodes]

            if not node_ids:
                return GraphExportResponse(
                    backend="neo4j",
                    nodes=[],
                    edges=[],
                    stats=self.get_stats(),
                )

            edge_records = session.run(
                """
                MATCH (a:GraphNode)-[r]->(b:GraphNode)
                WHERE a.id IN $node_ids AND b.id IN $node_ids
                RETURN a.id AS source, type(r) AS rel_type, b.id AS target
                """,
                node_ids=node_ids,
            ).data()

        edges: list[GraphEdge] = []
        for record in edge_records:
            edge_type = CYPHER_REL_TO_EDGE.get(record["rel_type"])
            if edge_type is None:
                continue
            source = record["source"]
            target = record["target"]
            edges.append(
                GraphEdge(
                    id=f"{source}--{target}",
                    source=source,
                    target=target,
                    type=edge_type,
                )
            )

        return GraphExportResponse(
            backend="neo4j",
            nodes=nodes,
            edges=edges,
            stats=self.get_stats(),
        )

    def _fetch_edges_for_nodes(self, node_ids: list[str]) -> list[GraphEdge]:
        if not node_ids:
            return []

        with neo4j_client.session() as session:
            records = session.run(
                """
                MATCH (a:GraphNode)-[r]->(b:GraphNode)
                WHERE a.id IN $node_ids AND b.id IN $node_ids
                RETURN a.id AS source, type(r) AS rel_type, b.id AS target
                """,
                node_ids=node_ids,
            ).data()

        edges: list[GraphEdge] = []
        for record in records:
            edge_type = CYPHER_REL_TO_EDGE.get(record["rel_type"])
            if edge_type is None:
                continue
            source = record["source"]
            target = record["target"]
            edges.append(
                GraphEdge(
                    id=f"{source}--{target}",
                    source=source,
                    target=target,
                    type=edge_type,
                )
            )
        return edges

    def _resolve_center_nodes(self, center: str) -> list[str]:
        normalized = center.strip()
        if not normalized:
            return []

        direct_candidates = [
            _cert_id(normalized),
            _component_id("outdoor", normalized),
            _component_id("coil", normalized),
            _component_id("furnace", normalized),
        ]

        with neo4j_client.session() as session:
            found = session.run(
                """
                MATCH (n:GraphNode)
                WHERE n.id IN $ids
                RETURN n.id AS id
                """,
                ids=direct_candidates,
            ).data()
            if found:
                return [row["id"] for row in found]

            partial = session.run(
                """
                MATCH (n:GraphNode)
                WHERE toLower(n.label) CONTAINS toLower($term)
                   OR toLower(n.id) CONTAINS toLower($term)
                RETURN n.id AS id
                LIMIT 5
                """,
                term=normalized,
            ).data()

        return [row["id"] for row in partial]

    def search_components(self, request: ComponentSearchRequest) -> list[dict[str, Any]]:
        """Find AHRI certification matchups via GraphNode component traversal."""
        term = request.model.strip()
        if not term:
            return []

        component_types = (
            [request.component_type]
            if request.component_type != "auto"
            else ["outdoor", "coil", "furnace"]
        )

        filters: list[str] = ["toLower(coalesce(cert.model_status, 'Active')) = 'active'"]
        params: dict[str, Any] = {"term": term, "component_types": component_types}

        if request.equipment_category:
            filters.append("cert.equipment_category = $equipment_category")
            params["equipment_category"] = request.equipment_category.strip()
        if request.refrigerant_type:
            filters.append("cert.refrigerant_type = $refrigerant_type")
            params["refrigerant_type"] = request.refrigerant_type.strip()
        if request.flow:
            filters.append("toLower(cert.indoor_type) = $flow")
            params["flow"] = request.flow.strip().lower()
        if request.coil_width:
            normalized = normalize_width(request.coil_width)
            if normalized:
                filters.append("cert.coil_width = $coil_width")
                params["coil_width"] = normalized
        if request.furnace_width:
            normalized = normalize_width(request.furnace_width)
            if normalized:
                filters.append("cert.furnace_width = $furnace_width")
                params["furnace_width"] = normalized

        filter_clause = " AND ".join(filters)
        query = f"""
        MATCH (comp:GraphNode)
        WHERE comp.type IN $component_types
          AND (
            toLower(comp.label) CONTAINS toLower($term)
            OR toLower(comp.id) CONTAINS toLower($term)
          )
        MATCH (cert:GraphNode {{type: 'certification'}})-[rel]->(comp)
        WHERE type(rel) IN {list(COMPONENT_REL_TYPES)}
          AND {filter_clause}
        OPTIONAL MATCH (cert)-[:HAS_OUTDOOR]->(outdoor:GraphNode)
        OPTIONAL MATCH (cert)-[:HAS_COIL]->(coil:GraphNode)
        OPTIONAL MATCH (cert)-[:HAS_FURNACE]->(furnace:GraphNode)
        RETURN
            cert.system_id AS system_id,
            comp.type AS matched_type,
            comp.label AS matched_model,
            outdoor.label AS outdoor_model,
            coil.label AS coil_model,
            furnace.label AS furnace_model,
            cert.seer AS seer
        ORDER BY cert.seer DESC, cert.ahri_number ASC
        """

        with neo4j_client.session() as session:
            rows = session.run(query, **params).data()

        deduped: dict[int, dict[str, Any]] = {}
        for row in rows:
            system_id = row.get("system_id")
            if system_id is None:
                continue
            system_id = int(system_id)
            existing = deduped.get(system_id)
            if existing is None:
                deduped[system_id] = row
                continue
            existing_seer = existing.get("seer") or 0
            row_seer = row.get("seer") or 0
            if row_seer > existing_seer:
                deduped[system_id] = row

        return list(deduped.values())

    def _neo4j_node_to_schema(self, neo_node: Any) -> GraphNode:
        props = dict(neo_node)
        node_id = props.pop("id")
        label = props.pop("label", node_id)
        node_type = props.pop("type")
        return GraphNode(id=node_id, label=label, type=node_type, properties=props)

    def _node_passes_filters(
        self, node: GraphNode, params: GraphExploreRequest, center_ids: list[str]
    ) -> bool:
        if node.id in center_ids:
            return True
        if node.type != "certification":
            return True

        props = node.properties
        if params.active_only and props.get("model_status") not in (None, "Active"):
            return False
        if params.equipment_category and props.get("equipment_category") != params.equipment_category:
            return False
        if params.refrigerant_type and props.get("refrigerant_type") != params.refrigerant_type:
            return False
        return True


neo4j_graph_store = Neo4jGraphStore()
