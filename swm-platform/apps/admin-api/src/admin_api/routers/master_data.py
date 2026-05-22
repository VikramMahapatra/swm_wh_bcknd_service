from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from swm_db import (
    AssignmentCreateInput,
    ContractorORM,
    ContractorRepository,
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


class VendorIn(BaseModel):
    vendor_code: str
    vendor_name: str
    contact_person: str | None = None
    email: str | None = None
    phone: str | None = None
    webhook_secret: str | None = None
    signature_key: str | None = None
    allowed_ips: list[str] = Field(default_factory=list)
    auth_type: str = "header"
    callback_format: dict[str, Any] = Field(default_factory=dict)
    active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeviceIn(BaseModel):
    vendor_id: UUID
    imei: str
    serial_no: str | None = None
    model: str | None = None
    manufacturer: str | None = None
    firmware_version: str | None = None
    sim_number: str | None = None
    installed_on: datetime | None = None
    activated_on: datetime | None = None
    last_seen: datetime | None = None
    battery_percent: float | None = None
    signal_strength: float | None = None
    health_status: str = "healthy"
    active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class VehicleIn(BaseModel):
    vehicle_number: str
    registration_number: str
    contractor_id: UUID
    ward_id: UUID
    route_id: UUID | None = None
    truck_type: str | None = None
    capacity_kg: float = 0
    capacity_cubic_meter: float = 0
    fuel_type: str = "diesel"
    operational_status: str = "operational"
    chassis_number: str | None = None
    engine_number: str | None = None
    manufacture_year: int | None = None
    active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContractorIn(BaseModel):
    contractor_code: str
    contractor_name: str
    contact: str | None = None
    sla_details: dict[str, Any] = Field(default_factory=dict)
    active: bool = True


class WardIn(BaseModel):
    ward_code: str
    ward_name: str
    zone_name: str
    active: bool = True


class RouteIn(BaseModel):
    route_code: str
    route_name: str
    expected_distance_km: float = 0
    expected_duration_min: int = 0
    start_point: str
    end_point: str
    active: bool = True


class GeofenceIn(BaseModel):
    geofence_code: str
    geofence_name: str
    type: str
    geometry_type: str
    center_lat: float | None = None
    center_lng: float | None = None
    radius_meter: float | None = None
    polygon: dict[str, Any] | None = None
    ward_id: UUID | None = None
    active: bool = True


class DeviceAssignmentIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    device_id: UUID
    vehicle_id: UUID
    assigned_from: datetime | None = None
    assigned_to: datetime | None = None
    active: bool = True
    remarks: str | None = None


@router.get("/vendors", response_model=PageResponse)
async def list_vendors(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    auth_type: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse:
    return await _list_entities(
        session,
        VendorORM,
        page=page,
        page_size=page_size,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
        filters={"active": active, "auth_type": auth_type},
    )


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
    created = await repo.bulk_create(
        [
            {
                "vendor_id": UUID(r["vendor_id"]),
                "imei": r["imei"],
                "serial_no": r.get("serial_no") or None,
                "model": r.get("model") or None,
                "manufacturer": r.get("manufacturer") or None,
                "firmware_version": r.get("firmware_version") or None,
                "sim_number": r.get("sim_number") or None,
                "health_status": r.get("health_status") or "healthy",
                "active": _parse_bool(r.get("active"), default=True),
                "metadata_json": {},
            }
            for r in rows
        ]
    )
    return {"created": len(created)}


@router.get("/vehicles", response_model=PageResponse)
async def list_vehicles(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    contractor_id: UUID | None = Query(default=None),
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
            "contractor_id": contractor_id,
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
        contractor_id=payload.contractor_id,
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
            contractor_id=payload.contractor_id,
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
        required_columns={"vehicle_number", "registration_number", "contractor_id", "ward_id"},
    )
    repo = VehicleRepository(session)
    created = await repo.bulk_create(
        [
            {
                "vehicle_number": r["vehicle_number"],
                "registration_number": r["registration_number"],
                "contractor_id": UUID(r["contractor_id"]),
                "ward_id": UUID(r["ward_id"]),
                "route_id": _parse_uuid(r.get("route_id")),
                "truck_type": r.get("truck_type") or None,
                "capacity_kg": float(r.get("capacity_kg") or 0),
                "capacity_cubic_meter": float(r.get("capacity_cubic_meter") or 0),
                "fuel_type": r.get("fuel_type") or "diesel",
                "operational_status": r.get("operational_status") or "operational",
                "chassis_number": r.get("chassis_number") or None,
                "engine_number": r.get("engine_number") or None,
                "manufacture_year": int(r["manufacture_year"]) if r.get("manufacture_year") else None,
                "active": _parse_bool(r.get("active"), default=True),
                "metadata_json": {},
            }
            for r in rows
        ]
    )
    return {"created": len(created)}


@router.get("/routes", response_model=PageResponse)
async def list_routes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse:
    return await _list_entities(
        session,
        RouteORM,
        page=page,
        page_size=page_size,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
        filters={"active": active},
    )


@router.post("/routes")
async def create_route(
    payload: RouteIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = RouteRepository(session)
    row = await repo.create(
        route_code=payload.route_code,
        route_name=payload.route_name,
        expected_distance_km=payload.expected_distance_km,
        expected_duration_min=payload.expected_duration_min,
        start_point=payload.start_point,
        end_point=payload.end_point,
        active=payload.active,
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
            route_code=payload.route_code,
            route_name=payload.route_name,
            expected_distance_km=payload.expected_distance_km,
            expected_duration_min=payload.expected_duration_min,
            start_point=payload.start_point,
            end_point=payload.end_point,
            active=payload.active,
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
    rows = _parse_csv_with_required(content, required_columns={"route_code", "route_name", "start_point", "end_point"})
    repo = RouteRepository(session)
    created = await repo.bulk_create(
        [
            {
                "route_code": r["route_code"],
                "route_name": r["route_name"],
                "expected_distance_km": float(r.get("expected_distance_km") or 0),
                "expected_duration_min": int(r.get("expected_duration_min") or 0),
                "start_point": r["start_point"],
                "end_point": r["end_point"],
                "active": _parse_bool(r.get("active"), default=True),
            }
            for r in rows
        ]
    )
    return {"created": len(created)}


@router.get("/geofences", response_model=PageResponse)
async def list_geofences(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    ward_id: UUID | None = Query(default=None),
    type: str | None = Query(default=None),  # noqa: A002
    geometry_type: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse:
    return await _list_entities(
        session,
        GeofenceORM,
        page=page,
        page_size=page_size,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
        filters={"active": active, "ward_id": ward_id, "type": type, "geometry_type": geometry_type},
    )


@router.post("/geofences")
async def create_geofence(
    payload: GeofenceIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = GeofenceRepository(session)
    create_kwargs: dict[str, Any] = {
        "geofence_code": payload.geofence_code,
        "geofence_name": payload.geofence_name,
        "type": payload.type,
        "geometry_type": payload.geometry_type,
        "center_lat": payload.center_lat,
        "center_lng": payload.center_lng,
        "radius_meter": payload.radius_meter,
        "ward_id": payload.ward_id,
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
            "ward_id": payload.ward_id,
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
        required_columns={"geofence_code", "geofence_name", "type", "geometry_type"},
    )
    repo = GeofenceRepository(session)
    created = await repo.bulk_create(
        [
            {
                "geofence_code": r["geofence_code"],
                "geofence_name": r["geofence_name"],
                "type": r["type"],
                "geometry_type": r["geometry_type"],
                "center_lat": float(r["center_lat"]) if r.get("center_lat") else None,
                "center_lng": float(r["center_lng"]) if r.get("center_lng") else None,
                "radius_meter": float(r["radius_meter"]) if r.get("radius_meter") else None,
                "ward_id": _parse_uuid(r.get("ward_id")),
                "active": _parse_bool(r.get("active"), default=True),
            }
            for r in rows
        ]
    )
    return {"created": len(created)}


@router.get("/contractors", response_model=PageResponse)
async def list_contractors(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> PageResponse:
    return await _list_entities(
        session,
        ContractorORM,
        page=page,
        page_size=page_size,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
        filters={"active": active},
    )


@router.post("/contractors")
async def create_contractor(
    payload: ContractorIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = ContractorRepository(session)
    row = await repo.create(
        contractor_code=payload.contractor_code,
        contractor_name=payload.contractor_name,
        contact=payload.contact,
        sla_details=payload.sla_details,
        active=payload.active,
    )
    return _to_dict(row)


@router.get("/contractors/{contractor_id}")
async def get_contractor(
    contractor_id: UUID,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = ContractorRepository(session)
    row = await _fetch_or_404(repo.get_by_id, "contractor", contractor_id)
    return _to_dict(row)


@router.put("/contractors/{contractor_id}")
async def update_contractor(
    contractor_id: UUID,
    payload: ContractorIn,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = ContractorRepository(session)
    try:
        row = await repo.update(
            contractor_id,
            contractor_code=payload.contractor_code,
            contractor_name=payload.contractor_name,
            contact=payload.contact,
            sla_details=payload.sla_details,
            active=payload.active,
        )
    except NoResultFound:
        _raise_not_found("contractor", contractor_id)
    return _to_dict(row)


@router.delete("/contractors/{contractor_id}", response_model=MessageResponse)
async def delete_contractor(
    contractor_id: UUID,
    _: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    repo = ContractorRepository(session)
    try:
        await repo.delete(contractor_id)
    except NoResultFound:
        _raise_not_found("contractor", contractor_id)
    return MessageResponse(message="deleted")


@router.post("/contractors/import")
async def bulk_import_contractors(
    file: UploadFile = File(...),
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    content = (await file.read()).decode("utf-8")
    rows = _parse_csv_with_required(content, required_columns={"contractor_code", "contractor_name"})
    repo = ContractorRepository(session)
    created = await repo.bulk_create(
        [
            {
                "contractor_code": r["contractor_code"],
                "contractor_name": r["contractor_name"],
                "contact": r.get("contact") or None,
                "sla_details": {},
                "active": _parse_bool(r.get("active"), default=True),
            }
            for r in rows
        ]
    )
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
    row = await repo.create(
        ward_code=payload.ward_code,
        ward_name=payload.ward_name,
        zone_name=payload.zone_name,
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
    try:
        row = await repo.update(
            ward_id,
            ward_code=payload.ward_code,
            ward_name=payload.ward_name,
            zone_name=payload.zone_name,
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
    created = await repo.bulk_create(
        [
            {
                "ward_code": r["ward_code"],
                "ward_name": r["ward_name"],
                "zone_name": r["zone_name"],
                "active": _parse_bool(r.get("active"), default=True),
            }
            for r in rows
        ]
    )
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
    for row in rows:
        await svc.assign(
            AssignmentCreateInput(
                device_id=UUID(row["device_id"]),
                vehicle_id=UUID(row["vehicle_id"]),
                assigned_from=datetime.fromisoformat(row["assigned_from"])
                if row.get("assigned_from")
                else None,
                remarks=row.get("remarks") or None,
            )
        )
        created += 1
    return {"created": created}
