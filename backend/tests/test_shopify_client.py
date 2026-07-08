from app.shopify.client import extract_list_items, extract_single_item

SAMPLE_PRODUCT_LIST_RESPONSE = {
    "success": True,
    "data": [
        {
            "id": "10375285702965",
            "shopify_id": "gid://shopify/Product/10375285702965",
            "title": "0130M00001P THERMOSTAT,DEFROST 89\" LEAD",
            "handle": "0130m00001p-thermostat-defrost-89-lead",
            "vendor": "product options & redirection",
            "product_type": "",
            "status": "active",
            "tags": ["0130M00001P", "Thermostats"],
            "images": [],
            "variants": [
                {
                    "id": "52190981554485",
                    "shopify_id": "gid://shopify/ProductVariant/52190981554485",
                    "title": "Default Title",
                    "price": "100.00",
                    "sku": "MSZ-GX18NL",
                    "inventory_quantity": 5,
                    "available_for_sale": True,
                }
            ],
        },
        {
            "id": "10375041679669",
            "shopify_id": "gid://shopify/Product/10375041679669",
            "title": "3.0 Ton Goodman",
            "handle": "3-0-ton-goodman",
            "vendor": "demo",
            "product_type": "Condenser Coil",
            "status": "active",
            "tags": ["GLZT7CA3610"],
            "images": [
                {
                    "id": "63861499625781",
                    "url": "https://cdn.shopify.com/example.jpg",
                }
            ],
            "variants": [
                {
                    "id": "52190546821429",
                    "sku": "GLZT7CA3610 AMVT42CP1300",
                    "price": "0.00",
                    "inventory_quantity": 0,
                    "available_for_sale": False,
                }
            ],
        },
    ],
    "message": None,
    "pagination": {
        "limit": 20,
        "has_next_page": True,
        "has_previous_page": False,
        "start_cursor": "abc",
        "end_cursor": "def",
    },
}


def test_fetch_page_sends_limit_when_configured():
    from app.shopify.client import ShopifyApiClient

    client = ShopifyApiClient(
        base_url="https://shop.worxstream.io/api/v1",
        token="test-token",
        shop_domain="example.myshopify.com",
        page_limit=50,
    )
    captured: dict = {}

    def fake_request(method, url, params=None):
        captured["url"] = url
        captured["params"] = params
        return {
            "success": True,
            "data": [],
            "pagination": {"has_next_page": False},
        }

    client._request = fake_request  # type: ignore[method-assign]
    client.fetch_page("orders")
    assert captured["url"].endswith("/orders")
    assert captured["params"] == {"limit": 50}

    client.fetch_page("orders", after="cursor123")
    assert captured["params"] == {"limit": 50, "after": "cursor123"}

    client.page_limit = 0
    client.fetch_page("orders")
    assert captured["params"] is None


def test_extract_product_list_items():
    items = extract_list_items("products", SAMPLE_PRODUCT_LIST_RESPONSE)
    assert len(items) == 2
    assert items[0]["id"] == "10375285702965"
    assert items[0]["variants"][0]["sku"] == "MSZ-GX18NL"


def test_extract_single_item_from_worxstream_envelope():
    payload = {"success": True, "data": SAMPLE_PRODUCT_LIST_RESPONSE["data"][0]}
    item = extract_single_item(payload)
    assert item["handle"] == "0130m00001p-thermostat-defrost-89-lead"


SAMPLE_PRODUCT_DETAIL_RESPONSE = {
    "success": True,
    "data": {
        "id": "9785832472867",
        "shopify_id": "gid://shopify/Product/9785832472867",
        "title": "MRCOOL VersaPro 4.0 Ton R454B Central Ducted Heat Pump Split System MVP-48-HP-230A00-O",
        "handle": "mrcool-versapro-4-0-ton-r454b-central-ducted-heat-pump-split-system-mvp-48-hp-230a00-o",
        "vendor": "MR COOL",
        "product_type": "Central Ducted Systems",
        "status": "active",
        "tags": ["MVP-48-HP-230A00-O", "VersaPro"],
        "description": "MrCool VersaPro 4-Ton Central Ducted Heat Pump Split System.",
        "images": [
            {
                "id": "48550301958435",
                "shopify_id": "gid://shopify/ProductImage/48550301958435",
                "url": "https://cdn.shopify.com/s/files/1/0766/1171/5363/files/mrcool-versapro.jpg",
                "alt_text": "MRCOOL VersaPro 4.0 Ton R454B Central Ducted Heat Pump Split System",
                "width": 1000,
                "height": 1000,
            }
        ],
        "variants": [
            {
                "id": "52465015128355",
                "shopify_id": "gid://shopify/ProductVariant/52465015128355",
                "title": "Default Title",
                "price": "3856.00",
                "compare_at_price": None,
                "sku": "MVP-48-HP-230A00-O",
                "inventory_quantity": 27,
                "available_for_sale": True,
                "position": 2,
                "weight": 0,
                "weight_unit": "POUNDS",
                "requires_shipping": True,
                "taxable": True,
                "barcode": "5299684643770",
                "created_at": "2025-01-31T16:52:40Z",
                "updated_at": "2026-07-08T03:17:07Z",
            }
        ],
        "options": [
            {
                "id": "gid://shopify/ProductOption/12279524753699",
                "name": "Title",
                "position": 1,
                "values": ["Default Title"],
            }
        ],
        "created_at": "2025-01-31T16:52:38Z",
        "updated_at": "2026-07-08T03:17:06Z",
    },
    "message": None,
}


