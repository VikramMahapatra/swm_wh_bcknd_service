from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
import signal
from typing import Any

from prometheus_client import Counter, Gauge, Histogram
from redis.exceptions import BusyLoadingError, RedisError
from swm_common import get_logger
from swm_redis.client import RedisClient

logger = get_logger("swm_redis.stream_consumer")

_CONSUMER_BATCH_TOTAL = Counter(
    "swm_stream_consumer_batch_total",
    "Total stream batches consumed",
    ["stream", "group", "status"],
)
_CONSUMER_MESSAGE_TOTAL = Counter(
    "swm_stream_consumer_message_total",
    "Total stream messages consumed",
    ["stream", "group", "status"],
)
_CONSUMER_BATCH_SECONDS = Histogram(
    "swm_stream_consumer_batch_seconds",
    "Batch handling duration in seconds",
    ["stream", "group"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)
_CONSUMER_PENDING = Gauge(
    "swm_stream_consumer_pending",
    "Pending messages in consumer group",
    ["stream", "group"],
)


@dataclass(slots=True)
class StreamConsumerRecord:
    stream: str
    message_id: str
    data: dict[str, Any]


@dataclass(slots=True)
class StreamConsumerSettings:
    stream: str = "gps.telemetry.raw"
    group: str = "storage"
    consumer_name: str = "storage-1"
    block_ms: int = 1000
    batch_size: int = 1000
    max_retries: int = 3
    retry_stream: str = "gps.telemetry.retry"
    poison_stream: str = "gps.telemetry.failed"
    pending_idle_ms: int = 120000
    claim_batch_size: int = 500
    checkpoint_key: str = "swm:stream:checkpoint"
    checkpoint_ttl_seconds: int = 7 * 24 * 60 * 60


class RedisStreamBatchConsumer:
    def __init__(self, redis_client: RedisClient, settings: StreamConsumerSettings) -> None:
        self.redis = redis_client
        self.settings = settings
        self._stop = asyncio.Event()

    async def setup(self) -> None:
        await self.redis.xgroup_create(
            self.settings.stream,
            self.settings.group,
            start_id="0-0",
            mkstream=True,
        )

    def install_signal_handlers(self) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self.stop)
            except NotImplementedError:
                # Windows event loop may not support this.
                pass

    def stop(self) -> None:
        self._stop.set()

    async def run_forever(self) -> None:
        await self.setup()
        self.install_signal_handlers()
        consecutive_failures = 0
        while not self._stop.is_set():
            try:
                await self._inspect_pending()
                await self._reclaim_stuck_messages()
                await self._consume_once()
                consecutive_failures = 0
            except BusyLoadingError:
                consecutive_failures += 1
                backoff_s = min(5.0, 0.2 * (2 ** min(consecutive_failures, 5)))
                logger.warning(
                    "stream_consumer_redis_loading_retry",
                    stream=self.settings.stream,
                    group=self.settings.group,
                    failures=consecutive_failures,
                    backoff_s=backoff_s,
                )
                await asyncio.sleep(backoff_s)
            except RedisError as exc:
                consecutive_failures += 1
                backoff_s = min(5.0, 0.2 * (2 ** min(consecutive_failures, 5)))
                logger.warning(
                    "stream_consumer_redis_error_retry",
                    stream=self.settings.stream,
                    group=self.settings.group,
                    failures=consecutive_failures,
                    backoff_s=backoff_s,
                    error=str(exc),
                )
                await asyncio.sleep(backoff_s)

    async def _consume_once(self) -> None:
        entries = await self.redis.xreadgroup(
            self.settings.group,
            self.settings.consumer_name,
            {self.settings.stream: ">"},
            count=self.settings.batch_size,
            block=self.settings.block_ms,
        )
        records = self._decode(entries)
        if not records:
            return

        started = asyncio.get_running_loop().time()
        try:
            await self.handle_batch(records)
            await self._ack_batch(records)
            _CONSUMER_BATCH_TOTAL.labels(self.settings.stream, self.settings.group, "ok").inc()
            _CONSUMER_MESSAGE_TOTAL.labels(self.settings.stream, self.settings.group, "ok").inc(len(records))
            await self._checkpoint(records[-1].message_id)
        except Exception as exc:
            _CONSUMER_BATCH_TOTAL.labels(self.settings.stream, self.settings.group, "error").inc()
            _CONSUMER_MESSAGE_TOTAL.labels(self.settings.stream, self.settings.group, "error").inc(len(records))
            await self._handle_failed_batch(records, exc)
        finally:
            _CONSUMER_BATCH_SECONDS.labels(self.settings.stream, self.settings.group).observe(
                asyncio.get_running_loop().time() - started
            )

    async def _inspect_pending(self) -> None:
        pending = await self.redis.xpending(self.settings.stream, self.settings.group)
        if isinstance(pending, dict):
            _CONSUMER_PENDING.labels(self.settings.stream, self.settings.group).set(float(pending.get("pending") or 0))
        elif isinstance(pending, (list, tuple)) and pending:
            _CONSUMER_PENDING.labels(self.settings.stream, self.settings.group).set(float(pending[0]))

    async def _reclaim_stuck_messages(self) -> None:
        claimed = await self.redis.xautoclaim(
            self.settings.stream,
            self.settings.group,
            self.settings.consumer_name,
            self.settings.pending_idle_ms,
            "0-0",
            count=self.settings.claim_batch_size,
        )
        if not claimed or len(claimed) < 2:
            return

        raw_records = claimed[1]
        if not raw_records:
            return

        records = [
            StreamConsumerRecord(
                stream=self.settings.stream,
                message_id=str(mid.decode() if isinstance(mid, bytes) else mid),
                data=self._decode_data(data),
            )
            for mid, data in raw_records
        ]

        logger.warning(
            "stream_consumer_reclaimed_messages",
            stream=self.settings.stream,
            group=self.settings.group,
            consumer=self.settings.consumer_name,
            reclaimed=len(records),
        )

        try:
            await self.handle_batch(records)
            await self._ack_batch(records)
        except Exception as exc:
            await self._handle_failed_batch(records, exc)

    async def _ack_batch(self, records: list[StreamConsumerRecord]) -> None:
        await self.redis.xack(
            self.settings.stream,
            self.settings.group,
            *(record.message_id for record in records),
        )

    async def _checkpoint(self, message_id: str) -> None:
        await self.redis.set_json(
            f"{self.settings.checkpoint_key}:{self.settings.stream}:{self.settings.group}",
            {
                "message_id": message_id,
                "updated_at": datetime.now(tz=UTC).isoformat(),
                "consumer_name": self.settings.consumer_name,
            },
            ttl=self.settings.checkpoint_ttl_seconds,
        )

    async def _handle_failed_batch(self, records: list[StreamConsumerRecord], error: Exception) -> None:
        for record in records:
            retry_count = self._retry_count(record.data) + 1
            payload = dict(record.data)
            payload["retry_count"] = str(retry_count)
            payload["last_error"] = str(error)
            payload["original_stream"] = self.settings.stream
            payload["original_message_id"] = record.message_id

            if retry_count <= self.settings.max_retries:
                await self.redis.xadd(self.settings.retry_stream, {k: str(v) for k, v in payload.items()})
            else:
                await self.redis.xadd(self.settings.poison_stream, {k: str(v) for k, v in payload.items()})

        await self._ack_batch(records)

    def _decode(self, entries: list[Any]) -> list[StreamConsumerRecord]:
        output: list[StreamConsumerRecord] = []
        for stream_name, messages in entries:
            stream = stream_name.decode() if isinstance(stream_name, bytes) else str(stream_name)
            for message_id, data in messages:
                mid = message_id.decode() if isinstance(message_id, bytes) else str(message_id)
                output.append(StreamConsumerRecord(stream=stream, message_id=mid, data=self._decode_data(data)))
        return output

    def _decode_data(self, data: dict[Any, Any]) -> dict[str, Any]:
        return {
            (k.decode() if isinstance(k, bytes) else str(k)):
            (v.decode() if isinstance(v, bytes) else v)
            for k, v in data.items()
        }

    def _retry_count(self, payload: dict[str, Any]) -> int:
        raw = payload.get("retry_count")
        try:
            return int(raw) if raw is not None else 0
        except (ValueError, TypeError):
            return 0

    async def handle_batch(self, records: list[StreamConsumerRecord]) -> None:
        raise NotImplementedError
