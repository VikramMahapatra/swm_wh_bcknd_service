from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from swm_db.models import VehicleORM


class VehicleRepository:
    """Repository for vehicle master CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs: Any) -> VehicleORM:
        vehicle = VehicleORM(**kwargs)
        self._session.add(vehicle)
        await self._session.flush()
        await self._session.refresh(vehicle)
        return vehicle

    async def get_by_id(self, vehicle_id: uuid.UUID) -> VehicleORM | None:
        result = await self._session.execute(select(VehicleORM).where(VehicleORM.id == vehicle_id))
        return result.scalar_one_or_none()

    async def get_by_vehicle_number(self, vehicle_number: str) -> VehicleORM | None:
        result = await self._session.execute(
            select(VehicleORM).where(VehicleORM.vehicle_number == vehicle_number.strip().upper())
        )
        return result.scalar_one_or_none()

    async def get_by_registration_number(self, registration_number: str) -> VehicleORM | None:
        result = await self._session.execute(
            select(VehicleORM).where(
                VehicleORM.registration_number == registration_number.strip().upper()
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        contractor_id: uuid.UUID | None = None,
        ward_id: uuid.UUID | None = None,
        route_id: uuid.UUID | None = None,
        active_only: bool | None = None,
    ) -> list[VehicleORM]:
        stmt = select(VehicleORM)
        if contractor_id is not None:
            stmt = stmt.where(VehicleORM.contractor_id == contractor_id)
        if ward_id is not None:
            stmt = stmt.where(VehicleORM.ward_id == ward_id)
        if route_id is not None:
            stmt = stmt.where(VehicleORM.route_id == route_id)
        if active_only is True:
            stmt = stmt.where(VehicleORM.active.is_(True))
        elif active_only is False:
            stmt = stmt.where(VehicleORM.active.is_(False))

        stmt = stmt.order_by(VehicleORM.vehicle_number)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, vehicle_id: uuid.UUID, **kwargs: Any) -> VehicleORM:
        vehicle = await self.get_by_id(vehicle_id)
        if vehicle is None:
            raise NoResultFound(f"Vehicle with id={vehicle_id} not found")

        for key, value in kwargs.items():
            setattr(vehicle, key, value)

        await self._session.flush()
        await self._session.refresh(vehicle)
        return vehicle

    async def delete(self, vehicle_id: uuid.UUID) -> None:
        vehicle = await self.get_by_id(vehicle_id)
        if vehicle is None:
            raise NoResultFound(f"Vehicle with id={vehicle_id} not found")

        await self._session.delete(vehicle)
        await self._session.flush()

    async def bulk_create(self, rows: Sequence[dict[str, Any]]) -> list[VehicleORM]:
        vehicles = [VehicleORM(**row) for row in rows]
        self._session.add_all(vehicles)
        await self._session.flush()
        for vehicle in vehicles:
            await self._session.refresh(vehicle)
        return vehicles
