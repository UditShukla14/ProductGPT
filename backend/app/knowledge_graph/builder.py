from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import networkx as nx

from app.models.hvac_system import HvacSystem
from app.schemas.knowledge_graph import GraphEdgeType, GraphNodeType

EDGE_ATTR = "type"

REL_TYPE_MAP: dict[GraphEdgeType, str] = {
    "has_outdoor": "HAS_OUTDOOR",
    "has_coil": "HAS_COIL",
    "has_furnace": "HAS_FURNACE",
    "in_category": "IN_CATEGORY",
    "uses_refrigerant": "USES_REFRIGERANT",
}

CYPHER_REL_TO_EDGE: dict[str, GraphEdgeType] = {v: k for k, v in REL_TYPE_MAP.items()}


@dataclass
class GraphElementNode:
    id: str
    label: str
    type: GraphNodeType
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphElementEdge:
    source: str
    target: str
    type: GraphEdgeType


def _component_id(component_type: GraphNodeType, model: str) -> str:
    return f"{component_type}:{model}"


def _cert_id(ahri_number: str) -> str:
    return f"certification:{ahri_number}"


def _category_id(category: str) -> str:
    return f"category:{category}"


def _refrigerant_id(refrigerant: str) -> str:
    return f"refrigerant:{refrigerant}"


def _outdoor_model(system: HvacSystem) -> str | None:
    value = (system.outdoor_model_revision or system.outdoor_model or "").strip()
    return value or None


def _coil_model(system: HvacSystem) -> str | None:
    value = (system.coil_model_revision or system.coil_model_number or "").strip()
    return value or None


def _furnace_model(system: HvacSystem) -> str | None:
    value = (system.furnace_model_revision or "").strip()
    return value or None


def extract_graph_elements(systems: list[HvacSystem]) -> tuple[list[GraphElementNode], list[GraphElementEdge]]:
    nodes: dict[str, GraphElementNode] = {}
    edges: list[GraphElementEdge] = []
    edge_keys: set[tuple[str, str, GraphEdgeType]] = set()

    def add_node(node_id: str, label: str, node_type: GraphNodeType, properties: dict[str, Any] | None = None) -> None:
        if node_id not in nodes:
            nodes[node_id] = GraphElementNode(
                id=node_id,
                label=label,
                type=node_type,
                properties=properties or {},
            )

    def add_edge(source: str, target: str, edge_type: GraphEdgeType) -> None:
        key = (source, target, edge_type)
        if key in edge_keys:
            return
        edge_keys.add(key)
        edges.append(GraphElementEdge(source=source, target=target, type=edge_type))

    for system in systems:
        ahri = (system.ahri_number or "").strip()
        if not ahri:
            continue

        cert_node = _cert_id(ahri)
        cert_props: dict[str, Any] = {
            "ahri_number": ahri,
            "tonnage": system.tonnage,
            "seer": system.seer,
            "eer": system.eer,
            "hspf": system.hspf,
            "model_status": system.model_status,
            "equipment_category": system.equipment_category,
            "refrigerant_type": system.refrigerant_type,
            "system_type": system.system_type,
            "description": system.description,
            "source_row_id": system.source_row_id,
            "system_id": system.id,
        }
        add_node(cert_node, ahri, "certification", cert_props)

        outdoor = _outdoor_model(system)
        if outdoor:
            outdoor_node = _component_id("outdoor", outdoor)
            add_node(outdoor_node, outdoor, "outdoor", {"model": outdoor})
            add_edge(cert_node, outdoor_node, "has_outdoor")

        coil = _coil_model(system)
        if coil:
            coil_node = _component_id("coil", coil)
            add_node(coil_node, coil, "coil", {"model": coil})
            add_edge(cert_node, coil_node, "has_coil")

        furnace = _furnace_model(system)
        if furnace:
            furnace_node = _component_id("furnace", furnace)
            add_node(furnace_node, furnace, "furnace", {"model": furnace})
            add_edge(cert_node, furnace_node, "has_furnace")

        if system.equipment_category:
            category_node = _category_id(system.equipment_category)
            add_node(
                category_node,
                system.equipment_category,
                "category",
                {"name": system.equipment_category},
            )
            add_edge(cert_node, category_node, "in_category")

        if system.refrigerant_type:
            refrigerant_node = _refrigerant_id(system.refrigerant_type)
            add_node(
                refrigerant_node,
                system.refrigerant_type,
                "refrigerant",
                {"name": system.refrigerant_type},
            )
            add_edge(cert_node, refrigerant_node, "uses_refrigerant")

    return list(nodes.values()), edges


def build_graph_from_systems(systems: list[HvacSystem]) -> nx.Graph:
    graph = nx.Graph()
    nodes, edges = extract_graph_elements(systems)

    for node in nodes:
        graph.add_node(node.id, label=node.label, type=node.type, properties=node.properties)

    for edge in edges:
        if not graph.has_edge(edge.source, edge.target):
            graph.add_edge(edge.source, edge.target, type=edge.type)

    return graph
