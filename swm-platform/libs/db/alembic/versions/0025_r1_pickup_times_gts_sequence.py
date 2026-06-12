"""assign logical R1 pickup timings

Revision ID: 0025_r1_pickup_times
Revises: 0024_gts_dump_master
Create Date: 2026-06-02
"""

from __future__ import annotations

import math
from datetime import time

from alembic import op
import sqlalchemy as sa


revision = "0025_r1_pickup_times"
down_revision = "0024_gts_dump_master"
branch_labels = None
depends_on = None


def _distance_km(prev: tuple[float | None, float | None] | None, current: tuple[float | None, float | None]) -> float:
    if prev is None or prev[0] is None or prev[1] is None or current[0] is None or current[1] is None:
        return 0.0
    lat1, lng1 = float(prev[0]), float(prev[1])
    lat2, lng2 = float(current[0]), float(current[1])
    radius_km = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lng / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _format_time(minutes_from_midnight: int) -> str:
    hours = (minutes_from_midnight // 60) % 24
    minutes = minutes_from_midnight % 60
    return time(hour=hours, minute=minutes).strftime("%H:%M")


def upgrade():
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT pp.id, pp.lat, pp.lng, COALESCE(pp.is_gts, false) AS is_gts, pp.sequence_no
            FROM pickup_points pp
            JOIN routes r ON r.id = pp.route_id
            LEFT JOIN wards w ON w.id = COALESCE(pp.ward_id, r.ward_id)
            WHERE lower(r.route_name) = lower('R1')
              AND (w.ward_code IS NULL OR lower(w.ward_code) = lower('W1') OR lower(w.ward_name) = lower('W1'))
            ORDER BY COALESCE(pp.is_gts, false), pp.sequence_no, pp.created_at, pp.id
            """
        )
    ).mappings().all()

    if not rows:
        return

    current_minutes = 6 * 60
    previous: tuple[float | None, float | None] | None = None

    for index, row in enumerate(rows, start=1):
        if index == 1:
            current_minutes = 6 * 60
        else:
            distance_minutes = int(round((_distance_km(previous, (row["lat"], row["lng"])) / 14.0) * 60))
            variation_minutes = [3, 6, 2, 7, 4][(index - 2) % 5]
            stop_buffer_minutes = 5 if not row["is_gts"] else 8
            current_minutes += max(7, min(18, distance_minutes + stop_buffer_minutes + variation_minutes))

        bind.execute(
            sa.text(
                """
                UPDATE pickup_points
                SET sequence_no = :sequence_no,
                    expected_pickup_time = :expected_pickup_time,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "sequence_no": index,
                "expected_pickup_time": _format_time(current_minutes),
            },
        )
        previous = (row["lat"], row["lng"])


def downgrade():
    # This migration updates operational schedule data. Previous timings are
    # intentionally not restored because they were inconsistent demo data.
    pass
