from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from swm_db.models import VehicleORM
from swm_db.vehicle_service import VehicleCreateInput, VehicleService, VehicleUpdateInput


def _vehicle() -> VehicleORM:
    return VehicleORM(
        id=uuid.uuid4(),
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


class TestVehicleService:
    @pytest.mark.asyncio
    async def test_create_vehicle_maps_payload(self) -> None:
        repo = AsyncMock()
        created = _vehicle()
        repo.create.return_value = created

        contractor_id = uuid.uuid4()
        ward_id = uuid.uuid4()
        service = VehicleService(repo)
        result = await service.create_vehicle(
            VehicleCreateInput(
                vehicle_number="TN01-AB-1234",
                registration_number="KA02-CD-9876",
                contractor_id=contractor_id,
                ward_id=ward_id,
                metadata={"fleet": "north"},
            )
        )

        assert result is created
        repo.create.assert_awaited_once()
        _, kwargs = repo.create.await_args
        assert kwargs["contractor_id"] == contractor_id
        assert kwargs["ward_id"] == ward_id
        assert kwargs["metadata_json"] == {"fleet": "north"}

    @pytest.mark.asyncio
    async def test_update_vehicle_builds_partial_map(self) -> None:
        repo = AsyncMock()
        updated = _vehicle()
        repo.update.return_value = updated

        service = VehicleService(repo)
        vehicle_id = uuid.uuid4()
        await service.update_vehicle(
            vehicle_id,
            VehicleUpdateInput(truck_type="tipper", active=False, metadata={"zone": "east"}),
        )

        repo.update.assert_awaited_once()
        args, kwargs = repo.update.await_args
        assert args[0] == vehicle_id
        assert kwargs["truck_type"] == "tipper"
        assert kwargs["active"] is False
        assert kwargs["metadata_json"] == {"zone": "east"}

    @pytest.mark.asyncio
    async def test_activate_and_deactivate_vehicle(self) -> None:
        repo = AsyncMock()
        repo.update.return_value = _vehicle()

        service = VehicleService(repo)
        vehicle_id = uuid.uuid4()

        await service.activate_vehicle(vehicle_id)
        await service.deactivate_vehicle(vehicle_id)

        assert repo.update.await_count == 2
