"""Shopify product catalog search and order-based recommendations from synced SQLite DBs."""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.shopify.graph.builder import _primary_image_url, _variants
from app.shopify.storage import load_all_records, load_record_by_id


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


def _primary_variant(product: dict[str, Any]) -> dict[str, Any] | None:
    variants = _variants(product)
    return variants[0] if variants else None


def product_to_summary(product: dict[str, Any]) -> dict[str, Any]:
    product_id = _first_str(product, "id", "shopify_id") or ""
    variant = _primary_variant(product)
    return {
        "id": product_id,
        "title": _first_str(product, "title", "name") or product_id,
        "vendor": _first_str(product, "vendor"),
        "product_type": _first_str(product, "product_type", "type"),
        "sku": _first_str(variant, "sku") if variant else None,
        "price": _first_str(variant, "price") if variant else None,
        "image_url": _primary_image_url(product),
        "status": _first_str(product, "status"),
        "handle": _first_str(product, "handle"),
    }


def product_to_detail(product: dict[str, Any]) -> dict[str, Any]:
    summary = product_to_summary(product)
    variants = _variants(product)
    return {
        **summary,
        "shopify_gid": _first_str(product, "shopify_id"),
        "description": _first_str(product, "description", "body_html"),
        "tags": _string_list(product.get("tags")),
        "inventory_quantity": variant.get("inventory_quantity") if (variant := _primary_variant(product)) else None,
        "available_for_sale": variant.get("available_for_sale") if variant else None,
        "variants": [
            {
                "id": _first_str(item, "id"),
                "sku": _first_str(item, "sku"),
                "title": _first_str(item, "title"),
                "price": _first_str(item, "price"),
                "inventory_quantity": item.get("inventory_quantity"),
                "available_for_sale": item.get("available_for_sale"),
            }
            for item in variants
        ],
        "created_at": _first_str(product, "created_at"),
        "updated_at": _first_str(product, "updated_at"),
    }


def _search_score(product: dict[str, Any], query: str) -> int:
    q = query.lower()
    title = (_first_str(product, "title") or "").lower()
    handle = (_first_str(product, "handle") or "").lower()
    vendor = (_first_str(product, "vendor") or "").lower()
    product_type = (_first_str(product, "product_type", "type") or "").lower()
    tags = [tag.lower() for tag in _string_list(product.get("tags"))]

    score = 0
    for variant in _variants(product):
        sku = (_first_str(variant, "sku") or "").lower()
        if sku == q:
            score = max(score, 120)
        elif sku.startswith(q):
            score = max(score, 100)
        elif q in sku:
            score = max(score, 80)

    product_id = _first_str(product, "id")
    shopify_gid = _first_str(product, "shopify_id") or ""
    if product_id == query or shopify_gid.endswith(f"/{query}"):
        score = max(score, 110)

    if title.startswith(q):
        score = max(score, 90)
    elif q in title:
        score = max(score, 70)

    if handle.startswith(q):
        score = max(score, 60)
    elif q in handle:
        score = max(score, 50)

    if any(tag == q for tag in tags):
        score = max(score, 55)
    elif any(q in tag for tag in tags):
        score = max(score, 45)

    if q in vendor:
        score = max(score, 40)
    if q in product_type:
        score = max(score, 35)
    if q in handle:
        score = max(score, 30)

    return score


def search_products(query: str, *, limit: int = 10) -> list[dict[str, Any]]:
    normalized = query.strip()
    if len(normalized) < 2:
        return []

    scored: list[tuple[int, dict[str, Any]]] = []
    for product in load_all_records("products"):
        score = _search_score(product, normalized)
        if score > 0:
            scored.append((score, product))

    scored.sort(key=lambda item: (-item[0], item[1].get("title", "")))
    return [product_to_summary(product) for _, product in scored[:limit]]


def get_product_detail(product_id: str) -> dict[str, Any] | None:
    product = load_record_by_id("products", product_id.strip())
    if product is None:
        return None
    return product_to_detail(product)



