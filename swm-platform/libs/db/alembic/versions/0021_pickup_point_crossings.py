"""pickup point crossing events and pickup radius

Revision ID: 0021_pickup_point_crossings
Revises: 0020_alert_vendor_column
Create Date: 2026-05-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0021_pickup_point_crossings"
down_revision = "0020_alert_vendor_column"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pickup_points", sa.Column("pickup_radius_m", sa.Float(), nullable=True))

    op.create_table(
        "pickup_point_crossings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("vehicle_id", sa.String(length=128), nullable=False),
        sa.Column("route_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pickup_point_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("crossed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("distance_m", sa.Float(), nullable=False),
        sa.Column("radius_m", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default=sa.text("'telemetry'")),
        sa.Column("imei", sa.String(length=17), nullable=True),
        sa.Column("vendor_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["pickup_point_id"], ["pickup_points.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pickup_point_crossings_crossed_at", "pickup_point_crossings", ["crossed_at"])
    op.create_index(
        "ix_pickup_point_crossings_vehicle_crossed",
        "pickup_point_crossings",
        ["vehicle_id", "crossed_at"],
    )
    op.create_index(
        "ix_pickup_point_crossings_route_crossed",
        "pickup_point_crossings",
        ["route_id", "crossed_at"],
    )
    op.create_index(
        "ix_pickup_point_crossings_pickup_crossed",
        "pickup_point_crossings",
        ["pickup_point_id", "crossed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_pickup_point_crossings_pickup_crossed", table_name="pickup_point_crossings")
    op.drop_index("ix_pickup_point_crossings_route_crossed", table_name="pickup_point_crossings")
    op.drop_index("ix_pickup_point_crossings_vehicle_crossed", table_name="pickup_point_crossings")
    op.drop_index("ix_pickup_point_crossings_crossed_at", table_name="pickup_point_crossings")
    op.drop_table("pickup_point_crossings")
    op.drop_column("pickup_points", "pickup_radius_m")
