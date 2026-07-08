from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import networkx as nx

from app.shopify.graph.schemas import ShopifyGraphEdgeType, ShopifyGraphNodeType
from app.shopify.storage import load_all_records

EDGE_ATTR = "type"

REL_TYPE_MAP: dict[ShopifyGraphEdgeType, str] = {
    "has_variant": "HAS_VARIANT",
    "placed_order": "PLACED_ORDER",
    "ordered_product": "ORDERED_PRODUCT",
    "ordered_variant": "ORDERED_VARIANT",
    "ordered_line_item": "ORDERED_LINE_ITEM",
}

CYPHER_REL_TO_EDGE: dict[str, ShopifyGraphEdgeType] = {v: k for k, v in REL_TYPE_MAP.items()}


@dataclass
class GraphElementNode:
    id: str
    label: str
    type: ShopifyGraphNodeType
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphElementEdge:
    source: str
    target: str
    type: ShopifyGraphEdgeType


def _product_id(value: Any) -> str:
    return f"product:{value}"


def _variant_id(value: Any) -> str:
    return f"variant:{value}"


def _customer_id(value: Any) -> str:
    return f"customer:{value}"


def _order_id(value: Any) -> str:
    return f"order:{value}"


def _line_item_id(value: Any) -> str:
    return f"line_item:{value}"


def _first_str(item: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = item.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if item is not None and str(item).strip()]


def _money_fields(value: Any) -> tuple[str | None, str | None]:
    if not isinstance(value, dict):
        return None, None
    amount = _first_str(value, "amount")
    currency = _first_str(value, "currency_code", "currencyCode", "currency")
    return amount, currency


def _address_fields(address: Any) -> dict[str, str | None]:
    if not isinstance(address, dict):
        return {}
    return {
        "address1": _first_str(address, "address1"),
        "address2": _first_str(address, "address2"),
        "city": _first_str(address, "city"),
        "province": _first_str(address, "province", "state"),
        "country": _first_str(address, "country"),
        "zip": _first_str(address, "zip", "postal_code"),
        "address_phone": _first_str(address, "phone"),
    }


def _primary_image_url(product: dict[str, Any]) -> str | None:
    url, _ = _primary_image(product)
    return url


def _primary_image(product: dict[str, Any]) -> tuple[str | None, str | None]:
    images = product.get("images")
    if not isinstance(images, list):
        return None, None
    for image in images:
        if not isinstance(image, dict):
            continue
        url = _first_str(image, "url", "src")
        if url:
            return url, _first_str(image, "alt_text", "altText", "alt")
    return None, None


def _product_option_names(product: dict[str, Any]) -> list[str]:
    options = product.get("options")
    if not isinstance(options, list):
        return []
    names: list[str] = []
    for option in options:
        if isinstance(option, dict):
            name = _first_str(option, "name")
            if name:
                names.append(name)
    return names


def _variants(product: dict[str, Any]) -> list[dict[str, Any]]:
    variants = product.get("variants")
    if isinstance(variants, list):
        return [variant for variant in variants if isinstance(variant, dict)]
    return []


def _fulfillment_tracking_numbers(fulfillments: Any) -> list[str]:
    if not isinstance(fulfillments, list):
        return []
    numbers: list[str] = []
    for fulfillment in fulfillments:
        if not isinstance(fulfillment, dict):
            continue
        tracking_info = fulfillment.get("tracking_info")
        if not isinstance(tracking_info, list):
            continue
        for entry in tracking_info:
            if not isinstance(entry, dict):
                continue
            number = _first_str(entry, "number")
            if number:
                numbers.append(number)
    return numbers


def _line_items(order: dict[str, Any]) -> list[dict[str, Any]]:
    line_items = order.get("line_items")
    if isinstance(line_items, list):
        return [item for item in line_items if isinstance(item, dict)]
    return []


