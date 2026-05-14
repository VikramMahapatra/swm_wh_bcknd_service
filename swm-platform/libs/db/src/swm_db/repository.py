"""
Generic async repository pattern with pagination support.

Design
------
* :class:`Page` is a typed, immutable result container for paginated queries.
* :class:`Repository` is a generic class parameterised on an :class:`~swm_db.base.AuditBase`
  subclass.  It provides the standard CRUD verbs *plus* soft-delete and
  restore.  All mutating operations call ``session.flush()`` so that the
  caller's unit-of-work (the surrounding transaction) is still in control of
  when data is actually committed.

Usage
-----
::

    class VehicleRepository(Repository["VehicleORM"]):
        pass

    async with session_manager.session() as ses:
        repo = VehicleRepository(ses, VehicleORM)
        vehicle = await repo.get_or_raise(vehicle_id)
        page   = await repo.paginate(page=1, page_size=20)
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from swm_db.base import AuditBase

# ----- type variable --------------------------------------------------------

ModelT = TypeVar("ModelT", bound=AuditBase)


# ---------------------------------------------------------------------------
# Pagination container
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Page(Generic[ModelT]):  # noqa: UP046
    """
    Immutable container for a single page of ORM results.

    Attributes
    ----------
    items:       The ORM objects on this page.
    total:       Total number of rows matching the query (before slicing).
    page:        1-based current page number.
    page_size:   Requested page size (may differ from ``len(items)`` on last page).
    """

    items: Sequence[ModelT]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        """Total number of pages."""
        if self.page_size <= 0:
            return 1
        return max(1, math.ceil(self.total / self.page_size))

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class Repository(Generic[ModelT]):  # noqa: UP046
    """
    Async generic repository.

    Parameters
    ----------
    session:
        The active :class:`~sqlalchemy.ext.asyncio.AsyncSession`.  The session
        should be provided by the caller (e.g. from ``DatabaseSessionManager.session()``).
    model:
        The concrete ORM class, e.g. ``VehicleORM``.
    """

    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self._session = session
        self._model = model

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get(self, id: uuid.UUID) -> ModelT | None:  # noqa: A002
        """Return the row with *id* or ``None`` (soft-deleted rows excluded)."""
        stmt = (
            select(self._model)
            .where(
                self._model.id == id,  # type: ignore[attr-defined]
                self._model.deleted_at.is_(None),  # type: ignore[attr-defined]
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_raise(self, id: uuid.UUID) -> ModelT:  # noqa: A002
        """
        Return the row with *id* or raise :class:`~sqlalchemy.exc.NoResultFound`.
        """
        obj = await self.get(id)
        if obj is None:
            raise NoResultFound(f"{self._model.__name__} with id={id} not found")
        return obj

    async def get_including_deleted(self, id: uuid.UUID) -> ModelT | None:  # noqa: A002
        """Return the row with *id* regardless of soft-delete status."""
        stmt = select(self._model).where(self._model.id == id)  # type: ignore[attr-defined]
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, *, include_deleted: bool = False) -> list[ModelT]:
        """Return every row, optionally including soft-deleted ones."""
        stmt = select(self._model)
        if not include_deleted:
            stmt = stmt.where(self._model.deleted_at.is_(None))  # type: ignore[attr-defined]
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, *, include_deleted: bool = False) -> int:
        """Return the total row count (optionally including soft-deleted rows)."""
        stmt = select(func.count()).select_from(self._model)
        if not include_deleted:
            stmt = stmt.where(self._model.deleted_at.is_(None))  # type: ignore[attr-defined]
        result = await self._session.execute(stmt)
        val = result.scalar_one()
        return int(val)

    async def paginate(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
    ) -> Page[ModelT]:
        """
        Return a :class:`Page` of rows.

        Parameters
        ----------
        page:
            1-based page number.
        page_size:
            Maximum rows per page (bounded to 1-1000 internally).
        include_deleted:
            When *True*, soft-deleted rows are included in the result.
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 1000))
        offset = (page - 1) * page_size

        base_stmt = select(self._model)
        if not include_deleted:
            base_stmt = base_stmt.where(self._model.deleted_at.is_(None))  # type: ignore[attr-defined]

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total_result = await self._session.execute(count_stmt)
        total = int(total_result.scalar_one())

        items_stmt = (
            base_stmt
            .order_by(self._model.created_at)  # type: ignore[attr-defined]
            .offset(offset)
            .limit(page_size)
        )
        items_result = await self._session.execute(items_stmt)
        items = list(items_result.scalars().all())

        return Page(items=items, total=total, page=page, page_size=page_size)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create(self, **kwargs: Any) -> ModelT:
        """
        Instantiate *model* with *kwargs*, add to the session, flush, and
        refresh so that server-side defaults (id, timestamps) are populated.
        """
        obj = self._model(**kwargs)
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def update(self, id: uuid.UUID, **kwargs: Any) -> ModelT:  # noqa: A002
        """
        Partial-update the row identified by *id*.

        Raises :class:`~sqlalchemy.exc.NoResultFound` when the row does not
        exist or is soft-deleted.
        """
        obj = await self.get_or_raise(id)
        for key, value in kwargs.items():
            setattr(obj, key, value)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def soft_delete(self, id: uuid.UUID, *, actor: str | None = None) -> None:  # noqa: A002
        """
        Logically delete the row by setting ``deleted_at`` to *now* (UTC).

        Raises :class:`~sqlalchemy.exc.NoResultFound` when the row does not
        exist or is already soft-deleted.
        """
        obj = await self.get_or_raise(id)
        obj.mark_deleted(actor=actor)  # type: ignore[attr-defined]
        await self._session.flush()

    async def hard_delete(self, id: uuid.UUID) -> None:  # noqa: A002
        """
        Permanently remove the row from the database.

        Works on both active and soft-deleted rows.  Raises
        :class:`~sqlalchemy.exc.NoResultFound` when the row does not exist at
        all.
        """
        obj = await self.get_including_deleted(id)
        if obj is None:
            raise NoResultFound(f"{self._model.__name__} with id={id} not found")
        await self._session.delete(obj)
        await self._session.flush()

    async def restore(self, id: uuid.UUID) -> ModelT:  # noqa: A002
        """
        Un-delete a soft-deleted row.

        Raises :class:`~sqlalchemy.exc.NoResultFound` when the row does not
        exist at all.  Returns the refreshed object.
        """
        obj = await self.get_including_deleted(id)
        if obj is None:
            raise NoResultFound(f"{self._model.__name__} with id={id} not found")
        obj.restore()  # type: ignore[attr-defined]
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def upsert(self, id: uuid.UUID, **kwargs: Any) -> ModelT:  # noqa: A002
        """
        Insert if *id* does not exist; update if it does.

        Includes soft-deleted rows in the lookup so that a previously deleted
        record can be revived via an upsert.
        """
        obj = await self.get_including_deleted(id)
        if obj is None:
            return await self.create(id=id, **kwargs)
        for key, value in kwargs.items():
            setattr(obj, key, value)
        # Restore if soft-deleted
        if obj.deleted_at is not None:  # type: ignore[attr-defined]
            obj.deleted_at = None  # type: ignore[attr-defined]
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    # ------------------------------------------------------------------
    # Bulk helpers
    # ------------------------------------------------------------------

    async def bulk_create(self, rows: list[dict[str, Any]]) -> list[ModelT]:
        """
        Insert multiple rows in a single flush.

        Each dict in *rows* is passed as ``**kwargs`` to the model constructor.
        Returns the list of refreshed ORM objects in insertion order.
        """
        objects = [self._model(**row) for row in rows]
        self._session.add_all(objects)
        await self._session.flush()
        for obj in objects:
            await self._session.refresh(obj)
        return objects
