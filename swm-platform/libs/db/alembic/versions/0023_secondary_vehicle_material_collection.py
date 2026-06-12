"""secondary vehicle material collection

Revision ID: 0023_secondary_vehicle
Revises: 0022_expected_pickup_time
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0023_secondary_vehicle"
down_revision = "0022_expected_pickup_time"
branch_labels = None
depends_on = None


SECONDARY_WASTE_TYPES = (
    "chicken_waste",
    "dry_waste",
    "green_waste",
    "mandai",
    "mix_waste",
    "wet_waste",
)


def upgrade():
    op.add_column(
        "vehicles",
        sa.Column("vehicle_category", sa.String(length=16), nullable=False, server_default="primary"),
    )
    op.add_column("vehicles", sa.Column("secondary_waste_type", sa.String(length=32), nullable=True))
    op.create_check_constraint(
        "ck_vehicles_vehicle_category",
        "vehicles",
        "vehicle_category IN ('primary','secondary')",
    )
    op.create_check_constraint(
        "ck_vehicles_secondary_waste_type",
        "vehicles",
        "secondary_waste_type IS NULL OR secondary_waste_type IN ('chicken_waste','dry_waste','green_waste','mandai','mix_waste','wet_waste')",
    )

    op.create_table(
        "dump_yards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("dump_yard_code", sa.String(length=32), nullable=False),
        sa.Column("dump_yard_name", sa.String(length=255), nullable=False),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ward_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ward_id"], ["wards.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dump_yard_code"),
    )
    op.create_index("ix_dump_yards_zone_id", "dump_yards", ["zone_id"])
    op.create_index("ix_dump_yards_active", "dump_yards", ["active"])

    op.create_table(
        "secondary_vehicle_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gtc_pickup_point_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dump_yard_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_type", sa.String(length=32), nullable=False),
        sa.Column("assigned_from", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("assigned_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("remarks", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["gtc_pickup_point_id"], ["pickup_points.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["dump_yard_id"], ["dump_yards.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_secondary_vehicle_assignments_vehicle", "secondary_vehicle_assignments", ["vehicle_id", "active"])
    op.create_index("ix_secondary_vehicle_assignments_gtc", "secondary_vehicle_assignments", ["gtc_pickup_point_id"])
    op.create_index("ix_secondary_vehicle_assignments_dump_yard", "secondary_vehicle_assignments", ["dump_yard_id"])

    op.create_table(
        "dump_yard_weighments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gtc_pickup_point_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dump_yard_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_type", sa.String(length=32), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("entry_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("gross_weight_kg", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tare_weight_kg", sa.Float(), nullable=False, server_default="0"),
        sa.Column("net_weight_kg", sa.Float(), nullable=False, server_default="0"),
        sa.Column("slip_number", sa.String(length=64), nullable=True),
        sa.Column("operator_name", sa.String(length=255), nullable=True),
        sa.Column("remarks", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["assignment_id"], ["secondary_vehicle_assignments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["gtc_pickup_point_id"], ["pickup_points.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["dump_yard_id"], ["dump_yards.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dump_yard_weighments_service_date", "dump_yard_weighments", ["service_date"])
    op.create_index("ix_dump_yard_weighments_vehicle_date", "dump_yard_weighments", ["vehicle_id", "service_date"])
    op.create_index("ix_dump_yard_weighments_material", "dump_yard_weighments", ["material_type"])

    # Existing records are explicitly marked Primary. Sample Secondary records are seeded
    # only when master vendor/ward/pickup-point data exists.
    op.execute("UPDATE vehicles SET vehicle_category = 'primary' WHERE vehicle_category IS NULL")
    op.execute(
        """
        INSERT INTO dump_yards (dump_yard_code, dump_yard_name, zone_id, ward_id, lat, lng, active)
        SELECT 'DY-AZ-001', 'A Zone Dump Yard', z.id, w.id, pp.lat, pp.lng, true
        FROM zones z
        JOIN wards w ON w.zone_id = z.id
        LEFT JOIN pickup_points pp ON pp.zone_id = z.id
        WHERE NOT EXISTS (SELECT 1 FROM dump_yards WHERE dump_yard_code = 'DY-AZ-001')
        ORDER BY z.zone_code, w.ward_code, pp.sequence_no NULLS LAST
        LIMIT 1
        """
    )
    for index, material in enumerate(SECONDARY_WASTE_TYPES, start=1):
        vehicle_no = f"SEC-{index:02d}"
        reg_no = f"SEC-AZ-{index:02d}"
        op.execute(
            f"""
            INSERT INTO vehicles (
                id, vehicle_number, registration_number, vehicle_category, secondary_waste_type,
                truck_type, capacity_kg, capacity_cubic_meter, vendor_id, ward_id, route_id,
                fuel_type, operational_status, active, metadata
            )
            SELECT
                gen_random_uuid(), '{vehicle_no}', '{reg_no}', 'secondary', '{material}',
                'secondary-collection', 1500, 4, v.id, w.id, NULL,
                'diesel', 'operational', true, '{{"seeded": true, "secondary_material": "{material}"}}'::jsonb
            FROM vendors v
            CROSS JOIN wards w
            WHERE NOT EXISTS (SELECT 1 FROM vehicles WHERE vehicle_number = '{vehicle_no}')
            ORDER BY v.created_at, w.ward_code
            LIMIT 1
            """
        )
        op.execute(
            f"""
            INSERT INTO secondary_vehicle_assignments (vehicle_id, gtc_pickup_point_id, dump_yard_id, material_type, remarks, active)
            SELECT veh.id, pp.id, dy.id, '{material}', 'Seed assignment for {material.replace("_", " ")}', true
            FROM vehicles veh
            CROSS JOIN pickup_points pp
            CROSS JOIN dump_yards dy
            WHERE veh.vehicle_number = '{vehicle_no}'
              AND NOT EXISTS (
                SELECT 1 FROM secondary_vehicle_assignments a
                WHERE a.vehicle_id = veh.id AND a.material_type = '{material}' AND a.active = true
              )
            ORDER BY pp.sequence_no NULLS LAST, pp.created_at
            LIMIT 1
            """
        )


def downgrade():
    op.drop_index("ix_dump_yard_weighments_material", table_name="dump_yard_weighments")
    op.drop_index("ix_dump_yard_weighments_vehicle_date", table_name="dump_yard_weighments")
    op.drop_index("ix_dump_yard_weighments_service_date", table_name="dump_yard_weighments")
    op.drop_table("dump_yard_weighments")

    op.drop_index("ix_secondary_vehicle_assignments_dump_yard", table_name="secondary_vehicle_assignments")
    op.drop_index("ix_secondary_vehicle_assignments_gtc", table_name="secondary_vehicle_assignments")
    op.drop_index("ix_secondary_vehicle_assignments_vehicle", table_name="secondary_vehicle_assignments")
    op.drop_table("secondary_vehicle_assignments")

    op.drop_index("ix_dump_yards_active", table_name="dump_yards")
    op.drop_index("ix_dump_yards_zone_id", table_name="dump_yards")
    op.drop_table("dump_yards")

    op.drop_constraint("ck_vehicles_secondary_waste_type", "vehicles", type_="check")
    op.drop_constraint("ck_vehicles_vehicle_category", "vehicles", type_="check")
    op.drop_column("vehicles", "secondary_waste_type")
    op.drop_column("vehicles", "vehicle_category")
