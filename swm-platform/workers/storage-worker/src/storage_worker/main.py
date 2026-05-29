from __future__ import annotations

import asyncio
import math
import uuid
from datetime import timedelta

from swm_clickhouse import ClickHouseRawTelemetryClient
from swm_common import configure_logging, get_logger, get_settings
from swm_db import (
    DatabaseSessionManager,
    DeviceORM,
    DeviceVehicleAssignmentORM,
    DeviceEventORM,
    EngineConfig,
    PickupPointCrossingORM,
    PickupPointORM,
    VehicleORM,
)
from swm_models import CanonicalTelemetry
from swm_redis import RedisClient, RedisStreamBatchConsumer, StreamConsumerRecord, StreamConsumerSettings
from sqlalchemy import String, cast, insert, or_, select

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("storage_worker")


class StorageStreamConsumer(RedisStreamBatchConsumer):
    def __init__(
        self,
        redis_client: RedisClient,
        clickhouse: ClickHouseRawTelemetryClient,
        postgres: "PostgresDeviceEventWriter",
        consumer_settings: StreamConsumerSettings,
    ) -> None:
        super().__init__(redis_client, consumer_settings)
        self.clickhouse = clickhouse
        self.postgres = postgres

    async def handle_batch(self, records: list[StreamConsumerRecord]) -> None:
        fallback_device = 0
        fallback_vehicle = 0
        events: list[CanonicalTelemetry] = []
        for record in records:
            payload = dict(record.data)
            if not payload.get("device_id"):
                payload["device_id"] = str(payload.get("imei") or "")
                fallback_device += 1
            if not payload.get("vehicle_id"):
                payload["vehicle_id"] = "unknown"
                fallback_vehicle += 1
            if "raw_payload" not in payload and "payload_raw" in payload:
                payload["raw_payload"] = payload["payload_raw"]
            events.append(CanonicalTelemetry.from_stream_data(payload))

        if fallback_device or fallback_vehicle:
            logger.warning(
                "storage_worker_missing_device_context_fallback",
                fallback_device=fallback_device,
                fallback_vehicle=fallback_vehicle,
                batch_size=len(records),
            )
        await self.postgres.insert_device_events_batch(events)
        await self.clickhouse.insert_raw_telemetry_batch(events)


