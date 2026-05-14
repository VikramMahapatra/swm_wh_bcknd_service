"""
Pytest configuration for the swm-platform test suite.

Provides an autouse fixture that resets structlog to a simple, cache-free
configuration before every test so that:

  - structlog.testing.capture_logs() works correctly
  - Module-level cached loggers are invalidated between tests
  - Tests are fully isolated from each other's logging configuration
"""

from __future__ import annotations

import logging

import pytest
import structlog


@pytest.fixture(autouse=True)
def reset_structlog() -> None:
    """Reset structlog to a minimal test configuration before each test."""
    structlog.reset_defaults()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
    structlog.contextvars.clear_contextvars()
