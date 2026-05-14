"""
swm_common.logger
=================
Production-grade structured logger factory for the SWM Fleet Platform.

Features
--------
- JSON lines output in production (structlog JSONRenderer)
- Human-readable colour output in dev (structlog ConsoleRenderer)
- Per-request context vars: request_id, correlation_id, trace_id
- Worker-scoped context: worker_name, task_id
- Automatic latency_ms injection (via middleware / manual timer)
- Full exception logging with traceback as a structured field
- File log rotation via stdlib RotatingFileHandler (optional)
- Zero configuration beyond ENV= and LOG_LEVEL= in .env
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
import traceback
from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Any, cast

import orjson
import structlog
from structlog.typing import FilteringBoundLogger

# ---------------------------------------------------------------------------
# Context variable field names (also used by middleware)
# ---------------------------------------------------------------------------
CTX_REQUEST_ID = "request_id"
CTX_CORRELATION_ID = "correlation_id"
CTX_TRACE_ID = "trace_id"
CTX_WORKER_NAME = "worker_name"
CTX_LATENCY_MS = "latency_ms"

# ---------------------------------------------------------------------------
# orjson-backed JSON renderer (handles datetime, UUID, bytes natively)
# ---------------------------------------------------------------------------


def _orjson_renderer(
    _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
) -> str:
    return orjson.dumps(dict(event_dict)).decode()


# ---------------------------------------------------------------------------
# Public API: configure_logging()
# ---------------------------------------------------------------------------


def configure_logging(
    log_level: str = "INFO",
    env: str = "dev",
    *,
    log_file: Path | None = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB per file
    backup_count: int = 5,
) -> None:
    """
    Initialise structlog and the stdlib root logger.

    Call once at application startup (e.g. in ``main.py`` before ``uvicorn.run``).

    Parameters
    ----------
    log_level:
        Standard level string: DEBUG, INFO, WARNING, ERROR, CRITICAL.
    env:
        ``"dev"`` → coloured console output.
        Anything else (``"prod"``, ``"staging"`` …) → JSON lines.
    log_file:
        Optional path.  When set, a ``RotatingFileHandler`` is added that always
        writes JSON regardless of ``env``.
    max_bytes:
        Rotation threshold for the file handler.
    backup_count:
        Number of rotated files to keep.
    """
    level_map: Mapping[str, int] = logging.getLevelNamesMapping()
    resolved_level = level_map.get(log_level.upper(), logging.INFO)
    is_dev = env.lower() == "dev"

    # --- shared pre-processors (always run) ---------------------------------
    shared_pre: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.FUNC_NAME,
            ]
        ),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.ExceptionRenderer(),
    ]

    if is_dev:
        # Pretty, coloured output with exception rendering inline
        renderer: Any = structlog.dev.ConsoleRenderer(
            exception_formatter=structlog.dev.plain_traceback,
        )
    else:
        renderer = _orjson_renderer

    structlog.configure(
        processors=[*shared_pre, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.make_filtering_bound_logger(resolved_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )

    # --- stdlib handler: stdout ---------------------------------------------
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                renderer,
            ],
            foreign_pre_chain=shared_pre,
        )
    )

    handlers: list[logging.Handler] = [stdout_handler]

    # --- stdlib handler: rotating file (JSON always) ------------------------
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler: logging.Handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processors=[
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    _orjson_renderer,
                ],
                foreign_pre_chain=shared_pre,
            )
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=resolved_level,
        handlers=handlers,
        force=True,  # overwrite any earlier basicConfig call
    )

    # Silence noisy third-party loggers
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "hpack"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Public API: get_logger()
# ---------------------------------------------------------------------------


def get_logger(name: str, **initial_context: Any) -> FilteringBoundLogger:
    """
    Return a structlog ``FilteringBoundLogger`` pre-bound with *initial_context*.

    Usage
    -----
    ::

        logger = get_logger(__name__, worker_name="storage-worker")
        logger.info("task_started", task_id="abc123")
    """
    logger = structlog.get_logger(name)
    if initial_context:
        return cast(FilteringBoundLogger, logger.bind(**initial_context))
    return cast(FilteringBoundLogger, logger)


# ---------------------------------------------------------------------------
# Public API: context helpers
# ---------------------------------------------------------------------------


def bind_request_context(
    *,
    request_id: str,
    correlation_id: str,
    trace_id: str,
) -> None:
    """Bind per-request IDs into structlog's contextvars store."""
    structlog.contextvars.bind_contextvars(
        **{
            CTX_REQUEST_ID: request_id,
            CTX_CORRELATION_ID: correlation_id,
            CTX_TRACE_ID: trace_id,
        }
    )


def bind_worker_context(worker_name: str, **extra: Any) -> None:
    """Bind worker-scoped fields into structlog's contextvars store."""
    structlog.contextvars.bind_contextvars(**{CTX_WORKER_NAME: worker_name, **extra})


def clear_context() -> None:
    """Clear all bound contextvars (call at the end of each request / task)."""
    structlog.contextvars.clear_contextvars()


# ---------------------------------------------------------------------------
# Public API: exception helper
# ---------------------------------------------------------------------------


def log_exception(
    logger: FilteringBoundLogger,
    exc: BaseException,
    message: str = "unhandled_exception",
    **extra: Any,
) -> None:
    """
    Log *exc* with a structured ``exception`` field containing the full
    traceback string, plus any *extra* context fields.

    This is useful in ``except`` blocks where you want structured JSON output
    rather than a raw stderr dump.

    Usage
    -----
    ::

        try:
            ...
        except Exception as exc:
            log_exception(logger, exc, "db_query_failed", table="device_events")
    """
    logger.error(
        message,
        exc_info=exc,
        exception_type=type(exc).__qualname__,
        exception_detail=str(exc),
        traceback="".join(traceback.format_exception(exc)),
        **extra,
    )