def test_extract_product_detail_from_worxstream_envelope():
    product = extract_single_item(SAMPLE_PRODUCT_DETAIL_RESPONSE)
    assert product["id"] == "9785832472867"
    assert product["product_type"] == "Central Ducted Systems"
    assert product["variants"][0]["barcode"] == "5299684643770"


def test_product_detail_graph_includes_description_and_variant_fields():
    from app.shopify.graph.builder import extract_product_elements

    product = SAMPLE_PRODUCT_DETAIL_RESPONSE["data"]
    nodes, edges = extract_product_elements(product)

    product_node = next(node for node in nodes if node.type == "product")
    assert product_node.properties["shopify_id"] == "9785832472867"
    assert product_node.properties["vendor"] == "MR COOL"
    assert product_node.properties["product_type"] == "Central Ducted Systems"
    assert "VersaPro" in product_node.properties["tags"]
    assert product_node.properties["description"].startswith("MrCool VersaPro")
    assert product_node.properties["image_alt_text"].startswith("MRCOOL VersaPro")
    assert product_node.properties["option_names"] == ["Title"]
    assert product_node.properties["created_at"] == "2025-01-31T16:52:38Z"

    variant_node = next(node for node in nodes if node.type == "variant")
    assert variant_node.properties["sku"] == "MVP-48-HP-230A00-O"
    assert variant_node.properties["price"] == "3856.00"
    assert variant_node.properties["barcode"] == "5299684643770"
    assert variant_node.properties["inventory_quantity"] == 27
    assert variant_node.properties["weight_unit"] == "POUNDS"
    assert variant_node.properties["requires_shipping"] is True
    assert len(edges) == 1
    assert edges[0].type == "has_variant"


def test_product_graph_includes_tags_and_image():
    from app.shopify.graph.builder import extract_product_elements

    product = SAMPLE_PRODUCT_LIST_RESPONSE["data"][1]
    nodes, edges = extract_product_elements(product)

    product_node = next(node for node in nodes if node.type == "product")
    assert product_node.properties["image_url"] == "https://cdn.shopify.com/example.jpg"
    assert "GLZT7CA3610" in product_node.properties["tags"]

    variant_node = next(node for node in nodes if node.type == "variant")
    assert variant_node.properties["sku"] == "GLZT7CA3610 AMVT42CP1300"
    assert variant_node.properties["available_for_sale"] is False
    assert len(edges) == 1
    assert edges[0].type == "has_variant"


SAMPLE_CUSTOMER_LIST_RESPONSE = {
    "success": True,
    "data": [
        {
            "id": "9568539607349",
            "shopify_id": "gid://shopify/Customer/9568539607349",
            "first_name": "parth",
            "last_name": "patel",
            "email": "parth@alphaparktech.com",
            "phone": "+917096204172",
            "tags": [],
            "number_of_orders": "0",
            "total_spent": {"amount": "0.0", "currency_code": "USD"},
            "default_address": {
                "address1": "Unit 1284",
                "address2": "2210 Holly Springs Parkway",
                "city": "Holly Springs",
                "province": "Georgia",
                "country": "United States",
                "zip": "30115",
            },
        },
        {
            "id": "10965635825973",
            "shopify_id": "gid://shopify/Customer/10965635825973",
            "first_name": "Vedant",
            "last_name": "Kale",
            "email": "vedant@acunitsforless.com",
            "phone": None,
            "tags": [],
            "number_of_orders": "0",
            "total_spent": {"amount": "0.0", "currency_code": "USD"},
            "default_address": {
                "address1": "3645 Wellborn Rd",
                "city": "Bryan",
                "province": "Texas",
                "country": "United States",
                "zip": "77801",
            },
        },
    ],
    "message": None,
    "pagination": {
        "limit": 20,
        "has_next_page": False,
        "has_previous_page": False,
        "start_cursor": "abc",
        "end_cursor": "def",
    },
}


