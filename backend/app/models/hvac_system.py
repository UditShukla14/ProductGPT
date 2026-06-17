from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class HvacSystem(Base):
    __tablename__ = "hvac_systems"
    __table_args__ = (UniqueConstraint("source_id", "source_row_id", name="uq_hvac_source_row"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(Integer, index=True)
    source_row_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ahri_number: Mapped[str] = mapped_column(String(32), index=True)
    version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tonnage: Mapped[float | None] = mapped_column(Float, index=True, nullable=True)
    outdoor_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    outdoor_model_revision: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    coil_model_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    coil_model_revision: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    furnace_model_revision: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    seer: Mapped[float | None] = mapped_column(Float, index=True, nullable=True)
    eer: Mapped[float | None] = mapped_column(Float, nullable=True)
    hspf: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_status: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    system_type: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    system_type_seer2: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    cond_seer: Mapped[str | None] = mapped_column(String(32), nullable=True)
    stage: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    indoor_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    indoor_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    config: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    cabinet_width: Mapped[str | None] = mapped_column(String(32), nullable=True)
    furnace_btu: Mapped[str | None] = mapped_column(String(32), nullable=True)
    blower_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
