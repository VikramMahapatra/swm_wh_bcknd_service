"""add vehicle master and dependency reference tables

Revision ID: 0004_vehicle_master
Revises: 0003_device_master
Create Date: 2026-05-04 01:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_vehicle_master"
down_revision: str | None = "0003_device_master"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contractors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contractor_name", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_contractors"),
    )

    op.create_table(
        "wards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ward_name", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_wards"),
    )

    op.create_table(
        "routes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("route_name", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_routes"),
    )

    op.create_table(
        "vehicles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_number", sa.String(length=24), nullable=False),
        sa.Column("registration_number", sa.String(length=24), nullable=False),
        sa.Column("truck_type", sa.String(length=64), nullable=True),
        sa.Column("capacity_kg", sa.Float(), nullable=False),
        sa.Column("capacity_cubic_meter", sa.Float(), nullable=False),
        sa.Column("contractor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ward_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("route_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fuel_type", sa.String(length=16), nullable=False),
        sa.Column("operational_status", sa.String(length=16), nullable=False),
        sa.Column("chassis_number", sa.String(length=64), nullable=True),
        sa.Column("engine_number", sa.String(length=64), nullable=True),
        sa.Column("manufacture_year", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(
            "fuel_type IN ('diesel','petrol','cng','electric','lng')",
            name="ck_vehicles_fuel_type",
        ),
        sa.CheckConstraint(
            "operational_status IN ('operational','maintenance','breakdown','retired')",
            name="ck_vehicles_operational_status",
        ),
        sa.CheckConstraint("capacity_kg >= 0", name="ck_vehicles_capacity_kg_non_negative"),
        sa.CheckConstraint(
            "capacity_cubic_meter >= 0",
            name="ck_vehicles_capacity_cubic_meter_non_negative",
        ),
        sa.CheckConstraint(
            "manufacture_year >= 1950 AND manufacture_year <= 2100",
            name="ck_vehicles_manufacture_year_range",
        ),
        sa.ForeignKeyConstraint(
            ["contractor_id"],
            ["contractors.id"],
            name="fk_vehicles_contractor_id_contractors",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["ward_id"],
            ["wards.id"],
            name="fk_vehicles_ward_id_wards",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["route_id"],
            ["routes.id"],
            name="fk_vehicles_route_id_routes",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_vehicles"),
        sa.UniqueConstraint("vehicle_number", name="uq_vehicles_vehicle_number"),
        sa.UniqueConstraint("registration_number", name="uq_vehicles_registration_number"),
    )

    op.create_index("ix_vehicles_contractor_id", "vehicles", ["contractor_id"])
    op.create_index("ix_vehicles_ward_id", "vehicles", ["ward_id"])
    op.create_index("ix_vehicles_route_id", "vehicles", ["route_id"])
    op.create_index("ix_vehicles_active", "vehicles", ["active"])


def downgrade() -> None:
    op.drop_index("ix_vehicles_active", table_name="vehicles")
    op.drop_index("ix_vehicles_route_id", table_name="vehicles")
    op.drop_index("ix_vehicles_ward_id", table_name="vehicles")
    op.drop_index("ix_vehicles_contractor_id", table_name="vehicles")
    op.drop_table("vehicles")
    op.drop_table("routes")
    op.drop_table("wards")
    op.drop_table("contractors")
