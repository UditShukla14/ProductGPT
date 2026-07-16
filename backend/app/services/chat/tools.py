"""Tool definitions and executors for Claude chat retrieval."""

from __future__ import annotations

import json
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.schemas.component_search import ComponentSearchRequest
from app.schemas.recommendations import HvacRecommendationRequest
from app.services.chat.sanitize import sanitize_for_chat, truncate_json_text
from app.services.component_search import search_by_component
from app.services.recommender import recommend_hvac_systems
from app.shopify.catalog import (
    get_product_detail,
    products_bought_together,
    search_products,
)
from app.shopify.hvac_matchups import shopify_product_hvac_matchups
from app.shopify.storage import count_records

CHAT_TOOLS: list[dict[str, Any]] = [
    {
        "name": "recommend_hvac",
        "description": (
            "Recommend AHRI-certified Goodman HVAC system matchups using structured "
            "filters (tonnage, SEER2, equipment category, refrigerant, flow, widths)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tonnage": {"type": "number", "description": "System tonnage, e.g. 2 or 2.5"},
                "min_seer": {"type": "number", "description": "Minimum SEER2"},
                "max_seer": {"type": "number", "description": "Maximum SEER2"},
                "equipment_category": {
                    "type": "string",
                    "description": "AC, Heat Pump, Package AC, or Package Heat Pump",
                },
                "refrigerant_type": {
                    "type": "string",
                    "description": "R-32 or R-410A",
                },
                "flow": {
                    "type": "string",
                    "description": "Coil/air-handler orientation: Horizontal or Vertical",
                },
                "coil_width": {"type": "string", "description": "Coil width in inches"},
                "furnace_width": {"type": "string", "description": "Furnace width in inches"},
                "limit": {"type": "integer", "description": "Max results (default 8)"},
                "prefer_higher_seer": {"type": "boolean"},
            },
        },
    },
    {
        "name": "search_hvac_component",
        "description": (
            "Search certified HVAC matchups by outdoor, coil, or furnace model number. "
            "Returns similar AHRI systems and compatible bought-together parts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Outdoor, coil, or furnace model number",
                },
                "component_type": {
                    "type": "string",
                    "enum": ["outdoor", "coil", "furnace", "auto"],
                },
                "equipment_category": {"type": "string"},
                "refrigerant_type": {"type": "string"},
                "flow": {"type": "string"},
                "coil_width": {"type": "string"},
                "furnace_width": {"type": "string"},
                "limit": {"type": "integer"},
                "prefer_higher_seer": {"type": "boolean"},
            },
            "required": ["model"],
        },
    },
    {
        "name": "search_shopify_products",
        "description": "Search the synced Shopify catalog by title, SKU, vendor, or tags.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search text (min 2 characters)"},
                "limit": {"type": "integer", "description": "Max products (default 8)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "shopify_product_context",
        "description": (
            "Load a Shopify product by id with bought-together items and Goodman AHRI "
            "matchups when the SKU maps to HVAC models. Does not include pricing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "Shopify product id"},
                "bought_together_limit": {"type": "integer"},
                "matchups_limit": {"type": "integer"},
            },
            "required": ["product_id"],
        },
    },
]

PRODUCT_SCOPED_TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_selected_product_context",
        "description": (
            "Load the currently selected Shopify product with bought-together items and "
            "Goodman AHRI matchups. Always use this for facts about the selected product. "
            "Does not include pricing. product_id is fixed by the server."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "bought_together_limit": {"type": "integer"},
                "matchups_limit": {"type": "integer"},
            },
        },
    },
]


def _compact_json(payload: Any) -> str:
    cleaned = sanitize_for_chat(payload)
    return truncate_json_text(json.dumps(cleaned, default=str, separators=(",", ":")))


def _summarize_hvac_systems(recommendations: list[Any], *, limit: int = 8) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for rec in recommendations[:limit]:
        system = rec.system
        items.append(
            {
                "ahri_number": system.ahri_number,
                "tonnage": system.tonnage,
                "seer": system.seer,
                "eer": system.eer,
                "hspf": system.hspf,
                "equipment_category": system.equipment_category,
                "refrigerant_type": system.refrigerant_type,
                "indoor_type": system.indoor_type,
                "coil_width": system.coil_width,
                "furnace_width": system.furnace_width,
                "outdoor_model": system.outdoor_model,
                "coil_model": system.coil_model,
                "furnace_model": system.furnace_model,
                "model_status": system.model_status,
                "score": rec.score,
                "reason": rec.reason,
            }
        )
    return items


