from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Float, String, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from swm_db import (
    AnalyticsDailyKPIORM,
    AnalyticsGeofenceEventORM,
    AnalyticsIdleRecordORM,
    AnalyticsOverspeedEventORM,
    AnalyticsTripRecordORM,
    AnalyticsVehicleStateORM,
    PickupPointCrossingORM,
    get_db_session,
)

from admin_api.api_support import (
    RoleContext,
    _csv_response,
    _rows_from_result,
    _to_dict,
    require_roles,
)

router = APIRouter()


def _period_start_expr(period: str) -> Any:
    metric_date = AnalyticsDailyKPIORM.metric_date
    if period == "daily":
        return metric_date.label("period_start")
    if period == "monthly":
        return func.date_trunc("month", metric_date).cast(String).label("period_start")
    if period == "quarterly":
        return func.date_trunc("quarter", metric_date).cast(String).label("period_start")
    if period == "half-yearly":
        return (
            func.to_date(
                func.concat(
                    func.extract("year", metric_date).cast(String),
                    "-",
                    case((func.extract("month", metric_date) <= 6, "01-01"), else_="07-01"),
                ),
                "YYYY-MM-DD",
            )
            .cast(String)
            .label("period_start")
        )
    return func.date_trunc("year", metric_date).cast(String).label("period_start")


