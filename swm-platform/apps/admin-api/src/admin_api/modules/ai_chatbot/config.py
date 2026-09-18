"""
Configuration for the AI Chat Bot module.

Read directly from the environment (docker-compose passes swm-platform/.env via
env_file). Kept independent of swm_common.Settings so this module stays
self-contained and easy to reason about in isolation.
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
    """Built fresh from the environment on each call (cheap, avoids stale caching)."""
    return AIChatbotSettings(
        api_key=os.getenv("APP_OPENAI_API_KEY", ""),
        model=os.getenv("APP_OPENAI_MODEL", "gpt-4o-mini"),
    )


def is_configured() -> bool:
    return bool(get_settings().api_key)
