from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from swm_common import get_settings
from swm_db import (
    DeviceORM,
    DeviceVehicleAssignmentORM,
    RouteORM,
    VehicleORM,
    WardORM,
    ZoneORM,
    get_db_session,
)

from swm_redis import RedisClient, RealtimeCacheKeys

from admin_api.api_support import (
    IngestionFailurePage,
    LiveMapSnapshotResponse,
    LiveMapTruckPosition,
    RoleContext,
    _read_failure_stream,
    require_roles,
)

router = APIRouter()
settings = get_settings()
redis_client = RedisClient.from_url(settings.redis_url)

INGESTION_QUARANTINE_STREAM = "gps.telemetry.retry"
INGESTION_DLQ_STREAM = "gps.telemetry.failed"


@router.get("/v1/realtime/trucks", response_model=LiveMapSnapshotResponse)
async def list_realtime_trucks(
    limit: int = Query(default=10000, ge=1, le=50000),
    session: AsyncSession = Depends(get_db_session),
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
    truck_rows: list[tuple[str, dict, dict, object]] = []
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
    imeis = [imei for imei, *_ in truck_rows]
    vehicle_meta: dict[str, dict[str, str | None]] = {}
    if imeis:
        stmt = (
            select(
                DeviceORM.imei,
                DeviceORM.id.label("device_id"),
                VehicleORM.id.label("vehicle_id"),
                VehicleORM.registration_number,
                VehicleORM.vehicle_number,
                VehicleORM.vehicle_category,
                VehicleORM.operational_status,
                WardORM.id.label("ward_id"),
                WardORM.ward_name,
                WardORM.ward_code,
                ZoneORM.id.label("zone_id"),
                ZoneORM.zone_name,
                ZoneORM.zone_code,
                RouteORM.id.label("route_id"),
                RouteORM.route_name,
            )
            .select_from(DeviceORM)
            .join(
                DeviceVehicleAssignmentORM,
                (DeviceVehicleAssignmentORM.device_id == DeviceORM.id)
                & (DeviceVehicleAssignmentORM.active.is_(True))
                & (DeviceVehicleAssignmentORM.assigned_to.is_(None)),
                isouter=True,
            )
            .join(VehicleORM, VehicleORM.id == DeviceVehicleAssignmentORM.vehicle_id, isouter=True)
            .join(WardORM, WardORM.id == VehicleORM.ward_id, isouter=True)
            .join(ZoneORM, ZoneORM.id == WardORM.zone_id, isouter=True)
            .join(RouteORM, RouteORM.id == VehicleORM.route_id, isouter=True)
            .where(DeviceORM.imei.in_(imeis))
        )
        for row in (await session.execute(stmt)).mappings().all():
            vehicle_meta[str(row["imei"])] = {
                "device_id": str(row["device_id"]) if row["device_id"] is not None else None,
                "vehicle_id": str(row["vehicle_id"]) if row["vehicle_id"] is not None else None,
                "registration_number": row["registration_number"],
                "vehicle_number": row["vehicle_number"],
                "vehicle_category": row["vehicle_category"],
                "operational_status": row["operational_status"],
                "ward_id": str(row["ward_id"]) if row["ward_id"] is not None else None,
                "ward_name": row["ward_name"],
                "ward_code": row["ward_code"],
                "zone_id": str(row["zone_id"]) if row["zone_id"] is not None else None,
                "zone_name": row["zone_name"],
                "zone_code": row["zone_code"],
                "route_id": str(row["route_id"]) if row["route_id"] is not None else None,
                "route_name": row["route_name"],
            }

    items: list[LiveMapTruckPosition] = []
    for (imei, payload, attributes, event_ts), state_payload in zip(truck_rows, state_payloads, strict=False):
        try:
            meta = vehicle_meta.get(imei, {})
            status = None
            if isinstance(state_payload, dict) and state_payload.get("status") is not None:
                status = str(state_payload.get("status"))

            items.append(
                LiveMapTruckPosition(
                    imei=imei,
                    device_id=meta.get("device_id")
                    or (str(payload["device_id"]) if payload.get("device_id") is not None else None),
                    vehicle_id=meta.get("registration_number")
                    or meta.get("vehicle_number")
                    or (str(attributes["vehicle_id"]) if attributes.get("vehicle_id") is not None else None),
                    registration_number=meta.get("registration_number"),
                    vehicle_number=meta.get("vehicle_number"),
                    lat=float(payload.get("lat")),
                    lng=float(payload.get("lon")),
                    speed_kph=float(payload.get("speed_kph", 0.0)),
                    heading=int(payload.get("heading", 0)),
                    ignition=bool(payload.get("ignition", False)),
                    event_ts=event_ts,
                    status=status,
                    vendor_id=(str(attributes["vendor_id"]) if attributes.get("vendor_id") is not None else None),
                    zone_id=meta.get("zone_id"),
                    zone_name=meta.get("zone_name"),
                    zone_code=meta.get("zone_code"),
                    ward_id=meta.get("ward_id"),
                    ward_name=meta.get("ward_name"),
                    ward_code=meta.get("ward_code"),
                    route_id=meta.get("route_id"),
                    route_name=meta.get("route_name"),
                    vehicle_category=meta.get("vehicle_category"),
                    operational_status=meta.get("operational_status"),
                )
            )
        except Exception:
            continue

    items.sort(key=lambda truck: truck.imei)
    return LiveMapSnapshotResponse(items=items, total=len(items))


@router.get("/v1/ingestion/failures", response_model=IngestionFailurePage)
async def list_ingestion_failures(
    source: str = Query(default="all", pattern="^(all|quarantine|dlq)$"),
    limit: int = Query(default=100, ge=1, le=500),
    vendor_id: str | None = Query(default=None),
    retryable: bool | None = Query(default=None),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
) -> IngestionFailurePage:
    items = []

    if source in {"all", "quarantine"}:
        items.extend(
            await _read_failure_stream(
                redis_client,
                INGESTION_QUARANTINE_STREAM,
                source="quarantine",
                limit=limit,
            )
        )
    if source in {"all", "dlq"}:
        items.extend(
            await _read_failure_stream(
                redis_client,
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
