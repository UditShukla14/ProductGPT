from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.chat import ChatMessageRequest
from app.services.chat.stream import stream_chat_messages

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/messages")
def post_chat_message(
    payload: ChatMessageRequest, db: Session = Depends(get_db)
) -> StreamingResponse:
    """Internal/UI product-scoped chat (SSE)."""
    return stream_chat_messages(db, payload)
