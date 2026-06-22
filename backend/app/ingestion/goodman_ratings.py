"""Ingest Goodman AHRI ratings export (multi-sheet Excel)."""

import json
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.models.hvac_system import HvacSystem
from app.models.knowledge_source import KnowledgeSource
from app.services.width_resolution import coil_width_from_model

SOURCE_TYPE = "goodman_ratings"
HEADER_MARKER = "AHRI Certified Reference Number"
BATCH_SIZE = 5_000

SHEET_CATEGORY = {
    "CN": "AC",
    "HP": "Heat Pump",
    "PackageAC": "Package AC",
    "PackageHP": "Package Heat Pump",
}

# Canonical Excel column → internal field key
FIELD_ALIASES: dict[str, list[str]] = {
    "ahri_number": ["AHRI Certified Reference Number"],
    "model_status": ["Model Status"],
    "manufacturer_type": ["Manufacturer Type"],
    "ahri_type": ["AHRI Type"],
    "series_name": ["Series Name"],
    "outdoor_brand": ["Outdoor Unit Brand Name"],
    "outdoor_model": ["Outdoor Unit Model Number  (Condenser or Single Package)"],
    "tonnage": ["Tonnage"],
    "indoor_brand": ["Indoor Unit Brand Name"],
    "coil_model": [
        "Indoor Unit Model Number (Evaporator and/or Air Handler)",
    ],
    "furnace_model": ["Furnace Model Number"],
    "furnace_family": ["Furnace Family"],
    "refrigerant": ["Refrigerant Type"],
    "seer": ["SEER"],
    "seer2": ["SEER2"],
    "eer": ["EER (A2) - Single or High Stage (95F)"],
    "eer2": ["EER2 (AFull) - Single or High Stage (95F)2", "EER2 (AFull) - Single or High Stage (95F)"],
    "hspf": ["HSPF (Region IV)"],
    "hspf2": ["HSPF2 (Region IV)"],
    "region": ["Region"],
    "sold_in": ["Sold in?"],
    "energy_star": ["Labeled ENERGY STAR ", "Labeled ENERGY STAR?"],
    "ira_eligible": ["Potential Eligibility for IRA Tax Credit"],
    "coil_type": ["Coil Type"],
}


def _normalize_model(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().rstrip("*").strip()
    return text or None


def _parse_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_field(row: dict[str, Any], key: str) -> Any:
    for col in FIELD_ALIASES.get(key, []):
        if col in row:
            return row[col]
    return None


def _find_header_row(raw: pd.DataFrame) -> int:
    for i in range(min(30, len(raw))):
        val = raw.iloc[i, 0]
        if isinstance(val, str) and HEADER_MARKER in val:
            return i
    raise ValueError(f"Could not find header row containing '{HEADER_MARKER}'")


def _load_sheet(file_path: Path, sheet_name: str) -> pd.DataFrame:
    raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    header_idx = _find_header_row(raw)
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_idx)
    df = df.dropna(how="all")
    ahri_col = df.columns[0]
    df = df[df[ahri_col].notna()].copy()
    return df


def _derive_system_type(category: str, manufacturer_type: str | None, ahri_type: str | None) -> str:
    parts = [category]
    if manufacturer_type:
        parts.append(manufacturer_type)
    return " / ".join(parts)


def _build_description(
    category: str,
    series: str | None,
    tonnage: float | None,
    outdoor: str | None,
    coil: str | None,
    furnace: str | None,
) -> str:
    parts: list[str] = []
    if series:
        parts.append(series)
    if tonnage is not None:
        parts.append(f"{tonnage:g} Ton")
    parts.append(category)
    if outdoor:
        parts.append(f"Outdoor {outdoor}")
    if coil:
        parts.append(f"Coil {coil}")
    if furnace:
        parts.append(f"Furnace {furnace}")
    return " - ".join(parts)


def _build_search_text(
    row: dict[str, Any],
    category: str,
    outdoor: str | None,
    coil: str | None,
    furnace: str | None,
    seer: float | None,
    seer2: float | None,
) -> str:
    parts = [
        f"AHRI {_get_field(row, 'ahri_number')}",
        category,
        f"{_get_field(row, 'tonnage')} ton" if _get_field(row, "tonnage") else None,
        _get_field(row, "series_name"),
        _get_field(row, "ahri_type"),
        f"SEER2 {seer2}" if seer2 else None,
        f"SEER {seer}" if seer else None,
        f"outdoor {outdoor}" if outdoor else None,
        f"coil {coil}" if coil else None,
        f"furnace {furnace}" if furnace else None,
        _get_field(row, "refrigerant"),
        _get_field(row, "region"),
        _get_field(row, "ira_eligible"),
    ]
    return " | ".join(str(part) for part in parts if part is not None and str(part).strip())


