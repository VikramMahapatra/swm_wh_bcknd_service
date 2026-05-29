"""add drivers gtc checkpoints and pickup points

Revision ID: 0011_driver_gtc_pickup_points
Revises: 0010_auth_management
Create Date: 2026-05-22 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_driver_gtc_pickup_points"
down_revision: str | None = "0010_auth_management"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "drivers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("license_number", sa.String(length=64), nullable=True),
        sa.Column("license_expiry", sa.Date(), nullable=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_vehicle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_drivers"),
    )
    op.create_index("ix_drivers_name", "drivers", ["name"])
    op.create_index("ix_drivers_vendor_id", "drivers", ["vendor_id"])
    op.create_index("ix_drivers_active", "drivers", ["active"])

    op.create_table(
        "gtc_checkpoints",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("truck_id", sa.String(length=128), nullable=False),
        sa.Column("arrived_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_dry", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_wet", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_metal", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_plastic", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_sanitary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("truck_cleanliness_score", sa.Float(), nullable=True),
        sa.Column("gtc_cleanliness_score", sa.Float(), nullable=True),
        sa.Column("remarks", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_gtc_checkpoints"),
    )
    op.create_index("ix_gtc_checkpoints_truck_arrived", "gtc_checkpoints", ["truck_id", "arrived_at"])
    op.create_index("ix_gtc_checkpoints_arrived_at", "gtc_checkpoints", ["arrived_at"])

    op.create_table(
        "pickup_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pickup_code", sa.String(length=64), nullable=False),
        sa.Column("pickup_name", sa.String(length=255), nullable=False),
        sa.Column("ward_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("route_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_pickup_points"),
        sa.UniqueConstraint("pickup_code", name="uq_pickup_points_pickup_code"),
    )
    op.create_index("ix_pickup_points_route_id", "pickup_points", ["route_id"])
    op.create_index("ix_pickup_points_ward_id", "pickup_points", ["ward_id"])
    op.create_index("ix_pickup_points_active", "pickup_points", ["active"])


def downgrade() -> None:
    op.drop_index("ix_pickup_points_active", table_name="pickup_points")
    op.drop_index("ix_pickup_points_ward_id", table_name="pickup_points")
    op.drop_index("ix_pickup_points_route_id", table_name="pickup_points")
    op.drop_table("pickup_points")

    op.drop_index("ix_gtc_checkpoints_arrived_at", table_name="gtc_checkpoints")
    op.drop_index("ix_gtc_checkpoints_truck_arrived", table_name="gtc_checkpoints")
    op.drop_table("gtc_checkpoints")

    op.drop_index("ix_drivers_active", table_name="drivers")
    op.drop_index("ix_drivers_vendor_id", table_name="drivers")
    op.drop_index("ix_drivers_name", table_name="drivers")
    op.drop_table("drivers")
