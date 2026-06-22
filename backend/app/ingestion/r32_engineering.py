"""Ingest Goodman R-32 engineering product export (accessories per SKU)."""

import json
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.models.engineering_product import EngineeringProduct
from app.models.knowledge_source import KnowledgeSource
from app.services.accessories import ACCESSORIES_COLUMN, apply_accessories_to_systems, parse_accessory_skus

SOURCE_TYPE = "r32_engineering"
BATCH_SIZE = 500
SKU_COLUMN = "SKU"


def ingest_r32_engineering(db: Session, file_path: Path, replace: bool = True) -> KnowledgeSource:
    if replace:
        db.query(EngineeringProduct).delete()
        db.flush()

    source = KnowledgeSource(
        source_type=SOURCE_TYPE,
        filename=file_path.name,
        status="processing",
    )
    db.add(source)
    db.flush()

    df = pd.read_excel(file_path, sheet_name=0)
    df = df.dropna(how="all")

    batch: list[EngineeringProduct] = []
    total_rows = 0

    for _, row in df.iterrows():
        sku_raw = row.get(SKU_COLUMN)
        if sku_raw is None or (isinstance(sku_raw, float) and pd.isna(sku_raw)):
            continue
        sku = str(sku_raw).strip()
        if not sku:
            continue

        accessories_raw = row.get(ACCESSORIES_COLUMN)
        accessory_skus = parse_accessory_skus(
            None if accessories_raw is None or (isinstance(accessories_raw, float) and pd.isna(accessories_raw))
            else str(accessories_raw)
        )

        short_description = row.get("shortDescription")
        if short_description is not None and not (isinstance(short_description, float) and pd.isna(short_description)):
            short_description = str(short_description).strip() or None
        else:
            short_description = None

        product_category = row.get("productCategory")
        if product_category is not None and not (isinstance(product_category, float) and pd.isna(product_category)):
            product_category = str(product_category).strip() or None
        else:
            product_category = None

        product_type = row.get("productType")
        if product_type is not None and not (isinstance(product_type, float) and pd.isna(product_type)):
            product_type = str(product_type).strip() or None
        else:
            product_type = None

        batch.append(
            EngineeringProduct(
                source_id=source.id,
                sku=sku,
                short_description=short_description,
                product_category=product_category,
                product_type=product_type,
                accessories=json.dumps(accessory_skus) if accessory_skus else None,
                raw_json=json.dumps(row.to_dict(), default=str),
            )
        )

        if len(batch) >= BATCH_SIZE:
            db.bulk_save_objects(batch)
            db.flush()
            total_rows += len(batch)
            batch.clear()

    if batch:
        db.bulk_save_objects(batch)
        db.flush()
        total_rows += len(batch)

    systems_updated = apply_accessories_to_systems(db)

    source.row_count = total_rows
    source.status = "completed"
    source.notes = f"Applied accessories to {systems_updated} HVAC systems"
    db.commit()
    db.refresh(source)
    return source
