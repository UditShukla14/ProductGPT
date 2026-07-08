"""Tests for Shopify detail enrichment during sync."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.shopify.client import ShopifyApiClient
from app.shopify.storage import ShopifyRecord, count_records, get_shopify_session, upsert_records
from app.shopify.sync import enrich_resource_details


@pytest.fixture
def customers_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "customers.db"
    monkeypatch.setattr("app.shopify.storage.SHOPIFY_DATA_DIR", tmp_path)
    monkeypatch.setattr("app.shopify.storage._engines", {})
    monkeypatch.setattr("app.shopify.storage._sessions", {})

    upsert_records(
        "customers",
        [
            {"id": "9568539607349", "email": "parth@alphaparktech.com"},
            {"id": "10965635825973", "email": "vedant@acunitsforless.com"},
        ],
    )
    assert db_path.exists()
    return tmp_path


def test_enrich_resource_details_upserts_full_payload(customers_db, monkeypatch):
    detail_payloads = {
        "9568539607349": {
            "id": "9568539607349",
            "email": "parth@alphaparktech.com",
            "verified_email": True,
            "addresses": [{"city": "Holly Springs"}],
        },
        "10965635825973": {
            "id": "10965635825973",
            "email": "vedant@acunitsforless.com",
            "verified_email": True,
            "addresses": [],
        },
    }

    class FakeClient(ShopifyApiClient):
        def fetch_detail(self, resource, resource_id):
            return detail_payloads[resource_id]

    client = FakeClient(
        base_url="https://shop.worxstream.io/api/v1",
        token="test-token",
        shop_domain="example.myshopify.com",
    )
    monkeypatch.setattr("app.config.settings.shopify_enrich_details", True)

    summary = enrich_resource_details(client, "customers")
    assert summary.enriched == 2
    assert summary.failed == 0
    assert count_records("customers") == 2

    db = get_shopify_session("customers")
    try:
        rows = db.query(ShopifyRecord).all()
        by_id = {row.shopify_id: json.loads(row.raw_json) for row in rows}
        assert by_id["9568539607349"]["verified_email"] is True
        assert by_id["9568539607349"]["addresses"][0]["city"] == "Holly Springs"
    finally:
        db.close()


def test_enrich_resource_details_with_explicit_ids(customers_db, monkeypatch):
    detail_payloads = {
        "9568539607349": {
            "id": "9568539607349",
            "email": "parth@alphaparktech.com",
            "verified_email": True,
        },
    }

    class FakeClient(ShopifyApiClient):
        def fetch_detail(self, resource, resource_id):
            return detail_payloads[resource_id]

    client = FakeClient(
        base_url="https://shop.worxstream.io/api/v1",
        token="test-token",
        shop_domain="example.myshopify.com",
    )
    monkeypatch.setattr("app.config.settings.shopify_enrich_details", True)

    summary = enrich_resource_details(
        client,
        "customers",
        resource_ids=["9568539607349"],
    )
    assert summary.enriched == 1
    assert summary.failed == 0

    db = get_shopify_session("customers")
    try:
        row = db.query(ShopifyRecord).filter_by(shopify_id="9568539607349").one()
        payload = json.loads(row.raw_json)
        assert payload["verified_email"] is True
        untouched = db.query(ShopifyRecord).filter_by(shopify_id="10965635825973").one()
        assert "verified_email" not in json.loads(untouched.raw_json)
    finally:
        db.close()


def test_enrich_continues_after_per_record_failure(customers_db, monkeypatch):
    class FakeClient(ShopifyApiClient):
        def fetch_detail(self, resource, resource_id):
            if resource_id == "9568539607349":
                raise RuntimeError("timed out")
            return {
                "id": resource_id,
                "email": "vedant@acunitsforless.com",
                "verified_email": True,
            }

    client = FakeClient(
        base_url="https://shop.worxstream.io/api/v1",
        token="test-token",
        shop_domain="example.myshopify.com",
    )

    summary = enrich_resource_details(client, "customers")
    assert summary.enriched == 1
    assert summary.failed == 1

    db = get_shopify_session("customers")
    try:
        by_id = {
            row.shopify_id: json.loads(row.raw_json)
            for row in db.query(ShopifyRecord).all()
        }
        assert "verified_email" not in by_id["9568539607349"]
        assert by_id["10965635825973"]["verified_email"] is True
    finally:
        db.close()


def test_enrich_skips_already_enriched_records(customers_db, monkeypatch):
    upsert_records(
        "customers",
        [
            {
                "id": "9568539607349",
                "email": "parth@alphaparktech.com",
                "verified_email": True,
                "addresses": [],
            }
        ],
    )

    calls: list[str] = []

    class FakeClient(ShopifyApiClient):
        def fetch_detail(self, resource, resource_id):
            calls.append(resource_id)
            return {
                "id": resource_id,
                "email": "vedant@acunitsforless.com",
                "verified_email": True,
            }

    client = FakeClient(
        base_url="https://shop.worxstream.io/api/v1",
        token="test-token",
        shop_domain="example.myshopify.com",
    )

    summary = enrich_resource_details(
        client,
        "customers",
        skip_already_enriched=True,
    )
    assert summary.skipped == 1
    assert summary.enriched == 1
    assert calls == ["10965635825973"]