async def _analytics_report(
    session: AsyncSession,
    *,
    period: str,
    date_from: date | None,
    date_to: date | None,
    vehicle_id: str | None,
    vendor_id: str | None,
    export: str,
) -> Any:
    period_expr = _period_start_expr(period)
    stmt = (
        select(
            period_expr,
            func.sum(AnalyticsDailyKPIORM.trips_count).label("trips_count"),
            func.sum(AnalyticsDailyKPIORM.distance_km).label("distance_km"),
            func.sum(AnalyticsDailyKPIORM.runtime_seconds).label("runtime_seconds"),
            func.sum(AnalyticsDailyKPIORM.moving_seconds).label("moving_seconds"),
            func.sum(AnalyticsDailyKPIORM.idle_seconds).label("idle_seconds"),
            func.sum(AnalyticsDailyKPIORM.stoppages_count).label("stoppages_count"),
            func.sum(AnalyticsDailyKPIORM.overspeed_count).label("overspeed_count"),
            func.sum(AnalyticsDailyKPIORM.geofence_entries).label("geofence_entries"),
            func.sum(AnalyticsDailyKPIORM.geofence_exits).label("geofence_exits"),
            func.sum(AnalyticsDailyKPIORM.route_deviation_count).label("route_deviation_count"),
            func.sum(AnalyticsDailyKPIORM.fuel_used_l).label("fuel_used_l"),
            func.avg(AnalyticsDailyKPIORM.utilization_pct).label("utilization_pct"),
        )
        .select_from(AnalyticsDailyKPIORM)
        .group_by(period_expr)
        .order_by(period_expr)
    )

    if date_from is not None:
        stmt = stmt.where(AnalyticsDailyKPIORM.metric_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(AnalyticsDailyKPIORM.metric_date <= date_to)
    if vehicle_id:
        stmt = stmt.where(AnalyticsDailyKPIORM.vehicle_id == vehicle_id)
    if vendor_id:
        stmt = stmt.where(AnalyticsDailyKPIORM.vendor_id == vendor_id)

    rows = _rows_from_result(await session.execute(stmt))
    if export == "csv":
        return _csv_response(rows, f"analytics-{period}-report.csv")
    return {"period": period, "items": rows, "total": len(rows)}


@router.get("/analytics/trips")
async def list_trip_records(
    started_from: datetime | None = Query(default=None),
    started_to: datetime | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    vendor_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = select(AnalyticsTripRecordORM).order_by(AnalyticsTripRecordORM.started_at.desc()).limit(limit)
    if started_from is not None:
        stmt = stmt.where(AnalyticsTripRecordORM.started_at >= started_from)
    if started_to is not None:
        stmt = stmt.where(AnalyticsTripRecordORM.started_at <= started_to)
    if vehicle_id:
        stmt = stmt.where(AnalyticsTripRecordORM.vehicle_id == vehicle_id)
    if vendor_id:
        stmt = stmt.where(AnalyticsTripRecordORM.vendor_id == vendor_id)

    rows = (await session.execute(stmt)).scalars().all()
    items = [_to_dict(row) for row in rows]
    return {"items": items, "total": len(items)}


@router.get("/analytics/idle-segments")
async def list_idle_segments(
    started_from: datetime | None = Query(default=None),
    started_to: datetime | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    vendor_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = select(AnalyticsIdleRecordORM).order_by(AnalyticsIdleRecordORM.started_at.desc()).limit(limit)
    if started_from is not None:
        stmt = stmt.where(AnalyticsIdleRecordORM.started_at >= started_from)
    if started_to is not None:
        stmt = stmt.where(AnalyticsIdleRecordORM.started_at <= started_to)
    if vehicle_id:
        stmt = stmt.where(AnalyticsIdleRecordORM.vehicle_id == vehicle_id)
    if vendor_id:
        stmt = stmt.where(AnalyticsIdleRecordORM.vendor_id == vendor_id)

    rows = (await session.execute(stmt)).scalars().all()
    items = [_to_dict(row) for row in rows]
    return {"items": items, "total": len(items)}


@router.get("/analytics/overspeed-events")
async def list_overspeed_events(
    from_ts: datetime | None = Query(default=None),
    to_ts: datetime | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    vendor_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = select(AnalyticsOverspeedEventORM).order_by(AnalyticsOverspeedEventORM.event_ts.desc()).limit(limit)
    if from_ts is not None:
        stmt = stmt.where(AnalyticsOverspeedEventORM.event_ts >= from_ts)
    if to_ts is not None:
        stmt = stmt.where(AnalyticsOverspeedEventORM.event_ts <= to_ts)
    if vehicle_id:
        stmt = stmt.where(AnalyticsOverspeedEventORM.vehicle_id == vehicle_id)
    if vendor_id:
        stmt = stmt.where(AnalyticsOverspeedEventORM.vendor_id == vendor_id)

    rows = (await session.execute(stmt)).scalars().all()
    items = [_to_dict(row) for row in rows]
    return {"items": items, "total": len(items)}


@router.get("/analytics/geofence-events")
async def list_geofence_events(
    from_ts: datetime | None = Query(default=None),
    to_ts: datetime | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = select(AnalyticsGeofenceEventORM).order_by(AnalyticsGeofenceEventORM.event_ts.desc()).limit(limit)
    if from_ts is not None:
        stmt = stmt.where(AnalyticsGeofenceEventORM.event_ts >= from_ts)
    if to_ts is not None:
        stmt = stmt.where(AnalyticsGeofenceEventORM.event_ts <= to_ts)
    if vehicle_id:
        stmt = stmt.where(AnalyticsGeofenceEventORM.vehicle_id == vehicle_id)
    if event_type:
        stmt = stmt.where(AnalyticsGeofenceEventORM.event_type == event_type)

    rows = (await session.execute(stmt)).scalars().all()
    items = [_to_dict(row) for row in rows]
    return {"items": items, "total": len(items)}


@router.get("/analytics/reports/daily")
async def report_daily(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    vendor_id: str | None = Query(default=None),
    export: str = Query(default="json", pattern="^(json|csv)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    return await _analytics_report(
        session,
        period="daily",
        date_from=date_from,
        date_to=date_to,
        vehicle_id=vehicle_id,
        vendor_id=vendor_id,
        export=export,
    )


@router.get("/analytics/reports/monthly")
async def report_monthly(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    vendor_id: str | None = Query(default=None),
    export: str = Query(default="json", pattern="^(json|csv)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    return await _analytics_report(
        session,
        period="monthly",
        date_from=date_from,
        date_to=date_to,
        vehicle_id=vehicle_id,
        vendor_id=vendor_id,
        export=export,
    )


@router.get("/analytics/reports/quarterly")
async def report_quarterly(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    vendor_id: str | None = Query(default=None),
    export: str = Query(default="json", pattern="^(json|csv)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    return await _analytics_report(
        session,
        period="quarterly",
        date_from=date_from,
        date_to=date_to,
        vehicle_id=vehicle_id,
        vendor_id=vendor_id,
        export=export,
    )


@router.get("/analytics/reports/half-yearly")
async def report_half_yearly(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    vendor_id: str | None = Query(default=None),
    export: str = Query(default="json", pattern="^(json|csv)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    return await _analytics_report(
        session,
        period="half-yearly",
        date_from=date_from,
        date_to=date_to,
        vehicle_id=vehicle_id,
        vendor_id=vendor_id,
        export=export,
    )


@router.get("/analytics/reports/annual")
async def report_annual(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    vendor_id: str | None = Query(default=None),
    export: str = Query(default="json", pattern="^(json|csv)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    return await _analytics_report(
        session,
        period="annual",
        date_from=date_from,
        date_to=date_to,
        vehicle_id=vehicle_id,
        vendor_id=vendor_id,
        export=export,
    )


@router.get("/analytics/vehicle-state")
async def list_vehicle_states(
    limit: int = Query(default=500, ge=1, le=5000),
    vehicle_id: str | None = Query(default=None),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = select(AnalyticsVehicleStateORM).limit(limit)
    if vehicle_id:
        stmt = stmt.where(AnalyticsVehicleStateORM.vehicle_id == vehicle_id)

    rows = (await session.execute(stmt)).scalars().all()
    items = [_to_dict(row) for row in rows]
    return {"items": items, "total": len(items)}


@router.get("/analytics/vehicle-state/{vehicle_id}")
async def get_vehicle_state(
    vehicle_id: str,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = select(AnalyticsVehicleStateORM).where(AnalyticsVehicleStateORM.vehicle_id == vehicle_id)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"vehicle state not found for {vehicle_id}")
    return _to_dict(row)


@router.get("/analytics/geofence-summary")
async def geofence_summary(
    from_ts: datetime | None = Query(default=None),
    to_ts: datetime | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    geofence_code: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
    export: str = Query(default="json", pattern="^(json|csv)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    stmt = (
        select(
            AnalyticsGeofenceEventORM.geofence_code,
            func.count(AnalyticsGeofenceEventORM.id).label("total_events"),
            func.sum(case((AnalyticsGeofenceEventORM.event_type == "entry", 1), else_=0)).label("entries"),
            func.sum(case((AnalyticsGeofenceEventORM.event_type == "exit", 1), else_=0)).label("exits"),
            (func.sum(AnalyticsGeofenceEventORM.dwell_seconds) / 60.0).label("total_dwell_minutes"),
            (func.avg(AnalyticsGeofenceEventORM.dwell_seconds) / 60.0).label("avg_dwell_minutes"),
        )
        .select_from(AnalyticsGeofenceEventORM)
        .group_by(AnalyticsGeofenceEventORM.geofence_code)
        .limit(limit)
    )

    if from_ts is not None:
        stmt = stmt.where(AnalyticsGeofenceEventORM.event_ts >= from_ts)
    if to_ts is not None:
        stmt = stmt.where(AnalyticsGeofenceEventORM.event_ts <= to_ts)
    if vehicle_id:
        stmt = stmt.where(AnalyticsGeofenceEventORM.vehicle_id == vehicle_id)
    if geofence_code:
        stmt = stmt.where(AnalyticsGeofenceEventORM.geofence_code == geofence_code)

    rows = _rows_from_result(await session.execute(stmt))
    if export == "csv":
        return _csv_response(rows, "geofence-summary.csv")
    return {"items": rows, "total": len(rows)}


@router.get("/analytics/vehicle-utilization")
async def vehicle_utilization(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    vendor_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
    export: str = Query(default="json", pattern="^(json|csv)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    stmt = (
        select(
            AnalyticsDailyKPIORM.metric_date,
            AnalyticsDailyKPIORM.vehicle_id,
            AnalyticsDailyKPIORM.utilization_pct,
            AnalyticsDailyKPIORM.distance_km,
            AnalyticsDailyKPIORM.runtime_seconds,
            AnalyticsDailyKPIORM.moving_seconds,
            AnalyticsDailyKPIORM.idle_seconds,
            AnalyticsDailyKPIORM.trips_count,
        )
        .select_from(AnalyticsDailyKPIORM)
        .order_by(AnalyticsDailyKPIORM.metric_date.desc(), AnalyticsDailyKPIORM.vehicle_id)
        .limit(limit)
    )

    if date_from is not None:
        stmt = stmt.where(AnalyticsDailyKPIORM.metric_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(AnalyticsDailyKPIORM.metric_date <= date_to)
    if vehicle_id:
        stmt = stmt.where(AnalyticsDailyKPIORM.vehicle_id == vehicle_id)
    if vendor_id:
        stmt = stmt.where(AnalyticsDailyKPIORM.vendor_id == vendor_id)

    rows = _rows_from_result(await session.execute(stmt))
    if export == "csv":
        return _csv_response(rows, "vehicle-utilization.csv")
    return {"items": rows, "total": len(rows)}


@router.get("/analytics/route-deviation-summary")
async def route_deviation_summary(
    from_ts: datetime | None = Query(default=None),
    to_ts: datetime | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
    export: str = Query(default="json", pattern="^(json|csv)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    trips_stmt = select(
        AnalyticsTripRecordORM.vehicle_id.label("vehicle_id"),
        func.count(AnalyticsTripRecordORM.id).label("trips_total"),
    ).select_from(AnalyticsTripRecordORM)

    if from_ts is not None:
        trips_stmt = trips_stmt.where(AnalyticsTripRecordORM.started_at >= from_ts)
    if to_ts is not None:
        trips_stmt = trips_stmt.where(AnalyticsTripRecordORM.started_at <= to_ts)
    if vehicle_id:
        trips_stmt = trips_stmt.where(AnalyticsTripRecordORM.vehicle_id == vehicle_id)

    trips_sq = trips_stmt.group_by(AnalyticsTripRecordORM.vehicle_id).subquery()

    deviations_stmt = (
        select(
            AnalyticsGeofenceEventORM.vehicle_id.label("vehicle_id"),
            func.count(AnalyticsGeofenceEventORM.id).label("trips_with_deviation"),
        )
        .select_from(AnalyticsGeofenceEventORM)
        .where(AnalyticsGeofenceEventORM.event_type == "route_deviation")
    )

    if from_ts is not None:
        deviations_stmt = deviations_stmt.where(AnalyticsGeofenceEventORM.event_ts >= from_ts)
    if to_ts is not None:
        deviations_stmt = deviations_stmt.where(AnalyticsGeofenceEventORM.event_ts <= to_ts)
    if vehicle_id:
        deviations_stmt = deviations_stmt.where(AnalyticsGeofenceEventORM.vehicle_id == vehicle_id)

    deviations_sq = deviations_stmt.group_by(AnalyticsGeofenceEventORM.vehicle_id).subquery()

    stmt = (
        select(
            trips_sq.c.vehicle_id,
            trips_sq.c.trips_total,
            func.coalesce(deviations_sq.c.trips_with_deviation, 0).label("trips_with_deviation"),
            cast(None, Float).label("avg_deviation_distance_km"),
            cast(None, Float).label("max_deviation_distance_km"),
        )
        .select_from(trips_sq.outerjoin(deviations_sq, deviations_sq.c.vehicle_id == trips_sq.c.vehicle_id))
        .limit(limit)
    )

    rows = _rows_from_result(await session.execute(stmt))
    if export == "csv":
        return _csv_response(rows, "route-deviation-summary.csv")
    return {"items": rows, "total": len(rows)}


@router.get("/analytics/fuel-efficiency")
async def fuel_efficiency(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    vendor_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
    export: str = Query(default="json", pattern="^(json|csv)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    stmt = (
        select(
            AnalyticsDailyKPIORM.metric_date,
            AnalyticsDailyKPIORM.vehicle_id,
            AnalyticsDailyKPIORM.vendor_id,
            AnalyticsDailyKPIORM.distance_km,
            AnalyticsDailyKPIORM.fuel_used_l,
            (AnalyticsDailyKPIORM.distance_km / func.nullif(AnalyticsDailyKPIORM.fuel_used_l, 0)).cast(Float).label("km_per_liter"),
        )
        .select_from(AnalyticsDailyKPIORM)
        .where(AnalyticsDailyKPIORM.fuel_used_l > 0)
        .order_by(AnalyticsDailyKPIORM.metric_date.desc())
        .limit(limit)
    )

    if date_from is not None:
        stmt = stmt.where(AnalyticsDailyKPIORM.metric_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(AnalyticsDailyKPIORM.metric_date <= date_to)
    if vehicle_id:
        stmt = stmt.where(AnalyticsDailyKPIORM.vehicle_id == vehicle_id)
    if vendor_id:
        stmt = stmt.where(AnalyticsDailyKPIORM.vendor_id == vendor_id)

    rows = _rows_from_result(await session.execute(stmt))
    if export == "csv":
        return _csv_response(rows, "fuel-efficiency.csv")
    return {"items": rows, "total": len(rows)}


@router.get("/analytics/speed-analysis")
async def speed_analysis(
    from_ts: datetime | None = Query(default=None),
    to_ts: datetime | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    vendor_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
    export: str = Query(default="json", pattern="^(json|csv)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    stmt = (
        select(
            AnalyticsOverspeedEventORM.vehicle_id,
            func.count(AnalyticsOverspeedEventORM.id).label("overspeed_events"),
            func.avg(AnalyticsOverspeedEventORM.speed_kph).label("avg_overspeed_kph"),
            func.max(AnalyticsOverspeedEventORM.speed_kph).label("max_speed_kph"),
            func.min(AnalyticsOverspeedEventORM.speed_kph).label("min_overspeed_kph"),
        )
        .select_from(AnalyticsOverspeedEventORM)
        .group_by(AnalyticsOverspeedEventORM.vehicle_id)
        .limit(limit)
    )

    if from_ts is not None:
        stmt = stmt.where(AnalyticsOverspeedEventORM.event_ts >= from_ts)
    if to_ts is not None:
        stmt = stmt.where(AnalyticsOverspeedEventORM.event_ts <= to_ts)
    if vehicle_id:
        stmt = stmt.where(AnalyticsOverspeedEventORM.vehicle_id == vehicle_id)
    if vendor_id:
        stmt = stmt.where(AnalyticsOverspeedEventORM.vendor_id == vendor_id)

    rows = _rows_from_result(await session.execute(stmt))
    if export == "csv":
        return _csv_response(rows, "speed-analysis.csv")
    return {"items": rows, "total": len(rows)}


@router.get("/analytics/idle-summary")
async def idle_summary(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    vendor_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
    export: str = Query(default="json", pattern="^(json|csv)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    stmt = (
        select(
            AnalyticsDailyKPIORM.metric_date,
            AnalyticsDailyKPIORM.vehicle_id,
            AnalyticsDailyKPIORM.idle_seconds,
            AnalyticsDailyKPIORM.stoppages_count,
            AnalyticsDailyKPIORM.moving_seconds,
            AnalyticsDailyKPIORM.runtime_seconds,
            (AnalyticsDailyKPIORM.idle_seconds * 100.0 / func.nullif(AnalyticsDailyKPIORM.runtime_seconds, 0)).cast(Float).label("idle_percent"),
        )
        .select_from(AnalyticsDailyKPIORM)
        .order_by(AnalyticsDailyKPIORM.metric_date.desc())
        .limit(limit)
    )

    if date_from is not None:
        stmt = stmt.where(AnalyticsDailyKPIORM.metric_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(AnalyticsDailyKPIORM.metric_date <= date_to)
    if vehicle_id:
        stmt = stmt.where(AnalyticsDailyKPIORM.vehicle_id == vehicle_id)
    if vendor_id:
        stmt = stmt.where(AnalyticsDailyKPIORM.vendor_id == vendor_id)

    rows = _rows_from_result(await session.execute(stmt))
    if export == "csv":
        return _csv_response(rows, "idle-summary.csv")
    return {"items": rows, "total": len(rows)}


@router.get("/analytics/pickup-point-crossings")
async def list_pickup_point_crossings(
    from_ts: datetime | None = Query(default=None),
    to_ts: datetime | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    route_id: str | None = Query(default=None),
    pickup_point_id: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
    export: str = Query(default="json", pattern="^(json|csv)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    stmt = select(PickupPointCrossingORM).order_by(PickupPointCrossingORM.crossed_at.desc()).limit(limit)
    if from_ts is not None:
        stmt = stmt.where(PickupPointCrossingORM.crossed_at >= from_ts)
    if to_ts is not None:
        stmt = stmt.where(PickupPointCrossingORM.crossed_at <= to_ts)
    if vehicle_id:
        stmt = stmt.where(PickupPointCrossingORM.vehicle_id == vehicle_id)
    if route_id:
        stmt = stmt.where(cast(PickupPointCrossingORM.route_id, String) == route_id)
    if pickup_point_id:
        stmt = stmt.where(cast(PickupPointCrossingORM.pickup_point_id, String) == pickup_point_id)

    rows = [_to_dict(row) for row in (await session.execute(stmt)).scalars().all()]
    if export == "csv":
        return _csv_response(rows, "pickup-point-crossings.csv")
    return {"items": rows, "total": len(rows)}
