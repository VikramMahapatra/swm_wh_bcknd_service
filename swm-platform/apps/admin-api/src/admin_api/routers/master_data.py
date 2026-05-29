from __future__ import annotations

import json
import ipaddress
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import NoResultFound
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from swm_db import (
    AssignmentCreateInput,
    DeviceORM,
    DeviceRepository,
    DeviceVehicleAssignmentORM,
    DeviceVehicleAssignmentRepository,
    DeviceVehicleAssignmentService,
    GeofenceORM,
    GeofenceRepository,
    RouteORM,
    RouteRepository,
    VehicleORM,
    VehicleRepository,
    VendorORM,
    VendorRepository,
    WardORM,
    WardRepository,
    ZoneORM,
    get_db_session,
)

from admin_api.api_support import (
    MessageResponse,
    PageResponse,
    RoleContext,
    _fetch_or_404,
    _list_entities,
    _parse_bool,
    _parse_csv_with_required,
    _parse_uuid,
    _raise_not_found,
    _to_dict,
    require_roles,
)

router = APIRouter()


def _parse_import_uuid(value: str | None, *, field: str, row_number: int, required: bool = True) -> UUID | None:
    normalized = (value or "").strip()
    if not normalized:
        if required:
            raise HTTPException(status_code=400, detail=f"invalid {field} at row {row_number}")
        return None
    try:
        return UUID(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid {field} at row {row_number}") from exc


def _parse_import_float(value: str | None, *, field: str, row_number: int, default: float | None = None) -> float | None:
    normalized = (value or "").strip()
    if not normalized:
        return default
    try:
        return float(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid {field} at row {row_number}") from exc


def _parse_import_int(value: str | None, *, field: str, row_number: int, default: int | None = None) -> int | None:
    normalized = (value or "").strip()
    if not normalized:
        return default
    try:
        return int(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid {field} at row {row_number}") from exc


def _parse_import_datetime(value: str | None, *, field: str, row_number: int) -> datetime | None:
    normalized = (value or "").strip()
    if not normalized:
        return None
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid {field} at row {row_number}") from exc


class VendorIn(BaseModel):
    vendor_code: str = Field(min_length=3, max_length=32, pattern=r"^[A-Z0-9_-]{3,32}$")
    vendor_name: str = Field(min_length=1)
    contact_person: str | None = None
    email: str | None = None
    phone: str | None = None
    webhook_secret: str | None = None
    signature_key: str | None = None
    allowed_ips: list[str] = Field(default_factory=list)
    auth_type: Literal["header", "signature", "ip"] = "header"
    callback_format: dict[str, Any] = Field(default_factory=dict)
    active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("email is not valid")
        local_part, _, domain = normalized.partition("@")
        if not local_part or "." not in domain or domain.startswith(".") or domain.endswith("."):
            raise ValueError("email is not valid")
        return normalized

    @field_validator("allowed_ips")
    @classmethod
    def validate_allowed_ips(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for ip in value:
            normalized.append(str(ipaddress.ip_address(ip)))
        return normalized


class DeviceIn(BaseModel):
    vendor_id: UUID
    imei: str = Field(min_length=14, max_length=17, pattern=r"^[0-9]{14,17}$")
    serial_no: str | None = None
    model: str | None = None
    manufacturer: str | None = None
    firmware_version: str | None = None
    sim_number: str | None = None
    installed_on: datetime | None = None
    activated_on: datetime | None = None
    last_seen: datetime | None = None
    battery_percent: float | None = Field(default=None, ge=0, le=100)
    signal_strength: float | None = None
    health_status: Literal["healthy", "warning", "critical", "offline"] = "healthy"
    active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class VehicleIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    vehicle_number: str = Field(min_length=4, max_length=24, pattern=r"^[A-Z0-9-]{4,24}$")
    registration_number: str = Field(min_length=4, max_length=24, pattern=r"^[A-Z0-9-]{4,24}$")
    vendor_id: UUID = Field(validation_alias=AliasChoices("vendor_id", "vendorId", "contractor_id", "contractorId"))
    ward_id: UUID
    route_id: UUID | None = None
    truck_type: str | None = None
    capacity_kg: float = Field(default=0, ge=0)
    capacity_cubic_meter: float = Field(default=0, ge=0)
    fuel_type: Literal["diesel", "petrol", "cng", "electric", "lng"] = "diesel"
    operational_status: Literal["operational", "maintenance", "breakdown", "retired"] = "operational"
    chassis_number: str | None = None
    engine_number: str | None = None
    manufacture_year: int | None = Field(default=None, ge=1950, le=2100)
    active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class WardIn(BaseModel):
    ward_code: str
    ward_name: str
    zone_name: str
    active: bool = True


async def _resolve_zone_id(session: AsyncSession, zone_ref: str) -> UUID:
    normalized = zone_ref.strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="zone_name is required")

    try:
        zone_uuid = UUID(normalized)
        zone = (await session.execute(select(ZoneORM).where(ZoneORM.id == zone_uuid))).scalars().first()
        if zone is not None:
            return zone.id
    except ValueError:
        pass

    zone = (
        await session.execute(
            select(ZoneORM).where(
                (func.lower(ZoneORM.zone_code) == normalized.lower())
                | (func.lower(ZoneORM.zone_name) == normalized.lower())
            )
        )
    ).scalars().first()
    if zone is None:
        raise HTTPException(status_code=400, detail=f"zone not found for '{zone_ref}'")
    return zone.id


class RouteIn(BaseModel):
    route_name: str = Field(min_length=1)
    zone_id: UUID
    ward_id: UUID
    polyline_coordinates: list[list[float]] = Field(min_length=2)


class GeofenceIn(BaseModel):
    geofence_code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Z0-9_-]{2,32}$")
    geofence_name: str = Field(min_length=1)
    type: Literal["depot", "landfill", "zone", "parking", "maintenance"]
    geometry_type: Literal["circle", "polygon"]
    center_lat: float | None = Field(default=None, ge=-90, le=90)
    center_lng: float | None = Field(default=None, ge=-180, le=180)
    radius_meter: float | None = Field(default=None, gt=0)
    polygon: dict[str, Any] | None = None
    geofence_for: Literal["zone", "ward", "route"] = "ward"
    zone_id: UUID
    ward_id: UUID | None = None
    route_id: UUID | None = None
    active: bool = True

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        if value.get("type") != "Polygon":
            raise ValueError("polygon GeoJSON type must be Polygon")
        coordinates = value.get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates) == 0:
            raise ValueError("polygon.coordinates must be a non-empty array")
        return value


class DeviceAssignmentIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    device_id: UUID
    vehicle_id: UUID
    assigned_from: datetime | None = None
    assigned_to: datetime | None = None
    active: bool = True
    remarks: str | None = None


# --- Zone CRUD Endpoints ---
class ZoneIn(BaseModel):
    zone_code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Z0-9_-]{2,32}$")
    zone_name: str = Field(min_length=1)
    active: bool = True

