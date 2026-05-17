from __future__ import annotations

import asyncio

from analytics_worker.analytics import AnalyticsEngine
from swm_common import configure_logging, get_logger, get_settings
from swm_models import CanonicalTelemetry
from swm_redis import RedisClient, RedisStreamBatchConsumer, StreamConsumerRecord, StreamConsumerSettings

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("analytics_worker")


class AnalyticsStreamConsumer(RedisStreamBatchConsumer):
    def __init__(
        self,
        redis_client: RedisClient,
        engine: AnalyticsEngine,
        consumer_settings: StreamConsumerSettings,
    ) -> None:
        super().__init__(redis_client, consumer_settings)
        self.engine = engine

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
                payload["vehicle_id"] = str(payload.get("imei") or "unknown")
                fallback_vehicle += 1
            if "raw_payload" not in payload and "payload_raw" in payload:
                payload["raw_payload"] = payload["payload_raw"]
            events.append(CanonicalTelemetry.from_stream_data(payload))

        if fallback_device or fallback_vehicle:
            logger.warning(
                "analytics_worker_missing_device_context_fallback",
                fallback_device=fallback_device,
                fallback_vehicle=fallback_vehicle,
                batch_size=len(records),
            )

        stats = await self.engine.process_batch(events)
        logger.info(
            "analytics_batch_processed",
            **stats,
        )


async def run_async() -> None:
    redis = RedisClient.from_url(settings.redis_url)
    engine = AnalyticsEngine(settings.postgres_dsn)
    consumer = AnalyticsStreamConsumer(
        redis,
        engine,
        StreamConsumerSettings(
            stream="gps.telemetry.raw",
            group="analytics",
            consumer_name="analytics-1",
            batch_size=1000,
            retry_stream="gps.telemetry.raw.analytics.retry",
            poison_stream="gps.telemetry.raw.analytics.poison",
            checkpoint_key="swm:stream:checkpoint:analytics",
        ),
    )

    logger.info("analytics_worker_started")
    try:
        await consumer.run_forever()
    finally:
        await engine.close()
        await redis.close()


def run() -> None:
    asyncio.run(run_async())


if __name__ == "__main__":
    run()
