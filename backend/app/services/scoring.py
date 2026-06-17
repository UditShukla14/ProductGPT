from app.schemas.recommendations import HvacRecommendation


def normalize_recommendation_scores(
    recommendations: list[HvacRecommendation],
) -> list[HvacRecommendation]:
    """Scale raw scores to 0–100 relative to the ranked result set."""
    if not recommendations:
        return recommendations

    scores = [item.score for item in recommendations]
    min_score = min(scores)
    max_score = max(scores)

    if min_score == max_score:
        return [item.model_copy(update={"score": 100.0}) for item in recommendations]

    normalized: list[HvacRecommendation] = []
    for item in recommendations:
        scaled = ((item.score - min_score) / (max_score - min_score)) * 100
        normalized.append(item.model_copy(update={"score": round(scaled, 1)}))

    return normalized
