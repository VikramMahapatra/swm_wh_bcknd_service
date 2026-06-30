"""add route type

Revision ID: 0028_route_type
Revises: 0027_driver_person_type
Create Date: 2026-06-29
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0028_route_type"
down_revision = "0027_driver_person_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "routes",
        sa.Column("route_type", sa.String(length=24), nullable=False, server_default=sa.text("'primary'")),
    )
    op.create_check_constraint(
        "ck_routes_route_type",
        "routes",
        "route_type IN ('primary','secondary')",
    )
    op.create_index("ix_routes_route_type", "routes", ["route_type"])


def downgrade() -> None:
    op.drop_index("ix_routes_route_type", table_name="routes")
    op.drop_constraint("ck_routes_route_type", "routes", type_="check")
    op.drop_column("routes", "route_type")
