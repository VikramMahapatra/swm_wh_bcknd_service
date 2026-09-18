"""
Read-only "tools" the AI can call to answer questions about any part of the
platform (fleet, alerts, zones/wards, vendors, devices, routes, pickup points,
drivers, tickets, trip/idle analytics, dump yard weighments, GTS checkpoints).

Each tool is a small async function that takes the DB session plus optional
filters and returns a plain dict. TOOL_SPECS describes them to the OpenAI API
(function-calling); execute_tool() dispatches a model-requested call to the
matching function. Add a new domain by writing one function + one spec entry.
"""
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Coroutine
from zoneinfo import ZoneInfo

from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from swm_db import (
    AlertORM,
    AnalyticsIdleRecordORM,
    AnalyticsTripRecordORM,
    AnalyticsVehicleStateORM,
    DeviceORM,
    DriverORM,
    DumpYardWeighmentORM,
    GtcCheckpointORM,
    PickupPointCrossingORM,
    PickupPointORM,
    RouteORM,
    TicketORM,
    VehicleORM,
    VendorORM,
    WardORM,
    ZoneORM,
)


def _fuzzy_match(column, value: str):
    """Punctuation- and WORD-ORDER-insensitive match: 'F Zone', 'Zone F' and 'Zone-F'
    must all match a DB value of 'Zone-F'. Requires every alphanumeric token from
    `value` to appear somewhere in the column, in any order."""
    tokens = re.findall(r"[a-zA-Z0-9]+", value)
    if not tokens:
        return column.ilike(f"%{value.strip()}%")
    return and_(*(column.ilike(f"%{token}%") for token in tokens))


# All timestamps are stored in UTC; the fleet operates in India, so surface
# times in IST (with an explicit label) instead of raw UTC to avoid users
# reading e.g. "09:46" and assuming it means 09:46 in their own timezone.
_LOCAL_TZ = ZoneInfo("Asia/Kolkata")


def _format_local(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)  # DB stores naive datetimes as UTC
    return dt.astimezone(_LOCAL_TZ).strftime("%Y-%m-%d %I:%M %p IST")


async def get_fleet_overview(
    session: AsyncSession, zone_name: str | None = None, ward_name: str | None = None, **_: Any
) -> dict:
    """Vehicle counts/breakdowns, optionally scoped to one zone and/or ward (case-insensitive, fuzzy match)."""
    vehicle_filters = []
    needs_scope_join = bool(zone_name or ward_name)
    if zone_name:
        vehicle_filters.append(_fuzzy_match(ZoneORM.zone_name, zone_name))
    if ward_name:
        vehicle_filters.append(_fuzzy_match(WardORM.ward_name, ward_name))

    def _scoped(stmt):
        if needs_scope_join:
            stmt = stmt.join(WardORM, VehicleORM.ward_id == WardORM.id).join(ZoneORM, WardORM.zone_id == ZoneORM.id).where(
                *vehicle_filters
            )
        return stmt

    total = int((await session.execute(_scoped(select(func.count()).select_from(VehicleORM)))).scalar_one())
    active = int(
        (
            await session.execute(_scoped(select(func.count()).select_from(VehicleORM).where(VehicleORM.active.is_(True))))
        ).scalar_one()
    )
    status_rows = (
        await session.execute(
            _scoped(select(VehicleORM.operational_status, func.count()).select_from(VehicleORM)).group_by(
                VehicleORM.operational_status
            )
        )
    ).all()
    category_rows = (
        await session.execute(
            _scoped(select(VehicleORM.vehicle_category, func.count()).select_from(VehicleORM)).group_by(
                VehicleORM.vehicle_category
            )
        )
    ).all()

    state_join = or_(
        cast(VehicleORM.id, String) == AnalyticsVehicleStateORM.vehicle_id,
        VehicleORM.vehicle_number == AnalyticsVehicleStateORM.vehicle_id,
    )
    moving_stmt = (
        select(func.count())
        .select_from(AnalyticsVehicleStateORM)
        .join(VehicleORM, state_join)
        .where(AnalyticsVehicleStateORM.last_ignition.is_(True), AnalyticsVehicleStateORM.last_speed_kph > 3)
    )
    idle_stmt = (
        select(func.count())
        .select_from(AnalyticsVehicleStateORM)
        .join(VehicleORM, state_join)
        .where(AnalyticsVehicleStateORM.last_ignition.is_(True), AnalyticsVehicleStateORM.last_speed_kph <= 3)
    )
    if needs_scope_join:
        scope_join = lambda stmt: stmt.join(WardORM, VehicleORM.ward_id == WardORM.id).join(
            ZoneORM, WardORM.zone_id == ZoneORM.id
        ).where(*vehicle_filters)
        moving_stmt = scope_join(moving_stmt)
        idle_stmt = scope_join(idle_stmt)
    moving_now = int((await session.execute(moving_stmt)).scalar_one())
    idle_now = int((await session.execute(idle_stmt)).scalar_one())

    return {
        "scope": {"zone_name": zone_name, "ward_name": ward_name} if needs_scope_join else "entire fleet",
        "total_vehicles": total,
        "active_vehicles": active,
        "inactive_vehicles": max(total - active, 0),
        "moving_now": moving_now,
        "idle_now": idle_now,
        "operational_status_breakdown": dict(status_rows),
        "category_breakdown": dict(category_rows),
    }


