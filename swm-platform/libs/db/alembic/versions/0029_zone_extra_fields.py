"""add zone description supervisor fields

Revision ID: 0029_zone_extra_fields
Revises: 0028_route_type
Create Date: 2026-06-29
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0029_zone_extra_fields"
down_revision = "0028_route_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("zones", sa.Column("description", sa.String(length=512), nullable=True))
    op.add_column("zones", sa.Column("supervisor_name", sa.String(length=255), nullable=True))
    op.add_column("zones", sa.Column("supervisor_phone", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("zones", "supervisor_phone")
    op.drop_column("zones", "supervisor_name")
    op.drop_column("zones", "description")
