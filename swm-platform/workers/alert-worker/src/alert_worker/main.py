from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import os
from typing import Any

from prometheus_client import Counter

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

_ALERT_EVENT_TOTAL = Counter(
    "swm_alert_worker_alert_event_total",
    "Alert events produced by alert-worker",
    ["alert_type", "severity", "status"],
)


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _has_panic(payload: dict[str, Any]) -> bool:
    for key in ("panic", "panic_button", "panic_status", "sos", "emergency", "alarm"):
        if _is_truthy(payload.get(key)):
            return True
    return False


def _has_geofence_breach(payload: dict[str, Any]) -> bool:
    if _is_truthy(payload.get("geofence_breach")) or _is_truthy(payload.get("route_deviation")):
        return True
    event_marker = str(
        payload.get("geofence_event")
        or payload.get("event_type")
        or payload.get("alert_type")
        or ""
    ).strip().lower()
    return event_marker in {"breach", "geofence_breach", "exit", "route_deviation"}


class AlertStreamConsumer(RedisStreamBatchConsumer):
    def __init__(
        self,
        redis_client: RedisClient,
        publisher: RedisPubSubPublisher,
        consumer_settings: StreamConsumerSettings,
    ) -> None:
        super().__init__(redis_client, consumer_settings)
        self.redis = redis_client
        self.publisher = publisher
        self.overspeed_kph = float(os.getenv("ALERT_OVERSPEED_KPH", "80"))
        self.stale_gps_seconds = int(os.getenv("ALERT_STALE_GPS_SECONDS", "300"))
        self.offline_seconds = int(os.getenv("ALERT_OFFLINE_SECONDS", "600"))
        self.alert_cooldown_seconds = int(os.getenv("ALERT_COOLDOWN_SECONDS", "120"))

    async def _publish_alert(self, event: CanonicalTelemetry, payload: dict[str, Any]) -> None:
        alert_type = str(payload["alert_type"])
        cooldown_key = f"swm:alerts:cooldown:{alert_type}:{event.imei}"
        inserted = await self.redis.set(
            cooldown_key,
            datetime.now(tz=UTC).isoformat(),
            ttl=self.alert_cooldown_seconds,
            nx=True,
        )
        if not inserted:
            _ALERT_EVENT_TOTAL.labels(alert_type, str(payload["severity"]), "suppressed").inc()
            return

        logger.warning("alert_event_generated", **payload)
        await self.publisher.publish(
            PubSubChannel.ALERT_EVENTS,
            payload,
            source="alert-worker",
        )
        _ALERT_EVENT_TOTAL.labels(alert_type, str(payload["severity"]), "emitted").inc()

    def _build_alert_payloads(self, event: CanonicalTelemetry, source_payload: dict[str, Any]) -> list[dict[str, Any]]:
        now = datetime.now(tz=UTC)
        age_seconds = max((now - event.event_ts).total_seconds(), 0.0)

        alerts: list[dict[str, Any]] = []
        if age_seconds >= self.offline_seconds:
            alerts.append({"alert_type": "offline", "severity": "critical"})
        elif age_seconds >= self.stale_gps_seconds:
            alerts.append({"alert_type": "stale_gps", "severity": "medium"})

        if event.speed >= self.overspeed_kph:
            alerts.append({"alert_type": "overspeed", "severity": "high"})

        merged_payload = {**event.raw_payload, **source_payload}
        if _has_geofence_breach(merged_payload):
            alerts.append({"alert_type": "geofence_breach", "severity": "high"})
        if _has_panic(merged_payload):
            alerts.append({"alert_type": "panic", "severity": "critical"})

        output: list[dict[str, Any]] = []
        for alert in alerts:
            output.append(
                {
                    "imei": event.imei,
                    "vehicle_id": event.vehicle_id,
                    "alert_type": alert["alert_type"],
                    "severity": alert["severity"],
                    "event_ts": event.event_ts.isoformat(),
                    "age_seconds": round(age_seconds, 3),
                }
            )
        return output

    async def handle_batch(self, records: list[StreamConsumerRecord]) -> None:
        for record in records:
            event = CanonicalTelemetry.from_stream_data(record.data)
            for payload in self._build_alert_payloads(event, record.data):
                await self._publish_alert(event, payload)


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
