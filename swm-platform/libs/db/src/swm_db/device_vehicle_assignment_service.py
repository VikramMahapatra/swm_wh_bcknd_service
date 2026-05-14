from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from swm_db.device_vehicle_assignment_repository import DeviceVehicleAssignmentRepository
from swm_db.models import DeviceVehicleAssignmentORM


@dataclass(slots=True)
class AssignmentCreateInput:
    device_id: uuid.UUID
    vehicle_id: uuid.UUID
    assigned_from: datetime | None = None
    remarks: str | None = None


class DeviceVehicleAssignmentService:
    """Service for assignment, replacement, and assignment history."""

    def __init__(self, repository: DeviceVehicleAssignmentRepository) -> None:
        self._repository = repository

    async def assign(
        self,
        payload: AssignmentCreateInput,
    ) -> DeviceVehicleAssignmentORM:
        assigned_at = payload.assigned_from or datetime.now(UTC)

        existing_pair = await self._repository.get_active_pair(
            device_id=payload.device_id,
            vehicle_id=payload.vehicle_id,
        )
        if existing_pair is not None:
            return existing_pair

        active_device = await self._repository.get_active_by_device(payload.device_id)
        if active_device is not None:
            await self._repository.close_assignment(
                active_device,
                assigned_to=assigned_at,
                remarks="Replaced by new vehicle assignment",
            )

        active_vehicle = await self._repository.get_active_by_vehicle(payload.vehicle_id)
        if active_vehicle is not None:
            await self._repository.close_assignment(
                active_vehicle,
                assigned_to=assigned_at,
                remarks="Replaced by new device assignment",
            )

        return await self._repository.create(
            device_id=payload.device_id,
            vehicle_id=payload.vehicle_id,
            assigned_from=assigned_at,
            remarks=payload.remarks,
        )

    async def unassign_device(
        self,
        device_id: uuid.UUID,
        *,
        assigned_to: datetime | None = None,
        remarks: str | None = None,
    ) -> DeviceVehicleAssignmentORM | None:
        active = await self._repository.get_active_by_device(device_id)
        if active is None:
            return None

        return await self._repository.close_assignment(
            active,
            assigned_to=assigned_to or datetime.now(UTC),
            remarks=remarks,
        )

    async def unassign_vehicle(
        self,
        vehicle_id: uuid.UUID,
        *,
        assigned_to: datetime | None = None,
        remarks: str | None = None,
    ) -> DeviceVehicleAssignmentORM | None:
        active = await self._repository.get_active_by_vehicle(vehicle_id)
        if active is None:
            return None

        return await self._repository.close_assignment(
            active,
            assigned_to=assigned_to or datetime.now(UTC),
            remarks=remarks,
        )

    async def history_by_device(self, device_id: uuid.UUID) -> list[DeviceVehicleAssignmentORM]:
        return await self._repository.list_history_by_device(device_id)

    async def history_by_vehicle(self, vehicle_id: uuid.UUID) -> list[DeviceVehicleAssignmentORM]:
        return await self._repository.list_history_by_vehicle(vehicle_id)
