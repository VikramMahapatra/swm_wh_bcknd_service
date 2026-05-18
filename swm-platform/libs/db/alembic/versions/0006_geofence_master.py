"""add geofence master with postgis support

Revision ID: 0006_geofence_master
Revises: 0005_master_data_details
Create Date: 2026-05-04 02:00:00
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_geofence_master"
down_revision: str | None = "0005_master_data_details"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    postgis_available = bool(
        bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'postgis')")).scalar()
    )
    postgis_enabled = False
    if postgis_available:
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        postgis_enabled = True

    constraints: list[Any] = [
        sa.CheckConstraint(
            "type IN ('depot','landfill','zone','parking','maintenance')",
            name="ck_geofences_type",
        ),
        sa.CheckConstraint(
            "geometry_type IN ('circle','polygon')",
            name="ck_geofences_geometry_type",
        ),
        sa.CheckConstraint(
            "center_lat IS NULL OR (center_lat >= -90 AND center_lat <= 90)",
            name="ck_geofences_center_lat_range",
        ),
        sa.CheckConstraint(
            "center_lng IS NULL OR (center_lng >= -180 AND center_lng <= 180)",
            name="ck_geofences_center_lng_range",
        ),
        sa.CheckConstraint(
            "radius_meter IS NULL OR radius_meter > 0",
            name="ck_geofences_radius_positive",
        ),
        sa.CheckConstraint(
            "(geometry_type <> 'circle') OR "
            "(center_lat IS NOT NULL AND center_lng IS NOT NULL AND radius_meter IS NOT NULL AND polygon IS NULL)",
            name="ck_geofences_circle_fields",
        ),
        sa.CheckConstraint(
            "(geometry_type <> 'polygon') OR "
            "(polygon IS NOT NULL AND center_lat IS NULL AND center_lng IS NULL AND radius_meter IS NULL)",
            name="ck_geofences_polygon_fields",
        ),
    ]
    if postgis_enabled:
        constraints.append(
            sa.CheckConstraint(
                "polygon IS NULL OR ST_IsValid(ST_SetSRID(ST_GeomFromGeoJSON(polygon::text), 4326))",
                name="ck_geofences_polygon_valid",
            )
        )

    op.create_table(
        "geofences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("geofence_code", sa.String(length=32), nullable=False),
        sa.Column("geofence_name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("geometry_type", sa.String(length=16), nullable=False),
        sa.Column("center_lat", sa.Float(), nullable=True),
        sa.Column("center_lng", sa.Float(), nullable=True),
        sa.Column("radius_meter", sa.Float(), nullable=True),
        sa.Column("polygon", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ward_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(
            ["ward_id"],
            ["wards.id"],
            name="fk_geofences_ward_id_wards",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_geofences"),
        sa.UniqueConstraint("geofence_code", name="uq_geofences_geofence_code"),
        *constraints,
    )

    op.create_index("ix_geofences_ward_id", "geofences", ["ward_id"])
    op.create_index("ix_geofences_active", "geofences", ["active"])

    if postgis_enabled:
        op.execute(
            """
            CREATE INDEX ix_geofences_circle_gist
            ON geofences
            USING GIST (geography(ST_SetSRID(ST_MakePoint(center_lng, center_lat), 4326)))
            WHERE geometry_type = 'circle' AND center_lat IS NOT NULL AND center_lng IS NOT NULL
            """
        )

        op.execute(
            """
            CREATE INDEX ix_geofences_polygon_gist
            ON geofences
            USING GIST (ST_SetSRID(ST_GeomFromGeoJSON(polygon::text), 4326))
            WHERE geometry_type = 'polygon' AND polygon IS NOT NULL
            """
        )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_geofences_polygon_gist")
    op.execute("DROP INDEX IF EXISTS ix_geofences_circle_gist")
    op.drop_index("ix_geofences_active", table_name="geofences")
    op.drop_index("ix_geofences_ward_id", table_name="geofences")
    op.drop_table("geofences")