async def get_vehicle_list(
    session: AsyncSession,
    zone_name: str | None = None,
    ward_name: str | None = None,
    active_only: bool = True,
    movement_status: str | None = None,
    limit: int = 30,
    **_: Any,
) -> dict:
    """Named list of vehicles (registration number + assigned driver), for questions like
    'list trucks with driver names in Zone F' where aggregate counts aren't enough."""
    state_join = or_(
        cast(VehicleORM.id, String) == AnalyticsVehicleStateORM.vehicle_id,
        VehicleORM.vehicle_number == AnalyticsVehicleStateORM.vehicle_id,
    )
    stmt = (
        select(
            VehicleORM.vehicle_number,
            VehicleORM.registration_number,
            VehicleORM.operational_status,
            VehicleORM.active,
            DriverORM.name,
            DriverORM.phone,
            AnalyticsVehicleStateORM.last_ignition,
            AnalyticsVehicleStateORM.last_speed_kph,
        )
        .outerjoin(DriverORM, DriverORM.assigned_vehicle_id == VehicleORM.id)
        .outerjoin(AnalyticsVehicleStateORM, state_join)
        .limit(min(limit, 50))
    )
    if zone_name or ward_name:
        stmt = stmt.join(WardORM, VehicleORM.ward_id == WardORM.id)
        if zone_name:
            stmt = stmt.join(ZoneORM, WardORM.zone_id == ZoneORM.id).where(_fuzzy_match(ZoneORM.zone_name, zone_name))
        if ward_name:
            stmt = stmt.where(_fuzzy_match(WardORM.ward_name, ward_name))
    if active_only:
        stmt = stmt.where(VehicleORM.active.is_(True))

    rows = (await session.execute(stmt)).all()

    def _movement(last_ignition: bool | None, last_speed_kph: float | None) -> str:
        if last_ignition is None:
            return "unknown"
        if not last_ignition:
            return "offline"
        return "moving" if (last_speed_kph or 0) > 3 else "idle"

    vehicles = [
        {
            "vehicle_number": v_num,
            "registration_number": reg_num,
            "operational_status": op_status,
            "active": active,
            "driver_name": driver_name,
            "driver_phone": driver_phone,
            "movement_status": _movement(last_ignition, last_speed),
        }
        for v_num, reg_num, op_status, active, driver_name, driver_phone, last_ignition, last_speed in rows
    ]
    if movement_status:
        vehicles = [v for v in vehicles if v["movement_status"] == movement_status]

    return {
        "scope": {"zone_name": zone_name, "ward_name": ward_name, "movement_status": movement_status},
        "matching_count": len(vehicles),
        "vehicles": vehicles,
    }


