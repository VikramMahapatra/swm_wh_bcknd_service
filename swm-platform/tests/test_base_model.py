from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from swm_db.base_model import FleetBaseModel, NAMING_CONVENTION


class VehicleDomainORM(FleetBaseModel):
    __tablename__ = "vehicles_domain"

    name: Mapped[str] = mapped_column(String(128), nullable=False)


class TestNamingConvention:
    def test_metadata_uses_expected_naming_convention(self) -> None:
        assert VehicleDomainORM.metadata.naming_convention == NAMING_CONVENTION


class TestFleetBaseModelColumns:
    def test_model_has_required_columns(self) -> None:
        columns = set(VehicleDomainORM.__table__.columns.keys())

        assert "id" in columns
        assert "created_at" in columns
        assert "updated_at" in columns
        assert "created_by" in columns
        assert "updated_by" in columns
        assert "deleted_at" in columns
        assert "version" in columns

    def test_mapper_uses_version_for_optimistic_locking(self) -> None:
        assert VehicleDomainORM.__mapper__.version_id_col is not None
        assert VehicleDomainORM.__mapper__.version_id_col.key == "version"


class TestUtilityMethods:
    def test_touch_updates_updated_at(self) -> None:
        obj = VehicleDomainORM(name="Truck-42")
        before = datetime(2020, 1, 1, tzinfo=UTC)
        obj.updated_at = before

        obj.touch()

        assert obj.updated_at > before

    def test_apply_audit_sets_created_and_updated_by(self) -> None:
        obj = VehicleDomainORM(name="Truck-42")

        obj.apply_audit("svc-ingestion")

        assert obj.created_by == "svc-ingestion"
        assert obj.updated_by == "svc-ingestion"

    def test_apply_audit_keeps_existing_created_by(self) -> None:
        obj = VehicleDomainORM(name="Truck-42")
        obj.created_by = "seed-script"

        obj.apply_audit("svc-admin")

        assert obj.created_by == "seed-script"
        assert obj.updated_by == "svc-admin"

    def test_soft_delete_sets_deleted_at_and_updated_by(self) -> None:
        obj = VehicleDomainORM(name="Truck-42")

        obj.soft_delete(actor="svc-delete")

        assert obj.deleted_at is not None
        assert obj.is_deleted() is True
        assert obj.updated_by == "svc-delete"

    def test_restore_clears_deleted_at(self) -> None:
        obj = VehicleDomainORM(name="Truck-42")
        obj.deleted_at = datetime.now(UTC)

        obj.restore(actor="svc-restore")

        assert obj.deleted_at is None
        assert obj.is_deleted() is False
        assert obj.updated_by == "svc-restore"

    def test_to_dict_includes_declared_columns(self) -> None:
        row_id = uuid.uuid4()
        obj = VehicleDomainORM(name="Truck-42")
        obj.id = row_id
        obj.version = 7

        data = obj.to_dict()

        assert data["id"] == row_id
        assert data["name"] == "Truck-42"
        assert data["version"] == 7
