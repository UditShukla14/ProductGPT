from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ShopifyProduct(Base):
    __tablename__ = "shopify_products"
    __table_args__ = (UniqueConstraint("variant_sku", name="uq_shopify_variant_sku"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(Integer, index=True)
    variant_sku: Mapped[str] = mapped_column(String(64), index=True)
    handle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    cabinet_width: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ahri_number: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
