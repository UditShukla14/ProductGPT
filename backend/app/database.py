from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_hvac_columns() -> None:
    inspector = inspect(engine)
    if "hvac_systems" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("hvac_systems")}
    additions = {
        "equipment_category": "VARCHAR(64)",
        "refrigerant_type": "VARCHAR(32)",
        "image_url": "TEXT",
        "coil_width": "VARCHAR(16)",
        "furnace_width": "VARCHAR(16)",
        "accessories_json": "TEXT",
    }

    with engine.begin() as conn:
        for column_name, column_type in additions.items():
            if column_name not in existing:
                conn.execute(text(f"ALTER TABLE hvac_systems ADD COLUMN {column_name} {column_type}"))

        if "equipment_category" not in existing or "refrigerant_type" not in existing:
            conn.execute(
                text(
                    """
                    UPDATE hvac_systems
                    SET equipment_category = json_extract(raw_json, '$._equipment_category'),
                        refrigerant_type = json_extract(raw_json, '$._refrigerant')
                    WHERE raw_json IS NOT NULL
                      AND (equipment_category IS NULL OR refrigerant_type IS NULL)
                    """
                )
            )

    shopify_existing = (
        {column["name"] for column in inspector.get_columns("shopify_products")}
        if "shopify_products" in inspector.get_table_names()
        else set()
    )
    if "shopify_products" in inspector.get_table_names() and "cabinet_width" not in shopify_existing:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE shopify_products ADD COLUMN cabinet_width VARCHAR(32)"))

    from app.services.width_resolution import apply_widths_to_systems

    db = SessionLocal()
    try:
        apply_widths_to_systems(db)
        db.commit()
    finally:
        db.close()


def init_db() -> None:
    from app.models import engineering_product, hvac_system, knowledge_source, shopify_product  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_hvac_columns()
