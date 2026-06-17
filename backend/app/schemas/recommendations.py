from pydantic import BaseModel, Field

from app.schemas.hvac import HvacSystemOut


class HvacRecommendationRequest(BaseModel):
    tonnage: float | None = None
    min_seer: float | None = None
    max_seer: float | None = None
    config: str | None = None
    system_type_seer2: str | None = None
    stage: str | None = None
    indoor_unit: str | None = None
    furnace_btu: str | None = None
    query: str | None = Field(default=None, description="Natural language hints for ranking")
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    prefer_higher_seer: bool = True


class HvacRecommendation(BaseModel):
    system: HvacSystemOut
    score: float
    reason: str


class HvacRecommendationResponse(BaseModel):
    recommendations: list[HvacRecommendation]
    meta: dict
