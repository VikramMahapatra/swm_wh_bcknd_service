from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from swm_db.models import RouteORM


class RouteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs: Any) -> RouteORM:
        route = RouteORM(**kwargs)
        self._session.add(route)
        await self._session.flush()
        await self._session.refresh(route)
        return route

    async def get_by_id(self, route_id: uuid.UUID) -> RouteORM | None:
        result = await self._session.execute(select(RouteORM).where(RouteORM.id == route_id))
        return result.scalar_one_or_none()

    async def get_by_code(self, route_code: str) -> RouteORM | None:
        result = await self._session.execute(
            select(RouteORM).where(RouteORM.route_code == route_code.strip().upper())
        )
        return result.scalar_one_or_none()

    async def list(self, *, active_only: bool | None = None) -> list[RouteORM]:
        stmt = select(RouteORM)
        if active_only is True:
            stmt = stmt.where(RouteORM.active.is_(True))
        elif active_only is False:
            stmt = stmt.where(RouteORM.active.is_(False))
        stmt = stmt.order_by(RouteORM.route_name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, route_id: uuid.UUID, **kwargs: Any) -> RouteORM:
        route = await self.get_by_id(route_id)
        if route is None:
            raise NoResultFound(f"Route with id={route_id} not found")

        for key, value in kwargs.items():
            setattr(route, key, value)

        await self._session.flush()
        await self._session.refresh(route)
        return route

    async def delete(self, route_id: uuid.UUID) -> None:
        route = await self.get_by_id(route_id)
        if route is None:
            raise NoResultFound(f"Route with id={route_id} not found")

        await self._session.delete(route)
        await self._session.flush()

    async def bulk_create(self, rows: Sequence[dict[str, Any]]) -> list[RouteORM]:
        routes = [RouteORM(**row) for row in rows]
        self._session.add_all(routes)
        await self._session.flush()
        for route in routes:
            await self._session.refresh(route)
        return routes
