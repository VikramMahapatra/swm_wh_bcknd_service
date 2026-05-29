"""add geofence scope fields for ward/zone

Revision ID: 0015_geofence_scope_fields
Revises: 0014_zone_table_and_ward_fk
Create Date: 2026-05-25 14:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_geofence_scope_fields"
down_revision: str | None = "0014_zone_table_and_ward_fk"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "geofences",
        sa.Column("scope_type", sa.String(length=16), nullable=False, server_default=sa.text("'ward'")),
    )
    op.add_column("geofences", sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_check_constraint(
        "ck_geofences_scope_type",
        "geofences",
        "scope_type IN ('ward','zone')",
    )
    op.create_index("ix_geofences_scope", "geofences", ["scope_type", "scope_id"])

    op.execute(
        "UPDATE geofences SET scope_type='ward', scope_id=ward_id WHERE ward_id IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_geofences_scope", table_name="geofences")
    op.drop_constraint("ck_geofences_scope_type", "geofences", type_="check")
    op.drop_column("geofences", "scope_id")
    op.drop_column("geofences", "scope_type")
