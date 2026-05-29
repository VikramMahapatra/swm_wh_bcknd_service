"""replace contractors with vendors for vehicles

Revision ID: 0019_vehicle_vendor_unification
Revises: 0018_pickup_points_route_order
Create Date: 2026-05-27 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0019_vehicle_vendor_unification"
down_revision: str | None = "0018_pickup_points_route_order"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("vehicles", sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=True))

    op.execute(
        """
        UPDATE vehicles v
        SET vendor_id = vd.id
        FROM contractors c
        JOIN vendors vd ON lower(trim(vd.vendor_name)) = lower(trim(c.contractor_name))
        WHERE v.contractor_id = c.id
        """
    )

    op.execute(
        """
        UPDATE vehicles
        SET vendor_id = (SELECT id FROM vendors ORDER BY created_at ASC LIMIT 1)
        WHERE vendor_id IS NULL
        """
    )

    op.alter_column("vehicles", "vendor_id", nullable=False)

    op.drop_constraint("fk_vehicles_contractor_id_contractors", "vehicles", type_="foreignkey")
    op.drop_index("ix_vehicles_contractor_id", table_name="vehicles")

    op.create_foreign_key(
        "fk_vehicles_vendor_id_vendors",
        "vehicles",
        "vendors",
        ["vendor_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_vehicles_vendor_id", "vehicles", ["vendor_id"])

    op.drop_column("vehicles", "contractor_id")
    op.drop_table("contractors")


def downgrade() -> None:
    op.create_table(
        "contractors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contractor_code", sa.String(length=24), nullable=False),
        sa.Column("contractor_name", sa.String(length=255), nullable=False),
        sa.Column("contact", sa.String(length=255), nullable=True),
        sa.Column("sla_details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_contractors"),
        sa.UniqueConstraint("contractor_code", name="uq_contractors_contractor_code"),
    )
    op.create_index("ix_contractors_contractor_name", "contractors", ["contractor_name"])

    op.add_column("vehicles", sa.Column("contractor_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(
        """
        UPDATE vehicles
        SET contractor_id = (SELECT id FROM contractors ORDER BY created_at ASC LIMIT 1)
        WHERE contractor_id IS NULL
        """
    )
    op.alter_column("vehicles", "contractor_id", nullable=False)

    op.drop_constraint("fk_vehicles_vendor_id_vendors", "vehicles", type_="foreignkey")
    op.drop_index("ix_vehicles_vendor_id", table_name="vehicles")

    op.create_foreign_key(
        "fk_vehicles_contractor_id_contractors",
        "vehicles",
        "contractors",
        ["contractor_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_vehicles_contractor_id", "vehicles", ["contractor_id"])

    op.drop_column("vehicles", "vendor_id")
