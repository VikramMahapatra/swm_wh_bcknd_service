"""
Unit tests for swm_db.

Tests use AsyncMock / MagicMock — no live database required.

Coverage
--------
TestAuditBase         — mixin fields, mark_deleted, restore, __repr__
TestTimestampMixin    — field presence on standalone model
TestSoftDeleteMixin   — is_deleted, mark_deleted, restore
TestEngineConfig      — dataclass defaults
TestDatabaseSessionManager — session(), transaction(), connect(), close()
TestRepository        — all CRUD operations via a fake AsyncSession
TestPage              — computed properties
TestGetDbSession      — FastAPI dependency generator
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import String
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from swm_db.base import AuditBase, SoftDeleteMixin
from swm_db.engine import DatabaseSessionManager, EngineConfig
from swm_db.repository import Page, Repository
from swm_db.session import get_db_session, override_session_manager, session_manager

# ---------------------------------------------------------------------------
# Test model
# ---------------------------------------------------------------------------


class RepoVehicleORM(AuditBase):
    """Minimal model used in repository tests."""

    __tablename__ = "vehicles_test"

    name: Mapped[str] = mapped_column(String(128), nullable=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_vehicle(**kwargs: Any) -> RepoVehicleORM:
    """Create a transient RepoVehicleORM with SQLAlchemy instrumentation intact."""
    obj = RepoVehicleORM(name=kwargs.pop("name", "Truck-1"))
    # Apply any overrides (id, deleted_at, etc.)
    for k, v in kwargs.items():
        setattr(obj, k, v)
    # Ensure id is set (mapped_column default runs at flush, not __init__)
    if obj.id is None:  # type: ignore[attr-defined]
        obj.id = uuid.uuid4()
    return obj


def _mock_session() -> MagicMock:
    """Return a MagicMock that quacks like AsyncSession."""
    ses = MagicMock(spec=AsyncSession)
    ses.execute = AsyncMock()
    ses.flush = AsyncMock()
    ses.refresh = AsyncMock()
    ses.delete = AsyncMock()
    ses.commit = AsyncMock()
    ses.rollback = AsyncMock()
    ses.add = MagicMock()
    ses.add_all = MagicMock()
    return ses


# ---------------------------------------------------------------------------
# AuditBase
# ---------------------------------------------------------------------------


class TestAuditBase:
    def test_repr_shows_class_and_id(self) -> None:
        v = _make_vehicle()
        assert "RepoVehicleORM" in repr(v)
        assert str(v.id) in repr(v)

    def test_is_deleted_false_when_deleted_at_is_none(self) -> None:
        v = _make_vehicle()
        assert v.is_deleted() is False

    def test_is_deleted_true_when_deleted_at_set(self) -> None:
        v = _make_vehicle(deleted_at=datetime.now(UTC))
        assert v.is_deleted() is True

    def test_mark_deleted_sets_deleted_at(self) -> None:
        v = _make_vehicle()
        before = datetime.now(UTC)
        v.mark_deleted()
        assert v.deleted_at is not None
        assert v.deleted_at >= before

    def test_mark_deleted_sets_updated_by_when_actor_provided(self) -> None:
        v = _make_vehicle()
        v.mark_deleted(actor="admin-service")
        assert v.updated_by == "admin-service"

    def test_restore_clears_deleted_at(self) -> None:
        v = _make_vehicle(deleted_at=datetime.now(UTC))
        v.restore()
        assert v.deleted_at is None


# ---------------------------------------------------------------------------
# SoftDeleteMixin standalone
# ---------------------------------------------------------------------------


class TestSoftDeleteMixin:
    def test_mark_deleted_without_audit_mixin(self) -> None:
        """mark_deleted must not fail if updated_by attribute is absent."""

        class Bare(SoftDeleteMixin):
            deleted_at: Any = None

        obj = Bare()
        obj.mark_deleted(actor="someone")  # should not raise
        assert obj.deleted_at is not None


# ---------------------------------------------------------------------------
# EngineConfig
# ---------------------------------------------------------------------------


class TestEngineConfig:
    def test_defaults(self) -> None:
        cfg = EngineConfig(dsn="postgresql+asyncpg://u:p@h/db")
        assert cfg.pool_size == 10
        assert cfg.max_overflow == 20
        assert cfg.pool_pre_ping is True
        assert cfg.echo is False

    def test_custom_values(self) -> None:
        cfg = EngineConfig(dsn="postgresql+asyncpg://u:p@h/db", pool_size=5, echo=True)
        assert cfg.pool_size == 5
        assert cfg.echo is True

    def test_frozen(self) -> None:
        cfg = EngineConfig(dsn="postgresql+asyncpg://u:p@h/db")
        with pytest.raises(AttributeError):
            cfg.pool_size = 1  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DatabaseSessionManager
# ---------------------------------------------------------------------------


class TestDatabaseSessionManager:
    def _make_mgr(self) -> DatabaseSessionManager:
        return DatabaseSessionManager(EngineConfig(dsn="postgresql+asyncpg://u:p@h/db"))

    @pytest.mark.asyncio
    async def test_session_yields_and_commits(self) -> None:
        mgr = self._make_mgr()

        mock_ses = _mock_session()
        factory = MagicMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=mock_ses)
        factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("swm_db.engine.build_async_engine") as mock_engine_fn,
            patch("swm_db.engine.async_sessionmaker", return_value=factory),
        ):
            mock_engine = MagicMock()
            mock_engine_fn.return_value = mock_engine

            async with mgr.session() as ses:
                assert ses is mock_ses

            mock_ses.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_session_rolls_back_on_exception(self) -> None:
        mgr = self._make_mgr()

        mock_ses = _mock_session()
        factory = MagicMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=mock_ses)
        factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("swm_db.engine.build_async_engine") as mock_engine_fn,
            patch("swm_db.engine.async_sessionmaker", return_value=factory),
        ):
            mock_engine_fn.return_value = MagicMock()

            with pytest.raises(ValueError, match="boom"):
                async with mgr.session():
                    raise ValueError("boom")

            mock_ses.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_disposes_engine(self) -> None:
        mgr = self._make_mgr()

        with patch("swm_db.engine.build_async_engine") as mock_engine_fn:
            mock_engine = AsyncMock()
            mock_engine_fn.return_value = mock_engine
            # force engine initialisation
            await mgr._get_engine()
            await mgr.close()

        mock_engine.dispose.assert_awaited_once()
        assert mgr._engine is None

    @pytest.mark.asyncio
    async def test_close_is_idempotent_when_never_opened(self) -> None:
        mgr = self._make_mgr()
        await mgr.close()  # should not raise


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------


class TestPage:
    def _page(self, total: int, page: int, page_size: int) -> Page[RepoVehicleORM]:
        return Page(items=[], total=total, page=page, page_size=page_size)

    def test_pages_single_page(self) -> None:
        assert self._page(5, 1, 10).pages == 1

    def test_pages_exact_boundary(self) -> None:
        assert self._page(20, 1, 10).pages == 2

    def test_pages_rounds_up(self) -> None:
        assert self._page(21, 1, 10).pages == 3

    def test_has_next_true(self) -> None:
        assert self._page(21, 1, 10).has_next is True

    def test_has_next_false_on_last_page(self) -> None:
        assert self._page(20, 2, 10).has_next is False

    def test_has_prev_false_on_first_page(self) -> None:
        assert self._page(50, 1, 10).has_prev is False

    def test_has_prev_true(self) -> None:
        assert self._page(50, 2, 10).has_prev is True

    def test_zero_page_size_returns_one_page(self) -> None:
        assert self._page(100, 1, 0).pages == 1


# ---------------------------------------------------------------------------
# Repository — helpers
# ---------------------------------------------------------------------------


def _repo(session: MagicMock) -> Repository[RepoVehicleORM]:
    return Repository(session, RepoVehicleORM)  # type: ignore[arg-type]


def _scalar_result(value: Any) -> MagicMock:
    """Return a mock that behaves like `session.execute(...)` result for scalar_one_or_none."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    r.scalar_one.return_value = value
    r.scalars.return_value.all.return_value = value if isinstance(value, list) else [value]
    return r


