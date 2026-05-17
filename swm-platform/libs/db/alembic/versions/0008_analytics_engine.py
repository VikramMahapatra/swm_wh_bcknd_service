"""add analytics engine tables

Revision ID: 0008_analytics_engine
Revises: 0007_device_vehicle_assignment
Create Date: 2026-05-17 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_analytics_engine"
down_revision: str | None = "0007_device_vehicle_assignment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analytics_vehicle_state",
        sa.Column("vehicle_id", sa.String(length=128), nullable=False),
        sa.Column("imei", sa.String(length=17), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("last_event_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_lat", sa.Float(), nullable=False),
        sa.Column("last_lng", sa.Float(), nullable=False),
        sa.Column("last_speed_kph", sa.Float(), nullable=False, server_default="0"),
        sa.Column("last_odometer_km", sa.Float(), nullable=True),
        sa.Column("last_ignition", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("trip_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("trip_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trip_start_odometer_km", sa.Float(), nullable=True),
        sa.Column("trip_distance_km", sa.Float(), nullable=False, server_default="0"),
        sa.Column("trip_runtime_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trip_moving_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trip_idle_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trip_stoppages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("idle_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("idle_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idle_anchor_lat", sa.Float(), nullable=True),
        sa.Column("idle_anchor_lng", sa.Float(), nullable=True),
        sa.Column("current_geofence_code", sa.String(length=32), nullable=True),
        sa.Column("current_geofence_entered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_route_deviation_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("vehicle_id", name="pk_analytics_vehicle_state"),
    )
    op.create_index("ix_analytics_vehicle_state_imei", "analytics_vehicle_state", ["imei"])

    op.create_table(
        "analytics_trip_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", sa.String(length=128), nullable=False),
        sa.Column("imei", sa.String(length=17), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("vendor_id", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("runtime_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("moving_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("idle_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stoppages_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("start_odometer_km", sa.Float(), nullable=True),
        sa.Column("end_odometer_km", sa.Float(), nullable=True),
        sa.Column("distance_km", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_analytics_trip_records"),
    )
    op.create_index("ix_analytics_trip_records_vehicle_started", "analytics_trip_records", ["vehicle_id", "started_at"])
    op.create_index("ix_analytics_trip_records_started", "analytics_trip_records", ["started_at"])

    op.create_table(
        "analytics_idle_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", sa.String(length=128), nullable=False),
        sa.Column("imei", sa.String(length=17), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("vendor_id", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_analytics_idle_records"),
    )
    op.create_index("ix_analytics_idle_records_vehicle_started", "analytics_idle_records", ["vehicle_id", "started_at"])
    op.create_index("ix_analytics_idle_records_started", "analytics_idle_records", ["started_at"])

    op.create_table(
        "analytics_overspeed_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", sa.String(length=128), nullable=False),
        sa.Column("imei", sa.String(length=17), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("vendor_id", sa.String(length=64), nullable=False),
        sa.Column("event_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("speed_kph", sa.Float(), nullable=False),
        sa.Column("threshold_kph", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_analytics_overspeed_events"),
    )
    op.create_index("ix_analytics_overspeed_vehicle_ts", "analytics_overspeed_events", ["vehicle_id", "event_ts"])
    op.create_index("ix_analytics_overspeed_event_ts", "analytics_overspeed_events", ["event_ts"])

    op.create_table(
        "analytics_geofence_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", sa.String(length=128), nullable=False),
        sa.Column("imei", sa.String(length=17), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("vendor_id", sa.String(length=64), nullable=False),
        sa.Column("geofence_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("geofence_code", sa.String(length=32), nullable=True),
        sa.Column("geofence_type", sa.String(length=16), nullable=True),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("event_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dwell_seconds", sa.Integer(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("event_type IN ('entry','exit','route_deviation')", name="ck_analytics_geofence_event_type"),
        sa.PrimaryKeyConstraint("id", name="pk_analytics_geofence_events"),
    )
    op.create_index("ix_analytics_geofence_vehicle_ts", "analytics_geofence_events", ["vehicle_id", "event_ts"])
    op.create_index("ix_analytics_geofence_code_ts", "analytics_geofence_events", ["geofence_code", "event_ts"])

    op.create_table(
        "analytics_daily_kpis",
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("vehicle_id", sa.String(length=128), nullable=False),
        sa.Column("imei", sa.String(length=17), nullable=False),
        sa.Column("vendor_id", sa.String(length=64), nullable=False),
        sa.Column("trips_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("distance_km", sa.Float(), nullable=False, server_default="0"),
        sa.Column("runtime_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("moving_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("idle_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stoppages_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overspeed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("geofence_entries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("geofence_exits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("route_deviation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fuel_used_l", sa.Float(), nullable=False, server_default="0"),
        sa.Column("utilization_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("metric_date", "vehicle_id", name="pk_analytics_daily_kpis"),
    )
    op.create_index("ix_analytics_daily_kpis_metric_date", "analytics_daily_kpis", ["metric_date"])
    op.create_index("ix_analytics_daily_kpis_vendor_date", "analytics_daily_kpis", ["vendor_id", "metric_date"])


def downgrade() -> None:
    op.drop_index("ix_analytics_daily_kpis_vendor_date", table_name="analytics_daily_kpis")
    op.drop_index("ix_analytics_daily_kpis_metric_date", table_name="analytics_daily_kpis")
    op.drop_table("analytics_daily_kpis")

    op.drop_index("ix_analytics_geofence_code_ts", table_name="analytics_geofence_events")
    op.drop_index("ix_analytics_geofence_vehicle_ts", table_name="analytics_geofence_events")
    op.drop_table("analytics_geofence_events")

    op.drop_index("ix_analytics_overspeed_event_ts", table_name="analytics_overspeed_events")
    op.drop_index("ix_analytics_overspeed_vehicle_ts", table_name="analytics_overspeed_events")
    op.drop_table("analytics_overspeed_events")

    op.drop_index("ix_analytics_idle_records_started", table_name="analytics_idle_records")
    op.drop_index("ix_analytics_idle_records_vehicle_started", table_name="analytics_idle_records")
    op.drop_table("analytics_idle_records")

    op.drop_index("ix_analytics_trip_records_started", table_name="analytics_trip_records")
    op.drop_index("ix_analytics_trip_records_vehicle_started", table_name="analytics_trip_records")
    op.drop_table("analytics_trip_records")

    op.drop_index("ix_analytics_vehicle_state_imei", table_name="analytics_vehicle_state")
    op.drop_table("analytics_vehicle_state")
