"""Request/response contracts for the AI Chat Bot module."""
from enum import Enum
from typing import List, Optional

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


class ReportMetric(BaseModel):
    label: str
    value: str
    hint: Optional[str] = None


class ReportResponse(BaseModel):
    summary: str
    metrics: List[ReportMetric] = Field(default_factory=list)
    insights: List[str] = Field(default_factory=list)
    generated_at: str
