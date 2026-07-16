"""Ingest OD Sales Excel into sales_line_items."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.models.knowledge_source import KnowledgeSource
from app.models.sales_line_item import SalesLineItem

SOURCE_TYPE = "od_sales"
BATCH_SIZE = 5_000

COLUMN_MAP = {
    "COD Division": "cod_division",
    "Branch Division": "branch_division",
    "Branch Region": "branch_region",
    "Vendor": "vendor",
    "Line of Business": "line_of_business",
    "SKU": "sku",
    "Job Line Item Quantity": "quantity",
    "Product Category": "product_category",
    "Product Subcategory": "product_subcategory",
}


def _clean_str(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def _clean_float(value: Any) -> float:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def ingest_od_sales(db: Session, file_path: Path, replace: bool = True) -> KnowledgeSource:
    df = pd.read_excel(file_path)
    missing = [col for col in COLUMN_MAP if col not in df.columns]
    if missing:
        raise ValueError(f"OD Sales file missing columns: {missing}")

    source = KnowledgeSource(
        source_type=SOURCE_TYPE,
        filename=file_path.name,
        row_count=0,
        status="processing",
    )
    db.add(source)
    db.flush()

    if replace:
        db.query(SalesLineItem).delete()
        db.flush()

    rows: list[SalesLineItem] = []
    for index, raw in df.iterrows():
        sku = _clean_str(raw.get("SKU"))
        if sku is None:
            continue
        rows.append(
            SalesLineItem(
                source_id=source.id,
                source_row_id=str(index),
                cod_division=_clean_str(raw.get("COD Division")),
                branch_division=_clean_str(raw.get("Branch Division")),
                branch_region=_clean_str(raw.get("Branch Region")),
                vendor=_clean_str(raw.get("Vendor")),
                line_of_business=_clean_str(raw.get("Line of Business")),
                sku=sku,
                quantity=_clean_float(raw.get("Job Line Item Quantity")),
                product_category=_clean_str(raw.get("Product Category")),
                product_subcategory=_clean_str(raw.get("Product Subcategory")),
            )
        )
        if len(rows) >= BATCH_SIZE:
            db.add_all(rows)
            db.flush()
            rows.clear()

    if rows:
        db.add_all(rows)
        db.flush()

    source.row_count = db.query(SalesLineItem).filter(SalesLineItem.source_id == source.id).count()
    source.status = "completed"
    db.commit()
    db.refresh(source)
    return source
