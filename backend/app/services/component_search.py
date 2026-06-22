from collections import defaultdict

from sqlalchemy import Float, cast, func, or_
from sqlalchemy.orm import Session

from app.models.hvac_system import HvacSystem
from app.services.product_images import load_sku_image_map, normalize_sku
from app.schemas.component_search import (
    BoughtTogetherItem,
    ComponentSearchRequest,
    ComponentSearchResponse,
    PairedMatchupsRequest,
    PairedMatchupsResponse,
)
from app.schemas.recommendations import HvacRecommendation
from app.services.hvac_search import system_to_schema
from app.services.scoring import normalize_recommendation_scores
from app.services.width_resolution import normalize_width

COMPONENT_TYPES = ("outdoor", "coil", "furnace")
HEAT_PUMP_CATEGORIES = frozenset({"Heat Pump", "Package Heat Pump"})


def _component_preference_order(equipment_category: str | None) -> tuple[str, ...]:
    if equipment_category in HEAT_PUMP_CATEGORIES:
        return ("coil", "outdoor", "furnace")
    return COMPONENT_TYPES


def _resolve_matched_type(type_counts: dict[str, int], equipment_category: str | None) -> str | None:
    if not type_counts:
        return None
    preference = _component_preference_order(equipment_category)
    return max(
        type_counts,
        key=lambda component_type: (
            type_counts[component_type],
            -preference.index(component_type),
        ),
    )


def _outdoor_model(system: HvacSystem) -> str | None:
    value = (system.outdoor_model_revision or system.outdoor_model or "").strip()
    return value or None


def _coil_model(system: HvacSystem) -> str | None:
    value = (system.coil_model_revision or system.coil_model_number or "").strip()
    return value or None


def _furnace_model(system: HvacSystem) -> str | None:
    value = (system.furnace_model_revision or "").strip()
    return value or None


def _component_models(system: HvacSystem) -> dict[str, str | None]:
    return {
        "outdoor": _outdoor_model(system),
        "coil": _coil_model(system),
        "furnace": _furnace_model(system),
    }


def _model_matches(query: str, model: str | None) -> bool:
    if not model:
        return False
    return query.lower() in model.lower()


def _detect_matched_type(
    query: str, system: HvacSystem, equipment_category: str | None = None
) -> str | None:
    models = _component_models(system)
    for component_type in _component_preference_order(equipment_category):
        if _model_matches(query, models[component_type]):
            return component_type
    return None


def _filter_by_component(query: str, component_type: str):
    term = f"%{query.strip()}%"
    if component_type == "outdoor":
        return or_(
            HvacSystem.outdoor_model.ilike(term),
            HvacSystem.outdoor_model_revision.ilike(term),
        )
    if component_type == "coil":
        return or_(
            HvacSystem.coil_model_number.ilike(term),
            HvacSystem.coil_model_revision.ilike(term),
        )
    return HvacSystem.furnace_model_revision.ilike(term)


def _apply_goodman_filters(
    query,
    equipment_category: str | None,
    refrigerant_type: str | None,
    flow: str | None = None,
    coil_width: str | None = None,
    furnace_width: str | None = None,
):
    if equipment_category:
        query = query.filter(HvacSystem.equipment_category == equipment_category.strip())
    if refrigerant_type:
        query = query.filter(HvacSystem.refrigerant_type == refrigerant_type.strip())
    if flow:
        query = query.filter(func.lower(HvacSystem.indoor_type) == flow.strip().lower())
    if coil_width:
        normalized = normalize_width(coil_width)
        if normalized:
            query = query.filter(HvacSystem.coil_width == normalized)
    if furnace_width:
        normalized = normalize_width(furnace_width)
        if normalized:
            query = query.filter(HvacSystem.furnace_width == normalized)
    return query


def _build_matchup_reason(
    matched_type: str | None, matched_model: str | None, system: HvacSystem
) -> str:
    models = _component_models(system)
    parts: list[str] = []
    if matched_type and matched_model:
        label = "air handler" if matched_type == "coil" else matched_type
        parts.append(f"includes your {label} model {matched_model}")
    for component_type in COMPONENT_TYPES:
        model = models[component_type]
        if model:
            parts.append(f"{component_type}: {model}")
    if system.seer is not None:
        parts.append(f"SEER {system.seer}")
    if system.tonnage is not None:
        parts.append(f"{system.tonnage} ton")
    return "; ".join(parts)


def _score_matchup(
    system: HvacSystem,
    query: str,
    matched_type: str | None,
    prefer_higher_seer: bool,
    equipment_category: str | None = None,
) -> float:
    score = 50.0
    models = _component_models(system)

    if matched_type and models[matched_type]:
        model = models[matched_type]
        if model.lower() == query.lower():
            score += 30
        elif model.lower().startswith(query.lower()):
            score += 20
        else:
            score += 10

        if equipment_category in HEAT_PUMP_CATEGORIES and matched_type == "coil":
            score += 15

    if prefer_higher_seer and system.seer is not None:
        score += min(system.seer, 20)

    if system.tonnage is not None:
        score += min(system.tonnage * 2, 10)

    return round(score, 2)


