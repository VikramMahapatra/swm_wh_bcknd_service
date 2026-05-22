"""
ingestion_api.webhook_gps
=========================
POST /webhook/gps

Accepts an array of GPS fix objects from any vendor, validates and normalises
each fix, enriches with a device-context lookup from the Redis realtime cache
(sub-millisecond, no DB round-trip in the hot path), then bulk-publishes all
events to the ``gps.telemetry.raw`` Redis stream.

Design goals
------------
* **Validation** — per-field Pydantic v2 strict model; unknown fields are
  rejected.
* **Normalisation** — vendor payload shapes are flattened to
  ``CanonicalTelemetryEvent`` via ``VendorAAdapter`` (the default flat adapter).
  Pass ``X-Vendor-Id`` to select a different registered adapter.
* **Device enrichment** — IMEI → ``device_id`` / ``vehicle_id`` resolved from
  the ``truck:last:{imei}`` realtime-cache key.  Cache misses are tolerated;
  downstream consumers handle late binding.
* **Latency** — all Redis calls (cache reads + stream writes) are fired in
  parallel via ``asyncio.gather``.  Target p99 < 50 ms.
* **202 Accepted** — the caller gets an acknowledgement as soon as the data
  is accepted into the stream; actual processing is async.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import orjson
from fastapi import APIRouter, Header, Request, Security, status
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, field_validator

from swm_common.logger import get_logger
from swm_redis.client import RedisClient
from swm_redis.realtime_cache import RealtimeCacheService, TruckLast
from swm_schemas import CanonicalTelemetryEvent

_logger = get_logger("ingestion_api.webhook_gps")

# ---------------------------------------------------------------------------
# Prometheus
# ---------------------------------------------------------------------------

_GPS_EVENTS_TOTAL = Counter(
    "swm_webhook_gps_events_total",
    "Total GPS fix events accepted via the webhook endpoint",
    ["vendor_id", "outcome"],
)

_GPS_REQUESTS_TOTAL = Counter(
    "swm_webhook_gps_requests_total",
    "Total webhook GPS ingestion requests",
    ["vendor_id", "status"],
)

_GPS_PAYLOAD_RECORDS_TOTAL = Counter(
    "swm_webhook_gps_payload_records_total",
    "Total webhook GPS payload records by processing stage",
    ["vendor_id", "stage"],
)

_GPS_VALIDATION_FAILURES_TOTAL = Counter(
    "swm_webhook_gps_validation_failures_total",
    "Total webhook GPS validation failures",
    ["vendor_id", "stage"],
)

_GPS_PUBLISH_FAILURES_TOTAL = Counter(
    "swm_webhook_gps_publish_failures_total",
    "Total webhook GPS publish failures",
    ["vendor_id"],
)

_GPS_SLO_VIOLATIONS_TOTAL = Counter(
    "swm_webhook_gps_slo_violations_total",
    "Total webhook GPS requests that exceeded 50ms",
    ["vendor_id", "status"],
)

_GPS_PROCESSING_SECONDS = Histogram(
    "swm_webhook_gps_processing_seconds",
    "End-to-end processing latency for POST /webhook/gps",
    ["vendor_id", "status"],
    buckets=[0.005, 0.010, 0.020, 0.030, 0.040, 0.050, 0.075, 0.100, 0.250, 0.500],
)

# ---------------------------------------------------------------------------
# Redis stream key
# ---------------------------------------------------------------------------

GPS_STREAM = "gps.telemetry.raw"
GPS_STREAM_MAXLEN = 100_000  # approximate cap; trimmed by Redis
TRACE_HEADER = "X-Trace-Id"
GPS_PUBLISH_BATCH_SIZE = 100
GPS_PUBLISH_MAX_PARALLEL_BATCHES = 8

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class GpsFix(BaseModel):
    """A single vendor GPS fix.  Accepts common field aliases
    so the same model handles multiple flat payload styles.
    """

    model_config = ConfigDict(
        strict=False,          # accept str lat/lng coercions from vendor SDKs
        extra="ignore",        # unknown vendor fields silently dropped
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    imei: str = Field(min_length=14, max_length=17, pattern=r"^[0-9]{14,17}$")

    lat: float = Field(alias="latitude", ge=-90.0, le=90.0)
    lng: float = Field(alias="longitude", ge=-180.0, le=180.0)
    speed: float = Field(default=0.0, ge=0.0, le=320.0)
    heading: float = Field(default=0.0, ge=0.0, le=360.0)

    acc_status: bool | None = Field(default=None, alias="ignition")
    odometer: float | None = Field(default=None, ge=0.0)
    fuel_level: float | None = Field(default=None, ge=0.0, le=100.0)

    # Raw timestamp — epoch seconds/ms or ISO-8601
    ts: datetime | int | float | str = Field(alias="timestamp")

    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("lat", mode="before")
    @classmethod
    def _accept_lat(cls, v: Any) -> Any:
        # lat may also come in as "lat" (not the alias)
        return v

    @field_validator("ts", mode="before")
    @classmethod
    def _parse_ts(cls, v: Any) -> datetime:
        if isinstance(v, datetime):
            return v.astimezone(UTC) if v.tzinfo else v.replace(tzinfo=UTC)
        if isinstance(v, (int, float)):
            epoch = float(v)
            if epoch > 1e12:
                epoch /= 1000.0
            return datetime.fromtimestamp(epoch, tz=UTC)
        if isinstance(v, str):
            s = v.rstrip("Z")
            parsed = datetime.fromisoformat(s)
            return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        raise ValueError(f"Cannot parse timestamp from {v!r}")

    model_config = ConfigDict(
        strict=False,
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class GpsWebhookResponse(BaseModel):
    accepted: int
    published: int
    rejected: int
    stream: str
    request_id: str
    latency_ms: float
    error_summary: dict[str, Any]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _to_event_ts(fix: GpsFix) -> datetime:
    ts = fix.ts
    if isinstance(ts, datetime):
        return ts
    # Should not reach here after validator, but defend anyway
    return datetime.now(tz=UTC)


def _build_stream_entry(
    event: CanonicalTelemetryEvent,
    *,
    device_id: str | None,
    vehicle_id: str | None,
    request_id: str,
    trace_id: str,
) -> dict[str, str]:
    """Serialise a validated GPS fix to a flat Redis stream entry (all strings)."""
    return {
        "imei": event.imei,
        "lat": str(event.lat),
        "lng": str(event.lng),
        "speed": str(event.speed),
        "heading": str(event.heading),
        "acc_status": "" if event.acc_status is None else str(int(event.acc_status)),
        "odometer": "" if event.odometer is None else str(event.odometer),
        "fuel_level": "" if event.fuel_level is None else str(event.fuel_level),
        "event_ts": event.event_ts.isoformat(),
        "received_at": datetime.now(tz=UTC).isoformat(),
        "vendor_id": event.vendor_id,
        "device_id": device_id or "",
        "vehicle_id": vehicle_id or "",
        "request_id": request_id,
        "trace_id": trace_id,
        "attributes": "{}",
        "payload_raw": orjson.dumps(event.payload_raw).decode(),
    }


def _to_canonical_event(
    fix: GpsFix,
    *,
    vendor_id: str,
    payload_raw: dict[str, Any],
) -> dict[str, Any]:
    heading = int(fix.heading) % 360
    return {
        "imei": fix.imei,
        "lat": fix.lat,
        "lng": fix.lng,
        "speed": fix.speed,
        "heading": heading,
        "acc_status": fix.acc_status,
        "odometer": fix.odometer,
        "fuel_level": fix.fuel_level,
        "event_ts": _to_event_ts(fix),
        "payload_raw": payload_raw,
        "vendor_id": vendor_id,
    }


def _summarize_validation_errors(exc: ValidationError) -> tuple[set[int], dict[str, int], list[str]]:
    invalid_indices: set[int] = set()
    field_counts: dict[str, int] = {}
    samples: list[str] = []
    for err in exc.errors():
        loc = err.get("loc", ())
        msg = str(err.get("msg", "validation error"))
        if loc and isinstance(loc[0], int):
            invalid_indices.add(loc[0])
            field = str(loc[1]) if len(loc) > 1 else "__root__"
            key = f"{loc[0]}:{field}"
            field_counts[key] = field_counts.get(key, 0) + 1
            if len(samples) < 5:
                samples.append(f"item[{loc[0]}].{field}: {msg}")
        else:
            field_counts["__root__"] = field_counts.get("__root__", 0) + 1
            if len(samples) < 5:
                samples.append(msg)
    return invalid_indices, field_counts, samples


async def _fetch_device_context(
    cache: RealtimeCacheService,
    imei: str,
) -> tuple[str | None, str | None]:
    """Return (device_id, vehicle_id) from realtime cache or (None, None)."""
    last: TruckLast | None = await cache.get_last(imei)
    if last is None:
        return None, None
    device_id = last.device_id
    # vehicle_id is stored in attributes by upstream cache-writer if available
    vehicle_id: str | None = last.attributes.get("vehicle_id")
    return device_id, vehicle_id


# ---------------------------------------------------------------------------
# Router factory — accepts dependencies via closure
# ---------------------------------------------------------------------------


def make_gps_webhook_router(
    *,
    redis_client: RedisClient,
    cache: RealtimeCacheService | None = None,
    auth_dependency: Any | None = None,
) -> APIRouter:
    """
    Build and return the GPS webhook APIRouter.

    ``cache`` may be omitted; a ``RealtimeCacheService`` is created from
    ``redis_client`` with default config when not provided.
    """
    _cache = cache or RealtimeCacheService(redis_client)
    dependencies = [Security(auth_dependency)] if auth_dependency is not None else []
    router = APIRouter(prefix="/webhook", tags=["webhook"], dependencies=dependencies)

    @router.post(
        "/gps",
        status_code=status.HTTP_202_ACCEPTED,
        response_model=GpsWebhookResponse,
        summary="Ingest an array of GPS fixes from a vendor device",
    )
    async def ingest_gps(
        request: Request,
        x_vendor_id: Annotated[str, Header(alias="X-Vendor-Id")] = "unknown",
        x_request_id: Annotated[str, Header(alias="X-Request-Id")] = "",
    ) -> JSONResponse:
        t0 = time.perf_counter()
        request_id = x_request_id or str(uuid.uuid4())
        trace_id = request.headers.get(TRACE_HEADER) or request_id
        vendor_id = x_vendor_id.strip() or "unknown"
        request_status = "accepted"

        # --- Parse raw body as JSON array --------------------------------
        raw_body = await request.body()
        try:
            raw_items: list[Any] = orjson.loads(raw_body)
            if not isinstance(raw_items, list):
                request_status = "invalid_payload"
                _GPS_REQUESTS_TOTAL.labels(vendor_id=vendor_id, status=request_status).inc()
                _GPS_PROCESSING_SECONDS.labels(vendor_id=vendor_id, status=request_status).observe(
                    (time.perf_counter() - t0)
                )
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={"error": "Request body must be a JSON array"},
                    headers={TRACE_HEADER: trace_id},
                )
        except Exception:
            request_status = "invalid_json"
            _GPS_REQUESTS_TOTAL.labels(vendor_id=vendor_id, status=request_status).inc()
            _GPS_PROCESSING_SECONDS.labels(vendor_id=vendor_id, status=request_status).observe(
                (time.perf_counter() - t0)
            )
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"error": "Request body must be a JSON array"},
                headers={TRACE_HEADER: trace_id},
            )

        _GPS_PAYLOAD_RECORDS_TOTAL.labels(vendor_id=vendor_id, stage="received").inc(len(raw_items))

        # --- Vector validation -------------------------------------------
        aliased_items: list[Any] = []
        for item in raw_items:
            if isinstance(item, dict):
                copied = dict(item)
                _alias_item(copied)
                aliased_items.append(copied)
            else:
                aliased_items.append(item)

        validate_many = TypeAdapter(list[GpsFix])
        canonical_many = TypeAdapter(list[CanonicalTelemetryEvent])

        validation_error_counts: dict[str, int] = {}
        validation_error_samples: list[str] = []
        invalid_indices: set[int] = set()
        invalid_reasons_by_index: dict[int, list[str]] = {}
        try:
            validated_fixes = validate_many.validate_python(aliased_items)
            indexed_valid: list[tuple[int, GpsFix]] = list(enumerate(validated_fixes))
        except ValidationError as exc:
            invalid_indices, validation_error_counts, validation_error_samples = _summarize_validation_errors(exc)
            for err in exc.errors():
                loc = err.get("loc", ())
                if loc and isinstance(loc[0], int):
                    idx = loc[0]
                    invalid_reasons_by_index.setdefault(idx, []).append(str(err.get("msg", "validation error")))
            indexed_valid = []
            for idx, item in enumerate(aliased_items):
                if idx in invalid_indices:
                    continue
                try:
                    indexed_valid.append((idx, GpsFix.model_validate(item)))
                except ValidationError:
                    invalid_indices.add(idx)
                    invalid_reasons_by_index.setdefault(idx, []).append("validation error")

        rejected = len(invalid_indices)
        if rejected:
            _GPS_EVENTS_TOTAL.labels(vendor_id=vendor_id, outcome="rejected").inc(rejected)
            _GPS_VALIDATION_FAILURES_TOTAL.labels(vendor_id=vendor_id, stage="validation").inc(rejected)
            _GPS_PAYLOAD_RECORDS_TOTAL.labels(vendor_id=vendor_id, stage="rejected_validation").inc(rejected)

        for idx in sorted(invalid_indices):
            payload = aliased_items[idx] if idx < len(aliased_items) else None
            reasons = invalid_reasons_by_index.get(idx, ["validation error"])
            reason = " | ".join(reasons[:3])
            _logger.warning(
                "webhook_gps.bad_payload",
                vendor_id=vendor_id,
                request_id=request_id,
                item_index=idx,
                reason=reason,
                payload=payload,
            )

        # --- Bulk normalize ----------------------------------------------
        normalization_failed = 0
        normalization_error_samples: list[str] = []
        normalization_invalid_positions: set[int] = set()
        indexed_events: list[tuple[int, CanonicalTelemetryEvent]] = []
        if indexed_valid:
            candidates = [
                _to_canonical_event(fix, vendor_id=vendor_id, payload_raw=aliased_items[idx])
                for idx, fix in indexed_valid
            ]
            try:
                normalized_events = canonical_many.validate_python(candidates)
                indexed_events = list(zip((idx for idx, _ in indexed_valid), normalized_events, strict=False))
            except ValidationError as exc:
                bad_norm_indices, _, samples = _summarize_validation_errors(exc)
                normalization_error_samples = samples
                normalization_invalid_positions = bad_norm_indices
                for pos, (idx, _) in enumerate(indexed_valid):
                    if pos in bad_norm_indices:
                        normalization_failed += 1
                    else:
                        indexed_events.append((idx, CanonicalTelemetryEvent.model_validate(candidates[pos])))

        if normalization_invalid_positions:
            for pos in sorted(normalization_invalid_positions):
                if pos >= len(indexed_valid):
                    continue
                idx, _ = indexed_valid[pos]
                payload = aliased_items[idx]
                reason = normalization_error_samples[0] if normalization_error_samples else "normalization error"
                _logger.warning(
                    "webhook_gps.bad_payload",
                    vendor_id=vendor_id,
                    request_id=request_id,
                    item_index=idx,
                    reason=reason,
                    stage="normalization",
                    payload=payload,
                )

        rejected += normalization_failed
        if normalization_failed:
            _GPS_VALIDATION_FAILURES_TOTAL.labels(vendor_id=vendor_id, stage="normalization").inc(
                normalization_failed
            )
            _GPS_PAYLOAD_RECORDS_TOTAL.labels(vendor_id=vendor_id, stage="rejected_normalization").inc(
                normalization_failed
            )

        # --- Parallel Redis operations -----------------------------------
        # 1) Fetch device context for every unique IMEI concurrently
        unique_imeis = list({event.imei for _, event in indexed_events})
        cache_results: list[tuple[str | None, str | None]] = await asyncio.gather(
            *(_fetch_device_context(_cache, imei) for imei in unique_imeis)
        )
        device_map: dict[str, tuple[str | None, str | None]] = dict(
            zip(unique_imeis, cache_results, strict=False)
        )

        # 2) Build stream entries
        stream_entries = [
            _build_stream_entry(
                event,
                device_id=device_map[event.imei][0],
                vehicle_id=device_map[event.imei][1],
                request_id=request_id,
                trace_id=trace_id,
            )
            for _, event in indexed_events
        ]

        # 3) Bulk publish in bounded parallel batches to reduce connection pressure.
        publish_error_samples: list[str] = []
        publish_semaphore = asyncio.Semaphore(GPS_PUBLISH_MAX_PARALLEL_BATCHES)

        async def _publish_batch(batch: list[dict[str, str]]) -> tuple[int, int, list[str]]:
            await publish_semaphore.acquire()
            try:
                published_count = 0
                failed_count = 0
                errors: list[str] = []
                for entry in batch:
                    try:
                        await redis_client.xadd(
                            GPS_STREAM,
                            entry,
                            maxlen=GPS_STREAM_MAXLEN,
                            approximate=True,
                        )
                        published_count += 1
                    except Exception as exc:
                        failed_count += 1
                        if len(errors) < 5:
                            errors.append(str(exc))
                return (published_count, failed_count, errors)
            finally:
                publish_semaphore.release()

        publish_batches = _chunked_entries(stream_entries, GPS_PUBLISH_BATCH_SIZE)
        publish_results = await asyncio.gather(*(_publish_batch(batch) for batch in publish_batches))

        published = sum(ok for ok, _, _ in publish_results)
        publish_failed = sum(failed for _, failed, _ in publish_results)
        for _, _, errors in publish_results:
            if errors and len(publish_error_samples) < 5:
                publish_error_samples.extend(errors)
                publish_error_samples = publish_error_samples[:5]
        accepted = len(indexed_events)
        rejected += publish_failed

        if accepted:
            _GPS_PAYLOAD_RECORDS_TOTAL.labels(vendor_id=vendor_id, stage="accepted").inc(accepted)
        if published:
            _GPS_PAYLOAD_RECORDS_TOTAL.labels(vendor_id=vendor_id, stage="published").inc(published)
        if publish_failed:
            _GPS_PAYLOAD_RECORDS_TOTAL.labels(vendor_id=vendor_id, stage="rejected_publish").inc(publish_failed)
            _GPS_PUBLISH_FAILURES_TOTAL.labels(vendor_id=vendor_id).inc(publish_failed)

        latency_ms = (time.perf_counter() - t0) * 1000
        if published == 0 and rejected > 0:
            request_status = "partial" if accepted > 0 else "failed"
        elif published > 0 and rejected > 0:
            request_status = "partial"
        else:
            request_status = "accepted"
        _GPS_REQUESTS_TOTAL.labels(vendor_id=vendor_id, status=request_status).inc()
        if published:
            _GPS_EVENTS_TOTAL.labels(vendor_id=vendor_id, outcome="accepted").inc(published)
        _GPS_PROCESSING_SECONDS.labels(vendor_id=vendor_id, status=request_status).observe(
            latency_ms / 1000.0
        )
        if latency_ms > 50.0:
            _GPS_SLO_VIOLATIONS_TOTAL.labels(vendor_id=vendor_id, status=request_status).inc()

        error_summary = {
            "validation": {
                "failed": len(invalid_indices),
                "error_counts": validation_error_counts,
                "samples": validation_error_samples,
            },
            "normalization": {
                "failed": normalization_failed,
                "samples": normalization_error_samples,
            },
            "publish": {
                "failed": publish_failed,
                "samples": publish_error_samples,
            },
        }

        _logger.info(
            "webhook_gps.ingested",
            vendor_id=vendor_id,
            accepted=accepted,
            published=published,
            rejected=rejected,
            latency_ms=round(latency_ms, 3),
            request_id=request_id,
            error_summary=error_summary,
        )

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "accepted": accepted,
                "published": published,
                "rejected": rejected,
                "stream": GPS_STREAM,
                "request_id": request_id,
                "latency_ms": round(latency_ms, 3),
                "error_summary": error_summary,
            },
            headers={TRACE_HEADER: trace_id},
        )

    return router


# ---------------------------------------------------------------------------
# Alias normalisation — map vendor-specific keys to canonical names
# ---------------------------------------------------------------------------

_LAT_ALIASES = {"lat", "latitude", "Lat", "Latitude", "LAT"}
_LNG_ALIASES = {"lng", "longitude", "lon", "Lon", "Longitude", "LNG", "LON"}
_TS_ALIASES = {"ts", "timestamp", "event_time", "eventTime", "gpsTime", "time", "datetime"}
_ACC_ALIASES = {"acc_status", "ignition", "acc", "ign"}


def _alias_item(item: dict[str, Any]) -> None:
    """
    Mutate *item* in-place to normalise common vendor key aliases to the
    Pydantic model's expected alias names (``latitude``, ``longitude``,
    ``timestamp``, ``ignition``).
    """
    for key in list(item):
        canon = None
        if key in _LAT_ALIASES and key != "latitude":
            canon = "latitude"
        elif key in _LNG_ALIASES and key != "longitude":
            canon = "longitude"
        elif key in _TS_ALIASES and key != "timestamp":
            canon = "timestamp"
        elif key in _ACC_ALIASES and key != "ignition":
            canon = "ignition"
        if canon and canon not in item:
            item[canon] = item.pop(key)


def _chunked_entries(items: list[dict[str, str]], size: int) -> list[list[dict[str, str]]]:
    return [items[i : i + size] for i in range(0, len(items), size)]
