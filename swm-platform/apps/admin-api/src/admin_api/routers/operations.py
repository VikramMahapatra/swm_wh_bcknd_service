from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import String, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from swm_db import (
    AlertActionORM,
    AlertORM,
    AnalyticsDailyKPIORM,
    AuditLogORM,
    OperationalCategoryORM,
    SystemConfigurationORM,
    get_db_session,
)

from admin_api.api_support import (
    MessageResponse,
    PageResponse,
    RoleContext,
    _actor_from_request,
    _export_rows,
    _list_entities,
    _rows_from_result,
    _to_dict,
    _write_audit_log,
    require_roles,
)

router = APIRouter()


class AlertIn(BaseModel):
    alert_type: str
    category: str
    title: str
    message: str | None = None
    severity: str = "medium"
    vehicle_id: str | None = None
    imei: str | None = None
    vendor_id: UUID | None = None
    route_id: UUID | None = None
    ward_id: UUID | None = None
    triggered_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AlertActionIn(BaseModel):
    actor: str | None = None
    notes: str | None = None
    escalation_status: str | None = None


class SystemConfigurationIn(BaseModel):
    config_key: str
    config_type: str
    description: str | None = None
    value: dict[str, Any] = Field(default_factory=dict)
    active: bool = True


class OperationalCategoryIn(BaseModel):
    category_code: str
    category_name: str
    description: str | None = None
    active: bool = True