async def get_alerts_overview(
    session: AsyncSession,
    status: str | None = None,
    severity: str | None = None,
    since_minutes: int | None = None,
    zone_name: str | None = None,
    ward_name: str | None = None,
    rank_by_vehicle: bool = False,
    limit: int = 10,
    **_: Any,
) -> dict:
    """Alert counts/list, optionally restricted to alerts triggered in the last `since_minutes`
    (e.g. 60 for "last 1 hour") and/or to a zone/ward. Without since_minutes, counts are
    ALL-TIME; without zone_name/ward_name, counts are FLEET-WIDE - always pass them when the
    user mentions a time window or a specific zone/ward, and never claim a zone in the answer
    unless zone_name was actually passed and matched at least one alert. Pass rank_by_vehicle=True
    for 'which truck/vehicle gets the most alerts' questions - do NOT try to answer that by
    counting the (capped, most-recent-only) 'matching_alerts' list yourself, it is not a
    reliable total; use the real GROUP BY aggregate in 'top_vehicles_by_alert_count' instead."""
    since_dt = datetime.now(timezone.utc) - timedelta(minutes=since_minutes) if since_minutes else None
    vehicle_match = or_(AlertORM.vehicle_id == cast(VehicleORM.id, String), AlertORM.vehicle_id == VehicleORM.vehicle_number)
    needs_scope_join = bool(zone_name or ward_name)

    def _apply_scope(stmt, *, via_vehicle_join: bool):
        if not needs_scope_join:
            return stmt
        if via_vehicle_join:
            stmt = stmt.join(VehicleORM, vehicle_match)
        stmt = stmt.join(WardORM, VehicleORM.ward_id == WardORM.id)
        if zone_name:
            stmt = stmt.join(ZoneORM, WardORM.zone_id == ZoneORM.id).where(_fuzzy_match(ZoneORM.zone_name, zone_name))
        if ward_name:
            stmt = stmt.where(_fuzzy_match(WardORM.ward_name, ward_name))
        return stmt

    status_stmt = select(AlertORM.status, func.count()).group_by(AlertORM.status)
    severity_stmt = (
        select(AlertORM.severity, func.count())
        .where(AlertORM.status.in_(["open", "acknowledged", "escalated"]))
        .group_by(AlertORM.severity)
    )
    if since_dt:
        status_stmt = status_stmt.where(AlertORM.triggered_at >= since_dt)
        severity_stmt = severity_stmt.where(AlertORM.triggered_at >= since_dt)
    status_stmt = _apply_scope(status_stmt, via_vehicle_join=True)
    severity_stmt = _apply_scope(severity_stmt, via_vehicle_join=True)

    by_status = dict((await session.execute(status_stmt)).all())
    by_severity = dict((await session.execute(severity_stmt)).all())

    top_vehicles_by_alert_count: list[dict] = []
    if rank_by_vehicle:
        rank_stmt = (
            select(
                VehicleORM.vehicle_number,
                VehicleORM.registration_number,
                func.count(AlertORM.id).label("alert_count"),
            )
            .select_from(AlertORM)
            .join(VehicleORM, vehicle_match)
            .group_by(VehicleORM.id, VehicleORM.vehicle_number, VehicleORM.registration_number)
            .order_by(func.count(AlertORM.id).desc())
            .limit(min(limit, 25))
        )
        if since_dt:
            rank_stmt = rank_stmt.where(AlertORM.triggered_at >= since_dt)
        if status:
            rank_stmt = rank_stmt.where(AlertORM.status == status)
        if severity:
            rank_stmt = rank_stmt.where(AlertORM.severity == severity)
        rank_stmt = _apply_scope(rank_stmt, via_vehicle_join=False)
        rank_rows = (await session.execute(rank_stmt)).all()
        top_vehicles_by_alert_count = [
            {"vehicle_number": registration_number or vehicle_number, "alert_count": int(count)}
            for vehicle_number, registration_number, count in rank_rows
        ]

    if needs_scope_join:
        # Inner join so the zone/ward filter actually excludes non-matching alerts.
        stmt = _apply_scope(
            select(AlertORM, VehicleORM.vehicle_number, VehicleORM.registration_number),
            via_vehicle_join=True,
        )
    else:
        stmt = select(AlertORM, VehicleORM.vehicle_number, VehicleORM.registration_number).outerjoin(
            VehicleORM, vehicle_match
        )
    stmt = stmt.order_by(AlertORM.triggered_at.desc()).limit(min(limit, 25))
    if since_dt:
        stmt = stmt.where(AlertORM.triggered_at >= since_dt)
    if status:
        stmt = stmt.where(AlertORM.status == status)
    if severity:
        stmt = stmt.where(AlertORM.severity == severity)
    rows = (await session.execute(stmt)).all()

    return {
        "time_window": f"last {since_minutes} minutes" if since_minutes else "all-time",
        "scope": {"zone_name": zone_name, "ward_name": ward_name} if needs_scope_join else "entire fleet",
        "counts_by_status": by_status,
        "open_counts_by_severity": by_severity,
        "top_vehicles_by_alert_count": top_vehicles_by_alert_count,
        "matching_alerts": [
            {
                "title": a.title,
                "category": a.category,
                "severity": a.severity,
                "status": a.status,
                # Prefer the human-readable registration/vehicle number; fall back to the
                # raw stored identifier only if it couldn't be matched to a vehicle record.
                "vehicle_number": registration_number or vehicle_number or a.vehicle_id,
                "triggered_at": _format_local(a.triggered_at),
            }
            for a, vehicle_number, registration_number in rows
        ],
    }


