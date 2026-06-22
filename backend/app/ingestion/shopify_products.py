"""Ingest Shopify product export CSV and enrich HVAC systems with images via Variant SKU."""

import csv
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.hvac_system import HvacSystem
from app.models.knowledge_source import KnowledgeSource
from app.models.shopify_product import ShopifyProduct
from app.services.product_images import build_sku_image_map, resolve_image_for_system
from app.services.width_resolution import apply_widths_to_systems, normalize_width

SOURCE_TYPE = "shopify_products"
BATCH_SIZE = 500

AHRI_COLUMN = "AHRI No (product.metafields.custom.ahri_no)"
CABINET_WIDTH_COLUMN = "Cabinet Width (product.metafields.goodman.cabinet_width)"


def _parse_price(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value.strip())
    except ValueError:
        return None


def _parse_primary_rows(file_path: Path) -> list[dict[str, str]]:
    with file_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return [row for row in reader if (row.get("Title") or "").strip()]


def apply_sku_images_to_systems(db: Session) -> int:
    products = db.query(ShopifyProduct).all()
    sku_images = build_sku_image_map(products)
    if not sku_images:
        return 0

    updated = 0
    for system in db.query(HvacSystem).all():
        image_url = resolve_image_for_system(system, sku_images)
        if image_url and system.image_url != image_url:
            system.image_url = image_url
            updated += 1

    db.flush()
    return updated


def ingest_shopify_products(db: Session, file_path: Path, replace: bool = True) -> KnowledgeSource:
    if replace:
        db.query(ShopifyProduct).delete()
        db.flush()

    source = KnowledgeSource(
        source_type=SOURCE_TYPE,
        filename=file_path.name,
        status="processing",
    )
    db.add(source)
    db.flush()

    rows = _parse_primary_rows(file_path)
    batch: list[ShopifyProduct] = []
    total_rows = 0

    for row in rows:
        variant_sku = (row.get("Variant SKU") or "").strip()
        if not variant_sku:
            continue

        batch.append(
            ShopifyProduct(
                source_id=source.id,
                variant_sku=variant_sku,
                handle=(row.get("Handle") or "").strip() or None,
                title=(row.get("Title") or "").strip() or None,
                image_url=(row.get("Image Src") or "").strip() or None,
                cabinet_width=normalize_width(row.get(CABINET_WIDTH_COLUMN)),
                ahri_number=(row.get(AHRI_COLUMN) or "").strip() or None,
                price=_parse_price(row.get("Variant Price")),
                status=(row.get("Status") or "").strip() or None,
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

    images_applied = apply_sku_images_to_systems(db)
    widths_applied = apply_widths_to_systems(db)

    source.row_count = total_rows
    source.status = "completed"
    source.notes = (
        f"Applied images to {images_applied} HVAC systems and widths to {widths_applied} "
        "via Variant SKU lookup"
    )
    db.commit()
    db.refresh(source)
    return source