# ---------------------------------------------------------------------------
# Repository.get / get_or_raise
# ---------------------------------------------------------------------------


class TestRepositoryGet:
    @pytest.mark.asyncio
    async def test_get_returns_object_when_found(self) -> None:
        ses = _mock_session()
        vehicle = _make_vehicle()
        ses.execute.return_value = _scalar_result(vehicle)
        result = await _repo(ses).get(vehicle.id)
        assert result is vehicle

    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_found(self) -> None:
        ses = _mock_session()
        ses.execute.return_value = _scalar_result(None)
        result = await _repo(ses).get(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_or_raise_raises_when_not_found(self) -> None:
        ses = _mock_session()
        ses.execute.return_value = _scalar_result(None)
        with pytest.raises(NoResultFound):
            await _repo(ses).get_or_raise(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_get_or_raise_returns_row(self) -> None:
        ses = _mock_session()
        vehicle = _make_vehicle()
        ses.execute.return_value = _scalar_result(vehicle)
        result = await _repo(ses).get_or_raise(vehicle.id)
        assert result is vehicle


# ---------------------------------------------------------------------------
# Repository.list_all / count
# ---------------------------------------------------------------------------


class TestRepositoryList:
    @pytest.mark.asyncio
    async def test_list_all_returns_list(self) -> None:
        ses = _mock_session()
        vehicles = [_make_vehicle(), _make_vehicle()]
        r = MagicMock()
        r.scalars.return_value.all.return_value = vehicles
        ses.execute.return_value = r
        result = await _repo(ses).list_all()
        assert result == vehicles

    @pytest.mark.asyncio
    async def test_count_returns_integer(self) -> None:
        ses = _mock_session()
        ses.execute.return_value = _scalar_result(42)
        count = await _repo(ses).count()
        assert count == 42


# ---------------------------------------------------------------------------
# Repository.create
# ---------------------------------------------------------------------------


class TestRepositoryCreate:
    @pytest.mark.asyncio
    async def test_create_adds_flushes_and_refreshes(self) -> None:
        ses = _mock_session()
        async def _refresh(obj: Any) -> None:
            pass

        ses.refresh.side_effect = _refresh

        repo = _repo(ses)
        # We need to intercept model construction; patch __init__ is fragile with
        # SQLAlchemy, so we test the side-effects instead.
        result = await repo.create(name="Bus-1")
        ses.add.assert_called_once()
        ses.flush.assert_awaited_once()
        ses.refresh.assert_awaited_once()
        # result is an instance of RepoVehicleORM
        assert isinstance(result, RepoVehicleORM)


# ---------------------------------------------------------------------------
# Repository.update
# ---------------------------------------------------------------------------


class TestRepositoryUpdate:
    @pytest.mark.asyncio
    async def test_update_sets_attributes_and_flushes(self) -> None:
        ses = _mock_session()
        vehicle = _make_vehicle(name="Old")
        ses.execute.return_value = _scalar_result(vehicle)

        result = await _repo(ses).update(vehicle.id, name="New")
        assert result.name == "New"
        ses.flush.assert_awaited_once()
        ses.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_raises_when_not_found(self) -> None:
        ses = _mock_session()
        ses.execute.return_value = _scalar_result(None)
        with pytest.raises(NoResultFound):
            await _repo(ses).update(uuid.uuid4(), name="X")


# ---------------------------------------------------------------------------
# Repository.soft_delete / hard_delete / restore
# ---------------------------------------------------------------------------


class TestRepositoryDelete:
    @pytest.mark.asyncio
    async def test_soft_delete_sets_deleted_at(self) -> None:
        ses = _mock_session()
        vehicle = _make_vehicle()
        ses.execute.return_value = _scalar_result(vehicle)

        await _repo(ses).soft_delete(vehicle.id, actor="system")
        assert vehicle.is_deleted() is True
        assert vehicle.updated_by == "system"
        ses.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_hard_delete_calls_session_delete(self) -> None:
        ses = _mock_session()
        vehicle = _make_vehicle()
        ses.execute.return_value = _scalar_result(vehicle)

        await _repo(ses).hard_delete(vehicle.id)
        ses.delete.assert_awaited_once_with(vehicle)
        ses.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_hard_delete_raises_when_not_found(self) -> None:
        ses = _mock_session()
        ses.execute.return_value = _scalar_result(None)
        with pytest.raises(NoResultFound):
            await _repo(ses).hard_delete(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_restore_clears_deleted_at(self) -> None:
        ses = _mock_session()
        vehicle = _make_vehicle(deleted_at=datetime.now(UTC))
        ses.execute.return_value = _scalar_result(vehicle)

        result = await _repo(ses).restore(vehicle.id)
        assert result.deleted_at is None
        ses.flush.assert_awaited_once()
        ses.refresh.assert_awaited_once()


# ---------------------------------------------------------------------------
# Repository.paginate
# ---------------------------------------------------------------------------


class TestRepositoryPaginate:
    @pytest.mark.asyncio
    async def test_paginate_returns_page(self) -> None:
        ses = _mock_session()
        vehicles = [_make_vehicle(), _make_vehicle(), _make_vehicle()]

        # First execute call → count query; second → items query
        count_result = MagicMock()
        count_result.scalar_one.return_value = 3
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = vehicles
        ses.execute.side_effect = [count_result, items_result]

        page = await _repo(ses).paginate(page=1, page_size=10)

        assert page.total == 3
        assert page.page == 1
        assert page.page_size == 10
        assert list(page.items) == vehicles
        assert page.pages == 1
        assert page.has_next is False

    @pytest.mark.asyncio
    async def test_paginate_clamps_page_to_minimum_1(self) -> None:
        ses = _mock_session()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = []
        ses.execute.side_effect = [count_result, items_result]

        page = await _repo(ses).paginate(page=-5, page_size=10)
        assert page.page == 1


# ---------------------------------------------------------------------------
# Repository.upsert
# ---------------------------------------------------------------------------


class TestRepositoryUpsert:
    @pytest.mark.asyncio
    async def test_upsert_creates_when_not_found(self) -> None:
        ses = _mock_session()
        ses.execute.return_value = _scalar_result(None)

        new_id = uuid.uuid4()
        result = await _repo(ses).upsert(new_id, name="Van-1")
        ses.add.assert_called_once()
        assert isinstance(result, RepoVehicleORM)

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self) -> None:
        ses = _mock_session()
        vehicle = _make_vehicle(name="Old")
        ses.execute.return_value = _scalar_result(vehicle)

        result = await _repo(ses).upsert(vehicle.id, name="New")
        assert result.name == "New"
        ses.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_upsert_restores_soft_deleted(self) -> None:
        ses = _mock_session()
        vehicle = _make_vehicle(deleted_at=datetime.now(UTC))
        ses.execute.return_value = _scalar_result(vehicle)

        await _repo(ses).upsert(vehicle.id, name="Revived")
        assert vehicle.deleted_at is None


# ---------------------------------------------------------------------------
# Repository.bulk_create
# ---------------------------------------------------------------------------


class TestRepositoryBulkCreate:
    @pytest.mark.asyncio
    async def test_bulk_create_adds_all_and_flushes(self) -> None:
        ses = _mock_session()
        rows = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        results = await _repo(ses).bulk_create(rows)
        ses.add_all.assert_called_once()
        ses.flush.assert_awaited_once()
        assert len(results) == 3
        assert all(isinstance(r, RepoVehicleORM) for r in results)


# ---------------------------------------------------------------------------
# get_db_session dependency
# ---------------------------------------------------------------------------


class TestGetDbSession:
    @pytest.mark.asyncio
    async def test_yields_session_from_manager(self) -> None:
        mock_ses = _mock_session()
        mock_mgr = MagicMock(spec=DatabaseSessionManager)
        mock_mgr.session.return_value.__aenter__ = AsyncMock(return_value=mock_ses)
        mock_mgr.session.return_value.__aexit__ = AsyncMock(return_value=False)

        original = session_manager
        override_session_manager(mock_mgr)  # type: ignore[arg-type]
        try:
            gen = get_db_session()
            ses = await gen.__anext__()
            assert ses is mock_ses
        finally:
            override_session_manager(original)
