from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.recommendations import HvacRecommendationRequest, HvacRecommendationResponse
from app.services.recommender import recommend_hvac_systems

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/hvac", response_model=HvacRecommendationResponse)
def recommend_hvac(
    payload: HvacRecommendationRequest, db: Session = Depends(get_db)
) -> HvacRecommendationResponse:
    return recommend_hvac_systems(db, payload)
