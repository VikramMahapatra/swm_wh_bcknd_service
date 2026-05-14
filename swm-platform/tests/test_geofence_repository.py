from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from swm_db.geofence_repository import GeofenceRepository
from swm_db.models import GeofenceORM


def _mock_session() -> MagicMock:
    ses = MagicMock(spec=AsyncSession)
    ses.execute = AsyncMock()
    ses.flush = AsyncMock()
    ses.refresh = AsyncMock()
    ses.delete = AsyncMock()
    ses.add = MagicMock()
    ses.add_all = MagicMock()
    return ses


def _scalar_result(value: Any) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalars.return_value.all.return_value = value if isinstance(value, list) else [value]
    return result


def _geofence(**kwargs: Any) -> GeofenceORM:
    obj = GeofenceORM(
        geofence_code=kwargs.pop("geofence_code", "GF-100"),
        geofence_name=kwargs.pop("geofence_name", "Default GF"),
        type=kwargs.pop("type", "zone"),
        geometry_type=kwargs.pop("geometry_type", "circle"),
        center_lat=kwargs.pop("center_lat", 12.9716),
        center_lng=kwargs.pop("center_lng", 77.5946),
        radius_meter=kwargs.pop("radius_meter", 100.0),
        polygon=kwargs.pop("polygon", None),
        ward_id=kwargs.pop("ward_id", None),
        active=kwargs.pop("active", True),
    )
    if obj.id is None:  # type: ignore[attr-defined]
        obj.id = uuid.uuid4()
    return obj


class TestGeofenceRepository:
    @pytest.mark.asyncio
    async def test_create_adds_flushes_refreshes(self) -> None:
        ses = _mock_session()
        repo = GeofenceRepository(ses)

        geofence = await repo.create(
            geofence_code="GF-201",
            geofence_name="Depot 201",
            type="depot",
            geometry_type="circle",
            center_lat=12.9,
            center_lng=77.5,
            radius_meter=200,
            active=True,
        )

        ses.add.assert_called_once()
        ses.flush.assert_awaited_once()
        ses.refresh.assert_awaited_once_with(geofence)

    @pytest.mark.asyncio
    async def test_get_by_code_normalizes_input(self) -> None:
        ses = _mock_session()
        geofence = _geofence(geofence_code="GF-ABC")
        ses.execute.return_value = _scalar_result(geofence)

        found = await GeofenceRepository(ses).get_by_code(" gf-abc ")
        assert found is geofence

    @pytest.mark.asyncio
    async def test_update_missing_raises(self) -> None:
        ses = _mock_session()
        ses.execute.return_value = _scalar_result(None)

        with pytest.raises(NoResultFound):
            await GeofenceRepository(ses).update(uuid.uuid4(), geofence_name="X")

    @pytest.mark.asyncio
    async def test_delete_calls_session_delete(self) -> None:
        ses = _mock_session()
        geofence = _geofence()
        ses.execute.return_value = _scalar_result(geofence)

        await GeofenceRepository(ses).delete(geofence.id)
        ses.delete.assert_awaited_once_with(geofence)
        ses.flush.assert_awaited_once()