@router.get("/v1/alerts")
async def list_alerts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=500),
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    category: str | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    from_ts: datetime | None = Query(default=None),
    to_ts: datetime | None = Query(default=None),
    export: str = Query(default="json", pattern="^(json|csv|xlsx|pdf)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    stmt = select(AlertORM)
    if status:
        stmt = stmt.where(AlertORM.status == status)
    if severity:
        stmt = stmt.where(AlertORM.severity == severity)
    if category:
        stmt = stmt.where(AlertORM.category == category)
    if vehicle_id:
        stmt = stmt.where(AlertORM.vehicle_id == vehicle_id)
    if from_ts is not None:
        stmt = stmt.where(AlertORM.triggered_at >= from_ts)
    if to_ts is not None:
        stmt = stmt.where(AlertORM.triggered_at <= to_ts)

    total = int((await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one())
    rows = (
        (await session.execute(stmt.order_by(AlertORM.triggered_at.desc()).offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )
    payload = [_to_dict(row) for row in rows]

    if export == "json":
        return {"items": payload, "total": total, "page": page, "page_size": page_size}
    return _export_rows(payload, export=export, basename="alerts", title="Alert Listing")


@router.post("/v1/alerts")
async def create_alert(
    payload: AlertIn,
    request: Request,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    actor = _actor_from_request(request)
    row = AlertORM(
        alert_type=payload.alert_type,
        category=payload.category,
        title=payload.title,
        message=payload.message,
        severity=payload.severity,
        status="open",
        vehicle_id=payload.vehicle_id,
        imei=payload.imei,
        vendor_id=payload.vendor_id,
        route_id=payload.route_id,
        ward_id=payload.ward_id,
        triggered_at=payload.triggered_at or datetime.now(UTC),
        metadata_json=payload.metadata,
    )
    session.add(row)
    await session.flush()
    session.add(
        AlertActionORM(
            alert_id=row.id,
            action_type="created",
            actor=actor,
            notes="alert created",
            payload_json={"status": row.status},
        )
    )
    await _write_audit_log(
        session,
        entity_type="alert",
        entity_id=str(row.id),
        action="create",
        actor=actor,
        before=None,
        after=_to_dict(row),
    )
    await session.commit()
    return _to_dict(row)


@router.post("/v1/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: UUID,
    payload: AlertActionIn,
    request: Request,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    row = (await session.execute(select(AlertORM).where(AlertORM.id == alert_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="alert not found")

    before = _to_dict(row)
    actor = payload.actor or _actor_from_request(request)
    row.status = "acknowledged"
    row.acknowledged_at = datetime.now(UTC)
    row.acknowledged_by = actor
    session.add(
        AlertActionORM(
            alert_id=row.id,
            action_type="acknowledged",
            actor=actor,
            notes=payload.notes,
            payload_json={"status": row.status},
        )
    )
    await _write_audit_log(
        session,
        entity_type="alert",
        entity_id=str(row.id),
        action="acknowledge",
        actor=actor,
        before=before,
        after=_to_dict(row),
    )
    await session.commit()
    return _to_dict(row)


@router.post("/v1/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: UUID,
    payload: AlertActionIn,
    request: Request,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    row = (await session.execute(select(AlertORM).where(AlertORM.id == alert_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="alert not found")

    before = _to_dict(row)
    actor = payload.actor or _actor_from_request(request)
    row.status = "resolved"
    row.resolved_at = datetime.now(UTC)
    row.resolved_by = actor
    session.add(
        AlertActionORM(
            alert_id=row.id,
            action_type="resolved",
            actor=actor,
            notes=payload.notes,
            payload_json={"status": row.status},
        )
    )
    await _write_audit_log(
        session,
        entity_type="alert",
        entity_id=str(row.id),
        action="resolve",
        actor=actor,
        before=before,
        after=_to_dict(row),
    )
    await session.commit()
    return _to_dict(row)


@router.post("/v1/alerts/{alert_id}/escalate")
async def escalate_alert(
    alert_id: UUID,
    payload: AlertActionIn,
    request: Request,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    row = (await session.execute(select(AlertORM).where(AlertORM.id == alert_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="alert not found")

    before = _to_dict(row)
    actor = payload.actor or _actor_from_request(request)
    row.status = "escalated"
    row.escalation_status = payload.escalation_status or "escalated"
    session.add(
        AlertActionORM(
            alert_id=row.id,
            action_type="escalated",
            actor=actor,
            notes=payload.notes,
            payload_json={"status": row.status, "escalation_status": row.escalation_status},
        )
    )
    await _write_audit_log(
        session,
        entity_type="alert",
        entity_id=str(row.id),
        action="escalate",
        actor=actor,
        before=before,
        after=_to_dict(row),
    )
    await session.commit()
    return _to_dict(row)


@router.get("/v1/alerts/{alert_id}/audit")
async def get_alert_audit(
    alert_id: UUID,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    actions = (
        (await session.execute(select(AlertActionORM).where(AlertActionORM.alert_id == alert_id).order_by(AlertActionORM.created_at.desc())))
        .scalars()
        .all()
    )
    logs = (
        (
            await session.execute(
                select(AuditLogORM)
                .where(AuditLogORM.entity_type == "alert", AuditLogORM.entity_id == str(alert_id))
                .order_by(AuditLogORM.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return {
        "alert_id": str(alert_id),
        "actions": [_to_dict(row) for row in actions],
        "audit_logs": [_to_dict(row) for row in logs],
    }


@router.get("/v1/configurations", response_model=PageResponse)
async def list_configurations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    config_type: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    q: str | None = Query(default=None),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse:
    return await _list_entities(
        session,
        SystemConfigurationORM,
        page=page,
        page_size=page_size,
        q=q,
        sort_by="updated_at",
        sort_order="desc",
        filters={"config_type": config_type, "active": active},
    )


@router.post("/v1/configurations")
async def create_configuration(
    payload: SystemConfigurationIn,
    request: Request,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    actor = _actor_from_request(request)
    row = SystemConfigurationORM(
        config_key=payload.config_key,
        config_type=payload.config_type,
        description=payload.description,
        value_json=payload.value,
        active=payload.active,
        updated_by=actor,
    )
    session.add(row)
    await session.flush()
    await _write_audit_log(
        session,
        entity_type="configuration",
        entity_id=str(row.id),
        action="create",
        actor=actor,
        before=None,
        after=_to_dict(row),
    )
    await session.commit()
    return _to_dict(row)


@router.put("/v1/configurations/{config_id}")
async def update_configuration(
    config_id: UUID,
    payload: SystemConfigurationIn,
    request: Request,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    row = (await session.execute(select(SystemConfigurationORM).where(SystemConfigurationORM.id == config_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="configuration not found")

    before = _to_dict(row)
    actor = _actor_from_request(request)
    row.config_key = payload.config_key
    row.config_type = payload.config_type
    row.description = payload.description
    row.value_json = payload.value
    row.active = payload.active
    row.updated_by = actor
    await _write_audit_log(
        session,
        entity_type="configuration",
        entity_id=str(row.id),
        action="update",
        actor=actor,
        before=before,
        after=_to_dict(row),
    )
    await session.commit()
    return _to_dict(row)


@router.delete("/v1/configurations/{config_id}", response_model=MessageResponse)
async def delete_configuration(
    config_id: UUID,
    request: Request,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    row = (await session.execute(select(SystemConfigurationORM).where(SystemConfigurationORM.id == config_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="configuration not found")
    before = _to_dict(row)
    session.delete(row)
    await _write_audit_log(
        session,
        entity_type="configuration",
        entity_id=str(config_id),
        action="delete",
        actor=_actor_from_request(request),
        before=before,
        after=None,
    )
    await session.commit()
    return MessageResponse(message="deleted")


@router.get("/v1/operational-categories", response_model=PageResponse)
async def list_operational_categories(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse:
    return await _list_entities(
        session,
        OperationalCategoryORM,
        page=page,
        page_size=page_size,
        q=q,
        sort_by="created_at",
        sort_order="desc",
        filters={"active": active},
    )


@router.post("/v1/operational-categories")
async def create_operational_category(
    payload: OperationalCategoryIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    row = OperationalCategoryORM(
        category_code=payload.category_code,
        category_name=payload.category_name,
        description=payload.description,
        active=payload.active,
    )
    session.add(row)
    await session.commit()
    return _to_dict(row)


@router.put("/v1/operational-categories/{category_id}")
async def update_operational_category(
    category_id: UUID,
    payload: OperationalCategoryIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    row = (await session.execute(select(OperationalCategoryORM).where(OperationalCategoryORM.id == category_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="operational category not found")
    row.category_code = payload.category_code
    row.category_name = payload.category_name
    row.description = payload.description
    row.active = payload.active
    await session.commit()
    return _to_dict(row)


@router.delete("/v1/operational-categories/{category_id}", response_model=MessageResponse)
async def delete_operational_category(
    category_id: UUID,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    row = (await session.execute(select(OperationalCategoryORM).where(OperationalCategoryORM.id == category_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="operational category not found")
    session.delete(row)
    await session.commit()
    return MessageResponse(message="deleted")


@router.get("/v1/reports/operations/export")
async def export_operational_reports(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    export: str = Query(default="csv", pattern="^(csv|xlsx|pdf|json)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    kpi_stmt = (
        select(
            AnalyticsDailyKPIORM.metric_date,
            func.sum(AnalyticsDailyKPIORM.trips_count).label("trips_count"),
            func.sum(AnalyticsDailyKPIORM.distance_km).label("distance_km"),
            func.avg(AnalyticsDailyKPIORM.utilization_pct).label("utilization_pct"),
        )
        .group_by(AnalyticsDailyKPIORM.metric_date)
        .order_by(AnalyticsDailyKPIORM.metric_date.desc())
    )
    if date_from is not None:
        kpi_stmt = kpi_stmt.where(AnalyticsDailyKPIORM.metric_date >= date_from)
    if date_to is not None:
        kpi_stmt = kpi_stmt.where(AnalyticsDailyKPIORM.metric_date <= date_to)
    kpi_rows = _rows_from_result(await session.execute(kpi_stmt))

    alert_stmt = (
        select(
            cast(func.date_trunc("day", AlertORM.triggered_at), String).label("metric_date"),
            func.count(AlertORM.id).label("alerts_total"),
            func.sum(case((AlertORM.status == "resolved", 1), else_=0)).label("alerts_resolved"),
            func.sum(case((AlertORM.status == "open", 1), else_=0)).label("alerts_open"),
        )
        .group_by(cast(func.date_trunc("day", AlertORM.triggered_at), String))
        .order_by(cast(func.date_trunc("day", AlertORM.triggered_at), String).desc())
    )
    if date_from is not None:
        alert_stmt = alert_stmt.where(AlertORM.triggered_at >= datetime.combine(date_from, datetime.min.time(), tzinfo=UTC))
    if date_to is not None:
        alert_stmt = alert_stmt.where(AlertORM.triggered_at <= datetime.combine(date_to, datetime.max.time(), tzinfo=UTC))
    alert_rows = _rows_from_result(await session.execute(alert_stmt))
    alerts_by_date = {str(row["metric_date"]): row for row in alert_rows}

    merged: list[dict[str, Any]] = []
    for row in kpi_rows:
        key = str(row["metric_date"])
        alert = alerts_by_date.get(key, {})
        merged.append(
            {
                "metric_date": key,
                "trips_count": row.get("trips_count", 0),
                "distance_km": row.get("distance_km", 0),
                "utilization_pct": row.get("utilization_pct", 0),
                "alerts_total": alert.get("alerts_total", 0),
                "alerts_open": alert.get("alerts_open", 0),
                "alerts_resolved": alert.get("alerts_resolved", 0),
            }
        )

    if export == "json":
        return {"items": merged, "total": len(merged)}
    return _export_rows(merged, export=export, basename="operational-report", title="Operational Report")


@router.get("/v1/audit-logs")
async def list_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=500),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    actor: str | None = Query(default=None),
    from_ts: datetime | None = Query(default=None),
    to_ts: datetime | None = Query(default=None),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = select(AuditLogORM)
    if entity_type:
        stmt = stmt.where(AuditLogORM.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLogORM.entity_id == entity_id)
    if actor:
        stmt = stmt.where(AuditLogORM.actor == actor)
    if from_ts is not None:
        stmt = stmt.where(AuditLogORM.created_at >= from_ts)
    if to_ts is not None:
        stmt = stmt.where(AuditLogORM.created_at <= to_ts)

    total = int((await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one())
    rows = (
        (await session.execute(stmt.order_by(AuditLogORM.created_at.desc()).offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )
    return {"items": [_to_dict(row) for row in rows], "total": total, "page": page, "page_size": page_size}