def extract_product_elements(product: dict[str, Any]) -> tuple[list[GraphElementNode], list[GraphElementEdge]]:
    nodes: list[GraphElementNode] = []
    edges: list[GraphElementEdge] = []

    product_key = _first_str(product, "id", "shopify_id")
    if not product_key:
        return nodes, edges

    product_node_id = _product_id(product_key)
    title = _first_str(product, "title", "name") or product_key
    image_url, image_alt_text = _primary_image(product)
    nodes.append(
        GraphElementNode(
            id=product_node_id,
            label=title,
            type="product",
            properties={
                "shopify_id": product_key,
                "shopify_gid": _first_str(product, "shopify_id"),
                "title": title,
                "handle": _first_str(product, "handle"),
                "vendor": _first_str(product, "vendor"),
                "product_type": _first_str(product, "product_type", "type"),
                "status": _first_str(product, "status"),
                "description": _first_str(product, "description", "body_html"),
                "tags": _string_list(product.get("tags")),
                "image_url": image_url,
                "image_alt_text": image_alt_text,
                "option_names": _product_option_names(product),
                "created_at": _first_str(product, "created_at"),
                "updated_at": _first_str(product, "updated_at"),
            },
        )
    )

    for variant in _variants(product):
        variant_key = _first_str(variant, "id", "variant_id")
        if not variant_key:
            continue
        variant_node_id = _variant_id(variant_key)
        sku = _first_str(variant, "sku")
        label = sku or _first_str(variant, "title") or variant_key
        nodes.append(
            GraphElementNode(
                id=variant_node_id,
                label=label,
                type="variant",
                properties={
                    "shopify_id": variant_key,
                    "shopify_gid": _first_str(variant, "shopify_id"),
                    "sku": sku,
                    "title": _first_str(variant, "title"),
                    "price": _first_str(variant, "price"),
                    "compare_at_price": _first_str(variant, "compare_at_price"),
                    "barcode": _first_str(variant, "barcode"),
                    "inventory_quantity": variant.get("inventory_quantity"),
                    "available_for_sale": variant.get("available_for_sale"),
                    "position": variant.get("position"),
                    "weight": variant.get("weight"),
                    "weight_unit": _first_str(variant, "weight_unit"),
                    "requires_shipping": variant.get("requires_shipping"),
                    "taxable": variant.get("taxable"),
                    "created_at": _first_str(variant, "created_at"),
                    "updated_at": _first_str(variant, "updated_at"),
                    "product_id": product_key,
                },
            )
        )
        edges.append(GraphElementEdge(source=product_node_id, target=variant_node_id, type="has_variant"))

    return nodes, edges


def extract_customer_element(customer: dict[str, Any]) -> GraphElementNode | None:
    customer_key = _first_str(customer, "id", "customer_id", "shopify_id")
    if not customer_key:
        return None

    first_name = _first_str(customer, "first_name", "firstName")
    last_name = _first_str(customer, "last_name", "lastName")
    email = _first_str(customer, "email")
    phone = _first_str(customer, "phone")
    label = " ".join(part for part in (first_name, last_name) if part) or email or customer_key
    total_spent_amount, total_spent_currency = _money_fields(customer.get("total_spent"))
    address = _address_fields(customer.get("default_address"))

    return GraphElementNode(
        id=_customer_id(customer_key),
        label=label,
        type="customer",
        properties={
            "shopify_id": customer_key,
            "shopify_gid": _first_str(customer, "shopify_id"),
            "email": email,
            "phone": phone,
            "first_name": first_name,
            "last_name": last_name,
            "tags": _string_list(customer.get("tags")),
            "number_of_orders": _first_str(customer, "number_of_orders"),
            "total_spent_amount": total_spent_amount,
            "total_spent_currency": total_spent_currency,
            "verified_email": customer.get("verified_email"),
            "tax_exempt": customer.get("tax_exempt"),
            "note": _first_str(customer, "note"),
            "address_count": (
                len(customer["addresses"])
                if isinstance(customer.get("addresses"), list)
                else None
            ),
            **address,
        },
    )


