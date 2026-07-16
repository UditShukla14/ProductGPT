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


def test_products_bought_together_resolves_line_items_by_sku(catalog_data):
    upsert_records(
        "products",
        [
            {
                "id": "900",
                "title": "Trane Air Handler",
                "vendor": "Trane",
                "product_type": "Air Handler",
                "variants": [{"id": "v900", "sku": "TWE060K3A", "price": "2532.50"}],
            },
            {
                "id": "901",
                "title": "Trane Thermostat",
                "vendor": "Trane",
                "product_type": "Thermostats",
                "variants": [{"id": "v901", "sku": "TCONT824", "price": "199.00"}],
            },
        ],
    )
    upsert_records(
        "orders",
        [
            {
                "id": "order-sku-1",
                "line_items": [
                    {
                        "sku": "TWE060K3A",
                        "variant": {"id": "52533172666677", "sku": "TWE060K3A"},
                    },
                    {
                        "sku": "TCONT824",
                        "variant": {"id": "52533172666678", "sku": "TCONT824"},
                    },
                ],
            },
            {
                "id": "order-sku-2",
                "line_items": [
                    {
                        "sku": "TWE060K3A",
                        "variant": {"id": "52533172666677", "sku": "TWE060K3A"},
                    },
                ],
            },
        ],
    )

    items = products_bought_together("900", limit=5)
    assert [item["product"]["id"] for item in items] == ["901"]
    assert items[0]["order_count"] == 1


def test_products_bought_together_matches_bundle_skus_with_model_code(catalog_data):
    upsert_records(
        "products",
        [
            {
                "id": "910",
                "title": "Mitsubishi SUZ-AA12NL Outdoor Unit",
                "vendor": "Mitsubishi",
                "product_type": "Heat Pump Outdoor Unit",
                "variants": [{"id": "v910", "sku": "SUZ-AA12NL", "price": "1299.00"}],
            },
            {
                "id": "911",
                "title": "Mitsubishi SUZ-AA12NL & MSZ-EX12NLW System",
                "vendor": "Mitsubishi",
                "product_type": "Wall Mounted Heat Pump System",
                "variants": [{"id": "v911", "sku": "SUZ-AA12NL, MSZ-EX12NLW", "price": "2499.00"}],
            },
            {
                "id": "912",
                "title": "Lineset MLS143812T-30",
                "vendor": "Mitsubishi",
                "product_type": "Accessories",
                "variants": [{"id": "v912", "sku": "MLS143812T-30", "price": "199.00"}],
            },
        ],
    )
    upsert_records(
        "orders",
        [
            {
                "id": "order-bundle-1",
                "line_items": [
                    {"sku": "SUZ-AA12NL, MSZ-EX12NLW"},
                    {"sku": "MLS143812T-30"},
                ],
            },
        ],
    )

    items = products_bought_together("910", limit=5)
    assert [item["product"]["id"] for item in items] == ["912", "911"]
    assert items[0]["order_count"] == 1
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


def test_products_same_category_by_brand_filters_btu_and_zone_keywords(catalog_data):
    upsert_records(
        "products",
        [
            {
                "id": "500",
                "title": "Mitsubishi 12,000 BTU Single Zone Mini Split",
                "vendor": "Mitsubishi",
                "product_type": "Mini Split Heat Pump System",
                "tags": ["MSZ-JP12WA"],
                "variants": [{"id": "v500", "sku": "MSZ-JP12WA", "price": "1999.00"}],
            },
            {
                "id": "600",
                "title": "MRCOOL 12,000 BTU Single Zone Mini Split Heat Pump",
                "vendor": "MRCOOL",
                "product_type": "Mini Split Heat Pump System",
                "tags": ["DIY-12K"],
                "variants": [{"id": "v600", "sku": "DIY-12K", "price": "1499.00"}],
            },
            {
                "id": "700",
                "title": "MRCOOL 18,000 BTU Single Zone Mini Split Heat Pump",
                "vendor": "MRCOOL",
                "product_type": "Mini Split Heat Pump System",
                "tags": ["DIY-18K"],
                "variants": [{"id": "v700", "sku": "DIY-18K", "price": "1699.00"}],
            },
            {
                "id": "800",
                "title": "MRCOOL 12,000 BTU 2 Zone Mini Split Heat Pump",
                "vendor": "MRCOOL",
                "product_type": "Mini Split Heat Pump System",
                "tags": ["DIY-12K-2Z"],
                "variants": [{"id": "v800", "sku": "DIY-12K-2Z", "price": "1799.00"}],
            },
        ],
    )

    grouped = products_same_category_by_brand("500", per_brand_limit=5)
    assert grouped["category"] == "Mini Split Heat Pump System"
    assert "BTU: 12,000 BTU" in grouped["match_keywords"]
    assert "Zone: Single zone" in grouped["match_keywords"]
    assert "Type: Mini-split system" in grouped["match_keywords"]
    assert grouped["current_vendor"] == "Mitsubishi"
    assert [brand["vendor"] for brand in grouped["brands"]] == ["MRCOOL"]
    assert [product["id"] for product in grouped["brands"][0]["products"]] == ["600"]


