"""Claude Haiku agent loop with tool retrieval and SSE-friendly events."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import anthropic
from sqlalchemy.orm import Session

from app.config import settings
from app.services.chat.pricing_guard import PRICING_REFUSAL, is_pricing_intent
from app.services.chat.prompts import GENERAL_SYSTEM_PROMPT, product_scoped_system_prompt
from app.services.chat.sanitize import sanitize_for_chat
from app.services.chat.tools import CHAT_TOOLS, PRODUCT_SCOPED_TOOLS, run_tool
from app.shopify.catalog import get_product_detail

MAX_TOOL_ROUNDS = 4
TOKEN_CHUNK_SIZE = 24


def _get_client() -> anthropic.Anthropic:
    if not settings.anthropic_api_key.strip():
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key.strip())


def _history_to_messages(
    history: list[dict[str, str]] | None, user_message: str
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for item in history or []:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message.strip()})
    return messages


def _extract_text(content: list[Any]) -> str:
    parts: list[str] = []
    for block in content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts)


def _sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def sanitize_tool_input(tool_input: dict[str, Any]) -> dict[str, Any]:
    """Drop any accidental price-like keys from tool args shown to the client."""
    cleaned = sanitize_for_chat(tool_input)
    return cleaned if isinstance(cleaned, dict) else {}


def iter_chat_sse(
    db: Session,
    *,
    message: str,
    history: list[dict[str, str]] | None = None,
    product_id: str | None = None,
) -> Iterator[str]:
    """Yield SSE frames: token | retrieval | done | error."""
    text = message.strip()
    if not text:
        yield _sse_event("error", {"message": "message is required"})
        yield _sse_event("done", {"ok": False})
        return

    if is_pricing_intent(text):
        yield _sse_event("token", {"text": PRICING_REFUSAL})
        yield _sse_event("done", {"ok": True, "refused": "pricing"})
        return

    forced_product_id = (product_id or "").strip() or None
    system_prompt = GENERAL_SYSTEM_PROMPT
    tools = CHAT_TOOLS

    if forced_product_id:
        detail = get_product_detail(forced_product_id)
        if detail is None:
            yield _sse_event(
                "error",
                {"message": f"Product '{forced_product_id}' was not found in the Shopify catalog."},
            )
            yield _sse_event("done", {"ok": False})
            return
        system_prompt = product_scoped_system_prompt(
            product_id=forced_product_id,
            title=str(detail.get("title") or forced_product_id),
            sku=detail.get("sku"),
            vendor=detail.get("vendor"),
            product_type=detail.get("product_type"),
        )
        tools = PRODUCT_SCOPED_TOOLS

    try:
        client = _get_client()
    except RuntimeError as exc:
        yield _sse_event("error", {"message": str(exc)})
        yield _sse_event("done", {"ok": False})
        return

    messages = _history_to_messages(history, text)

    try:
        for _round in range(MAX_TOOL_ROUNDS + 1):
            response = client.messages.create(
                model=settings.anthropic_model,
                max_tokens=settings.anthropic_max_tokens,
                system=system_prompt,
                tools=tools,
                messages=messages,
            )

            if response.stop_reason == "tool_use":
                if _round >= MAX_TOOL_ROUNDS:
                    yield _sse_event(
                        "error",
                        {"message": "Too many tool rounds; try a more specific question."},
                    )
                    yield _sse_event("done", {"ok": False})
                    return

                tool_results: list[dict[str, Any]] = []
                for block in response.content:
                    if getattr(block, "type", None) != "tool_use":
                        continue
                    result_text, preview = run_tool(
                        db,
                        block.name,
                        dict(block.input or {}),
                        forced_product_id=forced_product_id,
                    )
                    yield _sse_event(
                        "retrieval",
                        {
                            "tool": block.name,
                            "input": sanitize_tool_input(dict(block.input or {})),
                            "preview": preview,
                        },
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_text,
                        }
                    )

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
                continue

            answer = _extract_text(response.content).strip()
            if not answer:
                answer = (
                    "I could not produce an answer from the available data for this product. "
                    "Try asking about matchups, SKU, or related accessories."
                )
            for i in range(0, len(answer), TOKEN_CHUNK_SIZE):
                yield _sse_event("token", {"text": answer[i : i + TOKEN_CHUNK_SIZE]})
            yield _sse_event("done", {"ok": True})
            return

        yield _sse_event("error", {"message": "Tool loop exhausted without a final answer."})
        yield _sse_event("done", {"ok": False})
    except anthropic.APIError as exc:
        yield _sse_event("error", {"message": f"Claude API error: {exc}"})
        yield _sse_event("done", {"ok": False})
    except Exception as exc:  # noqa: BLE001
        yield _sse_event("error", {"message": str(exc)})
        yield _sse_event("done", {"ok": False})
