from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.recommendations import HvacRecommendation

ComponentType = Literal["outdoor", "coil", "furnace", "auto"]


class ComponentSearchRequest(BaseModel):
    model: str = Field(..., min_length=1, description="Condenser, evaporator coil, or furnace model number")
    component_type: ComponentType = Field(
        default="auto",
        description="Component to search; auto detects from model fields",
    )
    equipment_category: str | None = None
    refrigerant_type: str | None = None
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    prefer_higher_seer: bool = True


class BoughtTogetherItem(BaseModel):
    type: Literal["outdoor", "coil", "furnace"]
    model: str
    matchup_count: int
    best_seer: float | None = None
    sample_system_id: int | None = None
    image_url: str | None = None


class ComponentSearchResponse(BaseModel):
    query: str
    matched_type: Literal["outdoor", "coil", "furnace"] | None
    matched_model: str | None
    similar_matchups: list[HvacRecommendation]
    bought_together: list[BoughtTogetherItem]
    meta: dict


class PairedMatchupsRequest(BaseModel):
    anchor_type: Literal["outdoor", "coil", "furnace"]
    anchor_model: str = Field(..., min_length=1)
    paired_type: Literal["outdoor", "coil", "furnace"]
    paired_model: str = Field(..., min_length=1)
    equipment_category: str | None = None
    refrigerant_type: str | None = None
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    prefer_higher_seer: bool = True


class PairedMatchupsResponse(BaseModel):
    anchor_type: Literal["outdoor", "coil", "furnace"]
    anchor_model: str
    paired_type: Literal["outdoor", "coil", "furnace"]
    paired_model: str
    matchups: list[HvacRecommendation]
    meta: dict
