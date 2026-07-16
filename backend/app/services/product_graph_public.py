"""Public Shopify recommendations via merged ProductGraphNode (no SQLite catalog scans)."""

from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.knowledge_graph.neo4j_client import neo4j_client
from app.schemas.shopify_catalog import (
    ShopifyPublicBrandGroup,
    ShopifyPublicMatchups,
    ShopifyPublicProductRef,
    ShopifyPublicProductResponse,
    ShopifyPublicSimilarProducts,
)
from app.shopify.catalog import (
    _extract_product_profile,
    _first_str,
    _related_similarity_score,
)

_SCHEMA_QUERIES = (
    "CREATE INDEX product_graph_node_id IF NOT EXISTS FOR (n:ProductGraphNode) ON (n.id)",
    "CREATE INDEX product_graph_node_type IF NOT EXISTS FOR (n:ProductGraphNode) ON (n.type)",
    "CREATE INDEX product_graph_product_type IF NOT EXISTS FOR (n:ProductGraphNode) ON (n.product_type)",
    "CREATE INDEX product_graph_vendor IF NOT EXISTS FOR (n:ProductGraphNode) ON (n.vendor)",
    "CREATE INDEX product_graph_shopify_id IF NOT EXISTS FOR (n:ProductGraphNode) ON (n.shopify_id)",
)

_SIMILAR_CANDIDATE_LIMIT = 500
_indexes_ready = False
_kind_product_types_cache: dict[str, tuple[str, ...]] = {}
_KIND_TITLE_FRAGMENTS: dict[str, tuple[str, ...]] = {
    "mini_split_system": ("mini split", "mini-split", "ductless"),
    "ptac": ("ptac",),
    "vtac": ("vtac", "vertical zoneline"),
    "package_system": ("package", "packaged"),
}


class ProductGraphUnavailableError(RuntimeError):
    """Raised when ProductGraphNode data is required but Neo4j is offline/empty."""


def _ensure_connected() -> None:
    if not neo4j_client.enabled:
        raise ProductGraphUnavailableError("Neo4j is disabled")
    if not neo4j_client.is_connected and not neo4j_client.connect():
        raise ProductGraphUnavailableError("Neo4j is not available")


def product_graph_is_ready() -> bool:
    try:
        _ensure_connected()
        with neo4j_client.session() as session:
            row = session.run(
                "MATCH (n:ProductGraphNode {type:'product'}) RETURN n.id AS id LIMIT 1"
            ).single()
            return row is not None
    except Exception:
        return False


def ensure_product_graph_indexes() -> None:
    global _indexes_ready
    if _indexes_ready:
        return
    _ensure_connected()
    with neo4j_client.session() as session:
        for query in _SCHEMA_QUERIES:
            session.run(query)
    _indexes_ready = True


def _node_id(product_id: str) -> str:
    cleaned = product_id.strip()
    if cleaned.startswith("product:"):
        return cleaned
    return f"product:{cleaned}"


def _shopify_id(product_id: str) -> str:
    cleaned = product_id.strip()
    if cleaned.startswith("product:"):
        return cleaned.split(":", 1)[1]
    return cleaned


def _parse_tags(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if item is not None and str(item).strip()]
    if not isinstance(raw, str) or not raw.strip():
        return []
    text = raw.strip()
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if item is not None and str(item).strip()]
    except (SyntaxError, ValueError):
        pass
    return [part.strip() for part in text.split(",") if part.strip()]


def _ref(product_id: str | None, handle: str | None) -> ShopifyPublicProductRef | None:
    if not product_id:
        return None
    return ShopifyPublicProductRef(id=str(product_id), handle=handle)


def _row_to_product(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id") or ""),
        "handle": row.get("handle"),
        "vendor": row.get("vendor"),
        "title": row.get("title") or "",
        "product_type": row.get("product_type") or "",
        "tags": _parse_tags(row.get("tags")),
        "description": row.get("description") or "",
        "image_url": row.get("image_url"),
    }


def _fetch_product(product_id: str) -> dict[str, Any] | None:
    node_id = _node_id(product_id)
    shopify_id = _shopify_id(product_id)
    with neo4j_client.session() as session:
        row = session.run(
            """
            MATCH (p:ProductGraphNode {type:'product'})
            WHERE p.id = $node_id OR toString(p.shopify_id) = $shopify_id
            OPTIONAL MATCH (p)-[:MADE_BY]->(b:ProductGraphNode {type:'brand'})
            RETURN toString(p.shopify_id) AS id,
                   p.handle AS handle,
                   p.vendor AS vendor,
                   p.title AS title,
                   p.product_type AS product_type,
                   p.tags AS tags,
                   p.description AS description,
                   p.image_url AS image_url,
                   b.name AS brand_name,
                   b.image_url AS brand_image
            LIMIT 1
            """,
            node_id=node_id,
            shopify_id=shopify_id,
        ).single()
    if row is None:
        return None
    return dict(row)


