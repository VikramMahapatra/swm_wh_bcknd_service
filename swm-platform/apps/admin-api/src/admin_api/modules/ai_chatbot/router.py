"""HTTP surface for the AI Chat Bot module: one route per communication mode."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse
from swm_db import get_db_session

from admin_api.api_support import RoleContext, require_roles

from .config import is_configured
from .data_context import build_operations_snapshot
from .schemas import ChatStreamRequest, ReportRequest, ReportResponse
from .service import ai_chatbot_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Any authenticated role may use the assistant; it only ever reads data.
ALL_ROLES = ("admin", "fleet_manager", "supervisor", "operator", "analyst", "read_only")


@router.get("/ai-chatbot/health")
def health():
    return {"configured": is_configured()}


@router.post("/ai-chatbot/chat/stream")
async def chat_stream(
    payload: ChatStreamRequest,
    _ctx: RoleContext = Depends(require_roles(*ALL_ROLES)),
    session: AsyncSession = Depends(get_db_session),
):
    """Mode 1: free-form conversation, streamed token-by-token via Server-Sent Events."""
    if not is_configured():
        raise HTTPException(status_code=503, detail="AI Chat Bot is not configured (missing APP_OPENAI_API_KEY).")

    # Fetched up-front (while the session is still valid) so the live-count
    # snapshot can be embedded in the streamed reply's system prompt.
    live_snapshot = await build_operations_snapshot(session)

    return StreamingResponse(
        ai_chatbot_service.stream_chat(payload.messages, live_snapshot),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable proxy buffering so tokens arrive live
        },
    )


@router.post("/ai-chatbot/report", response_model=ReportResponse)
async def chat_report(
    payload: ReportRequest,
    _ctx: RoleContext = Depends(require_roles(*ALL_ROLES)),
    session: AsyncSession = Depends(get_db_session),
):
    """Mode 2: grounded Q&A over any part of the platform via OpenAI tool-calling."""
    if not is_configured():
        raise HTTPException(status_code=503, detail="AI Chat Bot is not configured (missing APP_OPENAI_API_KEY).")

    try:
        return await ai_chatbot_service.generate_report(payload.question, session, payload.history)
    except Exception as exc:
        logger.exception("AI report generation failed")
        raise HTTPException(status_code=502, detail=f"AI report generation failed: {exc}") from exc
