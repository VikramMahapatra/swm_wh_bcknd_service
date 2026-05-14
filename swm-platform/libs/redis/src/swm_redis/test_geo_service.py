from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from swm_redis.geo_service import GeoConfig, GeoPoint, GeoSearchResult, GeoUnit, RedisGeoService


@pytest.mark.asyncio
async def test_geoadd_typed() -> None:
    mock_client = MagicMock()
    mock_client.geoadd = AsyncMock(return_value=1)

    service = RedisGeoService(mock_client)
    added = await service.geoadd(
        "geo:vehicles",
        [GeoPoint(member="veh-1", longitude=77.5946, latitude=12.9716)],
    )

    assert added == 1
    mock_client.geoadd.assert_awaited_once()
    args = mock_client.geoadd.await_args.args
    assert args[0] == "geo:vehicles"
    assert args[1][0][2] == "veh-1"


@pytest.mark.asyncio
async def test_geosearch_radius_results() -> None:
    mock_client = MagicMock()
    mock_client.run_operation = AsyncMock(return_value=[("veh-1", 0.25), ("veh-2", 1.5)])
    mock_client.client = MagicMock()

    service = RedisGeoService(mock_client)
    found = await service.radius_search(longitude=77.59, latitude=12.97, radius_km=5, limit=5)

    assert len(found) == 2
    assert found[0] == GeoSearchResult(member="veh-1", distance=0.25, unit=GeoUnit.KM)


@pytest.mark.asyncio
async def test_nearest_vehicle() -> None:
    mock_client = MagicMock()
    mock_client.run_operation = AsyncMock(return_value=[("veh-9", 0.12)])
    mock_client.client = MagicMock()

    service = RedisGeoService(mock_client)
    nearest = await service.nearest_vehicle(longitude=77.59, latitude=12.97, max_radius_km=10)

    assert nearest is not None
    assert nearest.member == "veh-9"
    assert nearest.distance == 0.12


@pytest.mark.asyncio
async def test_nearest_vehicle_none() -> None:
    mock_client = MagicMock()
    mock_client.run_operation = AsyncMock(return_value=[])
    mock_client.client = MagicMock()

    service = RedisGeoService(mock_client)
    nearest = await service.nearest_vehicle(longitude=77.59, latitude=12.97)

    assert nearest is None


@pytest.mark.asyncio
async def test_depot_proximity() -> None:
    mock_client = MagicMock()
    mock_client.run_operation = AsyncMock(return_value=[("depot-a", 2.7), ("depot-b", 4.1)])
    mock_client.client = MagicMock()

    service = RedisGeoService(mock_client)
    depots = await service.depot_proximity(longitude=77.59, latitude=12.97, radius_km=10)

    assert [item.member for item in depots] == ["depot-a", "depot-b"]


@pytest.mark.asyncio
async def test_zone_lookup() -> None:
    mock_client = MagicMock()
    mock_client.run_operation = AsyncMock(return_value=[("zone-1", 0.8)])
    mock_client.client = MagicMock()

    service = RedisGeoService(mock_client)
    zones = await service.zone_lookup(longitude=77.59, latitude=12.97, radius_km=3)

    assert len(zones) == 1
    assert zones[0].member == "zone-1"


@pytest.mark.asyncio
async def test_add_vehicle_depot_zone_helpers() -> None:
    mock_client = MagicMock()
    mock_client.geoadd = AsyncMock(return_value=1)

    service = RedisGeoService(mock_client, config=GeoConfig())

    await service.add_vehicle_position(vehicle_id="veh-1", longitude=77.59, latitude=12.97)
    await service.add_depot(depot_id="dep-1", longitude=77.60, latitude=12.98)
    await service.add_zone(zone_id="zone-1", longitude=77.61, latitude=12.99)

    assert mock_client.geoadd.await_count == 3


@pytest.mark.asyncio
async def test_vehicle_distance_and_position() -> None:
    mock_client = MagicMock()
    mock_client.geodist = AsyncMock(return_value=3.42)
    mock_client.geopos = AsyncMock(return_value=[(77.5946, 12.9716)])

    service = RedisGeoService(mock_client)

    distance = await service.vehicle_distance_km("veh-1", "veh-2")
    position = await service.vehicle_position("veh-1")

    assert distance == 3.42
    assert position == (77.5946, 12.9716)
