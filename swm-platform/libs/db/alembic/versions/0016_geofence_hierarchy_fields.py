"""add geofence hierarchy fields matching UI

Revision ID: 0016_geofence_hierarchy_fields
Revises: 0015_geofence_scope_fields
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0016_geofence_hierarchy_fields"
down_revision = "0015_geofence_scope_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "geofences",
        sa.Column("geofence_for", sa.String(length=16), nullable=False, server_default=sa.text("'ward'")),
    )
    op.add_column("geofences", sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("geofences", sa.Column("route_id", postgresql.UUID(as_uuid=True), nullable=True))

    op.create_check_constraint(
        "ck_geofences_geofence_for",
        "geofences",
        "geofence_for IN ('zone','ward','route')",
    )
    op.create_foreign_key("fk_geofences_zone_id", "geofences", "zones", ["zone_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_geofences_route_id", "geofences", "routes", ["route_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_geofences_zone_id", "geofences", ["zone_id"])
    op.create_index("ix_geofences_route_id", "geofences", ["route_id"])
    op.create_index("ix_geofences_for_hierarchy", "geofences", ["geofence_for", "zone_id", "ward_id", "route_id"])

    # Backfill for existing ward/zone scoped geofences.
    op.execute(
        """
        UPDATE geofences g
        SET geofence_for = CASE
            WHEN g.scope_type = 'zone' THEN 'zone'
            ELSE 'ward'
        END,
        zone_id = CASE
            WHEN g.scope_type = 'zone' THEN g.scope_id
            WHEN g.ward_id IS NOT NULL THEN w.zone_id
            ELSE NULL
        END
        FROM wards w
        WHERE g.ward_id = w.id
           OR g.scope_type = 'zone'
        """
    )


def downgrade() -> None:
    op.drop_index("ix_geofences_for_hierarchy", table_name="geofences")
    op.drop_index("ix_geofences_route_id", table_name="geofences")
    op.drop_index("ix_geofences_zone_id", table_name="geofences")
    op.drop_constraint("fk_geofences_route_id", "geofences", type_="foreignkey")
    op.drop_constraint("fk_geofences_zone_id", "geofences", type_="foreignkey")
    op.drop_constraint("ck_geofences_geofence_for", "geofences", type_="check")
    op.drop_column("geofences", "route_id")
    op.drop_column("geofences", "zone_id")
    op.drop_column("geofences", "geofence_for")
