#!/usr/bin/env python3
"""Seed HVAC data from the default CSV."""

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings
from app.database import SessionLocal, init_db
from app.ingestion.hvac_system_finder import ingest_hvac_csv


def main() -> None:
    csv_path = settings.default_hvac_csv
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    init_db()
    db = SessionLocal()
    try:
        source = ingest_hvac_csv(db, csv_path, replace=True)
        print(f"Loaded {source.row_count} HVAC systems from {csv_path.name}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
