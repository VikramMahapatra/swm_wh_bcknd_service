from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable

from swm_models import CanonicalTelemetry
from swm_redis.client import RedisClient


class TelemetryStreamProducer:
    def __init__(
        self,
        redis_client: RedisClient,
        *,
        stream_name: str = "gps.telemetry.raw",
        maxlen: int = 100_000,
        approximate: bool = True,
    ) -> None:
        self.redis = redis_client
        self.stream_name = stream_name
        self.maxlen = maxlen
        self.approximate = approximate

    async def publish(self, event: CanonicalTelemetry) -> str:
        payload = event.to_stream_fields()
        payload.setdefault("received_ts", datetime.now(tz=UTC).isoformat())
        return await self.redis.xadd(
            self.stream_name,
            payload,
            maxlen=self.maxlen,
            approximate=self.approximate,
        )

    async def publish_batch(self, events: Iterable[CanonicalTelemetry]) -> list[str]:
        ids: list[str] = []
        for event in events:
            ids.append(await self.publish(event))
        return ids
