"""Redis sliding-window rate limiter with FastAPI middleware.

Scopes:
- global
- vendor
- ip
- imei
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import math
from typing import Any
from uuid import uuid4

from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from swm_common import get_logger

from swm_redis.client import RedisClient

logger = get_logger("swm_redis.rate_limiter")


_RATE_LIMIT_CHECK_TOTAL = Counter(
    "swm_rate_limiter_check_total",
    "Total number of rate limit checks",
    ["scope", "status"],
)
_RATE_LIMIT_CHECK_LATENCY = Histogram(
    "swm_rate_limiter_check_duration_seconds",
    "Rate limiter check latency in seconds",
    ["scope"],
    buckets=[0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1],
)


@dataclass(slots=True)
class RateLimitRule:
    limit: int
    window_seconds: int
    enabled: bool = True


@dataclass(slots=True)
class RedisRateLimiterConfig:
    key_prefix: str = "rl"
    global_rule: RateLimitRule = field(default_factory=lambda: RateLimitRule(limit=1000, window_seconds=60))
    vendor_rule: RateLimitRule = field(default_factory=lambda: RateLimitRule(limit=500, window_seconds=60))
    ip_rule: RateLimitRule = field(default_factory=lambda: RateLimitRule(limit=200, window_seconds=60))
    imei_rule: RateLimitRule = field(default_factory=lambda: RateLimitRule(limit=120, window_seconds=60))
    key_expiry_padding_seconds: int = 5


@dataclass(slots=True)
class RateLimitDecision:
    scope: str
    key: str
    limit: int
    current_count: int
    remaining: int
    reset_ms: int
    allowed: bool


class SlidingWindowRedisRateLimiter:
    """Atomic sliding-window limiter using Redis sorted sets + Lua."""

    _LUA_CHECK_AND_ADD = """
local key = KEYS[1]
local now_ms = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
local expire_seconds = tonumber(ARGV[5])

redis.call('ZREMRANGEBYSCORE', key, 0, now_ms - window_ms)
redis.call('ZADD', key, now_ms, member)

local count = redis.call('ZCARD', key)
redis.call('EXPIRE', key, expire_seconds)

local allowed = 0
if count <= limit then
  allowed = 1
end

local remaining = limit - count
if remaining < 0 then
  remaining = 0
end

local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
local reset_ms = 0
if #oldest >= 2 then
  local oldest_score = tonumber(oldest[2])
  reset_ms = oldest_score + window_ms - now_ms
  if reset_ms < 0 then
    reset_ms = 0
  end
end

return {allowed, count, remaining, reset_ms}
"""

    def __init__(self, redis_client: RedisClient, config: RedisRateLimiterConfig | None = None) -> None:
        self.redis = redis_client
        self.config = config or RedisRateLimiterConfig()

    async def check_request(
        self,
        *,
        vendor_id: str | None,
        ip_address: str | None,
        imei: str | None,
        now: datetime | None = None,
    ) -> tuple[bool, RateLimitDecision | None, list[RateLimitDecision]]:
        """Evaluate all scopes in order and short-circuit on first block."""
        ts = now or datetime.now(UTC)
        decisions: list[RateLimitDecision] = []

        scope_inputs = [
            ("global", "all", self.config.global_rule),
            ("vendor", vendor_id, self.config.vendor_rule),
            ("ip", ip_address, self.config.ip_rule),
            ("imei", imei, self.config.imei_rule),
        ]

        for scope, identifier, rule in scope_inputs:
            if not rule.enabled:
                continue
            if scope != "global" and not identifier:
                continue

            decision = await self._check_scope(scope=scope, identifier=identifier or "all", rule=rule, now=ts)
            decisions.append(decision)
            if not decision.allowed:
                return False, decision, decisions

        return True, None, decisions

    async def _check_scope(
        self,
        *,
        scope: str,
        identifier: str,
        rule: RateLimitRule,
        now: datetime,
    ) -> RateLimitDecision:
        key = self._scope_key(scope, identifier)
        now_ms = int(now.timestamp() * 1000)
        window_ms = rule.window_seconds * 1000
        member = f"{now_ms}-{uuid4().hex}"
        expiry = rule.window_seconds + self.config.key_expiry_padding_seconds

        started = datetime.now(UTC)
        raw = await self.redis.run_operation(
            lambda: self.redis.client.eval(
                self._LUA_CHECK_AND_ADD,
                1,
                key,
                str(now_ms),
                str(window_ms),
                str(rule.limit),
                member,
                str(expiry),
            ),
            operation="rate_limit_check",
        )
        elapsed = (datetime.now(UTC) - started).total_seconds()
        _RATE_LIMIT_CHECK_LATENCY.labels(scope=scope).observe(elapsed)

        allowed = int(raw[0]) == 1
        status = "allowed" if allowed else "blocked"
        _RATE_LIMIT_CHECK_TOTAL.labels(scope=scope, status=status).inc()

        return RateLimitDecision(
            scope=scope,
            key=key,
            limit=rule.limit,
            current_count=int(raw[1]),
            remaining=int(raw[2]),
            reset_ms=int(raw[3]),
            allowed=allowed,
        )

    def _scope_key(self, scope: str, identifier: str) -> str:
        return f"{self.config.key_prefix}:{scope}:{identifier}"


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware enforcing redis-based sliding window rate limits."""

    def __init__(
        self,
        app: Any,
        *,
        limiter: SlidingWindowRedisRateLimiter | None = None,
        redis_client: RedisClient | None = None,
        config: RedisRateLimiterConfig | None = None,
        vendor_header: str = "x-vendor-id",
        imei_header: str = "x-imei",
    ) -> None:
        super().__init__(app)
        if limiter is None:
            if redis_client is None:
                raise ValueError("Either limiter or redis_client must be provided")
            limiter = SlidingWindowRedisRateLimiter(redis_client, config=config)

        self.limiter = limiter
        self.vendor_header = vendor_header
        self.imei_header = imei_header

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        vendor_id = request.headers.get(self.vendor_header)
        imei = request.headers.get(self.imei_header)
        ip_address = self._client_ip(request)

        allowed, blocked, _decisions = await self.limiter.check_request(
            vendor_id=vendor_id,
            ip_address=ip_address,
            imei=imei,
        )

        if allowed:
            return await call_next(request)

        assert blocked is not None
        retry_after = max(1, math.ceil(blocked.reset_ms / 1000)) if blocked.reset_ms > 0 else 1
        logger.warning(
            "rate_limit_blocked",
            scope=blocked.scope,
            key=blocked.key,
            limit=blocked.limit,
            current_count=blocked.current_count,
            reset_ms=blocked.reset_ms,
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=429,
            content={
                "detail": "rate limit exceeded",
                "scope": blocked.scope,
                "limit": blocked.limit,
                "remaining": blocked.remaining,
                "retry_after_seconds": retry_after,
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Scope": blocked.scope,
                "X-RateLimit-Limit": str(blocked.limit),
                "X-RateLimit-Remaining": str(blocked.remaining),
            },
        )

    def _client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",", maxsplit=1)[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "unknown"
