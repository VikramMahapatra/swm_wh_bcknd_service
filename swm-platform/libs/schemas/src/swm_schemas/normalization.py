from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _StrictNormalizationModel(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )


class CanonicalTelemetryEvent(_StrictNormalizationModel):
    imei: str = Field(min_length=14, max_length=17, pattern=r"^[0-9]{14,17}$")
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    speed: float = Field(ge=0, le=320)
    heading: int = Field(ge=0, le=359)
    acc_status: bool | None = None
    odometer: float | None = Field(default=None, ge=0)
    fuel_level: float | None = Field(default=None, ge=0, le=100)
    event_ts: datetime
    payload_raw: dict[str, Any]
    vendor_id: str = Field(min_length=1, max_length=64)

    @field_validator("event_ts", mode="before")
    @classmethod
    def _normalize_event_ts(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, (int, float)):
            seconds = value / 1000 if value > 10_000_000_000 else value
            parsed = datetime.fromtimestamp(seconds, tz=UTC)
        elif isinstance(value, str):
            raw = value.strip()
            if not raw:
                raise ValueError("event_ts cannot be empty")
            if raw.isdigit():
                epoch = int(raw)
                seconds = epoch / 1000 if epoch > 10_000_000_000 else epoch
                parsed = datetime.fromtimestamp(seconds, tz=UTC)
            else:
                parsed = datetime.fromisoformat(raw[:-1] + "+00:00" if raw.endswith("Z") else raw)
        else:
            raise TypeError("event_ts must be datetime, epoch, or ISO-8601 string")

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)


