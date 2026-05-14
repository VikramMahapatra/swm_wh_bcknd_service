from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from swm_common import configure_logging, get_logger, get_settings
from swm_models import CanonicalTelemetry
from swm_redis import (
    FleetBucket,
    PubSubChannel,
    RedisClient,
    RedisPubSubPublisher,
    RedisStreamBatchConsumer,
    RealtimeCacheService,
    StreamConsumerRecord,
    StreamConsumerSettings,
    TruckLast,
    TruckState,
)

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("realtime_worker")


class RealtimeStreamConsumer(RedisStreamBatchConsumer):
    def __init__(
        self,
        redis_client: RedisClient,
        cache: RealtimeCacheService,
        publisher: RedisPubSubPublisher,
        consumer_settings: StreamConsumerSettings,
    ) -> None:
        super().__init__(redis_client, consumer_settings)
        self.cache = cache
        self.publisher = publisher

    async def handle_batch(self, records: list[StreamConsumerRecord]) -> None:
        for record in records:
            event = CanonicalTelemetry.from_stream_data(record.data)
            status = self._state_for(event)

            await self.cache.set_last(
                TruckLast(
                    imei=event.imei,
                    device_id=event.device_id,
                    ts=event.event_ts,
                    lat=event.lat,
                    lon=event.lng,
                    speed_kph=event.speed,
                    heading=event.heading,
                    ignition=bool(event.acc_status),
                    attributes={"vehicle_id": event.vehicle_id, "vendor_id": event.vendor_id},
                )
            )
            await self.cache.touch_last_seen(event.imei, event.event_ts)
            await self.cache.set_state(
                TruckState(
                    imei=event.imei,
                    status=status,
                    updated_at=datetime.now(tz=UTC),
                    reason="stream_realtime_update",
                )
            )
            await self.publisher.publish(
                PubSubChannel.LIVE_UPDATES,
                {
                    "imei": event.imei,
                    "vehicle_id": event.vehicle_id,
                    "lat": event.lat,
                    "lng": event.lng,
                    "speed": event.speed,
                    "status": status.value,
                    "event_ts": event.event_ts.isoformat(),
                },
                source="realtime-worker",
            )

    def _state_for(self, event: CanonicalTelemetry) -> FleetBucket:
        age_seconds = max((datetime.now(tz=UTC) - event.event_ts).total_seconds(), 0.0)
        if age_seconds > 300:
            return FleetBucket.OFFLINE
        if event.speed >= 5:
            return FleetBucket.MOVING
        if event.acc_status == 1:
            return FleetBucket.IDLE
        return FleetBucket.PARKED


async def run_async() -> None:
    redis = RedisClient.from_url(settings.redis_url)
    cache = RealtimeCacheService(redis)
    publisher = RedisPubSubPublisher(redis)
    consumer = RealtimeStreamConsumer(
        redis,
        cache,
        publisher,
        StreamConsumerSettings(
            stream="gps.telemetry.raw",
            group="realtime",
            consumer_name="realtime-1",
            batch_size=1000,
            retry_stream="gps.telemetry.raw.realtime.retry",
            poison_stream="gps.telemetry.raw.realtime.poison",
            checkpoint_key="swm:stream:checkpoint:realtime",
        ),
    )

    logger.info("realtime_worker_started")
    await consumer.run_forever()


def run() -> None:
    asyncio.run(run_async())


if __name__ == "__main__":
    run()