async def get_zones_and_wards(session: AsyncSession, **_: Any) -> dict:
    zone_rows = (await session.execute(select(ZoneORM))).scalars().all()
    ward_counts = dict((await session.execute(select(WardORM.zone_id, func.count()).group_by(WardORM.zone_id))).all())
    total_wards = int((await session.execute(select(func.count()).select_from(WardORM))).scalar_one())

    return {
        "total_zones": len(zone_rows),
        "total_wards": total_wards,
        "zones": [
            {
                "zone_code": z.zone_code,
                "zone_name": z.zone_name,
                "active": z.active,
                "ward_count": ward_counts.get(z.id, 0),
                "supervisor_name": z.supervisor_name,
            }
            for z in zone_rows
        ],
    }


async def get_vendors_overview(session: AsyncSession, active_only: bool = True, **_: Any) -> dict:
    stmt = select(VendorORM)
    if active_only:
        stmt = stmt.where(VendorORM.active.is_(True))
    vendors = (await session.execute(stmt)).scalars().all()
    vehicle_counts = dict((await session.execute(select(VehicleORM.vendor_id, func.count()).group_by(VehicleORM.vendor_id))).all())

    return {
        "total_vendors": len(vendors),
        "vendors": [
            {
                "vendor_code": v.vendor_code,
                "vendor_name": v.vendor_name,
                "active": v.active,
                "vehicle_count": vehicle_counts.get(v.id, 0),
                "contact_person": v.contact_person,
                "phone": v.phone,
            }
            for v in vendors
        ],
    }


async def get_devices_overview(session: AsyncSession, health_status: str | None = None, **_: Any) -> dict:
    by_health = dict((await session.execute(select(DeviceORM.health_status, func.count()).group_by(DeviceORM.health_status))).all())
    active_count = int(
        (await session.execute(select(func.count()).select_from(DeviceORM).where(DeviceORM.active.is_(True)))).scalar_one()
    )
    total = int((await session.execute(select(func.count()).select_from(DeviceORM))).scalar_one())

    stmt = select(DeviceORM).limit(10)
    if health_status:
        stmt = stmt.where(DeviceORM.health_status == health_status)
    matching = (await session.execute(stmt)).scalars().all()

    return {
        "total_devices": total,
        "active_devices": active_count,
        "counts_by_health_status": by_health,
        "matching_devices": [
            {"imei": d.imei, "model": d.model, "health_status": d.health_status, "battery_percent": d.battery_percent}
            for d in matching
        ],
    }


