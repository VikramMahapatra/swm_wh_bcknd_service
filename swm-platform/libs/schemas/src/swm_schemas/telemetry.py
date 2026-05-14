from datetime import UTC, datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator, field_validator


class _StrictSchemaModel(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        populate_by_name=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )


class DeviceEvent(_StrictSchemaModel):
    device_id: str = Field(
        min_length=3,
        max_length=64,
        validation_alias=AliasChoices("device_id", "deviceId", "id"),
    )
    ts: datetime = Field(
        validation_alias=AliasChoices("ts", "timestamp", "event_time", "eventTime", "gpsTime"),
    )
    lat: float = Field(
        ge=-90,
        le=90,
        validation_alias=AliasChoices("lat", "latitude"),
    )
    lon: float = Field(
        ge=-180,
        le=180,
        validation_alias=AliasChoices("lon", "lng", "longitude"),
    )
    speed_kph: float = Field(
        ge=0,
        le=320,
        validation_alias=AliasChoices("speed_kph", "speedKph", "speed"),
    )
    heading: int = Field(
        ge=0,
        le=359,
        validation_alias=AliasChoices("heading", "course", "direction"),
    )
    ignition: bool = Field(
        validation_alias=AliasChoices("ignition", "ignition_on", "ignitionOn"),
    )
    accuracy: float | None = Field(
        default=None,
        ge=0,
        le=5000,
        validation_alias=AliasChoices("accuracy", "accuracyMeters", "accuracy_m"),
    )
    battery_percent: float | None = Field(
        default=None,
        ge=0,
        le=100,
        validation_alias=AliasChoices("battery_percent", "batteryPercent", "battery"),
    )
    vendor_code: str | None = Field(
        default=None,
        min_length=2,
        max_length=64,
        validation_alias=AliasChoices("vendor_code", "vendorCode"),
    )
    registration_no: str | None = Field(
        default=None,
        min_length=3,
        max_length=32,
        validation_alias=AliasChoices("registration_no", "registrationNo", "vehicleNo"),
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("attributes", "metadata", "meta"),
    )

    @field_validator("ts", mode="before")
    @classmethod
    def _parse_timestamp(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, (int, float)):
            timestamp = value / 1000 if value > 10_000_000_000 else value
            parsed = datetime.fromtimestamp(timestamp, tz=UTC)
        elif isinstance(value, str):
            raw = value.strip()
            if not raw:
                raise ValueError("timestamp cannot be empty")
            if raw.isdigit():
                epoch = int(raw)
                timestamp = epoch / 1000 if epoch > 10_000_000_000 else epoch
                parsed = datetime.fromtimestamp(timestamp, tz=UTC)
            else:
                normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
                parsed = datetime.fromisoformat(normalized)
        else:
            raise TypeError("timestamp must be datetime, ISO-8601 string, or epoch")

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    @field_validator("attributes", mode="before")
    @classmethod
    def _normalize_attributes(cls, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise TypeError("attributes must be an object")
        return value


class VendorSinglePayload(_StrictSchemaModel):
    event: DeviceEvent

    @model_validator(mode="before")
    @classmethod
    def _wrap_single_event(cls, value: Any) -> Any:
        if isinstance(value, dict):
            for key in ("event", "payload", "data"):
                if key in value:
                    return {"event": value[key]}
            return {"event": value}
        return value


class VendorBatchPayload(_StrictSchemaModel):
    events: list[DeviceEvent] = Field(min_length=1, max_length=1000)

    @model_validator(mode="before")
    @classmethod
    def _wrap_batch_events(cls, value: Any) -> Any:
        if isinstance(value, list):
            return {"events": value}
        if isinstance(value, dict):
            for key in ("events", "items", "records", "batch"):
                if key in value:
                    return {"events": value[key]}
        return value


class EventBatch(VendorBatchPayload):
    pass