def extract_order_elements(order: dict[str, Any]) -> tuple[list[GraphElementNode], list[GraphElementEdge]]:
    nodes: list[GraphElementNode] = []
    edges: list[GraphElementEdge] = []

    order_key = _first_str(order, "id", "order_id", "shopify_id")
    if not order_key:
        return nodes, edges

    order_node_id = _order_id(order_key)
    order_number = _first_str(order, "order_number", "name", "number")
    label = order_number or order_key
    total_amount, total_currency = _money_fields(order.get("total_price"))
    subtotal_amount, subtotal_currency = _money_fields(order.get("subtotal_price"))
    if not total_currency:
        total_currency = _first_str(order, "currency_code")
    fulfillments = order.get("fulfillments")
    transactions = order.get("transactions")
    fulfillment_count = len(fulfillments) if isinstance(fulfillments, list) else None
    transaction_count = len(transactions) if isinstance(transactions, list) else None

    nodes.append(
        GraphElementNode(
            id=order_node_id,
            label=label,
            type="order",
            properties={
                "shopify_id": order_key,
                "shopify_gid": _first_str(order, "shopify_id"),
                "order_number": order_number,
                "email": _first_str(order, "email"),
                "phone": _first_str(order, "phone"),
                "note": _first_str(order, "note"),
                "tags": _string_list(order.get("tags")),
                "financial_status": _first_str(order, "financial_status"),
                "fulfillment_status": _first_str(order, "fulfillment_status"),
                "currency_code": total_currency,
                "total_price_amount": total_amount,
                "total_price_currency": total_currency,
                "subtotal_price_amount": subtotal_amount,
                "subtotal_price_currency": subtotal_currency or total_currency,
                "fulfillment_count": fulfillment_count,
                "transaction_count": transaction_count,
                "tracking_numbers": _fulfillment_tracking_numbers(fulfillments),
                "cancelled_at": _first_str(order, "cancelled_at"),
                "cancel_reason": _first_str(order, "cancel_reason"),
            },
        )
    )

    customer = order.get("customer")
    customer_key = _first_str(order, "customer_id")
    if isinstance(customer, dict):
        customer_key = customer_key or _first_str(customer, "id", "shopify_id")
        customer_node = extract_customer_element(customer)
        if customer_node is not None:
            nodes.append(customer_node)
            customer_key = customer_node.properties.get("shopify_id")

    if customer_key:
        customer_node_id = _customer_id(customer_key)
        edges.append(GraphElementEdge(source=customer_node_id, target=order_node_id, type="placed_order"))

    for line_item in _line_items(order):
        item_nodes, item_edges = _extract_line_item_elements(order_node_id, line_item)
        nodes.extend(item_nodes)
        edges.extend(item_edges)

    return nodes, edges