class VendorTelemetryAdapter:
    vendor_id: str

    def __init__(self, vendor_id: str) -> None:
        self.vendor_id = vendor_id.strip().lower()

    def normalize_single(self, payload: dict[str, Any]) -> CanonicalTelemetryEvent:
        raise NotImplementedError

    def normalize_batch(self, payload: Any) -> list[CanonicalTelemetryEvent]:
        return [self.normalize_single(item) for item in self._extract_batch(payload)]

    def _extract_batch(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [self._ensure_mapping(item) for item in payload]
        if isinstance(payload, dict):
            for key in ("events", "items", "records", "batch", "data"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [self._ensure_mapping(item) for item in value]
        raise ValueError(f"{self.vendor_id} batch payload must contain a list of records")

    def _build_event(
        self,
        *,
        payload_raw: dict[str, Any],
        imei: Any,
        lat: Any,
        lng: Any,
        speed: Any,
        heading: Any,
        event_ts: Any,
        acc_status: Any = None,
        odometer: Any = None,
        fuel_level: Any = None,
    ) -> CanonicalTelemetryEvent:
        return CanonicalTelemetryEvent(
            imei=self._parse_imei(imei),
            lat=self._parse_float(lat, field_name="lat"),
            lng=self._parse_float(lng, field_name="lng"),
            speed=self._parse_float(speed, field_name="speed"),
            heading=self._parse_heading(heading),
            acc_status=self._parse_bool(acc_status) if acc_status is not None else None,
            odometer=self._parse_float(odometer, field_name="odometer") if odometer is not None else None,
            fuel_level=self._parse_float(fuel_level, field_name="fuel_level") if fuel_level is not None else None,
            event_ts=event_ts,
            payload_raw=deepcopy(payload_raw),
            vendor_id=self.vendor_id,
        )

    def _ensure_mapping(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise TypeError(f"{self.vendor_id} payload must be an object")
        return payload

    def _require_path(self, payload: dict[str, Any], *paths: str) -> Any:
        for path in paths:
            value = self._get_path(payload, path)
            if value is not None:
                return value
        raise ValueError(f"missing required field for {self.vendor_id}: {' | '.join(paths)}")

    def _optional_path(self, payload: dict[str, Any], *paths: str) -> Any:
        for path in paths:
            value = self._get_path(payload, path)
            if value is not None:
                return value
        return None

    def _get_path(self, payload: dict[str, Any], path: str) -> Any:
        current: Any = payload
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    def _parse_imei(self, value: Any) -> str:
        if not isinstance(value, str):
            raise TypeError("imei must be a string")
        imei = value.strip()
        if not imei.isdigit() or not 14 <= len(imei) <= 17:
            raise ValueError("imei must contain 14 to 17 digits")
        return imei

    def _parse_float(self, value: Any, *, field_name: str) -> float:
        if isinstance(value, bool):
            raise TypeError(f"{field_name} must be numeric")
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                raise ValueError(f"{field_name} cannot be empty")
            return float(raw)
        raise TypeError(f"{field_name} must be numeric")

    def _parse_heading(self, value: Any) -> int:
        if isinstance(value, bool):
            raise TypeError("heading must be numeric")
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                raise ValueError("heading cannot be empty")
            return int(float(raw))
        raise TypeError("heading must be numeric")

    def _parse_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value in (0, 1):
                return bool(value)
            raise ValueError("boolean integer values must be 0 or 1")
        if isinstance(value, str):
            raw = value.strip().lower()
            if raw in {"1", "true", "t", "yes", "y", "on"}:
                return True
            if raw in {"0", "false", "f", "no", "n", "off"}:
                return False
        raise TypeError("acc_status must be boolean-like")


class VendorAAdapter(VendorTelemetryAdapter):
    def __init__(self) -> None:
        super().__init__("vendor_a")

    def normalize_single(self, payload: dict[str, Any]) -> CanonicalTelemetryEvent:
        record = self._ensure_mapping(payload.get("event") if isinstance(payload.get("event"), dict) else payload)
        return self._build_event(
            payload_raw=record,
            imei=self._require_path(record, "imei"),
            lat=self._require_path(record, "lat", "latitude"),
            lng=self._require_path(record, "lng", "longitude"),
            speed=self._require_path(record, "speed", "speed_kph"),
            heading=self._require_path(record, "heading"),
            acc_status=self._optional_path(record, "acc_status", "ignition"),
            odometer=self._optional_path(record, "odometer"),
            fuel_level=self._optional_path(record, "fuel_level"),
            event_ts=self._require_path(record, "event_ts", "timestamp", "ts"),
        )


class VendorBAdapter(VendorTelemetryAdapter):
    def __init__(self) -> None:
        super().__init__("vendor_b")

    def normalize_single(self, payload: dict[str, Any]) -> CanonicalTelemetryEvent:
        record = self._ensure_mapping(payload)
        return self._build_event(
            payload_raw=record,
            imei=self._require_path(record, "device.imei", "device.id"),
            lat=self._require_path(record, "telemetry.latitude"),
            lng=self._require_path(record, "telemetry.longitude"),
            speed=self._require_path(record, "telemetry.speedKph", "telemetry.speed"),
            heading=self._require_path(record, "telemetry.headingDeg", "telemetry.heading"),
            acc_status=self._optional_path(record, "telemetry.ignition", "telemetry.accStatus"),
            odometer=self._optional_path(record, "telemetry.odometerKm", "telemetry.odometer"),
            fuel_level=self._optional_path(record, "telemetry.fuelPct", "telemetry.fuelLevel"),
            event_ts=self._require_path(record, "eventTime", "timestamp"),
        )


class VendorCAdapter(VendorTelemetryAdapter):
    def __init__(self) -> None:
        super().__init__("vendor_c")

    def normalize_single(self, payload: dict[str, Any]) -> CanonicalTelemetryEvent:
        record = self._ensure_mapping(payload)
        nested = self._ensure_mapping(record.get("data") if isinstance(record.get("data"), dict) else record)
        return self._build_event(
            payload_raw=record,
            imei=self._require_path(nested, "gps.imei"),
            lat=self._require_path(nested, "gps.lat", "gps.latitude"),
            lng=self._require_path(nested, "gps.lon", "gps.lng", "gps.longitude"),
            speed=self._require_path(nested, "can.speed", "gps.speed"),
            heading=self._require_path(nested, "can.heading", "gps.heading"),
            acc_status=self._optional_path(nested, "can.acc", "can.ignition"),
            odometer=self._optional_path(nested, "can.odo", "can.odometer"),
            fuel_level=self._optional_path(nested, "can.fuel", "can.fuelLevel"),
            event_ts=self._require_path(nested, "ts", "timestamp"),
        )


class VendorTelemetryNormalizationEngine:
    def __init__(self, adapters: list[VendorTelemetryAdapter] | None = None) -> None:
        self._adapters: dict[str, VendorTelemetryAdapter] = {}
        for adapter in adapters or default_vendor_telemetry_adapters():
            self.register_adapter(adapter)

    def register_adapter(self, adapter: VendorTelemetryAdapter) -> None:
        self._adapters[adapter.vendor_id] = adapter

    def normalize_single(self, vendor_id: str, payload: dict[str, Any]) -> CanonicalTelemetryEvent:
        return self._get_adapter(vendor_id).normalize_single(payload)

    def normalize_batch(self, vendor_id: str, payload: Any) -> list[CanonicalTelemetryEvent]:
        return self._get_adapter(vendor_id).normalize_batch(payload)

    def _get_adapter(self, vendor_id: str) -> VendorTelemetryAdapter:
        key = vendor_id.strip().lower()
        adapter = self._adapters.get(key)
        if adapter is None:
            raise KeyError(f"no telemetry adapter registered for vendor_id={vendor_id}")
        return adapter



def default_vendor_telemetry_adapters() -> list[VendorTelemetryAdapter]:
    return [VendorAAdapter(), VendorBAdapter(), VendorCAdapter()]
