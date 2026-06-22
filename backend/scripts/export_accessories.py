"""Export deduplicated accessory SKUs from R-32 engineering data to Excel."""

import argparse
import sys
from pathlib import Path

import pandas as pd

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings
from app.database import SessionLocal, init_db
from app.services.accessories import collect_unique_accessories

DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "accessories_unique.xlsx"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export unique HVAC accessories to Excel")
    parser.add_argument(
        "output_path",
        nargs="?",
        default=str(DEFAULT_OUTPUT),
        help=f"Output .xlsx path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    init_db()
    db = SessionLocal()
    try:
        accessories = collect_unique_accessories(db)
        if not accessories:
            raise SystemExit(
                "No accessories found. Run seed_r32_engineering.py first "
                f"({settings.default_r32_engineering_xlsx})."
            )

        df = pd.DataFrame(accessories, columns=["sku", "description", "product_category", "product_type"])
        df.to_excel(output_path, index=False, sheet_name="Accessories")
        print(f"Exported {len(accessories)} unique accessories to {output_path}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
