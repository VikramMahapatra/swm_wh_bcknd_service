"""add vendor master table

Revision ID: 0002_vendor_master
Revises: 0001_initial
Create Date: 2026-05-04 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_vendor_master"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vendors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vendor_code", sa.String(length=32), nullable=False),
        sa.Column("vendor_name", sa.String(length=255), nullable=False),
        sa.Column("contact_person", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("webhook_secret", sa.String(length=255), nullable=True),
        sa.Column("signature_key", sa.String(length=255), nullable=True),
        sa.Column("allowed_ips", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("auth_type", sa.String(length=16), nullable=False),
        sa.Column("callback_format", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("auth_type IN ('header','signature','ip')", name="ck_vendors_auth_type"),
        sa.PrimaryKeyConstraint("id", name="pk_vendors"),
        sa.UniqueConstraint("vendor_code", name="uq_vendors_vendor_code"),
    )
    op.create_index("ix_vendors_vendor_name", "vendors", ["vendor_name"])
    op.create_index("ix_vendors_email", "vendors", ["email"])
    op.create_index("ix_vendors_active", "vendors", ["active"])


def downgrade() -> None:
    op.drop_index("ix_vendors_active", table_name="vendors")
    op.drop_index("ix_vendors_email", table_name="vendors")
    op.drop_index("ix_vendors_vendor_name", table_name="vendors")
    op.drop_table("vendors")
