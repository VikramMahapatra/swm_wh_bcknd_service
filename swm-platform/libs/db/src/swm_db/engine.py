"""
Async SQLAlchemy engine factory and ``DatabaseSessionManager``.

Usage
-----
::

    from swm_db.engine import DatabaseSessionManager, EngineConfig

    cfg = EngineConfig(dsn=settings.postgres_dsn)
    mgr = DatabaseSessionManager(cfg)

    async with mgr.session() as session:
        ...

    await mgr.close()

Alternatively use the module-level singleton helpers in :mod:`swm_db.session`.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ---------------------------------------------------------------------------
# Engine configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EngineConfig:
    """
    All parameters needed to build an :class:`AsyncEngine`.

    Attributes
    ----------
    dsn:
        PostgreSQL async DSN, e.g. ``postgresql+asyncpg://user:pw@host/db``.
    pool_size:
        Number of persistent connections kept alive.
    max_overflow:
        Extra connections allowed above *pool_size* under burst load.
    pool_timeout:
        Seconds to wait for a free connection before raising ``TimeoutError``.
    pool_recycle:
        Seconds before the pool discards and recreates idle connections.
        Use ≤ 1800 s to stay below typical cloud firewall idle timeouts.
    pool_pre_ping:
        Execute ``SELECT 1`` on checkout to detect stale connections.
    echo:
        Log all SQL to the root logger (useful in development only).
    """

    dsn: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: float = 30.0
    pool_recycle: int = 1800
    pool_pre_ping: bool = True
    echo: bool = False
    connect_args: dict[str, object] = field(default_factory=dict)


def build_async_engine(config: EngineConfig) -> AsyncEngine:
    """Return a fully configured :class:`AsyncEngine` from *config*."""
    return create_async_engine(
        config.dsn,
        pool_size=config.pool_size,
        max_overflow=config.max_overflow,
        pool_timeout=config.pool_timeout,
        pool_recycle=config.pool_recycle,
        pool_pre_ping=config.pool_pre_ping,
        echo=config.echo,
        connect_args=config.connect_args,
    )


# ---------------------------------------------------------------------------
# Session manager
# ---------------------------------------------------------------------------


class DatabaseSessionManager:
    """
    Lifecycle manager for an async SQLAlchemy engine + session factory.

    The manager owns the connection pool.  Create one per process (or test),
    then call :meth:`close` during shutdown.

    Context managers
    ----------------
    :meth:`session`
        Yields an :class:`AsyncSession`.  Commits on clean exit, rolls back
        on exception.  For fine-grained transaction control within the session
        use :meth:`transaction` instead.
    :meth:`transaction`
        Yields a session with an *explicit* ``BEGIN`` block.  The caller must
        not call ``commit()`` manually; the context manager does it.
    :meth:`connect`
        Yields a raw :class:`AsyncConnection` for DDL / migration work.

    Parameters
    ----------
    config:
        Engine configuration dataclass.
    """

    def __init__(self, config: EngineConfig) -> None:
        self._config = config
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker[AsyncSession] | None = None
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Lazy initialisation (safe for import-time construction)
    # ------------------------------------------------------------------

    async def _get_engine(self) -> AsyncEngine:
        if self._engine is None:
            async with self._lock:
                if self._engine is None:  # re-check after acquiring lock
                    self._engine = build_async_engine(self._config)
                    self._sessionmaker = async_sessionmaker(
                        bind=self._engine,
                        expire_on_commit=False,
                        autobegin=True,
                    )
        return self._engine

    async def _get_sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        await self._get_engine()
        assert self._sessionmaker is not None
        return self._sessionmaker

    # ------------------------------------------------------------------
    # Context managers
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """
        Yield an :class:`AsyncSession`.

        Commits automatically on clean exit.  Rolls back and re-raises on any
        exception so the caller never receives a dirty session.
        """
        factory = await self._get_sessionmaker()
        async with factory() as ses:
            try:
                yield ses
                await ses.commit()
            except Exception:
                await ses.rollback()
                raise

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncSession]:
        """
        Yield a session with an explicit ``BEGIN``.

        Commits on clean exit, rolls back on exception.  Useful when you need
        to guarantee that multiple operations share a single transaction
        boundary even though the ORM would otherwise auto-begin lazily.
        """
        async with self.session() as ses:
            async with ses.begin_nested():
                yield ses

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        """Yield a raw :class:`AsyncConnection` (for DDL / Alembic use)."""
        engine = await self._get_engine()
        async with engine.begin() as conn:
            yield conn

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Dispose the connection pool and release all resources."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None
