"""
swm_common.log_middleware
=========================
Starlette/FastAPI middleware that:

- Generates or propagates ``X-Request-Id``, ``X-Correlation-Id``,
  ``X-Trace-Id`` headers.
- Binds them into structlog contextvars for the duration of the request so
  every log line emitted inside that request automatically carries the IDs.
- Measures wall-clock latency and appends ``latency_ms`` to the final log.
- Emits a single structured ``http_request`` access log per request.
- Propagates the IDs back to the caller via response headers.
- Clears contextvars after each request so worker threads / tasks don't bleed
  context.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from swm_common.logger import (
    CTX_LATENCY_MS,
    bind_request_context,
    clear_context,
    get_logger,
)

_logger = get_logger("swm.access")

# Header names (canonical HTTP spelling)
HEADER_REQUEST_ID = "X-Request-Id"
HEADER_CORRELATION_ID = "X-Correlation-Id"
HEADER_TRACE_ID = "X-Trace-Id"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI/Starlette middleware that logs every HTTP request as structured JSON.

    Mount once at application creation::

        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)

    Every downstream log line automatically carries::

        request_id      unique per HTTP request (UUID4)
        correlation_id  propagated from X-Correlation-Id header or generated
        trace_id        propagated from X-Trace-Id header or generated
        latency_ms      added to the final access log entry
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # --- resolve / generate IDs -----------------------------------------
        request_id = request.headers.get(HEADER_REQUEST_ID) or str(uuid.uuid4())
        correlation_id = request.headers.get(HEADER_CORRELATION_ID) or request_id
        trace_id = request.headers.get(HEADER_TRACE_ID) or request_id

        # --- bind into structlog context (visible in ALL log lines below) ---
        bind_request_context(
            request_id=request_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )

        # --- call actual handler & measure latency --------------------------
        start_ns = time.perf_counter_ns()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            _logger.exception(
                "request_unhandled_exception",
                method=request.method,
                path=request.url.path,
            )
            raise
        finally:
            latency_ms = (time.perf_counter_ns() - start_ns) / 1_000_000

            _logger.info(
                "http_request",
                method=request.method,
                path=request.url.path,
                query=str(request.url.query) or None,
                status_code=status_code,
                **{CTX_LATENCY_MS: round(latency_ms, 3)},
                client_host=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            )

            clear_context()

        # --- propagate IDs back to caller -----------------------------------
        response.headers[HEADER_REQUEST_ID] = request_id
        response.headers[HEADER_CORRELATION_ID] = correlation_id
        response.headers[HEADER_TRACE_ID] = trace_id

        return response
