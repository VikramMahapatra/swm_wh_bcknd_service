from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from swm_redis.realtime_cache import (
    FleetBucket,
    RealtimeCacheConfig,
    RealtimeCacheKeys,
    RealtimeCacheService,
    TruckGeofence,
    TruckLast,
    TruckLastSeen,
    TruckState,
    TruckTrip,
)


def test_realtime_cache_keys() -> None:
    keys = RealtimeCacheKeys(prefix="swm")
    assert keys.truck_last("123") == "swm:truck:last:123"
    assert keys.truck_state("123") == "swm:truck:state:123"
    assert keys.truck_last_seen("123") == "swm:truck:last_seen:123"
    assert keys.truck_trip("123") == "swm:truck:trip:123"
    assert keys.truck_geofence("123") == "swm:truck:geofence:123"
    assert keys.fleet_set(FleetBucket.MOVING) == "swm:fleet:moving"


@pytest.mark.asyncio
async def test_set_and_get_last() -> None:
    mock_client = MagicMock()
    mock_client.set_json = AsyncMock(return_value=True)
    mock_client.get_json = AsyncMock(
        return_value={
            "imei": "123",
            "device_id": "dev-1",
            "ts": "2026-05-04T00:00:00+00:00",
            "lat": 12.3,
            "lon": 77.4,
            "speed_kph": 44.0,
            "heading": 90,
            "ignition": True,
            "attributes": {"src": "gps"},
        }
    )

    service = RealtimeCacheService(
        mock_client,
        config=RealtimeCacheConfig(key_prefix="swm"),
    )

    await service.set_last(
        TruckLast(
            imei="123",
            device_id="dev-1",
            ts=datetime(2026, 5, 4, tzinfo=UTC),
            lat=12.3,
            lon=77.4,
            speed_kph=44.0,
            heading=90,
            ignition=True,
            attributes={"src": "gps"},
        )
    )

    model = await service.get_last("123")
    assert model is not None
    assert model.imei == "123"
    assert model.device_id == "dev-1"
    assert model.attributes["src"] == "gps"
    mock_client.set_json.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_last_returns_none_on_cache_miss() -> None:
    mock_client = MagicMock()
    mock_client.get_json = AsyncMock(return_value=None)

    service = RealtimeCacheService(mock_client)

    model = await service.get_last("missing")

    assert model is None


@pytest.mark.asyncio
async def test_set_state_moves_between_fleet_sets() -> None:
    mock_client = MagicMock()
    mock_client.set_json = AsyncMock(return_value=True)
    mock_client.sadd = AsyncMock(return_value=1)
    mock_client.srem = AsyncMock(return_value=1)

    service = RealtimeCacheService(mock_client)

    await service.set_state(
        TruckState(
            imei="999",
            status=FleetBucket.IDLE,
            updated_at=datetime(2026, 5, 4, tzinfo=UTC),
            reason="signal_drop",
        )
    )

    mock_client.set_json.assert_awaited_once()
    # one add for selected bucket, removals for others
    mock_client.sadd.assert_awaited_once_with("fleet:idle", "999")
    assert mock_client.srem.await_count == 4


@pytest.mark.asyncio
async def test_last_seen_roundtrip() -> None:
    mock_client = MagicMock()
    mock_client.set_json = AsyncMock(return_value=True)
    mock_client.get_json = AsyncMock(return_value={"imei": "abc", "ts": "2026-05-04T00:00:00+00:00"})

    service = RealtimeCacheService(mock_client)

    await service.touch_last_seen("abc", datetime(2026, 5, 4, tzinfo=UTC))
    model = await service.get_last_seen("abc")

    assert isinstance(model, TruckLastSeen)
    assert model is not None
    assert model.imei == "abc"


@pytest.mark.asyncio
async def test_trip_and_geofence_roundtrip() -> None:
    mock_client = MagicMock()
    mock_client.set_json = AsyncMock(return_value=True)
    mock_client.delete = AsyncMock(return_value=1)
    mock_client.get_json = AsyncMock(
        side_effect=[
            {
                "imei": "777",
                "trip_id": "trip-1",
                "started_at": "2026-05-04T00:00:00+00:00",
                "route_id": "route-1",
                "contractor_id": "con-1",
                "ward_id": "ward-1",
                "metadata": {"mode": "live"},
            },
            {
                "imei": "777",
                "geofence_id": "geo-1",
                "geofence_code": "DEPOT-A",
                "geofence_type": "depot",
                "entered_at": "2026-05-04T00:01:00+00:00",
                "exited_at": None,
                "metadata": {"source": "rule-engine"},
            },
        ]
    )

    service = RealtimeCacheService(mock_client)

    await service.set_trip(
        TruckTrip(
            imei="777",
            trip_id="trip-1",
            started_at=datetime(2026, 5, 4, tzinfo=UTC),
            route_id="route-1",
            contractor_id="con-1",
            ward_id="ward-1",
            metadata={"mode": "live"},
        )
    )
    await service.set_geofence(
        TruckGeofence(
            imei="777",
            geofence_id="geo-1",
            geofence_code="DEPOT-A",
            geofence_type="depot",
            entered_at=datetime(2026, 5, 4, 0, 1, tzinfo=UTC),
            metadata={"source": "rule-engine"},
        )
    )

    trip = await service.get_trip("777")
    geofence = await service.get_geofence("777")

    assert trip is not None
    assert geofence is not None
    assert trip.trip_id == "trip-1"
    assert geofence.geofence_code == "DEPOT-A"

    await service.clear_trip("777")
    await service.clear_geofence("777")
    assert mock_client.delete.await_count == 2


@pytest.mark.asyncio
async def test_update_snapshot_sets_all_keys() -> None:
    mock_client = MagicMock()
    mock_client.set_json = AsyncMock(return_value=True)
    mock_client.sadd = AsyncMock(return_value=1)
    mock_client.srem = AsyncMock(return_value=1)

    service = RealtimeCacheService(mock_client)

    await service.update_snapshot(
        last=TruckLast(
            imei="111",
            device_id="dev-111",
            ts=datetime(2026, 5, 4, tzinfo=UTC),
            lat=10.0,
            lon=20.0,
            speed_kph=30.0,
            heading=120,
            ignition=True,
        ),
        state=TruckState(
            imei="111",
            status=FleetBucket.MOVING,
            updated_at=datetime(2026, 5, 4, tzinfo=UTC),
        ),
    )

    # last + state + last_seen
    assert mock_client.set_json.await_count == 3


@pytest.mark.asyncio
async def test_fleet_set_queries() -> None:
    mock_client = MagicMock()
    mock_client.smembers = AsyncMock(return_value={"123", "456"})
    mock_client.sismember = AsyncMock(return_value=True)

    service = RealtimeCacheService(mock_client)

    members = await service.get_fleet_members(FleetBucket.OFFLINE)
    in_set = await service.is_in_fleet_bucket(FleetBucket.OFFLINE, "123")

    assert members == {"123", "456"}
    assert in_set is True
