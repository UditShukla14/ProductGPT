from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SalesLineItem(Base):
    """One row from OD Sales Excel (job line item)."""

    __tablename__ = "sales_line_items"
    __table_args__ = (UniqueConstraint("source_id", "source_row_id", name="uq_sales_source_row"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(Integer, index=True)
    source_row_id: Mapped[str] = mapped_column(String(64), index=True)

    cod_division: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    branch_division: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    branch_region: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    line_of_business: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    sku: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    product_category: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    product_subcategory: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