async def get_routes_and_pickup_points(session: AsyncSession, zone_name: str | None = None, **_: Any) -> dict:
    total_routes = int((await session.execute(select(func.count()).select_from(RouteORM))).scalar_one())
    total_pickup_points = int((await session.execute(select(func.count()).select_from(PickupPointORM))).scalar_one())
    by_type = dict((await session.execute(select(RouteORM.route_type, func.count()).group_by(RouteORM.route_type))).all())

    stmt = select(RouteORM.route_name, RouteORM.route_type, ZoneORM.zone_name).join(ZoneORM, RouteORM.zone_id == ZoneORM.id).limit(15)
    if zone_name:
        stmt = stmt.where(_fuzzy_match(ZoneORM.zone_name, zone_name))
    routes = (await session.execute(stmt)).all()

    return {
        "total_routes": total_routes,
        "total_pickup_points": total_pickup_points,
        "routes_by_type": by_type,
        "matching_routes": [{"route_name": r[0], "route_type": r[1], "zone_name": r[2]} for r in routes],
    }


async def get_pickup_point_coverage(
    session: AsyncSession,
    zone_name: str | None = None,
    ward_name: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 10,
    **_: Any,
) -> dict:
    """Ranks vehicles by how many distinct pickup points they physically covered on a given
    IST calendar day (default: today) - mirrors the platform's own 'Daily Pickup Coverage'
    report (PickupPointCrossingORM). Use this for 'which truck covered the most pickup
    points' style questions; get_trip_and_idle_summary only has fleet-wide totals, no
    per-vehicle ranking."""
    day = _parse_date(date_to) or _parse_date(date_from) or datetime.now(_LOCAL_TZ).date()
    start_local = datetime.combine(day, datetime.min.time(), tzinfo=_LOCAL_TZ)
    from_ts = start_local.astimezone(timezone.utc)
    to_ts = (start_local + timedelta(days=1)).astimezone(timezone.utc)

    vehicle_match = or_(
        PickupPointCrossingORM.vehicle_id == cast(VehicleORM.id, String),
        PickupPointCrossingORM.vehicle_id == VehicleORM.vehicle_number,
        PickupPointCrossingORM.vehicle_id == VehicleORM.registration_number,
    )

    stmt = (
        select(
            VehicleORM.vehicle_number,
            VehicleORM.registration_number,
            func.count(func.distinct(PickupPointCrossingORM.pickup_point_id)).label("points_covered"),
            func.max(PickupPointCrossingORM.crossed_at).label("last_crossed_at"),
        )
        .select_from(PickupPointCrossingORM)
        .join(VehicleORM, vehicle_match)
        .where(PickupPointCrossingORM.crossed_at >= from_ts, PickupPointCrossingORM.crossed_at < to_ts)
        .group_by(VehicleORM.id, VehicleORM.vehicle_number, VehicleORM.registration_number)
    )
    needs_scope_join = bool(zone_name or ward_name)
    if needs_scope_join:
        stmt = stmt.join(WardORM, VehicleORM.ward_id == WardORM.id)
        if zone_name:
            stmt = stmt.join(ZoneORM, WardORM.zone_id == ZoneORM.id).where(_fuzzy_match(ZoneORM.zone_name, zone_name))
        if ward_name:
            stmt = stmt.where(_fuzzy_match(WardORM.ward_name, ward_name))
    stmt = stmt.order_by(func.count(func.distinct(PickupPointCrossingORM.pickup_point_id)).desc()).limit(min(limit, 25))

    rows = (await session.execute(stmt)).all()

    return {
        "date": day.isoformat(),
        "scope": {"zone_name": zone_name, "ward_name": ward_name} if needs_scope_join else "entire fleet",
        "vehicles_ranked_by_pickup_points_covered": [
            {
                "vehicle_number": registration_number or vehicle_number,
                "pickup_points_covered": int(covered),
                "last_crossed_at": _format_local(last_crossed_at),
            }
            for vehicle_number, registration_number, covered, last_crossed_at in rows
        ],
    }


async def get_drivers_overview(session: AsyncSession, active_only: bool = True, **_: Any) -> dict:
    stmt = select(func.count()).select_from(DriverORM)
    if active_only:
        stmt = stmt.where(DriverORM.active.is_(True))
    active_count = int((await session.execute(stmt)).scalar_one())
    total = int((await session.execute(select(func.count()).select_from(DriverORM))).scalar_one())
    by_type = dict((await session.execute(select(DriverORM.person_type, func.count()).group_by(DriverORM.person_type))).all())

    return {"total_drivers": total, "active_drivers": active_count, "counts_by_person_type": by_type}