def _row_to_hvac_system(
    row: dict[str, Any],
    source_id: int,
    sheet_name: str,
    row_index: int,
) -> HvacSystem | None:
    ahri = _normalize_model(_get_field(row, "ahri_number"))
    if not ahri:
        return None

    category = SHEET_CATEGORY.get(sheet_name, sheet_name)
    outdoor = _normalize_model(_get_field(row, "outdoor_model"))
    coil = _normalize_model(_get_field(row, "coil_model"))
    furnace = _normalize_model(_get_field(row, "furnace_model"))
    tonnage = _parse_float(_get_field(row, "tonnage"))
    seer2 = _parse_float(_get_field(row, "seer2"))
    seer_legacy = _parse_float(_get_field(row, "seer"))
    seer = seer2 or seer_legacy
    eer2 = _parse_float(_get_field(row, "eer2"))
    eer_legacy = _parse_float(_get_field(row, "eer"))
    eer = eer2 or eer_legacy
    hspf2 = _parse_float(_get_field(row, "hspf2"))
    hspf_legacy = _parse_float(_get_field(row, "hspf"))
    hspf = hspf2 or hspf_legacy

    manufacturer_type = _normalize_model(_get_field(row, "manufacturer_type"))
    ahri_type = _normalize_model(_get_field(row, "ahri_type"))
    series = _normalize_model(_get_field(row, "series_name"))
    refrigerant_type = _normalize_model(_get_field(row, "refrigerant"))
    coil_type = _normalize_model(_get_field(row, "coil_type"))

    enriched = {
        **row,
        "_sheet": sheet_name,
        "_equipment_category": category,
        "_seer2": seer2,
        "_eer2": eer2,
        "_hspf2": hspf2,
        "_refrigerant": refrigerant_type,
        "_region": _normalize_model(_get_field(row, "region")),
        "_sold_in": _normalize_model(_get_field(row, "sold_in")),
        "_energy_star": _normalize_model(_get_field(row, "energy_star")),
        "_ira_eligible": _normalize_model(_get_field(row, "ira_eligible")),
        "_outdoor_brand": _normalize_model(_get_field(row, "outdoor_brand")),
        "_indoor_brand": _normalize_model(_get_field(row, "indoor_brand")),
        "_furnace_family": _normalize_model(_get_field(row, "furnace_family")),
        "_coil_type": _normalize_model(_get_field(row, "coil_type")),
    }

    return HvacSystem(
        source_id=source_id,
        source_row_id=f"{sheet_name}_{row_index}_{ahri}",
        ahri_number=ahri,
        version="goodman_ratings",
        tonnage=tonnage,
        outdoor_model=outdoor,
        outdoor_model_revision=outdoor,
        coil_model_number=coil,
        coil_model_revision=coil,
        furnace_model_revision=furnace,
        seer=seer,
        eer=eer,
        hspf=hspf,
        model_status=_normalize_model(_get_field(row, "model_status")),
        system_type=_derive_system_type(category, manufacturer_type, ahri_type),
        system_type_seer2=ahri_type,
        cond_seer=str(int(seer2)) if seer2 is not None else None,
        stage=None,
        indoor_unit=_normalize_model(_get_field(row, "indoor_brand")),
        indoor_type=coil_type,
        config=coil_type,
        coil_width=coil_width_from_model(coil),
        furnace_width=None,
        cabinet_width=None,
        furnace_btu=None,
        blower_type=None,
        description=_build_description(category, series, tonnage, outdoor, coil, furnace),
        equipment_category=category,
        refrigerant_type=refrigerant_type,
        search_text=_build_search_text(row, category, outdoor, coil, furnace, seer_legacy, seer2),
        raw_json=json.dumps(enriched, default=str),
    )


def ingest_goodman_ratings(db: Session, file_path: Path, replace: bool = True) -> KnowledgeSource:
    if replace:
        db.query(HvacSystem).delete()
        db.query(KnowledgeSource).delete()
        db.flush()

    source = KnowledgeSource(
        source_type=SOURCE_TYPE,
        filename=file_path.name,
        status="processing",
    )
    db.add(source)
    db.flush()

    total_rows = 0
    for sheet_name in SHEET_CATEGORY:
        try:
            df = _load_sheet(file_path, sheet_name)
        except ValueError:
            continue

        batch: list[HvacSystem] = []
        for row_index, series in df.iterrows():
            record = _row_to_hvac_system(series.to_dict(), source.id, sheet_name, int(row_index))
            if record is None:
                continue
            batch.append(record)
            if len(batch) >= BATCH_SIZE:
                db.bulk_save_objects(batch)
                db.flush()
                total_rows += len(batch)
                batch.clear()

        if batch:
            db.bulk_save_objects(batch)
            db.flush()
            total_rows += len(batch)

    source.row_count = total_rows
    source.status = "completed"
    db.commit()
    db.refresh(source)
    return source
