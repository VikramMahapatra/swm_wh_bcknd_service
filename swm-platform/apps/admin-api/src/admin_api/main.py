from collections.abc import Awaitable, Callable
from csv import DictReader, DictWriter
from datetime import UTC, date, datetime
from io import BytesIO, StringIO
import os
from typing import Any
from uuid import UUID

import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Float, String, and_, asc, case, cast, desc, func, or_, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response
from swm_common import (
    REQUEST_COUNTER,
    configure_logging,
    get_logger,
    get_settings,
    metrics_response,
)
from swm_db import (
    AlertActionORM,
    AlertORM,
    AnalyticsDailyKPIORM,
    AnalyticsGeofenceEventORM,
    AnalyticsIdleRecordORM,
    AnalyticsOverspeedEventORM,
    AnalyticsTripRecordORM,
    AnalyticsVehicleStateORM,
    AuditLogORM,
    AssignmentCreateInput,
    ContractorORM,
    ContractorRepository,
    DeviceORM,
    DeviceRepository,
    DeviceEventORM,
    DeviceVehicleAssignmentORM,
    DeviceVehicleAssignmentRepository,
    DeviceVehicleAssignmentService,
    GeofenceORM,
    GeofenceRepository,
    OperationalCategoryORM,
    RouteORM,
    RouteRepository,
    SystemConfigurationORM,
    VehicleORM,
    VehicleRepository,
    VendorORM,
    VendorRepository,
    WardORM,
    WardRepository,
    get_db_session,
)
from swm_redis import RedisClient, RealtimeCacheKeys

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("admin_api")

app = FastAPI(title="SWM Admin API", version="0.1.0")

_cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8080,http://127.0.0.1:8080",
    ).split(",")
    if origin.strip()
]

# CORS origins should represent browser UI origins, not API service ports.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = RedisClient.from_url(settings.redis_url)

INGESTION_QUARANTINE_STREAM = "gps.telemetry.retry"
INGESTION_DLQ_STREAM = "gps.telemetry.failed"


class PageResponse(BaseModel):
    items: list[dict[str, Any]]
    page: int
    page_size: int
    total: int


class RoleContext(BaseModel):
    role: str


class MessageResponse(BaseModel):
    message: str


class IngestionFailureRecord(BaseModel):
    id: str
    source: str
    stage: str | None = None
    vendor_id: str | None = None
    request_id: str | None = None
    reason: str | None = None
    retryable: bool | None = None
    item_index: int | None = None
    stored_at: datetime | None = None
    payload_raw: str | None = None


class IngestionFailurePage(BaseModel):
    items: list[IngestionFailureRecord]
    total: int
    source: str


class LiveMapTruckPosition(BaseModel):
    imei: str
    device_id: str | None = None
    vehicle_id: str | None = None
    lat: float
    lng: float
    speed_kph: float
    heading: int
    ignition: bool
    event_ts: datetime
    status: str | None = None
    vendor_id: str | None = None


class LiveMapSnapshotResponse(BaseModel):
    items: list[LiveMapTruckPosition]
    total: int


def _to_dict(obj: Any) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for col in obj.__table__.columns:
        if col.name == "metadata" and hasattr(obj, "metadata_json"):
            value = getattr(obj, "metadata_json")
        else:
            value = getattr(obj, col.name)
        if isinstance(value, UUID):
            data[col.name] = str(value)
        elif isinstance(value, datetime):
            data[col.name] = value.isoformat()
        else:
            data[col.name] = value
    return data


