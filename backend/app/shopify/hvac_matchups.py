"""Resolve Shopify catalog products to Goodman AHRI matchups in productgpt.db."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.schemas.component_search import ComponentSearchRequest, ComponentSearchResponse
from app.schemas.shopify_catalog import ShopifyPublicMatchups, ShopifyPublicProductRef
from app.services.graph_component_search import search_by_component_graph
from app.shopify.catalog import (
    _build_product_lookup_indexes,
    _extract_model_codes,
    _first_str,
    _sku_tokens,
    _string_list,
    _variants,
)
from app.shopify.storage import load_record_by_id


def _empty_matchup_response(*, limit: int, offset: int, query: str = "") -> ComponentSearchResponse:
    return ComponentSearchResponse(
        query=query,
        matched_type=None,
        matched_model=None,
        similar_matchups=[],
        bought_together=[],
        meta={
            "total_matchups": 0,
            "offset": offset,
            "limit": limit,
            "returned": 0,
            "has_more": False,
        },
    )


def model_candidates_for_hvac_search(product: dict[str, Any]) -> list[str]:
    """Build ordered model/SKU candidates from a synced Shopify product record."""
    candidates: list[str] = []
    seen: set[str] = set()

    def add(value: str | None) -> None:
        if value is None:
            return
        normalized = value.strip()
        if len(normalized) < 3:
            return
        key = normalized.lower()
        if key in seen:
            return
        seen.add(key)
        candidates.append(normalized)

    for variant in _variants(product):
        sku = _first_str(variant, "sku")
        if not sku:
            continue
        add(sku)
        for token in _sku_tokens(sku):
            if len(token) >= 4:
                add(token.upper())

    for code in sorted(_extract_model_codes(product), key=len, reverse=True):
        add(code.upper())

    for tag in _string_list(product.get("tags")):
        if len(tag) >= 4:
            add(tag)

    title = _first_str(product, "title")
    if title and not candidates:
        add(title)

    return candidates


def shopify_product_hvac_matchups(
    db: Session,
    product_id: str,
    *,
    limit: int = 25,
    offset: int = 0,
    prefer_higher_seer: bool = True,
) -> ComponentSearchResponse:
    product = load_record_by_id("products", product_id.strip())
    if product is None:
        return _empty_matchup_response(limit=limit, offset=offset)

    candidates = model_candidates_for_hvac_search(product)
    if not candidates:
        return _empty_matchup_response(limit=limit, offset=offset)

    for model in candidates:
        result = search_by_component_graph(
            db,
            ComponentSearchRequest(
                model=model,
                component_type="auto",
                limit=limit,
                offset=offset,
                prefer_higher_seer=prefer_higher_seer,
            ),
        )
        if result.similar_matchups or result.matched_model:
            return result

    return _empty_matchup_response(limit=limit, offset=offset, query=candidates[0])


def _shopify_ref_for_model(
    model: str | None,
    *,
    sku_to_product: dict[str, str],
) -> ShopifyPublicProductRef | None:
    if not model:
        return None
    product_id = sku_to_product.get(model.strip().lower())
    if not product_id:
        for token in _sku_tokens(model):
            product_id = sku_to_product.get(token)
            if product_id:
                break
    if not product_id:
        return None
    product = load_record_by_id("products", product_id)
    if product is None:
        return None
    return ShopifyPublicProductRef(
        id=product_id,
        handle=_first_str(product, "handle"),
    )


def shopify_public_matchup_refs(
    db: Session,
    product_id: str,
    *,
    limit: int = 25,
    prefer_higher_seer: bool = True,
) -> ShopifyPublicMatchups:
    """AHRI graph matchups mapped to slim Shopify `{id, handle}` product refs."""
    hvac = shopify_product_hvac_matchups(
        db,
        product_id,
        limit=limit,
        prefer_higher_seer=prefer_higher_seer,
    )
    query = hvac.matched_model or hvac.query or ""
    if not hvac.similar_matchups:
        return ShopifyPublicMatchups(query=query, similar_matchups=[])

    sku_to_product, _ = _build_product_lookup_indexes()
    refs: list[ShopifyPublicProductRef] = []
    seen: set[str] = set()

    for item in hvac.similar_matchups:
        system = item.system
        for model in (system.outdoor_model, system.coil_model, system.furnace_model):
            ref = _shopify_ref_for_model(model, sku_to_product=sku_to_product)
            if ref is None or ref.id in seen:
                continue
            seen.add(ref.id)
            refs.append(ref)
            if len(refs) >= limit:
                return ShopifyPublicMatchups(query=query, similar_matchups=refs)

    return ShopifyPublicMatchups(query=query, similar_matchups=refs)
