"""HTTP surface for the AI Chat Bot module: one route per communication mode."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from ...database.database import get_db
from ...routers.auth import get_current_user
from .config import is_configured
from .data_context import build_operations_snapshot
from .schemas import ChatStreamRequest, ReportRequest, ReportResponse
from .service import ai_chatbot_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-chatbot", tags=["ai-chatbot"])


@router.get("/health")
def health():
    return {"configured": is_configured()}


@router.post("/chat/stream")
def chat_stream(payload: ChatStreamRequest, _user=Depends(get_current_user)):
    """Mode 1: free-form conversation, streamed token-by-token via Server-Sent Events."""
    if not is_configured():
        raise HTTPException(status_code=503, detail="AI Chat Bot is not configured (missing APP_OPENAI_API_KEY).")

    return StreamingResponse(
        ai_chatbot_service.stream_chat(payload.messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable proxy buffering so tokens arrive live
        },
    )


@router.post("/report", response_model=ReportResponse)
def chat_report(payload: ReportRequest, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    """Mode 2: one grounded answer built from the current live operations data."""
    if not is_configured():
        raise HTTPException(status_code=503, detail="AI Chat Bot is not configured (missing APP_OPENAI_API_KEY).")

    snapshot = build_operations_snapshot(db)
    try:
        return ai_chatbot_service.generate_report(payload.question, snapshot)
    except Exception as exc:
        logger.exception("AI report generation failed")
        raise HTTPException(status_code=502, detail=f"AI report generation failed: {exc}") from exc
