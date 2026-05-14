from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from swm_redis.distributed_lock import (
    DistributedLockConfig,
    LockAcquireTimeoutError,
    RedisDistributedLockService,
)


@pytest.mark.asyncio
async def test_lock_acquire_and_release() -> None:
    mock_client = MagicMock()
    mock_client.set = AsyncMock(return_value=True)
    mock_client.run_operation = AsyncMock(return_value=1)
    mock_client.client = MagicMock()

    service = RedisDistributedLockService(mock_client)
    lock = service.vehicle_lock("v1", config=DistributedLockConfig(auto_renew=False, ttl_seconds=10))

    acquired = await lock.acquire()
    assert acquired is True
    assert lock.acquired is True

    released = await lock.release()
    assert released is True
    mock_client.set.assert_awaited_once()
    mock_client.run_operation.assert_awaited_once()


@pytest.mark.asyncio
async def test_lock_timeout() -> None:
    mock_client = MagicMock()
    mock_client.set = AsyncMock(return_value=False)
    mock_client.run_operation = AsyncMock()
    mock_client.client = MagicMock()

    service = RedisDistributedLockService(mock_client)
    lock = service.report_lock(
        "r1",
        config=DistributedLockConfig(auto_renew=False, acquire_timeout_seconds=0.05, retry_interval_seconds=0.01),
    )

    with pytest.raises(LockAcquireTimeoutError):
        await lock.acquire()


@pytest.mark.asyncio
async def test_lock_context_manager_releases() -> None:
    mock_client = MagicMock()
    mock_client.set = AsyncMock(return_value=True)
    mock_client.run_operation = AsyncMock(return_value=1)
    mock_client.client = MagicMock()

    service = RedisDistributedLockService(mock_client)
    lock = service.analytics_lock("a1", config=DistributedLockConfig(auto_renew=False))

    async with lock:
        assert lock.acquired is True

    assert lock.acquired is False
    assert mock_client.run_operation.await_count == 1


@pytest.mark.asyncio
async def test_auto_renew_calls_renew_script() -> None:
    mock_client = MagicMock()
    mock_client.set = AsyncMock(return_value=True)
    # renew succeeds once, release succeeds once
    mock_client.run_operation = AsyncMock(side_effect=[1, 1, 1])
    mock_client.client = MagicMock()

    service = RedisDistributedLockService(mock_client)
    lock = service.vehicle_lock(
        "v2",
        config=DistributedLockConfig(
            ttl_seconds=1,
            auto_renew=True,
            renew_interval_seconds=0.05,
            acquire_timeout_seconds=1,
        ),
    )

    await lock.acquire()
    await asyncio.sleep(0.12)
    await lock.release()

    assert mock_client.run_operation.await_count >= 2


@pytest.mark.asyncio
async def test_acquire_many_uses_sorted_order() -> None:
    order: list[str] = []

    async def _set_side_effect(key, value, *, ttl=None, nx=False, xx=False):
        order.append(key)
        return True

    mock_client = MagicMock()
    mock_client.set = AsyncMock(side_effect=_set_side_effect)
    mock_client.run_operation = AsyncMock(return_value=1)
    mock_client.client = MagicMock()

    service = RedisDistributedLockService(mock_client)

    async with service.acquire_many(["b", "a", "a"], config=DistributedLockConfig(auto_renew=False)):
        pass

    # Deduplicated and sorted, deadlock prevention via deterministic ordering.
    assert order[:2] == ["lock:a", "lock:b"]


@pytest.mark.asyncio
async def test_use_case_key_prefixes() -> None:
    mock_client = MagicMock()
    mock_client.set = AsyncMock(return_value=True)
    mock_client.run_operation = AsyncMock(return_value=1)
    mock_client.client = MagicMock()

    service = RedisDistributedLockService(mock_client)

    v_lock = service.vehicle_lock("veh-1", config=DistributedLockConfig(auto_renew=False))
    r_lock = service.report_lock("rep-1", config=DistributedLockConfig(auto_renew=False))
    a_lock = service.analytics_lock("an-1", config=DistributedLockConfig(auto_renew=False))

    assert v_lock.key == "lock:vehicle:veh-1"
    assert r_lock.key == "lock:report:rep-1"
    assert a_lock.key == "lock:analytics:an-1"
