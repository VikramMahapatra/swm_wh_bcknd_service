"""Tests for ingestion_api.webhook_gps."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ingestion_api.webhook_gps import (
    GPS_STREAM,
    TRACE_HEADER,
    GpsFix,
    _alias_item,
    make_gps_webhook_router,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _mock_redis(*, xadd_result: str = "1-0") -> MagicMock:
    r = MagicMock()
    r.xadd = AsyncMock(return_value=xadd_result)
    return r


def _mock_cache(*, last: Any = None) -> MagicMock:
    c = MagicMock()
    c.get_last = AsyncMock(return_value=last)
    return c


def _make_client(
    redis: MagicMock | None = None,
    cache: MagicMock | None = None,
) -> TestClient:
    redis = redis or _mock_redis()
    app = FastAPI()
    app.include_router(make_gps_webhook_router(redis_client=redis, cache=cache or _mock_cache()))
    return TestClient(app)


_MINIMAL_FIX: dict[str, Any] = {
    "imei": "123456789012345",
    "latitude": 28.6139,
    "longitude": 77.2090,
    "timestamp": "2025-01-01T10:00:00Z",
}


# ---------------------------------------------------------------------------
# GpsFix model
# ---------------------------------------------------------------------------

class TestGpsFix:
    def test_valid_minimal_fix(self) -> None:
        fix = GpsFix.model_validate(_MINIMAL_FIX)
        assert fix.imei == "123456789012345"
        assert fix.lat == pytest.approx(28.6139)
        assert fix.lng == pytest.approx(77.2090)

    def test_epoch_ms_timestamp_parsed(self) -> None:
        item = {**_MINIMAL_FIX, "timestamp": 1_735_722_000_000}  # ms
        fix = GpsFix.model_validate(item)
        assert isinstance(fix.ts, datetime)
        assert fix.ts.tzinfo is not None

    def test_epoch_s_timestamp_parsed(self) -> None:
        item = {**_MINIMAL_FIX, "timestamp": 1_735_722_000}  # seconds
        fix = GpsFix.model_validate(item)
        assert isinstance(fix.ts, datetime)

    def test_invalid_imei_rejected(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            GpsFix.model_validate({**_MINIMAL_FIX, "imei": "short"})

    def test_lat_out_of_range_rejected(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            GpsFix.model_validate({**_MINIMAL_FIX, "latitude": 999.0})

    def test_unknown_fields_ignored(self) -> None:
        fix = GpsFix.model_validate({**_MINIMAL_FIX, "mystery_field": "ignored"})
        assert fix.imei == "123456789012345"


# ---------------------------------------------------------------------------
# Alias normalisation
# ---------------------------------------------------------------------------

class TestAliasItem:
    def test_lat_alias_mapped(self) -> None:
        item: dict[str, Any] = {"lat": 28.0, "longitude": 77.0, "timestamp": "2025-01-01T00:00:00Z"}
        _alias_item(item)
        assert "latitude" in item
        assert "lat" not in item

    def test_ts_alias_mapped(self) -> None:
        item: dict[str, Any] = {"latitude": 28.0, "longitude": 77.0, "ts": 1_735_000_000}
        _alias_item(item)
        assert "timestamp" in item
        assert "ts" not in item

    def test_ignition_alias_mapped(self) -> None:
        item: dict[str, Any] = {"latitude": 28.0, "longitude": 77.0, "timestamp": 0, "acc": True}
        _alias_item(item)
        assert "ignition" in item

    def test_existing_canonical_not_overwritten(self) -> None:
        item: dict[str, Any] = {"latitude": 28.0, "lat": 99.0, "longitude": 0.0, "timestamp": 0}
        _alias_item(item)
        # latitude was already present; lat alias should NOT overwrite it
        assert item["latitude"] == 28.0


# ---------------------------------------------------------------------------
# POST /webhook/gps endpoint
# ---------------------------------------------------------------------------

class TestWebhookGpsEndpoint:
    def test_single_event_accepted(self) -> None:
        redis = _mock_redis()
        client = _make_client(redis=redis)
        resp = client.post("/webhook/gps", json=[_MINIMAL_FIX])
        assert resp.status_code == 202
        body = resp.json()
        assert body["accepted"] == 1
        assert body["published"] == 1
        assert body["rejected"] == 0
        assert body["stream"] == GPS_STREAM
        assert "error_summary" in body
        redis.xadd.assert_awaited_once()

    def test_batch_events_accepted(self) -> None:
        fixes = [
            {**_MINIMAL_FIX, "imei": "12345678901234" + str(i)}
            for i in range(5)
        ]
        redis = _mock_redis()
        client = _make_client(redis=redis)
        resp = client.post("/webhook/gps", json=fixes)
        assert resp.status_code == 202
        assert resp.json()["accepted"] == 5
        assert resp.json()["published"] == 5
        assert redis.xadd.call_count == 5

    def test_invalid_item_counted_as_rejected(self) -> None:
        payload = [
            _MINIMAL_FIX,
            {"imei": "BAD", "latitude": 0, "longitude": 0, "timestamp": 0},
        ]
        client = _make_client()
        resp = client.post("/webhook/gps", json=payload)
        assert resp.status_code == 202
        assert resp.json()["accepted"] == 1
        assert resp.json()["published"] == 1
        assert resp.json()["rejected"] == 1
        assert resp.json()["error_summary"]["validation"]["failed"] == 1

    def test_all_invalid_returns_202_with_summary(self) -> None:
        payload = [{"garbage": True}]
        client = _make_client()
        resp = client.post("/webhook/gps", json=payload)
        assert resp.status_code == 202
        assert resp.json()["accepted"] == 0
        assert resp.json()["published"] == 0
        assert resp.json()["rejected"] == 1
        assert resp.json()["error_summary"]["validation"]["failed"] == 1

    def test_non_array_body_returns_422(self) -> None:
        client = _make_client()
        resp = client.post("/webhook/gps", json={"single": "object"})
        assert resp.status_code == 422

    def test_device_enrichment_applied(self) -> None:
        """device_id and vehicle_id from cache are written into the stream entry."""
        from swm_redis.realtime_cache import TruckLast
        from datetime import UTC, datetime

        cached_last = TruckLast(
            imei="123456789012345",
            device_id="dev-abc",
            ts=datetime.now(UTC),
            lat=28.6,
            lon=77.2,
            speed_kph=0.0,
            heading=0,
            ignition=False,
            attributes={"vehicle_id": "veh-xyz"},
        )
        cache = _mock_cache(last=cached_last)
        redis = _mock_redis()
        client = _make_client(redis=redis, cache=cache)
        resp = client.post("/webhook/gps", json=[_MINIMAL_FIX])
        assert resp.status_code == 202
        # Verify the stream entry carried device_id
        call_kwargs = redis.xadd.call_args
        stream_fields: dict[str, str] = call_kwargs.args[1]
        assert stream_fields["device_id"] == "dev-abc"
        assert stream_fields["vehicle_id"] == "veh-xyz"

    def test_cache_miss_tolerated(self) -> None:
        """Cache miss (None) should not crash — device_id written as empty string."""
        redis = _mock_redis()
        client = _make_client(redis=redis, cache=_mock_cache(last=None))
        resp = client.post("/webhook/gps", json=[_MINIMAL_FIX])
        assert resp.status_code == 202
        stream_fields: dict[str, str] = redis.xadd.call_args.args[1]
        assert stream_fields["device_id"] == ""

    def test_vendor_id_header_propagated(self) -> None:
        redis = _mock_redis()
        client = _make_client(redis=redis)
        resp = client.post("/webhook/gps", json=[_MINIMAL_FIX], headers={"X-Vendor-Id": "ACME"})
        assert resp.status_code == 202
        stream_fields: dict[str, str] = redis.xadd.call_args.args[1]
        assert stream_fields["vendor_id"] == "ACME"

    def test_partial_publish_failure_reported(self) -> None:
        redis = MagicMock()
        redis.xadd = AsyncMock(side_effect=["1-0", RuntimeError("redis timeout"), "2-0"])
        client = _make_client(redis=redis)
        payload = [
            _MINIMAL_FIX,
            {**_MINIMAL_FIX, "imei": "123456789012346"},
        ]
        resp = client.post("/webhook/gps", json=payload)
        assert resp.status_code == 202
        body = resp.json()
        assert body["accepted"] == 2
        assert body["published"] == 1
        assert body["rejected"] == 1
        assert body["error_summary"]["publish"]["failed"] == 1
        assert len(body["error_summary"]["publish"]["samples"]) == 1
        streams = [call.args[0] for call in redis.xadd.call_args_list]
        assert all(stream == GPS_STREAM for stream in streams)

    def test_latency_field_in_response(self) -> None:
        client = _make_client()
        resp = client.post("/webhook/gps", json=[_MINIMAL_FIX])
        assert resp.status_code == 202
        assert "latency_ms" in resp.json()
        assert resp.json()["latency_ms"] >= 0
        assert "error_summary" in resp.json()

    def test_request_id_propagated(self) -> None:
        client = _make_client()
        resp = client.post(
            "/webhook/gps",
            json=[_MINIMAL_FIX],
            headers={"X-Request-Id": "test-req-999"},
        )
        assert resp.status_code == 202
        assert resp.json()["request_id"] == "test-req-999"

    def test_trace_header_propagated_to_response_and_stream(self) -> None:
        redis = _mock_redis()
        client = _make_client(redis=redis)
        resp = client.post(
            "/webhook/gps",
            json=[_MINIMAL_FIX],
            headers={TRACE_HEADER: "trace-abc-123"},
        )
        assert resp.status_code == 202
        assert resp.headers[TRACE_HEADER] == "trace-abc-123"
        stream_fields: dict[str, str] = redis.xadd.call_args.args[1]
        assert stream_fields["trace_id"] == "trace-abc-123"
