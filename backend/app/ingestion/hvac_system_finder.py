import json
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.models.hvac_system import HvacSystem
from app.models.knowledge_source import KnowledgeSource

SOURCE_TYPE = "hvac_system_finder"


def _normalize_model(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def _parse_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_search_text(row: dict[str, Any], outdoor: str | None, coil: str | None, furnace: str | None) -> str:
    parts = [
        f"AHRI {row.get('ahri_number')}",
        f"{row.get('tonnage')} ton" if row.get("tonnage") else None,
        row.get("system_type"),
        f"SEER {row.get('seer')}" if row.get("seer") else None,
        f"outdoor {outdoor}" if outdoor else None,
        f"coil {coil}" if coil else None,
        f"furnace {furnace}" if furnace else None,
        row.get("config"),
        row.get("stage"),
        row.get("description"),
    ]
    return " | ".join(part for part in parts if part)


def _row_to_hvac_system(row: dict[str, Any], source_id: int) -> HvacSystem:
    outdoor = _normalize_model(row.get("outdoor_model_revision") or row.get("outdoor_model"))
    coil = _normalize_model(row.get("coil_model_revision") or row.get("coil_model_number"))
    furnace = _normalize_model(row.get("furnace_model_revision"))

    return HvacSystem(
        source_id=source_id,
        source_row_id=_normalize_model(row.get("id")),
        ahri_number=str(row.get("ahri_number", "")).strip(),
        version=_normalize_model(row.get("version")),
        tonnage=_parse_float(row.get("tonnage")),
        outdoor_model=outdoor,
        outdoor_model_revision=outdoor,
        coil_model_number=coil,
        coil_model_revision=coil,
        furnace_model_revision=furnace,
        seer=_parse_float(row.get("seer")),
        eer=_parse_float(row.get("eer")),
        hspf=_parse_float(row.get("hspf")),
        model_status=_normalize_model(row.get("model_status")),
        system_type=_normalize_model(row.get("system_type")),
        system_type_seer2=_normalize_model(row.get("system_type_seer2")),
        cond_seer=_normalize_model(row.get("cond_seer")),
        stage=_normalize_model(row.get("stage")),
        indoor_unit=_normalize_model(row.get("indoor_unit")),
        indoor_type=_normalize_model(row.get("indoor_type")),
        config=_normalize_model(row.get("config")),
        cabinet_width=_normalize_model(row.get("cabinet_width")),
        furnace_btu=_normalize_model(row.get("furnace_btu")),
        blower_type=_normalize_model(row.get("blower_type")),
        description=_normalize_model(row.get("description")),
        search_text=_build_search_text(row, outdoor, coil, furnace),
        raw_json=json.dumps(row, default=str),
    )


def ingest_hvac_csv(db: Session, file_path: Path, replace: bool = True) -> KnowledgeSource:
    df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
    df = df.replace({"": None, "NULL": None, "null": None})

    if replace:
        db.query(HvacSystem).delete()

    source = KnowledgeSource(
        source_type=SOURCE_TYPE,
        filename=file_path.name,
        status="processing",
    )
    db.add(source)
    db.flush()

    records: list[HvacSystem] = []
    for _, series in df.iterrows():
        row = series.to_dict()
        ahri = _normalize_model(row.get("ahri_number"))
        if not ahri:
            continue
        records.append(_row_to_hvac_system(row, source.id))

    db.bulk_save_objects(records)
    source.row_count = len(records)
    source.status = "completed"
    db.commit()
    db.refresh(source)
    return source
