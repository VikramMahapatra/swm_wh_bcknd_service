from datetime import UTC, datetime

import pytest

from pydantic import ValidationError

from swm_schemas import (
    EventBatch,
    VendorBatchPayload,
    VendorSinglePayload,
    VendorTelemetryNormalizationEngine,
)


def test_event_batch_parses() -> None:
    payload = {
        "events": [
            {
                "device_id": "truck-001",
                "ts": datetime.now(tz=UTC).isoformat(),
                "lat": 12.34,
                "lon": 56.78,
                "speed_kph": 77.7,
                "heading": 123,
                "ignition": True,
                "attributes": {"driver": "A"},
            }
        ]
    }

    batch = EventBatch.model_validate(payload)

    assert len(batch.events) == 1
    assert batch.events[0].device_id == "truck-001"


def test_vendor_single_payload_supports_aliases_and_nullable_fields() -> None:
    payload = {
        "payload": {
            "deviceId": "truck-002",
            "timestamp": "2026-05-04T10:20:30Z",
            "latitude": 12.34,
            "longitude": 56.78,
            "speed": 55.5,
            "course": 120,
            "ignitionOn": True,
            "accuracyMeters": None,
            "batteryPercent": None,
            "vendorCode": "vendor-a",
            "vehicleNo": "KA01AB1234",
            "metadata": {"route": "north"},
        }
    }

    wrapped = VendorSinglePayload.model_validate(payload)

    assert wrapped.event.device_id == "truck-002"
    assert wrapped.event.ts == datetime(2026, 5, 4, 10, 20, 30, tzinfo=UTC)
    assert wrapped.event.accuracy is None
    assert wrapped.event.battery_percent is None
    assert wrapped.event.registration_no == "KA01AB1234"
    assert wrapped.event.attributes["route"] == "north"


def test_vendor_batch_payload_accepts_batch_alias_and_epoch_timestamps() -> None:
    payload = {
        "items": [
            {
                "device_id": "truck-010",
                "ts": 1_777_888_000,
                "lat": 12.0,
                "lon": 77.0,
                "speed_kph": 0.0,
                "heading": 0,
                "ignition": False,
                "attributes": None,
            }
        ]
    }

    batch = VendorBatchPayload.model_validate(payload)

    assert len(batch.events) == 1
    assert batch.events[0].ts == datetime.fromtimestamp(1_777_888_000, tz=UTC)
    assert batch.events[0].attributes == {}


def test_event_batch_rejects_non_strict_numeric_strings() -> None:
    payload = {
        "events": [
            {
                "device_id": "truck-011",
                "ts": datetime.now(tz=UTC).isoformat(),
                "lat": "12.34",
                "lon": 56.78,
                "speed_kph": 40.5,
                "heading": 180,
                "ignition": True,
            }
        ]
    }

    with pytest.raises(ValidationError):
        EventBatch.model_validate(payload)


def test_vendor_single_payload_rejects_extra_fields() -> None:
    payload = {
        "event": {
            "device_id": "truck-012",
            "ts": "2026-05-04T10:20:30+00:00",
            "lat": 12.34,
            "lon": 56.78,
            "speed_kph": 20.0,
            "heading": 90,
            "ignition": True,
            "unexpected": "x",
        }
    }

    with pytest.raises(ValidationError):
        VendorSinglePayload.model_validate(payload)


def test_normalization_engine_vendor_a_single_payload() -> None:
    engine = VendorTelemetryNormalizationEngine()

    event = engine.normalize_single(
        "vendor_a",
        {
            "imei": "123456789012345",
            "lat": 12.9716,
            "lng": 77.5946,
            "speed": 34.5,
            "heading": 180,
            "acc_status": 1,
            "odometer": 12345.6,
            "fuel_level": 48.2,
            "event_ts": "2026-05-04T10:20:30Z",
            "vendor_field": "kept only in raw",
        },
    )

    assert event.imei == "123456789012345"
    assert event.lng == 77.5946
    assert event.acc_status is True
    assert event.odometer == 12345.6
    assert event.fuel_level == 48.2
    assert event.vendor_id == "vendor_a"
    assert event.payload_raw["vendor_field"] == "kept only in raw"


def test_normalization_engine_vendor_b_batch_payload() -> None:
    engine = VendorTelemetryNormalizationEngine()

    events = engine.normalize_batch(
        "vendor_b",
        {
            "records": [
                {
                    "device": {"imei": "123456789012346"},
                    "telemetry": {
                        "latitude": 13.01,
                        "longitude": 77.61,
                        "speedKph": 0.0,
                        "headingDeg": 90,
                        "ignition": False,
                        "odometerKm": 5000.5,
                        "fuelPct": 61.0,
                    },
                    "eventTime": "2026-05-04T11:00:00+00:00",
                },
                {
                    "device": {"imei": "123456789012347"},
                    "telemetry": {
                        "latitude": 13.02,
                        "longitude": 77.62,
                        "speed": 12.5,
                        "heading": 91,
                    },
                    "timestamp": 1_777_888_000,
                },
            ]
        },
    )

    assert len(events) == 2
    assert events[0].vendor_id == "vendor_b"
    assert events[0].acc_status is False
    assert events[0].odometer == 5000.5
    assert events[1].heading == 91
    assert events[1].event_ts == datetime.fromtimestamp(1_777_888_000, tz=UTC)


def test_normalization_engine_vendor_c_handles_nested_payload_shapes() -> None:
    engine = VendorTelemetryNormalizationEngine()

    events = engine.normalize_batch(
        "vendor_c",
        [
            {
                "data": {
                    "gps": {
                        "imei": "123456789012348",
                        "lat": "12.50",
                        "lon": "77.50",
                    },
                    "can": {
                        "speed": "45.5",
                        "heading": "270",
                        "acc": "0",
                        "odo": "7654.3",
                        "fuel": "39.5",
                    },
                    "ts": "2026-05-04T12:00:00Z",
                }
            }
        ],
    )

    assert len(events) == 1
    assert events[0].imei == "123456789012348"
    assert events[0].lat == 12.5
    assert events[0].lng == 77.5
    assert events[0].speed == 45.5
    assert events[0].heading == 270
    assert events[0].acc_status is False
    assert events[0].odometer == 7654.3
    assert events[0].fuel_level == 39.5


def test_normalization_engine_rejects_unknown_vendor() -> None:
    engine = VendorTelemetryNormalizationEngine()

    with pytest.raises(KeyError):
        engine.normalize_single("unknown_vendor", {"imei": "123456789012345"})
