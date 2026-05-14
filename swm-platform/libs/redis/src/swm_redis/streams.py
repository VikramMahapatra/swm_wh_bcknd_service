"""
Redis Streams topology and consumer group management.

Provides high-level API for:
- Stream initialization with consumer groups
- Publishing messages with schema validation
- Consuming with automatic retry and DLQ handling
- Monitoring and metrics collection
"""

from __future__ import annotations

import asyncio
import base64
import zlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
import time
from typing import Any
from uuid import UUID

import orjson
from prometheus_client import Counter, Gauge, Histogram
import structlog
from structlog import get_logger

from swm_common import bind_worker_context, clear_context
from swm_redis.client import RedisClient

logger = get_logger("redis.streams")

_STREAM_PUBLISH_TOTAL = Counter(
    "swm_redis_stream_publish_total",
    "Count of Redis stream publish attempts",
    ["stream", "status"],
)
_STREAM_PUBLISH_BATCH_SIZE = Histogram(
    "swm_redis_stream_publish_batch_size",
    "Batch size for Redis stream publish operations",
    ["stream"],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
)
_STREAM_PUBLISH_PAYLOAD_BYTES = Histogram(
    "swm_redis_stream_publish_payload_bytes",
    "Serialized payload size in bytes for Redis stream publish operations",
    ["stream", "compressed"],
    buckets=[128, 256, 512, 1024, 2048, 4096, 8192, 16384, 65536],
)
_STREAM_PUBLISH_LATENCY = Histogram(
    "swm_redis_stream_publish_duration_seconds",
    "Publish latency for Redis stream producer",
    ["stream", "operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)
_STREAM_REPLAY_JOB_TOTAL = Counter(
    "swm_redis_stream_replay_jobs_total",
    "Count of replay jobs by kind and status",
    ["kind", "status"],
)
_STREAM_REPLAY_MESSAGE_TOTAL = Counter(
    "swm_redis_stream_replay_messages_total",
    "Count of replayed stream messages by kind and status",
    ["kind", "status"],
)
_STREAM_CONSUMER_LAG_SECONDS = Gauge(
    "swm_redis_stream_consumer_lag_seconds",
    "Observed lag between a stream entry ID timestamp and consumer processing time",
    ["stream", "group", "consumer"],
)
_STREAM_CONSUMER_HEALTH = Gauge(
    "swm_redis_stream_consumer_health",
    "Consumer health state for Redis stream workers (1=healthy, 0=stopped)",
    ["stream", "group", "consumer"],
)
_STREAM_CONSUMER_LAST_SEEN_UNIX = Gauge(
    "swm_redis_stream_consumer_last_seen_unix",
    "Unix timestamp of the last successful consumer heartbeat",
    ["stream", "group", "consumer"],
)


@dataclass(slots=True)
class ProducerConfig:
    """Configuration for stream publishing behaviour."""

    stream_name: str = "gps.telemetry.raw"
    maxlen: int = 100_000
    approximate: bool = True
    timeout: float | None = 5.0
    compression_threshold_bytes: int = 512


@dataclass(slots=True)
class TelemetryEvent:
    """Canonical telemetry event payload for stream publishing."""

    device_id: UUID | str
    imei: str
    timestamp: datetime
    latitude: float
    longitude: float
    speed_kph: float
    heading: int
    accuracy: float | None = None
    battery_percent: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    trace_id: str | None = None
    correlation_id: str | None = None


class RedisTelemetryProducer:
    """High-level producer for telemetry stream publishing."""

    def __init__(
        self,
        redis_client: RedisClient,
        *,
        config: ProducerConfig | None = None,
    ) -> None:
        self._redis_client = redis_client
        self._config = config or ProducerConfig()

    async def publish_telemetry(self, event: TelemetryEvent | dict[str, Any]) -> str:
        """Publish one telemetry event via async XADD."""
        prepared = self._prepare_fields(event)
        started = time.perf_counter()
        try:
            message_id = await self._redis_client.xadd(
                self._config.stream_name,
                prepared,
                maxlen=self._config.maxlen,
                approximate=self._config.approximate,
                timeout=self._config.timeout,
            )
            _STREAM_PUBLISH_TOTAL.labels(stream=self._config.stream_name, status="ok").inc()
            _STREAM_PUBLISH_LATENCY.labels(
                stream=self._config.stream_name,
                operation="single",
            ).observe(time.perf_counter() - started)
            logger.debug(
                "stream_publish_ok",
                stream=self._config.stream_name,
                message_id=message_id,
                trace_id=prepared.get("trace_id"),
            )
            return message_id
        except Exception:
            _STREAM_PUBLISH_TOTAL.labels(stream=self._config.stream_name, status="error").inc()
            _STREAM_PUBLISH_LATENCY.labels(
                stream=self._config.stream_name,
                operation="single",
            ).observe(time.perf_counter() - started)
            raise

    async def publish_batch(self, events: list[TelemetryEvent | dict[str, Any]]) -> list[str]:
        """Publish a batch of telemetry events in one pipeline execution."""
        if not events:
            return []

        _STREAM_PUBLISH_BATCH_SIZE.labels(stream=self._config.stream_name).observe(len(events))
        started = time.perf_counter()
        prepared_batch = [self._prepare_fields(event) for event in events]

        pipe = self._redis_client.client.pipeline(transaction=False)
        try:
            for prepared in prepared_batch:
                pipe.xadd(
                    self._config.stream_name,
                    prepared,
                    id="*",
                    maxlen=self._config.maxlen,
                    approximate=self._config.approximate,
                )
            results = await self._redis_client.run_operation(
                pipe.execute,
                "xadd_batch",
                timeout=self._config.timeout,
            )
        except Exception:
            _STREAM_PUBLISH_TOTAL.labels(stream=self._config.stream_name, status="error").inc(len(events))
            _STREAM_PUBLISH_LATENCY.labels(
                stream=self._config.stream_name,
                operation="batch",
            ).observe(time.perf_counter() - started)
            raise
        finally:
            await pipe.reset()

        message_ids = [result.decode() if isinstance(result, bytes) else str(result) for result in results]
        _STREAM_PUBLISH_TOTAL.labels(stream=self._config.stream_name, status="ok").inc(len(message_ids))
        _STREAM_PUBLISH_LATENCY.labels(
            stream=self._config.stream_name,
            operation="batch",
        ).observe(time.perf_counter() - started)
        logger.debug(
            "stream_publish_batch_ok",
            stream=self._config.stream_name,
            batch_size=len(message_ids),
        )
        return message_ids

    def _prepare_fields(self, event: TelemetryEvent | dict[str, Any]) -> dict[str, str]:
        payload = self._normalize_event(event)
        trace_context = structlog.contextvars.get_contextvars()
        payload.setdefault("published_at", datetime.now(UTC).isoformat())
        payload.setdefault("trace_id", trace_context.get("trace_id") or payload.get("trace_id") or "")
        payload.setdefault(
            "correlation_id",
            trace_context.get("correlation_id") or payload.get("correlation_id") or "",
        )

        serialized = orjson.dumps(payload)
        compressed = len(serialized) >= self._config.compression_threshold_bytes
        encoded_payload = self._encode_payload(serialized, compress=compressed)
        _STREAM_PUBLISH_PAYLOAD_BYTES.labels(
            stream=self._config.stream_name,
            compressed=str(compressed).lower(),
        ).observe(len(serialized))

        return {
            "schema": "telemetry.v1",
            "content_type": "application/orjson",
            "content_encoding": "zlib+base64" if compressed else "identity+base64",
            "trace_id": str(payload.get("trace_id") or ""),
            "correlation_id": str(payload.get("correlation_id") or ""),
            "payload": encoded_payload,
        }

    def _normalize_event(self, event: TelemetryEvent | dict[str, Any]) -> dict[str, Any]:
        if isinstance(event, TelemetryEvent):
            return {
                "device_id": str(event.device_id),
                "imei": event.imei,
                "timestamp": event.timestamp.isoformat(),
                "latitude": event.latitude,
                "longitude": event.longitude,
                "speed_kph": event.speed_kph,
                "heading": event.heading,
                "accuracy": event.accuracy,
                "battery_percent": event.battery_percent,
                "attributes": event.attributes,
                "trace_id": event.trace_id,
                "correlation_id": event.correlation_id,
            }

        payload = dict(event)
        timestamp = payload.get("timestamp")
        if isinstance(timestamp, datetime):
            payload["timestamp"] = timestamp.isoformat()
        if "device_id" in payload:
            payload["device_id"] = str(payload["device_id"])
        return payload

    def _encode_payload(self, payload: bytes, *, compress: bool) -> str:
        raw = zlib.compress(payload) if compress else payload
        return base64.b64encode(raw).decode("ascii")


@dataclass
class StreamConfig:
    """Configuration for a single Redis stream."""

    name: str
    """Stream name (e.g., 'gps.telemetry.raw')."""

    maxlen: int
    """Target stream length for approximate trimming."""

    retention_hours: int | None = None
    """Optional time-based retention (not enforced; advisory)."""

    consumer_groups: list[str] = field(default_factory=list)
    """List of consumer group names to initialize."""


@dataclass
class ConsumerGroupConfig:
    """Configuration for a consumer group on a stream."""

    stream_name: str
    group_name: str
    consumer_name: str
    batch_size: int = 100
    block_ms: int = 1000
    claim_timeout_ms: int = 300_000  # 5 minutes
    idle_callback_interval_ms: int = 10_000


@dataclass(slots=True)
class StreamConsumerFrameworkConfig(ConsumerGroupConfig):
    """Configuration for the generic stream worker framework."""

    worker_count: int = 1
    max_retries: int = 3
    retry_stream_name: str | None = None
    poison_stream_name: str | None = None
    shutdown_grace_seconds: float = 10.0
    checkpoint_enabled: bool = True
    checkpoint_key: str | None = None
    checkpoint_ttl_seconds: int = 7 * 24 * 60 * 60
    claim_pending_on_start: bool = True
    claim_batch_size: int = 100
    backoff_base_seconds: float = 1.0


@dataclass
class StreamMessage:
    """Represents a message read from a Redis stream."""

    stream: str
    message_id: str
    data: dict[str, Any]
    processed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    retry_count: int = 0


@dataclass
class RetryMetadata:
    """Metadata attached to a message in the retry stream."""

    original_id: str
    retry_count: int
    last_error: str | None = None
    backoff_until: datetime | None = None
    attempted_consumer: str | None = None


class ReplayJobKind(StrEnum):
    """Kinds of replay jobs supported by the replay pipeline."""

    DEAD_LETTER = "dead_letter"
    BACKFILL = "backfill"


class ReplayJobStatus(StrEnum):
    """Execution state for a replay job."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass(slots=True)
class ReplayPipelineConfig:
    replay_stream_name: str = "replay.jobs"
    progress_key_prefix: str = "swm:stream:replay:job"
    progress_ttl_seconds: int = 30 * 24 * 60 * 60


@dataclass(slots=True)
class ReplayJobRequest:
    job_id: str
    kind: ReplayJobKind
    source_stream: str
    target_stream: str | None = None
    start_id: str = "-"
    end_id: str = "+"
    max_messages: int | None = None
    priority: int = 5
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class ReplayJobProgress:
    job_id: str
    kind: ReplayJobKind
    status: ReplayJobStatus
    source_stream: str
    target_stream: str | None
    priority: int
    start_id: str
    end_id: str
    max_messages: int | None
    total_messages: int = 0
    replayed_messages: int = 0
    failed_messages: int = 0
    last_replayed_id: str | None = None
    last_error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        denominator = self.total_messages or self.max_messages or 0
        progress_percent = 100.0 if denominator == 0 and self.status in {
            ReplayJobStatus.COMPLETED,
            ReplayJobStatus.PARTIAL,
        } else ((self.replayed_messages + self.failed_messages) / denominator * 100.0 if denominator else 0.0)
        return {
            "job_id": self.job_id,
            "kind": self.kind.value,
            "status": self.status.value,
            "source_stream": self.source_stream,
            "target_stream": self.target_stream,
            "priority": self.priority,
            "start_id": self.start_id,
            "end_id": self.end_id,
            "max_messages": self.max_messages,
            "total_messages": self.total_messages,
            "replayed_messages": self.replayed_messages,
            "failed_messages": self.failed_messages,
            "last_replayed_id": self.last_replayed_id,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "updated_at": self.updated_at.isoformat(),
            "progress_percent": round(progress_percent, 2),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ReplayJobProgress:
        return cls(
            job_id=str(payload["job_id"]),
            kind=ReplayJobKind(str(payload["kind"])),
            status=ReplayJobStatus(str(payload["status"])),
            source_stream=str(payload["source_stream"]),
            target_stream=str(payload["target_stream"]) if payload.get("target_stream") else None,
            priority=int(payload.get("priority") or 0),
            start_id=str(payload.get("start_id") or "-"),
            end_id=str(payload.get("end_id") or "+"),
            max_messages=int(payload["max_messages"]) if payload.get("max_messages") not in (None, "") else None,
            total_messages=int(payload.get("total_messages") or 0),
            replayed_messages=int(payload.get("replayed_messages") or 0),
            failed_messages=int(payload.get("failed_messages") or 0),
            last_replayed_id=str(payload["last_replayed_id"]) if payload.get("last_replayed_id") else None,
            last_error=str(payload["last_error"]) if payload.get("last_error") else None,
            created_at=datetime.fromisoformat(str(payload["created_at"])),
            started_at=datetime.fromisoformat(str(payload["started_at"])) if payload.get("started_at") else None,
            finished_at=datetime.fromisoformat(str(payload["finished_at"])) if payload.get("finished_at") else None,
            updated_at=datetime.fromisoformat(str(payload["updated_at"])),
        )


class PoisonMessageError(Exception):
    """Raised when a message should be sent directly to the poison queue."""


def _decode_stream_data(data: dict[Any, Any]) -> dict[str, Any]:
    return {
        key.decode() if isinstance(key, bytes) else str(key): value.decode() if isinstance(value, bytes) else value
        for key, value in data.items()
    }


def _decode_stream_message(stream_name: Any, message_id: Any, data: dict[Any, Any]) -> StreamMessage:
    return StreamMessage(
        stream=stream_name.decode() if isinstance(stream_name, bytes) else str(stream_name),
        message_id=message_id.decode() if isinstance(message_id, bytes) else str(message_id),
        data=_decode_stream_data(data),
    )


class AbstractStreamConsumer(ABC):
    """Generic Redis stream worker framework based on XREADGROUP."""

    def __init__(self, topology: StreamTopology, config: StreamConsumerFrameworkConfig) -> None:
        self.topology = topology
        self.config = config
        self._stop_event = asyncio.Event()
        self._tasks: list[asyncio.Task[None]] = []

    @abstractmethod
    async def handle_message(self, message: StreamMessage) -> None:
        """Process one stream message."""

    async def start(self) -> None:
        if self._tasks:
            return
        for worker_index in range(self.config.worker_count):
            task = asyncio.create_task(
                self._worker_loop(worker_index),
                name=f"stream-worker:{self.config.group_name}:{worker_index}",
            )
            self._tasks.append(task)

    async def run(self) -> None:
        await self.start()
        await asyncio.gather(*self._tasks)

    async def shutdown(self) -> None:
        self._stop_event.set()
        if not self._tasks:
            return

        done, pending = await asyncio.wait(self._tasks, timeout=self.config.shutdown_grace_seconds)
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        await asyncio.gather(*done, return_exceptions=True)
        self._tasks.clear()

    def stop(self) -> None:
        self._stop_event.set()

    async def _worker_loop(self, worker_index: int) -> None:
        consumer_name = self._worker_name(worker_index)
        bind_worker_context(worker_name=consumer_name, stream=self.config.stream_name)
        self._set_consumer_health(consumer_name, 1.0)
        try:
            if self.config.claim_pending_on_start:
                claimed = await self._claim_pending(consumer_name)
                for message in claimed:
                    if self._stop_event.is_set():
                        return
                    await self._process_message(message, consumer_name)

            while not self._stop_event.is_set():
                self._touch_consumer(consumer_name)
                entries = await self.topology.redis_client.xreadgroup(
                    self.config.group_name,
                    consumer_name,
                    {self.config.stream_name: ">"},
                    count=self.config.batch_size,
                    block=self.config.block_ms,
                )
                if not entries:
                    continue

                for stream_name, messages in entries:
                    for message_id, data in messages:
                        if self._stop_event.is_set():
                            return
                        await self._process_message(
                            _decode_stream_message(stream_name, message_id, data),
                            consumer_name,
                        )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(
                "stream_worker_failed",
                stream=self.config.stream_name,
                group=self.config.group_name,
                consumer=consumer_name,
                error=str(exc),
            )
        finally:
            self._set_consumer_health(consumer_name, 0.0)
            clear_context()

    async def _process_message(self, message: StreamMessage, consumer_name: str) -> None:
        self._touch_consumer(consumer_name)
        self._observe_stream_lag(message, consumer_name)
        try:
            await self.handle_message(message)
            await self._ack_and_checkpoint(message)
        except PoisonMessageError as exc:
            await self._send_to_poison_queue(message, str(exc), consumer_name)
            await self._ack_and_checkpoint(message)
        except Exception as exc:
            retry_count = self._next_retry_count(message)
            if retry_count <= self.config.max_retries:
                await self._retry_message(message, exc, retry_count, consumer_name)
                await self._ack_and_checkpoint(message)
            else:
                await self._send_to_poison_queue(message, str(exc), consumer_name, retry_count=retry_count)
                await self._ack_and_checkpoint(message)

    async def _retry_message(
        self,
        message: StreamMessage,
        exc: Exception,
        retry_count: int,
        consumer_name: str,
    ) -> None:
        backoff_seconds = self._calculate_backoff_seconds(retry_count)
        retry_payload = dict(message.data)
        retry_payload.update(
            {
                "original_stream": message.stream,
                "original_message_id": message.message_id,
                "retry_count": str(retry_count),
                "last_error": str(exc),
                "backoff_until": (datetime.now(UTC) + timedelta(seconds=backoff_seconds)).isoformat(),
                "consumer_name": consumer_name,
            }
        )
        await self.topology.redis_client.xadd(
            self._retry_stream_name,
            {key: str(value) for key, value in retry_payload.items()},
        )
        logger.warning(
            "stream_message_retried",
            stream=self.config.stream_name,
            retry_stream=self._retry_stream_name,
            message_id=message.message_id,
            retry_count=retry_count,
            backoff_seconds=backoff_seconds,
        )

    async def _send_to_poison_queue(
        self,
        message: StreamMessage,
        error: str,
        consumer_name: str,
        *,
        retry_count: int | None = None,
    ) -> None:
        poison_payload = dict(message.data)
        poison_payload.update(
            {
                "original_stream": message.stream,
                "original_message_id": message.message_id,
                "poisoned_at": datetime.now(UTC).isoformat(),
                "last_error": error,
                "consumer_name": consumer_name,
                "retry_count": str(retry_count if retry_count is not None else self._current_retry_count(message)),
            }
        )
        await self.topology.redis_client.xadd(
            self._poison_stream_name,
            {key: str(value) for key, value in poison_payload.items()},
        )
        logger.error(
            "stream_message_poisoned",
            stream=self.config.stream_name,
            poison_stream=self._poison_stream_name,
            message_id=message.message_id,
            error=error,
        )

    async def _ack_and_checkpoint(self, message: StreamMessage) -> None:
        await self.topology.redis_client.xack(
            self.config.stream_name,
            self.config.group_name,
            message.message_id,
        )
        if not self.config.checkpoint_enabled:
            return

        await self.topology.redis_client.set_json(
            self._checkpoint_key,
            {
                "stream": self.config.stream_name,
                "group": self.config.group_name,
                "message_id": message.message_id,
                "updated_at": datetime.now(UTC).isoformat(),
            },
            ttl=self.config.checkpoint_ttl_seconds,
        )

    async def _claim_pending(self, consumer_name: str) -> list[StreamMessage]:
        claimed = await self.topology.redis_client.xautoclaim(
            self.config.stream_name,
            self.config.group_name,
            consumer_name,
            self.config.claim_timeout_ms,
            "0",
            count=self.config.claim_batch_size,
        )
        if not claimed or len(claimed) < 2:
            return []
        return [
            _decode_stream_message(self.config.stream_name, message_id, data)
            for message_id, data in claimed[1]
        ]

    def _worker_name(self, worker_index: int) -> str:
        if self.config.worker_count == 1:
            return self.config.consumer_name
        return f"{self.config.consumer_name}-{worker_index}"

    def _current_retry_count(self, message: StreamMessage) -> int:
        raw = message.data.get("retry_count")
        try:
            return int(raw) if raw is not None else message.retry_count
        except (TypeError, ValueError):
            return message.retry_count

    def _next_retry_count(self, message: StreamMessage) -> int:
        return self._current_retry_count(message) + 1

    def _calculate_backoff_seconds(self, retry_count: int) -> float:
        return self.config.backoff_base_seconds * (2 ** max(retry_count - 1, 0))

    def _observe_stream_lag(self, message: StreamMessage, consumer_name: str) -> None:
        lag_seconds = self._message_lag_seconds(message.message_id)
        if lag_seconds is None:
            return
        _STREAM_CONSUMER_LAG_SECONDS.labels(
            stream=self.config.stream_name,
            group=self.config.group_name,
            consumer=consumer_name,
        ).set(lag_seconds)

    def _touch_consumer(self, consumer_name: str) -> None:
        _STREAM_CONSUMER_LAST_SEEN_UNIX.labels(
            stream=self.config.stream_name,
            group=self.config.group_name,
            consumer=consumer_name,
        ).set(datetime.now(UTC).timestamp())

    def _set_consumer_health(self, consumer_name: str, value: float) -> None:
        _STREAM_CONSUMER_HEALTH.labels(
            stream=self.config.stream_name,
            group=self.config.group_name,
            consumer=consumer_name,
        ).set(value)

    def _message_lag_seconds(self, message_id: str) -> float | None:
        try:
            stream_ms = int(message_id.split("-", 1)[0])
        except (IndexError, TypeError, ValueError):
            return None
        return max((datetime.now(UTC).timestamp() * 1000 - stream_ms) / 1000.0, 0.0)

    @property
    def _retry_stream_name(self) -> str:
        return self.config.retry_stream_name or f"{self.config.stream_name}.retry"

    @property
    def _poison_stream_name(self) -> str:
        return self.config.poison_stream_name or f"{self.config.stream_name}.poison"

    @property
    def _checkpoint_key(self) -> str:
        return self.config.checkpoint_key or (
            f"swm:stream:checkpoint:{self.config.stream_name}:{self.config.group_name}"
        )


class RedisReplayPipeline:
    """Replay jobs for dead-letter reprocessing and stream backfills."""

    _POISON_METADATA_FIELDS = {
        "original_stream",
        "original_message_id",
        "poisoned_at",
        "last_error",
        "consumer_name",
        "retry_count",
    }

    def __init__(self, topology: StreamTopology, *, config: ReplayPipelineConfig | None = None) -> None:
        self.topology = topology
        self.config = config or ReplayPipelineConfig()

    async def enqueue_dead_letter_reprocess(
        self,
        *,
        job_id: UUID | str,
        poison_stream: str,
        target_stream: str | None = None,
        start_id: str = "-",
        end_id: str = "+",
        max_messages: int | None = None,
        priority: int = 5,
    ) -> str:
        return await self.enqueue_job(
            ReplayJobRequest(
                job_id=str(job_id),
                kind=ReplayJobKind.DEAD_LETTER,
                source_stream=poison_stream,
                target_stream=target_stream,
                start_id=start_id,
                end_id=end_id,
                max_messages=max_messages,
                priority=self._normalize_priority(priority),
            )
        )

    async def enqueue_backfill(
        self,
        *,
        job_id: UUID | str,
        source_stream: str,
        target_stream: str,
        start_id: str = "-",
        end_id: str = "+",
        max_messages: int | None = None,
        priority: int = 5,
    ) -> str:
        return await self.enqueue_job(
            ReplayJobRequest(
                job_id=str(job_id),
                kind=ReplayJobKind.BACKFILL,
                source_stream=source_stream,
                target_stream=target_stream,
                start_id=start_id,
                end_id=end_id,
                max_messages=max_messages,
                priority=self._normalize_priority(priority),
            )
        )

    async def enqueue_job(self, job: ReplayJobRequest) -> str:
        message_id = await self.topology.redis_client.xadd(
            self.config.replay_stream_name,
            {
                "job_id": job.job_id,
                "job_type": "replay",
                "replay_kind": job.kind.value,
                "source_stream": job.source_stream,
                "target_stream": job.target_stream or "",
                "start_id": job.start_id,
                "end_id": job.end_id,
                "max_messages": str(job.max_messages) if job.max_messages is not None else "",
                "priority": str(self._normalize_priority(job.priority)),
                "created_at": job.created_at.isoformat(),
            },
        )
        progress = ReplayJobProgress(
            job_id=job.job_id,
            kind=job.kind,
            status=ReplayJobStatus.QUEUED,
            source_stream=job.source_stream,
            target_stream=job.target_stream,
            priority=self._normalize_priority(job.priority),
            start_id=job.start_id,
            end_id=job.end_id,
            max_messages=job.max_messages,
            created_at=job.created_at,
        )
        await self._write_progress(progress)
        _STREAM_REPLAY_JOB_TOTAL.labels(kind=job.kind.value, status=ReplayJobStatus.QUEUED.value).inc()
        return message_id

    async def process_job(self, job: ReplayJobRequest) -> ReplayJobProgress:
        progress = ReplayJobProgress(
            job_id=job.job_id,
            kind=job.kind,
            status=ReplayJobStatus.RUNNING,
            source_stream=job.source_stream,
            target_stream=job.target_stream,
            priority=self._normalize_priority(job.priority),
            start_id=job.start_id,
            end_id=job.end_id,
            max_messages=job.max_messages,
            created_at=job.created_at,
            started_at=datetime.now(UTC),
        )
        await self._write_progress(progress)
        _STREAM_REPLAY_JOB_TOTAL.labels(kind=job.kind.value, status=ReplayJobStatus.RUNNING.value).inc()

        try:
            entries = await self.topology.redis_client.xrange(
                job.source_stream,
                min_id=job.start_id,
                max_id=job.end_id,
                count=job.max_messages,
            )
            progress.total_messages = len(entries)
            await self._write_progress(progress)

            for message_id, data in entries:
                message = _decode_stream_message(job.source_stream, message_id, data)
                try:
                    target_stream = self._resolve_target_stream(job, message)
                    replay_payload = self._build_replay_payload(job, message)
                    await self.topology.redis_client.xadd(target_stream, replay_payload)
                    progress.replayed_messages += 1
                    progress.last_replayed_id = message.message_id
                    _STREAM_REPLAY_MESSAGE_TOTAL.labels(kind=job.kind.value, status="ok").inc()
                except Exception as exc:
                    progress.failed_messages += 1
                    progress.last_error = str(exc)
                    _STREAM_REPLAY_MESSAGE_TOTAL.labels(kind=job.kind.value, status="error").inc()
                    logger.error(
                        "stream_replay_message_failed",
                        job_id=job.job_id,
                        kind=job.kind.value,
                        source_stream=job.source_stream,
                        message_id=message.message_id,
                        error=str(exc),
                    )
                progress.updated_at = datetime.now(UTC)
                await self._write_progress(progress)
        except Exception as exc:
            progress.status = ReplayJobStatus.FAILED
            progress.last_error = str(exc)
            progress.finished_at = datetime.now(UTC)
            progress.updated_at = progress.finished_at
            await self._write_progress(progress)
            _STREAM_REPLAY_JOB_TOTAL.labels(kind=job.kind.value, status=ReplayJobStatus.FAILED.value).inc()
            logger.error(
                "stream_replay_job_failed",
                job_id=job.job_id,
                kind=job.kind.value,
                source_stream=job.source_stream,
                error=str(exc),
            )
            return progress

        progress.finished_at = datetime.now(UTC)
        progress.updated_at = progress.finished_at
        progress.status = ReplayJobStatus.PARTIAL if progress.failed_messages else ReplayJobStatus.COMPLETED
        await self._write_progress(progress)
        _STREAM_REPLAY_JOB_TOTAL.labels(kind=job.kind.value, status=progress.status.value).inc()
        logger.info(
            "stream_replay_job_completed",
            job_id=job.job_id,
            kind=job.kind.value,
            source_stream=job.source_stream,
            target_stream=job.target_stream,
            replayed_messages=progress.replayed_messages,
            failed_messages=progress.failed_messages,
        )
        return progress

    def parse_job(self, message: StreamMessage) -> ReplayJobRequest:
        created_at_raw = message.data.get("created_at")
        return ReplayJobRequest(
            job_id=str(message.data["job_id"]),
            kind=ReplayJobKind(str(message.data["replay_kind"])),
            source_stream=str(message.data["source_stream"]),
            target_stream=str(message.data["target_stream"]) if message.data.get("target_stream") else None,
            start_id=str(message.data.get("start_id") or "-"),
            end_id=str(message.data.get("end_id") or "+"),
            max_messages=self._parse_optional_int(message.data.get("max_messages")),
            priority=self._normalize_priority(self._parse_optional_int(message.data.get("priority")) or 5),
            created_at=datetime.fromisoformat(str(created_at_raw)) if created_at_raw else datetime.now(UTC),
        )

    async def get_progress(self, job_id: UUID | str) -> ReplayJobProgress | None:
        raw = await self.topology.redis_client.get_json(self.progress_key(str(job_id)))
        if raw is None:
            return None
        return ReplayJobProgress.from_dict(raw)

    def progress_key(self, job_id: str) -> str:
        return f"{self.config.progress_key_prefix}:{job_id}"

    async def _write_progress(self, progress: ReplayJobProgress) -> None:
        progress.updated_at = datetime.now(UTC)
        await self.topology.redis_client.set_json(
            self.progress_key(progress.job_id),
            progress.to_dict(),
            ttl=self.config.progress_ttl_seconds,
        )

    def _resolve_target_stream(self, job: ReplayJobRequest, message: StreamMessage) -> str:
        if job.target_stream:
            return job.target_stream
        if job.kind is ReplayJobKind.DEAD_LETTER:
            original_stream = message.data.get("original_stream")
            if original_stream:
                return str(original_stream)
        return job.source_stream

    def _build_replay_payload(self, job: ReplayJobRequest, message: StreamMessage) -> dict[str, str]:
        if job.kind is ReplayJobKind.BACKFILL:
            return {key: str(value) for key, value in message.data.items()}

        return {
            key: str(value)
            for key, value in message.data.items()
            if key not in self._POISON_METADATA_FIELDS
        }

    def _normalize_priority(self, priority: int) -> int:
        return max(1, min(priority, 10))

    def _parse_optional_int(self, raw: Any) -> int | None:
        if raw in (None, ""):
            return None
        return int(raw)


class RedisReplayJobProcessor(AbstractStreamConsumer):
    """Consumer-group worker that executes replay jobs from replay.jobs."""

    def __init__(
        self,
        topology: StreamTopology,
        replay_pipeline: RedisReplayPipeline,
        config: StreamConsumerFrameworkConfig | None = None,
    ) -> None:
        super().__init__(
            topology,
            config
            or StreamConsumerFrameworkConfig(
                stream_name=replay_pipeline.config.replay_stream_name,
                group_name="replay-worker:job-processor",
                consumer_name="replay-worker",
                retry_stream_name=f"{replay_pipeline.config.replay_stream_name}.retry",
                poison_stream_name=f"{replay_pipeline.config.replay_stream_name}.poison",
            ),
        )
        self.replay_pipeline = replay_pipeline

    async def handle_message(self, message: StreamMessage) -> None:
        await self.replay_pipeline.process_job(self.replay_pipeline.parse_job(message))

    async def _worker_loop(self, worker_index: int) -> None:
        consumer_name = self._worker_name(worker_index)
        bind_worker_context(worker_name=consumer_name, stream=self.config.stream_name)
        try:
            if self.config.claim_pending_on_start:
                claimed = await self._claim_pending(consumer_name)
                for message in self._prioritize_messages(claimed):
                    if self._stop_event.is_set():
                        return
                    await self._process_message(message, consumer_name)

            while not self._stop_event.is_set():
                entries = await self.topology.redis_client.xreadgroup(
                    self.config.group_name,
                    consumer_name,
                    {self.config.stream_name: ">"},
                    count=self.config.batch_size,
                    block=self.config.block_ms,
                )
                if not entries:
                    continue

                decoded_messages: list[StreamMessage] = []
                for stream_name, messages in entries:
                    for message_id, data in messages:
                        decoded_messages.append(_decode_stream_message(stream_name, message_id, data))

                for message in self._prioritize_messages(decoded_messages):
                    if self._stop_event.is_set():
                        return
                    await self._process_message(message, consumer_name)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(
                "replay_worker_failed",
                stream=self.config.stream_name,
                group=self.config.group_name,
                consumer=consumer_name,
                error=str(exc),
            )
        finally:
            clear_context()

    def _prioritize_messages(self, messages: list[StreamMessage]) -> list[StreamMessage]:
        return sorted(messages, key=self._message_priority, reverse=True)

    def _message_priority(self, message: StreamMessage) -> int:
        try:
            return int(message.data.get("priority", 0))
        except (TypeError, ValueError):
            return 0


class StreamTopology:
    """
    Manages the Redis Streams topology for the GPS Fleet platform.

    Handles:
    - Stream and consumer group initialization
    - Publishing messages
    - Consuming with automatic retry and DLQ
    - Dead-letter queue management
    - Metrics and monitoring hooks
    """

    # Default stream configurations
    DEFAULT_STREAMS = [
        StreamConfig(
            name="gps.telemetry.raw",
            maxlen=100_000,
            retention_hours=1,
            consumer_groups=["ingestion-api:telemetry-processor", "analytics-worker:telemetry-consumer"],
        ),
        StreamConfig(
            name="gps.telemetry.retry",
            maxlen=50_000,
            retention_hours=0.5,
            consumer_groups=["retry-worker:telemetry-retry-processor"],
        ),
        StreamConfig(
            name="gps.telemetry.failed",
            maxlen=10_000,
            retention_hours=72,
            consumer_groups=["dlq-monitor:telemetry-failure-handler"],
        ),
        StreamConfig(
            name="analytics.jobs",
            maxlen=50_000,
            retention_hours=24,
            consumer_groups=["analytics-worker:job-processor"],
        ),
        StreamConfig(
            name="report.jobs",
            maxlen=30_000,
            retention_hours=24,
            consumer_groups=["report-worker:job-processor"],
        ),
        StreamConfig(
            name="alert.events.stream",
            maxlen=100_000,
            retention_hours=168,  # 7 days
            consumer_groups=["alert-worker:event-processor"],
        ),
        StreamConfig(
            name="replay.jobs",
            maxlen=20_000,
            retention_hours=720,  # 30 days
            consumer_groups=["replay-worker:job-processor"],
        ),
    ]

    MAX_RETRIES = 3
    RETRY_STREAM = "gps.telemetry.retry"
    DLQ_STREAM = "gps.telemetry.failed"

    def __init__(self, redis_client: RedisClient | None = None, redis_url: str | None = None):
        """
        Initialize the stream topology.

        Args:
            redis_client: Existing RedisClient instance (preferred).
            redis_url: Redis connection URL (used to create RedisClient if redis_client not provided).
        """
        if redis_client is not None:
            self.redis_client = redis_client
        elif redis_url is not None:
            self.redis_client = RedisClient.from_url(redis_url)
        else:
            raise ValueError("Either redis_client or redis_url must be provided")
        self.telemetry_producer = RedisTelemetryProducer(
            self.redis_client,
            config=ProducerConfig(
                stream_name="gps.telemetry.raw",
                maxlen=self._stream_maxlen("gps.telemetry.raw"),
            ),
        )

    def _stream_maxlen(self, stream_name: str) -> int:
        for cfg in self.DEFAULT_STREAMS:
            if cfg.name == stream_name:
                return cfg.maxlen
        return 100_000

    async def initialize(self, streams: list[StreamConfig] | None = None) -> None:
        """
        Create all streams and consumer groups.

        Args:
            streams: Optional list of StreamConfig objects. If None, uses DEFAULT_STREAMS.
        """
        if streams is None:
            streams = self.DEFAULT_STREAMS

        redis = self.redis_client.client
        for stream_cfg in streams:
            # Create stream (MKSTREAM ensures it exists)
            try:
                await redis.execute_command(
                    "XGROUP", "CREATE", stream_cfg.name, "$group$", "$", "MKSTREAM"
                )
                logger.info("created_stream", stream=stream_cfg.name)
            except Exception as e:
                if "BUSYGROUP" in str(e):
                    logger.debug("stream_exists", stream=stream_cfg.name)
                else:
                    logger.error("failed_to_create_stream", stream=stream_cfg.name, error=str(e))
                    raise

            # Create consumer groups for this stream
            for group_name in stream_cfg.consumer_groups:
                try:
                    await redis.execute_command("XGROUP", "CREATE", stream_cfg.name, group_name, "$", "MKSTREAM")
                    logger.info("created_consumer_group", stream=stream_cfg.name, group=group_name)
                except Exception as e:
                    if "BUSYGROUP" in str(e):
                        logger.debug("group_exists", stream=stream_cfg.name, group=group_name)
                    else:
                        logger.error(
                            "failed_to_create_group",
                            stream=stream_cfg.name,
                            group=group_name,
                            error=str(e),
                        )

    async def publish_telemetry(
        self,
        device_id: UUID | str,
        imei: str,
        timestamp: datetime,
        latitude: float,
        longitude: float,
        speed_kph: float,
        heading: int,
        accuracy: float | None = None,
        battery_percent: float | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> str:
        """
        Publish a GPS telemetry message to gps.telemetry.raw.

        Args:
            device_id: Device UUID
            imei: Device IMEI
            timestamp: Telemetry timestamp
            latitude: Latitude
            longitude: Longitude
            speed_kph: Speed in km/h
            heading: Heading in degrees (0-359)
            accuracy: Optional accuracy in meters
            battery_percent: Optional battery percentage (0-100)
            attributes: Optional custom attributes dict

        Returns:
            Message ID assigned by Redis
        """
        return await self.telemetry_producer.publish_telemetry(
            TelemetryEvent(
                device_id=device_id,
                imei=imei,
                timestamp=timestamp,
                latitude=latitude,
                longitude=longitude,
                speed_kph=speed_kph,
                heading=heading,
                accuracy=accuracy,
                battery_percent=battery_percent,
                attributes=attributes or {},
            )
        )

    async def publish_job(
        self,
        stream_name: str,
        job_id: UUID | str,
        job_type: str,
        parameters: dict[str, Any],
        priority: int = 5,
        scheduled_for: datetime | None = None,
    ) -> str:
        """
        Publish a job message to a job stream (analytics.jobs, report.jobs, etc.).

        Args:
            stream_name: Target stream (must be a job stream)
            job_id: Unique job ID
            job_type: Type of job
            parameters: Job parameters dict
            priority: Priority 1-10 (higher = more important)
            scheduled_for: Optional time to process

        Returns:
            Message ID
        """
        if scheduled_for is None:
            scheduled_for = datetime.now(UTC)

        message = {
            "job_id": str(job_id),
            "job_type": job_type,
            "parameters": str(parameters),
            "priority": str(priority),
            "scheduled_for": scheduled_for.isoformat(),
            "created_at": datetime.now(UTC).isoformat(),
        }
        redis = self.redis_client.client
        message_id = await redis.xadd(stream_name, message)
        logger.debug("published_job", stream=stream_name, job_id=job_id, message_id=message_id)
        return message_id.decode() if isinstance(message_id, bytes) else message_id

    async def publish_alert(
        self,
        alert_id: UUID | str,
        alert_type: str,
        severity: str,
        device_id: UUID | str,
        vehicle_id: UUID | str | None,
        context: dict[str, Any],
        recipients: list[str] | None = None,
    ) -> str:
        """
        Publish an alert event to alert.events.stream.

        Args:
            alert_id: Unique alert ID
            alert_type: Type of alert (geofence_breach, speed_violation, etc.)
            severity: Severity level (critical, warning, info)
            device_id: Device that triggered alert
            vehicle_id: Optional vehicle ID
            context: Alert context (rule_id, threshold, etc.)
            recipients: List of recipient IDs

        Returns:
            Message ID
        """
        message = {
            "alert_id": str(alert_id),
            "alert_type": alert_type,
            "severity": severity,
            "device_id": str(device_id),
            "vehicle_id": str(vehicle_id) if vehicle_id else "",
            "triggered_at": datetime.now(UTC).isoformat(),
            "context": str(context),
            "recipients": str(recipients or []),
        }
        redis = self.redis_client.client
        message_id = await redis.xadd("alert.events.stream", message)
        logger.debug("published_alert", stream="alert.events.stream", alert_id=alert_id, message_id=message_id)
        return message_id.decode() if isinstance(message_id, bytes) else message_id

    def create_consumer(self, config: ConsumerGroupConfig) -> StreamConsumer:
        """
        Create a consumer for reading from a stream with a consumer group.

        Args:
            config: ConsumerGroupConfig with stream, group, consumer name, etc.

        Returns:
            StreamConsumer instance ready to read messages
        """
        return StreamConsumer(self, config)

    async def enqueue_retry(
        self,
        original_message: StreamMessage,
        error: str | None = None,
        retry_count: int | None = None,
        consumer_name: str | None = None,
    ) -> str:
        """
        Move a message to the retry stream with metadata.

        Args:
            original_message: The original failed message
            error: Error message from the failure
            retry_count: Number of retries so far (incremented here)
            consumer_name: Name of the consumer that failed

        Returns:
            Message ID in retry stream
        """
        retry_count = (retry_count or original_message.retry_count) + 1

        if retry_count > self.MAX_RETRIES:
            logger.warning(
                "max_retries_exceeded",
                original_id=original_message.message_id,
                retry_count=retry_count,
            )
            return await self.enqueue_dlq(
                original_message,
                final_error=error,
                failure_reason="max_retries_exceeded",
                last_consumer=consumer_name,
            )

        backoff_sec = self._calculate_backoff(retry_count - 1)
        backoff_until = datetime.now(UTC) + timedelta(seconds=backoff_sec)

        retry_msg = {
            "original_id": original_message.message_id,
            "payload": str(original_message.data),
            "retry_count": str(retry_count),
            "last_error": error or "",
            "backoff_until": backoff_until.isoformat(),
            "attempted_consumer": consumer_name or "unknown",
        }

        redis = self.redis_client.client
        message_id = await redis.xadd(self.RETRY_STREAM, retry_msg)
        logger.warning(
            "enqueued_retry",
            original_id=original_message.message_id,
            retry_count=retry_count,
            backoff_sec=backoff_sec,
        )
        return message_id.decode() if isinstance(message_id, bytes) else message_id

    async def enqueue_dlq(
        self,
        original_message: StreamMessage,
        final_error: str | None = None,
        failure_reason: str = "unknown",
        last_consumer: str | None = None,
    ) -> str:
        """
        Move a message to the dead-letter queue (DLQ).

        Args:
            original_message: The original failed message
            final_error: Final error message
            failure_reason: Reason for DLQ (max_retries_exceeded, permanent_error, etc.)
            last_consumer: Name of the consumer that last attempted

        Returns:
            Message ID in DLQ stream
        """
        dlq_msg = {
            "original_id": original_message.message_id,
            "payload": str(original_message.data),
            "retry_count": str(original_message.retry_count),
            "final_error": final_error or "",
            "failed_at": datetime.now(UTC).isoformat(),
            "failure_reason": failure_reason,
            "last_consumer": last_consumer or "unknown",
            "debug_info": "{}",
        }

        redis = self.redis_client.client
        message_id = await redis.xadd(self.DLQ_STREAM, dlq_msg)
        logger.error(
            "enqueued_dlq",
            original_id=original_message.message_id,
            failure_reason=failure_reason,
            error=final_error,
        )

        # Emit metric/alert for DLQ growth
        await self._on_dlq_entry(original_message.message_id, failure_reason)

        return message_id.decode() if isinstance(message_id, bytes) else message_id

    def _calculate_backoff(self, retry_count: int) -> int:
        """
        Calculate exponential backoff in seconds.

        retry_count=0 → 1s
        retry_count=1 → 4s
        retry_count=2 → 16s
        """
        import random

        base_delay = 2 ** (2 * retry_count)  # 1, 4, 16
        jitter = random.uniform(0, base_delay * 0.1)
        return int(base_delay + jitter)

    async def _on_dlq_entry(self, original_id: str, failure_reason: str) -> None:
        """Hook for monitoring/alerting on DLQ entries."""
        # Placeholder for metrics emission, alerting, etc.
        logger.info("dlq_entry_hook", original_id=original_id, failure_reason=failure_reason)

    async def get_stream_stats(self, stream_name: str) -> dict[str, Any]:
        """
        Get statistics about a stream (length, pending, etc.).

        Args:
            stream_name: Name of the stream

        Returns:
            Dict with stream stats
        """
        redis = self.redis_client.client
        info = await redis.xinfo_stream(stream_name)
        return {
            "length": info.get("length", 0),
            "first_entry": info.get("first-entry"),
            "last_entry": info.get("last-entry"),
        }

    async def get_consumer_group_stats(self, stream_name: str, group_name: str) -> dict[str, Any]:
        """
        Get statistics about a consumer group on a stream.

        Args:
            stream_name: Name of the stream
            group_name: Name of the consumer group

        Returns:
            Dict with group stats (consumers, pending, lag, etc.)
        """
        redis = self.redis_client.client
        try:
            groups_info = await redis.xinfo_groups(stream_name)
            for group_info in groups_info or []:
                if group_info.get("name") == group_name:
                    return {
                        "name": group_info.get("name"),
                        "consumers": group_info.get("consumers", 0),
                        "pending": group_info.get("pending", 0),
                        "last_delivered_id": group_info.get("last-delivered-id"),
                    }
        except Exception as e:
            logger.error("failed_to_get_group_stats", stream=stream_name, group=group_name, error=str(e))

        return {}

    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()


class StreamConsumer:
    """
    Reads messages from a Redis stream with consumer group semantics.

    Provides:
    - Batch reading with blocking
    - Automatic acknowledgment
    - Claimed pending entry handling
    """

    def __init__(self, topology: StreamTopology, config: ConsumerGroupConfig):
        """
        Initialize a stream consumer.

        Args:
            topology: Parent StreamTopology instance
            config: Consumer configuration
        """
        self.topology = topology
        self.config = config
        self.redis = topology.redis_client.client

    async def read_stream(self, batch_size: int | None = None, block_ms: int | None = None):
        """
        Generator that yields messages from the stream.

        Automatically claims pending entries and respects backoff times.

        Args:
            batch_size: Number of messages to read per batch (uses config default if None)
            block_ms: Blocking time in ms (uses config default if None)

        Yields:
            StreamMessage objects
        """
        batch_size = batch_size or self.config.batch_size
        block_ms = block_ms or self.config.block_ms

        while True:
            # Read new messages and claimed pending entries
            try:
                messages = await self.redis.xreadgroup(
                    self.config.group_name,
                    self.config.consumer_name,
                    {self.config.stream_name: ">"},
                    count=batch_size,
                    block=block_ms,
                )

                if messages:
                    for stream_name, msg_list in messages:
                        for message_id, data in msg_list:
                            yield _decode_stream_message(stream_name, message_id, data)
            except Exception as e:
                logger.error("stream_read_error", stream=self.config.stream_name, error=str(e))
                await asyncio.sleep(1)  # Backoff before retry

    async def ack(self, message: StreamMessage) -> None:
        """
        Acknowledge a message (remove from pending entry list).

        Args:
            message: StreamMessage to acknowledge
        """
        try:
            await self.redis.xack(self.config.stream_name, self.config.group_name, message.message_id)
            logger.debug("message_acked", stream=self.config.stream_name, message_id=message.message_id)
        except Exception as e:
            logger.error(
                "ack_failed",
                stream=self.config.stream_name,
                message_id=message.message_id,
                error=str(e),
            )

    async def claim_pending(self, min_idle_ms: int | None = None) -> list[StreamMessage]:
        """
        Attempt to claim pending entries from other consumers.

        Used to recover messages from crashed/slow consumers.

        Args:
            min_idle_ms: Minimum idle time before claiming (uses config claim_timeout_ms if None)

        Returns:
            List of claimed messages
        """
        min_idle_ms = min_idle_ms or self.config.claim_timeout_ms

        try:
            pending = await self.redis.xautoclaim(
                self.config.stream_name,
                self.config.group_name,
                self.config.consumer_name,
                min_idle_ms,
                "0",
                count=100,
            )

            claimed_messages = []
            if pending and len(pending) > 1:
                for message_id, data in pending[1]:
                    claimed_messages.append(_decode_stream_message(self.config.stream_name, message_id, data))

            if claimed_messages:
                logger.info(
                    "claimed_pending_entries",
                    stream=self.config.stream_name,
                    count=len(claimed_messages),
                )

            return claimed_messages
        except Exception as e:
            logger.error(
                "claim_failed",
                stream=self.config.stream_name,
                group=self.config.group_name,
                error=str(e),
            )
            return []
