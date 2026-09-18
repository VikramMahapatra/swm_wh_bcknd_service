"""
Thin wrapper around the OpenAI SDK for the two chat modes:

1. stream_chat()    -> free-form conversation, streamed token-by-token (SSE).
                       Given a lightweight live-data snapshot so it can answer
                       common overview questions directly while streaming.
2. generate_report()-> grounded Q&A over ANY part of the platform. Uses OpenAI
                       function-calling: the model picks which tool(s) in
                       tools.py to call (fleet, alerts, zones, vendors,
                       devices, routes, drivers, tickets, trip/idle analytics,
                       weighments, GTS checkpoints), we execute them against
                       Postgres, and the model turns the results into one
                       structured JSON answer. No streaming (needs the DB
                       session live for the whole tool-calling round trip).

Keeping all OpenAI-specific code in this one file means the router and the
frontend never need to know which model/provider or data domains exist.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Generator, List
from zoneinfo import ZoneInfo

from openai import AsyncOpenAI, OpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .schemas import ChatMessageIn, ReportMetric, ReportResponse
from .tools import TOOL_SPECS, execute_tool

logger = logging.getLogger(__name__)

CHAT_SYSTEM_PROMPT = (
    "You are Swachh Seva Assistant, a helpful AI copilot embedded in a municipal "
    "solid-waste-management fleet tracking platform. Be concise, friendly and "
    "practical. The platform covers: live fleet tracking, routes & pickup points, "
    "alerts, zones/wards, vendors, devices, drivers, tickets/complaints, GTS "
    "checkpoints, dump yard weighments, and trip/idle analytics reports. You are "
    "given a snapshot of current live numbers below - use it when relevant. For "
    "deeper questions (e.g. specific vendors, tickets, historical reports), tell "
    "the user to switch to 'Data Reports' mode, which can look up any part of "
    "the system precisely.\n\nCurrent live snapshot:\n{snapshot}"
)

REPORT_SYSTEM_PROMPT_TEMPLATE = (
    "You are a data analyst assistant for a municipal solid-waste-management "
    "fleet platform. The current date/time is __NOW_IST__ (IST) - use this for "
    "'today'/'yesterday' and any date_from/date_to arguments; never guess a "
    "different date. Use the provided tools to fetch whatever live data you "
    "need to answer the user's question - covering fleet status, alerts, "
    "zones/wards, vendors, devices, routes/pickup points, drivers, tickets, "
    "trip/idle analytics, dump yard weighments, and GTS checkpoints. If the "
    "user asks for a NAMED LIST (specific trucks, drivers, tickets, etc. - not "
    "just a count), call get_vehicle_list or another list-returning tool and "
    "include every matching row in the 'items' field below. If the user "
    "mentions ANY time window ('last hour', 'last 30 minutes', 'today', 'last "
    "24 hours'), you MUST pass the matching since_minutes argument (e.g. 'last "
    "1 hour' -> since_minutes=60) to get_alerts_overview/get_tickets_overview - "
    "otherwise those tools return all-time totals, which would be misleading. "
    "Likewise, if the user names a specific zone or ward, you MUST pass "
    "zone_name/ward_name to the tool - never claim results are scoped to a "
    "zone/ward/time-window in your answer unless you actually passed that "
    "filter argument to the tool and its response's 'scope'/'time_window' "
    "field confirms it; a tool that returns 0 matches for a zone name means "
    "that zone likely doesn't exist - say so, don't substitute fleet-wide data. "
    "Any 'triggered_at'/'created_at'/'arrived_at' timestamps returned by tools "
    "are already formatted in India Standard Time (IST) and labeled as such - "
    "use them as-is, do not convert or re-interpret them as UTC. "
    "Call as many tools as needed (in sequence) before answering. Never invent "
    "data - only use what the tools return. Once you have enough information, "
    "respond with ONLY strict JSON matching this shape (no markdown fences): "
    '{"summary": string, "metrics": [{"label": string, "value": string, "hint": string|null}], '
    '"insights": [string], "items": [object]}. "summary" is a 2-4 sentence '
    'plain-English answer. "metrics" are up to 6 key figures relevant to the '
    'question (omit for pure list questions). "insights" are up to 4 short, '
    'actionable observations. "items" is the full list of matching records '
    "when the user asked for named/individual results (e.g. each item might be "
    '{"vehicle_number": "...", "driver_name": "..."}) - leave empty otherwise.'
)

MAX_TOOL_ROUNDS = 8

_IST = ZoneInfo("Asia/Kolkata")


def _build_report_system_prompt() -> str:
    now_ist = datetime.now(_IST).strftime("%Y-%m-%d %I:%M %p IST (%A)")
    return REPORT_SYSTEM_PROMPT_TEMPLATE.replace("__NOW_IST__", now_ist)


class AIChatbotService:
    def __init__(self) -> None:
        self._client: OpenAI | None = None
        self._async_client: AsyncOpenAI | None = None

    def _get_client(self) -> OpenAI:
        settings = get_settings()
        if not settings.api_key:
            raise RuntimeError("APP_OPENAI_API_KEY is not set. Add it to swm-platform/.env to enable the AI Chat Bot.")
        if self._client is None:
            self._client = OpenAI(api_key=settings.api_key, timeout=settings.request_timeout_seconds)
        return self._client

    def _get_async_client(self) -> AsyncOpenAI:
        settings = get_settings()
        if not settings.api_key:
            raise RuntimeError("APP_OPENAI_API_KEY is not set. Add it to swm-platform/.env to enable the AI Chat Bot.")
        if self._async_client is None:
            self._async_client = AsyncOpenAI(api_key=settings.api_key, timeout=settings.request_timeout_seconds)
        return self._async_client

    def stream_chat(self, messages: List[ChatMessageIn], live_snapshot: dict) -> Generator[str, None, None]:
        """Yields Server-Sent-Events formatted chunks of the assistant's reply."""
        settings = get_settings()

        try:
            client = self._get_client()
        except RuntimeError as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
            return

        history = messages[-settings.max_history_messages:]
        system_prompt = CHAT_SYSTEM_PROMPT.format(snapshot=json.dumps(live_snapshot))
        payload = [{"role": "system", "content": system_prompt}]
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

    async def generate_report(self, question: str, session: AsyncSession, history: List[ChatMessageIn] | None = None) -> ReportResponse:
        settings = get_settings()
        client = self._get_async_client()

        prior_turns = (history or [])[-settings.max_history_messages:]
        conversation: list[dict] = [
            {"role": "system", "content": _build_report_system_prompt()},
            *({"role": m.role.value, "content": m.content} for m in prior_turns),
            {"role": "user", "content": question},
        ]

        for _ in range(MAX_TOOL_ROUNDS):
            response = await client.chat.completions.create(
                model=settings.model,
                messages=conversation,
                tools=TOOL_SPECS,
                tool_choice="auto",
                temperature=0.2,
                # Enforce strict JSON even on the very first non-tool-call answer -
                # without this the model sometimes replies with a markdown report
                # instead of the structured JSON, especially for broad "consolidate
                # everything" style questions.
                response_format={"type": "json_object"},
            )
            message = response.choices[0].message
            tool_calls = message.tool_calls or []

            if not tool_calls:
                return self._parse_report(message.content or "")

            conversation.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                        for tc in tool_calls
                    ],
                }
            )
            for tc in tool_calls:
                try:
                    arguments = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                result = await execute_tool(tc.function.name, arguments, session)
                conversation.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})

        # Ran out of tool-call rounds - ask once more for a final answer, no more tools.
        final = await client.chat.completions.create(
            model=settings.model,
            messages=conversation
            + [
                {
                    "role": "user",
                    "content": (
                        "Answer now. Respond with ONLY the flat JSON object described earlier - "
                        '{"summary": string, "metrics": [...], "insights": [...], "items": [...]}. '
                        "Do not nest another JSON object or string inside the 'summary' field."
                    ),
                }
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        return self._parse_report(final.choices[0].message.content or "")

    def _parse_report(self, raw_content: str) -> ReportResponse:
        parsed = self._extract_json_object(raw_content)

        summary = parsed.get("summary", "No summary was generated.")
        if isinstance(summary, str) and summary.strip().startswith("{"):
            # The model sometimes double-encodes: puts the whole JSON object,
            # as a string, inside its own "summary" field. Unwrap one level
            # rather than showing that raw JSON text to the user.
            nested = self._extract_json_object(summary)
            if nested:
                parsed = {**nested, **{k: v for k, v in parsed.items() if k != "summary"}}
                summary = nested.get("summary", summary)

        return ReportResponse(
            summary=summary if isinstance(summary, str) else "No summary was generated.",
            metrics=[ReportMetric(**m) for m in parsed.get("metrics", [])],
            insights=parsed.get("insights", []),
            items=parsed.get("items", []),
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _extract_json_object(raw_content: str) -> dict:
        """Parses the model's JSON answer defensively: strips markdown code fences,
        and if there's stray prose around the object, extracts the {...} substring.
        Never lets raw/broken JSON leak to the user as if it were the summary text."""
        raw = (raw_content or "").strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw[:4].lower() == "json":
                raw = raw[4:]
            raw = raw.strip()

        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                pass

        # Truly unparsable - fall back to the raw text as a plain-English answer,
        # unless it looks like broken JSON, in which case don't show that to the user.
        looks_like_json = raw.startswith("{") and raw.endswith("}")
        return {"summary": "I couldn't format that answer correctly - please try rephrasing the question." if looks_like_json else raw}


# Singleton instance reused across requests (the OpenAI clients are safe to share).
ai_chatbot_service = AIChatbotService()
