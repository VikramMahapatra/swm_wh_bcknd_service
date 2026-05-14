"""Typed realtime cache service for fleet truck status and indexing.

Key topology:
- truck:last:<imei>
- truck:state:<imei>
- truck:last_seen:<imei>
- truck:trip:<imei>
- truck:geofence:<imei>

Fleet sets:
- fleet:moving
- fleet:idle
- fleet:offline
- fleet:parked
- fleet:maintenance
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from prometheus_client import Counter

from swm_redis.client import RedisClient


_REALTIME_CACHE_LOOKUP_TOTAL = Counter(
    "swm_redis_realtime_cache_lookup_total",
    "Total realtime cache lookups by entity and result",
    ["entity", "result"],
)


class FleetBucket(StrEnum):
    MOVING = "moving"
    IDLE = "idle"
    OFFLINE = "offline"
    PARKED = "parked"
    MAINTENANCE = "maintenance"


@dataclass(slots=True)
class RealtimeCacheConfig:
    """TTL and namespace configuration for realtime cache keys."""

    key_prefix: str = ""
    last_ttl_seconds: int = 60 * 60 * 2
    state_ttl_seconds: int = 60 * 60 * 2
    last_seen_ttl_seconds: int = 60 * 60 * 24
    trip_ttl_seconds: int = 60 * 60 * 6
    geofence_ttl_seconds: int = 60 * 60 * 6


@dataclass(slots=True)
class TruckLast:
    imei: str
    device_id: str | None
    ts: datetime
    lat: float
    lon: float
    speed_kph: float
    heading: int
    ignition: bool
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TruckState:
    imei: str
    status: FleetBucket
    updated_at: datetime
    reason: str | None = None


@dataclass(slots=True)
class TruckLastSeen:
    imei: str
    ts: datetime


@dataclass(slots=True)
class TruckTrip:
    imei: str
    trip_id: str
    started_at: datetime
    route_id: str | None = None
    contractor_id: str | None = None
    ward_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TruckGeofence:
    imei: str
    geofence_id: str
    geofence_code: str
    geofence_type: str
    entered_at: datetime
    exited_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class RealtimeCacheKeys:
    """Key builder utilities for realtime truck cache."""

    def __init__(self, *, prefix: str = "") -> None:
        self.prefix = prefix.strip(":")

    def truck_last(self, imei: str) -> str:
        return self._k(f"truck:last:{imei}")

    def truck_state(self, imei: str) -> str:
        return self._k(f"truck:state:{imei}")

    def truck_last_seen(self, imei: str) -> str:
        return self._k(f"truck:last_seen:{imei}")

    def truck_trip(self, imei: str) -> str:
        return self._k(f"truck:trip:{imei}")

    def truck_geofence(self, imei: str) -> str:
        return self._k(f"truck:geofence:{imei}")

    def fleet_set(self, bucket: FleetBucket) -> str:
        return self._k(f"fleet:{bucket.value}")

    def _k(self, suffix: str) -> str:
        return f"{self.prefix}:{suffix}" if self.prefix else suffix


class RealtimeCacheService:
    """Typed cache service for truck realtime state and fleet membership sets."""

    def __init__(
        self,
        redis_client: RedisClient,
        *,
        config: RealtimeCacheConfig | None = None,
    ) -> None:
        self.redis = redis_client
        self.config = config or RealtimeCacheConfig()
        self.keys = RealtimeCacheKeys(prefix=self.config.key_prefix)

    async def set_last(self, model: TruckLast) -> None:
        await self.redis.set_json(
            self.keys.truck_last(model.imei),
            self._serialize_model(model),
            ttl=self.config.last_ttl_seconds,
        )

    async def get_last(self, imei: str) -> TruckLast | None:
        payload = await self.redis.get_json(self.keys.truck_last(imei))
        self._record_lookup("truck_last", payload)
        if payload is None:
            return None
        return TruckLast(
            imei=payload["imei"],
            device_id=payload.get("device_id"),
            ts=self._dt(payload["ts"]),
            lat=float(payload["lat"]),
            lon=float(payload["lon"]),
            speed_kph=float(payload["speed_kph"]),
            heading=int(payload["heading"]),
            ignition=bool(payload["ignition"]),
            attributes=dict(payload.get("attributes") or {}),
        )

    async def set_state(self, model: TruckState) -> None:
        await self.redis.set_json(
            self.keys.truck_state(model.imei),
            self._serialize_model(model),
            ttl=self.config.state_ttl_seconds,
        )
        await self._move_to_bucket(model.imei, model.status)

    async def get_state(self, imei: str) -> TruckState | None:
        payload = await self.redis.get_json(self.keys.truck_state(imei))
        self._record_lookup("truck_state", payload)
        if payload is None:
            return None
        return TruckState(
            imei=payload["imei"],
            status=FleetBucket(payload["status"]),
            updated_at=self._dt(payload["updated_at"]),
            reason=payload.get("reason"),
        )

    async def touch_last_seen(self, imei: str, ts: datetime | None = None) -> None:
        last_seen = TruckLastSeen(imei=imei, ts=ts or datetime.now(UTC))
        await self.redis.set_json(
            self.keys.truck_last_seen(imei),
            self._serialize_model(last_seen),
            ttl=self.config.last_seen_ttl_seconds,
        )

    async def get_last_seen(self, imei: str) -> TruckLastSeen | None:
        payload = await self.redis.get_json(self.keys.truck_last_seen(imei))
        self._record_lookup("truck_last_seen", payload)
        if payload is None:
            return None
        return TruckLastSeen(imei=payload["imei"], ts=self._dt(payload["ts"]))

    async def set_trip(self, model: TruckTrip) -> None:
        await self.redis.set_json(
            self.keys.truck_trip(model.imei),
            self._serialize_model(model),
            ttl=self.config.trip_ttl_seconds,
        )

    async def get_trip(self, imei: str) -> TruckTrip | None:
        payload = await self.redis.get_json(self.keys.truck_trip(imei))
        self._record_lookup("truck_trip", payload)
        if payload is None:
            return None
        return TruckTrip(
            imei=payload["imei"],
            trip_id=payload["trip_id"],
            started_at=self._dt(payload["started_at"]),
            route_id=payload.get("route_id"),
            contractor_id=payload.get("contractor_id"),
            ward_id=payload.get("ward_id"),
            metadata=dict(payload.get("metadata") or {}),
        )

    async def clear_trip(self, imei: str) -> None:
        await self.redis.delete(self.keys.truck_trip(imei))

    async def set_geofence(self, model: TruckGeofence) -> None:
        await self.redis.set_json(
            self.keys.truck_geofence(model.imei),
            self._serialize_model(model),
            ttl=self.config.geofence_ttl_seconds,
        )

    async def get_geofence(self, imei: str) -> TruckGeofence | None:
        payload = await self.redis.get_json(self.keys.truck_geofence(imei))
        self._record_lookup("truck_geofence", payload)
        if payload is None:
            return None
        return TruckGeofence(
            imei=payload["imei"],
            geofence_id=payload["geofence_id"],
            geofence_code=payload["geofence_code"],
            geofence_type=payload["geofence_type"],
            entered_at=self._dt(payload["entered_at"]),
            exited_at=self._dt(payload["exited_at"]) if payload.get("exited_at") else None,
            metadata=dict(payload.get("metadata") or {}),
        )

    async def clear_geofence(self, imei: str) -> None:
        await self.redis.delete(self.keys.truck_geofence(imei))

    async def get_fleet_members(self, bucket: FleetBucket) -> set[str]:
        return await self.redis.smembers(self.keys.fleet_set(bucket))

    async def is_in_fleet_bucket(self, bucket: FleetBucket, imei: str) -> bool:
        return await self.redis.sismember(self.keys.fleet_set(bucket), imei)

    async def remove_from_all_fleet_sets(self, imei: str) -> None:
        for bucket in FleetBucket:
            await self.redis.srem(self.keys.fleet_set(bucket), imei)

    async def update_snapshot(
        self,
        *,
        last: TruckLast,
        state: TruckState,
        trip: TruckTrip | None = None,
        geofence: TruckGeofence | None = None,
    ) -> None:
        await self.set_last(last)
        await self.set_state(state)
        await self.touch_last_seen(last.imei, last.ts)
        if trip is not None:
            await self.set_trip(trip)
        if geofence is not None:
            await self.set_geofence(geofence)

    async def _move_to_bucket(self, imei: str, bucket: FleetBucket) -> None:
        for fleet_bucket in FleetBucket:
            set_key = self.keys.fleet_set(fleet_bucket)
            if fleet_bucket == bucket:
                await self.redis.sadd(set_key, imei)
            else:
                await self.redis.srem(set_key, imei)

    def _serialize_model(self, model: Any) -> dict[str, Any]:
        data = asdict(model)
        return {k: self._serialize_value(v) for k, v in data.items()}

    def _serialize_value(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, FleetBucket):
            return value.value
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._serialize_value(v) for v in value]
        return value

    def _dt(self, raw: str) -> datetime:
        return datetime.fromisoformat(raw)

    def _record_lookup(self, entity: str, payload: Any) -> None:
        result = "hit" if payload is not None else "miss"
        _REALTIME_CACHE_LOOKUP_TOTAL.labels(entity=entity, result=result).inc()