async def get_tickets_overview(
    session: AsyncSession,
    status: str | None = None,
    priority: str | None = None,
    since_minutes: int | None = None,
    limit: int = 10,
    **_: Any,
) -> dict:
    """Ticket counts/list. Without since_minutes, counts are ALL-TIME totals - pass it
    when the user mentions a time window (e.g. 'today', 'last hour')."""
    since_dt = datetime.now(timezone.utc) - timedelta(minutes=since_minutes) if since_minutes else None

    status_stmt = select(TicketORM.status, func.count()).group_by(TicketORM.status)
    priority_stmt = select(TicketORM.priority, func.count()).group_by(TicketORM.priority)
    if since_dt:
        status_stmt = status_stmt.where(TicketORM.created_at >= since_dt)
        priority_stmt = priority_stmt.where(TicketORM.created_at >= since_dt)
    by_status = dict((await session.execute(status_stmt)).all())
    by_priority = dict((await session.execute(priority_stmt)).all())

    stmt = select(TicketORM).order_by(TicketORM.created_at.desc()).limit(min(limit, 25))
    if since_dt:
        stmt = stmt.where(TicketORM.created_at >= since_dt)
    if status:
        stmt = stmt.where(TicketORM.status == status)
    if priority:
        stmt = stmt.where(TicketORM.priority == priority)
    rows = (await session.execute(stmt)).scalars().all()

    return {
        "time_window": f"last {since_minutes} minutes" if since_minutes else "all-time",
        "counts_by_status": by_status,
        "counts_by_priority": by_priority,
        "matching_tickets": [
            {
                "title": t.title,
                "category": t.category,
                "priority": t.priority,
                "status": t.status,
                "sla_breached": t.sla_breached,
                "created_at": _format_local(t.created_at),
            }
            for t in rows
        ],
    }


async def get_trip_and_idle_summary(
    session: AsyncSession, date_from: str | None = None, date_to: str | None = None, **_: Any
) -> dict:
    end = _parse_date(date_to) or date.today()
    start = _parse_date(date_from) or (end - timedelta(days=1))
    start_dt = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end, datetime.max.time(), tzinfo=timezone.utc)

    trip_row = (
        await session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(AnalyticsTripRecordORM.distance_km), 0.0),
                func.coalesce(func.sum(AnalyticsTripRecordORM.moving_seconds), 0),
            ).where(AnalyticsTripRecordORM.started_at.between(start_dt, end_dt))
        )
    ).one()
    idle_row = (
        await session.execute(
            select(func.count(), func.coalesce(func.sum(AnalyticsIdleRecordORM.duration_seconds), 0)).where(
                AnalyticsIdleRecordORM.started_at.between(start_dt, end_dt)
            )
        )
    ).one()

    return {
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "trips_count": int(trip_row[0]),
        "total_distance_km": round(float(trip_row[1]), 2),
        "total_moving_seconds": int(trip_row[2]),
        "idle_events_count": int(idle_row[0]),
        "total_idle_seconds": int(idle_row[1]),
    }


async def get_dump_yard_weighments_overview(
    session: AsyncSession, date_from: str | None = None, date_to: str | None = None, **_: Any
) -> dict:
    end = _parse_date(date_to) or date.today()
    start = _parse_date(date_from) or end

    row = (
        await session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(DumpYardWeighmentORM.net_weight_kg), 0.0),
            ).where(DumpYardWeighmentORM.service_date.between(start, end))
        )
    ).one()
    by_material = dict(
        (
            await session.execute(
                select(DumpYardWeighmentORM.material_type, func.coalesce(func.sum(DumpYardWeighmentORM.net_weight_kg), 0.0))
                .where(DumpYardWeighmentORM.service_date.between(start, end))
                .group_by(DumpYardWeighmentORM.material_type)
            )
        ).all()
    )

    return {
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "weighment_count": int(row[0]),
        "total_net_weight_kg": round(float(row[1]), 2),
        "net_weight_kg_by_material": {k: round(float(v), 2) for k, v in by_material.items()},
    }


