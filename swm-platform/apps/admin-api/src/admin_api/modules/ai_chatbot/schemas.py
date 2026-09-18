"""Request/response contracts for the AI Chat Bot module."""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessageIn(BaseModel):
    role: ChatRole
    content: str


class ChatStreamRequest(BaseModel):
    """Payload for the streaming, free-form conversation endpoint."""
    messages: List[ChatMessageIn] = Field(..., min_length=1)


class ReportRequest(BaseModel):
    """Payload for the structured, data-grounded reporting endpoint."""
    question: str = Field(..., min_length=1)
    # Prior turns in this Data Reports conversation, oldest first, so follow-up
    # questions ("what about zone B?") can be answered with context.
    history: List[ChatMessageIn] = Field(default_factory=list)


class ReportMetric(BaseModel):
    label: str
    value: str
    hint: Optional[str] = None


class ReportResponse(BaseModel):
    summary: str
    metrics: List[ReportMetric] = Field(default_factory=list)
    insights: List[str] = Field(default_factory=list)
    # Row-based data for "list X" style questions (e.g. named trucks + drivers),
    # rendered as a table by the frontend. Each item is a flat {column: value} dict.
    items: List[Dict[str, Any]] = Field(default_factory=list)
    generated_at: str
