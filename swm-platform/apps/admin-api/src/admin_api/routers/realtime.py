from datetime import datetime

from fastapi import APIRouter, Depends, Query
from swm_common import get_settings

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
