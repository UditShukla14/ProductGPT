from __future__ import annotations

from collections import Counter
from typing import Any

from app.knowledge_graph.neo4j_client import neo4j_client
from app.shopify.graph.builder import (
    CYPHER_REL_TO_EDGE,
    GraphElementEdge,
    GraphElementNode,
    REL_TYPE_MAP,
    extract_graph_elements,
    load_shopify_graph_inputs,
)
from app.shopify.graph.schemas import (
    ShopifyGraphEdge,
    ShopifyGraphExploreRequest,
    ShopifyGraphExploreResponse,
    ShopifyGraphExportResponse,
    ShopifyGraphNode,
    ShopifyGraphStats,
)

BATCH_SIZE = 2_000

SCHEMA_QUERIES = [
    "CREATE CONSTRAINT shopify_node_id IF NOT EXISTS FOR (n:ShopifyNode) REQUIRE n.id IS UNIQUE",
    "CREATE INDEX shopify_node_type IF NOT EXISTS FOR (n:ShopifyNode) ON (n.type)",
    "CREATE INDEX shopify_node_label IF NOT EXISTS FOR (n:ShopifyNode) ON (n.label)",
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


class ShopifyNeo4jGraphStore:
    def is_ready(self) -> bool:
        return neo4j_client.is_connected

    def _session(self):
        return neo4j_client.session()

    def ensure_schema(self) -> None:
        with self._session() as session:
            for query in SCHEMA_QUERIES:
                session.run(query)

    def clear(self) -> None:
        with self._session() as session:
            session.run("MATCH (n:ShopifyNode) DETACH DELETE n")

    def sync_records(
        self,
        products: list[dict[str, Any]],
        customers: list[dict[str, Any]],
        orders: list[dict[str, Any]],
    ) -> ShopifyGraphStats:
        nodes, edges = extract_graph_elements(products, customers, orders)
        self.ensure_schema()
        self.clear()
        self._write_nodes(nodes)
        self._write_edges(edges)
        return self.get_stats()

    def rebuild(self) -> ShopifyGraphStats:
        products, customers, orders = load_shopify_graph_inputs()
        return self.sync_records(products, customers, orders)

    def _write_nodes(self, nodes: list[GraphElementNode]) -> None:
        query = """
        UNWIND $rows AS row
        MERGE (n:ShopifyNode {id: row.id})
        SET n.label = row.label,
            n.type = row.type,
            n += row.props
        """
        with self._session() as session:
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
        for edge in edges:
            rel_type = REL_TYPE_MAP[edge.type]
            query = f"""
            MATCH (source:ShopifyNode {{id: $source_id}})
            MATCH (target:ShopifyNode {{id: $target_id}})
            MERGE (source)-[r:{rel_type}]->(target)
            """
            with self._session() as session:
                session.run(query, source_id=edge.source, target_id=edge.target)

    def get_stats(self) -> ShopifyGraphStats:
        with self._session() as session:
            node_count = session.run("MATCH (n:ShopifyNode) RETURN count(n) AS count").single()["count"]
            edge_count = session.run("MATCH (:ShopifyNode)-[r]->(:ShopifyNode) RETURN count(r) AS count").single()[
                "count"
            ]
            nodes_by_type = Counter(
                record["type"]
                for record in session.run(
                    "MATCH (n:ShopifyNode) RETURN n.type AS type"
                )
            )
            edges_by_type = Counter(
                CYPHER_REL_TO_EDGE.get(record["rel_type"], record["rel_type"])
                for record in session.run(
                    "MATCH (:ShopifyNode)-[r]->(:ShopifyNode) RETURN type(r) AS rel_type"
                )
            )

        return ShopifyGraphStats(
            node_count=node_count,
            edge_count=edge_count,
            nodes_by_type=dict(nodes_by_type),
            edges_by_type=dict(edges_by_type),
            product_count=nodes_by_type.get("product", 0),
            customer_count=nodes_by_type.get("customer", 0),
            order_count=nodes_by_type.get("order", 0),
        )

    def explore(self, params: ShopifyGraphExploreRequest) -> ShopifyGraphExploreResponse:
        from app.shopify.graph.store import shopify_graph_store

        return shopify_graph_store._networkx.explore(params)

    def export_graph(self, limit: int | None = None) -> ShopifyGraphExportResponse:
        from app.shopify.graph.store import shopify_graph_store

        return shopify_graph_store._networkx.export_graph(limit=limit)


shopify_neo4j_graph_store = ShopifyNeo4jGraphStore()
