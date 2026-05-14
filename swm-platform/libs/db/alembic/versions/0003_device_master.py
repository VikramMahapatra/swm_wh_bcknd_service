"""add device master table

Revision ID: 0003_device_master
Revises: 0002_vendor_master
Create Date: 2026-05-04 00:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_device_master"
down_revision: str | None = "0002_vendor_master"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("imei", sa.String(length=17), nullable=False),
        sa.Column("serial_no", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("manufacturer", sa.String(length=128), nullable=True),
        sa.Column("firmware_version", sa.String(length=64), nullable=True),
        sa.Column("sim_number", sa.String(length=32), nullable=True),
        sa.Column("installed_on", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_on", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("battery_percent", sa.Float(), nullable=True),
        sa.Column("signal_strength", sa.Float(), nullable=True),
        sa.Column("health_status", sa.String(length=16), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(
            "health_status IN ('healthy','warning','critical','offline')",
            name="ck_devices_health_status",
        ),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], name="fk_devices_vendor_id_vendors", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_devices"),
    )
    op.create_index("ix_devices_imei", "devices", ["imei"], unique=True)
    op.create_index("ix_devices_vendor_id", "devices", ["vendor_id"])
    op.create_index("ix_devices_active", "devices", ["active"])
    op.create_index("ix_devices_last_seen", "devices", ["last_seen"])


def downgrade() -> None:
    op.drop_index("ix_devices_last_seen", table_name="devices")
    op.drop_index("ix_devices_active", table_name="devices")
    op.drop_index("ix_devices_vendor_id", table_name="devices")
    op.drop_index("ix_devices_imei", table_name="devices")
    op.drop_table("devices")