def execute_recommend_hvac(db: Session, tool_input: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    limit = min(int(tool_input.get("limit") or 8), 10)
    request = HvacRecommendationRequest(
        tonnage=tool_input.get("tonnage"),
        min_seer=tool_input.get("min_seer"),
        max_seer=tool_input.get("max_seer"),
        equipment_category=tool_input.get("equipment_category"),
        refrigerant_type=tool_input.get("refrigerant_type"),
        flow=tool_input.get("flow"),
        coil_width=tool_input.get("coil_width"),
        furnace_width=tool_input.get("furnace_width"),
        limit=limit,
        prefer_higher_seer=bool(tool_input.get("prefer_higher_seer", True)),
    )
    result = recommend_hvac_systems(db, request)
    summary = {
        "recommendations": _summarize_hvac_systems(result.recommendations, limit=limit),
        "meta": {
            "strategy_used": result.meta.get("strategy_used"),
            "candidate_count": result.meta.get("candidate_count"),
            "returned": result.meta.get("returned"),
        },
    }
    return _compact_json(summary), {
        "tool": "recommend_hvac",
        "count": len(summary["recommendations"]),
        "items": summary["recommendations"],
    }


def execute_search_hvac_component(db: Session, tool_input: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    limit = min(int(tool_input.get("limit") or 8), 10)
    request = ComponentSearchRequest(
        model=str(tool_input["model"]),
        component_type=tool_input.get("component_type") or "auto",
        equipment_category=tool_input.get("equipment_category"),
        refrigerant_type=tool_input.get("refrigerant_type"),
        flow=tool_input.get("flow"),
        coil_width=tool_input.get("coil_width"),
        furnace_width=tool_input.get("furnace_width"),
        limit=limit,
        prefer_higher_seer=bool(tool_input.get("prefer_higher_seer", True)),
    )
    result = search_by_component(db, request)
    summary = {
        "query": result.query,
        "matched_type": result.matched_type,
        "matched_model": result.matched_model,
        "similar_matchups": _summarize_hvac_systems(result.similar_matchups, limit=limit),
        "bought_together": [
            {
                "type": item.type,
                "model": item.model,
                "matchup_count": item.matchup_count,
                "best_seer": item.best_seer,
            }
            for item in result.bought_together[:8]
        ],
        "meta": {
            "total_matchups": result.meta.get("total_matchups"),
            "returned": result.meta.get("returned"),
        },
    }
    return _compact_json(summary), {
        "tool": "search_hvac_component",
        "matched_model": result.matched_model,
        "matched_type": result.matched_type,
        "count": len(summary["similar_matchups"]),
        "items": summary["similar_matchups"],
    }


def execute_search_shopify_products(_db: Session, tool_input: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if count_records("products") == 0:
        payload = {"error": "Shopify products database is empty. Data has not been synced yet."}
        return _compact_json(payload), {"tool": "search_shopify_products", "count": 0, "items": []}

    limit = min(int(tool_input.get("limit") or 8), 10)
    products = search_products(str(tool_input["query"]), limit=limit)
    # Explicitly drop price even before sanitize (defense in depth).
    cleaned = [
        {
            "id": p.get("id"),
            "title": p.get("title"),
            "vendor": p.get("vendor"),
            "product_type": p.get("product_type"),
            "sku": p.get("sku"),
            "status": p.get("status"),
            "handle": p.get("handle"),
            "image_url": p.get("image_url"),
        }
        for p in products
    ]
    summary = {"query": tool_input["query"], "results": cleaned}
    return _compact_json(summary), {
        "tool": "search_shopify_products",
        "count": len(cleaned),
        "items": cleaned,
    }


def execute_shopify_product_context(db: Session, tool_input: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if count_records("products") == 0:
        payload = {"error": "Shopify products database is empty. Data has not been synced yet."}
        return _compact_json(payload), {"tool": "shopify_product_context", "count": 0}

    product_id = str(tool_input["product_id"]).strip()
    detail = get_product_detail(product_id)
    if detail is None:
        payload = {"error": f"Product '{product_id}' not found"}
        return _compact_json(payload), {"tool": "shopify_product_context", "count": 0}

    bought_limit = min(int(tool_input.get("bought_together_limit") or 5), 8)
    matchups_limit = min(int(tool_input.get("matchups_limit") or 8), 10)

    bought = (
        products_bought_together(product_id, limit=bought_limit)
        if count_records("orders") > 0
        else []
    )
    matchups = shopify_product_hvac_matchups(
        db,
        product_id,
        limit=matchups_limit,
        prefer_higher_seer=True,
    )

    product_view = {
        "id": detail.get("id"),
        "title": detail.get("title"),
        "vendor": detail.get("vendor"),
        "product_type": detail.get("product_type"),
        "sku": detail.get("sku"),
        "status": detail.get("status"),
        "handle": detail.get("handle"),
        "tags": detail.get("tags"),
        "description": detail.get("description"),
        "variants": [
            {
                "id": v.get("id"),
                "sku": v.get("sku"),
                "title": v.get("title"),
                "inventory_quantity": v.get("inventory_quantity"),
                "available_for_sale": v.get("available_for_sale"),
            }
            for v in (detail.get("variants") or [])[:8]
        ],
    }
    bought_view = [
        {
            "product": {
                "id": item["product"].get("id"),
                "title": item["product"].get("title"),
                "vendor": item["product"].get("vendor"),
                "sku": item["product"].get("sku"),
                "product_type": item["product"].get("product_type"),
            },
            "order_count": item.get("order_count"),
            "reason": item.get("reason"),
        }
        for item in bought
    ]
    matchup_view = {
        "matched_type": matchups.matched_type,
        "matched_model": matchups.matched_model,
        "similar_matchups": _summarize_hvac_systems(matchups.similar_matchups, limit=matchups_limit),
        "bought_together": [
            {
                "type": item.type,
                "model": item.model,
                "matchup_count": item.matchup_count,
                "best_seer": item.best_seer,
            }
            for item in matchups.bought_together[:8]
        ],
    }
    summary = {
        "product_id": product_id,
        "product": product_view,
        "bought_together": bought_view,
        "matchups": matchup_view,
    }
    return _compact_json(summary), {
        "tool": "shopify_product_context",
        "product_id": product_id,
        "product": product_view,
        "matchup_count": len(matchup_view["similar_matchups"]),
        "bought_together_count": len(bought_view),
    }


TOOL_EXECUTORS: dict[str, Callable[[Session, dict[str, Any]], tuple[str, dict[str, Any]]]] = {
    "recommend_hvac": execute_recommend_hvac,
    "search_hvac_component": execute_search_hvac_component,
    "search_shopify_products": execute_search_shopify_products,
    "shopify_product_context": execute_shopify_product_context,
    "get_selected_product_context": execute_shopify_product_context,
}


def run_tool(
    db: Session,
    name: str,
    tool_input: dict[str, Any],
    *,
    forced_product_id: str | None = None,
) -> tuple[str, dict[str, Any]]:
    executor = TOOL_EXECUTORS.get(name)
    if executor is None:
        payload = {"error": f"Unknown tool: {name}"}
        return _compact_json(payload), {"tool": name, "error": "unknown_tool"}

    effective_input = dict(tool_input or {})
    if forced_product_id and name in {"shopify_product_context", "get_selected_product_context"}:
        effective_input["product_id"] = forced_product_id

    if forced_product_id and name not in {"shopify_product_context", "get_selected_product_context"}:
        payload = {
            "error": (
                f"Tool '{name}' is not available in product-scoped chat. "
                "Use get_selected_product_context for the selected product only."
            )
        }
        return _compact_json(payload), {"tool": name, "error": "tool_not_allowed"}

    try:
        return executor(db, effective_input)
    except Exception as exc:  # noqa: BLE001 — surface tool failures to the model
        payload = {"error": str(exc)}
        return _compact_json(payload), {"tool": name, "error": str(exc)}
