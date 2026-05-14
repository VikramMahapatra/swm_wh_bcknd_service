from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from swm_db.models import VehicleORM
from swm_db.vehicle_repository import VehicleRepository


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


def _vehicle(**kwargs: Any) -> VehicleORM:
    obj = VehicleORM(
        vehicle_number=kwargs.pop("vehicle_number", "TN01-AB-1234"),
        registration_number=kwargs.pop("registration_number", "KA02-CD-9876"),
        contractor_id=kwargs.pop("contractor_id", uuid.uuid4()),
        ward_id=kwargs.pop("ward_id", uuid.uuid4()),
        route_id=kwargs.pop("route_id", None),
        fuel_type=kwargs.pop("fuel_type", "diesel"),
        operational_status=kwargs.pop("operational_status", "operational"),
        capacity_kg=kwargs.pop("capacity_kg", 1000),
        capacity_cubic_meter=kwargs.pop("capacity_cubic_meter", 10),
        metadata_json=kwargs.pop("metadata_json", {}),
        **kwargs,
    )
    if obj.id is None:  # type: ignore[attr-defined]
        obj.id = uuid.uuid4()
    return obj


class TestVehicleRepository:
    @pytest.mark.asyncio
    async def test_create_adds_flushes_and_refreshes(self) -> None:
        ses = _mock_session()
        repo = VehicleRepository(ses)

        vehicle = await repo.create(
            vehicle_number="TN01-AB-1234",
            registration_number="KA02-CD-9876",
            contractor_id=uuid.uuid4(),
            ward_id=uuid.uuid4(),
            fuel_type="diesel",
            operational_status="operational",
            capacity_kg=1000,
            capacity_cubic_meter=10,
            metadata_json={},
        )

        ses.add.assert_called_once()
        ses.flush.assert_awaited_once()
        ses.refresh.assert_awaited_once_with(vehicle)

    @pytest.mark.asyncio
    async def test_get_by_id_returns_row(self) -> None:
        ses = _mock_session()
        vehicle = _vehicle()
        ses.execute.return_value = _scalar_result(vehicle)

        found = await VehicleRepository(ses).get_by_id(vehicle.id)
        assert found is vehicle

    @pytest.mark.asyncio
    async def test_get_by_vehicle_number_normalizes(self) -> None:
        ses = _mock_session()
        vehicle = _vehicle(vehicle_number="TN01-AB-1234")
        ses.execute.return_value = _scalar_result(vehicle)

        found = await VehicleRepository(ses).get_by_vehicle_number(" tn01-ab-1234 ")
        assert found is vehicle

    @pytest.mark.asyncio
    async def test_update_raises_when_missing(self) -> None:
        ses = _mock_session()
        ses.execute.return_value = _scalar_result(None)

        with pytest.raises(NoResultFound):
            await VehicleRepository(ses).update(uuid.uuid4(), truck_type="compactor")

    @pytest.mark.asyncio
    async def test_delete_calls_session_delete(self) -> None:
        ses = _mock_session()
        vehicle = _vehicle()
        ses.execute.return_value = _scalar_result(vehicle)

        await VehicleRepository(ses).delete(vehicle.id)
        ses.delete.assert_awaited_once_with(vehicle)
        ses.flush.assert_awaited_once()
