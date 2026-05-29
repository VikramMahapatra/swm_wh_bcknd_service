"""rename alert contractor_id to vendor_id

Revision ID: 0020_alert_vendor_column
Revises: 0019_vehicle_vendor_unification
Create Date: 2026-05-27 00:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0020_alert_vendor_column"
down_revision: str | None = "0019_vehicle_vendor_unification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("alerts") as batch_op:
        batch_op.alter_column("contractor_id", new_column_name="vendor_id")


def downgrade() -> None:
    with op.batch_alter_table("alerts") as batch_op:
        batch_op.alter_column("vendor_id", new_column_name="contractor_id")
