from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from swm_db.models import DeviceORM


class DeviceRepository:
    """Repository for device master CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs: Any) -> DeviceORM:
        device = DeviceORM(**kwargs)
        self._session.add(device)
        await self._session.flush()
        await self._session.refresh(device)
        return device

    async def get_by_id(self, device_id: uuid.UUID) -> DeviceORM | None:
        result = await self._session.execute(select(DeviceORM).where(DeviceORM.id == device_id))
        return result.scalar_one_or_none()

    async def get_by_imei(self, imei: str) -> DeviceORM | None:
        result = await self._session.execute(select(DeviceORM).where(DeviceORM.imei == imei.strip()))
        return result.scalar_one_or_none()

    async def list_by_vendor(self, vendor_id: uuid.UUID, *, active_only: bool | None = None) -> list[DeviceORM]:
        stmt = select(DeviceORM).where(DeviceORM.vendor_id == vendor_id)
        if active_only is True:
            stmt = stmt.where(DeviceORM.active.is_(True))
        elif active_only is False:
            stmt = stmt.where(DeviceORM.active.is_(False))

        stmt = stmt.order_by(DeviceORM.imei)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, device_id: uuid.UUID, **kwargs: Any) -> DeviceORM:
        device = await self.get_by_id(device_id)
        if device is None:
            raise NoResultFound(f"Device with id={device_id} not found")

        for key, value in kwargs.items():
            setattr(device, key, value)

        await self._session.flush()
        await self._session.refresh(device)
        return device

    async def delete(self, device_id: uuid.UUID) -> None:
        device = await self.get_by_id(device_id)
        if device is None:
            raise NoResultFound(f"Device with id={device_id} not found")

        await self._session.delete(device)
        await self._session.flush()

    async def bulk_create(self, rows: Sequence[dict[str, Any]]) -> list[DeviceORM]:
        devices = [DeviceORM(**row) for row in rows]
        self._session.add_all(devices)
        await self._session.flush()
        for device in devices:
            await self._session.refresh(device)
        return devices
