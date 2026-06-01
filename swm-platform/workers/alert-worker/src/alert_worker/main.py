from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import os
from typing import Any

from prometheus_client import Counter

from swm_common import configure_logging, get_logger, get_settings
from swm_db import AlertORM, DatabaseSessionManager, EngineConfig
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

_ALERT_TYPE_META = {
    "overspeed": ("fleet", "Overspeed detected"),
    "overspeeding": ("fleet", "Overspeeding detected"),
    "speed_violation": ("fleet", "Speed violation detected"),
    "speed_anomaly": ("fleet", "Speed anomaly detected"),
    "excessive_idle": ("fleet", "Excessive idle detected"),
    "route_deviation": ("route", "Route deviation detected"),
    "missed_pickup": ("operations", "Missed pickup detected"),
    "unauthorized_stop": ("operations", "Unauthorized stop detected"),
    "unauthorized_halt": ("operations", "Unauthorized halt detected"),
    "geofence_breach": ("route", "Geofence breach detected"),
    "gps_signal_loss": ("device", "GPS signal loss detected"),
    "stale_gps": ("device", "GPS signal loss detected"),
    "vehicle_offline": ("device", "Vehicle offline detected"),
    "offline": ("device", "Vehicle offline detected"),
    "panic": ("safety", "Panic alert detected"),
}

_ALERT_TYPE_ALIASES = {
    "overspeed": "overspeeding",
    "stale_gps": "gps_signal_loss",
    "offline": "vehicle_offline",
}


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


def _normalize_alert_type(value: str) -> str:
    raw = value.strip().lower()
    return _ALERT_TYPE_ALIASES.get(raw, raw)


def _normalize_severity(value: Any, fallback: str = "medium") -> str:
    raw = str(value or fallback).strip().lower()
    if raw in {"low", "medium", "high", "critical"}:
        return raw
    if raw in {"warning", "warn"}:
        return "medium"
    return fallback


def _nested_attributes(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("attributes")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        import json

        try:
            decoded = json.loads(raw)
            return decoded if isinstance(decoded, dict) else {}
        except Exception:
            return {}
    return {}


def _payload_raw(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("payload_raw") or payload.get("raw_payload")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        import json

        try:
            decoded = json.loads(raw)
            return decoded if isinstance(decoded, dict) else {}
        except Exception:
            return {}
    return {}


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
        self.session_manager = DatabaseSessionManager(EngineConfig(dsn=settings.postgres_dsn))
        self.overspeed_kph = float(os.getenv("ALERT_OVERSPEED_KPH", "80"))
        self.stale_gps_seconds = int(os.getenv("ALERT_STALE_GPS_SECONDS", "300"))
        self.offline_seconds = int(os.getenv("ALERT_OFFLINE_SECONDS", "600"))
        self.alert_cooldown_seconds = int(os.getenv("ALERT_COOLDOWN_SECONDS", "120"))

    async def _publish_alert(self, event: CanonicalTelemetry, payload: dict[str, Any]) -> None:
        alert_type = _normalize_alert_type(str(payload["alert_type"]))
        payload["alert_type"] = alert_type
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
        await self._persist_alert(event, payload)
        await self.publisher.publish(
            PubSubChannel.ALERT_EVENTS,
            payload,
            source="alert-worker",
        )
        _ALERT_EVENT_TOTAL.labels(alert_type, str(payload["severity"]), "emitted").inc()

    async def _persist_alert(self, event: CanonicalTelemetry, payload: dict[str, Any]) -> None:
        alert_type = _normalize_alert_type(str(payload["alert_type"]))
        category, title = _ALERT_TYPE_META.get(alert_type, ("operations", f"{alert_type.replace('_', ' ').title()} detected"))
        metadata = {
            "source": "alert-worker",
            "source_table": "gps.telemetry.raw",
            "source_key": f"alert-worker:{alert_type}:{event.imei}:{event.event_ts.isoformat()}",
            "location": {"lat": event.lat, "lng": event.lng},
            "speed_kph": event.speed,
            **payload.get("metadata", {}),
        }
        async with self.session_manager.session() as session:
            session.add(
                AlertORM(
                    alert_type=alert_type,
                    category=str(payload.get("category") or category),
                    title=str(payload.get("title") or title),
                    message=str(
                        payload.get("message")
                        or f"{title} for vehicle {event.vehicle_id} at {event.event_ts.isoformat()}."
                    ),
                    severity=_normalize_severity(payload.get("severity"), "medium"),
                    status="open",
                    vehicle_id=event.vehicle_id,
                    imei=event.imei,
                    triggered_at=event.event_ts,
                    metadata_json=metadata,
                )
            )

    def _build_alert_payloads(self, event: CanonicalTelemetry, source_payload: dict[str, Any]) -> list[dict[str, Any]]:
        now = datetime.now(tz=UTC)
        age_seconds = max((now - event.event_ts).total_seconds(), 0.0)

        alerts: list[dict[str, Any]] = []
        if age_seconds >= self.offline_seconds:
            alerts.append({"alert_type": "vehicle_offline", "severity": "critical"})
        elif age_seconds >= self.stale_gps_seconds:
            alerts.append({"alert_type": "gps_signal_loss", "severity": "medium"})

        if event.speed >= self.overspeed_kph:
            alerts.append({"alert_type": "overspeeding", "severity": "high"})

        decoded_payload_raw = _payload_raw(source_payload)
        raw_attrs = {**_nested_attributes(event.raw_payload), **_nested_attributes(decoded_payload_raw)}
        stream_attrs = _nested_attributes(source_payload)
        merged_payload = {**event.raw_payload, **decoded_payload_raw, **source_payload, **raw_attrs, **stream_attrs}
        if _has_geofence_breach(merged_payload):
            alerts.append({"alert_type": "geofence_breach", "severity": "high"})
        if _has_panic(merged_payload):
            alerts.append({"alert_type": "panic", "severity": "critical"})

        explicit_type = merged_payload.get("alert_type")
        if explicit_type:
            explicit_alert_type = _normalize_alert_type(str(explicit_type))
            if explicit_alert_type in _ALERT_TYPE_META:
                alerts.append(
                    {
                        "alert_type": explicit_alert_type,
                        "severity": _normalize_severity(merged_payload.get("alert_severity"), "high"),
                        "category": str(merged_payload.get("alert_category") or _ALERT_TYPE_META[explicit_alert_type][0]),
                        "message": str(merged_payload.get("alert_reason") or f"Injected {explicit_alert_type} alert"),
                        "metadata": {
                            key: value
                            for key, value in merged_payload.items()
                            if key
                            in {
                                "idle_seconds",
                                "halt_seconds",
                                "threshold_kph",
                                "offset_m",
                                "simulated_alert",
                                "alert_reason",
                            }
                        },
                    }
                )

        output: list[dict[str, Any]] = []
        for alert in alerts:
            output.append(
                {
                    "imei": event.imei,
                    "vehicle_id": event.vehicle_id,
                    "alert_type": alert["alert_type"],
                    "severity": alert["severity"],
                    "category": alert.get("category"),
                    "message": alert.get("message"),
                    "metadata": alert.get("metadata", {}),
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
