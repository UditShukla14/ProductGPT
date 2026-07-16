from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.knowledge_graph.neo4j_client import neo4j_client
from app.sales.graph.builder import (
    CYPHER_REL_TO_EDGE,
    GraphElementEdge,
    GraphElementNode,
    REL_TYPE_MAP,
    extract_graph_elements,
    load_sales_rows,
)
from app.sales.graph.schemas import SalesGraphStats

BATCH_SIZE = 2_000

SCHEMA_QUERIES = [
    "CREATE CONSTRAINT sales_node_id IF NOT EXISTS FOR (n:SalesNode) REQUIRE n.id IS UNIQUE",
    "CREATE INDEX sales_node_type IF NOT EXISTS FOR (n:SalesNode) ON (n.type)",
    "CREATE INDEX sales_node_label IF NOT EXISTS FOR (n:SalesNode) ON (n.label)",
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


class SalesNeo4jGraphStore:
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
            session.run("MATCH (n:SalesNode) DETACH DELETE n")

    def sync_records(self, nodes: list[GraphElementNode], edges: list[GraphElementEdge]) -> SalesGraphStats:
        self.ensure_schema()
        self.clear()
        self._write_nodes(nodes)
        self._write_edges(edges)
        return self.get_stats(line_item_count=0)

    def rebuild(self, db: Session) -> SalesGraphStats:
        rows = load_sales_rows(db)
        nodes, edges = extract_graph_elements(rows)
        stats = self.sync_records(nodes, edges)
        stats.line_item_count = len(rows)
        return stats

    def _write_nodes(self, nodes: list[GraphElementNode]) -> None:
        query = """
        UNWIND $rows AS row
        MERGE (n:SalesNode {id: row.id})
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
        # Group by relationship type for batched writes.
        by_type: dict[str, list[GraphElementEdge]] = {}
        for edge in edges:
            by_type.setdefault(edge.type, []).append(edge)

        with self._session() as session:
            for edge_type, typed_edges in by_type.items():
                rel_type = REL_TYPE_MAP[edge_type]
                query = f"""
                UNWIND $rows AS row
                MATCH (source:SalesNode {{id: row.source_id}})
                MATCH (target:SalesNode {{id: row.target_id}})
                MERGE (source)-[r:{rel_type}]->(target)
                SET r += row.props
                """
                for offset in range(0, len(typed_edges), BATCH_SIZE):
                    batch = typed_edges[offset : offset + BATCH_SIZE]
                    rows = [
                        {
                            "source_id": edge.source,
                            "target_id": edge.target,
                            "props": _flatten_properties(edge.properties),
                        }
                        for edge in batch
                    ]
                    session.run(query, rows=rows)

    def get_stats(self, *, line_item_count: int = 0) -> SalesGraphStats:
        with self._session() as session:
            node_count = session.run("MATCH (n:SalesNode) RETURN count(n) AS count").single()["count"]
            edge_count = session.run(
                "MATCH (:SalesNode)-[r]->(:SalesNode) RETURN count(r) AS count"
            ).single()["count"]
            nodes_by_type = Counter(
                record["type"]
                for record in session.run("MATCH (n:SalesNode) RETURN n.type AS type")
            )
            edges_by_type = Counter(
                CYPHER_REL_TO_EDGE.get(record["rel_type"], record["rel_type"])
                for record in session.run(
                    "MATCH (:SalesNode)-[r]->(:SalesNode) RETURN type(r) AS rel_type"
                )
            )

        return SalesGraphStats(
            node_count=node_count,
            edge_count=edge_count,
            nodes_by_type=dict(nodes_by_type),
            edges_by_type=dict(edges_by_type),
            sku_count=nodes_by_type.get("sku", 0),
            region_count=nodes_by_type.get("region", 0),
            vendor_count=nodes_by_type.get("vendor", 0),
            line_item_count=line_item_count,
        )


sales_neo4j_graph_store = SalesNeo4jGraphStore()
