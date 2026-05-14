from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from swm_db.models import WardORM


class WardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs: Any) -> WardORM:
        ward = WardORM(**kwargs)
        self._session.add(ward)
        await self._session.flush()
        await self._session.refresh(ward)
        return ward

    async def get_by_id(self, ward_id: uuid.UUID) -> WardORM | None:
        result = await self._session.execute(select(WardORM).where(WardORM.id == ward_id))
        return result.scalar_one_or_none()

    async def get_by_code(self, ward_code: str) -> WardORM | None:
        result = await self._session.execute(
            select(WardORM).where(WardORM.ward_code == ward_code.strip().upper())
        )
        return result.scalar_one_or_none()

    async def list(self, *, zone_name: str | None = None, active_only: bool | None = None) -> list[WardORM]:
        stmt = select(WardORM)
        if zone_name is not None:
            stmt = stmt.where(WardORM.zone_name == zone_name)
        if active_only is True:
            stmt = stmt.where(WardORM.active.is_(True))
        elif active_only is False:
            stmt = stmt.where(WardORM.active.is_(False))
        stmt = stmt.order_by(WardORM.ward_name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, ward_id: uuid.UUID, **kwargs: Any) -> WardORM:
        ward = await self.get_by_id(ward_id)
        if ward is None:
            raise NoResultFound(f"Ward with id={ward_id} not found")

        for key, value in kwargs.items():
            setattr(ward, key, value)

        await self._session.flush()
        await self._session.refresh(ward)
        return ward

    async def delete(self, ward_id: uuid.UUID) -> None:
        ward = await self.get_by_id(ward_id)
        if ward is None:
            raise NoResultFound(f"Ward with id={ward_id} not found")

        await self._session.delete(ward)
        await self._session.flush()

    async def bulk_create(self, rows: Sequence[dict[str, Any]]) -> list[WardORM]:
        wards = [WardORM(**row) for row in rows]
        self._session.add_all(wards)
        await self._session.flush()
        for ward in wards:
            await self._session.refresh(ward)
        return wards