def _bought_together(product_id: str, *, limit: int) -> list[ShopifyPublicProductRef]:
    node_id = _node_id(product_id)
    with neo4j_client.session() as session:
        rows = session.run(
            """
            MATCH (p:ProductGraphNode {id:$id})-[:HAS_VARIANT]->(v:ProductGraphNode)
            MATCH (o:ProductGraphNode)-[:ORDERED_VARIANT]->(v)
            MATCH (o)-[:ORDERED_VARIANT]->(v2:ProductGraphNode)
            WHERE v2 <> v
            MATCH (p2:ProductGraphNode)-[:HAS_VARIANT]->(v2)
            WHERE p2.type = 'product'
              AND p2.id <> p.id
              AND p2.shopify_id IS NOT NULL
            RETURN toString(p2.shopify_id) AS id, p2.handle AS handle, count(*) AS freq
            ORDER BY freq DESC
            LIMIT $limit
            """,
            id=node_id,
            limit=limit,
        ).data()
    refs: list[ShopifyPublicProductRef] = []
    for row in rows:
        ref = _ref(row.get("id"), row.get("handle"))
        if ref is not None:
            refs.append(ref)
    return refs


def _kind_fragments(kind: str, product_type: str) -> list[str]:
    if kind in _KIND_TITLE_FRAGMENTS:
        return list(_KIND_TITLE_FRAGMENTS[kind])
    if kind.startswith("type:") and product_type:
        tokens = product_type.lower().strip()
        if tokens:
            return [tokens[:48]]
    return []


def _product_types_for_fragments(fragments: list[str]) -> list[str]:
    """Resolve kind fragments to concrete product_type values (index-friendly IN)."""
    cache_key = "|".join(fragments)
    cached = _kind_product_types_cache.get(cache_key)
    if cached is not None:
        return list(cached)

    with neo4j_client.session() as session:
        rows = session.run(
            """
            MATCH (p:ProductGraphNode {type:'product'})
            WHERE p.product_type IS NOT NULL
              AND any(
                frag IN $fragments WHERE
                  toLower(p.product_type) CONTAINS frag
              )
            RETURN DISTINCT p.product_type AS product_type
            """,
            fragments=fragments,
        ).data()
    types = sorted(
        {
            str(row["product_type"]).strip()
            for row in rows
            if row.get("product_type") and str(row["product_type"]).strip()
        }
    )
    _kind_product_types_cache[cache_key] = tuple(types)
    return types


def _btu_search_tokens(btu: int | None) -> list[str]:
    if btu is None:
        return []
    tokens = {str(btu), f"{btu:,}"}
    # Near-capacity titles (catalog uses ±1000).
    for delta in (500, 1000):
        for value in (btu - delta, btu + delta):
            if value > 0:
                tokens.add(str(value))
                tokens.add(f"{value:,}")
    return sorted(tokens)


def _similar_candidates(source: dict[str, Any], *, limit: int) -> list[dict[str, Any]]:
    profile = _extract_product_profile(source)
    vendor = (_first_str(source, "vendor") or "").strip()
    product_type = (_first_str(source, "product_type", "type") or "").strip()
    fragments = _kind_fragments(profile["kind"], product_type)
    btu_tokens = _btu_search_tokens(profile.get("btu"))

    def _run(types: list[str], *, use_btu: bool) -> list[dict[str, Any]]:
        if not types:
            return []
        with neo4j_client.session() as session:
            return session.run(
                """
                MATCH (p:ProductGraphNode {type:'product'})
                WHERE p.product_type IN $types
                  AND ($vendor = '' OR p.vendor <> $vendor)
                  AND p.shopify_id IS NOT NULL
                  AND (
                    $use_btu = false OR any(
                      token IN $btu_tokens WHERE
                        toLower(coalesce(p.title, '')) CONTAINS token
                        OR toLower(coalesce(p.tags, '')) CONTAINS token
                    )
                  )
                OPTIONAL MATCH (p)-[:MADE_BY]->(b:ProductGraphNode {type:'brand'})
                RETURN toString(p.shopify_id) AS id,
                       p.handle AS handle,
                       p.vendor AS vendor,
                       p.title AS title,
                       p.product_type AS product_type,
                       p.tags AS tags,
                       p.description AS description,
                       p.image_url AS image_url,
                       coalesce(b.image_url, '') AS brand_image
                LIMIT $limit
                """,
                types=types,
                vendor=vendor,
                use_btu=use_btu,
                btu_tokens=btu_tokens,
                limit=limit,
            ).data()

    # Exact Shopify product_type first (uses product_type index).
    if product_type:
        exact = _run([product_type], use_btu=False)
        if exact:
            return exact

    if not fragments:
        return []

    type_list = _product_types_for_fragments(fragments)
    if not type_list:
        return []

    # Prefer BTU-narrowed candidates when available; fall back to kind types.
    if btu_tokens:
        narrowed = _run(type_list, use_btu=True)
        if narrowed:
            return narrowed
    return _run(type_list, use_btu=False)


