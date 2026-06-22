from pydantic import BaseModel, Field


class HvacComponent(BaseModel):
    type: str
    model: str
    image_url: str | None = None


class HvacAccessory(BaseModel):
    sku: str
    description: str | None = None
    source_model: str | None = None


class HvacSystemOut(BaseModel):
    id: int
    source_row_id: str | None = None
    ahri_number: str | None = None
    version: str | None = None
    tonnage: float | None
    seer: float | None
    eer: float | None
    hspf: float | None = None
    system_type: str | None
    system_type_seer2: str | None
    cond_seer: str | None = None
    stage: str | None
    config: str | None
    indoor_unit: str | None
    indoor_type: str | None = None
    coil_width: str | None = None
    furnace_width: str | None = None
    furnace_btu: str | None
    cabinet_width: str | None
    blower_type: str | None = None
    description: str | None
    model_status: str | None
    equipment_category: str | None = None
    refrigerant_type: str | None = None
    image_url: str | None = None
    outdoor_model: str | None
    coil_model: str | None
    furnace_model: str | None
    components: list[HvacComponent]
    accessories: list[HvacAccessory] = Field(default_factory=list)
    all_fields: dict[str, str] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class HvacSearchRequest(BaseModel):
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
    outdoor_model: str | None = None
    coil_model: str | None = None
    furnace_model: str | None = None
    query: str | None = Field(default=None, description="Free-text search over description and models")
    active_only: bool = True
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=1000)


class HvacSearchResponse(BaseModel):
    data: list[HvacSystemOut]
    meta: dict
