"""Shopify product catalog search and order-based recommendations from synced SQLite DBs."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

_BTU_RE = re.compile(r"(\d[\d,]*)\s*btu\b", re.I)
_ZONE_COUNT_RE = re.compile(r"\b(\d+)\s*[- ]?zones?\b", re.I)
_SINGLE_ZONE_RE = re.compile(r"\bsingle\s+zone\b", re.I)
_MODEL_TOKEN_RE = re.compile(r"^[A-Z0-9][A-Z0-9._/-]{2,}$", re.I)

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


def _product_search_text(product: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("title", "product_type", "type", "description", "handle"):
        value = _first_str(product, key)
        if value:
            parts.append(value)
    parts.extend(_string_list(product.get("tags")))
    for variant in _variants(product):
        for key in ("sku", "title"):
            value = _first_str(variant, key)
            if value:
                parts.append(value)
    return " ".join(parts).lower()


def _extract_btu_digits(product: dict[str, Any]) -> str | None:
    for text in (
        " ".join(_string_list(product.get("tags"))),
        _first_str(product, "title") or "",
    ):
        match = _BTU_RE.search(text)
        if match:
            return match.group(1).replace(",", "")
    return None


def _extract_zone_match_terms(product: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    blob = _product_search_text(product)

    if _SINGLE_ZONE_RE.search(blob):
        terms.extend(["single zone", "1 zone", "1-zone"])

    for match in _ZONE_COUNT_RE.finditer(blob):
        count = match.group(1)
        terms.extend([f"{count} zone", f"{count}-zone", f"{count} zone rooms"])

    product_type = (_first_str(product, "product_type", "type") or "").lower()
    if "single zone" in product_type or "single-zone" in product_type:
        terms.extend(["single zone", "1 zone", "1-zone"])

    return list(dict.fromkeys(terms))


def _text_contains_btu(text: str, btu_digits: str) -> bool:
    normalized = text.replace(",", "").replace(" ", "")
    if btu_digits in normalized:
        return True
    try:
        formatted = f"{int(btu_digits):,}"
    except ValueError:
        return False
    return formatted.lower() in text


def _text_contains_zone_term(text: str, zone_terms: list[str]) -> bool:
    return any(term in text for term in zone_terms)


def _format_zone_display(product: dict[str, Any]) -> str | None:
    blob = _product_search_text(product)
    if _SINGLE_ZONE_RE.search(blob):
        return "Single zone"
    match = _ZONE_COUNT_RE.search(blob)
    if match:
        return f"{match.group(1)} zone"
    product_type = (_first_str(product, "product_type", "type") or "").lower()
    if "single zone" in product_type or "single-zone" in product_type:
        return "Single zone"
    if "multi-zone" in product_type or "multi zone" in product_type:
        return "Multi-zone"
    return None


def _format_btu_display(btu_digits: str) -> str:
    try:
        return f"{int(btu_digits):,} BTU"
    except ValueError:
        return f"{btu_digits} BTU"


def build_match_keywords(product: dict[str, Any]) -> list[str]:
    keywords: list[str] = []
    category = (_first_str(product, "product_type", "type") or "").strip()
    if category:
        keywords.append(f"Category: {category}")

    btu = _extract_btu_digits(product)
    if btu:
        keywords.append(f"BTU: {_format_btu_display(btu)}")

    zone = _format_zone_display(product)
    if zone:
        keywords.append(f"Zone: {zone}")

    return keywords


def _matches_same_category_spec(source: dict[str, Any], candidate: dict[str, Any]) -> bool:
    category = (_first_str(source, "product_type", "type") or "").strip().lower()
    candidate_type = (_first_str(candidate, "product_type", "type") or "").strip().lower()
    if not category or candidate_type != category:
        return False

    candidate_text = _product_search_text(candidate)
    btu = _extract_btu_digits(source)
    zone_terms = _extract_zone_match_terms(source)

    if btu and not _text_contains_btu(candidate_text, btu):
        return False
    if zone_terms and not _text_contains_zone_term(candidate_text, zone_terms):
        return False
    return True


def _build_product_lookup_indexes() -> tuple[dict[str, str], dict[str, str]]:
    """Map variant SKU and variant id to parent product id from synced catalog."""
    sku_to_product: dict[str, str] = {}
    variant_to_product: dict[str, str] = {}
    for product in load_all_records("products"):
        product_id = _first_str(product, "id")
        if not product_id:
            continue
        for variant in _variants(product):
            sku = (_first_str(variant, "sku") or "").strip().lower()
            if sku:
                sku_to_product.setdefault(sku, product_id)
            variant_id = _first_str(variant, "id")
            if variant_id:
                variant_to_product[variant_id] = product_id
    return sku_to_product, variant_to_product


def _sku_tokens(sku: str) -> list[str]:
    return [token.strip().lower() for token in re.split(r"[,/\s]+", sku) if token.strip()]


def _extract_model_codes(product: dict[str, Any]) -> set[str]:
    codes: list[str] = []
    for variant in _variants(product):
        sku = _first_str(variant, "sku")
        if not sku:
            continue
        for token in _sku_tokens(sku):
            if len(token) >= 4 and _MODEL_TOKEN_RE.match(token):
                codes.append(token)
    for tag in _string_list(product.get("tags")):
        token = tag.strip()
        if len(token) >= 4 and _MODEL_TOKEN_RE.match(token):
            codes.append(token.lower())
    return set(codes)


def _line_item_skus(line_item: dict[str, Any]) -> list[str]:
    skus: list[str] = []
    sku = _first_str(line_item, "sku")
    if sku:
        skus.append(sku)
    variant = line_item.get("variant")
    if isinstance(variant, dict):
        variant_sku = _first_str(variant, "sku")
        if variant_sku:
            skus.append(variant_sku)
    return skus


def _sku_contains_model_code(sku: str, model_codes: set[str]) -> bool:
    if not model_codes:
        return False
    return any(token in model_codes for token in _sku_tokens(sku))


def _order_contains_target(
    order: dict[str, Any],
    target_id: str,
    model_codes: set[str],
    *,
    sku_to_product: dict[str, str],
    variant_to_product: dict[str, str],
) -> bool:
    product_ids = _product_ids_in_order(
        order,
        sku_to_product=sku_to_product,
        variant_to_product=variant_to_product,
    )
    if target_id in product_ids:
        return True
    if not model_codes:
        return False

    line_items = order.get("line_items")
    if not isinstance(line_items, list):
        return False
    for line_item in line_items:
        if not isinstance(line_item, dict):
            continue
        for sku in _line_item_skus(line_item):
            if _sku_contains_model_code(sku, model_codes):
                return True
    return False


def _line_item_product_id(
    line_item: dict[str, Any],
    *,
    sku_to_product: dict[str, str] | None = None,
    variant_to_product: dict[str, str] | None = None,
) -> str | None:
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
        product_id = _first_str(variant, "product_id")
        if product_id:
            return product_id
        if variant_to_product is not None:
            variant_id = _first_str(variant, "id")
            if variant_id and variant_id in variant_to_product:
                return variant_to_product[variant_id]
            shopify_gid = _first_str(variant, "shopify_id")
            if shopify_gid and shopify_gid.rsplit("/", 1)[-1] in variant_to_product:
                return variant_to_product[shopify_gid.rsplit("/", 1)[-1]]

    if sku_to_product is not None:
        for sku_source in (line_item, variant if isinstance(variant, dict) else None):
            if not isinstance(sku_source, dict):
                continue
            sku = (_first_str(sku_source, "sku") or "").strip().lower()
            if sku and sku in sku_to_product:
                return sku_to_product[sku]

    return None


def _product_ids_in_order(
    order: dict[str, Any],
    *,
    sku_to_product: dict[str, str] | None = None,
    variant_to_product: dict[str, str] | None = None,
) -> set[str]:
    ids: set[str] = set()
    line_items = order.get("line_items")
    if not isinstance(line_items, list):
        return ids
    for line_item in line_items:
        if not isinstance(line_item, dict):
            continue
        product_id = _line_item_product_id(
            line_item,
            sku_to_product=sku_to_product,
            variant_to_product=variant_to_product,
        )
        if product_id:
            ids.add(product_id)
    return ids


def products_bought_together(product_id: str, *, limit: int = 8) -> list[dict[str, Any]]:
    target_id = product_id.strip()
    target_product = load_record_by_id("products", target_id)
    model_codes = _extract_model_codes(target_product) if target_product else set()
    co_occurrence: Counter[str] = Counter()
    sku_to_product, variant_to_product = _build_product_lookup_indexes()

    for order in load_all_records("orders"):
        if not _order_contains_target(
            order,
            target_id,
            model_codes,
            sku_to_product=sku_to_product,
            variant_to_product=variant_to_product,
        ):
            continue
        product_ids = _product_ids_in_order(
            order,
            sku_to_product=sku_to_product,
            variant_to_product=variant_to_product,
        )
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

    matches: list[dict[str, Any]] = []
    for candidate in load_all_records("products"):
        candidate_id = _first_str(candidate, "id")
        if not candidate_id or candidate_id == product_id:
            continue
        if not _matches_same_category_spec(product, candidate):
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
        return {"category": None, "current_vendor": None, "match_keywords": [], "brands": []}

    category = (_first_str(product, "product_type", "type") or "").strip()
    current_vendor = (_first_str(product, "vendor") or "").strip()
    match_keywords = build_match_keywords(product)
    if not category:
        return {
            "category": None,
            "current_vendor": current_vendor or None,
            "match_keywords": match_keywords,
            "brands": [],
        }

    current_vendor_lower = current_vendor.lower()
    by_vendor: dict[str, list[dict[str, Any]]] = {}

    for candidate in load_all_records("products"):
        candidate_id = _first_str(candidate, "id")
        if not candidate_id or candidate_id == target_id:
            continue
        if not _matches_same_category_spec(product, candidate):
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
        "match_keywords": match_keywords,
        "brands": brands,
    }
