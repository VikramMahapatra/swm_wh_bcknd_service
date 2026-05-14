"""
Unit-tests for swm_redis.client.

All tests use AsyncMock / MagicMock - no live Redis required.

Run:
    uv run pytest tests/test_redis_client.py -v
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import orjson
import pytest
from redis.exceptions import ConnectionError as RedisConnError
from redis.exceptions import LockError, RedisError, ResponseError
from swm_redis.client import (
    _REDIS_OPS,
    RedisClient,
    RedisConnectionManager,
    _with_retry,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(mock_redis: Any) -> RedisClient:
    """Build a RedisClient wired to *mock_redis* (a MagicMock/AsyncMock Redis)."""
    mgr = MagicMock(spec=RedisConnectionManager)
    mgr.redis.return_value = mock_redis
    return RedisClient(mgr, default_timeout=None, retry_attempts=3, retry_base_delay=0.0)


def _redis_mock(**method_returns: Any) -> Any:
    """Return a MagicMock whose listed methods are AsyncMocks with given return values."""
    r = MagicMock()
    for method, rv in method_returns.items():
        am = AsyncMock(return_value=rv)
        setattr(r, method, am)
    return r


# ---------------------------------------------------------------------------
# _with_retry
# ---------------------------------------------------------------------------

class TestWithRetry:
    @pytest.mark.asyncio
    async def test_succeeds_first_attempt(self) -> None:
        calls = 0

        async def _fn() -> str:
            nonlocal calls
            calls += 1
            return "ok"

        result = await _with_retry(_fn, operation="test", attempts=3, base_delay=0.0)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_retries_on_connection_error(self) -> None:
        calls = 0

        async def _fn() -> str:
            nonlocal calls
            calls += 1
            if calls < 2:
                raise RedisConnError("down")
            return "recovered"

        result = await _with_retry(_fn, operation="test", attempts=3, base_delay=0.0)
        assert result == "recovered"

    @pytest.mark.asyncio
    async def test_raises_after_all_attempts_exhausted(self) -> None:
        async def _fn() -> None:
            raise RedisConnError("always fails")

        with pytest.raises(RedisConnError):
            await _with_retry(lambda: _fn(), operation="test", attempts=3, base_delay=0.0)

    @pytest.mark.asyncio
    async def test_non_retryable_error_raised_immediately(self) -> None:
        calls = 0

        async def _fn() -> None:
            nonlocal calls
            calls += 1
            raise ValueError("bad value")

        with pytest.raises(ValueError):
            await _with_retry(lambda: _fn(), operation="test", attempts=3, base_delay=0.0)

        assert calls == 1  # no retry for non-retryable

    @pytest.mark.asyncio
    async def test_timeout_raises_asyncio_timeout(self) -> None:
        async def _slow() -> None:
            await asyncio.sleep(10)

        with pytest.raises(TimeoutError):
            await _with_retry(_slow, operation="test", attempts=1, base_delay=0.0, timeout=0.01)


# ---------------------------------------------------------------------------
# RedisConnectionManager
# ---------------------------------------------------------------------------

class TestRedisConnectionManager:
    def setup_method(self) -> None:
        RedisConnectionManager._registry.clear()

    def test_get_returns_same_instance_for_same_url(self) -> None:
        url = "redis://localhost:6379/1"
        m1 = RedisConnectionManager.get(url)
        m2 = RedisConnectionManager.get(url)
        assert m1 is m2

    def test_get_returns_different_instances_for_different_urls(self) -> None:
        m1 = RedisConnectionManager.get("redis://localhost:6379/1")
        m2 = RedisConnectionManager.get("redis://localhost:6379/2")
        assert m1 is not m2

    @pytest.mark.asyncio
    async def test_close_all_drains_registry(self) -> None:
        RedisConnectionManager.get("redis://localhost:6379/3")
        with patch.object(RedisConnectionManager, "close", new_callable=AsyncMock) as mock_close:
            await RedisConnectionManager.close_all()
        assert RedisConnectionManager._registry == {}
        mock_close.assert_called_once()


# ---------------------------------------------------------------------------
# ping / health
# ---------------------------------------------------------------------------

class TestPing:
    @pytest.mark.asyncio
    async def test_ping_returns_true_on_success(self) -> None:
        client = _make_client(_redis_mock(ping=True))
        assert await client.ping() is True

    @pytest.mark.asyncio
    async def test_ping_returns_false_on_redis_error(self) -> None:
        r = MagicMock()
        r.ping = AsyncMock(side_effect=RedisError("unreachable"))
        client = _make_client(r)
        assert await client.ping() is False


# ---------------------------------------------------------------------------
# Key / Value
# ---------------------------------------------------------------------------

class TestSetGet:
    @pytest.mark.asyncio
    async def test_set_returns_true_on_ok(self) -> None:
        client = _make_client(_redis_mock(set=True))
        assert await client.set("k", "v") is True

    @pytest.mark.asyncio
    async def test_set_returns_false_when_condition_not_met(self) -> None:
        client = _make_client(_redis_mock(set=None))
        assert await client.set("k", "v", nx=True) is False

    @pytest.mark.asyncio
    async def test_get_returns_value(self) -> None:
        client = _make_client(_redis_mock(get="hello"))
        assert await client.get("k") == "hello"

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing_key(self) -> None:
        client = _make_client(_redis_mock(get=None))
        assert await client.get("missing") is None

    @pytest.mark.asyncio
    async def test_delete_returns_count(self) -> None:
        client = _make_client(_redis_mock(delete=2))
        assert await client.delete("a", "b") == 2

    @pytest.mark.asyncio
    async def test_exists_returns_count(self) -> None:
        client = _make_client(_redis_mock(exists=1))
        assert await client.exists("k") == 1

    @pytest.mark.asyncio
    async def test_expire_returns_bool(self) -> None:
        client = _make_client(_redis_mock(expire=True))
        assert await client.expire("k", 60) is True

    @pytest.mark.asyncio
    async def test_ttl_returns_seconds(self) -> None:
        client = _make_client(_redis_mock(ttl=30))
        assert await client.ttl("k") == 30

    @pytest.mark.asyncio
    async def test_incr_returns_new_value(self) -> None:
        client = _make_client(_redis_mock(incr=5))
        assert await client.incr("counter", 1) == 5


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

class TestJson:
    @pytest.mark.asyncio
    async def test_set_json_serialises_and_stores(self) -> None:
        r = _redis_mock(set=True)
        client = _make_client(r)
        assert await client.set_json("vehicle:1", {"lat": 12.9, "lng": 77.5}) is True
        stored = r.set.call_args[0][1]
        assert orjson.loads(stored) == {"lat": 12.9, "lng": 77.5}

    @pytest.mark.asyncio
    async def test_get_json_deserialises(self) -> None:
        payload = orjson.dumps({"speed": 55}).decode()
        client = _make_client(_redis_mock(get=payload))
        result = await client.get_json("trip:1")
        assert result == {"speed": 55}

    @pytest.mark.asyncio
    async def test_get_json_returns_none_for_missing(self) -> None:
        client = _make_client(_redis_mock(get=None))
        assert await client.get_json("nope") is None


# ---------------------------------------------------------------------------
# Hash helpers
# ---------------------------------------------------------------------------

class TestHash:
    @pytest.mark.asyncio
    async def test_hset_and_hget(self) -> None:
        r = _redis_mock(hset=2, hget="Bangalore")
        client = _make_client(r)
        assert await client.hset("loc:1", {"city": "Bangalore", "country": "IN"}) == 2
        assert await client.hget("loc:1", "city") == "Bangalore"

    @pytest.mark.asyncio
    async def test_hgetall_returns_mapping(self) -> None:
        data = {"city": "Delhi", "country": "IN"}
        client = _make_client(_redis_mock(hgetall=data))
        assert await client.hgetall("loc:2") == data

    @pytest.mark.asyncio
    async def test_hdel_returns_count(self) -> None:
        client = _make_client(_redis_mock(hdel=1))
        assert await client.hdel("loc:2", "city") == 1


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class TestPipeline:
    @pytest.mark.asyncio
    async def test_pipeline_executes_on_clean_exit(self) -> None:
        pipe = MagicMock()
        pipe.reset = AsyncMock()
        pipe.execute = AsyncMock(return_value=["OK", 1])

        r = MagicMock()
        r.pipeline.return_value = pipe
        client = _make_client(r)

        async with client.pipeline() as p:
            p.set("k", "v")

        pipe.execute.assert_awaited_once()
        pipe.reset.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_pipeline_resets_on_exception(self) -> None:
        pipe = MagicMock()
        pipe.reset = AsyncMock()
        pipe.execute = AsyncMock()

        r = MagicMock()
        r.pipeline.return_value = pipe
        client = _make_client(r)

        with pytest.raises(RuntimeError):
            async with client.pipeline():
                raise RuntimeError("oops")

        pipe.execute.assert_not_awaited()
        pipe.reset.assert_awaited_once()


# ---------------------------------------------------------------------------
# Pub/Sub
# ---------------------------------------------------------------------------

class TestPubSub:
    @pytest.mark.asyncio
    async def test_publish_returns_subscriber_count(self) -> None:
        client = _make_client(_redis_mock(publish=3))
        assert await client.publish("telemetry", "data") == 3

    @pytest.mark.asyncio
    async def test_subscribe_context_manager_yields_pubsub(self) -> None:
        ps = AsyncMock()
        ps.subscribe = AsyncMock()
        ps.unsubscribe = AsyncMock()
        ps.aclose = AsyncMock()

        r = MagicMock()
        r.pubsub.return_value = ps
        client = _make_client(r)

        async with client.subscribe("fleet:events") as pub:
            assert pub is ps

        ps.unsubscribe.assert_awaited_once()
        ps.aclose.assert_awaited_once()


# ---------------------------------------------------------------------------
# Streams
# ---------------------------------------------------------------------------

class TestStreams:
    @pytest.mark.asyncio
    async def test_xadd_returns_entry_id(self) -> None:
        client = _make_client(_redis_mock(xadd="1715000000000-0"))
        eid = await client.xadd("gps", {"lat": "12.9", "lng": "77.5"})
        assert eid == "1715000000000-0"

    @pytest.mark.asyncio
    async def test_xread_returns_list(self) -> None:
        data = [("gps", [("id-1", {"lat": "12.9"})])]
        client = _make_client(_redis_mock(xread=data))
        result = await client.xread({"gps": "0"})
        assert result == data

    @pytest.mark.asyncio
    async def test_xread_returns_empty_list_on_none(self) -> None:
        client = _make_client(_redis_mock(xread=None))
        assert await client.xread({"gps": "$"}) == []

    @pytest.mark.asyncio
    async def test_xreadgroup_returns_list(self) -> None:
        data = [("gps", [("id-2", {"lat": "13.0"})])]
        client = _make_client(_redis_mock(xreadgroup=data))
        result = await client.xreadgroup("grp1", "consumer1", {"gps": ">"})
        assert result == data

    @pytest.mark.asyncio
    async def test_xack_returns_count(self) -> None:
        client = _make_client(_redis_mock(xack=1))
        assert await client.xack("gps", "grp1", "id-1") == 1

    @pytest.mark.asyncio
    async def test_xlen_returns_int(self) -> None:
        client = _make_client(_redis_mock(xlen=42))
        assert await client.xlen("gps") == 42

    @pytest.mark.asyncio
    async def test_xgroup_create_suppresses_busygroup(self) -> None:
        """xgroup_create should not raise even when the group already exists."""
        r = MagicMock()
        r.xgroup_create = AsyncMock(side_effect=ResponseError("BUSYGROUP"))
        client = _make_client(r)
        await client.xgroup_create("gps", "grp1")  # should not raise


# ---------------------------------------------------------------------------
# Geo
# ---------------------------------------------------------------------------

class TestGeo:
    @pytest.mark.asyncio
    async def test_geoadd_returns_count(self) -> None:
        r = _redis_mock(geoadd=1)
        client = _make_client(r)
        n = await client.geoadd("fleet", [(77.5946, 12.9716, "vehicle:1")])
        assert n == 1
        args = r.geoadd.call_args[0]
        # flat list: [lon, lat, name]
        assert args[1] == [77.5946, 12.9716, "vehicle:1"]

    @pytest.mark.asyncio
    async def test_geopos_returns_positions(self) -> None:
        positions = [(77.5946, 12.9716)]
        client = _make_client(_redis_mock(geopos=positions))
        result = await client.geopos("fleet", "vehicle:1")
        assert result == positions

    @pytest.mark.asyncio
    async def test_geodist_returns_distance(self) -> None:
        client = _make_client(_redis_mock(geodist=5.23))
        dist = await client.geodist("fleet", "vehicle:1", "vehicle:2", unit="km")
        assert dist == pytest.approx(5.23)

    @pytest.mark.asyncio
    async def test_geosearch_returns_member_names(self) -> None:
        names = ["vehicle:1", "vehicle:3"]
        client = _make_client(_redis_mock(geosearch=names))
        result = await client.geosearch(
            "fleet", longitude=77.59, latitude=12.97, radius=10.0
        )
        assert result == names

    @pytest.mark.asyncio
    async def test_geosearch_returns_empty_list_on_none(self) -> None:
        client = _make_client(_redis_mock(geosearch=None))
        result = await client.geosearch("fleet", longitude=0.0, latitude=0.0, radius=1.0)
        assert result == []


# ---------------------------------------------------------------------------
# Lock
# ---------------------------------------------------------------------------

class TestLock:
    @pytest.mark.asyncio
    async def test_lock_acquired_and_released(self) -> None:
        lk = AsyncMock()
        lk.acquire = AsyncMock(return_value=True)
        lk.release = AsyncMock()

        r = MagicMock()
        r.lock = MagicMock(return_value=lk)
        client = _make_client(r)

        async with client.lock("my-lock") as acquired_lock:
            assert acquired_lock is lk

        lk.release.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_lock_raises_when_not_acquired(self) -> None:
        lk = AsyncMock()
        lk.acquire = AsyncMock(return_value=False)

        r = MagicMock()
        r.lock = MagicMock(return_value=lk)
        client = _make_client(r)

        with pytest.raises(LockError):
            async with client.lock("my-lock", blocking=False):
                pass  # should not reach here

    @pytest.mark.asyncio
    async def test_lock_released_even_if_body_raises(self) -> None:
        lk = AsyncMock()
        lk.acquire = AsyncMock(return_value=True)
        lk.release = AsyncMock()

        r = MagicMock()
        r.lock = MagicMock(return_value=lk)
        client = _make_client(r)

        with pytest.raises(ValueError):
            async with client.lock("my-lock"):
                raise ValueError("boom")

        lk.release.assert_awaited_once()


# ---------------------------------------------------------------------------
# Metrics - smoke test that counters are incremented
# ---------------------------------------------------------------------------

class TestMetrics:
    @pytest.mark.asyncio
    async def test_ok_counter_incremented(self) -> None:
        before = _REDIS_OPS.labels(operation="get", status="ok")._value.get()
        client = _make_client(_redis_mock(get="val"))
        await client.get("key")
        after = _REDIS_OPS.labels(operation="get", status="ok")._value.get()
        assert after > before

    @pytest.mark.asyncio
    async def test_retry_counter_incremented_on_connection_error(self) -> None:
        calls = 0

        async def _flaky() -> str:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RedisConnError("transient")
            return "ok"

        before = _REDIS_OPS.labels(operation="test_metric", status="retry")._value.get()
        await _with_retry(lambda: _flaky(), operation="test_metric", attempts=3, base_delay=0.0)
        after = _REDIS_OPS.labels(operation="test_metric", status="retry")._value.get()
        assert after > before
