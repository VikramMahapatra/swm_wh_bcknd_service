"""Lightweight Redis list queue service.

Queues:
- email queue
- sms queue
- push queue
- inapp queue

Processing pattern:
- Enqueue with LPUSH
- Consume with BRPOP worker
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

import orjson
from prometheus_client import Counter, Gauge, Histogram

from swm_common import get_logger
from swm_redis.client import RedisClient

logger = get_logger("swm_redis.list_queue")


class QueueName(StrEnum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    INAPP = "inapp"


@dataclass(slots=True)
class ListQueueConfig:
    key_prefix: str = "queue"


@dataclass(slots=True)
class QueueMessage:
    queue: QueueName
    message_id: str
    enqueued_at: datetime
    payload: dict[str, Any]


@dataclass(slots=True)
class ListQueueWorkerConfig:
    worker_count: int = 1
    brpop_timeout_seconds: int = 1


_QUEUE_ENQUEUED_TOTAL = Counter(
    "swm_redis_list_queue_enqueued_total",
    "Total messages enqueued to Redis list queues",
    ["queue"],
)
_QUEUE_DEQUEUED_TOTAL = Counter(
    "swm_redis_list_queue_dequeued_total",
    "Total messages dequeued from Redis list queues",
    ["queue"],
)
_QUEUE_HANDLER_TOTAL = Counter(
    "swm_redis_list_queue_handler_total",
    "Total list queue handler outcomes",
    ["queue", "status"],
)
_QUEUE_DEPTH = Gauge(
    "swm_redis_list_queue_depth",
    "Current queue depth by list",
    ["queue"],
)
_QUEUE_HANDLER_DURATION = Histogram(
    "swm_redis_list_queue_handler_duration_seconds",
    "Handler duration for list queue workers",
    ["queue"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
)


class RedisListQueueService:
    """Typed lightweight queue API over Redis lists."""

    def __init__(self, redis_client: RedisClient, *, config: ListQueueConfig | None = None) -> None:
        self.redis = redis_client
        self.config = config or ListQueueConfig()

    def queue_key(self, queue: QueueName) -> str:
        return f"{self.config.key_prefix}:{queue.value}"

    async def enqueue(self, queue: QueueName, payload: dict[str, Any]) -> str:
        message = {
            "message_id": uuid4().hex,
            "queue": queue.value,
            "enqueued_at": datetime.now(UTC).isoformat(),
            "payload": payload,
        }
        raw = orjson.dumps(message).decode("utf-8")
        await self.redis.lpush(self.queue_key(queue), raw)
        _QUEUE_ENQUEUED_TOTAL.labels(queue=queue.value).inc()
        await self._refresh_depth(queue)
        return message["message_id"]

    async def dequeue(self, queues: list[QueueName], *, timeout_seconds: int = 1) -> QueueMessage | None:
        keys = [self.queue_key(queue) for queue in queues]
        popped = await self.redis.brpop(keys, timeout=timeout_seconds)
        if popped is None:
            return None

        key, raw = popped
        queue_name = key.split(":")[-1]
        payload = orjson.loads(raw)
        queue = QueueName(queue_name)

        _QUEUE_DEQUEUED_TOTAL.labels(queue=queue.value).inc()
        await self._refresh_depth(queue)

        return QueueMessage(
            queue=queue,
            message_id=str(payload["message_id"]),
            enqueued_at=datetime.fromisoformat(str(payload["enqueued_at"])),
            payload=dict(payload.get("payload") or {}),
        )

    async def depth(self, queue: QueueName) -> int:
        return await self.redis.llen(self.queue_key(queue))

    async def _refresh_depth(self, queue: QueueName) -> None:
        try:
            _QUEUE_DEPTH.labels(queue=queue.value).set(await self.depth(queue))
        except Exception as exc:
            logger.debug("queue_depth_refresh_failed", queue=queue.value, error=str(exc))


class RedisListQueueWorker:
    """BRPOP worker loop for one or more Redis list queues."""

    def __init__(
        self,
        service: RedisListQueueService,
        queues: list[QueueName],
        *,
        config: ListQueueWorkerConfig | None = None,
    ) -> None:
        self.service = service
        self.queues = queues
        self.config = config or ListQueueWorkerConfig()
        self._handlers: dict[QueueName, Any] = {}
        self._default_handler: Any = None
        self._stop = asyncio.Event()
        self._tasks: list[asyncio.Task[None]] = []

    def register_handler(self, queue: QueueName, handler: Any) -> None:
        self._handlers[queue] = handler

    def register_default_handler(self, handler: Any) -> None:
        self._default_handler = handler

    async def start(self) -> None:
        if self._tasks:
            return
        self._stop.clear()
        for worker_idx in range(self.config.worker_count):
            task = asyncio.create_task(self._loop(worker_idx), name=f"list-queue-worker-{worker_idx}")
            self._tasks.append(task)

    async def shutdown(self) -> None:
        self._stop.set()
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def _loop(self, worker_idx: int) -> None:
        logger.debug("list_queue_worker_started", worker_idx=worker_idx)
        while not self._stop.is_set():
            try:
                message = await self.service.dequeue(
                    self.queues,
                    timeout_seconds=self.config.brpop_timeout_seconds,
                )
                if message is None:
                    continue

                handler = self._handlers.get(message.queue, self._default_handler)
                started = asyncio.get_running_loop().time()
                if handler is not None:
                    await handler(message)
                _QUEUE_HANDLER_TOTAL.labels(queue=message.queue.value, status="ok").inc()
                _QUEUE_HANDLER_DURATION.labels(queue=message.queue.value).observe(
                    asyncio.get_running_loop().time() - started
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                queue_name = message.queue.value if "message" in locals() and message is not None else "unknown"
                _QUEUE_HANDLER_TOTAL.labels(queue=queue_name, status="error").inc()
                logger.error("list_queue_worker_error", worker_idx=worker_idx, queue=queue_name, error=str(exc))
