"""add tickets and ticket comments

Revision ID: 0012_tickets_module
Revises: 0011_driver_gtc_pickup_points
Create Date: 2026-05-22 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_tickets_module"
down_revision: str | None = "0011_driver_gtc_pickup_points"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=4000), nullable=True),
        sa.Column("category", sa.String(length=32), nullable=False, server_default=sa.text("'complaint'")),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default=sa.text("'medium'")),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'open'")),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_to", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("related_alert_id", sa.String(length=128), nullable=True),
        sa.Column("related_truck_id", sa.String(length=128), nullable=True),
        sa.Column("related_driver_id", sa.String(length=128), nullable=True),
        sa.Column("escalation_level", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("sla_breached", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("status IN ('open','in_progress','pending','resolved','closed')", name="ck_tickets_status"),
        sa.CheckConstraint("priority IN ('low','medium','high','critical')", name="ck_tickets_priority"),
        sa.CheckConstraint(
            "category IN ('complaint','maintenance','driver_issue','vehicle_issue','route_issue','pickup_issue','other')",
            name="ck_tickets_category",
        ),
        sa.CheckConstraint("escalation_level >= 0", name="ck_tickets_escalation_non_negative"),
        sa.PrimaryKeyConstraint("id", name="pk_tickets"),
    )
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index("ix_tickets_priority", "tickets", ["priority"])
    op.create_index("ix_tickets_category", "tickets", ["category"])
    op.create_index("ix_tickets_created_at", "tickets", ["created_at"])

    op.create_table(
        "ticket_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("content", sa.String(length=4000), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], name="fk_ticket_comments_ticket_id_tickets", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_ticket_comments"),
    )
    op.create_index("ix_ticket_comments_ticket_id", "ticket_comments", ["ticket_id"])
    op.create_index("ix_ticket_comments_created_at", "ticket_comments", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ticket_comments_created_at", table_name="ticket_comments")
    op.drop_index("ix_ticket_comments_ticket_id", table_name="ticket_comments")
    op.drop_table("ticket_comments")

    op.drop_index("ix_tickets_created_at", table_name="tickets")
    op.drop_index("ix_tickets_category", table_name="tickets")
    op.drop_index("ix_tickets_priority", table_name="tickets")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_table("tickets")
