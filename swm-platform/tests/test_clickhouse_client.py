from datetime import UTC, datetime

from swm_clickhouse import ClickHouseRawTelemetryClient
from swm_models import CanonicalTelemetry


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


async def test_clickhouse_fallback_writes_parquet(tmp_path) -> None:  # type: ignore[no-untyped-def]
    client = ClickHouseRawTelemetryClient(
        host="localhost",
        port=8123,
        database="default",
        username="default",
        password="",
        fallback_dir=str(tmp_path),
    )

    path = await client.write_parquet_fallback([_event()], reason="test")

    assert path.exists()
    assert path.suffix == ".parquet"