def _extract_line_item_elements(
    order_node_id: str,
    line_item: dict[str, Any],
) -> tuple[list[GraphElementNode], list[GraphElementEdge]]:
    nodes: list[GraphElementNode] = []
    edges: list[GraphElementEdge] = []

    sku = _first_str(line_item, "sku")
    title = _first_str(line_item, "title")
    quantity = line_item.get("quantity")
    unit_price, unit_currency = _money_fields(
        line_item.get("discounted_unit_price") or line_item.get("original_unit_price")
    )

    variant = line_item.get("variant")
    product = line_item.get("product")
    variant_key = _first_str(line_item, "variant_id")
    product_key = _first_str(line_item, "product_id")

    if isinstance(variant, dict):
        variant_key = variant_key or _first_str(variant, "id")
        sku = sku or _first_str(variant, "sku")
    if isinstance(product, dict):
        product_key = product_key or _first_str(product, "id")

    common_props = {
        "sku": sku,
        "title": title,
        "quantity": quantity,
        "unit_price": unit_price,
        "unit_price_currency": unit_currency,
    }

    if variant_key:
        variant_node_id = _variant_id(variant_key)
        nodes.append(
            GraphElementNode(
                id=variant_node_id,
                label=sku or title or variant_key,
                type="variant",
                properties={
                    **common_props,
                    "shopify_id": variant_key,
                    "shopify_gid": (
                        _first_str(variant, "shopify_id") if isinstance(variant, dict) else None
                    ),
                    "product_id": product_key,
                },
            )
        )
        edges.append(
            GraphElementEdge(source=order_node_id, target=variant_node_id, type="ordered_variant")
        )

        if product_key:
            product_title = (
                _first_str(product, "title") if isinstance(product, dict) else None
            ) or title or product_key
            product_node_id = _product_id(product_key)
            nodes.append(
                GraphElementNode(
                    id=product_node_id,
                    label=product_title,
                    type="product",
                    properties={
                        "shopify_id": product_key,
                        "shopify_gid": (
                            _first_str(product, "shopify_id") if isinstance(product, dict) else None
                        ),
                        "title": product_title,
                    },
                )
            )
            edges.append(
                GraphElementEdge(source=product_node_id, target=variant_node_id, type="has_variant")
            )

        return nodes, edges

    if product_key:
        product_node_id = _product_id(product_key)
        nodes.append(
            GraphElementNode(
                id=product_node_id,
                label=sku or title or product_key,
                type="product",
                properties={
                    **common_props,
                    "shopify_id": product_key,
                    "shopify_gid": (
                        _first_str(product, "shopify_id") if isinstance(product, dict) else None
                    ),
                },
            )
        )
        edges.append(
            GraphElementEdge(source=order_node_id, target=product_node_id, type="ordered_product")
        )
        return nodes, edges

    line_item_key = _first_str(line_item, "id", "shopify_id")
    if line_item_key and (sku or title):
        line_item_node_id = _line_item_id(line_item_key)
        nodes.append(
            GraphElementNode(
                id=line_item_node_id,
                label=sku or title or line_item_key,
                type="line_item",
                properties={
                    **common_props,
                    "shopify_id": line_item_key,
                    "shopify_gid": _first_str(line_item, "shopify_id"),
                },
            )
        )
        edges.append(
            GraphElementEdge(source=order_node_id, target=line_item_node_id, type="ordered_line_item")
        )

    return nodes, edges


def extract_graph_elements(
    products: list[dict[str, Any]],
    customers: list[dict[str, Any]],
    orders: list[dict[str, Any]],
) -> tuple[list[GraphElementNode], list[GraphElementEdge]]:
    node_map: dict[str, GraphElementNode] = {}
    edges: list[GraphElementEdge] = []

    def add_node(node: GraphElementNode) -> None:
        existing = node_map.get(node.id)
        if existing is None:
            node_map[node.id] = node
            return
        existing.properties.update({k: v for k, v in node.properties.items() if v is not None})

    for product in products:
        product_nodes, product_edges = extract_product_elements(product)
        for node in product_nodes:
            add_node(node)
        edges.extend(product_edges)

    for customer in customers:
        node = extract_customer_element(customer)
        if node is not None:
            add_node(node)

    for order in orders:
        order_nodes, order_edges = extract_order_elements(order)
        for node in order_nodes:
            add_node(node)
        edges.extend(order_edges)

    return list(node_map.values()), edges


def build_graph_from_shopify_data(
    products: list[dict[str, Any]],
    customers: list[dict[str, Any]],
    orders: list[dict[str, Any]],
) -> nx.Graph:
    nodes, edges = extract_graph_elements(products, customers, orders)
    graph = nx.Graph()

    for node in nodes:
        graph.add_node(
            node.id,
            label=node.label,
            type=node.type,
            properties=node.properties,
        )

    for edge in edges:
        if graph.has_node(edge.source) and graph.has_node(edge.target):
            graph.add_edge(edge.source, edge.target, **{EDGE_ATTR: edge.type})

    return graph


def load_shopify_graph_inputs() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    return (
        load_all_records("products"),
        load_all_records("customers"),
        load_all_records("orders"),
    )
