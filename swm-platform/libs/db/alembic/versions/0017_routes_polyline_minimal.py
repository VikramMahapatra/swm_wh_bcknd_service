"""simplify routes table for polyline storage

Revision ID: 0017_routes_polyline_minimal
Revises: 0016_geofence_hierarchy_fields
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0017_routes_polyline_minimal"
down_revision = "0016_geofence_hierarchy_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("routes", sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("routes", sa.Column("ward_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "routes",
        sa.Column("polyline_coordinates", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )

    op.create_foreign_key("fk_routes_zone_id", "routes", "zones", ["zone_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_routes_ward_id", "routes", "wards", ["ward_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_routes_zone_id", "routes", ["zone_id"])
    op.create_index("ix_routes_ward_id", "routes", ["ward_id"])

    # Backfill ward_id from vehicles for existing routes; zone_id from ward.
    op.execute(
        """
        WITH picked_ward AS (
          SELECT v.route_id, (array_agg(v.ward_id))[1] AS ward_id
          FROM vehicles v
          WHERE v.route_id IS NOT NULL
          GROUP BY v.route_id
        )
        UPDATE routes r
        SET ward_id = pw.ward_id
        FROM picked_ward pw
        WHERE r.id = pw.route_id AND r.ward_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE routes r
        SET zone_id = w.zone_id
        FROM wards w
        WHERE r.ward_id = w.id AND r.zone_id IS NULL
        """
    )

    op.alter_column("routes", "zone_id", nullable=False)
    op.alter_column("routes", "ward_id", nullable=False)

    op.drop_index("ix_routes_active", table_name="routes")
    op.drop_column("routes", "route_code")
    op.drop_column("routes", "expected_distance_km")
    op.drop_column("routes", "expected_duration_min")
    op.drop_column("routes", "start_point")
    op.drop_column("routes", "end_point")
    op.drop_column("routes", "active")


def downgrade() -> None:
    op.add_column("routes", sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("routes", sa.Column("end_point", sa.String(length=255), nullable=False, server_default="N/A"))
    op.add_column("routes", sa.Column("start_point", sa.String(length=255), nullable=False, server_default="N/A"))
    op.add_column("routes", sa.Column("expected_duration_min", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("routes", sa.Column("expected_distance_km", sa.Float(), nullable=False, server_default="0"))
    op.add_column("routes", sa.Column("route_code", sa.String(length=24), nullable=False, server_default="ROUTE"))
    op.create_index("ix_routes_active", "routes", ["active"])

    op.drop_index("ix_routes_ward_id", table_name="routes")
    op.drop_index("ix_routes_zone_id", table_name="routes")
    op.drop_constraint("fk_routes_ward_id", "routes", type_="foreignkey")
    op.drop_constraint("fk_routes_zone_id", "routes", type_="foreignkey")
    op.drop_column("routes", "polyline_coordinates")
    op.drop_column("routes", "ward_id")
    op.drop_column("routes", "zone_id")
