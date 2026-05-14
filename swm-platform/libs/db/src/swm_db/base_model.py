"""
SQLAlchemy 2.0 async-ready declarative base domain models for Fleet GPS platform.

This module provides:
- Naming-convention metadata
- Reusable ORM mixins
- Shared base model with UUID PK + audit + soft-delete + optimistic locking
- Utility methods for common lifecycle operations
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

from sqlalchemy import DateTime, Integer, MetaData, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class FleetBase(DeclarativeBase):
    """Base declarative class with naming conventions and UUID type mapping."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map: ClassVar[dict[Any, Any]] = {
        uuid.UUID: UUID(as_uuid=True),
    }


class UUIDPrimaryKeyMixin:
    """Adds a UUID primary key named `id`."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )


class TimestampMixin:
    """Adds timezone-aware creation and update timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        index=True,
    )

    def touch(self) -> None:
        """Bump `updated_at` to now (UTC)."""
        self.updated_at = datetime.now(UTC)


class AuditMixin:
    """Adds actor-tracking fields for create/update operations."""

    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    def set_created_by(self, actor: str | None) -> None:
        self.created_by = actor

    def set_updated_by(self, actor: str | None) -> None:
        self.updated_by = actor

    def apply_audit(self, actor: str | None) -> None:
        """Populate `created_by` if empty and always set `updated_by`."""
        if self.created_by is None:
            self.created_by = actor
        self.updated_by = actor


class SoftDeleteMixin:
    """Adds soft-delete field and helpers."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,
    )

    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self, *, actor: str | None = None) -> None:
        """Soft-delete the row and update audit fields when present."""
        now = datetime.now(UTC)
        self.deleted_at = now
        if hasattr(self, "updated_at"):
            self.updated_at = now  # type: ignore[assignment]
        if hasattr(self, "updated_by"):
            self.updated_by = actor  # type: ignore[assignment]

    def restore(self, *, actor: str | None = None) -> None:
        """Restore a soft-deleted row."""
        now = datetime.now(UTC)
        self.deleted_at = None
        if hasattr(self, "updated_at"):
            self.updated_at = now  # type: ignore[assignment]
        if hasattr(self, "updated_by"):
            self.updated_by = actor  # type: ignore[assignment]


class VersionMixin:
    """Adds integer version field for optimistic locking."""

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {
            "version_id_col": cls.version,
            "version_id_generator": lambda current: 1 if current is None else current + 1,
        }


class FleetBaseModel(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    AuditMixin,
    SoftDeleteMixin,
    VersionMixin,
    FleetBase,
):
    """Shared abstract base model for Fleet GPS domain entities."""

    __abstract__ = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize mapped columns to a JSON-friendly dictionary."""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    def __repr__(self) -> str:
        return f"<{type(self).__name__} id={self.id} version={self.version}>"
