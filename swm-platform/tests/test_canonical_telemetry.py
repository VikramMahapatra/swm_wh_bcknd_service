from datetime import UTC, datetime

from swm_models import CanonicalTelemetry


def test_canonical_telemetry_from_stream_data() -> None:
    event = CanonicalTelemetry.from_stream_data(
        {
            "imei": "990000000000001",
            "lat": "18.54",
            "lng": "73.93",
            "speed": "10",
            "heading": "213",
            "acc_status": "1",
            "odometer": "371.13",
            "fuel_level": "",
            "vendor_id": "vendor_a",
            "device_id": "device_1",
            "vehicle_id": "vehicle_1",
            "event_ts": "2026-05-05T00:00:00Z",
            "received_ts": datetime.now(tz=UTC).isoformat(),
            "raw_payload": "{}",
        }
    )

    assert event.imei == "990000000000001"
    assert event.acc_status == 1
    assert event.odometer == 371.13
    assert event.fuel_level is None


def test_canonical_telemetry_to_stream_fields() -> None:
    event = CanonicalTelemetry(
        imei="990000000000002",
        lat=18.54,
        lng=73.93,
        speed=10,
        heading=200,
        acc_status=1,
        odometer=1.2,
        fuel_level=None,
        vendor_id="vendor_b",
        device_id="device_2",
        vehicle_id="vehicle_2",
        event_ts=datetime.now(tz=UTC),
        received_ts=datetime.now(tz=UTC),
        raw_payload={"x": 1},
    )

    fields = event.to_stream_fields()
    assert fields["imei"] == "990000000000002"
    assert fields["acc_status"] == "1"
    assert fields["fuel_level"] == ""
