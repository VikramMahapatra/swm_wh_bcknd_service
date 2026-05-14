"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-02 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "device_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("speed_kph", sa.Float(), nullable=False),
        sa.Column("heading", sa.Integer(), nullable=False),
        sa.Column("ignition", sa.Boolean(), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
    )
    op.create_index("ix_device_events_device_id", "device_events", ["device_id"])
    op.create_index("ix_device_events_ts", "device_events", ["ts"])


def downgrade() -> None:
    op.drop_index("ix_device_events_ts", table_name="device_events")
    op.drop_index("ix_device_events_device_id", table_name="device_events")
    op.drop_table("device_events")
