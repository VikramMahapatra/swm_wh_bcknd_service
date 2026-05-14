"""
swm_redis.client
================
Production-grade async Redis client for the SWM Fleet Platform.

Features
--------
- Connection pooling (max_connections configurable)
- Singleton connection manager - one pool per URL
- Health check (PING)
- Automatic retries with exponential back-off on transient errors
- Per-call asyncio timeout
- JSON serialiser/deserialiser (orjson)
- Pipeline helper (context-manager, auto-execute on clean exit)
- PubSub helper (subscribe / publish)
- Streams helper (XADD / XREAD / XREADGROUP / XACK / XGROUP_CREATE / XLEN)
- Geo helper (GEOADD / GEOPOS / GEODIST / GEOSEARCH)
- Distributed lock helper (context-manager)
- Prometheus metrics hooks (op counter + latency histogram)
"""
from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, ClassVar

import orjson
from prometheus_client import Counter, Histogram
from redis.asyncio import ConnectionPool, Redis
from redis.asyncio.lock import Lock
from redis.exceptions import BusyLoadingError
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import LockError, RedisError
from redis.exceptions import TimeoutError as RedisTimeoutError
from swm_common.logger import get_logger

_log = get_logger("swm.redis")

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
_REDIS_OPS = Counter(
    "swm_redis_operations_total",
    "Count of Redis operations",
    ["operation", "status"],
)
_REDIS_LATENCY = Histogram(
    "swm_redis_operation_duration_seconds",
    "Redis operation latency in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------
_RETRYABLE: tuple[type[Exception], ...] = (
    RedisConnectionError,
    RedisTimeoutError,
    BusyLoadingError,
    ConnectionError,
)


async def _with_retry(
    fn: Any,
    *,
    operation: str,
    attempts: int = 3,
    base_delay: float = 0.05,
    timeout: float | None = None,  # noqa: ASYNC109
) -> Any:
    for attempt in range(1, attempts + 1):
        t0 = time.perf_counter()
        try:
            coro = fn()
            result = await (asyncio.wait_for(coro, timeout=timeout) if timeout else coro)
            _REDIS_OPS.labels(operation=operation, status="ok").inc()
            _REDIS_LATENCY.labels(operation=operation).observe(time.perf_counter() - t0)
            return result
        except _RETRYABLE as exc:
            _REDIS_OPS.labels(operation=operation, status="retry").inc()
            last_exc = exc
            if attempt < attempts:
                await asyncio.sleep(base_delay * (2 ** (attempt - 1)))
        except BaseException as exc:
            _REDIS_OPS.labels(operation=operation, status="error").inc()
            _REDIS_LATENCY.labels(operation=operation).observe(time.perf_counter() - t0)
            raise exc
    _REDIS_OPS.labels(operation=operation, status="error").inc()
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Singleton connection manager
# ---------------------------------------------------------------------------
class RedisConnectionManager:
    """Manages a single ``ConnectionPool`` per URL.

    Call ``RedisConnectionManager.get(url)`` to obtain (or reuse) the shared
    instance.  Call ``close_all()`` during application shutdown.
    """

    _registry: ClassVar[dict[str, RedisConnectionManager]] = {}

    @classmethod
    def get(
        cls,
        url: str,
        *,
        max_connections: int = 20,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 3.0,
    ) -> RedisConnectionManager:
        """Return the existing manager for *url* or create a new one."""
        if url not in cls._registry:
            cls._registry[url] = cls(
                url,
                max_connections=max_connections,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_connect_timeout,
            )
        return cls._registry[url]

    @classmethod
    async def close_all(cls) -> None:
        """Disconnect all pools and clear the registry."""
        for mgr in list(cls._registry.values()):
            await mgr.close()
        cls._registry.clear()

    def __init__(
        self,
        url: str,
        *,
        max_connections: int = 20,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 3.0,
    ) -> None:
        self._pool = ConnectionPool.from_url(
            url,
            max_connections=max_connections,
            decode_responses=True,
            encoding="utf-8",
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
        )
        _log.info("redis_pool_created", url=url, max_connections=max_connections)

    def redis(self) -> Redis:
        """Return a Redis client backed by the shared pool."""
        return Redis(connection_pool=self._pool)

    async def close(self) -> None:
        await self._pool.disconnect()
        _log.info("redis_pool_closed")


# ---------------------------------------------------------------------------
# Sentinel for "use the client default"
# ---------------------------------------------------------------------------
_USE_DEFAULT: Any = object()


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------
class RedisClient:
    """Async Redis client with typed helpers for the SWM Fleet Platform.

    Usage::

        client = RedisClient.from_url("redis://localhost:6379/0")
        await client.ping()
        await client.set_json("vehicle:1", {"lat": 12.97, "lng": 77.59}, ttl=60)
        data = await client.get_json("vehicle:1")
    """

    def __init__(
        self,
        manager: RedisConnectionManager,
        *,
        default_timeout: float | None = 5.0,
        retry_attempts: int = 3,
        retry_base_delay: float = 0.05,
    ) -> None:
        self._mgr = manager
        self._r: Redis = manager.redis()
        self._default_timeout = default_timeout
        self._retry_attempts = retry_attempts
        self._retry_base_delay = retry_base_delay

    @classmethod
    def from_url(  # noqa: PLR0913
        cls,
        url: str,
        *,
        max_connections: int = 10,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 3.0,
        default_timeout: float | None = 5.0,
        retry_attempts: int = 3,
        retry_base_delay: float = 0.05,
    ) -> RedisClient:
        """Factory that creates (or reuses) the singleton pool for *url*."""
        mgr = RedisConnectionManager.get(
            url,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
        )
        return cls(
            mgr,
            default_timeout=default_timeout,
            retry_attempts=retry_attempts,
            retry_base_delay=retry_base_delay,
        )

    def _run(self, fn: Any, operation: str, *, timeout: Any = _USE_DEFAULT) -> Any:
        """Schedule fn with retry + timeout + metrics."""
        t = self._default_timeout if timeout is _USE_DEFAULT else timeout
        return _with_retry(
            fn,
            operation=operation,
            attempts=self._retry_attempts,
            base_delay=self._retry_base_delay,
            timeout=t,
        )

    @property
    def client(self) -> Redis:
        """Expose the underlying async Redis client for advanced operations."""
        return self._r

    async def run_operation(
        self,
        fn: Any,
        operation: str,
        *,
        timeout: Any = _USE_DEFAULT,
    ) -> Any:
        """Public wrapper around the internal retry/timeout execution path."""
        return await self._run(fn, operation, timeout=timeout)

    # --- health -------------------------------------------------------------------

    async def ping(self) -> bool:
        """Return True if Redis responds to PING."""
        try:
            return bool(await self._run(self._r.ping, "ping"))
        except RedisError:
            return False

    # --- key / value --------------------------------------------------------------

    async def set(
        self,
        key: str,
        value: str,
        *,
        ttl: int | None = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        result = await self._run(
            lambda: self._r.set(key, value, ex=ttl, nx=nx, xx=xx),
            "set",
        )
        return bool(result)

    async def get(self, key: str) -> str | None:
        return await self._run(lambda: self._r.get(key), "get")  # type: ignore[no-any-return]

    async def delete(self, *keys: str) -> int:
        return await self._run(lambda: self._r.delete(*keys), "delete")  # type: ignore[no-any-return]

    async def exists(self, *keys: str) -> int:
        return await self._run(lambda: self._r.exists(*keys), "exists")  # type: ignore[no-any-return]

    async def expire(self, key: str, seconds: int) -> bool:
        return bool(await self._run(lambda: self._r.expire(key, seconds), "expire"))

    async def ttl(self, key: str) -> int:
        return await self._run(lambda: self._r.ttl(key), "ttl")  # type: ignore[no-any-return]

    async def incr(self, key: str, amount: int = 1) -> int:
        return await self._run(lambda: self._r.incr(key, amount), "incr")  # type: ignore[no-any-return]

    # --- JSON ---------------------------------------------------------------------

    async def set_json(
        self,
        key: str,
        value: Any,
        *,
        ttl: int | None = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        serialised = orjson.dumps(value).decode()
        return await self.set(key, serialised, ttl=ttl, nx=nx, xx=xx)

    async def get_json(self, key: str) -> Any:
        raw = await self.get(key)
        if raw is None:
            return None
        return orjson.loads(raw)

    # --- hash ---------------------------------------------------------------------

    async def hset(self, key: str, mapping: dict[str, str]) -> int:
        return await self._run(lambda: self._r.hset(key, mapping=mapping), "hset")  # type: ignore[no-any-return]

    async def hget(self, key: str, field: str) -> str | None:
        return await self._run(lambda: self._r.hget(key, field), "hget")  # type: ignore[no-any-return]

    async def hgetall(self, key: str) -> dict[str, str]:
        return await self._run(lambda: self._r.hgetall(key), "hgetall")  # type: ignore[no-any-return]

    async def hdel(self, key: str, *fields: str) -> int:
        return await self._run(lambda: self._r.hdel(key, *fields), "hdel")  # type: ignore[no-any-return]

    # --- sets ---------------------------------------------------------------------

    async def sadd(self, key: str, *members: str) -> int:
        """Add one or more members to a Redis set."""
        return await self._run(lambda: self._r.sadd(key, *members), "sadd")  # type: ignore[no-any-return]

    async def srem(self, key: str, *members: str) -> int:
        """Remove one or more members from a Redis set."""
        return await self._run(lambda: self._r.srem(key, *members), "srem")  # type: ignore[no-any-return]

    async def smembers(self, key: str) -> set[str]:
        """Return all members in a Redis set."""
        return await self._run(lambda: self._r.smembers(key), "smembers")  # type: ignore[no-any-return]

    async def sismember(self, key: str, member: str) -> bool:
        """Check whether *member* exists in a Redis set."""
        return bool(await self._run(lambda: self._r.sismember(key, member), "sismember"))

    async def scard(self, key: str) -> int:
        """Return cardinality of a Redis set."""
        return await self._run(lambda: self._r.scard(key), "scard")  # type: ignore[no-any-return]

    # --- lists --------------------------------------------------------------------

    async def lpush(self, key: str, *values: str) -> int:
        """Push one or more values to the left side of a list."""
        return await self._run(lambda: self._r.lpush(key, *values), "lpush")  # type: ignore[no-any-return]

    async def brpop(self, keys: list[str], *, timeout: int = 0) -> tuple[str, str] | None:
        """Blocking right-pop across one or more list keys."""
        return await self._run(  # type: ignore[no-any-return]
            lambda: self._r.brpop(keys, timeout=timeout),
            "brpop",
            timeout=None if timeout > 0 else _USE_DEFAULT,
        )

    async def llen(self, key: str) -> int:
        """Return the length of a list."""
        return await self._run(lambda: self._r.llen(key), "llen")  # type: ignore[no-any-return]

    # --- pipeline -----------------------------------------------------------------

    @asynccontextmanager
    async def pipeline(self, transaction: bool = True) -> AsyncIterator[Any]:
        """Context manager yielding a pipeline.  Commands are auto-executed on clean exit."""
        pipe = self._r.pipeline(transaction=transaction)
        try:
            yield pipe
            await pipe.execute()
        finally:
            await pipe.reset()

    # --- pub/sub ------------------------------------------------------------------

    async def publish(self, channel: str, message: str) -> int:
        return await self._run(lambda: self._r.publish(channel, message), "publish")  # type: ignore[no-any-return]

    @asynccontextmanager
    async def subscribe(self, *channels: str) -> AsyncIterator[Any]:
        """Context manager that subscribes to *channels* and yields the PubSub object."""
        ps = self._r.pubsub()
        await ps.subscribe(*channels)
        try:
            yield ps
        finally:
            await ps.unsubscribe(*channels)
            with contextlib.suppress(Exception):
                await ps.aclose()

    # --- streams ------------------------------------------------------------------

    async def xadd(
        self,
        stream: str,
        fields: dict[str, str],
        *,
        entry_id: str = "*",
        maxlen: int | None = None,
        approximate: bool = True,
        timeout: float | None | object = _USE_DEFAULT,
    ) -> str:
        """Append an entry to *stream* and return its ID."""
        return await self._run(  # type: ignore[no-any-return]
            lambda: self._r.xadd(
                stream, fields, id=entry_id, maxlen=maxlen, approximate=approximate
            ),
            "xadd",
            timeout=timeout,
        )

    async def xread(
        self,
        streams: dict[str, str],
        *,
        count: int | None = None,
        block: int | None = None,
    ) -> list[Any]:
        """Read entries from one or more streams (non-consumer-group)."""
        # When block is set, let Redis own the timeout; skip asyncio wait_for.
        t = None if block is not None else self._default_timeout
        return (
            await self._run(
                lambda: self._r.xread(streams=streams, count=count, block=block),
                "xread",
                timeout=t,
            )
            or []
        )

    async def xrange(
        self,
        stream: str,
        min_id: str = "-",
        max_id: str = "+",
        *,
        count: int | None = None,
    ) -> list[Any]:
        """Read entries from a stream within an ID range."""
        return (
            await self._run(
                lambda: self._r.xrange(stream, min=min_id, max=max_id, count=count),
                "xrange",
            )
            or []
        )

    async def xgroup_create(
        self,
        stream: str,
        group: str,
        *,
        start_id: str = "$",
        mkstream: bool = True,
    ) -> None:
        """Create a consumer group.  Silently ignores BUSYGROUP if already exists."""
        with contextlib.suppress(Exception):
            await self._run(
                lambda: self._r.xgroup_create(stream, group, id=start_id, mkstream=mkstream),
                "xgroup_create",
            )

    async def xreadgroup(  # noqa: PLR0913
        self,
        group: str,
        consumer: str,
        streams: dict[str, str],
        *,
        count: int | None = None,
        block: int | None = None,
        no_ack: bool = False,
    ) -> list[Any]:
        """Read entries from streams via a consumer group."""
        t = None if block is not None else self._default_timeout
        return (
            await self._run(
                lambda: self._r.xreadgroup(
                    group, consumer, streams=streams, count=count, block=block, noack=no_ack
                ),
                "xreadgroup",
                timeout=t,
            )
            or []
        )

    async def xack(self, stream: str, group: str, *entry_ids: str) -> int:
        """Acknowledge entries in *group*."""
        return await self._run(lambda: self._r.xack(stream, group, *entry_ids), "xack")  # type: ignore[no-any-return]

    async def xpending(self, stream: str, group: str) -> Any:
        """Return XPENDING summary for a stream/group."""
        return await self._run(lambda: self._r.xpending(stream, group), "xpending")

    async def xpending_range(
        self,
        stream: str,
        group: str,
        min_id: str,
        max_id: str,
        count: int,
        consumer: str | None = None,
    ) -> Any:
        """Return XPENDING range details (optionally for one consumer)."""
        return await self._run(
            lambda: self._r.xpending_range(
                stream,
                group,
                min=min_id,
                max=max_id,
                count=count,
                consumername=consumer,
            ),
            "xpending_range",
        )

    async def xautoclaim(
        self,
        stream: str,
        group: str,
        consumer: str,
        min_idle_time: int,
        start_id: str,
        *,
        count: int | None = None,
    ) -> Any:
        """Claim pending entries that have been idle beyond *min_idle_time*."""
        return await self._run(
            lambda: self._r.xautoclaim(
                stream,
                group,
                consumer,
                min_idle_time,
                start_id,
                count=count,
            ),
            "xautoclaim",
        )

    async def xlen(self, stream: str) -> int:
        """Return the number of entries in *stream*."""
        return await self._run(lambda: self._r.xlen(stream), "xlen")  # type: ignore[no-any-return]

    # --- geo ----------------------------------------------------------------------

    async def geoadd(self, key: str, members: list[tuple[float, float, str]]) -> int:
        """Add geo members.  Each tuple is ``(longitude, latitude, name)``."""
        flat: list[Any] = []
        for lon, lat, name in members:
            flat += [lon, lat, name]
        return await self._run(lambda: self._r.geoadd(key, flat), "geoadd")  # type: ignore[no-any-return]

    async def geopos(self, key: str, *members: str) -> list[tuple[float, float] | None]:
        """Return ``(lon, lat)`` for each member, or None if not found."""
        return await self._run(lambda: self._r.geopos(key, *members), "geopos")  # type: ignore[no-any-return]

    async def geodist(
        self,
        key: str,
        member1: str,
        member2: str,
        unit: str = "km",
    ) -> float | None:
        """Return distance between two members."""
        return await self._run(
            lambda: self._r.geodist(key, member1, member2, unit=unit),
            "geodist",
        )  # type: ignore[no-any-return]

    async def geosearch(  # noqa: PLR0913
        self,
        key: str,
        longitude: float,
        latitude: float,
        radius: float,
        unit: str = "km",
        count: int | None = None,
        sort: str = "ASC",
    ) -> list[str]:
        """Return members within *radius* of (longitude, latitude)."""
        return (
            await self._run(
                lambda: self._r.geosearch(
                    key,
                    longitude=longitude,
                    latitude=latitude,
                    radius=radius,
                    unit=unit,
                    count=count,
                    sort=sort,
                ),
                "geosearch",
            )
            or []
        )

    # --- lock ---------------------------------------------------------------------

    @asynccontextmanager
    async def lock(
        self,
        name: str,
        *,
        timeout: float = 10.0,  # noqa: ASYNC109
        blocking_timeout: float = 5.0,
        blocking: bool = True,
    ) -> AsyncIterator[Lock]:
        """Distributed lock context-manager.

        Raises ``redis.exceptions.LockError`` if the lock cannot be acquired.
        """
        lk: Lock = self._r.lock(name, timeout=timeout, blocking_timeout=blocking_timeout)
        acquired = await lk.acquire(blocking=blocking)
        if not acquired:
            raise LockError(f"Could not acquire lock '{name}'")
        try:
            yield lk
        finally:
            with contextlib.suppress(Exception):
                await lk.release()

    # --- lifecycle ----------------------------------------------------------------

    async def close(self) -> None:
        """Disconnect the underlying connection pool."""
        await self._mgr.close()
