"""
Configuration for the AI Chat Bot module.

All settings are read from environment variables (loaded from backend/.env via
python-dotenv in database.py / main.py, which already runs at process start).
Keeping this in one place makes it obvious what the module needs to run.
"""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AIChatbotSettings:
    api_key: str
    model: str
    request_timeout_seconds: float = 60.0
    max_history_messages: int = 20  # how many prior turns we forward to the model


def get_settings() -> AIChatbotSettings:
    """Build settings fresh from the environment on each call (cheap, avoids stale import-time caching)."""
    return AIChatbotSettings(
        api_key=os.getenv("APP_OPENAI_API_KEY", ""),
        model=os.getenv("APP_OPENAI_MODEL", "gpt-4o-mini"),
    )


def is_configured() -> bool:
    return bool(get_settings().api_key)