async def get_gtc_checkpoints_overview(session: AsyncSession, limit: int = 10, **_: Any) -> dict:
    total = int((await session.execute(select(func.count()).select_from(GtcCheckpointORM))).scalar_one())
    recent = (
        await session.execute(select(GtcCheckpointORM).order_by(GtcCheckpointORM.arrived_at.desc()).limit(min(limit, 25)))
    ).scalars().all()

    return {
        "total_checkpoint_entries": total,
        "recent_entries": [
            {
                "truck_id": c.truck_id,
                "arrived_at": _format_local(c.arrived_at),
                "waste_types": [
                    name
                    for name, flag in [
                        ("dry", c.is_dry),
                        ("wet", c.is_wet),
                        ("metal", c.is_metal),
                        ("plastic", c.is_plastic),
                        ("sanitary", c.is_sanitary),
                    ]
                    if flag
                ],
                "truck_cleanliness_score": c.truck_cleanliness_score,
            }
            for c in recent
        ],
    }


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


ToolFn = Callable[..., Coroutine[Any, Any, dict]]

TOOL_REGISTRY: dict[str, ToolFn] = {
    "get_fleet_overview": get_fleet_overview,
    "get_vehicle_list": get_vehicle_list,
    "get_alerts_overview": get_alerts_overview,
    "get_zones_and_wards": get_zones_and_wards,
    "get_vendors_overview": get_vendors_overview,
    "get_devices_overview": get_devices_overview,
    "get_routes_and_pickup_points": get_routes_and_pickup_points,
    "get_pickup_point_coverage": get_pickup_point_coverage,
    "get_drivers_overview": get_drivers_overview,
    "get_tickets_overview": get_tickets_overview,
    "get_trip_and_idle_summary": get_trip_and_idle_summary,
    "get_dump_yard_weighments_overview": get_dump_yard_weighments_overview,
    "get_gtc_checkpoints_overview": get_gtc_checkpoints_overview,
}

