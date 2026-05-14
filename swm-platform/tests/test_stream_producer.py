from datetime import UTC, datetime

from swm_models import CanonicalTelemetry
from swm_redis.stream_producer import TelemetryStreamProducer


class _FakeRedisClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str], int | None, bool]] = []

    async def xadd(
        self,
        stream: str,
        fields: dict[str, str],
        *,
        maxlen: int | None = None,
        approximate: bool = True,
    ) -> str:
        self.calls.append((stream, fields, maxlen, approximate))
        return "1-0"


def _event() -> CanonicalTelemetry:
    return CanonicalTelemetry(
        imei="990000000000001",
        lat=18.54,
        lng=73.93,
        speed=10,
        heading=200,
        acc_status=1,
        odometer=2.3,
        fuel_level=None,
        vendor_id="vendor_a",
        device_id="device_1",
        vehicle_id="vehicle_1",
        event_ts=datetime.now(tz=UTC),
        received_ts=datetime.now(tz=UTC),
        raw_payload={"sample": True},
    )


async def test_stream_producer_publish() -> None:
    fake = _FakeRedisClient()
    producer = TelemetryStreamProducer(fake, stream_name="gps.telemetry.raw")

    message_id = await producer.publish(_event())

    assert message_id == "1-0"
    assert len(fake.calls) == 1
    assert fake.calls[0][0] == "gps.telemetry.raw"
