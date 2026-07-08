"""Resolve coil and furnace cabinet widths from model numbers."""

import re

from sqlalchemy.orm import Session

from app.models.hvac_system import HvacSystem

COIL_WIDTH_PATTERN = re.compile(r"(\d{2})(?=[A-Z]\d*$)")


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
    updated = 0
    for system in db.query(HvacSystem).all():
        if apply_widths_to_system(system):
            updated += 1
    db.flush()
    return updated
