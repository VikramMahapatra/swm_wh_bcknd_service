"""Extend supported waste material types.

Revision ID: 0026_extend_waste_materials
Revises: 0025_r1_pickup_times
Create Date: 2026-06-03
"""

from alembic import op


revision = "0026_extend_waste_materials"
down_revision = "0025_r1_pickup_times"
branch_labels = None
depends_on = None


OLD_TYPES = "'chicken_waste','dry_waste','green_waste','mandai','mix_waste','wet_waste'"
NEW_TYPES = (
    "'chicken_waste','biomedical_waste','construction_waste','dry_waste',"
    "'green_waste','mandai','mix_waste','mixed_waste','plastic_waste','wet_waste'"
)


def upgrade() -> None:
    op.drop_constraint("ck_vehicles_secondary_waste_type", "vehicles", type_="check")
    op.create_check_constraint(
        "ck_vehicles_secondary_waste_type",
        "vehicles",
        f"secondary_waste_type IS NULL OR secondary_waste_type IN ({NEW_TYPES})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_vehicles_secondary_waste_type", "vehicles", type_="check")
    op.execute("UPDATE vehicles SET secondary_waste_type = NULL WHERE secondary_waste_type NOT IN (" + OLD_TYPES + ")")
    op.create_check_constraint(
        "ck_vehicles_secondary_waste_type",
        "vehicles",
        f"secondary_waste_type IS NULL OR secondary_waste_type IN ({OLD_TYPES})",
    )
