"""add ward population area total_pickup_points fields

Revision ID: 0030_ward_extra_fields
Revises: 0029_zone_extra_fields
Create Date: 2026-06-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0030_ward_extra_fields"
down_revision = "0029_zone_extra_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("wards", sa.Column("population", sa.Integer(), nullable=True))
    op.add_column("wards", sa.Column("area", sa.Float(), nullable=True))
    op.add_column("wards", sa.Column("total_pickup_points", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("wards", "total_pickup_points")
    op.drop_column("wards", "area")
    op.drop_column("wards", "population")
