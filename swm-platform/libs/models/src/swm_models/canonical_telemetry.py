from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CanonicalTelemetry(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", validate_assignment=True)

    imei: str = Field(min_length=14, max_length=17, pattern=r"^[0-9]{14,17}$")
    lat: float = Field(ge=-90.0, le=90.0)
    lng: float = Field(ge=-180.0, le=180.0)
    speed: float = Field(ge=0.0, le=320.0)
    heading: int = Field(ge=0, le=359)
    acc_status: int = Field(ge=0, le=1)
    odometer: float | None = Field(default=None, ge=0.0)
    fuel_level: float | None = Field(default=None, ge=0.0, le=100.0)
    vendor_id: str = Field(min_length=1, max_length=64)
    device_id: str = Field(min_length=1, max_length=128)
    vehicle_id: str = Field(min_length=1, max_length=128)
    event_ts: datetime
    received_ts: datetime
    raw_payload: dict[str, Any]

    @field_validator("event_ts", "received_ts", mode="before")
    @classmethod
    def _to_utc(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            ts = value
        elif isinstance(value, (int, float)):
            seconds = float(value)
            if seconds > 10_000_000_000:
                seconds = seconds / 1000.0
            ts = datetime.fromtimestamp(seconds, tz=UTC)
        elif isinstance(value, str):
            raw = value.strip()
            ts = datetime.fromisoformat(raw[:-1] + "+00:00" if raw.endswith("Z") else raw)
        else:
            raise TypeError("timestamp must be datetime, epoch, or ISO string")

        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        return ts.astimezone(UTC)

    @classmethod
    def from_stream_data(cls, payload: dict[str, Any]) -> "CanonicalTelemetry":
        raw_payload = payload.get("raw_payload")
        if isinstance(raw_payload, str):
            # Keep robust for mixed stream encodings
            import orjson

            try:
                raw_payload_obj: dict[str, Any] = orjson.loads(raw_payload)
            except Exception:
                raw_payload_obj = {"_decode_error": raw_payload}
        elif isinstance(raw_payload, dict):
            raw_payload_obj = raw_payload
        else:
            raw_payload_obj = {}

        def _s(key: str, default: str = "") -> str:
            value = payload.get(key, default)
            return str(value) if value is not None else default

        def _f(key: str, default: float = 0.0) -> float:
            value = payload.get(key)
            return float(value) if value not in (None, "") else default

        def _i(key: str, default: int = 0) -> int:
            value = payload.get(key)
            return int(float(value)) if value not in (None, "") else default

        imei = _s("imei")
        device_id = _s("device_id") or imei
        vehicle_id = _s("vehicle_id") or imei

        return cls(
            imei=imei,
            lat=_f("lat"),
            lng=_f("lng"),
            speed=_f("speed"),
            heading=_i("heading"),
            acc_status=_i("acc_status"),
            odometer=_f("odometer") if payload.get("odometer") not in (None, "") else None,
            fuel_level=_f("fuel_level") if payload.get("fuel_level") not in (None, "") else None,
            vendor_id=_s("vendor_id"),
            device_id=device_id,
            vehicle_id=vehicle_id,
            event_ts=payload.get("event_ts") or datetime.now(tz=UTC),
            received_ts=payload.get("received_ts") or datetime.now(tz=UTC),
            raw_payload=raw_payload_obj,
        )

    def to_stream_fields(self) -> dict[str, str]:
        import orjson

        return {
            "imei": self.imei,
            "lat": str(self.lat),
            "lng": str(self.lng),
            "speed": str(self.speed),
            "heading": str(self.heading),
            "acc_status": str(self.acc_status),
            "odometer": "" if self.odometer is None else str(self.odometer),
            "fuel_level": "" if self.fuel_level is None else str(self.fuel_level),
            "vendor_id": self.vendor_id,
            "device_id": self.device_id,
            "vehicle_id": self.vehicle_id,
            "event_ts": self.event_ts.isoformat(),
            "received_ts": self.received_ts.isoformat(),
            "raw_payload": orjson.dumps(self.raw_payload).decode("utf-8"),
        }
