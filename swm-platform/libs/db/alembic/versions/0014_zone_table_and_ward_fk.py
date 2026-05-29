"""
Revision ID: 0014_zone_table_and_ward_fk
Revises: 0013_ensure_drivers_table
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '0014_zone_table_and_ward_fk'
down_revision = '0013_ensure_drivers_table'
branch_labels = None
depends_on = None

def upgrade():
    # Create zones table
    op.create_table(
        'zones',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False),
        sa.Column('zone_code', sa.String(length=24), nullable=False, unique=True),
        sa.Column('zone_name', sa.String(length=255), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_zones_code', 'zones', ['zone_code'], unique=True)
    op.create_index('ix_zones_active', 'zones', ['active'])

    # Add zone_id to wards, drop zone_name
    op.add_column('wards', sa.Column('zone_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_wards_zone_id', 'wards', 'zones', ['zone_id'], ['id'], ondelete='RESTRICT')

    # Data migration: create zones from unique zone_name in wards
    connection = op.get_bind()
    wards = connection.execute(sa.text('SELECT DISTINCT zone_name FROM wards')).fetchall()
    zone_map = {}
    for (zone_name,) in wards:
        if not zone_name:
            continue
        zone_code = zone_name.strip().upper().replace(' ', '_')[:24]
        result = connection.execute(sa.text('INSERT INTO zones (id, zone_code, zone_name, active) VALUES (:id, :code, :name, true) RETURNING id'), {
            'id': str(uuid.uuid4()),
            'code': zone_code,
            'name': zone_name.strip()
        })
        zone_id = result.fetchone()[0]
        zone_map[zone_name] = zone_id
    # Update wards to reference new zone_id
    for zone_name, zone_id in zone_map.items():
        connection.execute(sa.text('UPDATE wards SET zone_id = :zone_id WHERE zone_name = :zone_name'), {
            'zone_id': zone_id,
            'zone_name': zone_name
        })
    # Make zone_id non-nullable
    op.alter_column('wards', 'zone_id', nullable=False)
    # Drop old zone_name column and index
    op.drop_index('ix_wards_zone_name', table_name='wards')
    op.drop_column('wards', 'zone_name')

def downgrade():
    # Add zone_name back to wards
    op.add_column('wards', sa.Column('zone_name', sa.String(length=128), nullable=False, server_default='UNKNOWN'))
    # Data migration: fill zone_name from zones
    connection = op.get_bind()
    wards = connection.execute(sa.text('SELECT id, zone_id FROM wards')).fetchall()
    for ward_id, zone_id in wards:
        zone = connection.execute(sa.text('SELECT zone_name FROM zones WHERE id = :id'), {'id': zone_id}).fetchone()
        zone_name = zone[0] if zone else 'UNKNOWN'
        connection.execute(sa.text('UPDATE wards SET zone_name = :zone_name WHERE id = :id'), {'zone_name': zone_name, 'id': ward_id})
    op.create_index('ix_wards_zone_name', 'wards', ['zone_name'])
    # Remove zone_id and FK
    op.drop_constraint('fk_wards_zone_id', 'wards', type_='foreignkey')
    op.drop_column('wards', 'zone_id')
    # Drop zones table
    op.drop_index('ix_zones_code', table_name='zones')
    op.drop_index('ix_zones_active', table_name='zones')
    op.drop_table('zones')
