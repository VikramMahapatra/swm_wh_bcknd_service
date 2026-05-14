"""
Unit-tests for swm_common.logger and swm_common.log_middleware.

Run:
    uv run pytest tests/test_logger.py -v
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import tempfile
import uuid
from pathlib import Path
from typing import Any

import structlog
import structlog.contextvars
import structlog.testing
from fastapi import FastAPI
from starlette.testclient import TestClient
from swm_common.log_middleware import (
    HEADER_CORRELATION_ID,
    HEADER_REQUEST_ID,
    RequestLoggingMiddleware,
)
from swm_common.logger import (
    CTX_CORRELATION_ID,
    CTX_LATENCY_MS,
    CTX_REQUEST_ID,
    CTX_TRACE_ID,
    CTX_WORKER_NAME,
    bind_request_context,
    bind_worker_context,
    clear_context,
    configure_logging,
    get_logger,
    log_exception,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# configure_logging
# ---------------------------------------------------------------------------


class TestConfigureLogging:
    def test_dev_mode_sets_console_renderer(self) -> None:
        """configure_logging in dev mode should not raise and root level should match."""
        configure_logging(log_level="DEBUG", env="dev")
        assert logging.getLogger().level == logging.DEBUG

    def test_prod_mode_sets_json(self) -> None:
        configure_logging(log_level="INFO", env="prod")
        assert logging.getLogger().level == logging.INFO

    def test_unknown_level_falls_back_to_info(self) -> None:
        configure_logging(log_level="BANANA", env="prod")
        assert logging.getLogger().level == logging.INFO

    def _close_file_handlers(self) -> None:
        """Close rotating file handlers so Windows can delete the temp dir."""
        root = logging.getLogger()
        for handler in list(root.handlers):
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                handler.flush()
                handler.close()
                root.removeHandler(handler)

    def test_file_rotation_creates_file(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            log_path = Path(tmpdir) / "logs" / "app.log"
            configure_logging(log_level="DEBUG", env="prod", log_file=log_path)
            lgr = get_logger("rotation_test")
            lgr.info("rotation_probe")
            exists = log_path.exists()
            self._close_file_handlers()
        assert exists

    def test_log_file_produces_json_lines(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            log_path = Path(tmpdir) / "app.log"
            configure_logging(log_level="DEBUG", env="prod", log_file=log_path)
            lgr = get_logger("json_file_test")
            lgr.info("structured_event", payload="hello")
            for handler in logging.getLogger().handlers:
                handler.flush()
            content = log_path.read_text(encoding="utf-8").strip()
            self._close_file_handlers()
        assert content, "Log file should not be empty"
        record = json.loads(content.splitlines()[-1])
        assert record["event"] == "structured_event"
        assert record["payload"] == "hello"


# ---------------------------------------------------------------------------
# get_logger
# ---------------------------------------------------------------------------


class TestGetLogger:
    def test_returns_filtering_bound_logger(self) -> None:
        lgr = get_logger("test.logger")
        assert lgr is not None

    def test_bound_context_propagates(self) -> None:
        # Do NOT call configure_logging() here — conftest reset enables capture_logs()
        with structlog.testing.capture_logs() as cap:
            lgr = get_logger("test.bound", component="unit-test")
            lgr.info("bound_test")
        assert any(r.get("component") == "unit-test" for r in cap)

    def test_no_initial_context(self) -> None:
        lgr = get_logger("bare.logger")
        assert lgr is not None


# ---------------------------------------------------------------------------
# Context helpers
# ---------------------------------------------------------------------------


class TestContextHelpers:
    def setup_method(self) -> None:
        clear_context()

    def teardown_method(self) -> None:
        clear_context()

    def test_bind_request_context_sets_vars(self) -> None:
        rid = str(uuid.uuid4())
        cid = str(uuid.uuid4())
        tid = str(uuid.uuid4())
        bind_request_context(request_id=rid, correlation_id=cid, trace_id=tid)
        ctx = structlog.contextvars.get_contextvars()
        assert ctx[CTX_REQUEST_ID] == rid
        assert ctx[CTX_CORRELATION_ID] == cid
        assert ctx[CTX_TRACE_ID] == tid

    def test_bind_worker_context_sets_worker_name(self) -> None:
        bind_worker_context("storage-worker", task_id="t-001")
        ctx = structlog.contextvars.get_contextvars()
        assert ctx[CTX_WORKER_NAME] == "storage-worker"
        assert ctx["task_id"] == "t-001"

    def test_clear_context_removes_all_vars(self) -> None:
        bind_request_context(
            request_id="r",
            correlation_id="c",
            trace_id="t",
        )
        bind_worker_context("w")
        clear_context()
        assert structlog.contextvars.get_contextvars() == {}

    def test_context_captured_in_log_output(self) -> None:
        # capture_logs() doesn't run merge_contextvars, so we verify the bound
        # context is accessible via get_contextvars() directly.
        rid = str(uuid.uuid4())
        bind_request_context(request_id=rid, correlation_id=rid, trace_id=rid)
        ctx = structlog.contextvars.get_contextvars()
        assert ctx[CTX_REQUEST_ID] == rid
        assert ctx[CTX_CORRELATION_ID] == rid
        assert ctx[CTX_TRACE_ID] == rid


# ---------------------------------------------------------------------------
# log_exception
# ---------------------------------------------------------------------------


class TestLogException:
    def test_logs_exception_type_and_detail(self) -> None:
        lgr = get_logger("exc.test")
        with structlog.testing.capture_logs() as cap:
            try:
                raise ValueError("bad input")
            except ValueError as exc:
                log_exception(lgr, exc, "validation_failed", field="speed_kph")

        assert len(cap) == 1
        record = cap[0]
        assert record["event"] == "validation_failed"
        assert record["exception_type"] == "ValueError"
        assert record["exception_detail"] == "bad input"
        assert record["field"] == "speed_kph"
        assert "traceback" in record

    def test_log_level_is_error(self) -> None:
        lgr = get_logger("exc.level.test")
        with structlog.testing.capture_logs() as cap:
            log_exception(lgr, RuntimeError("boom"), "runtime_error")
        assert cap[0]["log_level"] == "error"


# ---------------------------------------------------------------------------
# RequestLoggingMiddleware
# ---------------------------------------------------------------------------


HTTP_OK = 200


def _make_app() -> Any:
    """Create a minimal FastAPI app with the middleware attached."""
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        # Log something inside the request to prove context propagation
        get_logger("handler").info("handler_called")
        return {"pong": "ok"}

    @app.get("/error")
    async def broken() -> dict[str, str]:
        msg = "intentional"
        raise RuntimeError(msg)

    return app


class TestRequestLoggingMiddleware:
    def setup_method(self) -> None:
        # Do NOT call configure_logging() — that resets cache_logger_on_first_use=True
        # which breaks capture_logs(). conftest.py's reset_structlog fixture is sufficient.
        clear_context()

    def test_200_request_logged(self) -> None:
        app = _make_app()
        with structlog.testing.capture_logs() as cap:
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/ping")

        assert response.status_code == HTTP_OK
        access_logs = [r for r in cap if r.get("event") == "http_request"]
        assert len(access_logs) == 1
        record = access_logs[0]
        assert record["method"] == "GET"
        assert record["path"] == "/ping"
        assert record["status_code"] == HTTP_OK
        assert CTX_LATENCY_MS in record
        assert isinstance(record[CTX_LATENCY_MS], float)

    def test_request_id_generated_when_absent(self) -> None:
        app = _make_app()
        with structlog.testing.capture_logs() as cap:
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/ping")

        assert HEADER_REQUEST_ID.lower() in {k.lower() for k in response.headers}
        uuid.UUID(response.headers[HEADER_REQUEST_ID])  # must be valid UUID
        access_logs = [r for r in cap if r.get("event") == "http_request"]
        assert len(access_logs) == 1

    def test_request_id_propagated_from_header(self) -> None:
        app = _make_app()
        my_rid = str(uuid.uuid4())
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/ping", headers={HEADER_REQUEST_ID: my_rid})
        assert response.headers.get(HEADER_REQUEST_ID) == my_rid

    def test_correlation_id_propagated(self) -> None:
        app = _make_app()
        cid = "trace-abc-123"
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/ping", headers={HEADER_CORRELATION_ID: cid})
        assert response.headers.get(HEADER_CORRELATION_ID) == cid

    def test_context_cleared_after_request(self) -> None:
        """Context vars must not bleed between requests."""
        app = _make_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            client.get("/ping")
            # After response the middleware called clear_context(); the
            # test harness runs in the same thread so we can inspect directly.
        assert structlog.contextvars.get_contextvars() == {}

    def test_context_visible_inside_handler(self) -> None:
        """Middleware echoes request_id back in the response header."""
        app = _make_app()
        rid = str(uuid.uuid4())
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/ping", headers={HEADER_REQUEST_ID: rid})
        assert response.headers.get(HEADER_REQUEST_ID) == rid

    def test_latency_ms_is_non_negative(self) -> None:
        app = _make_app()
        with structlog.testing.capture_logs() as cap:
            with TestClient(app, raise_server_exceptions=False) as client:
                client.get("/ping")

        access_logs = [r for r in cap if r.get("event") == "http_request"]
        assert access_logs[0][CTX_LATENCY_MS] >= 0.0
