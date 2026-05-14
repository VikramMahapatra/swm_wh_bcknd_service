from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from swm_common import configure_logging, get_logger, get_settings
from swm_models import CanonicalTelemetry
from swm_redis import (
    PubSubChannel,
    RedisClient,
    RedisPubSubPublisher,
    RedisStreamBatchConsumer,
    StreamConsumerRecord,
    StreamConsumerSettings,
)

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("alert_worker")


class AlertStreamConsumer(RedisStreamBatchConsumer):
    def __init__(
        self,
        redis_client: RedisClient,
        publisher: RedisPubSubPublisher,
        consumer_settings: StreamConsumerSettings,
    ) -> None:
        super().__init__(redis_client, consumer_settings)
        self.publisher = publisher

    async def handle_batch(self, records: list[StreamConsumerRecord]) -> None:
        for record in records:
            event = CanonicalTelemetry.from_stream_data(record.data)
            alerts: list[dict[str, str]] = []

            # Skeleton alert checks.
            if event.speed >= 90:
                alerts.append({"type": "overspeed", "severity": "high"})
            if (datetime.now(tz=UTC) - event.event_ts).total_seconds() >= 300:
                alerts.append({"type": "stale_gps", "severity": "medium"})

            for alert in alerts:
                payload = {
                    "imei": event.imei,
                    "vehicle_id": event.vehicle_id,
                    "alert_type": alert["type"],
                    "severity": alert["severity"],
                    "event_ts": event.event_ts.isoformat(),
                }
                logger.warning("alert_event_generated", **payload)
                await self.publisher.publish(
                    PubSubChannel.ALERT_EVENTS,
                    payload,
                    source="alert-worker",
                )


async def run_async() -> None:
    redis = RedisClient.from_url(settings.redis_url)
    publisher = RedisPubSubPublisher(redis)
    consumer = AlertStreamConsumer(
        redis,
        publisher,
        StreamConsumerSettings(
            stream="gps.telemetry.raw",
            group="alert",
            consumer_name="alert-1",
            batch_size=1000,
            retry_stream="gps.telemetry.raw.alert.retry",
            poison_stream="gps.telemetry.raw.alert.poison",
            checkpoint_key="swm:stream:checkpoint:alert",
        ),
    )

    logger.info("alert_worker_started")
    await consumer.run_forever()


def run() -> None:
    asyncio.run(run_async())


if __name__ == "__main__":
    run()
