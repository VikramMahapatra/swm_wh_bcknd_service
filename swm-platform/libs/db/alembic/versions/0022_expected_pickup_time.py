"""add expected_pickup_time to pickup_points

Revision ID: 0022_expected_pickup_time
Revises: 0021_pickup_point_crossings
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa

revision = "0022_expected_pickup_time"
down_revision = "0021_pickup_point_crossings"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('pickup_points', sa.Column('expected_pickup_time', sa.String(), nullable=True))

def downgrade():
    op.drop_column('pickup_points', 'expected_pickup_time')