def _to_str(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _to_bool(value: Any) -> bool | None:
    if value is None:
        return None
    raw = _to_str(value).strip().lower()
    if raw in {"1", "true", "yes", "y", "on"}:
        return True
    if raw in {"0", "false", "no", "n", "off"}:
        return False
    return None


def _to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    raw = _to_str(value).strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _normalize_stream_fields(fields: Any) -> dict[str, Any]:
    if not isinstance(fields, dict):
        return {}
    normalized: dict[str, Any] = {}
    for key, value in fields.items():
        normalized[_to_str(key)] = value
    return normalized


async def _read_failure_stream(stream: str, *, source: str, limit: int) -> list[IngestionFailureRecord]:
    rows = await redis_client.xrange(stream, count=limit)
    items: list[IngestionFailureRecord] = []
    for entry in rows:
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            continue
        entry_id, fields = entry
        data = _normalize_stream_fields(fields)
        item_index: int | None = None
        if data.get("item_index") is not None and _to_str(data.get("item_index")).isdigit():
            item_index = int(_to_str(data.get("item_index")))
        items.append(
            IngestionFailureRecord(
                id=_to_str(entry_id),
                source=source,
                stage=_to_str(data["stage"]) if data.get("stage") is not None else None,
                vendor_id=_to_str(data["vendor_id"]) if data.get("vendor_id") is not None else None,
                request_id=_to_str(data["request_id"]) if data.get("request_id") is not None else None,
                reason=_to_str(data["reason"]) if data.get("reason") is not None else None,
                retryable=_to_bool(data.get("retryable")),
                item_index=item_index,
                stored_at=_to_datetime(data.get("stored_at")),
                payload_raw=_to_str(data["payload_raw"]) if data.get("payload_raw") is not None else None,
            )
        )
    return items


def _parse_csv(file_content: str) -> list[dict[str, str]]:
    reader = DictReader(StringIO(file_content))
    return [dict(row) for row in reader]


def _parse_csv_with_required(file_content: str, *, required_columns: set[str]) -> list[dict[str, str]]:
    reader = DictReader(StringIO(file_content))
    headers = set(reader.fieldnames or [])
    missing = sorted(required_columns - headers)
    if missing:
        raise HTTPException(status_code=400, detail=f"missing csv columns: {', '.join(missing)}")
    return [dict(row) for row in reader]


def _parse_bool(value: str | None, *, default: bool = True) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_uuid(value: str | None) -> UUID | None:
    if value is None or value == "":
        return None
    return UUID(value)


def _allowed_sort(model: Any) -> set[str]:
    return {c.name for c in model.__table__.columns}


def _csv_response(rows: list[dict[str, Any]], filename: str) -> Response:
    output = StringIO()
    if rows:
        writer = DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _xlsx_response(rows: list[dict[str, Any]], filename: str) -> Response:
    try:
        from openpyxl import Workbook
    except ImportError as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail="openpyxl is required for xlsx export") from exc

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Report"

    if rows:
        headers = list(rows[0].keys())
        sheet.append(headers)
        for row in rows:
            sheet.append([row.get(h) for h in headers])

    output = BytesIO()
    workbook.save(output)
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _pdf_response(rows: list[dict[str, Any]], *, filename: str, title: str) -> Response:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail="reportlab is required for pdf export") from exc

    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    x = 40
    y = height - 40

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x, y, title)
    y -= 24
    pdf.setFont("Helvetica", 9)

    if not rows:
        pdf.drawString(x, y, "No data")
    else:
        for row in rows:
            if y < 50:
                pdf.showPage()
                y = height - 40
                pdf.setFont("Helvetica", 9)
            line = " | ".join(f"{k}: {row.get(k)}" for k in row)
            pdf.drawString(x, y, line[:170])
            y -= 14

    pdf.save()
    return Response(
        content=output.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _export_rows(rows: list[dict[str, Any]], *, export: str, basename: str, title: str) -> Any:
    if export == "csv":
        return _csv_response(rows, f"{basename}.csv")
    if export == "xlsx":
        return _xlsx_response(rows, f"{basename}.xlsx")
    if export == "pdf":
        return _pdf_response(rows, filename=f"{basename}.pdf", title=title)
    return {"items": rows, "total": len(rows)}


def _actor_from_request(request: Request) -> str:
    actor = request.headers.get("x-user") or request.headers.get("x-actor")
    return actor if actor else "system"


async def _write_audit_log(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    actor: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    metadata: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditLogORM(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor=actor,
            before_json=before,
            after_json=after,
            metadata_json=metadata or {},
        )
    )
    await session.flush()


def _serialize_scalar(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def _rows_from_result(result: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in result.mappings().all():
        rows.append({key: _serialize_scalar(value) for key, value in dict(row).items()})
    return rows


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


async def _list_entities(  # noqa: PLR0913
    session: AsyncSession,
    model: Any,
    *,
    page: int,
    page_size: int,
    q: str | None,
    sort_by: str,
    sort_order: str,
    filters: dict[str, Any],
) -> PageResponse:
    stmt = select(model)

    for key, value in filters.items():
        if value is None:
            continue
        stmt = stmt.where(getattr(model, key) == value)

    if q:
        q_like = f"%{q.strip()}%"
        searchable = [
            col.name
            for col in model.__table__.columns
            if isinstance(col.type, String) and col.name not in {"webhook_secret", "signature_key"}
        ]
        if searchable:
            stmt = stmt.where(or_(*[cast(getattr(model, c), String).ilike(q_like) for c in searchable]))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = int((await session.execute(count_stmt)).scalar_one())

    sort_fields = _allowed_sort(model)
    if sort_by not in sort_fields:
        sort_by = "created_at" if "created_at" in sort_fields else next(iter(sort_fields))
    order_col = getattr(model, sort_by)
    stmt = stmt.order_by(desc(order_col) if sort_order == "desc" else asc(order_col))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    rows = list((await session.execute(stmt)).scalars().all())
    return PageResponse(items=[_to_dict(r) for r in rows], page=page, page_size=page_size, total=total)


async def get_role_context(request: Request) -> RoleContext:
    # RBAC-ready hook: replace with JWT/OPA integration later.
    role = request.headers.get("x-role", "admin")
    return RoleContext(role=role)


def require_roles(*roles: str):
    async def _require(ctx: RoleContext = Depends(get_role_context)) -> RoleContext:
        if ctx.role not in roles:
            raise HTTPException(status_code=403, detail="forbidden")
        return ctx

    return _require


def _raise_not_found(entity: str, entity_id: UUID) -> None:
    raise HTTPException(status_code=404, detail=f"{entity} with id={entity_id} not found")


async def _fetch_or_404(getter: Callable[[UUID], Awaitable[Any | None]], entity: str, entity_id: UUID) -> Any:
    row = await getter(entity_id)
    if row is None:
        _raise_not_found(entity, entity_id)
    return row


class VendorIn(BaseModel):
    vendor_code: str
    vendor_name: str
    contact_person: str | None = None
    email: str | None = None
    phone: str | None = None
    webhook_secret: str | None = None
    signature_key: str | None = None
    allowed_ips: list[str] = Field(default_factory=list)
    auth_type: str = "header"
    callback_format: dict[str, Any] = Field(default_factory=dict)
    active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeviceIn(BaseModel):
    vendor_id: UUID
    imei: str
    serial_no: str | None = None
    model: str | None = None
    manufacturer: str | None = None
    firmware_version: str | None = None
    sim_number: str | None = None
    installed_on: datetime | None = None
    activated_on: datetime | None = None
    last_seen: datetime | None = None
    battery_percent: float | None = None
    signal_strength: float | None = None
    health_status: str = "healthy"
    active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class VehicleIn(BaseModel):
    vehicle_number: str
    registration_number: str
    contractor_id: UUID
    ward_id: UUID
    route_id: UUID | None = None
    truck_type: str | None = None
    capacity_kg: float = 0
    capacity_cubic_meter: float = 0
    fuel_type: str = "diesel"
    operational_status: str = "operational"
    chassis_number: str | None = None
    engine_number: str | None = None
    manufacture_year: int | None = None
    active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContractorIn(BaseModel):
    contractor_code: str
    contractor_name: str
    contact: str | None = None
    sla_details: dict[str, Any] = Field(default_factory=dict)
    active: bool = True


class WardIn(BaseModel):
    ward_code: str
    ward_name: str
    zone_name: str
    active: bool = True


class RouteIn(BaseModel):
    route_code: str
    route_name: str
    expected_distance_km: float = 0
    expected_duration_min: int = 0
    start_point: str
    end_point: str
    active: bool = True


class GeofenceIn(BaseModel):
    geofence_code: str
    geofence_name: str
    type: str
    geometry_type: str
    center_lat: float | None = None
    center_lng: float | None = None
    radius_meter: float | None = None
    polygon: dict[str, Any] | None = None
    ward_id: UUID | None = None
    active: bool = True


class DeviceAssignmentIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    device_id: UUID
    vehicle_id: UUID
    assigned_from: datetime | None = None
    assigned_to: datetime | None = None
    active: bool = True
    remarks: str | None = None


class AlertIn(BaseModel):
    alert_type: str
    category: str
    title: str
    message: str | None = None
    severity: str = "medium"
    vehicle_id: str | None = None
    imei: str | None = None
    contractor_id: UUID | None = None
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


@app.middleware("http")
async def metrics_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    response = await call_next(request)
    REQUEST_COUNTER.labels(
        app="admin-api",
        method=request.method,
        path=request.url.path,
        status=str(response.status_code),
    ).inc()
    return response


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "admin-api"}


@app.get("/metrics")
async def metrics() -> Response:
    return metrics_response()


@app.get("/v1/platform/status")
async def platform_status() -> dict[str, str]:
    now = datetime.now(tz=UTC).isoformat()
    logger.info("platform_status_requested", ts=now)
    return {"status": "operational", "timestamp": now}


@app.get("/v1/realtime/trucks", response_model=LiveMapSnapshotResponse)
async def list_realtime_trucks(
    limit: int = Query(default=10000, ge=1, le=50000),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
) -> LiveMapSnapshotResponse:
    keys = RealtimeCacheKeys()
    pattern = keys.truck_last("*")

    cursor = 0
    matched_keys: list[str] = []
    while True:
        cursor, batch = await redis_client.scan(cursor=cursor, match=pattern, count=1000)
        if batch:
            matched_keys.extend(batch)
            if len(matched_keys) >= limit:
                matched_keys = matched_keys[:limit]
                break
        if cursor == 0:
            break

    last_payloads = await redis_client.mget_json(*matched_keys)
    truck_rows: list[tuple[str, dict[str, Any], dict[str, Any], datetime]] = []
    state_keys: list[str] = []

    for key, payload in zip(matched_keys, last_payloads, strict=False):
        if not isinstance(payload, dict):
            continue

        attributes_raw = payload.get("attributes")
        attributes = attributes_raw if isinstance(attributes_raw, dict) else {}

        try:
            event_ts = datetime.fromisoformat(str(payload.get("ts")))
            imei = str(payload.get("imei") or key.rsplit(":", 1)[-1])
        except Exception:
            continue

        truck_rows.append((imei, payload, attributes, event_ts))
        state_keys.append(keys.truck_state(imei))

    state_payloads = await redis_client.mget_json(*state_keys)

    items: list[LiveMapTruckPosition] = []
    for (imei, payload, attributes, event_ts), state_payload in zip(truck_rows, state_payloads, strict=False):
        try:
            status = None
            if isinstance(state_payload, dict) and state_payload.get("status") is not None:
                status = str(state_payload.get("status"))

            items.append(
                LiveMapTruckPosition(
                    imei=imei,
                    device_id=(str(payload["device_id"]) if payload.get("device_id") is not None else None),
                    vehicle_id=(str(attributes["vehicle_id"]) if attributes.get("vehicle_id") is not None else None),
                    lat=float(payload.get("lat")),
                    lng=float(payload.get("lon")),
                    speed_kph=float(payload.get("speed_kph", 0.0)),
                    heading=int(payload.get("heading", 0)),
                    ignition=bool(payload.get("ignition", False)),
                    event_ts=event_ts,
                    status=status,
                    vendor_id=(str(attributes["vendor_id"]) if attributes.get("vendor_id") is not None else None),
                )
            )
        except Exception:
            continue

    items.sort(key=lambda truck: truck.imei)
    return LiveMapSnapshotResponse(items=items, total=len(items))


@app.get("/v1/ingestion/failures", response_model=IngestionFailurePage)
async def list_ingestion_failures(
    source: str = Query(default="all", pattern="^(all|quarantine|dlq)$"),
    limit: int = Query(default=100, ge=1, le=500),
    vendor_id: str | None = Query(default=None),
    retryable: bool | None = Query(default=None),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
) -> IngestionFailurePage:
    items: list[IngestionFailureRecord] = []

    if source in {"all", "quarantine"}:
        items.extend(
            await _read_failure_stream(
                INGESTION_QUARANTINE_STREAM,
                source="quarantine",
                limit=limit,
            )
        )
    if source in {"all", "dlq"}:
        items.extend(
            await _read_failure_stream(
                INGESTION_DLQ_STREAM,
                source="dlq",
                limit=limit,
            )
        )

    if vendor_id is not None:
        key = vendor_id.strip().lower()
        items = [item for item in items if (item.vendor_id or "").strip().lower() == key]
    if retryable is not None:
        items = [item for item in items if item.retryable is retryable]

    items.sort(key=lambda item: item.id, reverse=True)
    trimmed = items[:limit]
    return IngestionFailurePage(items=trimmed, total=len(trimmed), source=source)


@app.get("/vendors", response_model=PageResponse)
async def list_vendors(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    auth_type: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse:
    return await _list_entities(
        session,
        VendorORM,
        page=page,
        page_size=page_size,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
        filters={"active": active, "auth_type": auth_type},
    )


@app.post("/vendors")
async def create_vendor(
    payload: VendorIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = VendorRepository(session)
    row = await repo.create(
        vendor_code=payload.vendor_code,
        vendor_name=payload.vendor_name,
        contact_person=payload.contact_person,
        email=payload.email,
        phone=payload.phone,
        webhook_secret=payload.webhook_secret,
        signature_key=payload.signature_key,
        allowed_ips=payload.allowed_ips,
        auth_type=payload.auth_type,
        callback_format=payload.callback_format,
        active=payload.active,
        metadata_json=payload.metadata,
    )
    return _to_dict(row)


@app.get("/vendors/{vendor_id}")
async def get_vendor(
    vendor_id: UUID,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = VendorRepository(session)
    row = await _fetch_or_404(repo.get_by_id, "vendor", vendor_id)
    return _to_dict(row)


@app.put("/vendors/{vendor_id}")
async def update_vendor(
    vendor_id: UUID,
    payload: VendorIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = VendorRepository(session)
    try:
        row = await repo.update(
            vendor_id,
            vendor_code=payload.vendor_code,
            vendor_name=payload.vendor_name,
            contact_person=payload.contact_person,
            email=payload.email,
            phone=payload.phone,
            webhook_secret=payload.webhook_secret,
            signature_key=payload.signature_key,
            allowed_ips=payload.allowed_ips,
            auth_type=payload.auth_type,
            callback_format=payload.callback_format,
            active=payload.active,
            metadata_json=payload.metadata,
        )
    except NoResultFound:
        _raise_not_found("vendor", vendor_id)
    return _to_dict(row)


@app.delete("/vendors/{vendor_id}", response_model=MessageResponse)
async def delete_vendor(
    vendor_id: UUID,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    repo = VendorRepository(session)
    try:
        await repo.delete(vendor_id)
    except NoResultFound:
        _raise_not_found("vendor", vendor_id)
    return MessageResponse(message="deleted")


@app.post("/vendors/import")
async def bulk_import_vendors(
    file: UploadFile = File(...),
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    content = (await file.read()).decode("utf-8")
    rows = _parse_csv_with_required(content, required_columns={"vendor_code", "vendor_name"})
    repo = VendorRepository(session)
    created = await repo.bulk_create(
        [
            {
                "vendor_code": r["vendor_code"],
                "vendor_name": r["vendor_name"],
                "contact_person": r.get("contact_person") or None,
                "email": r.get("email") or None,
                "phone": r.get("phone") or None,
                "webhook_secret": r.get("webhook_secret") or None,
                "signature_key": r.get("signature_key") or None,
                "allowed_ips": [ip.strip() for ip in (r.get("allowed_ips") or "").split(";") if ip.strip()],
                "auth_type": r.get("auth_type") or "header",
                "callback_format": {},
                "active": _parse_bool(r.get("active"), default=True),
                "metadata_json": {},
            }
            for r in rows
        ]
    )
    return {"created": len(created)}


@app.get("/devices", response_model=PageResponse)
async def list_devices(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    vendor_id: UUID | None = Query(default=None),
    health_status: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse:
    return await _list_entities(
        session,
        DeviceORM,
        page=page,
        page_size=page_size,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
        filters={"active": active, "vendor_id": vendor_id, "health_status": health_status},
    )


@app.post("/devices")
async def create_device(
    payload: DeviceIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = DeviceRepository(session)
    row = await repo.create(
        vendor_id=payload.vendor_id,
        imei=payload.imei,
        serial_no=payload.serial_no,
        model=payload.model,
        manufacturer=payload.manufacturer,
        firmware_version=payload.firmware_version,
        sim_number=payload.sim_number,
        installed_on=payload.installed_on,
        activated_on=payload.activated_on,
        last_seen=payload.last_seen,
        battery_percent=payload.battery_percent,
        signal_strength=payload.signal_strength,
        health_status=payload.health_status,
        active=payload.active,
        metadata_json=payload.metadata,
    )
    return _to_dict(row)


@app.get("/devices/{device_id}")
async def get_device(
    device_id: UUID,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = DeviceRepository(session)
    row = await _fetch_or_404(repo.get_by_id, "device", device_id)
    return _to_dict(row)


@app.put("/devices/{device_id}")
async def update_device(
    device_id: UUID,
    payload: DeviceIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = DeviceRepository(session)
    try:
        row = await repo.update(
            device_id,
            vendor_id=payload.vendor_id,
            imei=payload.imei,
            serial_no=payload.serial_no,
            model=payload.model,
            manufacturer=payload.manufacturer,
            firmware_version=payload.firmware_version,
            sim_number=payload.sim_number,
            installed_on=payload.installed_on,
            activated_on=payload.activated_on,
            last_seen=payload.last_seen,
            battery_percent=payload.battery_percent,
            signal_strength=payload.signal_strength,
            health_status=payload.health_status,
            active=payload.active,
            metadata_json=payload.metadata,
        )
    except NoResultFound:
        _raise_not_found("device", device_id)
    return _to_dict(row)


@app.delete("/devices/{device_id}", response_model=MessageResponse)
async def delete_device(
    device_id: UUID,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    repo = DeviceRepository(session)
    try:
        await repo.delete(device_id)
    except NoResultFound:
        _raise_not_found("device", device_id)
    return MessageResponse(message="deleted")


@app.post("/devices/import")
async def bulk_import_devices(
    file: UploadFile = File(...),
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    content = (await file.read()).decode("utf-8")
    rows = _parse_csv_with_required(content, required_columns={"vendor_id", "imei"})
    repo = DeviceRepository(session)
    created = await repo.bulk_create(
        [
            {
                "vendor_id": UUID(r["vendor_id"]),
                "imei": r["imei"],
                "serial_no": r.get("serial_no") or None,
                "model": r.get("model") or None,
                "manufacturer": r.get("manufacturer") or None,
                "firmware_version": r.get("firmware_version") or None,
                "sim_number": r.get("sim_number") or None,
                "health_status": r.get("health_status") or "healthy",
                "active": _parse_bool(r.get("active"), default=True),
                "metadata_json": {},
            }
            for r in rows
        ]
    )
    return {"created": len(created)}


@app.get("/vehicles", response_model=PageResponse)
async def list_vehicles(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    contractor_id: UUID | None = Query(default=None),
    ward_id: UUID | None = Query(default=None),
    route_id: UUID | None = Query(default=None),
    fuel_type: str | None = Query(default=None),
    operational_status: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse:
    return await _list_entities(
        session,
        VehicleORM,
        page=page,
        page_size=page_size,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
        filters={
            "active": active,
            "contractor_id": contractor_id,
            "ward_id": ward_id,
            "route_id": route_id,
            "fuel_type": fuel_type,
            "operational_status": operational_status,
        },
    )


@app.post("/vehicles")
async def create_vehicle(
    payload: VehicleIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = VehicleRepository(session)
    row = await repo.create(
        vehicle_number=payload.vehicle_number,
        registration_number=payload.registration_number,
        truck_type=payload.truck_type,
        capacity_kg=payload.capacity_kg,
        capacity_cubic_meter=payload.capacity_cubic_meter,
        contractor_id=payload.contractor_id,
        ward_id=payload.ward_id,
        route_id=payload.route_id,
        fuel_type=payload.fuel_type,
        operational_status=payload.operational_status,
        chassis_number=payload.chassis_number,
        engine_number=payload.engine_number,
        manufacture_year=payload.manufacture_year,
        active=payload.active,
        metadata_json=payload.metadata,
    )
    return _to_dict(row)


@app.get("/vehicles/{vehicle_id}")
async def get_vehicle(
    vehicle_id: UUID,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = VehicleRepository(session)
    row = await _fetch_or_404(repo.get_by_id, "vehicle", vehicle_id)
    return _to_dict(row)


@app.put("/vehicles/{vehicle_id}")
async def update_vehicle(
    vehicle_id: UUID,
    payload: VehicleIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = VehicleRepository(session)
    try:
        row = await repo.update(
            vehicle_id,
            vehicle_number=payload.vehicle_number,
            registration_number=payload.registration_number,
            truck_type=payload.truck_type,
            capacity_kg=payload.capacity_kg,
            capacity_cubic_meter=payload.capacity_cubic_meter,
            contractor_id=payload.contractor_id,
            ward_id=payload.ward_id,
            route_id=payload.route_id,
            fuel_type=payload.fuel_type,
            operational_status=payload.operational_status,
            chassis_number=payload.chassis_number,
            engine_number=payload.engine_number,
            manufacture_year=payload.manufacture_year,
            active=payload.active,
            metadata_json=payload.metadata,
        )
    except NoResultFound:
        _raise_not_found("vehicle", vehicle_id)
    return _to_dict(row)


@app.delete("/vehicles/{vehicle_id}", response_model=MessageResponse)
async def delete_vehicle(
    vehicle_id: UUID,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    repo = VehicleRepository(session)
    try:
        await repo.delete(vehicle_id)
    except NoResultFound:
        _raise_not_found("vehicle", vehicle_id)
    return MessageResponse(message="deleted")


@app.post("/vehicles/import")
async def bulk_import_vehicles(
    file: UploadFile = File(...),
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    content = (await file.read()).decode("utf-8")
    rows = _parse_csv_with_required(
        content,
        required_columns={"vehicle_number", "registration_number", "contractor_id", "ward_id"},
    )
    repo = VehicleRepository(session)
    created = await repo.bulk_create(
        [
            {
                "vehicle_number": r["vehicle_number"],
                "registration_number": r["registration_number"],
                "contractor_id": UUID(r["contractor_id"]),
                "ward_id": UUID(r["ward_id"]),
                "route_id": _parse_uuid(r.get("route_id")),
                "truck_type": r.get("truck_type") or None,
                "capacity_kg": float(r.get("capacity_kg") or 0),
                "capacity_cubic_meter": float(r.get("capacity_cubic_meter") or 0),
                "fuel_type": r.get("fuel_type") or "diesel",
                "operational_status": r.get("operational_status") or "operational",
                "chassis_number": r.get("chassis_number") or None,
                "engine_number": r.get("engine_number") or None,
                "manufacture_year": int(r["manufacture_year"]) if r.get("manufacture_year") else None,
                "active": _parse_bool(r.get("active"), default=True),
                "metadata_json": {},
            }
            for r in rows
        ]
    )
    return {"created": len(created)}


@app.get("/routes", response_model=PageResponse)
async def list_routes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse:
    return await _list_entities(
        session,
        RouteORM,
        page=page,
        page_size=page_size,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
        filters={"active": active},
    )


@app.post("/routes")
async def create_route(
    payload: RouteIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = RouteRepository(session)
    row = await repo.create(
        route_code=payload.route_code,
        route_name=payload.route_name,
        expected_distance_km=payload.expected_distance_km,
        expected_duration_min=payload.expected_duration_min,
        start_point=payload.start_point,
        end_point=payload.end_point,
        active=payload.active,
    )
    return _to_dict(row)


@app.get("/routes/{route_id}")
async def get_route(
    route_id: UUID,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = RouteRepository(session)
    row = await _fetch_or_404(repo.get_by_id, "route", route_id)
    return _to_dict(row)


@app.put("/routes/{route_id}")
async def update_route(
    route_id: UUID,
    payload: RouteIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = RouteRepository(session)
    try:
        row = await repo.update(
            route_id,
            route_code=payload.route_code,
            route_name=payload.route_name,
            expected_distance_km=payload.expected_distance_km,
            expected_duration_min=payload.expected_duration_min,
            start_point=payload.start_point,
            end_point=payload.end_point,
            active=payload.active,
        )
    except NoResultFound:
        _raise_not_found("route", route_id)
    return _to_dict(row)


@app.delete("/routes/{route_id}", response_model=MessageResponse)
async def delete_route(
    route_id: UUID,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    repo = RouteRepository(session)
    try:
        await repo.delete(route_id)
    except NoResultFound:
        _raise_not_found("route", route_id)
    return MessageResponse(message="deleted")


@app.post("/routes/import")
async def bulk_import_routes(
    file: UploadFile = File(...),
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    content = (await file.read()).decode("utf-8")
    rows = _parse_csv_with_required(content, required_columns={"route_code", "route_name", "start_point", "end_point"})
    repo = RouteRepository(session)
    created = await repo.bulk_create(
        [
            {
                "route_code": r["route_code"],
                "route_name": r["route_name"],
                "expected_distance_km": float(r.get("expected_distance_km") or 0),
                "expected_duration_min": int(r.get("expected_duration_min") or 0),
                "start_point": r["start_point"],
                "end_point": r["end_point"],
                "active": _parse_bool(r.get("active"), default=True),
            }
            for r in rows
        ]
    )
    return {"created": len(created)}


@app.get("/geofences", response_model=PageResponse)
async def list_geofences(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    ward_id: UUID | None = Query(default=None),
    type: str | None = Query(default=None),  # noqa: A002
    geometry_type: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse:
    return await _list_entities(
        session,
        GeofenceORM,
        page=page,
        page_size=page_size,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
        filters={"active": active, "ward_id": ward_id, "type": type, "geometry_type": geometry_type},
    )


@app.post("/geofences")
async def create_geofence(
    payload: GeofenceIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = GeofenceRepository(session)
    create_kwargs: dict[str, Any] = {
        "geofence_code": payload.geofence_code,
        "geofence_name": payload.geofence_name,
        "type": payload.type,
        "geometry_type": payload.geometry_type,
        "center_lat": payload.center_lat,
        "center_lng": payload.center_lng,
        "radius_meter": payload.radius_meter,
        "ward_id": payload.ward_id,
        "active": payload.active,
    }
    if payload.polygon is not None:
        create_kwargs["polygon"] = payload.polygon
    row = await repo.create(**create_kwargs)
    return _to_dict(row)


@app.get("/geofences/{geofence_id}")
async def get_geofence(
    geofence_id: UUID,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = GeofenceRepository(session)
    row = await _fetch_or_404(repo.get_by_id, "geofence", geofence_id)
    return _to_dict(row)


@app.put("/geofences/{geofence_id}")
async def update_geofence(
    geofence_id: UUID,
    payload: GeofenceIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = GeofenceRepository(session)
    try:
        update_kwargs: dict[str, Any] = {
            "geofence_code": payload.geofence_code,
            "geofence_name": payload.geofence_name,
            "type": payload.type,
            "geometry_type": payload.geometry_type,
            "center_lat": payload.center_lat,
            "center_lng": payload.center_lng,
            "radius_meter": payload.radius_meter,
            "ward_id": payload.ward_id,
            "active": payload.active,
        }
        if payload.polygon is not None:
            update_kwargs["polygon"] = payload.polygon
        row = await repo.update(geofence_id, **update_kwargs)
    except NoResultFound:
        _raise_not_found("geofence", geofence_id)
    return _to_dict(row)


@app.delete("/geofences/{geofence_id}", response_model=MessageResponse)
async def delete_geofence(
    geofence_id: UUID,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    repo = GeofenceRepository(session)
    try:
        await repo.delete(geofence_id)
    except NoResultFound:
        _raise_not_found("geofence", geofence_id)
    return MessageResponse(message="deleted")


@app.post("/geofences/import")
async def bulk_import_geofences(
    file: UploadFile = File(...),
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    content = (await file.read()).decode("utf-8")
    rows = _parse_csv_with_required(
        content,
        required_columns={"geofence_code", "geofence_name", "type", "geometry_type"},
    )
    repo = GeofenceRepository(session)
    created = await repo.bulk_create(
        [
            {
                "geofence_code": r["geofence_code"],
                "geofence_name": r["geofence_name"],
                "type": r["type"],
                "geometry_type": r["geometry_type"],
                "center_lat": float(r["center_lat"]) if r.get("center_lat") else None,
                "center_lng": float(r["center_lng"]) if r.get("center_lng") else None,
                "radius_meter": float(r["radius_meter"]) if r.get("radius_meter") else None,
                "ward_id": _parse_uuid(r.get("ward_id")),
                "active": _parse_bool(r.get("active"), default=True),
            }
            for r in rows
        ]
    )
    return {"created": len(created)}


@app.get("/contractors", response_model=PageResponse)
async def list_contractors(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse:
    return await _list_entities(
        session,
        ContractorORM,
        page=page,
        page_size=page_size,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
        filters={"active": active},
    )


@app.post("/contractors")
async def create_contractor(
    payload: ContractorIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = ContractorRepository(session)
    row = await repo.create(
        contractor_code=payload.contractor_code,
        contractor_name=payload.contractor_name,
        contact=payload.contact,
        sla_details=payload.sla_details,
        active=payload.active,
    )
    return _to_dict(row)


@app.get("/contractors/{contractor_id}")
async def get_contractor(
    contractor_id: UUID,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = ContractorRepository(session)
    row = await _fetch_or_404(repo.get_by_id, "contractor", contractor_id)
    return _to_dict(row)


@app.put("/contractors/{contractor_id}")
async def update_contractor(
    contractor_id: UUID,
    payload: ContractorIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = ContractorRepository(session)
    try:
        row = await repo.update(
            contractor_id,
            contractor_code=payload.contractor_code,
            contractor_name=payload.contractor_name,
            contact=payload.contact,
            sla_details=payload.sla_details,
            active=payload.active,
        )
    except NoResultFound:
        _raise_not_found("contractor", contractor_id)
    return _to_dict(row)


@app.delete("/contractors/{contractor_id}", response_model=MessageResponse)
async def delete_contractor(
    contractor_id: UUID,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    repo = ContractorRepository(session)
    try:
        await repo.delete(contractor_id)
    except NoResultFound:
        _raise_not_found("contractor", contractor_id)
    return MessageResponse(message="deleted")


@app.post("/contractors/import")
async def bulk_import_contractors(
    file: UploadFile = File(...),
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    content = (await file.read()).decode("utf-8")
    rows = _parse_csv_with_required(content, required_columns={"contractor_code", "contractor_name"})
    repo = ContractorRepository(session)
    created = await repo.bulk_create(
        [
            {
                "contractor_code": r["contractor_code"],
                "contractor_name": r["contractor_name"],
                "contact": r.get("contact") or None,
                "sla_details": {},
                "active": _parse_bool(r.get("active"), default=True),
            }
            for r in rows
        ]
    )
    return {"created": len(created)}


@app.get("/wards", response_model=PageResponse)
async def list_wards(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    zone_name: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse:
    return await _list_entities(
        session,
        WardORM,
        page=page,
        page_size=page_size,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
        filters={"active": active, "zone_name": zone_name},
    )


@app.post("/wards")
async def create_ward(
    payload: WardIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = WardRepository(session)
    row = await repo.create(
        ward_code=payload.ward_code,
        ward_name=payload.ward_name,
        zone_name=payload.zone_name,
        active=payload.active,
    )
    return _to_dict(row)


@app.get("/wards/{ward_id}")
async def get_ward(
    ward_id: UUID,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = WardRepository(session)
    row = await _fetch_or_404(repo.get_by_id, "ward", ward_id)
    return _to_dict(row)


@app.put("/wards/{ward_id}")
async def update_ward(
    ward_id: UUID,
    payload: WardIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = WardRepository(session)
    try:
        row = await repo.update(
            ward_id,
            ward_code=payload.ward_code,
            ward_name=payload.ward_name,
            zone_name=payload.zone_name,
            active=payload.active,
        )
    except NoResultFound:
        _raise_not_found("ward", ward_id)
    return _to_dict(row)


@app.delete("/wards/{ward_id}", response_model=MessageResponse)
async def delete_ward(
    ward_id: UUID,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    repo = WardRepository(session)
    try:
        await repo.delete(ward_id)
    except NoResultFound:
        _raise_not_found("ward", ward_id)
    return MessageResponse(message="deleted")


@app.post("/wards/import")
async def bulk_import_wards(
    file: UploadFile = File(...),
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    content = (await file.read()).decode("utf-8")
    rows = _parse_csv_with_required(content, required_columns={"ward_code", "ward_name", "zone_name"})
    repo = WardRepository(session)
    created = await repo.bulk_create(
        [
            {
                "ward_code": r["ward_code"],
                "ward_name": r["ward_name"],
                "zone_name": r["zone_name"],
                "active": _parse_bool(r.get("active"), default=True),
            }
            for r in rows
        ]
    )
    return {"created": len(created)}


@app.post("/device-assignments")
async def assign_device(
    payload: DeviceAssignmentIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    svc = DeviceVehicleAssignmentService(DeviceVehicleAssignmentRepository(session))
    row = await svc.assign(
        AssignmentCreateInput(
            device_id=payload.device_id,
            vehicle_id=payload.vehicle_id,
            assigned_from=payload.assigned_from,
            remarks=payload.remarks,
        )
    )
    return _to_dict(row)


@app.get("/device-assignments/{device_id}")
async def get_active_assignment_by_device(
    device_id: UUID,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = DeviceVehicleAssignmentRepository(session)
    row = await repo.get_active_by_device(device_id)
    if row is None:
        _raise_not_found("device assignment", device_id)
    return _to_dict(row)


@app.put("/device-assignments/{device_id}")
async def reassign_device(
    device_id: UUID,
    vehicle_id: UUID = Query(...),
    remarks: str | None = Query(default=None),
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    svc = DeviceVehicleAssignmentService(DeviceVehicleAssignmentRepository(session))
    row = await svc.assign(
        AssignmentCreateInput(
            device_id=device_id,
            vehicle_id=vehicle_id,
            remarks=remarks,
        )
    )
    return _to_dict(row)


@app.delete("/device-assignments/{device_id}", response_model=MessageResponse)
async def unassign_device(
    device_id: UUID,
    remarks: str | None = Query(default=None),
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    svc = DeviceVehicleAssignmentService(DeviceVehicleAssignmentRepository(session))
    row = await svc.unassign_device(device_id, remarks=remarks)
    if row is None:
        _raise_not_found("device assignment", device_id)
    return MessageResponse(message="deleted")


@app.get("/device-assignments", response_model=PageResponse)
async def list_device_assignments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    device_id: UUID | None = Query(default=None),
    vehicle_id: UUID | None = Query(default=None),
    active: bool | None = Query(default=None),
    sort_by: str = Query(default="assigned_from"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse:
    return await _list_entities(
        session,
        DeviceVehicleAssignmentORM,
        page=page,
        page_size=page_size,
        q=None,
        sort_by=sort_by,
        sort_order=sort_order,
        filters={"device_id": device_id, "vehicle_id": vehicle_id, "active": active},
    )


@app.post("/device-assignments/import")
async def bulk_import_device_assignments(
    file: UploadFile = File(...),
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    content = (await file.read()).decode("utf-8")
    rows = _parse_csv_with_required(content, required_columns={"device_id", "vehicle_id"})
    svc = DeviceVehicleAssignmentService(DeviceVehicleAssignmentRepository(session))
    created = 0
    for row in rows:
        await svc.assign(
            AssignmentCreateInput(
                device_id=UUID(row["device_id"]),
                vehicle_id=UUID(row["vehicle_id"]),
                assigned_from=datetime.fromisoformat(row["assigned_from"])
                if row.get("assigned_from")
                else None,
                remarks=row.get("remarks") or None,
            )
        )
        created += 1
    return {"created": created}


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


@app.get("/analytics/trips")
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


@app.get("/analytics/idle-segments")
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


@app.get("/analytics/overspeed-events")
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


@app.get("/analytics/geofence-events")
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


@app.get("/analytics/reports/daily")
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


@app.get("/analytics/reports/monthly")
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


@app.get("/analytics/reports/quarterly")
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


@app.get("/analytics/reports/half-yearly")
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


@app.get("/analytics/reports/annual")
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


@app.get("/analytics/vehicle-state")
async def list_vehicle_states(
    limit: int = Query(default=500, ge=1, le=5000),
    vehicle_id: str | None = Query(default=None),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get current state for all or filtered vehicles."""
    stmt = select(AnalyticsVehicleStateORM).limit(limit)
    if vehicle_id:
        stmt = stmt.where(AnalyticsVehicleStateORM.vehicle_id == vehicle_id)
    
    rows = (await session.execute(stmt)).scalars().all()
    items = [_to_dict(row) for row in rows]
    return {"items": items, "total": len(items)}


@app.get("/analytics/vehicle-state/{vehicle_id}")
async def get_vehicle_state(
    vehicle_id: str,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get current state for a specific vehicle."""
    stmt = select(AnalyticsVehicleStateORM).where(AnalyticsVehicleStateORM.vehicle_id == vehicle_id)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"vehicle state not found for {vehicle_id}")
    return _to_dict(row)


@app.get("/analytics/geofence-summary")
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
    """Get geofence entry/exit/dwell summary statistics."""
    stmt = (
        select(
            AnalyticsGeofenceEventORM.geofence_code,
            func.count(AnalyticsGeofenceEventORM.id).label("total_events"),
            func.sum(case((AnalyticsGeofenceEventORM.event_type == "entry", 1), else_=0)).label("entries"),
            func.sum(case((AnalyticsGeofenceEventORM.event_type == "exit", 1), else_=0)).label("exits"),
            func.sum(AnalyticsGeofenceEventORM.dwell_minutes).label("total_dwell_minutes"),
            func.avg(AnalyticsGeofenceEventORM.dwell_minutes).label("avg_dwell_minutes"),
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


@app.get("/analytics/vehicle-utilization")
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
    """Get vehicle utilization metrics by day."""
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


@app.get("/analytics/route-deviation-summary")
async def route_deviation_summary(
    from_ts: datetime | None = Query(default=None),
    to_ts: datetime | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
    export: str = Query(default="json", pattern="^(json|csv)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """Get route deviation event summary by vehicle."""
    stmt = (
        select(
            AnalyticsTripRecordORM.vehicle_id,
            func.count(AnalyticsTripRecordORM.id).label("trips_total"),
            func.sum(case((AnalyticsTripRecordORM.route_deviation == True, 1), else_=0)).label("trips_with_deviation"),
            func.avg(AnalyticsTripRecordORM.route_deviation_distance_km).label("avg_deviation_distance_km"),
            func.max(AnalyticsTripRecordORM.route_deviation_distance_km).label("max_deviation_distance_km"),
        )
        .select_from(AnalyticsTripRecordORM)
        .group_by(AnalyticsTripRecordORM.vehicle_id)
        .limit(limit)
    )
    
    if from_ts is not None:
        stmt = stmt.where(AnalyticsTripRecordORM.started_at >= from_ts)
    if to_ts is not None:
        stmt = stmt.where(AnalyticsTripRecordORM.started_at <= to_ts)
    if vehicle_id:
        stmt = stmt.where(AnalyticsTripRecordORM.vehicle_id == vehicle_id)
    
    rows = _rows_from_result(await session.execute(stmt))
    if export == "csv":
        return _csv_response(rows, "route-deviation-summary.csv")
    return {"items": rows, "total": len(rows)}


@app.get("/analytics/fuel-efficiency")
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
    """Get fuel efficiency metrics (km per liter)."""
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


@app.get("/analytics/speed-analysis")
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
    """Get speed statistics: overspeed events count and distribution by vehicle."""
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


@app.get("/analytics/idle-summary")
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
    """Get idle time summary by vehicle and date."""
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


@app.get("/v1/dashboard/kpis")
async def dashboard_kpis(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    contractor_id: UUID | None = Query(default=None),
    route_id: UUID | None = Query(default=None),
    ward_id: UUID | None = Query(default=None),
    zone_name: str | None = Query(default=None),
    export: str = Query(default="json", pattern="^(json|csv|xlsx|pdf)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    vehicle_filters = []
    if contractor_id is not None:
        vehicle_filters.append(VehicleORM.contractor_id == contractor_id)
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


@app.get("/v1/vehicles/{vehicle_id}/detail")
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


@app.get("/v1/vehicles/search", response_model=PageResponse)
async def search_vehicles(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    vehicle_number: str | None = Query(default=None),
    imei: str | None = Query(default=None),
    contractor_id: UUID | None = Query(default=None),
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
    if contractor_id is not None:
        stmt = stmt.where(VehicleORM.contractor_id == contractor_id)
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


@app.get("/v1/alerts")
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


@app.post("/v1/alerts")
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
        contractor_id=payload.contractor_id,
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


@app.post("/v1/alerts/{alert_id}/acknowledge")
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


@app.post("/v1/alerts/{alert_id}/resolve")
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


@app.post("/v1/alerts/{alert_id}/escalate")
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


@app.get("/v1/alerts/{alert_id}/audit")
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


@app.get("/v1/configurations", response_model=PageResponse)
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


@app.post("/v1/configurations")
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


@app.put("/v1/configurations/{config_id}")
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


@app.delete("/v1/configurations/{config_id}", response_model=MessageResponse)
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


@app.get("/v1/operational-categories", response_model=PageResponse)
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


@app.post("/v1/operational-categories")
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


@app.put("/v1/operational-categories/{category_id}")
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


@app.delete("/v1/operational-categories/{category_id}", response_model=MessageResponse)
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


@app.get("/v1/reports/operations/export")
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


@app.get("/v1/audit-logs")
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


def run() -> None:
    uvicorn.run(
        "admin_api.main:app",
        host=settings.admin_api_host,
        port=settings.admin_api_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