def _build_bought_together(
    systems: list[HvacSystem],
    matched_type: str | None,
    sku_images: dict[str, str] | None = None,
) -> list[BoughtTogetherItem]:
    sku_images = sku_images or {}
    aggregates: dict[str, dict[str, dict]] = {
        component_type: defaultdict(
            lambda: {"count": 0, "best_seer": None, "sample_system_id": None}
        )
        for component_type in COMPONENT_TYPES
    }

    for system in systems:
        models = _component_models(system)
        for component_type, model in models.items():
            if component_type == matched_type or not model:
                continue
            entry = aggregates[component_type][model]
            entry["count"] += 1
            if system.seer is not None and (
                entry["best_seer"] is None or system.seer > entry["best_seer"]
            ):
                entry["best_seer"] = system.seer
                entry["sample_system_id"] = system.id
            elif entry["sample_system_id"] is None:
                entry["sample_system_id"] = system.id

    items: list[BoughtTogetherItem] = []
    for component_type in COMPONENT_TYPES:
        if component_type == matched_type:
            continue
        for model, stats in aggregates[component_type].items():
            sku = normalize_sku(model)
            items.append(
                BoughtTogetherItem(
                    type=component_type,
                    model=model,
                    matchup_count=stats["count"],
                    best_seer=stats["best_seer"],
                    sample_system_id=stats["sample_system_id"],
                    image_url=sku_images.get(sku) if sku else None,
                )
            )

    items.sort(key=lambda item: (-item.matchup_count, -(item.best_seer or 0), item.model))
    return items


def search_by_component(
    db: Session, request: ComponentSearchRequest
) -> ComponentSearchResponse:
    query = request.model.strip()
    base_query = db.query(HvacSystem).filter(
        func.lower(HvacSystem.model_status) == "active"
    )
    base_query = _apply_goodman_filters(
        base_query,
        request.equipment_category,
        request.refrigerant_type,
        request.flow,
        request.coil_width,
        request.furnace_width,
    )

    if request.component_type == "auto":
        base_query = base_query.filter(
            or_(
                _filter_by_component(query, "outdoor"),
                _filter_by_component(query, "coil"),
                _filter_by_component(query, "furnace"),
            )
        )
        matched_type: str | None = None
    else:
        matched_type = request.component_type
        base_query = base_query.filter(_filter_by_component(query, matched_type))

    systems = (
        base_query.order_by(
            cast(HvacSystem.seer, Float).desc().nullslast(),
            HvacSystem.ahri_number,
        )
        .all()
    )

    if request.component_type == "auto" and systems:
        type_counts: dict[str, int] = defaultdict(int)
        for system in systems:
            detected = _detect_matched_type(query, system, request.equipment_category)
            if detected:
                type_counts[detected] += 1
        matched_type = _resolve_matched_type(type_counts, request.equipment_category)

    matched_model: str | None = None
    if matched_type and systems:
        for system in systems:
            model = _component_models(system)[matched_type]
            if _model_matches(query, model):
                matched_model = model
                break

    sku_images = load_sku_image_map(db)

    ranked: list[HvacRecommendation] = []
    for system in systems:
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
    bought_together = _build_bought_together(systems, matched_type, sku_images=sku_images)

    meta = {
        "total_matchups": len(ranked),
        "offset": request.offset,
        "limit": request.limit,
        "returned": len(page),
        "has_more": request.offset + len(page) < len(ranked),
        "component_type": request.component_type,
    }

    return ComponentSearchResponse(
        query=query,
        matched_type=matched_type,
        matched_model=matched_model,
        similar_matchups=page,
        bought_together=bought_together,
        meta=meta,
    )


def search_paired_matchups(
    db: Session, request: PairedMatchupsRequest
) -> PairedMatchupsResponse:
    base_query = db.query(HvacSystem).filter(
        func.lower(HvacSystem.model_status) == "active",
        _filter_by_component(request.anchor_model, request.anchor_type),
        _filter_by_component(request.paired_model, request.paired_type),
    )
    base_query = _apply_goodman_filters(
        base_query,
        request.equipment_category,
        request.refrigerant_type,
        request.flow,
        request.coil_width,
        request.furnace_width,
    )

    systems = (
        base_query.order_by(
            cast(HvacSystem.seer, Float).desc().nullslast(),
            HvacSystem.ahri_number,
        )
        .all()
    )

    sku_images = load_sku_image_map(db)

    ranked: list[HvacRecommendation] = []
    for system in systems:
        reason = _build_matchup_reason(
            request.anchor_type,
            request.anchor_model,
            system,
        )
        score = _score_matchup(
            system,
            request.anchor_model,
            request.anchor_type,
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

    meta = {
        "total_matchups": len(ranked),
        "offset": request.offset,
        "limit": request.limit,
        "returned": len(page),
        "has_more": request.offset + len(page) < len(ranked),
    }

    return PairedMatchupsResponse(
        anchor_type=request.anchor_type,
        anchor_model=request.anchor_model,
        paired_type=request.paired_type,
        paired_model=request.paired_model,
        matchups=page,
        meta=meta,
    )