class PostgresDeviceEventWriter:
    def __init__(self, postgres_dsn: str) -> None:
        self._session_manager = DatabaseSessionManager(EngineConfig(dsn=postgres_dsn))

    async def insert_device_events_batch(self, events: list[CanonicalTelemetry]) -> int:
        if not events:
            return 0

        rows = [
            {
                "device_id": event.device_id,
                "ts": event.event_ts,
                "lat": event.lat,
                "lon": event.lng,
                "speed_kph": float(event.speed),
                "heading": event.heading,
                "ignition": bool(event.acc_status),
                "attributes": {
                    "imei": event.imei,
                    "vendor_id": event.vendor_id,
                    "vehicle_id": event.vehicle_id,
                    "odometer": event.odometer,
                    "fuel_level": event.fuel_level,
                    "raw_payload": event.raw_payload,
                },
            }
            for event in events
        ]

        async with self._session_manager.session() as session:
            # Use the table insert so only explicit columns in rows are sent.
            # This avoids ORM-side UUID id defaults conflicting with integer PK.
            await session.execute(insert(DeviceEventORM.__table__), rows)
            await self._insert_pickup_crossings(session, events)
        return len(rows)

    async def _insert_pickup_crossings(self, session, events: list[CanonicalTelemetry]) -> int:
        candidate_ids = {
            str(event.vehicle_id).strip()
            for event in events
            if str(event.vehicle_id).strip() and str(event.vehicle_id).strip() != "unknown"
        }

        # Resolve vehicles even when stream has vehicle_id=unknown by using active device assignments.
        device_ids = {
            str(event.device_id).strip()
            for event in events
            if str(event.device_id).strip() and str(event.device_id).strip() != "unknown"
        }
        imeis = {str(event.imei).strip() for event in events if str(event.imei).strip()}

        vehicle_filters = []
        if candidate_ids:
            vehicle_filters.extend(
                [
                    cast(VehicleORM.id, String).in_(candidate_ids),
                    VehicleORM.vehicle_number.in_(candidate_ids),
                ]
            )

        assigned_vehicle_ids: set[str] = set()
        if device_ids or imeis:
            assignment_stmt = (
                select(
                    cast(DeviceVehicleAssignmentORM.vehicle_id, String).label("vehicle_id"),
                    cast(DeviceVehicleAssignmentORM.device_id, String).label("device_id"),
                    DeviceORM.imei.label("imei"),
                )
                .select_from(DeviceVehicleAssignmentORM)
                .join(DeviceORM, DeviceVehicleAssignmentORM.device_id == DeviceORM.id)
                .where(DeviceVehicleAssignmentORM.active.is_(True))
            )
            if device_ids and imeis:
                assignment_stmt = assignment_stmt.where(
                    or_(
                        cast(DeviceVehicleAssignmentORM.device_id, String).in_(device_ids),
                        DeviceORM.imei.in_(imeis),
                    )
                )
            elif device_ids:
                assignment_stmt = assignment_stmt.where(cast(DeviceVehicleAssignmentORM.device_id, String).in_(device_ids))
            else:
                assignment_stmt = assignment_stmt.where(DeviceORM.imei.in_(imeis))

            assignment_rows = (await session.execute(assignment_stmt)).all()
            for row in assignment_rows:
                vehicle_id_str = str(row.vehicle_id)
                assigned_vehicle_ids.add(vehicle_id_str)
                if row.device_id:
                    assigned_vehicle_ids.add(str(row.device_id))
                if row.imei:
                    assigned_vehicle_ids.add(str(row.imei))

            if assignment_rows:
                vehicle_filters.append(cast(VehicleORM.id, String).in_({str(row.vehicle_id) for row in assignment_rows}))

        if not vehicle_filters:
            return 0

        vehicle_stmt = select(VehicleORM.id, VehicleORM.vehicle_number, VehicleORM.route_id).where(or_(*vehicle_filters))
        vehicle_rows = (await session.execute(vehicle_stmt)).all()
        if not vehicle_rows:
            return 0

        vehicle_by_any: dict[str, tuple[str, uuid.UUID | None]] = {}
        route_ids: set[uuid.UUID] = set()
        for row in vehicle_rows:
            vehicle_id_str = str(row.id)
            vehicle_no = str(row.vehicle_number or "")
            route_id = row.route_id
            vehicle_by_any[vehicle_id_str] = (vehicle_id_str, route_id)
            if vehicle_no:
                vehicle_by_any[vehicle_no] = (vehicle_id_str, route_id)
            if route_id is not None:
                route_ids.add(route_id)

        # Map assignment identities (device id / IMEI) to resolved vehicle rows
        if device_ids or imeis:
            assignment_stmt = (
                select(
                    cast(DeviceVehicleAssignmentORM.vehicle_id, String).label("vehicle_id"),
                    cast(DeviceVehicleAssignmentORM.device_id, String).label("device_id"),
                    DeviceORM.imei.label("imei"),
                )
                .select_from(DeviceVehicleAssignmentORM)
                .join(DeviceORM, DeviceVehicleAssignmentORM.device_id == DeviceORM.id)
                .where(DeviceVehicleAssignmentORM.active.is_(True))
            )
            if device_ids and imeis:
                assignment_stmt = assignment_stmt.where(
                    or_(
                        cast(DeviceVehicleAssignmentORM.device_id, String).in_(device_ids),
                        DeviceORM.imei.in_(imeis),
                    )
                )
            elif device_ids:
                assignment_stmt = assignment_stmt.where(cast(DeviceVehicleAssignmentORM.device_id, String).in_(device_ids))
            else:
                assignment_stmt = assignment_stmt.where(DeviceORM.imei.in_(imeis))

            assignment_rows = (await session.execute(assignment_stmt)).all()
            for row in assignment_rows:
                resolved = vehicle_by_any.get(str(row.vehicle_id))
                if not resolved:
                    continue
                if row.device_id:
                    vehicle_by_any[str(row.device_id)] = resolved
                if row.imei:
                    vehicle_by_any[str(row.imei)] = resolved

        if not route_ids:
            return 0

        pickup_stmt = select(
            PickupPointORM.id,
            PickupPointORM.route_id,
            PickupPointORM.lat,
            PickupPointORM.lng,
            PickupPointORM.pickup_radius_m,
        ).where(PickupPointORM.route_id.in_(route_ids))
        pickup_rows = (await session.execute(pickup_stmt)).all()
        pickups_by_route: dict[uuid.UUID, list] = {}
        for row in pickup_rows:
            if row.route_id is None or row.lat is None or row.lng is None:
                continue
            pickups_by_route.setdefault(row.route_id, []).append(row)

        if not pickups_by_route:
            return 0

        identity_keys = set(candidate_ids) | device_ids | imeis
        resolved_vehicle_ids = {vehicle_by_any[key][0] for key in identity_keys if key in vehicle_by_any}
        if not resolved_vehicle_ids:
            return 0

        cooldown_cutoff = max((event.event_ts for event in events), default=None)
        if cooldown_cutoff is None:
            return 0
        cooldown_cutoff = cooldown_cutoff - timedelta(seconds=max(settings.pickup_cross_cooldown_seconds, 0))

        recent_stmt = select(
            PickupPointCrossingORM.vehicle_id,
            PickupPointCrossingORM.pickup_point_id,
            PickupPointCrossingORM.crossed_at,
        ).where(
            PickupPointCrossingORM.vehicle_id.in_(resolved_vehicle_ids),
            PickupPointCrossingORM.crossed_at >= cooldown_cutoff,
        )
        recent_rows = (await session.execute(recent_stmt)).all()
        recent_map = {(str(row.vehicle_id), str(row.pickup_point_id)): row.crossed_at for row in recent_rows}

        crossing_rows = []
        for event in events:
            lookup_keys = [
                str(event.vehicle_id).strip(),
                str(event.device_id).strip(),
                str(event.imei).strip(),
            ]
            resolved = None
            for key in lookup_keys:
                if not key or key == "unknown":
                    continue
                resolved = vehicle_by_any.get(key)
                if resolved:
                    break
            if not resolved:
                continue
            resolved_vehicle_id, route_id = resolved
            if route_id is None:
                continue
            for pickup in pickups_by_route.get(route_id, []):
                radius = float(pickup.pickup_radius_m or settings.pickup_cross_radius_m)
                if radius <= 0:
                    continue
                distance = _haversine_m(event.lat, event.lng, float(pickup.lat), float(pickup.lng))
                if distance > radius:
                    continue
                dedupe_key = (resolved_vehicle_id, str(pickup.id))
                last_crossed = recent_map.get(dedupe_key)
                if last_crossed is not None and (event.event_ts - last_crossed).total_seconds() < settings.pickup_cross_cooldown_seconds:
                    continue
                recent_map[dedupe_key] = event.event_ts
                crossing_rows.append(
                    {
                        "vehicle_id": resolved_vehicle_id,
                        "route_id": route_id,
                        "pickup_point_id": pickup.id,
                        "crossed_at": event.event_ts,
                        "lat": float(event.lat),
                        "lng": float(event.lng),
                        "distance_m": float(distance),
                        "radius_m": float(radius),
                        "source": "telemetry",
                        "imei": event.imei,
                        "vendor_id": event.vendor_id,
                    }
                )

        if crossing_rows:
            await session.execute(insert(PickupPointCrossingORM.__table__), crossing_rows)
        return len(crossing_rows)

    async def close(self) -> None:
        await self._session_manager.close()


async def run_async() -> None:
    redis = RedisClient.from_url(settings.redis_url)
    clickhouse = ClickHouseRawTelemetryClient(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        database=settings.clickhouse_db,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password,
    )
    postgres = PostgresDeviceEventWriter(settings.postgres_dsn)
    await clickhouse.ensure_table()

    consumer = StorageStreamConsumer(
        redis,
        clickhouse,
        postgres,
        StreamConsumerSettings(
            stream="gps.telemetry.raw",
            group="storage",
            consumer_name="storage-1",
            batch_size=2000,
            max_retries=5,
            retry_stream="gps.telemetry.raw.storage.retry",
            poison_stream="gps.telemetry.raw.storage.poison",
            checkpoint_key="swm:stream:checkpoint:storage",
        ),
    )

    logger.info("storage_worker_started")
    try:
        await consumer.run_forever()
    finally:
        await postgres.close()
        await redis.close()


def run() -> None:
    asyncio.run(run_async())


if __name__ == "__main__":
    run()


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