# JSON schema describing each tool to the OpenAI API (function-calling).
TOOL_SPECS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_fleet_overview",
            "description": "Live vehicle/fleet counts: total, active, moving/idle right now, and breakdowns by operational status and category. Pass zone_name and/or ward_name to scope the counts to a specific zone/ward (e.g. 'how many trucks in Zone F') instead of the whole fleet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "zone_name": {"type": "string", "description": "Filter to vehicles whose ward belongs to this zone (partial match, e.g. 'Zone F' or 'F')."},
                    "ward_name": {"type": "string", "description": "Filter to vehicles in this ward (partial match)."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vehicle_list",
            "description": "Named list of individual vehicles (registration number, operational status, moving/idle status) with their assigned driver's name and phone. Use this whenever the user wants specific vehicle/truck names or driver names, not just a count - e.g. 'list trucks with driver names active in Zone F'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "zone_name": {"type": "string"},
                    "ward_name": {"type": "string"},
                    "active_only": {"type": "boolean", "description": "Only include active vehicles, default true"},
                    "movement_status": {"type": "string", "enum": ["moving", "idle", "offline"]},
                    "limit": {"type": "integer", "description": "Max vehicles to return, default 30, max 50"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_alerts_overview",
            "description": "Alert counts by status/severity plus a list of matching alerts. Without since_minutes, counts are ALL-TIME totals - ALWAYS pass since_minutes when the user mentions a time window (e.g. 'last 1 hour' -> 60, 'last 24 hours' -> 1440, 'today' -> minutes since midnight). Without zone_name/ward_name, counts are FLEET-WIDE (not scoped to any zone) - pass zone_name/ward_name whenever the user names one, so the results are actually filtered to that zone instead of just being described as if they were. For 'which truck/vehicle has the most alerts' questions, set rank_by_vehicle=true and read 'top_vehicles_by_alert_count' - do not try to count the capped 'matching_alerts' list yourself.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["open", "acknowledged", "resolved", "escalated"]},
                    "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "since_minutes": {"type": "integer", "description": "Only include alerts triggered in the last N minutes."},
                    "zone_name": {"type": "string", "description": "Filter to alerts on vehicles whose ward belongs to this zone (partial match)."},
                    "ward_name": {"type": "string", "description": "Filter to alerts on vehicles in this ward (partial match)."},
                    "rank_by_vehicle": {"type": "boolean", "description": "Set true to get a real per-vehicle alert count ranking in 'top_vehicles_by_alert_count'."},
                    "limit": {"type": "integer", "description": "Max alerts/vehicles to return, default 10"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_zones_and_wards",
            "description": "Zones and wards master data: counts, ward-per-zone breakdown, supervisors.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vendors_overview",
            "description": "Vendor master data: counts, per-vendor vehicle counts, contact details.",
            "parameters": {
                "type": "object",
                "properties": {"active_only": {"type": "boolean", "description": "Only include active vendors, default true"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_devices_overview",
            "description": "GPS device/IoT hardware counts by health status (healthy/warning/critical/offline).",
            "parameters": {
                "type": "object",
                "properties": {"health_status": {"type": "string", "enum": ["healthy", "warning", "critical", "offline"]}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_routes_and_pickup_points",
            "description": "Route and pickup-point master data: counts, breakdown by route type, optionally filtered by zone name.",
            "parameters": {"type": "object", "properties": {"zone_name": {"type": "string"}}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pickup_point_coverage",
            "description": "Ranks vehicles by number of distinct pickup points they actually covered on a given day (default today, IST calendar day) - this is the ONLY tool that can answer 'which truck/vehicle covered the most pickup points'. Not the same as get_trip_and_idle_summary, which has no per-vehicle breakdown.",
            "parameters": {
                "type": "object",
                "properties": {
                    "zone_name": {"type": "string"},
                    "ward_name": {"type": "string"},
                    "date_from": {"type": "string", "description": "ISO YYYY-MM-DD, defaults to today"},
                    "date_to": {"type": "string", "description": "ISO YYYY-MM-DD, defaults to today"},
                    "limit": {"type": "integer", "description": "Max vehicles to return, default 10"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_drivers_overview",
            "description": "Driver/crew counts, active vs total, breakdown by person type (driver/helper/ic_member).",
            "parameters": {
                "type": "object",
                "properties": {"active_only": {"type": "boolean", "description": "Only count active drivers, default true"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_tickets_overview",
            "description": "Support/complaint ticket counts by status and priority, plus a list of matching tickets. Without since_minutes, counts are ALL-TIME totals - pass it when the user mentions a time window (e.g. 'today', 'last hour').",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["open", "in_progress", "pending", "resolved", "closed"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "since_minutes": {"type": "integer", "description": "Only include tickets created in the last N minutes."},
                    "limit": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_trip_and_idle_summary",
            "description": "FLEET-WIDE trip/idle totals (trip count, total distance, moving/idle seconds) for a date range - no per-vehicle breakdown and no zone filter. Do NOT use this for 'which vehicle...' ranking questions - use get_pickup_point_coverage or get_vehicle_list instead. Dates are ISO YYYY-MM-DD; defaults to yesterday-to-today.",
            "parameters": {
                "type": "object",
                "properties": {"date_from": {"type": "string"}, "date_to": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dump_yard_weighments_overview",
            "description": "Dump yard weighment/tonnage summary (collection tonnage) for a date range, broken down by waste material type. Dates are ISO YYYY-MM-DD; defaults to today.",
            "parameters": {
                "type": "object",
                "properties": {"date_from": {"type": "string"}, "date_to": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_gtc_checkpoints_overview",
            "description": "GTS/GTC checkpoint inspection entries: total count and recent entries with waste-type flags and cleanliness scores.",
            "parameters": {"type": "object", "properties": {"limit": {"type": "integer"}}},
        },
    },
]


async def execute_tool(name: str, arguments: dict, session: AsyncSession) -> dict:
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return {"error": f"Unknown tool '{name}'"}
    try:
        return await fn(session, **arguments)
    except Exception as exc:  # keep the model's conversation alive with a readable error
        return {"error": f"Tool '{name}' failed: {exc}"}
