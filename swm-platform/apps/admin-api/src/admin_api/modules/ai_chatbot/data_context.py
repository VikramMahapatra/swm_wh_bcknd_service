"""
Builds a small, structured snapshot of live operational data from Postgres.

Intentionally simple and read-only: it exists so the "reporting" chat mode can
ground its answers in real numbers instead of the model guessing.
"""
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from swm_db import AlertORM, AnalyticsVehicleStateORM, VehicleORM


async def build_operations_snapshot(session: AsyncSession) -> dict:
    total_vehicles = int((await session.execute(select(func.count()).select_from(VehicleORM))).scalar_one())
    active_vehicles = int(
        (await session.execute(select(func.count()).select_from(VehicleORM).where(VehicleORM.active.is_(True)))).scalar_one()
    )

    status_rows = (
        await session.execute(
            select(VehicleORM.operational_status, func.count()).group_by(VehicleORM.operational_status)
        )
    ).all()
    status_breakdown = {status: count for status, count in status_rows}

    state_join = or_(
        cast(VehicleORM.id, String) == AnalyticsVehicleStateORM.vehicle_id,
        VehicleORM.vehicle_number == AnalyticsVehicleStateORM.vehicle_id,
    )
    moving_now = int(
        (
            await session.execute(
                select(func.count())
                .select_from(AnalyticsVehicleStateORM)
                .join(VehicleORM, state_join)
                .where(AnalyticsVehicleStateORM.last_ignition.is_(True), AnalyticsVehicleStateORM.last_speed_kph > 3)
            )
        ).scalar_one()
    )
    idle_now = int(
        (
            await session.execute(
                select(func.count())
                .select_from(AnalyticsVehicleStateORM)
                .join(VehicleORM, state_join)
                .where(AnalyticsVehicleStateORM.last_ignition.is_(True), AnalyticsVehicleStateORM.last_speed_kph <= 3)
            )
        ).scalar_one()
    )

    alert_status_rows = (
        await session.execute(select(AlertORM.status, func.count()).group_by(AlertORM.status))
    ).all()
    alert_severity_rows = (
        await session.execute(
            select(AlertORM.severity, func.count())
            .where(AlertORM.status.in_(["open", "acknowledged", "escalated"]))
            .group_by(AlertORM.severity)
        )
    ).all()

    recent_alerts_rows = (
        await session.execute(
            select(AlertORM)
            .where(AlertORM.status.in_(["open", "acknowledged", "escalated"]))
            .order_by(AlertORM.triggered_at.desc())
            .limit(5)
        )
    ).scalars().all()

    return {
        "fleet": {
            "total_vehicles": total_vehicles,
            "active_vehicles": active_vehicles,
            "inactive_vehicles": max(total_vehicles - active_vehicles, 0),
            "moving_now": moving_now,
            "idle_now": idle_now,
            "operational_status_breakdown": dict(status_breakdown),
        },
        "alerts": {
            "by_status": dict(alert_status_rows),
            "open_by_severity": dict(alert_severity_rows),
            "recent": [
                {
                    "title": a.title,
                    "category": a.category,
                    "severity": a.severity,
                    "status": a.status,
                    "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
                }
                for a in recent_alerts_rows
            ],
        },
    }
