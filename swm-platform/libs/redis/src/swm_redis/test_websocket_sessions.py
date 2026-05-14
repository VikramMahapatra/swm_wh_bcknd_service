from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from swm_redis.websocket_sessions import WebSocketSessionConfig, WebSocketSessionService


@pytest.mark.asyncio
async def test_connect_creates_session_and_sets() -> None:
    mock_client = MagicMock()
    mock_client.set_json = AsyncMock(return_value=True)
    mock_client.sadd = AsyncMock(return_value=1)
    mock_client.expire = AsyncMock(return_value=True)
    mock_client.scard = AsyncMock(return_value=1)

    service = WebSocketSessionService(mock_client)
    session = await service.connect(user_id="user-1", device_id="device-1")

    assert session.user_id == "user-1"
    assert session.device_id == "device-1"
    assert session.session_id
    assert mock_client.set_json.await_count == 1
    assert mock_client.sadd.await_count == 2
    assert mock_client.expire.await_count == 1


@pytest.mark.asyncio
async def test_multi_device_login() -> None:
    mock_client = MagicMock()
    mock_client.set_json = AsyncMock(return_value=True)
    mock_client.sadd = AsyncMock(return_value=1)
    mock_client.expire = AsyncMock(return_value=True)
    mock_client.scard = AsyncMock(return_value=2)
    mock_client.smembers = AsyncMock(return_value={"s-1", "s-2"})

    service = WebSocketSessionService(mock_client)
    await service.connect(user_id="user-1", session_id="s-1", device_id="phone")
    await service.connect(user_id="user-1", session_id="s-2", device_id="tablet")

    session_ids = await service.get_user_session_ids("user-1")
    assert session_ids == ["s-1", "s-2"]


@pytest.mark.asyncio
async def test_heartbeat_refreshes_payload_and_ttl() -> None:
    mock_client = MagicMock()
    mock_client.get_json = AsyncMock(
        return_value={
            "session_id": "s-1",
            "user_id": "user-1",
            "connected_at": "2026-05-04T00:00:00+00:00",
            "last_seen_at": "2026-05-04T00:00:00+00:00",
            "device_id": "d-1",
            "metadata": {},
        }
    )
    mock_client.set_json = AsyncMock(return_value=True)
    mock_client.expire = AsyncMock(return_value=True)

    service = WebSocketSessionService(mock_client)
    ok = await service.heartbeat("s-1", ts=datetime(2026, 5, 4, 0, 1, tzinfo=UTC))

    assert ok is True
    assert mock_client.set_json.await_count == 1
    assert mock_client.expire.await_count == 1


@pytest.mark.asyncio
async def test_refresh_ttl() -> None:
    mock_client = MagicMock()
    mock_client.get_json = AsyncMock(
        return_value={
            "session_id": "s-1",
            "user_id": "user-1",
            "connected_at": "2026-05-04T00:00:00+00:00",
            "last_seen_at": "2026-05-04T00:00:00+00:00",
            "device_id": None,
            "metadata": {},
        }
    )
    mock_client.expire = AsyncMock(return_value=True)

    service = WebSocketSessionService(mock_client)
    ok = await service.refresh_ttl("s-1")

    assert ok is True
    assert mock_client.expire.await_count == 2


@pytest.mark.asyncio
async def test_disconnect_cleanup() -> None:
    mock_client = MagicMock()
    mock_client.get_json = AsyncMock(
        return_value={
            "session_id": "s-1",
            "user_id": "user-1",
            "connected_at": "2026-05-04T00:00:00+00:00",
            "last_seen_at": "2026-05-04T00:00:00+00:00",
            "device_id": None,
            "metadata": {},
        }
    )
    mock_client.srem = AsyncMock(return_value=1)
    mock_client.delete = AsyncMock(return_value=1)
    mock_client.scard = AsyncMock(return_value=0)

    service = WebSocketSessionService(mock_client)
    ok = await service.disconnect("s-1")

    assert ok is True
    # global + user session set removal
    assert mock_client.srem.await_count == 2
    mock_client.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_disconnect_user_all_sessions() -> None:
    mock_client = MagicMock()
    mock_client.smembers = AsyncMock(return_value={"s-1", "s-2"})
    mock_client.get_json = AsyncMock(
        side_effect=[
            {
                "session_id": "s-1",
                "user_id": "user-1",
                "connected_at": "2026-05-04T00:00:00+00:00",
                "last_seen_at": "2026-05-04T00:00:00+00:00",
                "device_id": None,
                "metadata": {},
            },
            {
                "session_id": "s-2",
                "user_id": "user-1",
                "connected_at": "2026-05-04T00:00:00+00:00",
                "last_seen_at": "2026-05-04T00:00:00+00:00",
                "device_id": None,
                "metadata": {},
            },
        ]
    )
    mock_client.srem = AsyncMock(return_value=1)
    mock_client.delete = AsyncMock(return_value=1)
    mock_client.scard = AsyncMock(return_value=0)

    service = WebSocketSessionService(mock_client)
    count = await service.disconnect_user("user-1")

    assert count == 2


@pytest.mark.asyncio
async def test_get_user_sessions_prunes_stale_refs() -> None:
    mock_client = MagicMock()
    mock_client.smembers = AsyncMock(return_value={"s-1", "s-2"})
    mock_client.get_json = AsyncMock(
        side_effect=[
            {
                "session_id": "s-1",
                "user_id": "user-1",
                "connected_at": "2026-05-04T00:00:00+00:00",
                "last_seen_at": "2026-05-04T00:00:00+00:00",
                "device_id": None,
                "metadata": {},
            },
            None,
        ]
    )
    mock_client.srem = AsyncMock(return_value=1)

    service = WebSocketSessionService(mock_client)
    sessions = await service.get_user_sessions("user-1")

    assert len(sessions) == 1
    assert sessions[0].session_id == "s-1"
    # stale cleanup for s-2 from user set and ws:connections
    assert mock_client.srem.await_count == 2