class ZoneOut(BaseModel):
    zone_code: str
    zone_name: str
    active: bool

@router.post("/zones", response_model=ZoneOut)
async def create_zone(payload: ZoneIn, session: AsyncSession = Depends(get_db_session)):
    zone = ZoneORM(
        zone_code=payload.zone_code,
        zone_name=payload.zone_name,
        active=payload.active,
    )
    session.add(zone)
    await session.commit()
    await session.refresh(zone)
    return zone

@router.get("/zones", response_model=list[ZoneOut])
async def list_zones(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(ZoneORM).order_by(ZoneORM.zone_code))
    return result.scalars().all()

@router.get("/zones/{zone_id}", response_model=ZoneOut)
async def get_zone(zone_id: UUID, session: AsyncSession = Depends(get_db_session)):
    zone = await session.get(ZoneORM, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone

@router.put("/zones/{zone_id}", response_model=ZoneOut)
async def update_zone(zone_id: UUID, payload: ZoneIn, session: AsyncSession = Depends(get_db_session)):
    zone = await session.get(ZoneORM, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    zone.zone_code = payload.zone_code
    zone.zone_name = payload.zone_name
    zone.active = payload.active
    await session.commit()
    await session.refresh(zone)
    return zone

@router.delete("/zones/{zone_id}", response_model=MessageResponse)
async def delete_zone(zone_id: UUID, session: AsyncSession = Depends(get_db_session)):
    zone = await session.get(ZoneORM, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    await session.delete(zone)
    await session.commit()
    return MessageResponse(message="Zone deleted successfully")


@router.get("/vendors")
async def list_vendors(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    auth_type: str | None = Query(default=None),
    ui_compat: bool = Query(default=False),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse | list[dict[str, Any]]:
    result = await _list_entities(
        session,
        VendorORM,
        page=page,
        page_size=page_size,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
        filters={"active": active, "auth_type": auth_type},
    )

    if not ui_compat:
        return result

    items: list[dict[str, Any]] = []
    for vendor in result.items:
        item_id = vendor.get("id")
        item_name = vendor.get("vendor_name") or vendor.get("contact_person") or ""
        items.append(
            {
                "id": str(item_id) if item_id is not None else "",
                "name": item_name,
                "company_name": vendor.get("vendor_name") or "",
                "companyName": vendor.get("vendor_name") or "",
                "phone": vendor.get("phone"),
                "email": vendor.get("email"),
                "status": "active" if vendor.get("active", True) else "inactive",
                "supervisor_name": vendor.get("contact_person"),
                "active": vendor.get("active", True),
            }
        )
    return items


@router.post("/vendors")
async def create_vendor(
    payload: VendorIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = VendorRepository(session)
    row = await repo.create(
        vendor_code=payload.vendor_code,
        vendor_name=payload.vendor_name,
        contact_person=payload.contact_person,
        email=payload.email,
        phone=payload.phone,
        webhook_secret=payload.webhook_secret,
        signature_key=payload.signature_key,
        allowed_ips=payload.allowed_ips,
        auth_type=payload.auth_type,
        callback_format=payload.callback_format,
        active=payload.active,
        metadata_json=payload.metadata,
    )
    return _to_dict(row)


@router.get("/vendors/{vendor_id}")
async def get_vendor(
    vendor_id: UUID,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = VendorRepository(session)
    row = await _fetch_or_404(repo.get_by_id, "vendor", vendor_id)
    return _to_dict(row)


@router.put("/vendors/{vendor_id}")
async def update_vendor(
    vendor_id: UUID,
    payload: VendorIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = VendorRepository(session)
    try:
        row = await repo.update(
            vendor_id,
            vendor_code=payload.vendor_code,
            vendor_name=payload.vendor_name,
            contact_person=payload.contact_person,
            email=payload.email,
            phone=payload.phone,
            webhook_secret=payload.webhook_secret,
            signature_key=payload.signature_key,
            allowed_ips=payload.allowed_ips,
            auth_type=payload.auth_type,
            callback_format=payload.callback_format,
            active=payload.active,
            metadata_json=payload.metadata,
        )
    except NoResultFound:
        _raise_not_found("vendor", vendor_id)
    return _to_dict(row)


@router.delete("/vendors/{vendor_id}", response_model=MessageResponse)
async def delete_vendor(
    vendor_id: UUID,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    repo = VendorRepository(session)
    try:
        await repo.delete(vendor_id)
    except NoResultFound:
        _raise_not_found("vendor", vendor_id)
    return MessageResponse(message="deleted")


@router.post("/vendors/import")
async def bulk_import_vendors(
    file: UploadFile = File(...),
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    content = (await file.read()).decode("utf-8")
    rows = _parse_csv_with_required(content, required_columns={"vendor_code", "vendor_name"})
    repo = VendorRepository(session)
    created = await repo.bulk_create(
        [
            {
                "vendor_code": r["vendor_code"],
                "vendor_name": r["vendor_name"],
                "contact_person": r.get("contact_person") or None,
                "email": r.get("email") or None,
                "phone": r.get("phone") or None,
                "webhook_secret": r.get("webhook_secret") or None,
                "signature_key": r.get("signature_key") or None,
                "allowed_ips": [ip.strip() for ip in (r.get("allowed_ips") or "").split(";") if ip.strip()],
                "auth_type": r.get("auth_type") or "header",
                "callback_format": {},
                "active": _parse_bool(r.get("active"), default=True),
                "metadata_json": {},
            }
            for r in rows
        ]
    )
    return {"created": len(created)}


@router.get("/devices", response_model=PageResponse)
async def list_devices(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    vendor_id: UUID | None = Query(default=None),
    health_status: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse:
    return await _list_entities(
        session,
        DeviceORM,
        page=page,
        page_size=page_size,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
        filters={"active": active, "vendor_id": vendor_id, "health_status": health_status},
    )


@router.post("/devices")
async def create_device(
    payload: DeviceIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = DeviceRepository(session)
    row = await repo.create(
        vendor_id=payload.vendor_id,
        imei=payload.imei,
        serial_no=payload.serial_no,
        model=payload.model,
        manufacturer=payload.manufacturer,
        firmware_version=payload.firmware_version,
        sim_number=payload.sim_number,
        installed_on=payload.installed_on,
        activated_on=payload.activated_on,
        last_seen=payload.last_seen,
        battery_percent=payload.battery_percent,
        signal_strength=payload.signal_strength,
        health_status=payload.health_status,
        active=payload.active,
        metadata_json=payload.metadata,
    )
    return _to_dict(row)


@router.get("/devices/{device_id}")
async def get_device(
    device_id: UUID,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = DeviceRepository(session)
    row = await _fetch_or_404(repo.get_by_id, "device", device_id)
    return _to_dict(row)


@router.put("/devices/{device_id}")
async def update_device(
    device_id: UUID,
    payload: DeviceIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = DeviceRepository(session)
    try:
        row = await repo.update(
            device_id,
            vendor_id=payload.vendor_id,
            imei=payload.imei,
            serial_no=payload.serial_no,
            model=payload.model,
            manufacturer=payload.manufacturer,
            firmware_version=payload.firmware_version,
            sim_number=payload.sim_number,
            installed_on=payload.installed_on,
            activated_on=payload.activated_on,
            last_seen=payload.last_seen,
            battery_percent=payload.battery_percent,
            signal_strength=payload.signal_strength,
            health_status=payload.health_status,
            active=payload.active,
            metadata_json=payload.metadata,
        )
    except NoResultFound:
        _raise_not_found("device", device_id)
    return _to_dict(row)


@router.delete("/devices/{device_id}", response_model=MessageResponse)
async def delete_device(
    device_id: UUID,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    repo = DeviceRepository(session)
    try:
        await repo.delete(device_id)
    except NoResultFound:
        _raise_not_found("device", device_id)
    return MessageResponse(message="deleted")


@router.post("/devices/import")
async def bulk_import_devices(
    file: UploadFile = File(...),
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    content = (await file.read()).decode("utf-8")
    rows = _parse_csv_with_required(content, required_columns={"vendor_id", "imei"})
    repo = DeviceRepository(session)
    payloads: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        payloads.append(
            {
                "vendor_id": _parse_import_uuid(row.get("vendor_id"), field="vendor_id", row_number=index),
                "imei": row["imei"],
                "serial_no": row.get("serial_no") or None,
                "model": row.get("model") or None,
                "manufacturer": row.get("manufacturer") or None,
                "firmware_version": row.get("firmware_version") or None,
                "sim_number": row.get("sim_number") or None,
                "health_status": row.get("health_status") or "healthy",
                "active": _parse_bool(row.get("active"), default=True),
                "metadata_json": {},
            }
        )
    created = await repo.bulk_create(payloads)
    return {"created": len(created)}


@router.get("/vehicles", response_model=PageResponse)
async def list_vehicles(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    vendor_id: UUID | None = Query(default=None),
    ward_id: UUID | None = Query(default=None),
    route_id: UUID | None = Query(default=None),
    fuel_type: str | None = Query(default=None),
    operational_status: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse:
    return await _list_entities(
        session,
        VehicleORM,
        page=page,
        page_size=page_size,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
        filters={
            "active": active,
            "vendor_id": vendor_id,
            "ward_id": ward_id,
            "route_id": route_id,
            "fuel_type": fuel_type,
            "operational_status": operational_status,
        },
    )


@router.post("/vehicles")
async def create_vehicle(
    payload: VehicleIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = VehicleRepository(session)
    row = await repo.create(
        vehicle_number=payload.vehicle_number,
        registration_number=payload.registration_number,
        truck_type=payload.truck_type,
        capacity_kg=payload.capacity_kg,
        capacity_cubic_meter=payload.capacity_cubic_meter,
        vendor_id=payload.vendor_id,
        ward_id=payload.ward_id,
        route_id=payload.route_id,
        fuel_type=payload.fuel_type,
        operational_status=payload.operational_status,
        chassis_number=payload.chassis_number,
        engine_number=payload.engine_number,
        manufacture_year=payload.manufacture_year,
        active=payload.active,
        metadata_json=payload.metadata,
    )
    return _to_dict(row)


@router.get("/vehicles/{vehicle_id}")
async def get_vehicle(
    vehicle_id: UUID,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = VehicleRepository(session)
    row = await _fetch_or_404(repo.get_by_id, "vehicle", vehicle_id)
    return _to_dict(row)


@router.put("/vehicles/{vehicle_id}")
async def update_vehicle(
    vehicle_id: UUID,
    payload: VehicleIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = VehicleRepository(session)
    try:
        row = await repo.update(
            vehicle_id,
            vehicle_number=payload.vehicle_number,
            registration_number=payload.registration_number,
            truck_type=payload.truck_type,
            capacity_kg=payload.capacity_kg,
            capacity_cubic_meter=payload.capacity_cubic_meter,
            vendor_id=payload.vendor_id,
            ward_id=payload.ward_id,
            route_id=payload.route_id,
            fuel_type=payload.fuel_type,
            operational_status=payload.operational_status,
            chassis_number=payload.chassis_number,
            engine_number=payload.engine_number,
            manufacture_year=payload.manufacture_year,
            active=payload.active,
            metadata_json=payload.metadata,
        )
    except NoResultFound:
        _raise_not_found("vehicle", vehicle_id)
    return _to_dict(row)


@router.delete("/vehicles/{vehicle_id}", response_model=MessageResponse)
async def delete_vehicle(
    vehicle_id: UUID,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    repo = VehicleRepository(session)
    try:
        await repo.delete(vehicle_id)
    except NoResultFound:
        _raise_not_found("vehicle", vehicle_id)
    return MessageResponse(message="deleted")


@router.post("/vehicles/import")
async def bulk_import_vehicles(
    file: UploadFile = File(...),
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    content = (await file.read()).decode("utf-8")
    rows = _parse_csv_with_required(
        content,
        required_columns={"vehicle_number", "registration_number", "vendor_id", "ward_id"},
    )
    repo = VehicleRepository(session)
    payloads: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        payloads.append(
            {
                "vehicle_number": row["vehicle_number"],
                "registration_number": row["registration_number"],
                "vendor_id": _parse_import_uuid(row.get("vendor_id"), field="vendor_id", row_number=index),
                "ward_id": _parse_import_uuid(row.get("ward_id"), field="ward_id", row_number=index),
                "route_id": _parse_import_uuid(row.get("route_id"), field="route_id", row_number=index, required=False),
                "truck_type": row.get("truck_type") or None,
                "capacity_kg": _parse_import_float(row.get("capacity_kg"), field="capacity_kg", row_number=index, default=0.0),
                "capacity_cubic_meter": _parse_import_float(
                    row.get("capacity_cubic_meter"), field="capacity_cubic_meter", row_number=index, default=0.0
                ),
                "fuel_type": row.get("fuel_type") or "diesel",
                "operational_status": row.get("operational_status") or "operational",
                "chassis_number": row.get("chassis_number") or None,
                "engine_number": row.get("engine_number") or None,
                "manufacture_year": _parse_import_int(
                    row.get("manufacture_year"), field="manufacture_year", row_number=index, default=None
                ),
                "active": _parse_bool(row.get("active"), default=True),
                "metadata_json": {},
            }
        )
    created = await repo.bulk_create(payloads)
    return {"created": len(created)}


@router.get("/routes")
async def list_routes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    ward_id: UUID | None = Query(default=None),
    zone_id: UUID | None = Query(default=None),
    ui_compat: bool = Query(default=False),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse | list[dict[str, Any]]:
    result = await _list_entities(
        session,
        RouteORM,
        page=page,
        page_size=page_size,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
        filters={},
    )

    if not ui_compat and ward_id is None and zone_id is None:
        return result

    compat_items: list[dict[str, Any]] = []

    for route in result.items:
        route_zone_id = str(route.get("zone_id") or "")
        route_ward_id = str(route.get("ward_id") or "")
        mapped = {
            "id": str(route.get("id") or ""),
            "name": route.get("route_name") or "",
            "type": "primary",
            "zone_id": route_zone_id,
            "ward_id": route_ward_id,
            "polyline_coordinates": route.get("polyline_coordinates") or [],
            "status": "active",
            "active": True,
        }

        if ward_id is not None and mapped["ward_id"] != str(ward_id):
            continue
        if zone_id is not None and mapped["zone_id"] != str(zone_id):
            continue

        compat_items.append(mapped)

    if ui_compat:
        return compat_items

    # Non-compat mode with zone/ward filters keeps existing paged envelope while applying filters.
    return PageResponse(items=compat_items, page=page, page_size=page_size, total=len(compat_items))


@router.post("/routes")
async def create_route(
    payload: RouteIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = RouteRepository(session)
    row = await repo.create(
        route_name=payload.route_name,
        zone_id=payload.zone_id,
        ward_id=payload.ward_id,
        polyline_coordinates=payload.polyline_coordinates,
    )
    return _to_dict(row)


@router.get("/routes/{route_id}")
async def get_route(
    route_id: UUID,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = RouteRepository(session)
    row = await _fetch_or_404(repo.get_by_id, "route", route_id)
    return _to_dict(row)


@router.put("/routes/{route_id}")
async def update_route(
    route_id: UUID,
    payload: RouteIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = RouteRepository(session)
    try:
        row = await repo.update(
            route_id,
            route_name=payload.route_name,
            zone_id=payload.zone_id,
            ward_id=payload.ward_id,
            polyline_coordinates=payload.polyline_coordinates,
        )
    except NoResultFound:
        _raise_not_found("route", route_id)
    return _to_dict(row)


@router.delete("/routes/{route_id}", response_model=MessageResponse)
async def delete_route(
    route_id: UUID,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    repo = RouteRepository(session)
    try:
        await repo.delete(route_id)
    except NoResultFound:
        _raise_not_found("route", route_id)
    return MessageResponse(message="deleted")


@router.post("/routes/import")
async def bulk_import_routes(
    file: UploadFile = File(...),
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    content = (await file.read()).decode("utf-8")
    rows = _parse_csv_with_required(content, required_columns={"route_name", "zone_id", "ward_id", "polyline_coordinates"})
    repo = RouteRepository(session)
    payloads: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        payloads.append(
            {
                "route_name": row["route_name"],
                "zone_id": _parse_import_uuid(row.get("zone_id"), field="zone_id", row_number=index),
                "ward_id": _parse_import_uuid(row.get("ward_id"), field="ward_id", row_number=index),
                "polyline_coordinates": json.loads(row.get("polyline_coordinates") or "[]"),
            }
        )
    created = await repo.bulk_create(payloads)
    return {"created": len(created)}


@router.get("/geofences", response_model=PageResponse)
async def list_geofences(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    geofence_for: str | None = Query(default=None),
    ward_id: UUID | None = Query(default=None),
    zone_id: UUID | None = Query(default=None),
    route_id: UUID | None = Query(default=None),
    type: str | None = Query(default=None),  # noqa: A002
    geometry_type: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse:
    filters: dict[str, Any] = {
        "active": active,
        "type": type,
        "geometry_type": geometry_type,
        "geofence_for": geofence_for,
        "zone_id": zone_id,
        "ward_id": ward_id,
        "route_id": route_id,
    }

    return await _list_entities(
        session,
        GeofenceORM,
        page=page,
        page_size=page_size,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
        filters=filters,
    )


@router.post("/geofences")
async def create_geofence(
    payload: GeofenceIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = GeofenceRepository(session)
    if payload.geofence_for in {"ward", "route"} and payload.ward_id is None:
        raise HTTPException(status_code=422, detail="ward_id is required for ward/route geofence")
    if payload.geofence_for == "route" and payload.route_id is None:
        raise HTTPException(status_code=422, detail="route_id is required for route geofence")

    create_kwargs: dict[str, Any] = {
        "geofence_code": payload.geofence_code,
        "geofence_name": payload.geofence_name,
        "type": payload.type,
        "geometry_type": payload.geometry_type,
        "center_lat": payload.center_lat,
        "center_lng": payload.center_lng,
        "radius_meter": payload.radius_meter,
        "geofence_for": payload.geofence_for,
        "zone_id": payload.zone_id,
        "ward_id": payload.ward_id,
        "route_id": payload.route_id,
        "scope_type": "zone" if payload.geofence_for == "zone" else "ward",
        "scope_id": payload.zone_id if payload.geofence_for == "zone" else payload.ward_id,
        "active": payload.active,
    }
    if payload.polygon is not None:
        create_kwargs["polygon"] = payload.polygon
    row = await repo.create(**create_kwargs)
    return _to_dict(row)


@router.get("/geofences/{geofence_id}")
async def get_geofence(
    geofence_id: UUID,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = GeofenceRepository(session)
    row = await _fetch_or_404(repo.get_by_id, "geofence", geofence_id)
    return _to_dict(row)


@router.put("/geofences/{geofence_id}")
async def update_geofence(
    geofence_id: UUID,
    payload: GeofenceIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    if payload.geofence_for in {"ward", "route"} and payload.ward_id is None:
        raise HTTPException(status_code=422, detail="ward_id is required for ward/route geofence")
    if payload.geofence_for == "route" and payload.route_id is None:
        raise HTTPException(status_code=422, detail="route_id is required for route geofence")

    repo = GeofenceRepository(session)
    try:
        update_kwargs: dict[str, Any] = {
            "geofence_code": payload.geofence_code,
            "geofence_name": payload.geofence_name,
            "type": payload.type,
            "geometry_type": payload.geometry_type,
            "center_lat": payload.center_lat,
            "center_lng": payload.center_lng,
            "radius_meter": payload.radius_meter,
            "geofence_for": payload.geofence_for,
            "zone_id": payload.zone_id,
            "ward_id": payload.ward_id,
            "route_id": payload.route_id,
            "scope_type": "zone" if payload.geofence_for == "zone" else "ward",
            "scope_id": payload.zone_id if payload.geofence_for == "zone" else payload.ward_id,
            "active": payload.active,
        }
        if payload.polygon is not None:
            update_kwargs["polygon"] = payload.polygon
        row = await repo.update(geofence_id, **update_kwargs)
    except NoResultFound:
        _raise_not_found("geofence", geofence_id)
    return _to_dict(row)


@router.delete("/geofences/{geofence_id}", response_model=MessageResponse)
async def delete_geofence(
    geofence_id: UUID,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    repo = GeofenceRepository(session)
    try:
        await repo.delete(geofence_id)
    except NoResultFound:
        _raise_not_found("geofence", geofence_id)
    return MessageResponse(message="deleted")


@router.post("/geofences/import")
async def bulk_import_geofences(
    file: UploadFile = File(...),
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    content = (await file.read()).decode("utf-8")
    rows = _parse_csv_with_required(
        content,
        required_columns={"geofence_code", "geofence_name", "type", "geometry_type", "geofence_for", "zone_id", "coordinates"},
    )
    repo = GeofenceRepository(session)
    payloads: list[dict[str, Any]] = []

    def _parse_coordinates_polygon(raw: str, *, row_number: int) -> dict[str, Any]:
        chunks = [part.strip() for part in raw.split(";") if part.strip()]
        points: list[list[float]] = []
        for chunk in chunks:
            pair = [token.strip() for token in chunk.split(",")]
            if len(pair) != 2:
                raise HTTPException(status_code=400, detail=f"invalid coordinates at row {row_number}")
            try:
                lat = float(pair[0])
                lng = float(pair[1])
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"invalid coordinates at row {row_number}") from exc
            points.append([lng, lat])
        if len(points) < 3:
            raise HTTPException(status_code=400, detail=f"coordinates must include at least 3 points at row {row_number}")
        if points[0] != points[-1]:
            points.append(points[0])
        return {"type": "Polygon", "coordinates": [points]}

    for index, row in enumerate(rows, start=2):
        geofence_for = (row.get("geofence_for") or "").strip().lower()
        if geofence_for not in {"zone", "ward", "route"}:
            raise HTTPException(status_code=400, detail=f"invalid geofence_for at row {index}")
        zone_id = _parse_import_uuid(row.get("zone_id"), field="zone_id", row_number=index, required=True)
        ward_id = _parse_import_uuid(row.get("ward_id"), field="ward_id", row_number=index, required=geofence_for != "zone")
        route_id = _parse_import_uuid(row.get("route_id"), field="route_id", row_number=index, required=geofence_for == "route")
        coordinates_raw = (row.get("coordinates") or "").strip()
        payloads.append(
            {
                "geofence_code": row["geofence_code"],
                "geofence_name": row["geofence_name"],
                "type": row["type"],
                "geometry_type": row["geometry_type"],
                "center_lat": _parse_import_float(row.get("center_lat"), field="center_lat", row_number=index, default=None),
                "center_lng": _parse_import_float(row.get("center_lng"), field="center_lng", row_number=index, default=None),
                "radius_meter": _parse_import_float(
                    row.get("radius_meter"), field="radius_meter", row_number=index, default=None
                ),
                "geofence_for": geofence_for,
                "zone_id": zone_id,
                "ward_id": ward_id,
                "route_id": route_id,
                "scope_type": "zone" if geofence_for == "zone" else "ward",
                "scope_id": zone_id if geofence_for == "zone" else ward_id,
                "polygon": _parse_coordinates_polygon(coordinates_raw, row_number=index) if coordinates_raw else None,
                "active": _parse_bool(row.get("active"), default=True),
            }
        )
    created = await repo.bulk_create(payloads)
    return {"created": len(created)}


@router.get("/wards", response_model=PageResponse)
async def list_wards(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    zone_name: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse:
    return await _list_entities(
        session,
        WardORM,
        page=page,
        page_size=page_size,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
        filters={"active": active, "zone_name": zone_name},
    )


@router.post("/wards")
async def create_ward(
    payload: WardIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = WardRepository(session)
    zone_id = await _resolve_zone_id(session, payload.zone_name)
    row = await repo.create(
        ward_code=payload.ward_code,
        ward_name=payload.ward_name,
        zone_id=zone_id,
        active=payload.active,
    )
    return _to_dict(row)


@router.get("/wards/{ward_id}")
async def get_ward(
    ward_id: UUID,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = WardRepository(session)
    row = await _fetch_or_404(repo.get_by_id, "ward", ward_id)
    return _to_dict(row)


@router.put("/wards/{ward_id}")
async def update_ward(
    ward_id: UUID,
    payload: WardIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = WardRepository(session)
    zone_id = await _resolve_zone_id(session, payload.zone_name)
    try:
        row = await repo.update(
            ward_id,
            ward_code=payload.ward_code,
            ward_name=payload.ward_name,
            zone_id=zone_id,
            active=payload.active,
        )
    except NoResultFound:
        _raise_not_found("ward", ward_id)
    return _to_dict(row)


@router.delete("/wards/{ward_id}", response_model=MessageResponse)
async def delete_ward(
    ward_id: UUID,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    repo = WardRepository(session)
    try:
        await repo.delete(ward_id)
    except NoResultFound:
        _raise_not_found("ward", ward_id)
    return MessageResponse(message="deleted")


@router.post("/wards/import")
async def bulk_import_wards(
    file: UploadFile = File(...),
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    content = (await file.read()).decode("utf-8")
    rows = _parse_csv_with_required(content, required_columns={"ward_code", "ward_name", "zone_name"})
    repo = WardRepository(session)
    payloads: list[dict[str, Any]] = []
    for row in rows:
        zone_id = await _resolve_zone_id(session, row["zone_name"])
        payloads.append(
            {
                "ward_code": row["ward_code"],
                "ward_name": row["ward_name"],
                "zone_id": zone_id,
                "active": _parse_bool(row.get("active"), default=True),
            }
        )
    created = await repo.bulk_create(payloads)
    return {"created": len(created)}


@router.post("/device-assignments")
async def assign_device(
    payload: DeviceAssignmentIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    svc = DeviceVehicleAssignmentService(DeviceVehicleAssignmentRepository(session))
    row = await svc.assign(
        AssignmentCreateInput(
            device_id=payload.device_id,
            vehicle_id=payload.vehicle_id,
            assigned_from=payload.assigned_from,
            remarks=payload.remarks,
        )
    )
    return _to_dict(row)


@router.get("/device-assignments/{device_id}")
async def get_active_assignment_by_device(
    device_id: UUID,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = DeviceVehicleAssignmentRepository(session)
    row = await repo.get_active_by_device(device_id)
    if row is None:
        _raise_not_found("device assignment", device_id)
    return _to_dict(row)


@router.put("/device-assignments/{device_id}")
async def reassign_device(
    device_id: UUID,
    vehicle_id: UUID = Query(...),
    remarks: str | None = Query(default=None),
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    svc = DeviceVehicleAssignmentService(DeviceVehicleAssignmentRepository(session))
    row = await svc.assign(
        AssignmentCreateInput(
            device_id=device_id,
            vehicle_id=vehicle_id,
            remarks=remarks,
        )
    )
    return _to_dict(row)


@router.delete("/device-assignments/{device_id}", response_model=MessageResponse)
async def unassign_device(
    device_id: UUID,
    remarks: str | None = Query(default=None),
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    svc = DeviceVehicleAssignmentService(DeviceVehicleAssignmentRepository(session))
    row = await svc.unassign_device(device_id, remarks=remarks)
    if row is None:
        _raise_not_found("device assignment", device_id)
    return MessageResponse(message="deleted")


@router.get("/device-assignments", response_model=PageResponse)
async def list_device_assignments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    device_id: UUID | None = Query(default=None),
    vehicle_id: UUID | None = Query(default=None),
    active: bool | None = Query(default=None),
    sort_by: str = Query(default="assigned_from"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse:
    return await _list_entities(
        session,
        DeviceVehicleAssignmentORM,
        page=page,
        page_size=page_size,
        q=None,
        sort_by=sort_by,
        sort_order=sort_order,
        filters={"device_id": device_id, "vehicle_id": vehicle_id, "active": active},
    )


@router.post("/device-assignments/import")
async def bulk_import_device_assignments(
    file: UploadFile = File(...),
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    content = (await file.read()).decode("utf-8")
    rows = _parse_csv_with_required(content, required_columns={"device_id", "vehicle_id"})
    svc = DeviceVehicleAssignmentService(DeviceVehicleAssignmentRepository(session))
    created = 0
    for index, row in enumerate(rows, start=2):
        await svc.assign(
            AssignmentCreateInput(
                device_id=_parse_import_uuid(row.get("device_id"), field="device_id", row_number=index),
                vehicle_id=_parse_import_uuid(row.get("vehicle_id"), field="vehicle_id", row_number=index),
                assigned_from=_parse_import_datetime(row.get("assigned_from"), field="assigned_from", row_number=index),
                remarks=row.get("remarks") or None,
            )
        )
        created += 1
    return {"created": created}
