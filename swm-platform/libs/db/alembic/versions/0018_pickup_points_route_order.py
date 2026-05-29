"""simplify pickup points for route mapping

Revision ID: 0018_pickup_points_route_order
Revises: 0017_routes_polyline_minimal
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0018_pickup_points_route_order"
down_revision = "0017_routes_polyline_minimal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_pickup_points_active", table_name="pickup_points")
    op.drop_constraint("uq_pickup_points_pickup_code", "pickup_points", type_="unique")

    op.add_column("pickup_points", sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("pickup_points", sa.Column("sequence_no", sa.Integer(), nullable=False, server_default=sa.text("1")))

    op.execute(
        """
        WITH ranked AS (
          SELECT id, row_number() OVER (PARTITION BY route_id ORDER BY pickup_name, id) AS seq
          FROM pickup_points
        )
        UPDATE pickup_points p
        SET sequence_no = ranked.seq
        FROM ranked
        WHERE p.id = ranked.id
        """
    )
    op.execute(
        """
        UPDATE pickup_points p
        SET zone_id = r.zone_id
        FROM routes r
        WHERE p.route_id = r.id
          AND p.zone_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE pickup_points p
        SET zone_id = w.zone_id
        FROM wards w
        WHERE p.ward_id = w.id
          AND p.zone_id IS NULL
        """
    )
    op.execute("UPDATE pickup_points p SET route_id = NULL WHERE route_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM routes r WHERE r.id = p.route_id)")
    op.execute("UPDATE pickup_points p SET ward_id = NULL WHERE ward_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM wards w WHERE w.id = p.ward_id)")
    op.execute("UPDATE pickup_points p SET zone_id = NULL WHERE zone_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM zones z WHERE z.id = p.zone_id)")

    op.create_foreign_key("fk_pickup_points_zone_id", "pickup_points", "zones", ["zone_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_pickup_points_ward_id", "pickup_points", "wards", ["ward_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_pickup_points_route_id", "pickup_points", "routes", ["route_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_pickup_points_zone_id", "pickup_points", ["zone_id"])
    op.create_index("ix_pickup_points_route_sequence", "pickup_points", ["route_id", "sequence_no"])

    op.drop_column("pickup_points", "pickup_code")
    op.drop_column("pickup_points", "category")
    op.drop_column("pickup_points", "active")
    op.drop_column("pickup_points", "metadata")


def downgrade() -> None:
    op.add_column("pickup_points", sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("pickup_points", sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("pickup_points", sa.Column("category", sa.String(length=64), nullable=True))
    op.add_column("pickup_points", sa.Column("pickup_code", sa.String(length=64), nullable=False, server_default="PICKUP"))
    op.create_unique_constraint("uq_pickup_points_pickup_code", "pickup_points", ["pickup_code"])
    op.create_index("ix_pickup_points_active", "pickup_points", ["active"])

    op.drop_index("ix_pickup_points_route_sequence", table_name="pickup_points")
    op.drop_index("ix_pickup_points_zone_id", table_name="pickup_points")
    op.drop_constraint("fk_pickup_points_route_id", "pickup_points", type_="foreignkey")
    op.drop_constraint("fk_pickup_points_ward_id", "pickup_points", type_="foreignkey")
    op.drop_constraint("fk_pickup_points_zone_id", "pickup_points", type_="foreignkey")
    op.drop_column("pickup_points", "sequence_no")
    op.drop_column("pickup_points", "zone_id")
