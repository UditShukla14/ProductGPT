"""Shopify product catalog search and order-based recommendations from synced SQLite DBs."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

_BTU_RE = re.compile(r"(\d[\d,]*)\s*btu\b", re.I)
_ZONE_COUNT_RE = re.compile(r"\b(\d+)\s*[- ]?zones?\b", re.I)
_SINGLE_ZONE_RE = re.compile(r"\bsingle\s+zone\b", re.I)
_MULTI_ZONE_RE = re.compile(r"\bmulti[\s\-]?zone\b", re.I)
_MODEL_TOKEN_RE = re.compile(r"^[A-Z0-9][A-Z0-9._/-]{2,}$", re.I)
_SEER_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*seer(?:2)?\b", re.I)
_VOLTAGE_RE = re.compile(r"\b(115|208|220|230|240|265)\s*v(?:olt)?s?\b", re.I)
_REFRIGERANT_RE = re.compile(r"\b(r[\s\-]?32|r[\s\-]?410a)\b", re.I)
# Near-capacity tolerance for nominal vs rated BTU (e.g. 12,000 title vs 11,500 rated).
_BTU_TOLERANCE = 1000
# Minimum similarity score before a product is treated as "related".
_MIN_RELATED_SCORE = 55
_COMPONENT_TYPE_MARKERS = (
    "condenser",
    "outdoor unit",
    "indoor",
    "wall unit",
    "accessory",
    "accessories",
    "parts",
    "lineset",
    "thermostat",
)
_KIND_LABELS = {
    "mini_split_system": "Mini-split system",
    "ptac": "PTAC",
    "vtac": "VTAC",
    "package_system": "Package system",
    "component": "Component",
    "other": "Other",
}

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


def _extract_btu_digits(product: dict[str, Any], *, blob: str | None = None) -> str | None:
    texts = (
        " ".join(_string_list(product.get("tags"))),
        _first_str(product, "title") or "",
        _first_str(product, "description") or "",
    )
    if blob is not None:
        texts = (blob, *texts)
    for text in texts:
        match = _BTU_RE.search(text)
        if match:
            return match.group(1).replace(",", "")
    return None


def _extract_zone_count(product: dict[str, Any], *, blob: str | None = None) -> int | None:
    blob = _product_search_text(product) if blob is None else blob
    if _SINGLE_ZONE_RE.search(blob):
        return 1
    if _MULTI_ZONE_RE.search(blob):
        match = _ZONE_COUNT_RE.search(blob)
        return int(match.group(1)) if match else 2
    match = _ZONE_COUNT_RE.search(blob)
    if match:
        return int(match.group(1))
    product_type = (_first_str(product, "product_type", "type") or "").lower()
    if "single zone" in product_type or "single-zone" in product_type:
        return 1
    if "multi-zone" in product_type or "multi zone" in product_type:
        return 2
    return None


def _extract_zone_match_terms(product: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    zone_count = _extract_zone_count(product)
    if zone_count == 1:
        terms.extend(["single zone", "1 zone", "1-zone"])
    elif zone_count and zone_count > 1:
        terms.extend(
            [
                f"{zone_count} zone",
                f"{zone_count}-zone",
                f"{zone_count} zone rooms",
                "multi zone",
                "multi-zone",
            ]
        )
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
    zone_count = _extract_zone_count(product)
    if zone_count == 1:
        return "Single zone"
    if zone_count and zone_count > 1:
        return f"{zone_count} zone"
    return None


def _format_btu_display(btu_digits: str) -> str:
    try:
        return f"{int(btu_digits):,} BTU"
    except ValueError:
        return f"{btu_digits} BTU"


def _normalize_type_tokens(product_type: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", product_type.lower()).strip()


def _detect_product_kind(product: dict[str, Any], *, blob: str | None = None) -> str:
    """Coarse product family used as a hard gate for related matching."""
    type_tokens = _normalize_type_tokens(
        _first_str(product, "product_type", "type") or ""
    )
    if blob is None:
        blob = _product_search_text(product)

    if any(marker in type_tokens for marker in _COMPONENT_TYPE_MARKERS):
        return "component"
    if any(marker in blob for marker in ("condenser only", "outdoor unit only", "indoor unit only")):
        return "component"
    if "ptac" in type_tokens or re.search(r"\bptac\b", blob):
        return "ptac"
    if "vtac" in type_tokens or re.search(r"\bvtac\b", blob) or "vertical zoneline" in blob:
        return "vtac"
    if "package" in type_tokens or "packaged" in blob:
        return "package_system"

    is_mini = (
        "mini split" in type_tokens
        or "ductless" in type_tokens
        or "mini split" in blob
        or "mini-split" in blob
        or "ductless" in blob
    )
    is_split_hp = (
        type_tokens == "split heat pump"
        or type_tokens.startswith("split heat pump ")
        or "split heat pump" in blob
    )
    if is_mini or is_split_hp:
        return "mini_split_system"

    if type_tokens:
        return f"type:{type_tokens}"
    return "other"


def _extract_product_profile(product: dict[str, Any]) -> dict[str, Any]:
    text = _product_search_text(product)
    title = (_first_str(product, "title") or "").lower()
    btu_digits = _extract_btu_digits(product, blob=text)
    seer_match = _SEER_RE.search(title) or _SEER_RE.search(text)
    voltage_match = _VOLTAGE_RE.search(title) or _VOLTAGE_RE.search(text)
    refrigerant_match = _REFRIGERANT_RE.search(text)

    heat_pump: bool | None = None
    if "heat pump" in text:
        heat_pump = True
    elif "cooling only" in text or "cool only" in text:
        heat_pump = False

    return {
        "kind": _detect_product_kind(product, blob=text),
        "btu": int(btu_digits) if btu_digits else None,
        "seer": float(seer_match.group(1)) if seer_match else None,
        "voltage": int(voltage_match.group(1)) if voltage_match else None,
        "zone_count": _extract_zone_count(product, blob=text),
        "heat_pump": heat_pump,
        "refrigerant": (
            re.sub(r"[\s\-]+", "", refrigerant_match.group(1)).lower()
            if refrigerant_match
            else None
        ),
        "product_type": (_first_str(product, "product_type", "type") or "").strip(),
        "_text": text,
    }


def build_match_keywords(product: dict[str, Any]) -> list[str]:
    """Human-readable attributes used for related-product matching."""
    profile = _extract_product_profile(product)
    keywords: list[str] = []

    if profile["btu"] is not None:
        keywords.append(f"BTU: {_format_btu_display(str(profile['btu']))}")
    if profile["seer"] is not None:
        keywords.append(f"SEER2: {profile['seer']:g}")
    if profile["voltage"] is not None:
        keywords.append(f"Voltage: {profile['voltage']}V")
    zone = _format_zone_display(product)
    if zone:
        keywords.append(f"Zone: {zone}")
    kind_label = _KIND_LABELS.get(profile["kind"])
    if kind_label:
        keywords.append(f"Type: {kind_label}")
    elif profile["product_type"]:
        keywords.append(f"Category: {profile['product_type']}")
    if profile["heat_pump"] is True:
        keywords.append("Heat pump")
    elif profile["heat_pump"] is False:
        keywords.append("Cooling only")

    return keywords


def _category_family_key(product_type: str) -> str:
    exact = product_type.strip().lower()
    if not exact:
        return ""

    tokens = _normalize_type_tokens(product_type)
    if any(marker in tokens for marker in _COMPONENT_TYPE_MARKERS):
        return f"exact:{exact}"

    is_mini = "mini split" in tokens or "ductless" in tokens
    is_split_hp = tokens == "split heat pump" or tokens.startswith("split heat pump ")
    if is_mini or is_split_hp:
        if (
            "system" in tokens
            or "heat pump" in tokens
            or tokens in {"mini split", "mini split ac"}
        ):
            return "family:mini_split_system"

    return f"exact:{exact}"


def _same_product_category(source_type: str, candidate_type: str) -> bool:
    source = source_type.strip()
    candidate = candidate_type.strip()
    if not source or not candidate:
        return False
    if source.lower() == candidate.lower():
        return True
    source_family = _category_family_key(source)
    candidate_family = _category_family_key(candidate)
    return bool(source_family) and source_family == candidate_family and source_family.startswith(
        "family:"
    )


def _btu_near(source_btu: int, candidate_btu: int | None, candidate_text: str) -> tuple[bool, bool]:
    """Return (is_near, is_exact) for BTU capacity."""
    if candidate_btu is not None:
        if candidate_btu == source_btu:
            return True, True
        if abs(candidate_btu - source_btu) <= _BTU_TOLERANCE:
            return True, False
        return False, False

    if _text_contains_btu(candidate_text, str(source_btu)):
        return True, True
    for delta in range(500, _BTU_TOLERANCE + 1, 500):
        for value in (source_btu - delta, source_btu + delta):
            if value > 0 and _text_contains_btu(candidate_text, str(value)):
                return True, False
    return False, False


def _related_similarity_score(
    source: dict[str, Any],
    candidate: dict[str, Any],
    *,
    source_profile: dict[str, Any] | None = None,
) -> int | None:
    """Score how closely a catalog product resembles the source.

    Returns None when the candidate fails hard gates (wrong equipment kind / capacity).
    """
    source_profile = source_profile or _extract_product_profile(source)
    candidate_profile = _extract_product_profile(candidate)
    candidate_text = candidate_profile.get("_text") or _product_search_text(candidate)
    score = 0

    source_kind = source_profile["kind"]
    candidate_kind = candidate_profile["kind"]

    if source_kind.startswith("type:"):
        if not _same_product_category(
            source_profile["product_type"],
            candidate_profile["product_type"],
        ):
            return None
        score += 20
    else:
        if candidate_kind != source_kind:
            return None
        if source_kind == "component":
            if not _same_product_category(
                source_profile["product_type"],
                candidate_profile["product_type"],
            ):
                return None
        score += 25

    source_btu = source_profile["btu"]
    if source_btu is not None:
        near, exact = _btu_near(source_btu, candidate_profile["btu"], candidate_text)
        if not near:
            return None
        score += 40 if exact else 28
    elif source_profile["product_type"]:
        score += 15

    if source_profile["seer"] is not None and candidate_profile["seer"] is not None:
        seer_delta = abs(source_profile["seer"] - candidate_profile["seer"])
        if seer_delta == 0:
            score += 18
        elif seer_delta <= 2:
            score += 10

    if (
        source_profile["voltage"] is not None
        and candidate_profile["voltage"] is not None
        and source_profile["voltage"] == candidate_profile["voltage"]
    ):
        score += 12

    # Soft signal — prefer matching heat-pump vs cooling-only, but do not hard-reject.
    if (
        source_profile["heat_pump"] is not None
        and candidate_profile["heat_pump"] is not None
    ):
        score += 15 if source_profile["heat_pump"] == candidate_profile["heat_pump"] else -15

    if (
        source_profile["zone_count"] is not None
        and candidate_profile["zone_count"] is not None
    ):
        if source_profile["zone_count"] != candidate_profile["zone_count"]:
            return None
        score += 10

    if (
        source_profile["refrigerant"]
        and candidate_profile["refrigerant"]
        and source_profile["refrigerant"] == candidate_profile["refrigerant"]
    ):
        score += 5

    if score < _MIN_RELATED_SCORE:
        return None
    return score


def _matches_same_category_spec(source: dict[str, Any], candidate: dict[str, Any]) -> bool:
    return _related_similarity_score(source, candidate) is not None


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

    profile = _extract_product_profile(product)
    if profile["btu"] is None and not profile["product_type"]:
        return []

    scored: list[tuple[int, dict[str, Any]]] = []
    source_profile = profile
    for candidate in load_all_records("products"):
        candidate_id = _first_str(candidate, "id")
        if not candidate_id or candidate_id == product_id:
            continue
        score = _related_similarity_score(product, candidate, source_profile=source_profile)
        if score is None:
            continue
        scored.append((score, product_to_summary(candidate)))

    scored.sort(key=lambda item: (-item[0], item[1].get("title") or ""))
    return [summary for _, summary in scored[:limit]]


def products_same_category_by_brand(
    product_id: str,
    *,
    per_brand_limit: int = 8,
) -> dict[str, Any]:
    """Return related products grouped by vendor, excluding the current product and vendor.

    Related means structured similarity (equipment kind + BTU), with SEER / voltage /
    heat-pump / zone as soft boosts — not exact Shopify product_type equality.
    """
    target_id = product_id.strip()
    product = load_record_by_id("products", target_id)
    if product is None:
        return {"category": None, "current_vendor": None, "match_keywords": [], "brands": []}

    category = (_first_str(product, "product_type", "type") or "").strip()
    current_vendor = (_first_str(product, "vendor") or "").strip()
    match_keywords = build_match_keywords(product)
    profile = _extract_product_profile(product)
    if profile["btu"] is None and not category:
        return {
            "category": None,
            "current_vendor": current_vendor or None,
            "match_keywords": match_keywords,
            "brands": [],
        }

    current_vendor_lower = current_vendor.lower()
    by_vendor: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    source_profile = profile

    for candidate in load_all_records("products"):
        candidate_id = _first_str(candidate, "id")
        if not candidate_id or candidate_id == target_id:
            continue
        score = _related_similarity_score(product, candidate, source_profile=source_profile)
        if score is None:
            continue

        vendor = (_first_str(candidate, "vendor") or "Other").strip()
        if current_vendor_lower and vendor.lower() == current_vendor_lower:
            continue

        by_vendor.setdefault(vendor, []).append((score, product_to_summary(candidate)))

    brands = []
    for vendor, scored_products in by_vendor.items():
        scored_products.sort(key=lambda item: (-item[0], item[1].get("title") or ""))
        products = [summary for _, summary in scored_products[:per_brand_limit]]
        if products:
            brands.append({"vendor": vendor, "products": products})

    brands.sort(key=lambda item: (-len(item["products"]), item["vendor"].lower()))

    return {
        "category": category or None,
        "current_vendor": current_vendor or None,
        "match_keywords": match_keywords,
        "brands": brands,
    }
