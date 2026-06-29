from sqlalchemy.orm import Session

from app.schemas.hvac import HvacSearchRequest
from app.schemas.recommendations import (
    HvacRecommendation,
    HvacRecommendationRequest,
    HvacRecommendationResponse,
)
from app.services.hvac_search import _apply_filters, system_to_schema
from app.services.product_images import load_sku_image_map
from app.services.scoring import normalize_recommendation_scores
from app.services.width_resolution import normalize_width
from app.models.hvac_system import HvacSystem


def _score_system(system: HvacSystem, request: HvacRecommendationRequest) -> tuple[float, str]:
    score = 0.0
    reasons: list[str] = []

    if request.tonnage is not None and system.tonnage == request.tonnage:
        score += 30
        reasons.append(f"matches {request.tonnage} ton")

    if request.min_seer is not None and system.seer is not None and system.seer >= request.min_seer:
        score += 20
        reasons.append(f"SEER2 {system.seer} >= {request.min_seer}")

    if (
        request.equipment_category
        and system.equipment_category
        and request.equipment_category == system.equipment_category
    ):
        score += 15
        reasons.append(f"category: {system.equipment_category}")

    if (
        request.refrigerant_type
        and system.refrigerant_type
        and request.refrigerant_type == system.refrigerant_type
    ):
        score += 15
        reasons.append(f"refrigerant: {system.refrigerant_type}")

    if (
        request.flow
        and system.indoor_type
        and request.flow.lower() == system.indoor_type.lower()
    ):
        score += 15
        reasons.append(f"flow: {system.indoor_type}")

    if request.coil_width and system.coil_width:
        requested_coil_width = normalize_width(request.coil_width)
        if requested_coil_width and requested_coil_width == system.coil_width:
            score += 10
            reasons.append(f"coil width: {system.coil_width}\"")

    if request.furnace_width and system.furnace_width:
        requested_furnace_width = normalize_width(request.furnace_width)
        if requested_furnace_width and requested_furnace_width == system.furnace_width:
            score += 10
            reasons.append(f"furnace width: {system.furnace_width}\"")

    if request.prefer_higher_seer and system.seer is not None:
        score += min(system.seer, 20)

    if not reasons:
        reasons.append("matches base HVAC compatibility filters")

    return score, "; ".join(reasons)


def recommend_hvac_systems(
    db: Session, request: HvacRecommendationRequest
) -> HvacRecommendationResponse:
    search_params = HvacSearchRequest(
        tonnage=request.tonnage,
        min_seer=request.min_seer,
        max_seer=request.max_seer,
        equipment_category=request.equipment_category,
        refrigerant_type=request.refrigerant_type,
        flow=request.flow,
        coil_width=request.coil_width,
        furnace_width=request.furnace_width,
        active_only=True,
        page=1,
        limit=500,
    )

    query = db.query(HvacSystem)
    query = _apply_filters(query, search_params)
    candidates = query.all()
    sku_images = load_sku_image_map(db)

    ranked: list[HvacRecommendation] = []
    for system in candidates:
        score, reason = _score_system(system, request)
        ranked.append(
            HvacRecommendation(
                system=system_to_schema(system, sku_images),
                score=round(score, 2),
                reason=reason,
            )
        )

    ranked.sort(key=lambda item: item.score, reverse=True)
    ranked = normalize_recommendation_scores(ranked)
    page = ranked[request.offset : request.offset + request.limit]
    recommendations = page

    meta = {
        "strategy_used": "constraint_scoring",
        "candidate_count": len(candidates),
        "total_ranked": len(ranked),
        "offset": request.offset,
        "limit": request.limit,
        "returned": len(recommendations),
        "has_more": request.offset + len(recommendations) < len(ranked),
        "filters_applied": request.model_dump(exclude_none=True),
    }
    return HvacRecommendationResponse(recommendations=recommendations, meta=meta)
