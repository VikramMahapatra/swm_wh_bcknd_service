from __future__ import annotations

import asyncio

from swm_clickhouse import ClickHouseRawTelemetryClient
from swm_common import configure_logging, get_logger, get_settings
from swm_db import DatabaseSessionManager, DeviceEventORM, EngineConfig
from swm_models import CanonicalTelemetry
from swm_redis import RedisClient, RedisStreamBatchConsumer, StreamConsumerRecord, StreamConsumerSettings
from sqlalchemy import insert

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
        return len(rows)

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
