from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.hvac_system import HvacSystem


def normalize_sku(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip().upper()
    return text or None


def load_sku_image_map(_db: Session) -> dict[str, str]:
    return {}


def resolve_image_for_model(model: str | None, sku_images: dict[str, str]) -> str | None:
    sku = normalize_sku(model)
    if not sku:
        return None
    return sku_images.get(sku)


def resolve_image_for_models(
    models: list[str | None], sku_images: dict[str, str]
) -> str | None:
    for model in models:
        image_url = resolve_image_for_model(model, sku_images)
        if image_url:
            return image_url
    return None


def resolve_image_for_system(system: HvacSystem, sku_images: dict[str, str]) -> str | None:
    if system.image_url:
        return system.image_url
    return resolve_image_for_models(
        [
            system.outdoor_model_revision or system.outdoor_model,
            system.coil_model_revision or system.coil_model_number,
            system.furnace_model_revision,
        ],
        sku_images,
    )


def component_models_for_system(system: HvacSystem) -> dict[str, str | None]:
    return {
        "outdoor": normalize_sku(system.outdoor_model_revision or system.outdoor_model),
        "coil": normalize_sku(system.coil_model_revision or system.coil_model_number),
        "furnace": normalize_sku(system.furnace_model_revision),
    }