def test_extract_customer_list_items():
    items = extract_list_items("customers", SAMPLE_CUSTOMER_LIST_RESPONSE)
    assert len(items) == 2
    assert items[0]["email"] == "parth@alphaparktech.com"


def test_customer_graph_includes_address_and_spending():
    from app.shopify.graph.builder import extract_customer_element

    customer = SAMPLE_CUSTOMER_LIST_RESPONSE["data"][0]
    node = extract_customer_element(customer)
    assert node is not None
    assert node.properties["shopify_id"] == "9568539607349"
    assert node.properties["shopify_gid"] == "gid://shopify/Customer/9568539607349"
    assert node.properties["phone"] == "+917096204172"
    assert node.properties["city"] == "Holly Springs"
    assert node.properties["province"] == "Georgia"
    assert node.properties["total_spent_amount"] == "0.0"
    assert node.properties["total_spent_currency"] == "USD"
    assert node.label == "parth patel"


SAMPLE_ORDER_WITH_VARIANT = {
    "id": "7491384181045",
    "shopify_id": "gid://shopify/Order/7491384181045",
    "order_number": "#1025",
    "email": "vedant@acunitsforless.com",
    "tags": ["Vendor: Trane"],
    "financial_status": "PAID",
    "fulfillment_status": "FULFILLED",
    "currency_code": "USD",
    "total_price": {"amount": "2532.5", "currency_code": "USD"},
    "customer": {
        "id": "10965635825973",
        "shopify_id": "gid://shopify/Customer/10965635825973",
        "first_name": "Vedant",
        "last_name": "Kale",
        "email": "vedant@acunitsforless.com",
    },
    "line_items": [
        {
            "id": "18293226340661",
            "shopify_id": "gid://shopify/LineItem/18293226340661",
            "title": "Trane 5 ton Light Commercial Air Handler",
            "quantity": 1,
            "sku": "TWE060K3A",
            "discounted_unit_price": {"amount": "2532.5", "currencyCode": "USD"},
            "variant": {
                "id": "52533172666677",
                "shopify_id": "gid://shopify/ProductVariant/52533172666677",
                "sku": "TWE060K3A",
            },
            "product": None,
        }
    ],
}

SAMPLE_ORDER_SKU_ONLY = {
    "id": "7121222271285",
    "shopify_id": "gid://shopify/Order/7121222271285",
    "order_number": "#1016",
    "financial_status": "PAID",
    "fulfillment_status": "UNFULFILLED",
    "total_price": {"amount": "9008.0", "currency_code": "USD"},
    "customer": {"id": "9568539607349", "email": "parth@alphaparktech.com"},
    "line_items": [
        {
            "id": "17534278795573",
            "title": "1.5 Ton Goodman system",
            "quantity": 1,
            "sku": "GLXS4BA1810 GR9S800403AX CAPTA2422A3",
            "variant": None,
            "product": None,
        }
    ],
}

SAMPLE_ORDER_LINE_ITEM_ONLY = {
    "id": "7144315814197",
    "order_number": "#1017",
    "financial_status": "PAID",
    "total_price": {"amount": "50.9", "currency_code": "USD"},
    "customer": {"id": "9568539607349", "email": "parth@alphaparktech.com"},
    "line_items": [
        {
            "id": "17601540915509",
            "title": "(Sample) Coconut Bar Soap",
            "quantity": 2,
            "sku": "",
            "variant": None,
            "product": None,
        }
    ],
}


def test_extract_order_list_items():
    payload = {"success": True, "data": [SAMPLE_ORDER_WITH_VARIANT]}
    items = extract_list_items("orders", payload)
    assert len(items) == 1
    assert items[0]["order_number"] == "#1025"


def test_order_graph_with_nested_variant():
    from app.shopify.graph.builder import extract_order_elements

    nodes, edges = extract_order_elements(SAMPLE_ORDER_WITH_VARIANT)
    order_node = next(n for n in nodes if n.type == "order")
    assert order_node.label == "#1025"
    assert order_node.properties["total_price_amount"] == "2532.5"
    assert order_node.properties["financial_status"] == "PAID"

    variant_node = next(n for n in nodes if n.type == "variant")
    assert variant_node.properties["sku"] == "TWE060K3A"
    assert variant_node.properties["quantity"] == 1

    customer_edge = next(e for e in edges if e.type == "placed_order")
    variant_edge = next(e for e in edges if e.type == "ordered_variant")
    assert customer_edge.source == "customer:10965635825973"
    assert variant_edge.target == "variant:52533172666677"


