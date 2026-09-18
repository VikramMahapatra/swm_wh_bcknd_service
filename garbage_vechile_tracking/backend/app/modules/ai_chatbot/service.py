"""
Thin wrapper around the OpenAI SDK for the two chat modes:

1. stream_chat()    -> free-form conversation, streamed token-by-token (SSE).
2. generate_report()-> a single grounded answer built from live operations data,
                       returned as one structured JSON payload (no streaming).

Keeping all OpenAI-specific code in this one file means the router and the
frontend never need to know which model/provider is behind the scenes.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Generator, List

from openai import OpenAI

from .config import get_settings
from .schemas import ChatMessageIn, ReportMetric, ReportResponse

logger = logging.getLogger(__name__)

CHAT_SYSTEM_PROMPT = (
    "You are Swachh Seva Assistant, a helpful AI copilot embedded in a municipal "
    "solid-waste-management fleet tracking platform. Be concise, friendly and "
    "practical. If asked about live fleet numbers, alerts or reports, tell the "
    "user to switch to the 'Data Reports' mode for grounded, up-to-date figures."
)

REPORT_SYSTEM_PROMPT = (
    "You are a data analyst assistant for a municipal solid-waste-management "
    "fleet platform. You will be given a JSON snapshot of live operations data "
    "and a user question. Answer ONLY using the provided data - never invent "
    "numbers. Respond with strict JSON matching this shape: "
    '{"summary": string, "metrics": [{"label": string, "value": string, "hint": string|null}], '
    '"insights": [string]}. "summary" is a 2-3 sentence plain-English answer. '
    '"metrics" are up to 6 key figures relevant to the question. "insights" are '
    "up to 4 short, actionable bullet observations. Do not include markdown fences."
)


class AIChatbotService:
    def __init__(self) -> None:
        self._client: OpenAI | None = None

    def _get_client(self) -> OpenAI:
        settings = get_settings()
        if not settings.api_key:
            raise RuntimeError(
                "APP_OPENAI_API_KEY is not set. Add it to backend/.env to enable the AI Chat Bot."
            )
        # Recreate lazily so a key change (env reload) is picked up without a code change.
        if self._client is None:
            self._client = OpenAI(api_key=settings.api_key, timeout=get_settings().request_timeout_seconds)
        return self._client

    def stream_chat(self, messages: List[ChatMessageIn]) -> Generator[str, None, None]:
        """Yields Server-Sent-Events formatted chunks of the assistant's reply."""
        settings = get_settings()
        client = self._get_client()

        history = messages[-settings.max_history_messages:]
        payload = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
        payload += [{"role": m.role.value, "content": m.content} for m in history]

        try:
            stream = client.chat.completions.create(
                model=settings.model,
                messages=payload,
                stream=True,
                temperature=0.4,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield f"data: {json.dumps({'token': delta})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as exc:  # surfaced to the client as a single error event
            logger.exception("AI chat streaming failed")
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    def generate_report(self, question: str, operations_snapshot: dict) -> ReportResponse:
        settings = get_settings()
        client = self._get_client()

        user_payload = json.dumps({"question": question, "operations_snapshot": operations_snapshot})

        response = client.chat.completions.create(
            model=settings.model,
            messages=[
                {"role": "system", "content": REPORT_SYSTEM_PROMPT},
                {"role": "user", "content": user_payload},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        parsed = json.loads(raw)

        return ReportResponse(
            summary=parsed.get("summary", "No summary was generated."),
            metrics=[ReportMetric(**m) for m in parsed.get("metrics", [])],
            insights=parsed.get("insights", []),
            generated_at=datetime.now(timezone.utc).isoformat(),
        )


# Singleton instance reused across requests (the OpenAI client is safe to share).
ai_chatbot_service = AIChatbotService()
