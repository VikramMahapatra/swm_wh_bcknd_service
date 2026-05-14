"""add device vehicle assignment history

Revision ID: 0007_device_vehicle_assignment
Revises: 0006_geofence_master
Create Date: 2026-05-04 02:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_device_vehicle_assignment"
down_revision: str | None = "0006_geofence_master"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "device_vehicle_assignments",
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "assigned_from",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("assigned_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("remarks", sa.String(length=500), nullable=True),
        sa.CheckConstraint(
            "assigned_to IS NULL OR assigned_to >= assigned_from",
            name="ck_dva_assigned_range",
        ),
        sa.CheckConstraint(
            "(active = false) OR (assigned_to IS NULL)",
            name="ck_dva_active_assigned_to",
        ),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
            name="fk_dva_device_id_devices",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_id"],
            ["vehicles.id"],
            name="fk_dva_vehicle_id_vehicles",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("device_id", "vehicle_id", "assigned_from", name="pk_dva"),
    )

    op.create_index(
        "ix_dva_device_assigned_from",
        "device_vehicle_assignments",
        ["device_id", "assigned_from"],
    )
    op.create_index(
        "ix_dva_vehicle_assigned_from",
        "device_vehicle_assignments",
        ["vehicle_id", "assigned_from"],
    )
    op.create_index(
        "ux_dva_active_device",
        "device_vehicle_assignments",
        ["device_id"],
        unique=True,
        postgresql_where=sa.text("active IS TRUE AND assigned_to IS NULL"),
    )
    op.create_index(
        "ux_dva_active_vehicle",
        "device_vehicle_assignments",
        ["vehicle_id"],
        unique=True,
        postgresql_where=sa.text("active IS TRUE AND assigned_to IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_dva_active_vehicle", table_name="device_vehicle_assignments")
    op.drop_index("ux_dva_active_device", table_name="device_vehicle_assignments")
    op.drop_index("ix_dva_vehicle_assigned_from", table_name="device_vehicle_assignments")
    op.drop_index("ix_dva_device_assigned_from", table_name="device_vehicle_assignments")
    op.drop_table("device_vehicle_assignments")
