"""ensure drivers table exists

Revision ID: 0013_ensure_drivers_table
Revises: 0012_tickets_module
Create Date: 2026-05-23 20:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0013_ensure_drivers_table"
down_revision: str | None = "0012_tickets_module"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("drivers"):
        op.create_table(
            "drivers",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("phone", sa.String(length=32), nullable=True),
            sa.Column("license_number", sa.String(length=64), nullable=True),
            sa.Column("license_expiry", sa.Date(), nullable=True),
            sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("assigned_vehicle_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.PrimaryKeyConstraint("id", name="pk_drivers"),
        )
        op.create_index("ix_drivers_name", "drivers", ["name"])
        op.create_index("ix_drivers_vendor_id", "drivers", ["vendor_id"])
        op.create_index("ix_drivers_active", "drivers", ["active"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("drivers"):
        op.drop_index("ix_drivers_active", table_name="drivers")
        op.drop_index("ix_drivers_vendor_id", table_name="drivers")
        op.drop_index("ix_drivers_name", table_name="drivers")
        op.drop_table("drivers")
