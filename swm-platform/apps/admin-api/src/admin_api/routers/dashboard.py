from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, and_, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from swm_db import (
    AlertORM,
    AnalyticsDailyKPIORM,
    AnalyticsGeofenceEventORM,
    AnalyticsIdleRecordORM,
    AnalyticsTripRecordORM,
    AnalyticsVehicleStateORM,
    DeviceEventORM,
    DeviceORM,
    DeviceVehicleAssignmentORM,
    RouteORM,
    VehicleORM,
    WardORM,
    get_db_session,
)

from admin_api.api_support import (
    PageResponse,
    RoleContext,
    _export_rows,
    _to_dict,
    require_roles,
)

router = APIRouter()


@router.get("/v1/dashboard/kpis")
async def dashboard_kpis(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    vendor_id: UUID | None = Query(default=None),
    route_id: UUID | None = Query(default=None),
    ward_id: UUID | None = Query(default=None),
    zone_name: str | None = Query(default=None),
    export: str = Query(default="json", pattern="^(json|csv|xlsx|pdf)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    vehicle_filters = []
    if vendor_id is not None:
        vehicle_filters.append(VehicleORM.vendor_id == vendor_id)
    if route_id is not None:
        vehicle_filters.append(VehicleORM.route_id == route_id)
    if ward_id is not None:
        vehicle_filters.append(VehicleORM.ward_id == ward_id)
    if zone_name:
        vehicle_filters.append(WardORM.zone_name == zone_name)

    vehicle_base = select(VehicleORM.id).join(WardORM, VehicleORM.ward_id == WardORM.id)
    if vehicle_filters:
        vehicle_base = vehicle_base.where(and_(*vehicle_filters))
    vehicle_subquery = vehicle_base.subquery()

    total_fleet = int((await session.execute(select(func.count()).select_from(vehicle_subquery))).scalar_one())
    active_fleet = int(
        (
            await session.execute(
                select(func.count())
                .select_from(VehicleORM)
                .join(WardORM, VehicleORM.ward_id == WardORM.id)
                .where(VehicleORM.active.is_(True), *vehicle_filters)
            )
        ).scalar_one()
    )
    inactive_fleet = max(total_fleet - active_fleet, 0)

    state_join = or_(
        cast(VehicleORM.id, String) == AnalyticsVehicleStateORM.vehicle_id,
        VehicleORM.vehicle_number == AnalyticsVehicleStateORM.vehicle_id,
    )

    moving_stmt = (
        select(func.count())
        .select_from(AnalyticsVehicleStateORM)
        .join(VehicleORM, state_join)
        .join(WardORM, VehicleORM.ward_id == WardORM.id)
        .where(AnalyticsVehicleStateORM.last_ignition.is_(True), AnalyticsVehicleStateORM.last_speed_kph > 3)
    )
    idle_stmt = (
        select(func.count())
        .select_from(AnalyticsVehicleStateORM)
        .join(VehicleORM, state_join)
        .join(WardORM, VehicleORM.ward_id == WardORM.id)
        .where(AnalyticsVehicleStateORM.last_ignition.is_(True), AnalyticsVehicleStateORM.last_speed_kph <= 3)
    )
    if vehicle_filters:
        moving_stmt = moving_stmt.where(*vehicle_filters)
        idle_stmt = idle_stmt.where(*vehicle_filters)

    moving_vehicles = int((await session.execute(moving_stmt)).scalar_one())
    idle_vehicles = int((await session.execute(idle_stmt)).scalar_one())

    kpi_stmt = (
        select(
            func.avg(AnalyticsDailyKPIORM.utilization_pct).label("avg_utilization_pct"),
            func.avg(
                case(
                    (
                        RouteORM.expected_distance_km > 0,
                        func.least((AnalyticsDailyKPIORM.distance_km / RouteORM.expected_distance_km) * 100.0, 100.0),
                    ),
                    else_=None,
                )
            ).label("route_completion_pct"),
        )
        .select_from(AnalyticsDailyKPIORM)
        .join(
            VehicleORM,
            or_(
                cast(VehicleORM.id, String) == AnalyticsDailyKPIORM.vehicle_id,
                VehicleORM.vehicle_number == AnalyticsDailyKPIORM.vehicle_id,
            ),
        )
        .join(WardORM, VehicleORM.ward_id == WardORM.id)
        .outerjoin(RouteORM, VehicleORM.route_id == RouteORM.id)
    )
    if date_from is not None:
        kpi_stmt = kpi_stmt.where(AnalyticsDailyKPIORM.metric_date >= date_from)
    if date_to is not None:
        kpi_stmt = kpi_stmt.where(AnalyticsDailyKPIORM.metric_date <= date_to)
    if vehicle_filters:
        kpi_stmt = kpi_stmt.where(*vehicle_filters)

    kpi_row = (await session.execute(kpi_stmt)).mappings().first() or {}
    result = {
        "total_fleet_count": total_fleet,
        "active_vehicles": active_fleet,
        "inactive_vehicles": inactive_fleet,
        "idle_vehicles": idle_vehicles,
        "moving_vehicles": moving_vehicles,
        "route_completion_pct": float(kpi_row.get("route_completion_pct") or 0.0),
        "avg_utilization_pct": float(kpi_row.get("avg_utilization_pct") or 0.0),
    }
    if export == "json":
        return result
    return _export_rows([result], export=export, basename="dashboard-kpis", title="Dashboard KPI Summary")


@router.get("/v1/vehicles/{vehicle_id}/detail")
async def vehicle_detail(
    vehicle_id: UUID,
    from_ts: datetime | None = Query(default=None),
    to_ts: datetime | None = Query(default=None),
    history_limit: int = Query(default=100, ge=1, le=1000),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    vehicle = (await session.execute(select(VehicleORM).where(VehicleORM.id == vehicle_id))).scalar_one_or_none()
    if vehicle is None:
        raise HTTPException(status_code=404, detail=f"vehicle with id={vehicle_id} not found")

    vehicle_keys = [str(vehicle.id), vehicle.vehicle_number]
    assignment = (
        (
            await session.execute(
                select(DeviceVehicleAssignmentORM)
                .where(DeviceVehicleAssignmentORM.vehicle_id == vehicle.id, DeviceVehicleAssignmentORM.active.is_(True))
                .order_by(DeviceVehicleAssignmentORM.assigned_from.desc())
                .limit(1)
            )
        )
        .scalars()
        .first()
    )

    device: DeviceORM | None = None
    telemetry_keys = list(vehicle_keys)
    if assignment is not None:
        device = (await session.execute(select(DeviceORM).where(DeviceORM.id == assignment.device_id))).scalar_one_or_none()
        telemetry_keys.append(str(assignment.device_id))
    if device is not None:
        telemetry_keys.extend([str(device.id), device.imei])

    state = (
        (
            await session.execute(
                select(AnalyticsVehicleStateORM)
                .where(AnalyticsVehicleStateORM.vehicle_id.in_(vehicle_keys))
                .order_by(AnalyticsVehicleStateORM.updated_at.desc())
                .limit(1)
            )
        )
        .scalars()
        .first()
    )

    trip_stmt = (
        select(AnalyticsTripRecordORM)
        .where(AnalyticsTripRecordORM.vehicle_id.in_(vehicle_keys))
        .order_by(AnalyticsTripRecordORM.started_at.desc())
        .limit(history_limit)
    )
    idle_stmt = (
        select(AnalyticsIdleRecordORM)
        .where(AnalyticsIdleRecordORM.vehicle_id.in_(vehicle_keys))
        .order_by(AnalyticsIdleRecordORM.started_at.desc())
        .limit(history_limit)
    )
    route_stmt = (
        select(AnalyticsGeofenceEventORM)
        .where(AnalyticsGeofenceEventORM.vehicle_id.in_(vehicle_keys))
        .order_by(AnalyticsGeofenceEventORM.event_ts.desc())
        .limit(history_limit)
    )
    alert_stmt = (
        select(AlertORM)
        .where(AlertORM.vehicle_id.in_(vehicle_keys))
        .order_by(AlertORM.triggered_at.desc())
        .limit(history_limit)
    )

    if from_ts is not None:
        trip_stmt = trip_stmt.where(AnalyticsTripRecordORM.started_at >= from_ts)
        idle_stmt = idle_stmt.where(AnalyticsIdleRecordORM.started_at >= from_ts)
        route_stmt = route_stmt.where(AnalyticsGeofenceEventORM.event_ts >= from_ts)
        alert_stmt = alert_stmt.where(AlertORM.triggered_at >= from_ts)
    if to_ts is not None:
        trip_stmt = trip_stmt.where(AnalyticsTripRecordORM.started_at <= to_ts)
        idle_stmt = idle_stmt.where(AnalyticsIdleRecordORM.started_at <= to_ts)
        route_stmt = route_stmt.where(AnalyticsGeofenceEventORM.event_ts <= to_ts)
        alert_stmt = alert_stmt.where(AlertORM.triggered_at <= to_ts)

    telemetry_stmt = select(DeviceEventORM).where(DeviceEventORM.device_id.in_(telemetry_keys)).order_by(DeviceEventORM.ts.desc())
    if from_ts is not None:
        telemetry_stmt = telemetry_stmt.where(DeviceEventORM.ts >= from_ts)
    if to_ts is not None:
        telemetry_stmt = telemetry_stmt.where(DeviceEventORM.ts <= to_ts)
    telemetry_stmt = telemetry_stmt.limit(history_limit)

    return {
        "vehicle": _to_dict(vehicle),
        "device_assignment": _to_dict(assignment) if assignment is not None else None,
        "device": _to_dict(device) if device is not None else None,
        "current_state": _to_dict(state) if state is not None else None,
        "trip_history": [_to_dict(row) for row in (await session.execute(trip_stmt)).scalars().all()],
        "idle_history": [_to_dict(row) for row in (await session.execute(idle_stmt)).scalars().all()],
        "route_history": [_to_dict(row) for row in (await session.execute(route_stmt)).scalars().all()],
        "alerts": [_to_dict(row) for row in (await session.execute(alert_stmt)).scalars().all()],
        "telemetry_snapshots": [_to_dict(row) for row in (await session.execute(telemetry_stmt)).scalars().all()],
    }


@router.get("/v1/vehicles/search", response_model=PageResponse)
async def search_vehicles(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    vehicle_number: str | None = Query(default=None),
    imei: str | None = Query(default=None),
    vendor_id: UUID | None = Query(default=None),
    route_id: UUID | None = Query(default=None),
    zone_name: str | None = Query(default=None),
    ward_id: UUID | None = Query(default=None),
    operational_status: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    alert_category: str | None = Query(default=None),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse:
    stmt = (
        select(VehicleORM)
        .distinct()
        .join(WardORM, VehicleORM.ward_id == WardORM.id)
        .outerjoin(
            DeviceVehicleAssignmentORM,
            and_(
                DeviceVehicleAssignmentORM.vehicle_id == VehicleORM.id,
                DeviceVehicleAssignmentORM.active.is_(True),
            ),
        )
        .outerjoin(DeviceORM, DeviceORM.id == DeviceVehicleAssignmentORM.device_id)
    )

    if vehicle_number:
        stmt = stmt.where(VehicleORM.vehicle_number.ilike(f"%{vehicle_number.strip()}%"))
    if imei:
        stmt = stmt.where(DeviceORM.imei.ilike(f"%{imei.strip()}%"))
    if vendor_id is not None:
        stmt = stmt.where(VehicleORM.vendor_id == vendor_id)
    if route_id is not None:
        stmt = stmt.where(VehicleORM.route_id == route_id)
    if zone_name:
        stmt = stmt.where(WardORM.zone_name == zone_name)
    if ward_id is not None:
        stmt = stmt.where(VehicleORM.ward_id == ward_id)
    if operational_status:
        stmt = stmt.where(VehicleORM.operational_status == operational_status)

    if alert_category or date_from or date_to:
        alert_exists_stmt = select(AlertORM.id).where(
            or_(
                AlertORM.vehicle_id == cast(VehicleORM.id, String),
                AlertORM.vehicle_id == VehicleORM.vehicle_number,
            )
        )
        if alert_category:
            alert_exists_stmt = alert_exists_stmt.where(AlertORM.category == alert_category)
        if date_from is not None:
            alert_exists_stmt = alert_exists_stmt.where(AlertORM.triggered_at >= date_from)
        if date_to is not None:
            alert_exists_stmt = alert_exists_stmt.where(AlertORM.triggered_at <= date_to)
        stmt = stmt.where(alert_exists_stmt.exists())

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = int((await session.execute(count_stmt)).scalar_one())
    rows = (
        (
            await session.execute(
                stmt.order_by(VehicleORM.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return PageResponse(items=[_to_dict(row) for row in rows], page=page, page_size=page_size, total=total)
