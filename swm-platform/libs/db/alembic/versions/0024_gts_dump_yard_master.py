"""gts and dump yard master

Revision ID: 0024_gts_dump_master
Revises: 0023_secondary_vehicle
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0024_gts_dump_master"
down_revision = "0023_secondary_vehicle"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("dump_yards", sa.Column("address", sa.String(length=1000), nullable=True))
    op.add_column("dump_yards", sa.Column("capacity", sa.Float(), nullable=True))

    op.create_table(
        "gts_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("address", sa.String(length=1000), nullable=True),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ward_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ward_id"], ["wards.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gts_points_ward_id", "gts_points", ["ward_id"])
    op.create_index("ix_gts_points_active", "gts_points", ["active"])
    op.create_index("ix_gts_points_ward_name", "gts_points", ["ward_id", "name"], unique=True)

    op.add_column("pickup_points", sa.Column("is_gts", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("pickup_points", sa.Column("gts_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_pickup_points_gts_id", "pickup_points", "gts_points", ["gts_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_pickup_points_gts_id", "pickup_points", ["gts_id"])
    op.create_index("ix_pickup_points_is_gts", "pickup_points", ["is_gts"])

    op.execute(
        """
        INSERT INTO dump_yards (id, dump_yard_code, dump_yard_name, address, zone_id, ward_id, lat, lng, active)
        SELECT gen_random_uuid(), 'DY-MUNSHI', 'Munshi Dump Yard', 'Munshi Dump Yard',
               z.id, w.id, pp.lat, pp.lng, true
        FROM zones z
        LEFT JOIN wards w ON w.zone_id = z.id
        LEFT JOIN pickup_points pp ON pp.ward_id = w.id
        WHERE NOT EXISTS (
            SELECT 1 FROM dump_yards WHERE lower(dump_yard_name) = lower('Munshi Dump Yard')
        )
        ORDER BY z.zone_code, w.ward_code, pp.sequence_no NULLS LAST
        LIMIT 1
        """
    )

    op.execute(
        """
        INSERT INTO gts_points (id, name, latitude, longitude, address, zone_id, ward_id, active)
        SELECT gen_random_uuid(),
               'Dehu Road Garbage Collection Center',
               pp.lat,
               pp.lng,
               'Dehu Road Garbage Collection Center',
               COALESCE(pp.zone_id, r.zone_id, w.zone_id),
               COALESCE(pp.ward_id, r.ward_id, w.id),
               true
        FROM pickup_points pp
        LEFT JOIN routes r ON r.id = pp.route_id
        LEFT JOIN wards w ON w.id = COALESCE(pp.ward_id, r.ward_id)
        WHERE pp.id = '79a2bdf8-d731-4fe0-8e4a-daa510aa22a0'
          AND NOT EXISTS (
              SELECT 1 FROM gts_points g
              WHERE lower(g.name) = lower('Dehu Road Garbage Collection Center')
                AND g.ward_id IS NOT DISTINCT FROM COALESCE(pp.ward_id, r.ward_id, w.id)
          )
        LIMIT 1
        """
    )

    op.execute(
        """
        UPDATE pickup_points pp
        SET pickup_name = 'Dehu Road Garbage Collection Center',
            is_gts = true,
            gts_id = g.id,
            sequence_no = COALESCE((
                SELECT MAX(p2.sequence_no) + 1
                FROM pickup_points p2
                WHERE p2.route_id = pp.route_id
                  AND p2.id <> pp.id
            ), pp.sequence_no)
        FROM gts_points g
        WHERE pp.id = '79a2bdf8-d731-4fe0-8e4a-daa510aa22a0'
          AND lower(g.name) = lower('Dehu Road Garbage Collection Center')
          AND g.ward_id IS NOT DISTINCT FROM pp.ward_id
        """
    )

    # Fallback for R1/W1 if the specific pickup point is not present in a fresh/demo DB.
    op.execute(
        """
        INSERT INTO gts_points (id, name, latitude, longitude, address, zone_id, ward_id, active)
        SELECT gen_random_uuid(), 'Dehu Road Garbage Collection Center',
               pp.lat, pp.lng, 'Dehu Road Garbage Collection Center',
               r.zone_id, r.ward_id, true
        FROM routes r
        JOIN wards w ON w.id = r.ward_id
        LEFT JOIN pickup_points pp ON pp.route_id = r.id
        WHERE lower(r.route_name) = lower('R1')
          AND (lower(w.ward_code) = lower('W1') OR lower(w.ward_name) = lower('W1'))
          AND NOT EXISTS (
              SELECT 1 FROM gts_points g
              WHERE lower(g.name) = lower('Dehu Road Garbage Collection Center')
                AND g.ward_id = r.ward_id
          )
        ORDER BY pp.sequence_no DESC NULLS LAST
        LIMIT 1
        """
    )


def downgrade():
    op.drop_index("ix_pickup_points_is_gts", table_name="pickup_points")
    op.drop_index("ix_pickup_points_gts_id", table_name="pickup_points")
    op.drop_constraint("fk_pickup_points_gts_id", "pickup_points", type_="foreignkey")
    op.drop_column("pickup_points", "gts_id")
    op.drop_column("pickup_points", "is_gts")

    op.drop_index("ix_gts_points_ward_name", table_name="gts_points")
    op.drop_index("ix_gts_points_active", table_name="gts_points")
    op.drop_index("ix_gts_points_ward_id", table_name="gts_points")
    op.drop_table("gts_points")

    op.drop_column("dump_yards", "capacity")
    op.drop_column("dump_yards", "address")