def _line_item_product_id(line_item: dict[str, Any]) -> str | None:
    nested = line_item.get("product")
    if isinstance(nested, dict):
        product_id = _first_str(nested, "id")
        if product_id:
            return product_id

    product_id = _first_str(line_item, "product_id")
    if product_id:
        return product_id

    variant = line_item.get("variant")
    if isinstance(variant, dict):
        return _first_str(variant, "product_id")

    return None


def _product_ids_in_order(order: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    line_items = order.get("line_items")
    if not isinstance(line_items, list):
        return ids
    for line_item in line_items:
        if not isinstance(line_item, dict):
            continue
        product_id = _line_item_product_id(line_item)
        if product_id:
            ids.add(product_id)
    return ids


def products_bought_together(product_id: str, *, limit: int = 8) -> list[dict[str, Any]]:
    target_id = product_id.strip()
    co_occurrence: Counter[str] = Counter()

    for order in load_all_records("orders"):
        product_ids = _product_ids_in_order(order)
        if target_id not in product_ids:
            continue
        for other_id in product_ids:
            if other_id != target_id:
                co_occurrence[other_id] += 1

    recommendations: list[dict[str, Any]] = []
    for other_id, count in co_occurrence.most_common(limit):
        product = load_record_by_id("products", other_id)
        if product is None:
            continue
        recommendations.append(
            {
                "product": product_to_summary(product),
                "order_count": count,
                "reason": f"Purchased together in {count} order{'s' if count != 1 else ''}",
            }
        )
    return recommendations


def products_same_category(product_id: str, *, limit: int = 8) -> list[dict[str, Any]]:
    product = load_record_by_id("products", product_id.strip())
    if product is None:
        return []

    category = (_first_str(product, "product_type", "type") or "").strip()
    if not category:
        return []

    category_lower = category.lower()
    matches: list[dict[str, Any]] = []
    for candidate in load_all_records("products"):
        candidate_id = _first_str(candidate, "id")
        if not candidate_id or candidate_id == product_id:
            continue
        candidate_type = (_first_str(candidate, "product_type", "type") or "").strip()
        if candidate_type.lower() != category_lower:
            continue
        matches.append(product_to_summary(candidate))
        if len(matches) >= limit:
            break

    return matches


def products_same_category_by_brand(
    product_id: str,
    *,
    per_brand_limit: int = 8,
) -> dict[str, Any]:
    """Return same-category products grouped by vendor, excluding the current product and vendor."""
    target_id = product_id.strip()
    product = load_record_by_id("products", target_id)
    if product is None:
        return {"category": None, "current_vendor": None, "brands": []}

    category = (_first_str(product, "product_type", "type") or "").strip()
    current_vendor = (_first_str(product, "vendor") or "").strip()
    if not category:
        return {"category": None, "current_vendor": current_vendor or None, "brands": []}

    category_lower = category.lower()
    current_vendor_lower = current_vendor.lower()
    by_vendor: dict[str, list[dict[str, Any]]] = {}

    for candidate in load_all_records("products"):
        candidate_id = _first_str(candidate, "id")
        if not candidate_id or candidate_id == target_id:
            continue
        candidate_type = (_first_str(candidate, "product_type", "type") or "").strip()
        if candidate_type.lower() != category_lower:
            continue

        vendor = (_first_str(candidate, "vendor") or "Other").strip()
        if current_vendor_lower and vendor.lower() == current_vendor_lower:
            continue

        bucket = by_vendor.setdefault(vendor, [])
        if len(bucket) < per_brand_limit:
            bucket.append(product_to_summary(candidate))

    brands = [
        {"vendor": vendor, "products": products}
        for vendor, products in sorted(by_vendor.items(), key=lambda item: (-len(item[1]), item[0].lower()))
        if products
    ]

    return {
        "category": category,
        "current_vendor": current_vendor or None,
        "brands": brands,
    }
