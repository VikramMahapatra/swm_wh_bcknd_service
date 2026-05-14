from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from swm_db.models import GeofenceORM


class GeofenceRepository:
    """Repository for geofence CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs: Any) -> GeofenceORM:
        geofence = GeofenceORM(**kwargs)
        self._session.add(geofence)
        await self._session.flush()
        await self._session.refresh(geofence)
        return geofence

    async def get_by_id(self, geofence_id: uuid.UUID) -> GeofenceORM | None:
        result = await self._session.execute(select(GeofenceORM).where(GeofenceORM.id == geofence_id))
        return result.scalar_one_or_none()

    async def get_by_code(self, geofence_code: str) -> GeofenceORM | None:
        result = await self._session.execute(
            select(GeofenceORM).where(GeofenceORM.geofence_code == geofence_code.strip().upper())
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        ward_id: uuid.UUID | None = None,
        active_only: bool | None = None,
    ) -> list[GeofenceORM]:
        stmt = select(GeofenceORM)
        if ward_id is not None:
            stmt = stmt.where(GeofenceORM.ward_id == ward_id)
        if active_only is True:
            stmt = stmt.where(GeofenceORM.active.is_(True))
        elif active_only is False:
            stmt = stmt.where(GeofenceORM.active.is_(False))

        stmt = stmt.order_by(GeofenceORM.geofence_name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, geofence_id: uuid.UUID, **kwargs: Any) -> GeofenceORM:
        geofence = await self.get_by_id(geofence_id)
        if geofence is None:
            raise NoResultFound(f"Geofence with id={geofence_id} not found")

        for key, value in kwargs.items():
            setattr(geofence, key, value)

        await self._session.flush()
        await self._session.refresh(geofence)
        return geofence

    async def delete(self, geofence_id: uuid.UUID) -> None:
        geofence = await self.get_by_id(geofence_id)
        if geofence is None:
            raise NoResultFound(f"Geofence with id={geofence_id} not found")

        await self._session.delete(geofence)
        await self._session.flush()

    async def bulk_create(self, rows: Sequence[dict[str, Any]]) -> list[GeofenceORM]:
        geofences = [GeofenceORM(**row) for row in rows]
        self._session.add_all(geofences)
        await self._session.flush()
        for geofence in geofences:
            await self._session.refresh(geofence)
        return geofences
