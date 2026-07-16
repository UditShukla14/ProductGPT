"""Strip pricing and truncate payloads before sending tool results to Claude."""

from __future__ import annotations

from typing import Any

PRICE_KEY_FRAGMENTS = (
    "price",
    "cost",
    "msrp",
    "amount",
    "subtotal",
    "total_price",
    "unit_price",
    "compare_at",
    "discount",
    "tax",
    "money",
    "currency",
)

MAX_LIST_ITEMS = 8
MAX_STRING_LEN = 500
MAX_JSON_CHARS = 12_000


def _is_price_key(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in PRICE_KEY_FRAGMENTS)


def sanitize_for_chat(value: Any, *, _depth: int = 0) -> Any:
    """Recursively drop price/money fields and bound payload size."""
    if _depth > 8:
        return None

    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if _is_price_key(str(key)):
                continue
            # Drop bulky raw dumps that are not useful for chat grounding.
            if key in {"raw_json", "all_fields", "accessories"}:
                continue
            cleaned[key] = sanitize_for_chat(item, _depth=_depth + 1)
        return cleaned

    if isinstance(value, list):
        return [sanitize_for_chat(item, _depth=_depth + 1) for item in value[:MAX_LIST_ITEMS]]

    if isinstance(value, str) and len(value) > MAX_STRING_LEN:
        return value[: MAX_STRING_LEN - 1] + "…"

    return value


def truncate_json_text(text: str, *, max_chars: int = MAX_JSON_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"
