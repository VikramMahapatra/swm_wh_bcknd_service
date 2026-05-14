from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from swm_db.device_vehicle_assignment_service import AssignmentCreateInput, DeviceVehicleAssignmentService
from swm_db.models import DeviceVehicleAssignmentORM


def _assignment(**kwargs: Any) -> DeviceVehicleAssignmentORM:
    assigned_from = kwargs.pop("assigned_from", datetime.now(UTC))
    return DeviceVehicleAssignmentORM(
        device_id=kwargs.pop("device_id", uuid.uuid4()),
        vehicle_id=kwargs.pop("vehicle_id", uuid.uuid4()),
        assigned_from=assigned_from,
        assigned_to=kwargs.pop("assigned_to", None),
        active=kwargs.pop("active", True),
        remarks=kwargs.pop("remarks", None),
        **kwargs,
    )


class TestDeviceVehicleAssignmentModel:
    def test_assigned_to_cannot_be_before_assigned_from(self) -> None:
        start = datetime.now(UTC)
        row = _assignment(assigned_from=start)
        with pytest.raises(ValueError, match="assigned_to"):
            row.assigned_to = start - timedelta(minutes=1)

    def test_close_marks_inactive_and_sets_assigned_to(self) -> None:
        row = _assignment()
        end = datetime.now(UTC)

        row.close(assigned_to=end, remarks="swap")

        assert row.active is False
        assert row.assigned_to == end
        assert row.remarks == "swap"


class TestDeviceVehicleAssignmentService:
    @pytest.mark.asyncio
    async def test_assign_replaces_existing_device_and_vehicle_mappings(self) -> None:
        repo = AsyncMock()

        existing_device = _assignment(device_id=uuid.uuid4(), vehicle_id=uuid.uuid4())
        existing_vehicle = _assignment(device_id=uuid.uuid4(), vehicle_id=uuid.uuid4())
        new_mapping = _assignment(device_id=existing_device.device_id, vehicle_id=existing_vehicle.vehicle_id)

        repo.get_active_pair.return_value = None
        repo.get_active_by_device.return_value = existing_device
        repo.get_active_by_vehicle.return_value = existing_vehicle
        repo.create.return_value = new_mapping

        svc = DeviceVehicleAssignmentService(repo)
        payload = AssignmentCreateInput(
            device_id=existing_device.device_id,
            vehicle_id=existing_vehicle.vehicle_id,
            remarks="replaced",
        )

        result = await svc.assign(payload)

        assert result is new_mapping
        assert repo.close_assignment.await_count == 2
        repo.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_assign_returns_existing_active_pair(self) -> None:
        repo = AsyncMock()
        pair = _assignment()
        repo.get_active_pair.return_value = pair

        svc = DeviceVehicleAssignmentService(repo)
        result = await svc.assign(
            AssignmentCreateInput(device_id=pair.device_id, vehicle_id=pair.vehicle_id)
        )

        assert result is pair
        repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_unassign_device_returns_none_when_no_active(self) -> None:
        repo = AsyncMock()
        repo.get_active_by_device.return_value = None

        svc = DeviceVehicleAssignmentService(repo)
        result = await svc.unassign_device(uuid.uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_unassign_vehicle_closes_active_row(self) -> None:
        repo = AsyncMock()
        active = _assignment()
        closed = _assignment(
            assigned_from=active.assigned_from,
            active=False,
            assigned_to=active.assigned_from + timedelta(minutes=1),
        )
        repo.get_active_by_vehicle.return_value = active
        repo.close_assignment.return_value = closed

        svc = DeviceVehicleAssignmentService(repo)
        result = await svc.unassign_vehicle(active.vehicle_id, remarks="maintenance")

        assert result is closed
        repo.close_assignment.assert_awaited_once()


class TestRepositoryImportContract:
    def test_repository_module_importable(self) -> None:
        from swm_db.device_vehicle_assignment_repository import DeviceVehicleAssignmentRepository

        ses = MagicMock(spec=AsyncSession)
        repo = DeviceVehicleAssignmentRepository(ses)
        assert repo is not None