def test_related_products_require_similar_profile_not_btu_keyword_only(catalog_data):
    """Nearly-same mini-splits match; PTACs / wrong capacity / components do not."""
    upsert_records(
        "products",
        [
            {
                "id": "910",
                "title": "Pioneer 12,000 BTU 17 SEER2 Ductless Mini-Split Heat Pump 115V",
                "vendor": "Pioneer",
                "product_type": "Mini-Split Inverter AC Heat Pump System",
                "description": "R-32 inverter heat pump full set",
                "tags": ["WYT012"],
                "variants": [{"id": "v910", "sku": "WYT012", "price": "809.00"}],
            },
            {
                "id": "920",
                "title": "MRCOOL 12,000 BTU 17 SEER2 Mini Split Heat Pump System 115V",
                "vendor": "MRCOOL",
                "product_type": "Mini Split Heat Pump System",
                "tags": ["DIY-12"],
                "variants": [{"id": "v920", "sku": "DIY-12", "price": "1199.00"}],
            },
            {
                "id": "925",
                "title": "Daikin 12,000 BTU Mini Split Heat Pump System",
                "vendor": "Daikin",
                "product_type": "Mini Split Heat Pump System",
                "tags": ["DX12"],
                "variants": [{"id": "v925", "sku": "DX12", "price": "1399.00"}],
            },
            {
                "id": "930",
                "title": "GE 12,000 BTU PTAC Heat Pump",
                "vendor": "GE",
                "product_type": "PTAC",
                "tags": ["AZVS12"],
                "variants": [{"id": "v930", "sku": "AZVS12", "price": "999.00"}],
            },
            {
                "id": "935",
                "title": "MRCOOL 12,000 BTU Mini Split Condenser Only",
                "vendor": "MRCOOL",
                "product_type": "Mini Split Condenser",
                "tags": ["DIY-12-C"],
                "variants": [{"id": "v935", "sku": "DIY-12-C", "price": "799.00"}],
            },
            {
                "id": "940",
                "title": "Pioneer 18,000 BTU Mini-Split Inverter Heat Pump System",
                "vendor": "Pioneer",
                "product_type": "Mini-Split Inverter AC Heat Pump System",
                "tags": ["WYT018"],
                "variants": [{"id": "v940", "sku": "WYT018", "price": "1499.00"}],
            },
            {
                "id": "950",
                "title": "Daikin 24,000 BTU Mini Split Heat Pump",
                "vendor": "Daikin",
                "product_type": "Mini Split Heat Pump System",
                "tags": ["DX24"],
                "variants": [{"id": "v950", "sku": "DX24", "price": "1899.00"}],
            },
        ],
    )

    grouped = products_same_category_by_brand("910", per_brand_limit=5)
    assert grouped["match_keywords"][0] == "BTU: 12,000 BTU"
    assert "SEER2: 17" in grouped["match_keywords"]
    assert "Voltage: 115V" in grouped["match_keywords"]
    assert grouped["current_vendor"] == "Pioneer"
    brands = {brand["vendor"]: [p["id"] for p in brand["products"]] for brand in grouped["brands"]}
    assert brands == {"Daikin": ["925"], "MRCOOL": ["920"]}
