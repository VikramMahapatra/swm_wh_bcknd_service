from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from swm_db.models import VendorORM


class VendorRepository:
    """Repository for vendor master CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs: Any) -> VendorORM:
        vendor = VendorORM(**kwargs)
        self._session.add(vendor)
        await self._session.flush()
        await self._session.refresh(vendor)
        return vendor

    async def get_by_id(self, vendor_id: uuid.UUID) -> VendorORM | None:
        result = await self._session.execute(select(VendorORM).where(VendorORM.id == vendor_id))
        return result.scalar_one_or_none()

    async def get_by_code(self, vendor_code: str) -> VendorORM | None:
        result = await self._session.execute(
            select(VendorORM).where(VendorORM.vendor_code == vendor_code.strip().upper())
        )
        return result.scalar_one_or_none()

    async def list(self, *, active_only: bool | None = None) -> list[VendorORM]:
        stmt = select(VendorORM)
        if active_only is True:
            stmt = stmt.where(VendorORM.active.is_(True))
        elif active_only is False:
            stmt = stmt.where(VendorORM.active.is_(False))

        stmt = stmt.order_by(VendorORM.vendor_name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, vendor_id: uuid.UUID, **kwargs: Any) -> VendorORM:
        vendor = await self.get_by_id(vendor_id)
        if vendor is None:
            raise NoResultFound(f"Vendor with id={vendor_id} not found")

        for key, value in kwargs.items():
            setattr(vendor, key, value)

        await self._session.flush()
        await self._session.refresh(vendor)
        return vendor

    async def delete(self, vendor_id: uuid.UUID) -> None:
        vendor = await self.get_by_id(vendor_id)
        if vendor is None:
            raise NoResultFound(f"Vendor with id={vendor_id} not found")

        await self._session.delete(vendor)
        await self._session.flush()

    async def bulk_create(self, rows: Sequence[dict[str, Any]]) -> list[VendorORM]:
        vendors = [VendorORM(**row) for row in rows]
        self._session.add_all(vendors)
        await self._session.flush()
        for vendor in vendors:
            await self._session.refresh(vendor)
        return vendors
