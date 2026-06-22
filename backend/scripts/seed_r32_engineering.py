"""Load R-32 engineering export and apply accessories to HVAC systems."""

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings
from app.database import SessionLocal, init_db
from app.ingestion.r32_engineering import ingest_r32_engineering
from app.knowledge_graph.store import graph_store
from app.models.engineering_product import EngineeringProduct
from app.models.hvac_system import HvacSystem


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest R-32 engineering product export")
    parser.add_argument(
        "xlsx_path",
        nargs="?",
        default=str(settings.default_r32_engineering_xlsx),
        help="Path to R32_Engineering_file.xlsx",
    )
    parser.add_argument(
        "--no-replace",
        action="store_true",
        help="Append products instead of replacing existing engineering rows",
    )
    args = parser.parse_args()

    xlsx_path = Path(args.xlsx_path)
    if not xlsx_path.exists():
        raise SystemExit(f"XLSX not found: {xlsx_path}")

    init_db()
    db = SessionLocal()
    try:
        source = ingest_r32_engineering(db, xlsx_path, replace=not args.no_replace)
        graph_store.rebuild(db)
        with_accessories = (
            db.query(HvacSystem)
            .filter(HvacSystem.accessories_json.isnot(None), HvacSystem.accessories_json != "[]")
            .count()
        )
        print(
            f"Ingested {source.row_count} engineering products; "
            f"{with_accessories} HVAC systems now have accessories. "
            f"{source.notes}"
        )
        print(f"Total engineering_products rows: {db.query(EngineeringProduct).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
