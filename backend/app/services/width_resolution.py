"""Resolve coil and furnace cabinet widths from model numbers and Shopify SKUs."""

import csv
import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.hvac_system import HvacSystem
from app.models.shopify_product import ShopifyProduct

COIL_WIDTH_PATTERN = re.compile(r"(\d{2})(?=[A-Z]\d*$)")
CABINET_WIDTH_COLUMN = "Cabinet Width (product.metafields.goodman.cabinet_width)"


def normalize_width(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip().rstrip('"').strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return text
    if number.is_integer():
        return str(int(number))
    return format(number, "g")


def coil_width_from_model(model: str | None) -> str | None:
    if not model:
        return None
    match = COIL_WIDTH_PATTERN.search(model.strip())
    if not match:
        return None
    width = int(match.group(1))
    if 14 <= width <= 36:
        return str(width)
    return None


def load_sku_cabinet_width_map(db: Session) -> dict[str, str]:
    widths: dict[str, str] = {}
    for product in db.query(ShopifyProduct).filter(ShopifyProduct.cabinet_width.isnot(None)).all():
        normalized = normalize_width(product.cabinet_width)
        if normalized:
            widths[product.variant_sku.strip().upper()] = normalized

    if widths:
        return widths

    return _load_cabinet_widths_from_csv()


def _load_cabinet_widths_from_csv(file_path: Path | None = None) -> dict[str, str]:
    from app.config import settings

    path = file_path or settings.default_shopify_products_csv
    if not path.exists():
        return {}

    widths: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            sku = (row.get("Variant SKU") or "").strip().upper()
            cabinet_width = normalize_width(row.get(CABINET_WIDTH_COLUMN))
            if sku and cabinet_width:
                widths[sku] = cabinet_width
    return widths


def resolve_furnace_width(
    furnace_model: str | None, sku_widths: dict[str, str] | None = None
) -> str | None:
    if not furnace_model:
        return None
    sku_widths = sku_widths or {}
    return sku_widths.get(furnace_model.strip().upper())


def apply_widths_to_system(
    system: HvacSystem,
    sku_widths: dict[str, str] | None = None,
) -> bool:
    changed = False
    coil_width = coil_width_from_model(system.coil_model_revision)
    if coil_width and system.coil_width != coil_width:
        system.coil_width = coil_width
        changed = True

    furnace_model = (system.furnace_model_revision or "").strip()
    furnace_width = resolve_furnace_width(furnace_model, sku_widths)
    if furnace_width and system.furnace_width != furnace_width:
        system.furnace_width = furnace_width
        changed = True

    return changed


def apply_widths_to_systems(db: Session) -> int:
    sku_widths = load_sku_cabinet_width_map(db)
    updated = 0
    for system in db.query(HvacSystem).all():
        if apply_widths_to_system(system, sku_widths):
            updated += 1
    db.flush()
    return updated
