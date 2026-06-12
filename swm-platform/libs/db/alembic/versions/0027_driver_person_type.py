"""add person type to drivers

Revision ID: 0027_driver_person_type
Revises: 0026_extend_waste_materials
Create Date: 2026-06-04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0027_driver_person_type"
down_revision = "0026_extend_waste_materials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "drivers",
        sa.Column("person_type", sa.String(length=24), nullable=False, server_default=sa.text("'driver'")),
    )
    op.create_check_constraint(
        "ck_drivers_person_type",
        "drivers",
        "person_type IN ('driver','helper','ic_member')",
    )
    op.create_index("ix_drivers_person_type", "drivers", ["person_type"])


def downgrade() -> None:
    op.drop_index("ix_drivers_person_type", table_name="drivers")
    op.drop_constraint("ck_drivers_person_type", "drivers", type_="check")
    op.drop_column("drivers", "person_type")
