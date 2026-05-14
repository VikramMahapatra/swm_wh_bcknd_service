from __future__ import annotations

import asyncio

from swm_common import configure_logging, get_logger, get_settings
from swm_models import CanonicalTelemetry
from swm_redis import RedisClient, RedisStreamBatchConsumer, StreamConsumerRecord, StreamConsumerSettings

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("analytics_worker")


class AnalyticsStreamConsumer(RedisStreamBatchConsumer):
    async def handle_batch(self, records: list[StreamConsumerRecord]) -> None:
        events = [CanonicalTelemetry.from_stream_data(record.data) for record in records]

        # Skeleton analytics pipeline:
        # - moving/idle/parked
        # - trip start/trip end
        # - overspeed events
        # - geofence enter/exit
        # TODO: persist derived entities into PostgreSQL via swm_db repositories.
        moving = sum(1 for event in events if event.speed >= 5)
        overspeed = sum(1 for event in events if event.speed >= 80)
        logger.info(
            "analytics_batch_processed",
            batch_size=len(events),
            moving=moving,
            overspeed=overspeed,
        )


async def run_async() -> None:
    redis = RedisClient.from_url(settings.redis_url)
    consumer = AnalyticsStreamConsumer(
        redis,
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
    await consumer.run_forever()


def run() -> None:
    asyncio.run(run_async())


if __name__ == "__main__":
    run()
