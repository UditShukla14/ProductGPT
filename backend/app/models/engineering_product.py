from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EngineeringProduct(Base):
    __tablename__ = "engineering_products"
    __table_args__ = (UniqueConstraint("sku", name="uq_engineering_product_sku"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(Integer, index=True)
    sku: Mapped[str] = mapped_column(String(64), index=True)
    short_description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    product_category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    product_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    accessories: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
