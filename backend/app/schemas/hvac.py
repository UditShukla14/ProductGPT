from pydantic import BaseModel, Field


class HvacComponent(BaseModel):
    type: str
    model: str


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
    furnace_btu: str | None
    cabinet_width: str | None
    blower_type: str | None = None
    description: str | None
    model_status: str | None
    outdoor_model: str | None
    coil_model: str | None
    furnace_model: str | None
    components: list[HvacComponent]
    all_fields: dict[str, str] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class HvacSearchRequest(BaseModel):
    tonnage: float | None = None
    min_seer: float | None = None
    max_seer: float | None = None
    config: str | None = None
    system_type_seer2: str | None = None
    stage: str | None = None
    indoor_unit: str | None = None
    furnace_btu: str | None = None
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
