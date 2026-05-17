from collections.abc import Awaitable, Callable
from csv import DictReader
from datetime import UTC, datetime
from io import StringIO
from typing import Any
from uuid import UUID

import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import String, asc, cast, desc, func, or_, select
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
    AssignmentCreateInput,
    ContractorORM,
    ContractorRepository,
    DeviceORM,
    DeviceRepository,
    DeviceVehicleAssignmentORM,
    DeviceVehicleAssignmentRepository,
    DeviceVehicleAssignmentService,
    GeofenceORM,
    GeofenceRepository,
    RouteORM,
    RouteRepository,
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

# Add CORS middleware to allow frontend (localhost:8080) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
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
    row = await repo.create(
        geofence_code=payload.geofence_code,
        geofence_name=payload.geofence_name,
        type=payload.type,
        geometry_type=payload.geometry_type,
        center_lat=payload.center_lat,
        center_lng=payload.center_lng,
        radius_meter=payload.radius_meter,
        polygon=payload.polygon,
        ward_id=payload.ward_id,
        active=payload.active,
    )
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
        row = await repo.update(
            geofence_id,
            geofence_code=payload.geofence_code,
            geofence_name=payload.geofence_name,
            type=payload.type,
            geometry_type=payload.geometry_type,
            center_lat=payload.center_lat,
            center_lng=payload.center_lng,
            radius_meter=payload.radius_meter,
            polygon=payload.polygon,
            ward_id=payload.ward_id,
            active=payload.active,
        )
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
                "polygon": None,
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


def run() -> None:
    uvicorn.run(
        "admin_api.main:app",
        host=settings.admin_api_host,
        port=settings.admin_api_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
