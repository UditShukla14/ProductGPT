"""Separate SQLite databases for Shopify API entities."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import settings
from app.shopify.client import ResourceName

SHOPIFY_DATA_DIR = settings.shopify_data_dir


class ShopifyBase(DeclarativeBase):
    pass


class ShopifyRecord(ShopifyBase):
    __tablename__ = "shopify_records"
    __table_args__ = (UniqueConstraint("shopify_id", name="uq_shopify_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shopify_id: Mapped[str] = mapped_column(String(128), index=True)
    raw_json: Mapped[str] = mapped_column(Text)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ShopifySyncRun(ShopifyBase):
    __tablename__ = "shopify_sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32))
    records_fetched: Mapped[int] = mapped_column(Integer, default=0)
    records_upserted: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_engines: dict[ResourceName, Any] = {}
_sessions: dict[ResourceName, sessionmaker[Session]] = {}


def db_path_for(resource: ResourceName) -> Path:
    return SHOPIFY_DATA_DIR / f"{resource}.db"


def _ensure_engine(resource: ResourceName):
    if resource in _engines:
        return _engines[resource], _sessions[resource]

    SHOPIFY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = db_path_for(resource)
    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
    )
    ShopifyBase.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    _engines[resource] = engine
    _sessions[resource] = session_factory
    return engine, session_factory


def get_shopify_session(resource: ResourceName) -> Session:
    _, session_factory = _ensure_engine(resource)
    return session_factory()


def extract_shopify_id(item: dict[str, Any]) -> str:
    for key in ("id", "shopify_id", "gid"):
        value = item.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    raise ValueError(f"Shopify record missing id field: {item!r}")


def upsert_records(resource: ResourceName, items: list[dict[str, Any]]) -> tuple[int, int]:
    if not items:
        return 0, 0

    db = get_shopify_session(resource)
    try:
        shopify_ids = [extract_shopify_id(item) for item in items]
        existing_rows = {
            row.shopify_id: row
            for row in db.scalars(
                select(ShopifyRecord).where(ShopifyRecord.shopify_id.in_(shopify_ids))
            ).all()
        }

        now = datetime.now(timezone.utc)
        upserted = 0
        for item in items:
            shopify_id = extract_shopify_id(item)
            payload = json.dumps(item, separators=(",", ":"), sort_keys=True)
            existing = existing_rows.get(shopify_id)
            if existing is not None:
                existing.raw_json = payload
                existing.synced_at = now
            else:
                db.add(ShopifyRecord(shopify_id=shopify_id, raw_json=payload, synced_at=now))
            upserted += 1

        db.commit()
        return len(items), upserted
    finally:
        db.close()


def count_records(resource: ResourceName) -> int:
    db = get_shopify_session(resource)
    try:
        return db.query(ShopifyRecord).count()
    finally:
        db.close()


def list_shopify_ids(resource: ResourceName) -> list[str]:
    db = get_shopify_session(resource)
    try:
        return list(db.scalars(select(ShopifyRecord.shopify_id)).all())
    finally:
        db.close()


def load_record_by_id(resource: ResourceName, shopify_id: str) -> dict[str, Any] | None:
    db = get_shopify_session(resource)
    try:
        row = db.scalars(
            select(ShopifyRecord).where(ShopifyRecord.shopify_id == shopify_id)
        ).first()
        if row is None:
            return None
        return json.loads(row.raw_json)
    finally:
        db.close()


def load_all_records(resource: ResourceName) -> list[dict[str, Any]]:
    db = get_shopify_session(resource)
    try:
        rows = db.query(ShopifyRecord).all()
        return [json.loads(row.raw_json) for row in rows]
    finally:
        db.close()


def latest_sync_run(resource: ResourceName) -> ShopifySyncRun | None:
    db = get_shopify_session(resource)
    try:
        return (
            db.query(ShopifySyncRun)
            .filter(ShopifySyncRun.resource == resource)
            .order_by(ShopifySyncRun.id.desc())
            .first()
        )
    finally:
        db.close()