def test_order_graph_sku_only_line_item():
    from app.shopify.graph.builder import extract_order_elements

    nodes, edges = extract_order_elements(SAMPLE_ORDER_SKU_ONLY)
    line_item_node = next(n for n in nodes if n.type == "line_item")
    assert "GLXS4BA1810" in line_item_node.properties["sku"]
    assert any(e.type == "ordered_line_item" for e in edges)


def test_order_graph_title_only_line_item():
    from app.shopify.graph.builder import extract_order_elements

    nodes, edges = extract_order_elements(SAMPLE_ORDER_LINE_ITEM_ONLY)
    line_item_node = next(n for n in nodes if n.type == "line_item")
    assert line_item_node.label == "(Sample) Coconut Bar Soap"
    assert line_item_node.properties["quantity"] == 2


SAMPLE_ORDER_DETAIL = {
    **SAMPLE_ORDER_WITH_VARIANT,
    "subtotal_price": {"amount": "2532.5", "currency_code": "USD"},
    "fulfillments": [
        {
            "id": "6749389095221",
            "status": "SUCCESS",
            "tracking_info": [{"number": "RXO101239", "company": "RXO"}],
        }
    ],
    "transactions": [
        {"id": "9250151924021", "status": "SUCCESS", "kind": "AUTHORIZATION"},
        {"id": "9250152022325", "status": "SUCCESS", "kind": "CAPTURE"},
    ],
    "line_items": [
        {
            **SAMPLE_ORDER_WITH_VARIANT["line_items"][0],
            "product": {
                "id": "10458798588213",
                "shopify_id": "gid://shopify/Product/10458798588213",
                "title": "Trane 5 ton Light Commercial Air Handler",
            },
        }
    ],
}


def test_fetch_detail_uses_single_item_endpoint():
    from app.shopify.client import ShopifyApiClient

    client = ShopifyApiClient(
        base_url="https://shop.worxstream.io/api/v1",
        token="test-token",
        shop_domain="example.myshopify.com",
    )
    captured: dict = {}

    def fake_fetch_page(resource, *, after=None, resource_id=None):
        captured["resource"] = resource
        captured["resource_id"] = resource_id
        return {"success": True, "data": SAMPLE_ORDER_DETAIL}

    client.fetch_page = fake_fetch_page  # type: ignore[method-assign]
    detail = client.fetch_detail("orders", "7491384181045")
    assert captured["resource"] == "orders"
    assert captured["resource_id"] == "7491384181045"
    assert detail["order_number"] == "#1025"


def test_request_retries_on_read_timeout():
    import httpx

    from app.shopify.client import ShopifyApiClient

    client = ShopifyApiClient(
        base_url="https://shop.worxstream.io/api/v1",
        token="test-token",
        shop_domain="example.myshopify.com",
        max_retries=2,
    )
    calls = {"n": 0}

    class OkResponse:
        status_code = 200
        headers: dict = {}

        def raise_for_status(self):
            return None

        def json(self):
            return {"success": True, "data": {"id": "1"}}

    def fake_request(method, url, params=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ReadTimeout("timed out")
        return OkResponse()

    client._client.request = fake_request  # type: ignore[method-assign]
    payload = client._request("GET", "/products/1")
    assert calls["n"] == 2
    assert payload["data"]["id"] == "1"


def test_order_detail_graph_includes_fulfillments_and_product_link():
    from app.shopify.graph.builder import extract_order_elements

    nodes, edges = extract_order_elements(SAMPLE_ORDER_DETAIL)
    order_node = next(n for n in nodes if n.type == "order")
    assert order_node.properties["fulfillment_count"] == 1
    assert order_node.properties["transaction_count"] == 2
    assert order_node.properties["tracking_numbers"] == ["RXO101239"]
    assert order_node.properties["subtotal_price_amount"] == "2532.5"

    product_node = next(n for n in nodes if n.type == "product")
    assert product_node.properties["shopify_id"] == "10458798588213"
    assert any(e.type == "has_variant" for e in edges)


def test_customer_detail_graph_includes_addresses_and_flags():
    from app.shopify.graph.builder import extract_customer_element

    customer = {
        **SAMPLE_CUSTOMER_LIST_RESPONSE["data"][0],
        "verified_email": True,
        "tax_exempt": False,
        "addresses": [
            SAMPLE_CUSTOMER_LIST_RESPONSE["data"][0]["default_address"],
        ],
    }
    node = extract_customer_element(customer)
    assert node is not None
    assert node.properties["verified_email"] is True
    assert node.properties["tax_exempt"] is False
    assert node.properties["address_count"] == 1
