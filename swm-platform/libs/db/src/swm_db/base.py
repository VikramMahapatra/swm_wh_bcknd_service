"""
Declarative base and reusable column mixins for all ORM models.

Hierarchy
---------
Base                — bare DeclarativeBase; use for models that need no mixins
TimestampMixin      — created_at / updated_at
SoftDeleteMixin     — deleted_at (soft-delete predicate helper)
AuditMixin          — created_by / updated_by (free-text actor identifiers)
AuditBase           — convenience: Base + all three mixins (recommended default)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

from sqlalchemy import DateTime, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedColumn, mapped_column


class Base(DeclarativeBase):
    """Bare declarative base — all ORM models inherit from this (or AuditBase)."""

    # Expose type_annotation_map for UUID so callers don't re-declare it.
    type_annotation_map: ClassVar[dict[Any, Any]] = {
        uuid.UUID: UUID(as_uuid=True),
    }


# ---------------------------------------------------------------------------
# Column mixins
# ---------------------------------------------------------------------------


class TimestampMixin:
    """Adds ``created_at`` and ``updated_at`` columns (timezone-aware)."""

    created_at: MappedColumn[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: MappedColumn[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """
    Adds a nullable ``deleted_at`` timestamp.

    Rows with a non-NULL ``deleted_at`` are considered logically deleted.
    Use :meth:`is_deleted` to check at the Python level and
    ``Model.deleted_at.is_(None)`` in queries to filter them out.
    """

    deleted_at: MappedColumn[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        server_default=text("NULL"),
        index=True,
    )

    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def mark_deleted(self, *, actor: str | None = None) -> None:
        """Set ``deleted_at`` to *now* (UTC).  Call ``session.flush()`` after."""
        self.deleted_at = datetime.now(UTC)
        # If the model also carries AuditMixin fields, update updated_by too.
        if hasattr(self, "updated_by") and actor is not None:
            self.updated_by = actor  # type: ignore[attr-defined]

    def restore(self) -> None:
        """Clear ``deleted_at``, un-deleting the row."""
        self.deleted_at = None


class AuditMixin:
    """
    Adds ``created_by`` and ``updated_by`` free-text actor columns.

    Typically populated from the authenticated user's ID or service name.
    """

    created_by: MappedColumn[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )
    updated_by: MappedColumn[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )


# ---------------------------------------------------------------------------
# Convenience composite base
# ---------------------------------------------------------------------------


class AuditBase(TimestampMixin, SoftDeleteMixin, AuditMixin, Base):
    """
    Recommended base for application models.

    Provides:
    - UUID primary key (``id``)
    - ``created_at`` / ``updated_at`` timestamps
    - ``deleted_at`` soft-delete
    - ``created_by`` / ``updated_by`` audit columns
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    def __repr__(self) -> str:
        return f"<{type(self).__name__} id={self.id}>"
