from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from swm_db.models import ContractorORM


class ContractorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs: Any) -> ContractorORM:
        contractor = ContractorORM(**kwargs)
        self._session.add(contractor)
        await self._session.flush()
        await self._session.refresh(contractor)
        return contractor

    async def get_by_id(self, contractor_id: uuid.UUID) -> ContractorORM | None:
        result = await self._session.execute(
            select(ContractorORM).where(ContractorORM.id == contractor_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, contractor_code: str) -> ContractorORM | None:
        result = await self._session.execute(
            select(ContractorORM).where(
                ContractorORM.contractor_code == contractor_code.strip().upper()
            )
        )
        return result.scalar_one_or_none()

    async def list(self, *, active_only: bool | None = None) -> list[ContractorORM]:
        stmt = select(ContractorORM)
        if active_only is True:
            stmt = stmt.where(ContractorORM.active.is_(True))
        elif active_only is False:
            stmt = stmt.where(ContractorORM.active.is_(False))
        stmt = stmt.order_by(ContractorORM.contractor_name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, contractor_id: uuid.UUID, **kwargs: Any) -> ContractorORM:
        contractor = await self.get_by_id(contractor_id)
        if contractor is None:
            raise NoResultFound(f"Contractor with id={contractor_id} not found")

        for key, value in kwargs.items():
            setattr(contractor, key, value)

        await self._session.flush()
        await self._session.refresh(contractor)
        return contractor

    async def delete(self, contractor_id: uuid.UUID) -> None:
        contractor = await self.get_by_id(contractor_id)
        if contractor is None:
            raise NoResultFound(f"Contractor with id={contractor_id} not found")

        await self._session.delete(contractor)
        await self._session.flush()

    async def bulk_create(self, rows: Sequence[dict[str, Any]]) -> list[ContractorORM]:
        contractors = [ContractorORM(**row) for row in rows]
        self._session.add_all(contractors)
        await self._session.flush()
        for contractor in contractors:
            await self._session.refresh(contractor)
        return contractors
