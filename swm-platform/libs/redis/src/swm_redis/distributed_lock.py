"""Redis distributed lock service.

Features:
- SET NX EX lock acquisition
- Auto-renew heartbeat
- Async context manager
- Deadlock prevention with deterministic lock ordering
- Metrics and structured logging
"""

from __future__ import annotations

import asyncio
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from time import perf_counter
from typing import Any
from uuid import uuid4

from prometheus_client import Counter, Gauge, Histogram

from swm_common import get_logger
from swm_redis.client import RedisClient

logger = get_logger("swm_redis.distributed_lock")


_LOCK_ACQUIRE_TOTAL = Counter(
    "swm_redis_lock_acquire_total",
    "Total distributed lock acquire attempts",
    ["lock_type", "status"],
)
_LOCK_RELEASE_TOTAL = Counter(
    "swm_redis_lock_release_total",
    "Total distributed lock release attempts",
    ["lock_type", "status"],
)
_LOCK_RENEW_TOTAL = Counter(
    "swm_redis_lock_renew_total",
    "Total distributed lock renew attempts",
    ["lock_type", "status"],
)
_LOCK_ACQUIRE_LATENCY = Histogram(
    "swm_redis_lock_acquire_duration_seconds",
    "Distributed lock acquire latency in seconds",
    ["lock_type"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
)
_LOCK_WAIT_SECONDS = Histogram(
    "swm_redis_lock_wait_seconds",
    "Time spent waiting to acquire a distributed lock",
    ["lock_type", "status"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
)
_LOCK_HOLD_LATENCY = Histogram(
    "swm_redis_lock_hold_duration_seconds",
    "Distributed lock hold duration in seconds",
    ["lock_type"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)
_LOCK_ACTIVE = Gauge(
    "swm_redis_lock_active",
    "Currently active distributed locks",
    ["lock_type"],
)


class LockAcquireTimeoutError(TimeoutError):
    """Raised when a lock cannot be acquired within the timeout."""


@dataclass(slots=True)
class DistributedLockConfig:
    ttl_seconds: int = 30
    acquire_timeout_seconds: float = 5.0
    retry_interval_seconds: float = 0.05
    auto_renew: bool = True
    renew_interval_seconds: float | None = None


class RedisDistributedLock(AbstractAsyncContextManager["RedisDistributedLock"]):
    """Single distributed lock instance with owner token and auto-renew support."""

    _LUA_RELEASE = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""

    _LUA_RENEW = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('EXPIRE', KEYS[1], tonumber(ARGV[2]))
end
return 0
"""

    def __init__(
        self,
        redis_client: RedisClient,
        *,
        key: str,
        lock_type: str,
        config: DistributedLockConfig | None = None,
    ) -> None:
        self.redis = redis_client
        self.key = key
        self.lock_type = lock_type
        self.config = config or DistributedLockConfig()
        self.owner_token = uuid4().hex
        self._acquired = False
        self._renew_task: asyncio.Task[None] | None = None
        self._stopped = asyncio.Event()
        self._acquired_at = 0.0

    @property
    def acquired(self) -> bool:
        return self._acquired

    async def acquire(self) -> bool:
        started = perf_counter()
        deadline = perf_counter() + self.config.acquire_timeout_seconds

        while True:
            ok = await self.redis.set(
                self.key,
                self.owner_token,
                ttl=self.config.ttl_seconds,
                nx=True,
            )
            if ok:
                self._acquired = True
                self._acquired_at = perf_counter()
                _LOCK_ACQUIRE_TOTAL.labels(lock_type=self.lock_type, status="ok").inc()
                wait_seconds = perf_counter() - started
                _LOCK_ACQUIRE_LATENCY.labels(lock_type=self.lock_type).observe(wait_seconds)
                _LOCK_WAIT_SECONDS.labels(lock_type=self.lock_type, status="ok").observe(wait_seconds)
                _LOCK_ACTIVE.labels(lock_type=self.lock_type).inc()
                logger.debug("lock_acquired", lock_key=self.key, lock_type=self.lock_type)
                self._start_renew_task_if_needed()
                return True

            if perf_counter() >= deadline:
                _LOCK_ACQUIRE_TOTAL.labels(lock_type=self.lock_type, status="timeout").inc()
                wait_seconds = perf_counter() - started
                _LOCK_ACQUIRE_LATENCY.labels(lock_type=self.lock_type).observe(wait_seconds)
                _LOCK_WAIT_SECONDS.labels(lock_type=self.lock_type, status="timeout").observe(wait_seconds)
                raise LockAcquireTimeoutError(f"could not acquire lock {self.key}")

            await asyncio.sleep(self.config.retry_interval_seconds)

    async def release(self) -> bool:
        self._stopped.set()
        if self._renew_task is not None:
            self._renew_task.cancel()
            await asyncio.gather(self._renew_task, return_exceptions=True)
            self._renew_task = None

        if not self._acquired:
            return False

        result = await self.redis.run_operation(
            lambda: self.redis.client.eval(self._LUA_RELEASE, 1, self.key, self.owner_token),
            operation="lock_release",
        )
        released = int(result) == 1

        if released:
            _LOCK_RELEASE_TOTAL.labels(lock_type=self.lock_type, status="ok").inc()
            _LOCK_HOLD_LATENCY.labels(lock_type=self.lock_type).observe(perf_counter() - self._acquired_at)
            logger.debug("lock_released", lock_key=self.key, lock_type=self.lock_type)
        else:
            _LOCK_RELEASE_TOTAL.labels(lock_type=self.lock_type, status="lost").inc()
            logger.warning("lock_release_lost_ownership", lock_key=self.key, lock_type=self.lock_type)

        self._acquired = False
        _LOCK_ACTIVE.labels(lock_type=self.lock_type).dec()
        return released

    async def _renew_once(self) -> bool:
        if not self._acquired:
            return False

        result = await self.redis.run_operation(
            lambda: self.redis.client.eval(
                self._LUA_RENEW,
                1,
                self.key,
                self.owner_token,
                str(self.config.ttl_seconds),
            ),
            operation="lock_renew",
        )
        renewed = int(result) == 1
        if renewed:
            _LOCK_RENEW_TOTAL.labels(lock_type=self.lock_type, status="ok").inc()
        else:
            _LOCK_RENEW_TOTAL.labels(lock_type=self.lock_type, status="lost").inc()
        return renewed

    def _start_renew_task_if_needed(self) -> None:
        if not self.config.auto_renew:
            return

        interval = self.config.renew_interval_seconds
        if interval is None:
            interval = max(1.0, self.config.ttl_seconds / 3)

        async def _loop() -> None:
            while not self._stopped.is_set():
                await asyncio.sleep(interval)
                if self._stopped.is_set():
                    return
                try:
                    renewed = await self._renew_once()
                    if not renewed:
                        logger.warning("lock_renew_failed_lost_ownership", lock_key=self.key, lock_type=self.lock_type)
                        self._acquired = False
                        _LOCK_ACTIVE.labels(lock_type=self.lock_type).dec()
                        self._stopped.set()
                        return
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    _LOCK_RENEW_TOTAL.labels(lock_type=self.lock_type, status="error").inc()
                    logger.warning(
                        "lock_renew_error",
                        lock_key=self.key,
                        lock_type=self.lock_type,
                        error=str(exc),
                    )

        self._renew_task = asyncio.create_task(_loop(), name=f"lock-renew:{self.key}")

    async def __aenter__(self) -> RedisDistributedLock:
        await self.acquire()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.release()


class MultiRedisDistributedLock(AbstractAsyncContextManager["MultiRedisDistributedLock"]):
    """Acquire multiple locks with sorted ordering to avoid deadlocks."""

    def __init__(self, locks: list[RedisDistributedLock]) -> None:
        self._locks = locks

    async def __aenter__(self) -> MultiRedisDistributedLock:
        for lock in self._locks:
            await lock.acquire()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        for lock in reversed(self._locks):
            await lock.release()


class RedisDistributedLockService:
    """Factory and helpers for distributed lock use cases."""

    def __init__(self, redis_client: RedisClient, *, key_prefix: str = "lock") -> None:
        self.redis = redis_client
        self.key_prefix = key_prefix.strip(":")

    def lock(self, key: str, *, lock_type: str = "generic", config: DistributedLockConfig | None = None) -> RedisDistributedLock:
        return RedisDistributedLock(
            self.redis,
            key=self._k(key),
            lock_type=lock_type,
            config=config,
        )

    def vehicle_lock(self, vehicle_id: str, *, config: DistributedLockConfig | None = None) -> RedisDistributedLock:
        return self.lock(f"vehicle:{vehicle_id}", lock_type="vehicle", config=config)

    def report_lock(self, report_id: str, *, config: DistributedLockConfig | None = None) -> RedisDistributedLock:
        return self.lock(f"report:{report_id}", lock_type="report", config=config)

    def analytics_lock(self, analytics_id: str, *, config: DistributedLockConfig | None = None) -> RedisDistributedLock:
        return self.lock(f"analytics:{analytics_id}", lock_type="analytics", config=config)

    def acquire_many(
        self,
        keys: list[str],
        *,
        lock_type: str = "multi",
        config: DistributedLockConfig | None = None,
    ) -> MultiRedisDistributedLock:
        unique = sorted(set(keys))
        locks = [self.lock(key, lock_type=lock_type, config=config) for key in unique]
        return MultiRedisDistributedLock(locks)

    def _k(self, suffix: str) -> str:
        if self.key_prefix:
            return f"{self.key_prefix}:{suffix}"
        return suffix
