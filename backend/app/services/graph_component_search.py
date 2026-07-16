"""Component matchup search via Neo4j GraphNode traversal (no SQLite ILIKE fallback)."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.knowledge_graph.neo4j_store import neo4j_graph_store
from app.knowledge_graph.store import graph_store
from app.models.hvac_system import HvacSystem
from app.schemas.component_search import ComponentSearchRequest, ComponentSearchResponse
from app.schemas.recommendations import HvacRecommendation
from app.services.component_search import (
    _build_bought_together,
    _build_matchup_reason,
    _component_models,
    _detect_matched_type,
    _model_matches,
    _resolve_matched_type,
    _score_matchup,
)
from app.services.hvac_search import system_to_schema
from app.services.product_images import load_sku_image_map
from app.services.scoring import normalize_recommendation_scores


class GraphSearchUnavailableError(RuntimeError):
    """Raised when Neo4j GraphNode backend is required but not connected."""


def graph_search_is_ready() -> bool:
    return graph_store.backend == "neo4j" and neo4j_graph_store.is_ready()


def search_by_component_graph(
    db: Session, request: ComponentSearchRequest
) -> ComponentSearchResponse:
    if not graph_search_is_ready():
        raise GraphSearchUnavailableError(
            "Neo4j product graph is not available. Start Neo4j and re-sync the graph."
        )

    query = request.model.strip()
    graph_matches = neo4j_graph_store.search_components(request)
    if not graph_matches:
        return ComponentSearchResponse(
            query=query,
            matched_type=None,
            matched_model=None,
            similar_matchups=[],
            bought_together=[],
            meta={
                "total_matchups": 0,
                "offset": request.offset,
                "limit": request.limit,
                "returned": 0,
                "has_more": False,
                "component_type": request.component_type,
                "backend": "neo4j",
            },
        )

    system_ids = [int(row["system_id"]) for row in graph_matches if row.get("system_id") is not None]
    systems = db.query(HvacSystem).filter(HvacSystem.id.in_(system_ids)).all()
    systems_by_id = {system.id: system for system in systems}

    ordered_systems: list[HvacSystem] = []
    for system_id in system_ids:
        system = systems_by_id.get(system_id)
        if system is not None:
            ordered_systems.append(system)

    matched_type: str | None
    if request.component_type == "auto":
        type_counts: dict[str, int] = defaultdict(int)
        for system in ordered_systems:
            detected = _detect_matched_type(query, system, request.equipment_category)
            if detected:
                type_counts[detected] += 1
        matched_type = _resolve_matched_type(type_counts, request.equipment_category)
    else:
        matched_type = request.component_type

    matched_model: str | None = None
    if matched_type and ordered_systems:
        for system in ordered_systems:
            model = _component_models(system)[matched_type]
            if _model_matches(query, model):
                matched_model = model
                break

    sku_images = load_sku_image_map(db)
    ranked: list[HvacRecommendation] = []
    for system in ordered_systems:
        system_match_type = (
            _detect_matched_type(query, system, request.equipment_category)
            if request.component_type == "auto"
            else matched_type
        )
        system_match_model = (
            _component_models(system).get(system_match_type) if system_match_type else None
        )
        if system_match_model and not _model_matches(query, system_match_model):
            system_match_model = None

        reason = _build_matchup_reason(system_match_type, system_match_model, system)
        score = _score_matchup(
            system,
            query,
            system_match_type,
            request.prefer_higher_seer,
            request.equipment_category,
        )
        ranked.append(
            HvacRecommendation(
                system=system_to_schema(system, sku_images),
                score=score,
                reason=reason,
            )
        )

    ranked.sort(key=lambda item: item.score, reverse=True)
    ranked = normalize_recommendation_scores(ranked)
    page = ranked[request.offset : request.offset + request.limit]
    bought_together = _build_bought_together(ordered_systems, matched_type, sku_images=sku_images)

    return ComponentSearchResponse(
        query=query,
        matched_type=matched_type,
        matched_model=matched_model,
        similar_matchups=page,
        bought_together=bought_together,
        meta={
            "total_matchups": len(ranked),
            "offset": request.offset,
            "limit": request.limit,
            "returned": len(page),
            "has_more": request.offset + len(page) < len(ranked),
            "component_type": request.component_type,
            "backend": "neo4j",
        },
    )
