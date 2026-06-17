from sqlalchemy.orm import Session

from app.schemas.hvac import HvacSearchRequest
from app.schemas.recommendations import (
    HvacRecommendation,
    HvacRecommendationRequest,
    HvacRecommendationResponse,
)
from app.services.hvac_search import _apply_filters, system_to_schema
from app.services.scoring import normalize_recommendation_scores
from app.models.hvac_system import HvacSystem


def _score_system(system: HvacSystem, request: HvacRecommendationRequest) -> tuple[float, str]:
    score = 0.0
    reasons: list[str] = []

    if request.tonnage is not None and system.tonnage == request.tonnage:
        score += 30
        reasons.append(f"matches {request.tonnage} ton")

    if request.min_seer is not None and system.seer is not None and system.seer >= request.min_seer:
        score += 20
        reasons.append(f"SEER {system.seer} >= {request.min_seer}")

    if request.config and system.config and request.config.lower() in system.config.lower():
        score += 15
        reasons.append(f"config: {system.config}")

    if (
        request.system_type_seer2
        and system.system_type_seer2
        and request.system_type_seer2.lower() in system.system_type_seer2.lower()
    ):
        score += 15
        reasons.append(f"SEER2 type: {system.system_type_seer2}")

    if request.stage and system.stage and request.stage.lower() in system.stage.lower():
        score += 10
        reasons.append(f"stage: {system.stage}")

    if request.indoor_unit and system.indoor_unit and request.indoor_unit.lower() in system.indoor_unit.lower():
        score += 5
        reasons.append(f"indoor: {system.indoor_unit}")

    if request.furnace_btu and system.furnace_btu == request.furnace_btu:
        score += 5
        reasons.append(f"furnace BTU: {system.furnace_btu}")

    if request.query and system.search_text:
        query_lower = request.query.lower()
        matches = sum(
            1
            for token in query_lower.split()
            if token and token in system.search_text.lower()
        )
        if matches:
            score += min(matches * 3, 15)
            reasons.append(f"matches query terms ({matches})")

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
        config=request.config,
        system_type_seer2=request.system_type_seer2,
        stage=request.stage,
        indoor_unit=request.indoor_unit,
        furnace_btu=request.furnace_btu,
        query=request.query,
        active_only=True,
        page=1,
        limit=500,
    )

    query = db.query(HvacSystem)
    query = _apply_filters(query, search_params)
    candidates = query.all()

    ranked: list[HvacRecommendation] = []
    for system in candidates:
        score, reason = _score_system(system, request)
        ranked.append(
            HvacRecommendation(
                system=system_to_schema(system),
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
