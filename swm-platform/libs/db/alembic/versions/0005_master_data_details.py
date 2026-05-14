"""expand contractor ward route master data

Revision ID: 0005_master_data_details
Revises: 0004_vehicle_master
Create Date: 2026-05-04 01:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_master_data_details"
down_revision: str | None = "0004_vehicle_master"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("contractors", sa.Column("contractor_code", sa.String(length=24), nullable=False))
    op.add_column("contractors", sa.Column("contact", sa.String(length=255), nullable=True))
    op.add_column(
        "contractors",
        sa.Column(
            "sla_details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_unique_constraint("uq_contractors_contractor_code", "contractors", ["contractor_code"])
    op.create_index("ix_contractors_contractor_name", "contractors", ["contractor_name"])

    op.add_column("wards", sa.Column("ward_code", sa.String(length=24), nullable=False))
    op.add_column("wards", sa.Column("zone_name", sa.String(length=128), nullable=False, server_default="UNKNOWN"))
    op.create_unique_constraint("uq_wards_ward_code", "wards", ["ward_code"])
    op.create_index("ix_wards_zone_name", "wards", ["zone_name"])

    op.add_column("routes", sa.Column("route_code", sa.String(length=24), nullable=False))
    op.add_column(
        "routes",
        sa.Column(
            "expected_distance_km",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "routes",
        sa.Column(
            "expected_duration_min",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "routes",
        sa.Column(
            "start_point",
            sa.String(length=255),
            nullable=False,
            server_default="UNKNOWN",
        ),
    )
    op.add_column(
        "routes",
        sa.Column(
            "end_point",
            sa.String(length=255),
            nullable=False,
            server_default="UNKNOWN",
        ),
    )
    op.create_unique_constraint("uq_routes_route_code", "routes", ["route_code"])
    op.create_index("ix_routes_active", "routes", ["active"])


def downgrade() -> None:
    op.drop_index("ix_routes_active", table_name="routes")
    op.drop_constraint("uq_routes_route_code", "routes", type_="unique")
    op.drop_column("routes", "end_point")
    op.drop_column("routes", "start_point")
    op.drop_column("routes", "expected_duration_min")
    op.drop_column("routes", "expected_distance_km")
    op.drop_column("routes", "route_code")

    op.drop_index("ix_wards_zone_name", table_name="wards")
    op.drop_constraint("uq_wards_ward_code", "wards", type_="unique")
    op.drop_column("wards", "zone_name")
    op.drop_column("wards", "ward_code")

    op.drop_index("ix_contractors_contractor_name", table_name="contractors")
    op.drop_constraint("uq_contractors_contractor_code", "contractors", type_="unique")
    op.drop_column("contractors", "sla_details")
    op.drop_column("contractors", "contact")
    op.drop_column("contractors", "contractor_code")
