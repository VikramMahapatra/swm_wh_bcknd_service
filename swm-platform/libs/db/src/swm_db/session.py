"""
Module-level singleton :class:`DatabaseSessionManager` and FastAPI / dependency
injection helpers.

The singleton is initialised lazily on first use from ``settings.postgres_dsn``.
In tests, replace it by calling :func:`override_session_manager`.

Example (FastAPI lifespan)::

    from contextlib import asynccontextmanager
    from fastapi import FastAPI
    from swm_db.session import session_manager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        await session_manager.close()

    app = FastAPI(lifespan=lifespan)

Example (dependency injection)::

    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession
    from swm_db.session import get_db_session

    @router.get("/items")
    async def list_items(db: AsyncSession = Depends(get_db_session)):
        ...
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from swm_common.settings import get_settings

from swm_db.engine import DatabaseSessionManager, EngineConfig


def _make_default_manager() -> DatabaseSessionManager:
    settings = get_settings()
    config = EngineConfig(dsn=settings.postgres_dsn)
    return DatabaseSessionManager(config)


# Module-level singleton; tests may replace this via override_session_manager().
session_manager: DatabaseSessionManager = _make_default_manager()


def override_session_manager(manager: DatabaseSessionManager) -> None:
    """
    Replace the module-level :data:`session_manager` singleton.

    Intended for use in tests or application startup where a custom
    :class:`~swm_db.engine.EngineConfig` is required::

        from swm_db.session import override_session_manager
        from swm_db.engine import DatabaseSessionManager, EngineConfig

        override_session_manager(DatabaseSessionManager(EngineConfig(dsn=TEST_DSN)))
    """
    global session_manager  # noqa: PLW0603
    session_manager = manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a managed :class:`AsyncSession`.

    Commits on clean exit; rolls back and re-raises on exception.
    """
    async with session_manager.session() as ses:
        yield ses

