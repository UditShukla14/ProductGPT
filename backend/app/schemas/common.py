from pydantic import BaseModel


class IngestUploadResponse(BaseModel):
    source_id: int
    source_type: str
    filename: str
    row_count: int
    status: str


class HealthResponse(BaseModel):
    status: str
    hvac_system_count: int
    knowledge_sources: int
