from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.component_search import ComponentType
from app.schemas.hvac import HvacAccessory
from app.schemas.recommendations import HvacRecommendation


class ProductLookupResponse(BaseModel):
    product_id: str
    matched_type: Literal["outdoor", "coil", "furnace"] | None
    matched_model: str | None
    similar_matchups: list[HvacRecommendation]
    accessories: list[HvacAccessory]
    meta: dict


class ProductLookupQuery(BaseModel):
    component_type: ComponentType = Field(
        default="auto",
        description="Component to search; auto detects from model fields",
    )
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
