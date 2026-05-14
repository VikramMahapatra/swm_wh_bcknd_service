from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from swm_db.models import DeviceVehicleAssignmentORM


class DeviceVehicleAssignmentRepository:
    """Repository for device-vehicle assignment history."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        device_id: uuid.UUID,
        vehicle_id: uuid.UUID,
        assigned_from: datetime,
        remarks: str | None = None,
    ) -> DeviceVehicleAssignmentORM:
        row = DeviceVehicleAssignmentORM(
            device_id=device_id,
            vehicle_id=vehicle_id,
            assigned_from=assigned_from,
            active=True,
            remarks=remarks,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_active_by_device(self, device_id: uuid.UUID) -> DeviceVehicleAssignmentORM | None:
        result = await self._session.execute(
            select(DeviceVehicleAssignmentORM).where(
                DeviceVehicleAssignmentORM.device_id == device_id,
                DeviceVehicleAssignmentORM.active.is_(True),
                DeviceVehicleAssignmentORM.assigned_to.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_active_by_vehicle(self, vehicle_id: uuid.UUID) -> DeviceVehicleAssignmentORM | None:
        result = await self._session.execute(
            select(DeviceVehicleAssignmentORM).where(
                DeviceVehicleAssignmentORM.vehicle_id == vehicle_id,
                DeviceVehicleAssignmentORM.active.is_(True),
                DeviceVehicleAssignmentORM.assigned_to.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_active_pair(
        self,
        *,
        device_id: uuid.UUID,
        vehicle_id: uuid.UUID,
    ) -> DeviceVehicleAssignmentORM | None:
        result = await self._session.execute(
            select(DeviceVehicleAssignmentORM).where(
                DeviceVehicleAssignmentORM.device_id == device_id,
                DeviceVehicleAssignmentORM.vehicle_id == vehicle_id,
                DeviceVehicleAssignmentORM.active.is_(True),
                DeviceVehicleAssignmentORM.assigned_to.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_history_by_device(self, device_id: uuid.UUID) -> list[DeviceVehicleAssignmentORM]:
        result = await self._session.execute(
            select(DeviceVehicleAssignmentORM)
            .where(DeviceVehicleAssignmentORM.device_id == device_id)
            .order_by(desc(DeviceVehicleAssignmentORM.assigned_from))
        )
        return list(result.scalars().all())

    async def list_history_by_vehicle(self, vehicle_id: uuid.UUID) -> list[DeviceVehicleAssignmentORM]:
        result = await self._session.execute(
            select(DeviceVehicleAssignmentORM)
            .where(DeviceVehicleAssignmentORM.vehicle_id == vehicle_id)
            .order_by(desc(DeviceVehicleAssignmentORM.assigned_from))
        )
        return list(result.scalars().all())

    async def close_assignment(
        self,
        row: DeviceVehicleAssignmentORM,
        *,
        assigned_to: datetime,
        remarks: str | None = None,
    ) -> DeviceVehicleAssignmentORM:
        row.close(assigned_to=assigned_to, remarks=remarks)
        await self._session.flush()
        await self._session.refresh(row)
        return row