def _similar_products(
    product_id: str,
    source_row: dict[str, Any],
    *,
    per_brand_limit: int,
) -> ShopifyPublicSimilarProducts:
    source = _row_to_product(source_row)
    current_vendor = (_first_str(source, "vendor") or "").strip() or None
    source_profile = _extract_product_profile(source)
    candidates = _similar_candidates(source, limit=_SIMILAR_CANDIDATE_LIMIT)

    by_vendor: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    brand_images: dict[str, str] = {}
    for row in candidates:
        candidate_id = str(row.get("id") or "")
        if not candidate_id or candidate_id == _shopify_id(product_id):
            continue
        candidate = _row_to_product(row)
        score = _related_similarity_score(
            source, candidate, source_profile=source_profile
        )
        if score is None:
            continue
        vendor = (_first_str(candidate, "vendor") or "Other").strip()
        if current_vendor and vendor.lower() == current_vendor.lower():
            continue
        by_vendor.setdefault(vendor, []).append((score, candidate))
        brand_image = (row.get("brand_image") or "").strip()
        if brand_image and vendor not in brand_images:
            brand_images[vendor] = brand_image

    brands: list[ShopifyPublicBrandGroup] = []
    for vendor, scored in by_vendor.items():
        scored.sort(key=lambda item: (-item[0], item[1].get("title") or ""))
        products = [
            ShopifyPublicProductRef(id=item["id"], handle=item.get("handle"))
            for _, item in scored[:per_brand_limit]
            if item.get("id")
        ]
        if not products:
            continue
        brands.append(
            ShopifyPublicBrandGroup(
                vendor=vendor,
                image_url=brand_images.get(vendor) or None,
                products=products,
            )
        )

    brands.sort(key=lambda item: (-len(item.products), item.vendor.lower()))
    return ShopifyPublicSimilarProducts(
        product_id=_shopify_id(product_id),
        current_vendor=current_vendor,
        brands=brands,
    )


def _matchups(product_id: str, *, limit: int) -> ShopifyPublicMatchups:
    node_id = _node_id(product_id)
    with neo4j_client.session() as session:
        rows = session.run(
            """
            MATCH (p:ProductGraphNode {id:$id})-[:MATCHES_COMPONENT]->(comp:ProductGraphNode)
            WHERE comp.type IN ['outdoor', 'coil', 'furnace']
            WITH p, collect(DISTINCT comp) AS comps
            WITH p, comps,
                 head([
                   c IN comps WHERE c.type = 'outdoor'
                   | coalesce(c.model, c.label, c.id)
                 ]) AS outdoor_model
            UNWIND comps AS comp
            MATCH (other:ProductGraphNode)-[:MATCHES_COMPONENT]->(comp)
            WHERE other.type = 'product'
              AND other.id <> p.id
              AND other.shopify_id IS NOT NULL
            WITH outdoor_model, other, count(DISTINCT comp) AS shared
            RETURN toString(other.shopify_id) AS id,
                   other.handle AS handle,
                   shared,
                   outdoor_model
            ORDER BY shared DESC, other.handle
            LIMIT $limit
            """,
            id=node_id,
            limit=limit,
        ).data()

    query = ""
    refs: list[ShopifyPublicProductRef] = []
    seen: set[str] = set()
    for row in rows:
        if not query and row.get("outdoor_model"):
            query = str(row["outdoor_model"])
        ref = _ref(row.get("id"), row.get("handle"))
        if ref is None or ref.id in seen:
            continue
        seen.add(ref.id)
        refs.append(ref)

    return ShopifyPublicMatchups(query=query, similar_matchups=refs)


def get_public_shopify_recommendations(
    product_id: str,
    *,
    bought_together_limit: int = 8,
    similar_products_per_brand: int = 8,
    matchups_limit: int = 25,
) -> ShopifyPublicProductResponse:
    """Load slim public Shopify payload entirely from ProductGraphNode."""
    _ensure_connected()
    ensure_product_graph_indexes()

    source_row = _fetch_product(product_id)
    if source_row is None:
        raise KeyError(product_id)

    source_id = str(source_row.get("id") or _shopify_id(product_id))
    source_ref = ShopifyPublicProductRef(
        id=source_id,
        handle=source_row.get("handle"),
    )

    with ThreadPoolExecutor(max_workers=3) as executor:
        fut_bought = executor.submit(
            _bought_together, source_id, limit=bought_together_limit
        )
        fut_similar = executor.submit(
            _similar_products,
            source_id,
            source_row,
            per_brand_limit=similar_products_per_brand,
        )
        fut_matchups = executor.submit(_matchups, source_id, limit=matchups_limit)
        bought_refs = fut_bought.result()
        similar = fut_similar.result()
        matchups = fut_matchups.result()

    if bought_refs and all(ref.id != source_ref.id for ref in bought_refs):
        bought_refs = [source_ref, *bought_refs][: bought_together_limit + 1]

    return ShopifyPublicProductResponse(
        product_id=source_id,
        product=source_ref,
        bought_together=bought_refs,
        similar_products=similar,
        matchups=matchups,
    )
