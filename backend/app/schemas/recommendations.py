from pydantic import BaseModel, Field

from app.schemas.hvac import HvacSystemOut


class HvacRecommendationRequest(BaseModel):
    tonnage: float | None = None
    min_seer: float | None = None
    max_seer: float | None = None
    equipment_category: str | None = None
    refrigerant_type: str | None = None
    flow: str | None = Field(
        default=None,
        description="Coil / air-handler flow orientation: Horizontal or Vertical",
    )
    coil_width: str | None = Field(
        default=None,
        description="Evaporator coil cabinet width in inches (e.g. 18, 22, 26, 30)",
    )
    furnace_width: str | None = Field(
        default=None,
        description="Furnace cabinet width in inches (e.g. 14, 17.5, 21, 24.5)",
    )
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
