
from __future__ import annotations

import ipaddress
import re
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Column,
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from swm_db.base import AuditBase, Base

"""
Application ORM models.

All models should inherit from :class:`~swm_db.base.AuditBase` which provides:
- UUID primary key
- created_at / updated_at timestamps
- deleted_at soft-delete
- created_by / updated_by audit columns
"""

class ZoneORM(Base):
    __tablename__ = "zones"
    __table_args__ = (
        Index("ix_zones_code", "zone_code", unique=True),
        Index("ix_zones_active", "active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    zone_code: Mapped[str] = mapped_column(String(24), nullable=False, unique=True)
    zone_name: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    wards: Mapped[list["WardORM"]] = relationship("WardORM", back_populates="zone")

    @validates("zone_code")
    def validate_zone_code(self, _: str, value: str) -> str:
        normalized = value.strip().upper()
        if not _WARD_CODE_RE.fullmatch(normalized):
            raise ValueError("zone_code must match ^[A-Z0-9_-]{2,24}$")
        return normalized


class DeviceEventORM(Base):
    __tablename__ = "device_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    device_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    speed_kph: Mapped[float] = mapped_column(Float, nullable=False)
    heading: Mapped[int] = mapped_column(nullable=False)
    ignition: Mapped[bool] = mapped_column(Boolean, nullable=False)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


_VENDOR_CODE_RE = re.compile(r"^[A-Z0-9_-]{3,32}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_AUTH_TYPES = {"header", "signature", "ip"}
_IMEI_RE = re.compile(r"^[0-9]{14,17}$")
_HEALTH_STATUSES = {"healthy", "warning", "critical", "offline"}
_VEHICLE_NO_RE = re.compile(r"^[A-Z0-9-]{4,24}$")
_REG_NO_RE = re.compile(r"^[A-Z0-9-]{4,24}$")
_FUEL_TYPES = {"diesel", "petrol", "cng", "electric", "lng"}
_VEHICLE_STATUSES = {"operational", "maintenance", "breakdown", "retired"}
_WARD_CODE_RE = re.compile(r"^[A-Z0-9_-]{2,24}$")
_ROUTE_CODE_RE = re.compile(r"^[A-Z0-9_-]{2,24}$")
_GEOFENCE_CODE_RE = re.compile(r"^[A-Z0-9_-]{2,32}$")
_GEOFENCE_TYPES = {"depot", "landfill", "zone", "parking", "maintenance"}
_GEOMETRY_TYPES = {"circle", "polygon"}
_GEOFENCE_FOR_TYPES = {"zone", "ward", "route"}
_ALERT_STATUSES = {"open", "acknowledged", "resolved", "escalated"}
_ALERT_SEVERITIES = {"low", "medium", "high", "critical"}
_ALERT_ACTIONS = {"created", "acknowledged", "resolved", "escalated", "updated", "commented"}
_TICKET_STATUSES = {"open", "in_progress", "pending", "resolved", "closed"}
_TICKET_PRIORITIES = {"low", "medium", "high", "critical"}
_TICKET_CATEGORIES = {
    "complaint",
    "maintenance",
    "driver_issue",
    "vehicle_issue",
    "route_issue",
    "pickup_issue",
    "other",
}
_CONFIG_TYPES = {
    "speed_threshold",
    "geofence",
    "idle_threshold",
    "alert_rule",
    "webhook_secret",
    "vendor_config",
    "retention_policy",
}


class VendorORM(Base):
    __tablename__ = "vendors"
    __table_args__ = (
        CheckConstraint(
            "auth_type IN ('header','signature','ip')",
            name="ck_vendors_auth_type",
        ),
        Index("ix_vendors_vendor_name", "vendor_name"),
        Index("ix_vendors_email", "email"),
        Index("ix_vendors_active", "active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    vendor_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    vendor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_person: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    signature_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    allowed_ips: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    auth_type: Mapped[str] = mapped_column(String(16), nullable=False, default="header")
    callback_format: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    devices: Mapped[list["DeviceORM"]] = relationship(
        back_populates="vendor",
        cascade="all, delete-orphan",
    )

    @validates("vendor_code")
    def validate_vendor_code(self, _: str, value: str) -> str:
        code = value.strip().upper()
        if not _VENDOR_CODE_RE.fullmatch(code):
            raise ValueError("vendor_code must match ^[A-Z0-9_-]{3,32}$")
        return code

    @validates("email")
    def validate_email(self, _: str, value: str | None) -> str | None:
        if value is None:
            return None
        email = value.strip().lower()
        if not _EMAIL_RE.fullmatch(email):
            raise ValueError("email is not valid")
        return email

    @validates("auth_type")
    def validate_auth_type(self, _: str, value: str) -> str:
        auth_type = value.strip().lower()
        if auth_type not in _AUTH_TYPES:
            raise ValueError("auth_type must be one of: header, signature, ip")
        return auth_type

    @validates("allowed_ips")
    def validate_allowed_ips(self, _: str, value: list[str]) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("allowed_ips must be a list of IP strings")
        normalised: list[str] = []
        for ip in value:
            ip_obj = ipaddress.ip_address(ip)
            normalised.append(str(ip_obj))
        return normalised

    @validates("callback_format", "metadata_json")
    def validate_json_objects(self, field: str, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError(f"{field} must be a JSON object")
        return value


class DeviceORM(Base):
    __tablename__ = "devices"
    __table_args__ = (
        CheckConstraint(
            "health_status IN ('healthy','warning','critical','offline')",
            name="ck_devices_health_status",
        ),
        Index("ix_devices_vendor_id", "vendor_id"),
        Index("ix_devices_active", "active"),
        Index("ix_devices_last_seen", "last_seen"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
    )
    imei: Mapped[str] = mapped_column(String(17), nullable=False, unique=True, index=True)
    serial_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(128), nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sim_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    installed_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    battery_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    signal_strength: Mapped[float | None] = mapped_column(Float, nullable=True)
    health_status: Mapped[str] = mapped_column(String(16), nullable=False, default="healthy")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    vendor: Mapped[VendorORM] = relationship(back_populates="devices")
    assignments: Mapped[list["DeviceVehicleAssignmentORM"]] = relationship(
        back_populates="device",
        cascade="all, delete-orphan",
    )

    @validates("imei")
    def validate_imei(self, _: str, value: str) -> str:
        imei = value.strip()
        if not _IMEI_RE.fullmatch(imei):
            raise ValueError("imei must be 14-17 numeric digits")
        return imei

    @validates("health_status")
    def validate_health_status(self, _: str, value: str) -> str:
        status = value.strip().lower()
        if status not in _HEALTH_STATUSES:
            raise ValueError("health_status must be one of: healthy, warning, critical, offline")
        return status

    @validates("battery_percent")
    def validate_battery_percent(self, _: str, value: float | None) -> float | None:
        if value is None:
            return None
        if value < 0 or value > 100:
            raise ValueError("battery_percent must be between 0 and 100")
        return value

    @validates("metadata_json")
    def validate_metadata_json(self, _: str, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("metadata_json must be a JSON object")
        return value


class WardORM(Base):
    __tablename__ = "wards"
    __table_args__ = ()

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    ward_code: Mapped[str] = mapped_column(String(24), nullable=False, unique=True)
    ward_name: Mapped[str] = mapped_column(String(255), nullable=False)
    zone_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("zones.id", ondelete="RESTRICT"), nullable=False)

    zone: Mapped["ZoneORM"] = relationship("ZoneORM", back_populates="wards")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    vehicles: Mapped[list["VehicleORM"]] = relationship(back_populates="ward")
    geofences: Mapped[list["GeofenceORM"]] = relationship(back_populates="ward")

    @validates("ward_code")
    def validate_ward_code(self, _: str, value: str) -> str:
        normalized = value.strip().upper()
        if not _WARD_CODE_RE.fullmatch(normalized):
            raise ValueError("ward_code must match ^[A-Z0-9_-]{2,24}$")
        return normalized


class RouteORM(Base):
    __tablename__ = "routes"
    __table_args__ = (
        Index("ix_routes_zone_id", "zone_id"),
        Index("ix_routes_ward_id", "ward_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    route_name: Mapped[str] = mapped_column(String(255), nullable=False)
    zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("zones.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ward_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wards.id", ondelete="RESTRICT"),
        nullable=False,
    )
    polyline_coordinates: Mapped[list[list[float]]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    vehicles: Mapped[list["VehicleORM"]] = relationship(back_populates="route")
    zone: Mapped["ZoneORM"] = relationship("ZoneORM")
    ward: Mapped["WardORM"] = relationship("WardORM")

    @validates("polyline_coordinates")
    def validate_polyline_coordinates(self, _: str, value: list[list[float]]) -> list[list[float]]:
        if not isinstance(value, list) or len(value) < 2:
            raise ValueError("polyline_coordinates must include at least 2 points")
        normalized: list[list[float]] = []
        for point in value:
            if not isinstance(point, list) or len(point) != 2:
                raise ValueError("polyline point must be [lng, lat]")
            lng = float(point[0])
            lat = float(point[1])
            if lng < -180 or lng > 180 or lat < -90 or lat > 90:
                raise ValueError("polyline point coordinates out of range")
            normalized.append([lng, lat])
        return normalized


class GeofenceORM(Base):
    __tablename__ = "geofences"
    __table_args__ = (
        CheckConstraint(
            "type IN ('depot','landfill','zone','parking','maintenance')",
            name="ck_geofences_type",
        ),
        CheckConstraint(
            "geometry_type IN ('circle','polygon')",
            name="ck_geofences_geometry_type",
        ),
        CheckConstraint(
            "geofence_for IN ('zone','ward','route')",
            name="ck_geofences_geofence_for",
        ),
        CheckConstraint(
            "scope_type IN ('ward','zone')",
            name="ck_geofences_scope_type",
        ),
        Index("ix_geofences_zone_id", "zone_id"),
        Index("ix_geofences_ward_id", "ward_id"),
        Index("ix_geofences_route_id", "route_id"),
        Index("ix_geofences_scope", "scope_type", "scope_id"),
        Index("ix_geofences_for_hierarchy", "geofence_for", "zone_id", "ward_id", "route_id"),
        Index("ix_geofences_active", "active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    geofence_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    geofence_name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    geometry_type: Mapped[str] = mapped_column(String(16), nullable=False)
    center_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    center_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    radius_meter: Mapped[float | None] = mapped_column(Float, nullable=True)
    polygon: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    geofence_for: Mapped[str] = mapped_column(String(16), nullable=False, default="ward", server_default=text("'ward'"))
    zone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("zones.id", ondelete="SET NULL"),
        nullable=True,
    )
    route_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("routes.id", ondelete="SET NULL"),
        nullable=True,
    )
    scope_type: Mapped[str] = mapped_column(String(16), nullable=False, default="ward", server_default=text("'ward'"))
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    ward_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wards.id", ondelete="SET NULL"),
        nullable=True,
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    ward: Mapped[WardORM | None] = relationship(back_populates="geofences")

    @validates("geofence_code")
    def validate_geofence_code(self, _: str, value: str) -> str:
        normalized = value.strip().upper()
        if not _GEOFENCE_CODE_RE.fullmatch(normalized):
            raise ValueError("geofence_code must match ^[A-Z0-9_-]{2,32}$")
        return normalized

    @validates("type")
    def validate_type(self, _: str, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _GEOFENCE_TYPES:
            raise ValueError("type must be one of: depot, landfill, zone, parking, maintenance")
        return normalized

    @validates("geometry_type")
    def validate_geometry_type(self, _: str, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _GEOMETRY_TYPES:
            raise ValueError("geometry_type must be one of: circle, polygon")
        return normalized

    @validates("geofence_for")
    def validate_geofence_for(self, _: str, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _GEOFENCE_FOR_TYPES:
            raise ValueError("geofence_for must be one of: zone, ward, route")
        return normalized

    @validates("center_lat")
    def validate_center_lat(self, _: str, value: float | None) -> float | None:
        if value is None:
            return None
        if value < -90 or value > 90:
            raise ValueError("center_lat must be between -90 and 90")
        return value

    @validates("center_lng")
    def validate_center_lng(self, _: str, value: float | None) -> float | None:
        if value is None:
            return None
        if value < -180 or value > 180:
            raise ValueError("center_lng must be between -180 and 180")
        return value

    @validates("radius_meter")
    def validate_radius_meter(self, _: str, value: float | None) -> float | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("radius_meter must be greater than 0")
        return value

    @validates("polygon")
    def validate_polygon(self, _: str, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise ValueError("polygon must be a GeoJSON object")
        if value.get("type") != "Polygon":
            raise ValueError("polygon GeoJSON type must be Polygon")
        coordinates = value.get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates) == 0:
            raise ValueError("polygon.coordinates must be a non-empty array")
        return value


class VehicleORM(Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        CheckConstraint(
            "fuel_type IN ('diesel','petrol','cng','electric','lng')",
            name="ck_vehicles_fuel_type",
        ),
        CheckConstraint(
            "operational_status IN ('operational','maintenance','breakdown','retired')",
            name="ck_vehicles_operational_status",
        ),
        CheckConstraint("capacity_kg >= 0", name="ck_vehicles_capacity_kg_non_negative"),
        CheckConstraint(
            "capacity_cubic_meter >= 0",
            name="ck_vehicles_capacity_cubic_meter_non_negative",
        ),
        CheckConstraint(
            "manufacture_year >= 1950 AND manufacture_year <= 2100",
            name="ck_vehicles_manufacture_year_range",
        ),
        Index("ix_vehicles_vendor_id", "vendor_id"),
        Index("ix_vehicles_ward_id", "ward_id"),
        Index("ix_vehicles_route_id", "route_id"),
        Index("ix_vehicles_active", "active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    vehicle_number: Mapped[str] = mapped_column(String(24), nullable=False, unique=True)
    registration_number: Mapped[str] = mapped_column(String(24), nullable=False, unique=True)
    truck_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    capacity_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    capacity_cubic_meter: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ward_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wards.id", ondelete="RESTRICT"),
        nullable=False,
    )
    route_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("routes.id", ondelete="SET NULL"),
        nullable=True,
    )
    fuel_type: Mapped[str] = mapped_column(String(16), nullable=False, default="diesel")
    operational_status: Mapped[str] = mapped_column(String(16), nullable=False, default="operational")
    chassis_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    engine_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manufacture_year: Mapped[int | None] = mapped_column(nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    vendor: Mapped[VendorORM] = relationship()
    ward: Mapped[WardORM] = relationship(back_populates="vehicles")
    route: Mapped[RouteORM | None] = relationship(back_populates="vehicles")
    assignments: Mapped[list["DeviceVehicleAssignmentORM"]] = relationship(
        back_populates="vehicle",
        cascade="all, delete-orphan",
    )

    @validates("vehicle_number")
    def validate_vehicle_number(self, _: str, value: str) -> str:
        normalized = value.strip().upper()
        if not _VEHICLE_NO_RE.fullmatch(normalized):
            raise ValueError("vehicle_number must match ^[A-Z0-9-]{4,24}$")
        return normalized

    @validates("registration_number")
    def validate_registration_number(self, _: str, value: str) -> str:
        normalized = value.strip().upper()
        if not _REG_NO_RE.fullmatch(normalized):
            raise ValueError("registration_number must match ^[A-Z0-9-]{4,24}$")
        return normalized

    @validates("fuel_type")
    def validate_fuel_type(self, _: str, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _FUEL_TYPES:
            raise ValueError("fuel_type must be one of: diesel, petrol, cng, electric, lng")
        return normalized

    @validates("operational_status")
    def validate_operational_status(self, _: str, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _VEHICLE_STATUSES:
            raise ValueError(
                "operational_status must be one of: operational, maintenance, breakdown, retired"
            )
        return normalized

    @validates("capacity_kg", "capacity_cubic_meter")
    def validate_non_negative_capacity(self, field: str, value: float) -> float:
        if value < 0:
            raise ValueError(f"{field} must be non-negative")
        return value

    @validates("manufacture_year")
    def validate_manufacture_year(self, _: str, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 1950 or value > 2100:
            raise ValueError("manufacture_year must be between 1950 and 2100")
        return value

    @validates("metadata_json")
    def validate_metadata_json_vehicle(self, _: str, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("metadata_json must be a JSON object")
        return value


class DeviceVehicleAssignmentORM(Base):
    __tablename__ = "device_vehicle_assignments"
    __table_args__ = (
        CheckConstraint(
            "assigned_to IS NULL OR assigned_to >= assigned_from",
            name="ck_dva_assigned_range",
        ),
        CheckConstraint(
            "(active = false) OR (assigned_to IS NULL)",
            name="ck_dva_active_assigned_to",
        ),
        Index("ix_dva_device_assigned_from", "device_id", "assigned_from"),
        Index("ix_dva_vehicle_assigned_from", "vehicle_id", "assigned_from"),
        Index(
            "ux_dva_active_device",
            "device_id",
            unique=True,
            postgresql_where=text("active IS TRUE AND assigned_to IS NULL"),
        ),
        Index(
            "ux_dva_active_vehicle",
            "vehicle_id",
            unique=True,
            postgresql_where=text("active IS TRUE AND assigned_to IS NULL"),
        ),
    )

    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        primary_key=True,
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    assigned_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    assigned_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    remarks: Mapped[str | None] = mapped_column(String(500), nullable=True)

    device: Mapped[DeviceORM] = relationship(back_populates="assignments")
    vehicle: Mapped[VehicleORM] = relationship(back_populates="assignments")

    @validates("assigned_to")
    def validate_assigned_to(self, _: str, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if self.assigned_from is not None and value < self.assigned_from:
            raise ValueError("assigned_to must be greater than or equal to assigned_from")
        return value

    def close(self, *, assigned_to: datetime, remarks: str | None = None) -> None:
        self.assigned_to = assigned_to
        self.active = False
        if remarks is not None:
            self.remarks = remarks


class DriverORM(Base):
    __tablename__ = "drivers"
    __table_args__ = (
        Index("ix_drivers_name", "name"),
        Index("ix_drivers_vendor_id", "vendor_id"),
        Index("ix_drivers_active", "active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    license_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    assigned_vehicle_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class GtcCheckpointORM(Base):
    __tablename__ = "gtc_checkpoints"
    __table_args__ = (
        Index("ix_gtc_checkpoints_truck_arrived", "truck_id", "arrived_at"),
        Index("ix_gtc_checkpoints_arrived_at", "arrived_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    truck_id: Mapped[str] = mapped_column(String(128), nullable=False)
    arrived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_dry: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    is_wet: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    is_metal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    is_plastic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    is_sanitary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    truck_cleanliness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    gtc_cleanliness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    remarks: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class PickupPointORM(Base):
    __tablename__ = "pickup_points"
    __table_args__ = (
        Index("ix_pickup_points_zone_id", "zone_id"),
        Index("ix_pickup_points_route_id", "route_id"),
        Index("ix_pickup_points_ward_id", "ward_id"),
        Index("ix_pickup_points_route_sequence", "route_id", "sequence_no"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    pickup_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("zones.id", ondelete="RESTRICT"), nullable=True)
    ward_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("wards.id", ondelete="RESTRICT"), nullable=True)
    route_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("routes.id", ondelete="CASCADE"), nullable=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_pickup_time: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pickup_radius_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class PickupPointCrossingORM(Base):
    __tablename__ = "pickup_point_crossings"
    __table_args__ = (
        Index("ix_pickup_point_crossings_crossed_at", "crossed_at"),
        Index("ix_pickup_point_crossings_vehicle_crossed", "vehicle_id", "crossed_at"),
        Index("ix_pickup_point_crossings_route_crossed", "route_id", "crossed_at"),
        Index("ix_pickup_point_crossings_pickup_crossed", "pickup_point_id", "crossed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    vehicle_id: Mapped[str] = mapped_column(String(128), nullable=False)
    route_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("routes.id", ondelete="SET NULL"),
        nullable=True,
    )
    pickup_point_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pickup_points.id", ondelete="CASCADE"),
        nullable=False,
    )
    crossed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    distance_m: Mapped[float] = mapped_column(Float, nullable=False)
    radius_m: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="telemetry")
    imei: Mapped[str | None] = mapped_column(String(17), nullable=True)
    vendor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class TicketORM(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open','in_progress','pending','resolved','closed')",
            name="ck_tickets_status",
        ),
        CheckConstraint(
            "priority IN ('low','medium','high','critical')",
            name="ck_tickets_priority",
        ),
        CheckConstraint(
            "category IN ('complaint','maintenance','driver_issue','vehicle_issue','route_issue','pickup_issue','other')",
            name="ck_tickets_category",
        ),
        CheckConstraint("escalation_level >= 0", name="ck_tickets_escalation_non_negative"),
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_priority", "priority"),
        Index("ix_tickets_category", "category"),
        Index("ix_tickets_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="complaint")
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    related_alert_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    related_truck_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    related_driver_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    escalation_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    sla_breached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    comments: Mapped[list["TicketCommentORM"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
    )

    @validates("status")
    def validate_ticket_status(self, _: str, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _TICKET_STATUSES:
            raise ValueError("status must be one of: open, in_progress, pending, resolved, closed")
        return normalized

    @validates("priority")
    def validate_ticket_priority(self, _: str, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _TICKET_PRIORITIES:
            raise ValueError("priority must be one of: low, medium, high, critical")
        return normalized

    @validates("category")
    def validate_ticket_category(self, _: str, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _TICKET_CATEGORIES:
            raise ValueError(
                "category must be one of: complaint, maintenance, driver_issue, vehicle_issue, route_issue, pickup_issue, other"
            )
        return normalized


class TicketCommentORM(Base):
    __tablename__ = "ticket_comments"
    __table_args__ = (
        Index("ix_ticket_comments_ticket_id", "ticket_id"),
        Index("ix_ticket_comments_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
    )
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(String(4000), nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    ticket: Mapped[TicketORM] = relationship(back_populates="comments")


class AnalyticsVehicleStateORM(Base):
    __tablename__ = "analytics_vehicle_state"

    vehicle_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    imei: Mapped[str] = mapped_column(String(17), nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    last_event_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_lat: Mapped[float] = mapped_column(Float, nullable=False)
    last_lng: Mapped[float] = mapped_column(Float, nullable=False)
    last_speed_kph: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_odometer_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_ignition: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    trip_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trip_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trip_start_odometer_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    trip_distance_km: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    trip_runtime_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trip_moving_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trip_idle_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trip_stoppages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    idle_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    idle_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idle_anchor_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    idle_anchor_lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    current_geofence_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    current_geofence_entered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_route_deviation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class AnalyticsTripRecordORM(Base):
    __tablename__ = "analytics_trip_records"
    __table_args__ = (
        Index("ix_analytics_trip_records_vehicle_started", "vehicle_id", "started_at"),
        Index("ix_analytics_trip_records_started", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    vehicle_id: Mapped[str] = mapped_column(String(128), nullable=False)
    imei: Mapped[str] = mapped_column(String(17), nullable=False)
    device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    vendor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    runtime_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    moving_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    idle_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stoppages_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_odometer_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_odometer_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class AnalyticsIdleRecordORM(Base):
    __tablename__ = "analytics_idle_records"
    __table_args__ = (
        Index("ix_analytics_idle_records_vehicle_started", "vehicle_id", "started_at"),
        Index("ix_analytics_idle_records_started", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    vehicle_id: Mapped[str] = mapped_column(String(128), nullable=False)
    imei: Mapped[str] = mapped_column(String(17), nullable=False)
    device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    vendor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class AnalyticsOverspeedEventORM(Base):
    __tablename__ = "analytics_overspeed_events"
    __table_args__ = (
        Index("ix_analytics_overspeed_vehicle_ts", "vehicle_id", "event_ts"),
        Index("ix_analytics_overspeed_event_ts", "event_ts"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    vehicle_id: Mapped[str] = mapped_column(String(128), nullable=False)
    imei: Mapped[str] = mapped_column(String(17), nullable=False)
    device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    vendor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    speed_kph: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_kph: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class AnalyticsGeofenceEventORM(Base):
    __tablename__ = "analytics_geofence_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('entry','exit','route_deviation')",
            name="ck_analytics_geofence_event_type",
        ),
        Index("ix_analytics_geofence_vehicle_ts", "vehicle_id", "event_ts"),
        Index("ix_analytics_geofence_code_ts", "geofence_code", "event_ts"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    vehicle_id: Mapped[str] = mapped_column(String(128), nullable=False)
    imei: Mapped[str] = mapped_column(String(17), nullable=False)
    device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    vendor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    geofence_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    geofence_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    geofence_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    event_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dwell_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class AnalyticsDailyKPIORM(Base):
    __tablename__ = "analytics_daily_kpis"
    __table_args__ = (
        Index("ix_analytics_daily_kpis_metric_date", "metric_date"),
        Index("ix_analytics_daily_kpis_vendor_date", "vendor_id", "metric_date"),
    )

    metric_date: Mapped[date] = mapped_column(Date, primary_key=True)
    vehicle_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    imei: Mapped[str] = mapped_column(String(17), nullable=False)
    vendor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    trips_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    runtime_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    moving_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    idle_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stoppages_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overspeed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    geofence_entries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    geofence_exits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    route_deviation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fuel_used_l: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    utilization_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class OperationalCategoryORM(Base):
    __tablename__ = "operational_categories"
    __table_args__ = (Index("ix_operational_categories_active", "active"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    category_code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    category_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class AlertORM(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open','acknowledged','resolved','escalated')",
            name="ck_alerts_status",
        ),
        CheckConstraint(
            "severity IN ('low','medium','high','critical')",
            name="ck_alerts_severity",
        ),
        Index("ix_alerts_vehicle_ts", "vehicle_id", "triggered_at"),
        Index("ix_alerts_status", "status"),
        Index("ix_alerts_category", "category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    escalation_status: Mapped[str] = mapped_column(String(64), nullable=False, default="none")

    vehicle_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    imei: Mapped[str | None] = mapped_column(String(17), nullable=True)
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    route_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    ward_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    actions: Mapped[list["AlertActionORM"]] = relationship(
        back_populates="alert",
        cascade="all, delete-orphan",
    )

    @validates("status")
    def validate_status(self, _: str, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _ALERT_STATUSES:
            raise ValueError("status must be one of: open, acknowledged, resolved, escalated")
        return normalized

    @validates("severity")
    def validate_severity(self, _: str, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _ALERT_SEVERITIES:
            raise ValueError("severity must be one of: low, medium, high, critical")
        return normalized


class AlertActionORM(Base):
    __tablename__ = "alert_actions"
    __table_args__ = (
        CheckConstraint(
            "action_type IN ('created','acknowledged','resolved','escalated','updated','commented')",
            name="ck_alert_actions_type",
        ),
        Index("ix_alert_actions_alert_created", "alert_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column("payload", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    alert: Mapped[AlertORM] = relationship(back_populates="actions")

    @validates("action_type")
    def validate_action_type(self, _: str, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _ALERT_ACTIONS:
            raise ValueError(
                "action_type must be one of: created, acknowledged, resolved, escalated, updated, commented"
            )
        return normalized


class SystemConfigurationORM(Base):
    __tablename__ = "system_configurations"
    __table_args__ = (
        CheckConstraint(
            "config_type IN ('speed_threshold','geofence','idle_threshold','alert_rule','webhook_secret','vendor_config','retention_policy')",
            name="ck_system_configurations_type",
        ),
        Index("ix_system_configurations_type", "config_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    config_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    config_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    value_json: Mapped[dict[str, Any]] = mapped_column("value", JSONB, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    @validates("config_type")
    def validate_config_type(self, _: str, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _CONFIG_TYPES:
            raise ValueError(
                "config_type must be one of: speed_threshold, geofence, idle_threshold, alert_rule, webhook_secret, vendor_config, retention_policy"
            )
        return normalized


class AuditLogORM(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_created", "created_at"),
        Index("ix_audit_logs_actor", "actor"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    before_json: Mapped[dict[str, Any] | None] = mapped_column("before", JSONB, nullable=True)
    after_json: Mapped[dict[str, Any] | None] = mapped_column("after", JSONB, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


auth_user_roles = Table(
    "auth_user_roles",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("auth_roles.id", ondelete="CASCADE"), primary_key=True),
    Column("assigned_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("assigned_by", String(255), nullable=True),
)


auth_role_permissions = Table(
    "auth_role_permissions",
    Base.metadata,
    Column("role_id", UUID(as_uuid=True), ForeignKey("auth_roles.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "permission_id",
        UUID(as_uuid=True),
        ForeignKey("auth_permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("granted_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("granted_by", String(255), nullable=True),
)


class AuthRoleORM(AuditBase):
    __tablename__ = "auth_roles"
    __table_args__ = (
        Index("ix_auth_roles_active", "active"),
        Index("ix_auth_roles_role_name", "role_name"),
    )

    role_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    role_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    permissions: Mapped[list["AuthPermissionORM"]] = relationship(
        secondary=auth_role_permissions,
        back_populates="roles",
    )
    users: Mapped[list["AuthUserORM"]] = relationship(
        secondary=auth_user_roles,
        back_populates="roles",
    )

    @validates("role_key")
    def validate_role_key(self, _: str, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized or len(normalized) > 64:
            raise ValueError("role_key must be 1-64 characters")
        return normalized


class AuthPermissionORM(AuditBase):
    __tablename__ = "auth_permissions"
    __table_args__ = (
        Index("ix_auth_permissions_active", "active"),
        Index("ix_auth_permissions_permission_name", "permission_name"),
    )

    permission_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    permission_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    roles: Mapped[list[AuthRoleORM]] = relationship(
        secondary=auth_role_permissions,
        back_populates="permissions",
    )

    @validates("permission_key")
    def validate_permission_key(self, _: str, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized or len(normalized) > 128:
            raise ValueError("permission_key must be 1-128 characters")
        return normalized


class AuthUserORM(AuditBase):
    __tablename__ = "auth_users"
    __table_args__ = (
        Index("ix_auth_users_username", "username"),
        Index("ix_auth_users_email", "email"),
        Index("ix_auth_users_active", "active"),
    )

    username: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, unique=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    roles: Mapped[list[AuthRoleORM]] = relationship(
        secondary=auth_user_roles,
        back_populates="users",
    )
    refresh_tokens: Mapped[list["AuthRefreshTokenORM"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @validates("username")
    def validate_username(self, _: str, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized or len(normalized) > 128:
            raise ValueError("username must be 1-128 characters")
        return normalized

    @validates("email")
    def validate_email(self, _: str, value: str | None) -> str | None:
        if value is None:
            return None
        email = value.strip().lower()
        if not _EMAIL_RE.fullmatch(email):
            raise ValueError("email is not valid")
        return email

    @validates("metadata_json")
    def validate_metadata_json(self, _: str, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("metadata_json must be a JSON object")
        return value


class AuthRefreshTokenORM(Base):
    __tablename__ = "auth_refresh_tokens"
    __table_args__ = (
        Index("ix_auth_refresh_tokens_user_id", "user_id"),
        Index("ix_auth_refresh_tokens_expires_at", "expires_at"),
        Index("ix_auth_refresh_tokens_revoked_at", "revoked_at"),
        Index("ix_auth_refresh_tokens_token_family_id", "token_family_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    token_family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    replaced_by_token_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_refresh_tokens.id", ondelete="SET NULL"),
        nullable=True,
    )

    user: Mapped[AuthUserORM] = relationship(back_populates="refresh_tokens")
