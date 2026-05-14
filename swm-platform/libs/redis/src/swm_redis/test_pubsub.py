from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from swm_redis.pubsub import (
    BackpressurePolicy,
    PubSubChannel,
    PubSubConfig,
    RedisPubSubPublisher,
    RedisPubSubSubscriber,
)


@pytest.mark.asyncio
async def test_publisher_serializes_and_publishes() -> None:
    mock_client = MagicMock()
    mock_client.publish = AsyncMock(return_value=2)

    publisher = RedisPubSubPublisher(mock_client)
    recipients = await publisher.publish(
        PubSubChannel.LIVE_UPDATES,
        {"imei": "123", "speed": 42.5},
        source="ingestion-api",
        trace_id="trace-1",
        correlation_id="corr-1",
    )

    assert recipients == 2
    mock_client.publish.assert_awaited_once()
    args = mock_client.publish.await_args.args
    assert args[0] == "live_updates"
    assert "trace-1" in args[1]


@pytest.mark.asyncio
async def test_subscriber_deserialize() -> None:
    mock_client = MagicMock()
    subscriber = RedisPubSubSubscriber(mock_client, [PubSubChannel.FLEET_EVENTS])

    raw = {
        "channel": b"fleet_events",
        "data": b'{"ts":"2026-05-04T00:00:00+00:00","trace_id":"t1","correlation_id":"c1","source":"worker","payload":{"imei":"abc"}}',
    }

    envelope = subscriber._deserialize(raw)

    assert envelope.channel == "fleet_events"
    assert envelope.trace_id == "t1"
    assert envelope.correlation_id == "c1"
    assert envelope.payload["imei"] == "abc"


def test_payload_size_bytes_handles_common_inputs() -> None:
    mock_client = MagicMock()
    subscriber = RedisPubSubSubscriber(mock_client, [PubSubChannel.FLEET_EVENTS])

    assert subscriber._payload_size_bytes(b"abc") == 3
    assert subscriber._payload_size_bytes("abc") == 3
    assert subscriber._payload_size_bytes({"a": 1}) > 0


@pytest.mark.asyncio
async def test_backpressure_drop_new() -> None:
    mock_client = MagicMock()
    subscriber = RedisPubSubSubscriber(
        mock_client,
        [PubSubChannel.ALERT_EVENTS],
        config=PubSubConfig(queue_maxsize=1, backpressure_policy=BackpressurePolicy.DROP_NEW),
    )

    e1 = subscriber._deserialize(
        {
            "channel": "alert_events",
            "data": '{"ts":"2026-05-04T00:00:00+00:00","payload":{"id":1}}',
        }
    )
    e2 = subscriber._deserialize(
        {
            "channel": "alert_events",
            "data": '{"ts":"2026-05-04T00:00:00+00:00","payload":{"id":2}}',
        }
    )

    await subscriber._enqueue(e1)
    await subscriber._enqueue(e2)

    kept = await subscriber._queue.get()
    assert kept.payload["id"] == 1


@pytest.mark.asyncio
async def test_backpressure_drop_oldest() -> None:
    mock_client = MagicMock()
    subscriber = RedisPubSubSubscriber(
        mock_client,
        [PubSubChannel.ALERT_EVENTS],
        config=PubSubConfig(queue_maxsize=1, backpressure_policy=BackpressurePolicy.DROP_OLDEST),
    )

    e1 = subscriber._deserialize(
        {
            "channel": "alert_events",
            "data": '{"ts":"2026-05-04T00:00:00+00:00","payload":{"id":1}}',
        }
    )
    e2 = subscriber._deserialize(
        {
            "channel": "alert_events",
            "data": '{"ts":"2026-05-04T00:00:00+00:00","payload":{"id":2}}',
        }
    )

    await subscriber._enqueue(e1)
    await subscriber._enqueue(e2)

    kept = await subscriber._queue.get()
    assert kept.payload["id"] == 2


@pytest.mark.asyncio
async def test_subscriber_worker_dispatches_handler() -> None:
    mock_client = MagicMock()
    subscriber = RedisPubSubSubscriber(
        mock_client,
        [PubSubChannel.DASHBOARD_UPDATES],
        config=PubSubConfig(worker_count=1, queue_maxsize=10),
    )

    processed: list[dict] = []

    async def handler(envelope):
        processed.append(envelope.payload)

    subscriber.register_handler(PubSubChannel.DASHBOARD_UPDATES, handler)

    await subscriber.start()

    msg = subscriber._deserialize(
        {
            "channel": "dashboard_updates",
            "data": '{"ts":"2026-05-04T00:00:00+00:00","payload":{"widgets":5}}',
        }
    )
    await subscriber._enqueue(msg)

    await asyncio.sleep(0.05)
    await subscriber.shutdown()

    assert processed and processed[0]["widgets"] == 5


@pytest.mark.asyncio
async def test_subscriber_reconnect_on_reader_error() -> None:
    pubsub = MagicMock()
    pubsub.subscribe = AsyncMock(side_effect=RuntimeError("boom"))
    pubsub.unsubscribe = AsyncMock(return_value=None)
    pubsub.aclose = AsyncMock(return_value=None)

    mock_client = MagicMock()
    mock_client.client = MagicMock()
    mock_client.client.pubsub = MagicMock(return_value=pubsub)

    subscriber = RedisPubSubSubscriber(
        mock_client,
        [PubSubChannel.LIVE_UPDATES],
        config=PubSubConfig(reconnect_base_seconds=0.01, reconnect_max_seconds=0.02),
    )

    task = asyncio.create_task(subscriber._reader_loop())
    await asyncio.sleep(0.05)
    subscriber._stop.set()
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert pubsub.subscribe.await_count >= 1
