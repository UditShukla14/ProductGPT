"""Resolve R-32 engineering accessories for HVAC systems and components."""

import json

from sqlalchemy.orm import Session

from app.models.engineering_product import EngineeringProduct
from app.models.hvac_system import HvacSystem

ACCESSORIES_COLUMN = "componentsProductReference"


def parse_accessory_skus(value: str | None) -> list[str]:
    if not value:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for part in str(value).split(";"):
        sku = part.strip()
        if not sku:
            continue
        key = sku.upper()
        if key in seen:
            continue
        seen.add(key)
        result.append(sku)
    return result


def load_engineering_product_map(db: Session) -> dict[str, EngineeringProduct]:
    products: dict[str, EngineeringProduct] = {}
    for product in db.query(EngineeringProduct).all():
        products[product.sku.strip().upper()] = product
    return products


def load_accessories_by_sku(db: Session) -> dict[str, list[str]]:
    by_sku: dict[str, list[str]] = {}
    for product in db.query(EngineeringProduct).all():
        if not product.accessories:
            continue
        try:
            skus = json.loads(product.accessories)
        except json.JSONDecodeError:
            skus = parse_accessory_skus(product.accessories)
        if skus:
            by_sku[product.sku.strip().upper()] = skus
    return by_sku


def resolve_accessories_for_models(
    models: list[str | None],
    accessories_by_sku: dict[str, list[str]],
    product_map: dict[str, EngineeringProduct],
) -> list[dict[str, str | None]]:
    resolved: list[dict[str, str | None]] = []
    seen: set[str] = set()

    for model in models:
        if not model:
            continue
        model_key = model.strip().upper()
        for accessory_sku in accessories_by_sku.get(model_key, []):
            accessory_key = accessory_sku.strip().upper()
            if accessory_key in seen:
                continue
            seen.add(accessory_key)
            meta = product_map.get(accessory_key)
            resolved.append(
                {
                    "sku": accessory_sku.strip(),
                    "description": meta.short_description if meta else None,
                    "source_model": model.strip(),
                }
            )
    return resolved


def resolve_system_accessories(
    system: HvacSystem,
    accessories_by_sku: dict[str, list[str]],
    product_map: dict[str, EngineeringProduct],
) -> list[dict[str, str | None]]:
    models = [
        system.outdoor_model_revision or system.outdoor_model,
        system.coil_model_revision or system.coil_model_number,
        system.furnace_model_revision,
    ]
    return resolve_accessories_for_models(models, accessories_by_sku, product_map)


def apply_accessories_to_systems(db: Session) -> int:
    accessories_by_sku = load_accessories_by_sku(db)
    if not accessories_by_sku:
        return 0

    product_map = load_engineering_product_map(db)
    updated = 0
    for system in db.query(HvacSystem).all():
        accessories = resolve_system_accessories(system, accessories_by_sku, product_map)
        payload = json.dumps(accessories)
        if system.accessories_json != payload:
            system.accessories_json = payload
            updated += 1
    db.flush()
    return updated


def parse_system_accessories(system: HvacSystem) -> list[dict[str, str | None]]:
    if not system.accessories_json:
        return []
    try:
        data = json.loads(system.accessories_json)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict) and item.get("sku")]


def collect_unique_accessories(db: Session) -> list[dict[str, str | None]]:
    """Return deduplicated accessory rows (one per SKU) from engineering product references."""
    product_map = load_engineering_product_map(db)
    accessories_by_sku = load_accessories_by_sku(db)

    seen: set[str] = set()
    unique: list[dict[str, str | None]] = []

    for accessory_skus in accessories_by_sku.values():
        for accessory_sku in accessory_skus:
            sku = accessory_sku.strip()
            if not sku:
                continue
            key = sku.upper()
            if key in seen:
                continue
            seen.add(key)
            meta = product_map.get(key)
            unique.append(
                {
                    "sku": sku,
                    "description": meta.short_description if meta else None,
                    "product_category": meta.product_category if meta else None,
                    "product_type": meta.product_type if meta else None,
                }
            )

    unique.sort(key=lambda row: row["sku"].upper())
    return unique
