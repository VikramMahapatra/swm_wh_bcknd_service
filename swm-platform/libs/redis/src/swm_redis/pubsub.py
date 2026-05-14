"""Typed Redis pub/sub layer for realtime channels.

Channels:
- live_updates
- fleet_events
- alert_events
- dashboard_updates
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import orjson
from prometheus_client import Counter, Gauge, Histogram
import structlog

from swm_common import get_logger
from swm_redis.client import RedisClient

logger = get_logger("swm_redis.pubsub")


class PubSubChannel(StrEnum):
    LIVE_UPDATES = "live_updates"
    FLEET_EVENTS = "fleet_events"
    ALERT_EVENTS = "alert_events"
    DASHBOARD_UPDATES = "dashboard_updates"


class BackpressurePolicy(StrEnum):
    BLOCK = "block"
    DROP_NEW = "drop_new"
    DROP_OLDEST = "drop_oldest"


@dataclass(slots=True)
class PubSubConfig:
    queue_maxsize: int = 1000
    worker_count: int = 2
    message_poll_timeout: float = 1.0
    reconnect_base_seconds: float = 0.5
    reconnect_max_seconds: float = 10.0
    backpressure_policy: BackpressurePolicy = BackpressurePolicy.DROP_OLDEST


@dataclass(slots=True)
class PubSubEnvelope:
    channel: str
    payload: dict[str, Any]
    ts: datetime
    trace_id: str = ""
    correlation_id: str = ""
    source: str = ""


_PUBSUB_PUBLISH_TOTAL = Counter(
    "swm_redis_pubsub_publish_total",
    "Count of pub/sub publish attempts",
    ["channel", "status"],
)
_PUBSUB_RECEIVED_TOTAL = Counter(
    "swm_redis_pubsub_received_total",
    "Count of pub/sub received messages",
    ["channel"],
)
_PUBSUB_RECONNECT_TOTAL = Counter(
    "swm_redis_pubsub_reconnect_total",
    "Count of pub/sub reconnect attempts",
    ["reason"],
)
_PUBSUB_DROPPED_TOTAL = Counter(
    "swm_redis_pubsub_dropped_total",
    "Count of dropped pub/sub messages due to backpressure",
    ["channel", "policy"],
)
_PUBSUB_THROUGHPUT_MESSAGES_TOTAL = Counter(
    "swm_redis_pubsub_throughput_messages_total",
    "Pub/sub message throughput by channel and direction",
    ["channel", "direction"],
)
_PUBSUB_THROUGHPUT_BYTES_TOTAL = Counter(
    "swm_redis_pubsub_throughput_bytes_total",
    "Pub/sub payload throughput in bytes by channel and direction",
    ["channel", "direction"],
)
_PUBSUB_QUEUE_DEPTH = Gauge(
    "swm_redis_pubsub_queue_depth",
    "Current pub/sub subscriber queue depth",
)
_PUBSUB_HANDLER_DURATION = Histogram(
    "swm_redis_pubsub_handler_duration_seconds",
    "Duration of pub/sub message handlers",
    ["channel"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)


class RedisPubSubPublisher:
    """Typed publisher for Redis pub/sub channels."""

    def __init__(self, redis_client: RedisClient) -> None:
        self.redis = redis_client

    async def publish(
        self,
        channel: PubSubChannel | str,
        payload: dict[str, Any] | Any,
        *,
        source: str = "",
        trace_id: str | None = None,
        correlation_id: str | None = None,
    ) -> int:
        channel_name = str(channel)
        serialized = self._serialize(channel_name, payload, source, trace_id, correlation_id)

        try:
            count = await self.redis.publish(channel_name, serialized)
            _PUBSUB_PUBLISH_TOTAL.labels(channel=channel_name, status="ok").inc()
            _PUBSUB_THROUGHPUT_MESSAGES_TOTAL.labels(channel=channel_name, direction="published").inc()
            _PUBSUB_THROUGHPUT_BYTES_TOTAL.labels(channel=channel_name, direction="published").inc(
                len(serialized.encode("utf-8"))
            )
            return count
        except Exception:
            _PUBSUB_PUBLISH_TOTAL.labels(channel=channel_name, status="error").inc()
            raise

    def _serialize(
        self,
        channel: str,
        payload: dict[str, Any] | Any,
        source: str,
        trace_id: str | None,
        correlation_id: str | None,
    ) -> str:
        ctx = structlog.contextvars.get_contextvars()
        body = {
            "channel": channel,
            "ts": datetime.now(UTC).isoformat(),
            "trace_id": trace_id or str(ctx.get("trace_id") or ""),
            "correlation_id": correlation_id or str(ctx.get("correlation_id") or ""),
            "source": source,
            "payload": self._normalize_payload(payload),
        }
        return orjson.dumps(body).decode("utf-8")

    def _normalize_payload(self, payload: dict[str, Any] | Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            return payload
        if is_dataclass(payload):
            return asdict(payload)
        if hasattr(payload, "model_dump"):
            return payload.model_dump()  # type: ignore[no-any-return]
        if hasattr(payload, "dict"):
            return payload.dict()  # type: ignore[no-any-return]
        return {"value": payload}


class RedisPubSubSubscriber:
    """Subscriber with reconnect, backpressure, and worker dispatch."""

    def __init__(
        self,
        redis_client: RedisClient,
        channels: list[PubSubChannel | str],
        *,
        config: PubSubConfig | None = None,
    ) -> None:
        self.redis = redis_client
        self.channels = [str(channel) for channel in channels]
        self.config = config or PubSubConfig()
        self._queue: asyncio.Queue[PubSubEnvelope] = asyncio.Queue(maxsize=self.config.queue_maxsize)
        self._stop = asyncio.Event()
        self._reader_task: asyncio.Task[None] | None = None
        self._worker_tasks: list[asyncio.Task[None]] = []
        self._handlers: dict[str, Any] = {}
        self._default_handler: Any = None

    def register_handler(self, channel: PubSubChannel | str, handler: Any) -> None:
        self._handlers[str(channel)] = handler

    def register_default_handler(self, handler: Any) -> None:
        self._default_handler = handler

    async def start(self) -> None:
        if self._reader_task is not None:
            return

        self._reader_task = asyncio.create_task(self._reader_loop(), name="redis-pubsub-reader")
        self._worker_tasks = [
            asyncio.create_task(self._worker_loop(i), name=f"redis-pubsub-worker-{i}")
            for i in range(self.config.worker_count)
        ]

    async def shutdown(self) -> None:
        self._stop.set()

        tasks: list[asyncio.Task[None]] = []
        if self._reader_task is not None:
            tasks.append(self._reader_task)
        tasks.extend(self._worker_tasks)

        for task in tasks:
            task.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._reader_task = None
        self._worker_tasks = []

    async def _reader_loop(self) -> None:
        backoff_seconds = self.config.reconnect_base_seconds

        while not self._stop.is_set():
            pubsub = self.redis.client.pubsub()
            try:
                await pubsub.subscribe(*self.channels)
                logger.info("pubsub_subscribed", channels=self.channels)
                backoff_seconds = self.config.reconnect_base_seconds

                while not self._stop.is_set():
                    raw = await pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=self.config.message_poll_timeout,
                    )
                    if raw is None:
                        continue

                    envelope = self._deserialize(raw)
                    _PUBSUB_RECEIVED_TOTAL.labels(channel=envelope.channel).inc()
                    _PUBSUB_THROUGHPUT_MESSAGES_TOTAL.labels(channel=envelope.channel, direction="received").inc()
                    _PUBSUB_THROUGHPUT_BYTES_TOTAL.labels(channel=envelope.channel, direction="received").inc(
                        self._payload_size_bytes(raw.get("data"))
                    )
                    await self._enqueue(envelope)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                _PUBSUB_RECONNECT_TOTAL.labels(reason="reader_error").inc()
                logger.warning("pubsub_reader_error", error=str(exc), reconnect_in=backoff_seconds)
                await asyncio.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2, self.config.reconnect_max_seconds)
            finally:
                try:
                    await pubsub.unsubscribe(*self.channels)
                except Exception:
                    pass
                try:
                    await pubsub.aclose()
                except Exception:
                    pass

    async def _worker_loop(self, worker_id: int) -> None:
        logger.debug("pubsub_worker_started", worker_id=worker_id)
        while not self._stop.is_set():
            try:
                envelope = await asyncio.wait_for(self._queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                raise

            try:
                started = asyncio.get_running_loop().time()
                handler = self._handlers.get(envelope.channel, self._default_handler)
                if handler is not None:
                    await handler(envelope)
                _PUBSUB_HANDLER_DURATION.labels(channel=envelope.channel).observe(
                    asyncio.get_running_loop().time() - started
                )
            except Exception as exc:
                logger.error("pubsub_handler_error", channel=envelope.channel, error=str(exc))
            finally:
                self._queue.task_done()
                _PUBSUB_QUEUE_DEPTH.set(self._queue.qsize())

    async def _enqueue(self, envelope: PubSubEnvelope) -> None:
        if self.config.queue_maxsize <= 0:
            await self._queue.put(envelope)
            _PUBSUB_QUEUE_DEPTH.set(self._queue.qsize())
            return

        if not self._queue.full():
            self._queue.put_nowait(envelope)
            _PUBSUB_QUEUE_DEPTH.set(self._queue.qsize())
            return

        channel = envelope.channel
        policy = self.config.backpressure_policy

        if policy == BackpressurePolicy.BLOCK:
            await self._queue.put(envelope)
            _PUBSUB_QUEUE_DEPTH.set(self._queue.qsize())
            return

        if policy == BackpressurePolicy.DROP_NEW:
            _PUBSUB_DROPPED_TOTAL.labels(channel=channel, policy=policy.value).inc()
            return

        # DROP_OLDEST
        try:
            _ = self._queue.get_nowait()
            self._queue.task_done()
        except asyncio.QueueEmpty:
            pass
        self._queue.put_nowait(envelope)
        _PUBSUB_DROPPED_TOTAL.labels(channel=channel, policy=policy.value).inc()
        _PUBSUB_QUEUE_DEPTH.set(self._queue.qsize())

    def _deserialize(self, raw: dict[str, Any]) -> PubSubEnvelope:
        channel = raw.get("channel")
        data = raw.get("data")

        channel_name = channel.decode("utf-8") if isinstance(channel, bytes) else str(channel)

        if isinstance(data, bytes):
            parsed = orjson.loads(data)
        elif isinstance(data, str):
            parsed = orjson.loads(data)
        else:
            parsed = {"payload": data}

        return PubSubEnvelope(
            channel=channel_name,
            payload=dict(parsed.get("payload") or {}),
            ts=datetime.fromisoformat(parsed.get("ts") or datetime.now(UTC).isoformat()),
            trace_id=str(parsed.get("trace_id") or ""),
            correlation_id=str(parsed.get("correlation_id") or ""),
            source=str(parsed.get("source") or ""),
        )

    def _payload_size_bytes(self, payload: Any) -> int:
        if payload is None:
            return 0
        if isinstance(payload, bytes):
            return len(payload)
        if isinstance(payload, str):
            return len(payload.encode("utf-8"))
        return len(orjson.dumps(payload))
