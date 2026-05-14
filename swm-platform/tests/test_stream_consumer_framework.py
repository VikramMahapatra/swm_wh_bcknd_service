from __future__ import annotations

from typing import Any

from swm_redis.stream_consumer import (
    RedisStreamBatchConsumer,
    StreamConsumerRecord,
    StreamConsumerSettings,
)


class _FakeRedisClient:
    def __init__(self) -> None:
        self.created_groups: list[tuple[str, str]] = []
        self.acks: list[tuple[str, str, tuple[str, ...]]] = []
        self.published_retry: list[dict[str, str]] = []
        self.published_poison: list[dict[str, str]] = []
        self.checkpoints: list[dict[str, Any]] = []

    async def xgroup_create(self, stream: str, group: str, *, start_id: str, mkstream: bool) -> None:
        self.created_groups.append((stream, group))

    async def xpending(self, stream: str, group: str) -> dict[str, int]:
        return {"pending": 0}

    async def xautoclaim(
        self,
        stream: str,
        group: str,
        consumer: str,
        min_idle_time: int,
        start_id: str,
        *,
        count: int | None = None,
    ) -> list[Any]:
        return []

    async def xreadgroup(
        self,
        group: str,
        consumer: str,
        streams: dict[str, str],
        *,
        count: int | None = None,
        block: int | None = None,
        no_ack: bool = False,
    ) -> list[Any]:
        return []

    async def xack(self, stream: str, group: str, *entry_ids: str) -> int:
        self.acks.append((stream, group, entry_ids))
        return len(entry_ids)

    async def set_json(self, key: str, payload: dict[str, Any], *, ttl: int) -> None:
        self.checkpoints.append({"key": key, "payload": payload, "ttl": ttl})

    async def xadd(
        self,
        stream: str,
        fields: dict[str, str],
        *,
        entry_id: str = "*",
        maxlen: int | None = None,
        approximate: bool = True,
        timeout: float | None | object = None,
    ) -> str:
        if stream.endswith(".retry"):
            self.published_retry.append(fields)
        if stream.endswith(".poison"):
            self.published_poison.append(fields)
        return "1-0"


class _DemoConsumer(RedisStreamBatchConsumer):
    def __init__(self, redis_client: _FakeRedisClient, fail: bool = False) -> None:
        super().__init__(
            redis_client,
            StreamConsumerSettings(
                stream="gps.telemetry.raw",
                group="storage",
                consumer_name="storage-1",
                retry_stream="gps.telemetry.raw.storage.retry",
                poison_stream="gps.telemetry.raw.storage.poison",
            ),
        )
        self.fail = fail

    async def handle_batch(self, records: list[StreamConsumerRecord]) -> None:
        if self.fail:
            raise RuntimeError("batch failed")


async def test_consumer_setup_creates_group() -> None:
    fake = _FakeRedisClient()
    consumer = _DemoConsumer(fake)

    await consumer.setup()

    assert fake.created_groups == [("gps.telemetry.raw", "storage")]


async def test_consumer_failed_batch_goes_to_retry() -> None:
    fake = _FakeRedisClient()
    consumer = _DemoConsumer(fake, fail=True)

    records = [StreamConsumerRecord(stream="gps.telemetry.raw", message_id="1-0", data={"imei": "x"})]
    await consumer._handle_failed_batch(records, RuntimeError("boom"))

    assert len(fake.published_retry) == 1
    assert len(fake.acks) == 1
