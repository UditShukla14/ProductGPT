import json

from sqlalchemy import Float, cast, func, or_
from sqlalchemy.orm import Session

from app.models.hvac_system import HvacSystem
from app.schemas.hvac import HvacComponent, HvacSearchRequest, HvacSystemOut
from app.services.product_images import load_sku_image_map, resolve_image_for_model

FIELD_LABELS: dict[str, str] = {
    "id": "Row ID",
    "ahri_number": "AHRI Number",
    "version": "Version",
    "tonnage": "Tonnage",
    "outdoor_model": "Outdoor Model",
    "outdoor_model_revision": "Outdoor Model Revision",
    "coil_model_number": "Coil Model Number",
    "coil_model_revision": "Coil Model Revision",
    "furnace_model_revision": "Furnace Model Revision",
    "blower_model_revision": "Blower Model Revision",
    "fit": "Fit",
    "seer": "SEER",
    "eer": "EER",
    "cooling": "Cooling",
    "txv_piston": "TXV Piston",
    "hsk": "HSK",
    "hspf": "HSPF",
    "orifice_size": "Orifice Size",
    "indoor_coil_air_qty": "Indoor Coil Air Qty",
    "high_cop": "High COP",
    "hsvtc": "HSVTC",
    "model_status": "Model Status",
    "region": "Region",
    "high_heat": "High Heat",
    "afue": "AFUE",
    "low_heat": "Low Heat",
    "low_cop": "Low COP",
    "system_type": "System Type",
    "system_type_seer2": "System Type SEER2",
    "cond_seer": "Cond SEER",
    "stage": "Stage",
    "indoor_unit": "Indoor Unit",
    "indoor_type": "Indoor Type",
    "config": "Configuration",
    "cabinet_width": "Cabinet Width",
    "ext_txv": "Ext TXV",
    "furnace_btu": "Furnace BTU",
    "blower_type": "Blower Type",
    "description": "Description",
    "equipment_category": "Equipment Category",
    "refrigerant_type": "Refrigerant Type",
    "file": "File",
    "created_at": "Created At",
    "updated_at": "Updated At",
    "deleted_at": "Deleted At",
    "executed": "Executed",
}


def _parse_all_fields(raw_json: str | None) -> dict[str, str]:
    if not raw_json:
        return {}
    try:
        row = json.loads(raw_json)
    except json.JSONDecodeError:
        return {}

    fields: dict[str, str] = {}
    for key, value in row.items():
        if value is None:
            continue
        text = str(value).strip()
        if not text or text.lower() in {"null", "nan", "none"}:
            continue
        label = FIELD_LABELS.get(key, key.replace("_", " ").title())
        fields[label] = text
    return fields


def system_to_schema(
    system: HvacSystem,
    sku_images: dict[str, str] | None = None,
) -> HvacSystemOut:
    sku_images = sku_images or {}
    components: list[HvacComponent] = []
    outdoor = system.outdoor_model_revision or system.outdoor_model
    if outdoor:
        components.append(
            HvacComponent(
                type="outdoor",
                model=outdoor,
                image_url=resolve_image_for_model(outdoor, sku_images),
            )
        )
    coil = system.coil_model_revision or system.coil_model_number
    if coil:
        components.append(
            HvacComponent(
                type="coil",
                model=coil,
                image_url=resolve_image_for_model(coil, sku_images),
            )
        )
    if system.furnace_model_revision:
        components.append(
            HvacComponent(
                type="furnace",
                model=system.furnace_model_revision,
                image_url=resolve_image_for_model(system.furnace_model_revision, sku_images),
            )
        )

    return HvacSystemOut(
        id=system.id,
        source_row_id=system.source_row_id,
        ahri_number=system.ahri_number,
        version=system.version,
        tonnage=system.tonnage,
        seer=system.seer,
        eer=system.eer,
        hspf=system.hspf,
        system_type=system.system_type,
        system_type_seer2=system.system_type_seer2,
        cond_seer=system.cond_seer,
        stage=system.stage,
        config=system.config,
        indoor_unit=system.indoor_unit,
        indoor_type=system.indoor_type,
        furnace_btu=system.furnace_btu,
        cabinet_width=system.cabinet_width,
        blower_type=system.blower_type,
        description=system.description,
        model_status=system.model_status,
        equipment_category=system.equipment_category,
        refrigerant_type=system.refrigerant_type,
        image_url=system.image_url,
        outdoor_model=outdoor,
        coil_model=coil,
        furnace_model=system.furnace_model_revision,
        components=components,
        all_fields=_parse_all_fields(system.raw_json),
    )


def _apply_filters(query, params: HvacSearchRequest):
    if params.active_only:
        query = query.filter(func.lower(HvacSystem.model_status) == "active")

    if params.tonnage is not None:
        query = query.filter(HvacSystem.tonnage == params.tonnage)

    if params.min_seer is not None:
        query = query.filter(HvacSystem.seer >= params.min_seer)

    if params.max_seer is not None:
        query = query.filter(HvacSystem.seer <= params.max_seer)

    if params.equipment_category:
        query = query.filter(HvacSystem.equipment_category == params.equipment_category.strip())

    if params.refrigerant_type:
        query = query.filter(HvacSystem.refrigerant_type == params.refrigerant_type.strip())

    if params.outdoor_model:
        model = params.outdoor_model.strip()
        query = query.filter(
            or_(
                HvacSystem.outdoor_model.ilike(f"%{model}%"),
                HvacSystem.outdoor_model_revision.ilike(f"%{model}%"),
            )
        )

    if params.coil_model:
        model = params.coil_model.strip()
        query = query.filter(
            or_(
                HvacSystem.coil_model_number.ilike(f"%{model}%"),
                HvacSystem.coil_model_revision.ilike(f"%{model}%"),
            )
        )

    if params.furnace_model:
        query = query.filter(HvacSystem.furnace_model_revision.ilike(f"%{params.furnace_model.strip()}%"))

    if params.query:
        term = f"%{params.query.strip()}%"
        query = query.filter(
            or_(
                HvacSystem.description.ilike(term),
                HvacSystem.search_text.ilike(term),
                HvacSystem.ahri_number.ilike(term),
                HvacSystem.outdoor_model_revision.ilike(term),
                HvacSystem.coil_model_revision.ilike(term),
                HvacSystem.furnace_model_revision.ilike(term),
            )
        )

    return query


def search_hvac_systems(db: Session, params: HvacSearchRequest) -> tuple[list[HvacSystemOut], dict]:
    query = db.query(HvacSystem)
    query = _apply_filters(query, params)

    total = query.count()
    offset = (params.page - 1) * params.limit
    systems = (
        query.order_by(cast(HvacSystem.seer, Float).desc().nullslast(), HvacSystem.ahri_number)
        .offset(offset)
        .limit(params.limit)
        .all()
    )

    sku_images = load_sku_image_map(db)
    meta = {
        "total": total,
        "page": params.page,
        "limit": params.limit,
        "pages": (total + params.limit - 1) // params.limit if total else 0,
    }
    return [system_to_schema(system, sku_images) for system in systems], meta
