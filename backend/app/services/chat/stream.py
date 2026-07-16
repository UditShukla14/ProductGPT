"""Shared SSE streaming response for product-scoped chat."""

from __future__ import annotations

from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.schemas.chat import ChatMessageRequest
from app.services.chat.agent import iter_chat_sse


def stream_chat_messages(db: Session, payload: ChatMessageRequest) -> StreamingResponse:
    history = [item.model_dump() for item in payload.history]

    def event_stream():
        yield from iter_chat_sse(
            db,
            message=payload.message,
            history=history,
            product_id=payload.product_id,
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
