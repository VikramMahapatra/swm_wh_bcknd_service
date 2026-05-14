from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from swm_redis.rate_limiter import (
    RateLimitDecision,
    RateLimitRule,
    RedisRateLimitMiddleware,
    RedisRateLimiterConfig,
    SlidingWindowRedisRateLimiter,
)


@pytest.mark.asyncio
async def test_sliding_window_check_scope_allowed() -> None:
    mock_redis = MagicMock()
    mock_redis.run_operation = AsyncMock(return_value=[1, 5, 95, 800])
    mock_redis.client = MagicMock()

    limiter = SlidingWindowRedisRateLimiter(
        mock_redis,
        RedisRateLimiterConfig(
            key_prefix="rl",
            global_rule=RateLimitRule(limit=100, window_seconds=60),
            vendor_rule=RateLimitRule(limit=100, window_seconds=60),
            ip_rule=RateLimitRule(limit=100, window_seconds=60),
            imei_rule=RateLimitRule(limit=100, window_seconds=60),
        ),
    )

    decision = await limiter._check_scope(
        scope="vendor",
        identifier="v1",
        rule=RateLimitRule(limit=100, window_seconds=60),
        now=datetime(2026, 5, 4, tzinfo=UTC),
    )

    assert decision.allowed is True
    assert decision.scope == "vendor"
    assert decision.current_count == 5
    assert decision.remaining == 95


@pytest.mark.asyncio
async def test_check_request_short_circuits_on_block() -> None:
    mock_redis = MagicMock()
    # global allow, vendor block
    mock_redis.run_operation = AsyncMock(side_effect=[[1, 1, 9, 1000], [0, 11, 0, 2500]])
    mock_redis.client = MagicMock()

    limiter = SlidingWindowRedisRateLimiter(
        mock_redis,
        RedisRateLimiterConfig(
            global_rule=RateLimitRule(limit=10, window_seconds=60),
            vendor_rule=RateLimitRule(limit=10, window_seconds=60),
            ip_rule=RateLimitRule(limit=10, window_seconds=60),
            imei_rule=RateLimitRule(limit=10, window_seconds=60),
        ),
    )

    allowed, blocked, decisions = await limiter.check_request(
        vendor_id="vendor-a",
        ip_address="1.2.3.4",
        imei="111",
    )

    assert allowed is False
    assert blocked is not None
    assert blocked.scope == "vendor"
    assert len(decisions) == 2


def test_rate_limit_middleware_blocks() -> None:
    app = FastAPI()

    class _StubLimiter:
        async def check_request(self, *, vendor_id, ip_address, imei, now=None):
            blocked = RateLimitDecision(
                scope="ip",
                key="rl:ip:1.2.3.4",
                limit=5,
                current_count=10,
                remaining=0,
                reset_ms=1200,
                allowed=False,
            )
            return False, blocked, [blocked]

    app.add_middleware(RedisRateLimitMiddleware, limiter=_StubLimiter())

    @app.get("/ok")
    async def ok() -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/ok")

    assert response.status_code == 429
    assert response.json()["scope"] == "ip"
    assert response.headers["X-RateLimit-Scope"] == "ip"


def test_rate_limit_middleware_allows() -> None:
    app = FastAPI()

    class _StubLimiter:
        async def check_request(self, *, vendor_id, ip_address, imei, now=None):
            return True, None, []

    app.add_middleware(RedisRateLimitMiddleware, limiter=_StubLimiter())

    @app.get("/ok")
    async def ok() -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/ok", headers={"x-forwarded-for": "8.8.8.8", "x-vendor-id": "v1", "x-imei": "imei-1"})

    assert response.status_code == 200
    assert response.json() == {"ok": True}
