from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from swm_redis.list_queue import (
    ListQueueWorkerConfig,
    QueueName,
    RedisListQueueService,
    RedisListQueueWorker,
)


@pytest.mark.asyncio
async def test_enqueue_uses_lpush() -> None:
    mock_client = MagicMock()
    mock_client.lpush = AsyncMock(return_value=1)
    mock_client.llen = AsyncMock(return_value=1)

    service = RedisListQueueService(mock_client)
    message_id = await service.enqueue(QueueName.EMAIL, {"to": "a@b.com", "subject": "hello"})

    assert message_id
    mock_client.lpush.assert_awaited_once()
    args = mock_client.lpush.await_args.args
    assert args[0] == "queue:email"
    assert "subject" in args[1]


@pytest.mark.asyncio
async def test_dequeue_uses_brpop() -> None:
    mock_client = MagicMock()
    mock_client.brpop = AsyncMock(
        return_value=(
            "queue:sms",
            '{"message_id":"m-1","queue":"sms","enqueued_at":"2026-05-04T00:00:00+00:00","payload":{"to":"999","text":"otp"}}',
        )
    )
    mock_client.llen = AsyncMock(return_value=0)

    service = RedisListQueueService(mock_client)
    message = await service.dequeue([QueueName.SMS], timeout_seconds=1)

    assert message is not None
    assert message.queue == QueueName.SMS
    assert message.message_id == "m-1"
    assert message.payload["text"] == "otp"
    mock_client.brpop.assert_awaited_once()


@pytest.mark.asyncio
async def test_worker_brpop_dispatches_handlers() -> None:
    mock_client = MagicMock()
    service = RedisListQueueService(mock_client)

    processed: list[tuple[str, dict]] = []

    async def email_handler(msg):
        processed.append((msg.queue.value, msg.payload))

    worker = RedisListQueueWorker(
        service,
        [QueueName.EMAIL, QueueName.SMS, QueueName.PUSH, QueueName.INAPP],
        config=ListQueueWorkerConfig(worker_count=1, brpop_timeout_seconds=1),
    )
    worker.register_handler(QueueName.EMAIL, email_handler)

    message = type(
        "_M",
        (),
        {
            "queue": QueueName.EMAIL,
            "message_id": "1",
            "payload": {"to": "x@y.com"},
        },
    )()
    service.dequeue = AsyncMock(side_effect=[message, None, None, None])  # type: ignore[assignment]

    await worker.start()
    await asyncio.sleep(0.05)
    await worker.shutdown()

    assert processed
    assert processed[0][0] == "email"


@pytest.mark.asyncio
async def test_worker_default_handler() -> None:
    mock_client = MagicMock()
    service = RedisListQueueService(mock_client)

    processed: list[str] = []

    async def default_handler(msg):
        processed.append(msg.queue.value)

    worker = RedisListQueueWorker(service, [QueueName.PUSH])
    worker.register_default_handler(default_handler)

    message = type("_M", (), {"queue": QueueName.PUSH, "message_id": "1", "payload": {}})()
    service.dequeue = AsyncMock(side_effect=[message, None, None])  # type: ignore[assignment]

    await worker.start()
    await asyncio.sleep(0.05)
    await worker.shutdown()

    assert processed == ["push"]
