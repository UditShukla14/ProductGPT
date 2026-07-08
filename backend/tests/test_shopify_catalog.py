"""Tests for Shopify catalog search and order-based recommendations."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.shopify.catalog import (
    get_product_detail,
    products_bought_together,
    products_same_category,
    products_same_category_by_brand,
    search_products,
)
from app.shopify.storage import upsert_records


@pytest.fixture
def catalog_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.shopify.storage.SHOPIFY_DATA_DIR", tmp_path)
    monkeypatch.setattr("app.shopify.storage._engines", {})
    monkeypatch.setattr("app.shopify.storage._sessions", {})

    upsert_records(
        "products",
        [
            {
                "id": "100",
                "title": "Carrier Condenser 3 Ton",
                "vendor": "Carrier",
                "product_type": "Condenser",
                "handle": "carrier-condenser-3-ton",
                "tags": ["hvac", "outdoor"],
                "variants": [{"id": "v100", "sku": "COND-3T", "price": "2499.00"}],
                "images": [{"src": "https://example.com/condenser.jpg"}],
            },
            {
                "id": "200",
                "title": "Goodman Coil 3 Ton",
                "vendor": "Goodman",
                "product_type": "Coil",
                "handle": "goodman-coil-3-ton",
                "variants": [{"id": "v200", "sku": "COIL-3T", "price": "899.00"}],
            },
            {
                "id": "300",
                "title": "Trane Condenser 4 Ton",
                "vendor": "Trane",
                "product_type": "Condenser",
                "handle": "trane-condenser-4-ton",
                "variants": [{"id": "v300", "sku": "COND-4T", "price": "2899.00"}],
            },
            {
                "id": "400",
                "title": "Goodman Condenser 3 Ton",
                "vendor": "Goodman",
                "product_type": "Condenser",
                "handle": "goodman-condenser-3-ton",
                "variants": [{"id": "v400", "sku": "GMAN-3T", "price": "2199.00"}],
            },
        ],
    )

    upsert_records(
        "orders",
        [
            {
                "id": "order-1",
                "line_items": [
                    {"product_id": "100"},
                    {"product_id": "200"},
                ],
            },
            {
                "id": "order-2",
                "line_items": [
                    {"product_id": "100"},
                    {"product_id": "200"},
                    {"product_id": "300"},
                ],
            },
            {
                "id": "order-3",
                "line_items": [{"product_id": "300"}],
            },
        ],
    )

    return tmp_path


def test_search_products_by_title_and_sku(catalog_data):
    by_title = search_products("Carrier", limit=5)
    assert [item["id"] for item in by_title] == ["100"]

    by_sku = search_products("COND-3T", limit=5)
    assert [item["id"] for item in by_sku] == ["100"]


def test_get_product_detail(catalog_data):
    detail = get_product_detail("100")
    assert detail is not None
    assert detail["title"] == "Carrier Condenser 3 Ton"
    assert detail["sku"] == "COND-3T"
    assert detail["image_url"] == "https://example.com/condenser.jpg"


def test_products_bought_together(catalog_data):
    items = products_bought_together("100", limit=5)
    assert [item["product"]["id"] for item in items] == ["200", "300"]
    assert items[0]["order_count"] == 2
    assert items[1]["order_count"] == 1


def test_products_same_category(catalog_data):
    items = products_same_category("100", limit=5)
    assert {item["id"] for item in items} == {"300", "400"}


def test_products_same_category_by_brand(catalog_data):
    grouped = products_same_category_by_brand("100", per_brand_limit=5)
    assert grouped["category"] == "Condenser"
    assert grouped["current_vendor"] == "Carrier"
    assert [brand["vendor"] for brand in grouped["brands"]] == ["Goodman", "Trane"]
    assert [product["id"] for product in grouped["brands"][0]["products"]] == ["400"]
    assert [product["id"] for product in grouped["brands"][1]["products"]] == ["300"]
