"""Load Shopify product export and apply Variant SKU images to HVAC systems."""

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings
from app.database import SessionLocal, init_db
from app.ingestion.shopify_products import ingest_shopify_products
from app.knowledge_graph.store import graph_store
from app.models.hvac_system import HvacSystem
from app.models.shopify_product import ShopifyProduct


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Shopify product export CSV")
    parser.add_argument(
        "csv_path",
        nargs="?",
        default=str(settings.default_shopify_products_csv),
        help="Path to Shopify products_export CSV",
    )
    parser.add_argument(
        "--no-replace",
        action="store_true",
        help="Append products instead of replacing existing Shopify rows",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    init_db()
    db = SessionLocal()
    try:
        source = ingest_shopify_products(db, csv_path, replace=not args.no_replace)
        graph_store.rebuild(db)
        with_images = db.query(HvacSystem).filter(HvacSystem.image_url.isnot(None)).count()
        print(
            f"Ingested {source.row_count} Shopify products; "
            f"{with_images} HVAC systems now have images. "
            f"{source.notes}"
        )
        print(f"Total shopify_products rows: {db.query(ShopifyProduct).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
