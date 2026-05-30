from __future__ import annotations

import math
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from datetime import timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import String, and_, case, cast, func, or_, select
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession
from swm_db import (
    AlertORM,
    AnalyticsDailyKPIORM,
    AnalyticsGeofenceEventORM,
    AnalyticsOverspeedEventORM,
    AuthUserORM,
    DeviceEventORM,
    DeviceORM,
    DeviceVehicleAssignmentORM,
    DriverORM,
    GtcCheckpointORM,
    PickupPointCrossingORM,
    PickupPointORM,
    RouteORM,
    TicketCommentORM,
    TicketORM,
    VehicleORM,
    VendorORM,
    WardORM,
    ZoneORM,
    get_db_session,
)
from swm_common import get_settings

from admin_api.api_support import RoleContext, _to_dict, get_role_context, require_roles
from admin_api.routers import auth as auth_router
from admin_api.routers import realtime as realtime_router

router = APIRouter(tags=["compatibility"])


# --- Social endpoints compatibility ---
@router.get("/social-media/twitter-mentions")
async def get_twitter_mentions(
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
):
    """
    TODO: Implement fetching twitter mentions for dashboard/social panel.
    Should return a list of mentions with id, text, author, created_at, status, etc.
    """
    return {"items": [], "total": 0}


@router.get("/social-media/twitter-mentions/statistics/summary")
async def get_twitter_mentions_summary(
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
):
    """
    TODO: Implement summary stats for twitter mentions (counts by status, etc).
    """
    return {"total": 0, "responded": 0, "pending": 0}


from fastapi import Body
@router.put("/social-media/twitter-mentions/{mention_id}/respond")
async def respond_twitter_mention(
    mention_id: str,
    payload: dict = Body(...),
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
):
    """
    TODO: Implement respond/update logic for a twitter mention.
    Should update status/response and return updated mention.
    """
    return {"id": mention_id, "status": "responded"}


# --- Collection ton today endpoint compatibility ---

@router.get("/collection-ton-today")
async def get_collection_ton_today(
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Returns today's collection tonnage by zone and vehicle.
    Output: { items: [{zone, vehicle, weight}], total: float }
    """
    today = datetime.now(timezone.utc).date()
    result = await session.execute(
        select(
            ZoneORM.zone_name,
            VehicleORM.vehicle_number,
            func.sum(AnalyticsDailyKPIORM.distance_km).label("weight"),
        )
        .select_from(AnalyticsDailyKPIORM)
        .join(
            VehicleORM,
            or_(
                cast(VehicleORM.id, String) == AnalyticsDailyKPIORM.vehicle_id,
                VehicleORM.vehicle_number == AnalyticsDailyKPIORM.vehicle_id,
            ),
        )
        .join(WardORM, VehicleORM.ward_id == WardORM.id)
        .join(ZoneORM, WardORM.zone_id == ZoneORM.id)
        .where(AnalyticsDailyKPIORM.metric_date == today)
        .group_by(ZoneORM.zone_name, VehicleORM.vehicle_number)
        .order_by(ZoneORM.zone_name.asc(), VehicleORM.vehicle_number.asc())
    )
    rows = result.fetchall()
    items = [
        {"zone": zone, "vehicle": vehicle, "weight": float(weight or 0.0)}
        for zone, vehicle, weight in rows
    ]
    total = float(sum(item["weight"] for item in items))
    return {"items": items, "total": total}


class LoginJsonRequest(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "user"


class AssignRouteRequest(BaseModel):
    assigned_route_id: str


class GtcCheckpointCreateRequest(BaseModel):
    truck_id: str
    arrived_at: str | None = None
    is_dry: bool = False
    is_wet: bool = False
    is_metal: bool = False
    is_plastic: bool = False
    is_sanitary: bool = False
    truck_cleanliness_score: float | None = None
    gtc_cleanliness_score: float | None = None
    remarks: str | None = None


class DriverCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str = Field(min_length=1)
    phone: str | None = None
    license_number: str | None = Field(default=None, validation_alias=AliasChoices("license_number", "licenseNumber"))
    license_expiry: str | None = Field(default=None, validation_alias=AliasChoices("license_expiry", "licenseExpiry"))
    vendor_id: str | None = Field(default=None, validation_alias=AliasChoices("vendor_id", "vendorId"))
    assigned_truck_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("assigned_truck_id", "assignedTruckId", "assigned_vehicle_id"),
    )
    status: str | None = None
    active: bool | None = None
    email: str | None = None
    address: str | None = None
    emergency_contact: str | None = Field(default=None, validation_alias=AliasChoices("emergency_contact", "emergencyContact"))
    join_date: str | None = Field(default=None, validation_alias=AliasChoices("join_date", "joinDate"))

    @field_validator("vendor_id", "assigned_truck_id", mode="before")
    @classmethod
    def validate_optional_uuid_fields(cls, value: str | None) -> str | None:
        return _validate_optional_uuid_string(value)


class DriverUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str | None = None
    phone: str | None = None
    license_number: str | None = Field(default=None, validation_alias=AliasChoices("license_number", "licenseNumber"))
    license_expiry: str | None = Field(default=None, validation_alias=AliasChoices("license_expiry", "licenseExpiry"))
    vendor_id: str | None = Field(default=None, validation_alias=AliasChoices("vendor_id", "vendorId"))
    assigned_truck_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("assigned_truck_id", "assignedTruckId", "assigned_vehicle_id"),
    )
    status: str | None = None
    active: bool | None = None
    email: str | None = None
    address: str | None = None
    emergency_contact: str | None = Field(default=None, validation_alias=AliasChoices("emergency_contact", "emergencyContact"))
    join_date: str | None = Field(default=None, validation_alias=AliasChoices("join_date", "joinDate"))

    @field_validator("vendor_id", "assigned_truck_id", mode="before")
    @classmethod
    def validate_optional_uuid_fields(cls, value: str | None) -> str | None:
        return _validate_optional_uuid_string(value)


class PickupCoordinate(BaseModel):
    sequence_no: int | None = Field(default=None, validation_alias=AliasChoices("sequence_no", "sequenceNo", "order"))
    lat: float = Field(validation_alias=AliasChoices("lat", "latitude"))
    lng: float = Field(validation_alias=AliasChoices("lng", "longitude"))
    pickup_name: str | None = Field(default=None, validation_alias=AliasChoices("pickup_name", "pickupName", "name"))
    expected_pickup_time: str | None = Field(
        default=None,
        validation_alias=AliasChoices("expected_pickup_time", "expectedPickupTime", "pickup_times", "pickupTimes"),
    )
    pickup_radius_m: float | None = Field(default=None, validation_alias=AliasChoices("pickup_radius_m", "pickupRadiusM", "radius_m", "radiusM"))


class PickupPointCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    pickup_name: str | None = Field(default=None, validation_alias=AliasChoices("pickup_name", "pickupName", "name"))
    zone_id: str = Field(validation_alias=AliasChoices("zone_id", "zoneId"))
    ward_id: str = Field(validation_alias=AliasChoices("ward_id", "wardId"))
    route_id: str = Field(validation_alias=AliasChoices("route_id", "routeId"))
    sequence_no: int | None = Field(default=None, validation_alias=AliasChoices("sequence_no", "sequenceNo", "order"))
    lat: float | None = Field(default=None, validation_alias=AliasChoices("lat", "latitude"))
    lng: float | None = Field(default=None, validation_alias=AliasChoices("lng", "longitude"))
    expected_pickup_time: str | None = Field(
        default=None,
        validation_alias=AliasChoices("expected_pickup_time", "expectedPickupTime", "pickup_times", "pickupTimes"),
    )
    pickup_radius_m: float | None = Field(default=None, validation_alias=AliasChoices("pickup_radius_m", "pickupRadiusM", "radius_m", "radiusM"))
    pickup_points: list[PickupCoordinate] = Field(default_factory=list, validation_alias=AliasChoices("pickup_points", "pickupPoints", "points"))

    @field_validator("zone_id", "ward_id", "route_id", mode="before")
    @classmethod
    def validate_uuid_fields(cls, value: str | None) -> str | None:
        parsed = _validate_optional_uuid_string(value)
        if parsed is None:
            raise ValueError("zone_id, ward_id and route_id are required")
        return parsed


class PickupPointUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    pickup_name: str | None = Field(default=None, validation_alias=AliasChoices("pickup_name", "pickupName", "name"))
    zone_id: str | None = Field(default=None, validation_alias=AliasChoices("zone_id", "zoneId"))
    ward_id: str | None = Field(default=None, validation_alias=AliasChoices("ward_id", "wardId"))
    route_id: str | None = Field(default=None, validation_alias=AliasChoices("route_id", "routeId"))
    sequence_no: int | None = Field(default=None, validation_alias=AliasChoices("sequence_no", "sequenceNo", "order"))
    lat: float | None = Field(default=None, validation_alias=AliasChoices("lat", "latitude"))
    lng: float | None = Field(default=None, validation_alias=AliasChoices("lng", "longitude"))
    expected_pickup_time: str | None = Field(
        default=None,
        validation_alias=AliasChoices("expected_pickup_time", "expectedPickupTime", "pickup_times", "pickupTimes"),
    )
    pickup_radius_m: float | None = Field(default=None, validation_alias=AliasChoices("pickup_radius_m", "pickupRadiusM", "radius_m", "radiusM"))

    @field_validator("zone_id", "ward_id", "route_id", mode="before")
    @classmethod
    def validate_optional_uuid_fields(cls, value: str | None) -> str | None:
        return _validate_optional_uuid_string(value)


TicketStatus = Literal["open", "in_progress", "pending", "resolved", "closed"]
TicketPriority = Literal["low", "medium", "high", "critical"]
TicketCategory = Literal[
    "complaint",
    "maintenance",
    "driver_issue",
    "vehicle_issue",
    "route_issue",
    "pickup_issue",
    "other",
]


class TicketCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    title: str = Field(min_length=1)
    description: str | None = None
    category: TicketCategory = "complaint"
    priority: TicketPriority = "medium"
    status: TicketStatus = "open"
    due_date: str | None = Field(default=None, validation_alias=AliasChoices("due_date", "dueDate"))
    assigned_to: str | None = Field(default=None, validation_alias=AliasChoices("assigned_to", "assignedTo"))
    created_by: str | None = Field(default=None, validation_alias=AliasChoices("created_by", "createdBy"))
    related_alert_id: str | None = Field(default=None, validation_alias=AliasChoices("related_alert_id", "relatedAlertId"))
    related_truck_id: str | None = Field(default=None, validation_alias=AliasChoices("related_truck_id", "relatedTruckId"))
    related_driver_id: str | None = Field(default=None, validation_alias=AliasChoices("related_driver_id", "relatedDriverId"))
    escalation_level: int = Field(default=0, validation_alias=AliasChoices("escalation_level", "escalationLevel"))
    sla_breached: bool = Field(default=False, validation_alias=AliasChoices("sla_breached", "slaBreached"))


class TicketUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    title: str | None = None
    description: str | None = None
    category: TicketCategory | None = None
    priority: TicketPriority | None = None
    status: TicketStatus | None = None
    due_date: str | None = Field(default=None, validation_alias=AliasChoices("due_date", "dueDate"))
    assigned_to: str | None = Field(default=None, validation_alias=AliasChoices("assigned_to", "assignedTo"))
    created_by: str | None = Field(default=None, validation_alias=AliasChoices("created_by", "createdBy"))
    related_alert_id: str | None = Field(default=None, validation_alias=AliasChoices("related_alert_id", "relatedAlertId"))
    related_truck_id: str | None = Field(default=None, validation_alias=AliasChoices("related_truck_id", "relatedTruckId"))
    related_driver_id: str | None = Field(default=None, validation_alias=AliasChoices("related_driver_id", "relatedDriverId"))
    escalation_level: int | None = Field(default=None, validation_alias=AliasChoices("escalation_level", "escalationLevel"))
    sla_breached: bool | None = Field(default=None, validation_alias=AliasChoices("sla_breached", "slaBreached"))


class TicketCommentCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    comment: str | None = None
    content: str | None = None
    author: str | None = None
    is_internal: bool = Field(default=False, validation_alias=AliasChoices("is_internal", "isInternal"))


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def _parse_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _validate_optional_uuid_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if normalized == "":
        return None
    try:
        UUID(normalized)
    except ValueError as exc:
        raise ValueError("must be a valid UUID") from exc
    return normalized


def _resolve_active(*, status: str | None, active: bool | None, default: bool = True) -> bool:
    if active is not None:
        return active
    if status is None:
        return default
    return status.strip().lower() not in {"inactive", "disabled"}


def _driver_to_dict(row: DriverORM) -> dict:
    metadata = dict(row.metadata_json) if isinstance(row.metadata_json, dict) else {}
    license_expiry = row.license_expiry.isoformat() if row.license_expiry is not None else None
    assigned_truck_id = str(row.assigned_vehicle_id) if row.assigned_vehicle_id is not None else None
    vendor_id = str(row.vendor_id) if row.vendor_id is not None else None
    status = str(metadata.get("status") or ("active" if row.active else "inactive"))
    return {
        "id": str(row.id),
        "name": row.name,
        "phone": row.phone,
        "email": metadata.get("email"),
        "address": metadata.get("address"),
        "emergency_contact": metadata.get("emergency_contact"),
        "emergencyContact": metadata.get("emergency_contact"),
        "join_date": metadata.get("join_date"),
        "joinDate": metadata.get("join_date"),
        "license_number": row.license_number,
        "licenseNumber": row.license_number,
        "license_expiry": license_expiry,
        "licenseExpiry": license_expiry,
        "vendor_id": vendor_id,
        "vendorId": vendor_id,
        "assigned_truck_id": assigned_truck_id,
        "assignedTruckId": assigned_truck_id,
        "status": status,
        "active": row.active,
    }


def _pickup_point_to_dict(row: PickupPointORM) -> dict:
    zone_id = str(row.zone_id) if row.zone_id is not None else None
    ward_id = str(row.ward_id) if row.ward_id is not None else None
    route_id = str(row.route_id) if row.route_id is not None else None
    return {
        "id": str(row.id),
        "pickup_name": row.pickup_name,
        "pickupName": row.pickup_name,
        "name": row.pickup_name or f"Pickup {row.sequence_no}",
        "zone_id": zone_id,
        "zoneId": zone_id,
        "ward_id": ward_id,
        "wardId": ward_id,
        "route_id": route_id,
        "routeId": route_id,
        "sequence_no": row.sequence_no,
        "sequenceNo": row.sequence_no,
        "order": row.sequence_no,
        "lat": row.lat,
        "lng": row.lng,
        "latitude": row.lat,
        "longitude": row.lng,
        "position": {"lat": row.lat, "lng": row.lng},
        "expected_pickup_time": row.expected_pickup_time,
        "expectedPickupTime": row.expected_pickup_time,
        "pickup_radius_m": row.pickup_radius_m,
        "pickupRadiusM": row.pickup_radius_m,
    }


def _ticket_comment_to_dict(row: TicketCommentORM) -> dict:
    return {
        "id": str(row.id),
        "ticket_id": str(row.ticket_id),
        "ticketId": str(row.ticket_id),
        "author": row.author,
        "content": row.content,
        "comment": row.content,
        "is_internal": row.is_internal,
        "isInternal": row.is_internal,
        "created_at": row.created_at.isoformat() if row.created_at is not None else None,
        "createdAt": row.created_at.isoformat() if row.created_at is not None else None,
    }


def _ticket_to_dict(row: TicketORM, comments: list[TicketCommentORM] | None = None) -> dict:
    comments_rows = comments or []
    due_date = row.due_at.isoformat() if row.due_at is not None else None
    created_at = row.created_at.isoformat() if row.created_at is not None else None
    updated_at = row.updated_at.isoformat() if row.updated_at is not None else None
    return {
        "id": str(row.id),
        "ticket_number": str(row.id),
        "title": row.title,
        "description": row.description,
        "category": row.category,
        "priority": row.priority,
        "status": row.status,
        "due_date": due_date,
        "dueDate": due_date,
        "assigned_to": row.assigned_to,
        "assignedTo": row.assigned_to,
        "created_by": row.created_by,
        "createdBy": row.created_by,
        "related_alert_id": row.related_alert_id,
        "relatedAlertId": row.related_alert_id,
        "related_truck_id": row.related_truck_id,
        "relatedTruckId": row.related_truck_id,
        "related_driver_id": row.related_driver_id,
        "relatedDriverId": row.related_driver_id,
        "escalation_level": row.escalation_level,
        "escalationLevel": row.escalation_level,
        "sla_breached": row.sla_breached,
        "slaBreached": row.sla_breached,
        "created_at": created_at,
        "createdAt": created_at,
        "updated_at": updated_at,
        "updatedAt": updated_at,
        "comments": [_ticket_comment_to_dict(comment) for comment in comments_rows],
    }


def _normalize_role(role: str) -> str:
    value = role.strip().lower()
    if value in {"admin"}:
        return "admin"
    if value in {"operator", "ops", "user"}:
        return "operator"
    if value in {"supervisor"}:
        return "supervisor"
    if value in {"fleet_manager", "fleet manager"}:
        return "fleet_manager"
    if value in {"analyst"}:
        return "analyst"
    return "read_only"


def _is_spare_vehicle(vehicle: VehicleORM) -> bool:
    truck_type = (vehicle.truck_type or "").strip().lower()
    op_status = (vehicle.operational_status or "").strip().lower()
    metadata = vehicle.metadata_json if isinstance(vehicle.metadata_json, dict) else {}
    return truck_type == "spare" or op_status == "spare" or bool(metadata.get("is_spare"))


async def _weekly_collection_trend(session: AsyncSession, *, days: int = 7) -> list[dict]:
    rows = (
        await session.execute(
            select(
                AnalyticsDailyKPIORM.metric_date,
                func.avg(AnalyticsDailyKPIORM.utilization_pct).label("avg_utilization_pct"),
                func.sum(AnalyticsDailyKPIORM.trips_count).label("trips_count"),
            )
            .group_by(AnalyticsDailyKPIORM.metric_date)
            .order_by(AnalyticsDailyKPIORM.metric_date.desc())
            .limit(days)
        )
    ).all()
    trend: list[dict] = []
    for metric_date, avg_utilization_pct, trips_count in reversed(rows):
        trend.append(
            {
                "date": metric_date.isoformat() if metric_date is not None else None,
                "collection_rate": float(avg_utilization_pct or 0.0),
                "trips_count": int(trips_count or 0),
            }
        )
    return trend


async def _zone_performance_rows(session: AsyncSession) -> list[dict]:
    rows = (
        await session.execute(
            select(
                ZoneORM.zone_name,
                func.avg(AnalyticsDailyKPIORM.utilization_pct).label("efficiency"),
                func.count(func.distinct(VehicleORM.id)).label("total_trucks"),
                func.sum(AnalyticsDailyKPIORM.trips_count).label("total_trips"),
            )
            .select_from(AnalyticsDailyKPIORM)
            .join(
                VehicleORM,
                or_(
                    cast(VehicleORM.id, String) == AnalyticsDailyKPIORM.vehicle_id,
                    VehicleORM.vehicle_number == AnalyticsDailyKPIORM.vehicle_id,
                ),
            )
            .join(WardORM, VehicleORM.ward_id == WardORM.id)
            .join(ZoneORM, WardORM.zone_id == ZoneORM.id)
            .group_by(ZoneORM.zone_name)
            .order_by(ZoneORM.zone_name.asc())
        )
    ).all()

    items: list[dict] = []
    for zone_name, efficiency, total_trucks, total_trips in rows:
        items.append(
            {
                "zone": zone_name,
                "efficiency": float(efficiency or 0.0),
                "total_trucks": int(total_trucks or 0),
                "total_trips": int(total_trips or 0),
            }
        )
    return items


async def _vendor_performance_rows(session: AsyncSession) -> list[dict]:
    rows = (
        await session.execute(
            select(
                cast(VehicleORM.vendor_id, String).label("vendor_id"),
                func.max(VendorORM.vendor_name).label("vendor_name"),
                func.avg(AnalyticsDailyKPIORM.utilization_pct).label("efficiency"),
                func.count(func.distinct(VehicleORM.id)).label("total_trucks"),
                func.sum(AnalyticsDailyKPIORM.trips_count).label("total_trips"),
            )
            .select_from(AnalyticsDailyKPIORM)
            .join(
                VehicleORM,
                or_(
                    cast(VehicleORM.id, String) == AnalyticsDailyKPIORM.vehicle_id,
                    VehicleORM.vehicle_number == AnalyticsDailyKPIORM.vehicle_id,
                ),
            )
            .outerjoin(VendorORM, VendorORM.id == VehicleORM.vendor_id)
            .group_by(cast(VehicleORM.vendor_id, String))
            .order_by(func.max(VendorORM.vendor_name).asc().nulls_last())
        )
    ).all()

    items: list[dict] = []
    for vendor_id, vendor_name, efficiency, total_trucks, total_trips in rows:
        items.append(
            {
                "vendor_id": vendor_id,
                "vendor": vendor_name or vendor_id or "Unknown",
                "efficiency": float(efficiency or 0.0),
                "total_trucks": int(total_trucks or 0),
                "total_trips": int(total_trips or 0),
            }
        )
    return items


@router.post("/auth/login-json", response_model=auth_router.LoginResponse)
async def login_json(
    payload: LoginJsonRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> auth_router.LoginResponse:
    username_or_email = payload.email.strip().lower()
    user = await session.scalar(
        select(AuthUserORM).where(
            AuthUserORM.deleted_at.is_(None),
            or_(
                func.lower(AuthUserORM.username) == username_or_email,
                func.lower(AuthUserORM.email) == username_or_email,
            ),
        )
    )
    username = user.username if user is not None else username_or_email
    return await auth_router.login(
        auth_router.LoginRequest(username=username, password=payload.password),
        request,
        session,
    )


@router.get("/auth/me", response_model=auth_router.TokenIntrospectionResponse)
async def auth_me(ctx: RoleContext = Depends(get_role_context)) -> auth_router.TokenIntrospectionResponse:
    return await auth_router.me(ctx)


@router.get("/auth/users", response_model=list[auth_router.AuthUserResponse])
async def auth_users(
    ctx: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> list[auth_router.AuthUserResponse]:
    return await auth_router.list_users(ctx, session)


@router.post("/auth/register", response_model=auth_router.AuthUserResponse)
async def auth_register(
    payload: RegisterRequest,
    ctx: RoleContext = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> auth_router.AuthUserResponse:
    username = payload.email.strip().lower()
    create_payload = auth_router.AuthUserCreate(
        username=username,
        password=payload.password,
        email=username,
        display_name=payload.name,
        roles=[_normalize_role(payload.role)],
        active=True,
    )
    return await auth_router.create_user(create_payload, ctx, session)


@router.get("/alerts")
async def alerts_list(
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    truck_id: str | None = Query(default=None),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    stmt = select(AlertORM)
    if status:
        stmt = stmt.where(AlertORM.status == status)
    if severity:
        stmt = stmt.where(AlertORM.severity == severity)
    if truck_id:
        stmt = stmt.where(AlertORM.vehicle_id == truck_id)

    rows = (await session.execute(stmt.order_by(AlertORM.triggered_at.desc()).limit(500))).scalars().all()
    return [_to_dict(row) for row in rows]


@router.get("/alerts/active")
async def alerts_active(
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    rows = (
        await session.execute(
            select(AlertORM)
            .where(AlertORM.status.in_(["open", "active", "acknowledged", "escalated"]))
            .order_by(AlertORM.triggered_at.desc())
            .limit(500)
        )
    ).scalars().all()
    return [_to_dict(row) for row in rows]


@router.get("/alerts/expiry")
async def alerts_expiry(
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
) -> dict:
    # Placeholder response to satisfy current UI contract until expiry-domain models are introduced.
    return {"items": [], "total": 0}


@router.get("/zones")
async def zones_list(
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    rows = (
        await session.execute(
            select(ZoneORM.id, ZoneORM.zone_name, ZoneORM.zone_code, ZoneORM.active, func.count(WardORM.id))
            .select_from(ZoneORM)
            .outerjoin(WardORM, WardORM.zone_id == ZoneORM.id)
            .group_by(ZoneORM.id, ZoneORM.zone_name, ZoneORM.zone_code, ZoneORM.active)
            .order_by(ZoneORM.zone_name.asc())
        )
    ).all()

    return [
        {
            "id": str(zone_id),
            "name": zone_name,
            "code": zone_code,
            "description": "",
            "supervisor_name": "",
            "supervisor_phone": "",
            "total_wards": int(ward_count or 0),
            "status": "active" if active else "inactive",
        }
        for zone_id, zone_name, zone_code, active, ward_count in rows
    ]


@router.get("/zones/{zone_id}/wards")
async def zone_wards(
    zone_id: str,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    zone_uuid = _parse_uuid(zone_id)
    if zone_uuid is None:
        return []
    rows = (
        await session.execute(
            select(WardORM)
            .where(WardORM.zone_id == zone_uuid)
            .order_by(WardORM.ward_name.asc())
        )
    ).scalars().all()
    return [_to_dict(row) for row in rows]


@router.get("/trucks")
async def trucks_list(
    zone_id: str | None = Query(default=None),
    vendor_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    ctx: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    realtime = await realtime_router.list_realtime_trucks(limit=50000, _=ctx)

    realtime_by_vehicle: dict[str, dict] = {}
    realtime_by_imei: dict[str, dict] = {}
    for item in realtime.items:
        record = {
            "imei": item.imei,
            "vehicle_id": item.vehicle_id,
            "lat": item.lat,
            "lng": item.lng,
            "speed_kph": item.speed_kph,
            "status": item.status,
            "event_ts": item.event_ts,
            "vendor_id": item.vendor_id,
        }
        if item.vehicle_id:
            realtime_by_vehicle[item.vehicle_id] = record
        realtime_by_imei[item.imei] = record

    vehicle_rows = (
        await session.execute(
            select(VehicleORM, WardORM, RouteORM, ZoneORM)
            .join(WardORM, VehicleORM.ward_id == WardORM.id)
            .join(ZoneORM, WardORM.zone_id == ZoneORM.id)
            .outerjoin(RouteORM, VehicleORM.route_id == RouteORM.id)
            .order_by(VehicleORM.vehicle_number.asc())
        )
    ).all()

    items: list[dict] = []
    used_vehicle_keys: set[str] = set()

    for vehicle, ward, route, zone in vehicle_rows:
        vehicle_key = vehicle.vehicle_number or vehicle.registration_number or str(vehicle.id)
        rt = realtime_by_vehicle.get(vehicle_key)

        truck = {
            "id": str(vehicle.id),
            "registration_number": vehicle.registration_number or vehicle.vehicle_number,
            "type": vehicle.truck_type or "compactor",
            "route_type": vehicle.truck_type or "primary",
            "latitude": float(rt["lat"]) if rt and rt.get("lat") is not None else None,
            "longitude": float(rt["lng"]) if rt and rt.get("lng") is not None else None,
            "current_status": (rt.get("status") if rt else None) or vehicle.operational_status or "idle",
            "speed": float(rt.get("speed_kph") if rt else 0) or 0,
            "trips_completed": 0,
            "trips_allowed": 0,
            "driver_name": None,
            "route_name": route.route_name if route is not None else None,
            "vendor_id": str(vehicle.vendor_id) if vehicle.vendor_id is not None else "",
            "zone_id": str(zone.id),
            "ward_id": str(ward.id),
            "is_spare": _is_spare_vehicle(vehicle),
            "last_update": (rt.get("event_ts").isoformat() if rt and isinstance(rt.get("event_ts"), datetime) else None),
        }

        if zone_id and truck["zone_id"] != zone_id:
            continue
        if vendor_id and truck["vendor_id"] != vendor_id:
            continue
        if status and truck["current_status"] != status:
            continue

        items.append(truck)
        used_vehicle_keys.add(vehicle_key)

    # Include live-only records that do not have a corresponding vehicle master row yet.
    for rt in realtime.items:
        vehicle_key = rt.vehicle_id or rt.imei
        if vehicle_key in used_vehicle_keys:
            continue
        truck = {
            "id": rt.imei,
            "registration_number": rt.vehicle_id or rt.imei,
            "type": "compactor",
            "route_type": "primary",
            "latitude": rt.lat,
            "longitude": rt.lng,
            "current_status": rt.status or "idle",
            "speed": rt.speed_kph,
            "trips_completed": 0,
            "trips_allowed": 0,
            "driver_name": None,
            "route_name": None,
            "vendor_id": rt.vendor_id or "",
            "zone_id": "",
            "ward_id": "",
            "is_spare": False,
            "last_update": rt.event_ts.isoformat() if isinstance(rt.event_ts, datetime) else None,
        }
        if vendor_id and truck["vendor_id"] != vendor_id:
            continue
        if status and truck["current_status"] != status:
            continue
        items.append(truck)

    return items


@router.get("/trucks/spare")
async def spare_trucks(
    ctx: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    trucks = await trucks_list(ctx=ctx, session=session)
    return [truck for truck in trucks if bool(truck.get("is_spare"))]


@router.put("/trucks/{truck_id}/assign-route")
async def assign_truck_route(
    truck_id: str,
    payload: AssignRouteRequest,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        route_uuid = UUID(payload.assigned_route_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="assigned_route_id must be a UUID") from exc

    route_exists = await session.scalar(select(RouteORM.id).where(RouteORM.id == route_uuid))
    if route_exists is None:
        raise HTTPException(status_code=404, detail="route not found")

    vehicle = (
        await session.execute(
            select(VehicleORM).where(
                and_(
                    VehicleORM.active.is_(True),
                    or_(
                        cast(VehicleORM.id, String) == truck_id,
                        VehicleORM.vehicle_number == truck_id,
                        VehicleORM.registration_number == truck_id,
                    ),
                )
            )
        )
    ).scalars().first()

    if vehicle is None:
        raise HTTPException(status_code=404, detail="truck not found")

    vehicle.route_id = route_uuid
    await session.commit()
    await session.refresh(vehicle)
    return _to_dict(vehicle)


@router.get("/reports/statistics")
async def reports_statistics(
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    total_trucks = int((await session.execute(select(func.count()).select_from(VehicleORM))).scalar_one())
    active_trucks = int(
        (
            await session.execute(
                select(func.count()).select_from(VehicleORM).where(VehicleORM.active.is_(True))
            )
        ).scalar_one()
    )
    idle_trucks = max(total_trucks - active_trucks, 0)
    total_zones = int((await session.execute(select(func.count()).select_from(ZoneORM))).scalar_one())
    total_wards = int((await session.execute(select(func.count()).select_from(WardORM))).scalar_one())
    total_vendors = int((await session.execute(select(func.count()).select_from(VendorORM))).scalar_one())
    total_routes = int((await session.execute(select(func.count()).select_from(RouteORM))).scalar_one())
    active_alerts = int(
        (
            await session.execute(
                select(func.count())
                .select_from(AlertORM)
                .where(AlertORM.status.in_(["open", "active", "acknowledged", "escalated"]))
            )
        ).scalar_one()
    )

    return {
        "total_trucks": total_trucks,
        "active_trucks": active_trucks,
        "idle_trucks": idle_trucks,
        "total_zones": total_zones,
        "total_wards": total_wards,
        "total_vendors": total_vendors,
        "total_routes": total_routes,
        "total_pickup_points": 0,
        "active_alerts": active_alerts,
    }


@router.get("/reports/zone-performance")
async def reports_zone_performance(
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    return await _zone_performance_rows(session)


@router.get("/reports/vendor-performance")
async def reports_vendor_performance(
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    return await _vendor_performance_rows(session)


@router.get("/reports/collection-efficiency")
async def reports_collection_efficiency(
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    row = (
        await session.execute(
            select(
                func.avg(AnalyticsDailyKPIORM.utilization_pct).label("avg_utilization_pct"),
                func.sum(AnalyticsDailyKPIORM.trips_count).label("total_trips"),
                func.sum(AnalyticsDailyKPIORM.distance_km).label("total_distance_km"),
            )
        )
    ).first()
    avg_utilization_pct = float(row[0] or 0.0) if row else 0.0
    total_trips = int(row[1] or 0) if row else 0
    total_distance_km = float(row[2] or 0.0) if row else 0.0
    return {
        "collection_efficiency": avg_utilization_pct,
        "avg_utilization_pct": avg_utilization_pct,
        "total_trips": total_trips,
        "total_distance_km": total_distance_km,
    }


def _report_date_window(
    date_from: date | None,
    date_to: date | None,
) -> tuple[date, date, datetime, datetime]:
    report_tz = timezone(timedelta(hours=5, minutes=30))
    if date_from is None and date_to is None:
        date_from = datetime.now(report_tz).date()
        date_to = date_from
    elif date_from is None:
        date_from = date_to
    elif date_to is None:
        date_to = date_from

    assert date_from is not None
    assert date_to is not None
    from_ts = datetime.combine(date_from, time.min, tzinfo=report_tz).astimezone(timezone.utc)
    to_ts = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=report_tz).astimezone(timezone.utc)
    return date_from, date_to, from_ts, to_ts


def _distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def _has_gtc_halt(
    session: AsyncSession,
    *,
    identities: set[str],
    entered_at: datetime,
    gtc_lat: float,
    gtc_lng: float,
    radius_m: float,
    halt_seconds: int,
) -> tuple[bool, datetime | None]:
    if not identities:
        return False, None

    watch_until = entered_at + timedelta(seconds=max(halt_seconds * 3, halt_seconds + 600))
    stmt = (
        select(DeviceEventORM.ts, DeviceEventORM.lat, DeviceEventORM.lon)
        .where(
            DeviceEventORM.ts >= entered_at,
            DeviceEventORM.ts <= watch_until,
            or_(
                DeviceEventORM.device_id.in_(identities),
                DeviceEventORM.attributes["vehicle_id"].as_string().in_(identities),
                DeviceEventORM.attributes["imei"].as_string().in_(identities),
            ),
        )
        .order_by(DeviceEventORM.ts.asc())
    )
    events = (await session.execute(stmt)).all()

    inside_since: datetime | None = None
    last_inside: datetime | None = None
    first_inside_any: datetime | None = None
    last_inside_any: datetime | None = None
    for event_ts, lat, lon in events:
        inside = _distance_m(float(lat), float(lon), gtc_lat, gtc_lng) <= radius_m
        if inside:
            first_inside_any = first_inside_any or event_ts
            last_inside_any = event_ts
            inside_since = inside_since or event_ts
            last_inside = event_ts
            if (event_ts - inside_since).total_seconds() >= halt_seconds:
                return True, event_ts
        else:
            inside_since = None

    # If telemetry is sparse/noisy, accept repeated evidence inside the GTC
    # geofence spanning the threshold. This matches geofence-entry style data
    # where only periodic points land exactly inside the center radius.
    if first_inside_any is not None and last_inside_any is not None:
        return (last_inside_any - first_inside_any).total_seconds() >= halt_seconds, last_inside_any
    return False, None


async def _completed_trip_rows(
    session: AsyncSession,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    zone_id: str | None = None,
    ward_id: str | None = None,
    vehicle_id: str | None = None,
) -> list[dict]:
    settings = get_settings()
    _, _, from_ts, to_ts = _report_date_window(date_from, date_to)
    report_tz = timezone(timedelta(hours=5, minutes=30))

    vehicle_stmt = (
        select(VehicleORM, WardORM, ZoneORM, VendorORM, RouteORM)
        .join(WardORM, VehicleORM.ward_id == WardORM.id)
        .join(ZoneORM, WardORM.zone_id == ZoneORM.id)
        .join(VendorORM, VehicleORM.vendor_id == VendorORM.id)
        .outerjoin(RouteORM, VehicleORM.route_id == RouteORM.id)
        .where(VehicleORM.route_id.is_not(None))
    )
    if zone_id:
        vehicle_stmt = vehicle_stmt.where(cast(ZoneORM.id, String) == zone_id)
    if ward_id:
        vehicle_stmt = vehicle_stmt.where(cast(WardORM.id, String) == ward_id)
    if vehicle_id:
        vehicle_stmt = vehicle_stmt.where(
            or_(
                cast(VehicleORM.id, String) == vehicle_id,
                VehicleORM.vehicle_number == vehicle_id,
                VehicleORM.registration_number == vehicle_id,
            )
        )
    vehicle_rows = (await session.execute(vehicle_stmt)).all()
    if not vehicle_rows:
        return []

    vehicle_info: dict[str, dict] = {}
    vehicle_ids: set[str] = set()
    route_ids: set[UUID] = set()
    identities_by_vehicle: dict[str, set[str]] = {}
    for vehicle, ward, zone, vendor, route in vehicle_rows:
        canonical_id = str(vehicle.id)
        vehicle_ids.add(canonical_id)
        if vehicle.route_id is not None:
            route_ids.add(vehicle.route_id)
        identities = {
            canonical_id,
            str(vehicle.vehicle_number or ""),
            str(vehicle.registration_number or ""),
        }
        identities.discard("")
        identities_by_vehicle[canonical_id] = identities
        info = {
            "vehicle_id": canonical_id,
            "truck": vehicle.vehicle_number or vehicle.registration_number or canonical_id,
            "type": vehicle.truck_type or "Vehicle",
            "route_id": str(vehicle.route_id) if vehicle.route_id is not None else None,
            "route": route.route_name if route is not None else "-",
            "zone": zone.zone_name,
            "ward": ward.ward_name,
            "vendor": vendor.vendor_name,
            "driver": "Unassigned",
        }
        for identity in identities:
            vehicle_info[identity] = info

    assignment_rows = (
        await session.execute(
            select(
                cast(DeviceVehicleAssignmentORM.vehicle_id, String).label("vehicle_id"),
                cast(DeviceVehicleAssignmentORM.device_id, String).label("device_id"),
                DeviceORM.imei,
            )
            .select_from(DeviceVehicleAssignmentORM)
            .join(DeviceORM, DeviceVehicleAssignmentORM.device_id == DeviceORM.id)
            .where(
                DeviceVehicleAssignmentORM.active.is_(True),
                cast(DeviceVehicleAssignmentORM.vehicle_id, String).in_(vehicle_ids),
            )
        )
    ).all()
    for row in assignment_rows:
        identities = identities_by_vehicle.setdefault(str(row.vehicle_id), {str(row.vehicle_id)})
        info = vehicle_info.get(str(row.vehicle_id))
        if row.device_id:
            identities.add(str(row.device_id))
            if info is not None:
                vehicle_info[str(row.device_id)] = info
        if row.imei:
            identities.add(str(row.imei))
            if info is not None:
                vehicle_info[str(row.imei)] = info

    driver_name_by_vehicle: dict[str, str] = {}
    driver_rows = (
        await session.execute(
            select(DriverORM)
            .where(
                DriverORM.active.is_(True),
                cast(DriverORM.assigned_vehicle_id, String).in_(vehicle_ids),
            )
            .order_by(DriverORM.name.asc())
        )
    ).scalars().all()
    for driver in driver_rows:
        assigned_vehicle_id = str(driver.assigned_vehicle_id) if driver.assigned_vehicle_id is not None else None
        if not assigned_vehicle_id:
            continue
        driver_name_by_vehicle[assigned_vehicle_id] = driver.name
        for identity in identities_by_vehicle.get(assigned_vehicle_id, {assigned_vehicle_id}):
            info = vehicle_info.get(identity)
            if info is not None:
                info["driver"] = driver.name

    pickup_rows = (
        await session.execute(
            select(PickupPointORM)
            .where(PickupPointORM.route_id.in_(route_ids))
            .order_by(PickupPointORM.route_id.asc(), PickupPointORM.sequence_no.asc())
        )
    ).scalars().all()
    last_pickup_by_route: dict[str, PickupPointORM] = {}
    pickup_count_by_route: dict[str, int] = {}
    pickup_points_by_route: dict[str, list[PickupPointORM]] = {}
    pickup_by_id: dict[str, PickupPointORM] = {}
    for pickup in pickup_rows:
        if pickup.route_id is None or pickup.lat is None or pickup.lng is None:
            continue
        route_key = str(pickup.route_id)
        pickup_key = str(pickup.id)
        pickup_points_by_route.setdefault(route_key, []).append(pickup)
        pickup_by_id[pickup_key] = pickup
        pickup_count_by_route[route_key] = pickup_count_by_route.get(route_key, 0) + 1
        current = last_pickup_by_route.get(route_key)
        if current is None or pickup.sequence_no >= current.sequence_no:
            last_pickup_by_route[route_key] = pickup

    all_vehicle_identities = set().union(*identities_by_vehicle.values()) if identities_by_vehicle else set()
    crossing_rows = (
        await session.execute(
            select(
                PickupPointCrossingORM.vehicle_id,
                PickupPointCrossingORM.route_id,
                PickupPointCrossingORM.pickup_point_id,
                PickupPointCrossingORM.crossed_at,
                PickupPointCrossingORM.distance_m,
            )
            .where(
                PickupPointCrossingORM.vehicle_id.in_(all_vehicle_identities),
                PickupPointCrossingORM.route_id.in_(route_ids),
                PickupPointCrossingORM.crossed_at >= from_ts,
                PickupPointCrossingORM.crossed_at < to_ts,
            )
            .order_by(
                PickupPointCrossingORM.vehicle_id.asc(),
                PickupPointCrossingORM.route_id.asc(),
                PickupPointCrossingORM.crossed_at.asc(),
            )
        )
    ).all()

    trip_rows: list[dict] = []
    route_started_at: dict[tuple[str, str], datetime] = {}
    completed_keys: set[tuple[str, str, datetime]] = set()

    def _trip_detail_rows(
        *,
        vehicle_key: str,
        route_id_str: str,
        started_at: datetime,
        completed_at: datetime,
    ) -> list[dict]:
        identities = identities_by_vehicle.get(vehicle_key, {vehicle_key})
        crossings_by_pickup: dict[str, list] = {}
        for crossing_row in crossing_rows:
            if str(crossing_row.vehicle_id) not in identities:
                continue
            if str(crossing_row.route_id) != route_id_str:
                continue
            if crossing_row.crossed_at < started_at or crossing_row.crossed_at > completed_at:
                continue
            crossings_by_pickup.setdefault(str(crossing_row.pickup_point_id), []).append(crossing_row)

        details: list[dict] = []
        for pickup in pickup_points_by_route.get(route_id_str, []):
            pickup_crossings = crossings_by_pickup.get(str(pickup.id), [])
            first_crossing = min(pickup_crossings, key=lambda item: item.crossed_at) if pickup_crossings else None
            last_crossing = max(pickup_crossings, key=lambda item: item.crossed_at) if pickup_crossings else None
            nearest_distance = min((float(item.distance_m) for item in pickup_crossings), default=None)
            details.append(
                {
                    "id": str(pickup.id),
                    "sequenceNo": int(pickup.sequence_no or 0),
                    "pickupName": pickup.pickup_name or f"Pickup Point {pickup.sequence_no}",
                    "expectedTime": pickup.expected_pickup_time,
                    "status": "covered" if pickup_crossings else "missed",
                    "actualTime": first_crossing.crossed_at.astimezone(report_tz).strftime("%H:%M:%S")
                    if first_crossing
                    else None,
                    "lastCrossedTime": last_crossing.crossed_at.astimezone(report_tz).strftime("%H:%M:%S")
                    if last_crossing
                    else None,
                    "firstCrossedAt": first_crossing.crossed_at.isoformat() if first_crossing else None,
                    "lastCrossedAt": last_crossing.crossed_at.isoformat() if last_crossing else None,
                    "crossingCount": len(pickup_crossings),
                    "nearestDistanceM": nearest_distance,
                    "isGtcPoint": str(pickup.id) == str(last_pickup_by_route[route_id_str].id),
                }
            )
        return details

    for crossing in crossing_rows:
        info = vehicle_info.get(str(crossing.vehicle_id))
        route_id_str = str(crossing.route_id)
        if info is None or route_id_str not in last_pickup_by_route:
            continue
        vehicle_key = info["vehicle_id"]
        state_key = (vehicle_key, route_id_str)
        last_pickup = last_pickup_by_route[route_id_str]
        is_gtc_crossing = str(crossing.pickup_point_id) == str(last_pickup.id)
        if not is_gtc_crossing:
            route_started_at[state_key] = route_started_at.get(state_key) or crossing.crossed_at
            continue

        started_at = route_started_at.get(state_key)
        if started_at is None or started_at >= crossing.crossed_at:
            continue
        completion_key = (vehicle_key, route_id_str, crossing.crossed_at)
        if completion_key in completed_keys:
            continue

        completed, completed_at = await _has_gtc_halt(
            session,
            identities=identities_by_vehicle.get(vehicle_key, {vehicle_key}),
            entered_at=crossing.crossed_at,
            gtc_lat=float(last_pickup.lat),
            gtc_lng=float(last_pickup.lng),
            radius_m=float(settings.gtc_trip_radius_m),
            halt_seconds=max(settings.gtc_trip_halt_seconds, 0),
        )
        completion_method = "gtc_halt"
        if not completed:
            # Some simulator/backfill data has reliable pickup-point crossings
            # but no dense telemetry points at the GTC to prove the halt window.
            # In that case, route visited + later GTC crossing is the best
            # available completion evidence, so keep the report populated.
            completed = True
            completed_at = crossing.crossed_at
            completion_method = "gtc_crossing_fallback"
        if not completed:
            continue

        completed_keys.add(completion_key)
        completed_at = completed_at or crossing.crossed_at
        started_local = started_at.astimezone(report_tz)
        completed_local = completed_at.astimezone(report_tz)
        duration_minutes = max(0, int((completed_at - started_at).total_seconds() // 60))
        trip_details = _trip_detail_rows(
            vehicle_key=vehicle_key,
            route_id_str=route_id_str,
            started_at=started_at,
            completed_at=completed_at,
        )
        trip_rows.append(
            {
                "id": f"TRP-{completed_local:%Y%m%d}-{len(trip_rows) + 1:03d}",
                "date": completed_local.date().isoformat(),
                "vehicle_id": vehicle_key,
                "truck": info["truck"],
                "driver": driver_name_by_vehicle.get(vehicle_key) or info.get("driver") or "Unassigned",
                "route_id": route_id_str,
                "route": info["route"],
                "zone": info["zone"],
                "ward": info["ward"],
                "vendor": info["vendor"],
                "routeType": info["type"],
                "startTime": started_local.strftime("%H:%M"),
                "endTime": completed_local.strftime("%H:%M"),
                "startedAt": started_at.isoformat(),
                "completedAt": completed_at.isoformat(),
                "durationMinutes": duration_minutes,
                "duration": f"{duration_minutes // 60}h {duration_minutes % 60}m"
                if duration_minutes >= 60
                else f"{duration_minutes}m",
                "pickups": pickup_count_by_route.get(route_id_str, 0),
                "status": "completed",
                "gtcPoint": last_pickup.pickup_name or f"Pickup {last_pickup.sequence_no}",
                "gtcRadiusM": float(settings.gtc_trip_radius_m),
                "haltSeconds": int(settings.gtc_trip_halt_seconds),
                "completionMethod": completion_method,
                "tripDetails": trip_details,
            }
        )
        route_started_at.pop(state_key, None)

    return trip_rows


@router.get("/trips/completed")
async def trips_completed(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    zone_id: str | None = Query(default=None),
    ward_id: str | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    rows = await _completed_trip_rows(
        session,
        date_from=date_from,
        date_to=date_to,
        zone_id=zone_id,
        ward_id=ward_id,
        vehicle_id=vehicle_id,
    )
    return {"items": rows, "total": len(rows), "trip_count": len(rows)}


def _parse_expected_pickup_time(value: str | None) -> time | None:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M%p"):
        try:
            return datetime.strptime(cleaned.upper(), fmt).time()
        except ValueError:
            continue
    return None


async def _first_pickup_arrival_rows(
    session: AsyncSession,
    *,
    date_from: date | None,
    date_to: date | None,
    zone_id: str | None = None,
    ward_id: str | None = None,
    vehicle_id: str | None = None,
) -> list[dict]:
    settings = get_settings()
    report_tz = timezone(timedelta(hours=5, minutes=30))
    date_from, date_to, from_ts, to_ts = _report_date_window(date_from, date_to)

    vehicle_stmt = (
        select(VehicleORM, WardORM, ZoneORM, VendorORM, RouteORM)
        .join(WardORM, VehicleORM.ward_id == WardORM.id)
        .join(ZoneORM, WardORM.zone_id == ZoneORM.id)
        .outerjoin(VendorORM, VehicleORM.vendor_id == VendorORM.id)
        .outerjoin(RouteORM, VehicleORM.route_id == RouteORM.id)
        .where(VehicleORM.route_id.is_not(None))
    )
    if zone_id:
        vehicle_stmt = vehicle_stmt.where(cast(ZoneORM.id, String) == zone_id)
    if ward_id:
        vehicle_stmt = vehicle_stmt.where(cast(WardORM.id, String) == ward_id)
    if vehicle_id:
        vehicle_stmt = vehicle_stmt.where(
            or_(
                cast(VehicleORM.id, String) == vehicle_id,
                VehicleORM.vehicle_number == vehicle_id,
                VehicleORM.registration_number == vehicle_id,
            )
        )

    vehicle_rows = (await session.execute(vehicle_stmt)).all()
    if not vehicle_rows:
        return []

    vehicle_ids: set[str] = set()
    route_ids: set[UUID] = set()
    identities_by_vehicle: dict[str, set[str]] = {}
    vehicle_info: dict[str, dict] = {}
    for vehicle, ward, zone, vendor, route in vehicle_rows:
        canonical_id = str(vehicle.id)
        vehicle_ids.add(canonical_id)
        if vehicle.route_id is not None:
            route_ids.add(vehicle.route_id)
        identities = {
            canonical_id,
            str(vehicle.vehicle_number or ""),
            str(vehicle.registration_number or ""),
        }
        identities.discard("")
        identities_by_vehicle[canonical_id] = identities
        info = {
            "vehicle_id": canonical_id,
            "truck": vehicle.vehicle_number or vehicle.registration_number or canonical_id,
            "driver": "Unassigned",
            "route_id": str(vehicle.route_id) if vehicle.route_id is not None else None,
            "route": route.route_name if route is not None else "-",
            "routeType": vehicle.truck_type or "Vehicle",
            "zone": zone.zone_name,
            "ward": ward.ward_name,
            "vendor": vendor.vendor_name if vendor is not None else "-",
        }
        for identity in identities:
            vehicle_info[identity] = info

    assignment_rows = (
        await session.execute(
            select(
                cast(DeviceVehicleAssignmentORM.vehicle_id, String).label("vehicle_id"),
                cast(DeviceVehicleAssignmentORM.device_id, String).label("device_id"),
                DeviceORM.imei,
            )
            .select_from(DeviceVehicleAssignmentORM)
            .join(DeviceORM, DeviceVehicleAssignmentORM.device_id == DeviceORM.id)
            .where(
                DeviceVehicleAssignmentORM.active.is_(True),
                cast(DeviceVehicleAssignmentORM.vehicle_id, String).in_(vehicle_ids),
            )
        )
    ).all()
    for row in assignment_rows:
        identities = identities_by_vehicle.setdefault(str(row.vehicle_id), {str(row.vehicle_id)})
        info = vehicle_info.get(str(row.vehicle_id))
        if row.device_id:
            identities.add(str(row.device_id))
            if info is not None:
                vehicle_info[str(row.device_id)] = info
        if row.imei:
            identities.add(str(row.imei))
            if info is not None:
                vehicle_info[str(row.imei)] = info

    first_pickup_by_route: dict[str, PickupPointORM] = {}
    pickup_rows = (
        await session.execute(
            select(PickupPointORM)
            .where(PickupPointORM.route_id.in_(route_ids))
            .order_by(PickupPointORM.route_id.asc(), PickupPointORM.sequence_no.asc())
        )
    ).scalars().all()
    for pickup in pickup_rows:
        if pickup.route_id is None:
            continue
        route_key = str(pickup.route_id)
        current = first_pickup_by_route.get(route_key)
        if current is None or pickup.sequence_no < current.sequence_no:
            first_pickup_by_route[route_key] = pickup

    first_pickup_ids = {pickup.id for pickup in first_pickup_by_route.values()}
    if not first_pickup_ids:
        return []

    all_vehicle_identities = set().union(*identities_by_vehicle.values()) if identities_by_vehicle else set()
    local_cross_date = func.date(func.timezone("Asia/Kolkata", PickupPointCrossingORM.crossed_at))
    crossing_stmt = (
        select(
            PickupPointCrossingORM.vehicle_id.label("vehicle_id"),
            PickupPointCrossingORM.route_id.label("route_id"),
            PickupPointCrossingORM.pickup_point_id.label("pickup_point_id"),
            local_cross_date.label("cross_date"),
            func.min(PickupPointCrossingORM.crossed_at).label("first_entered_at"),
            func.min(PickupPointCrossingORM.distance_m).label("nearest_distance_m"),
            func.count(PickupPointCrossingORM.id).label("crossing_count"),
        )
        .where(
            PickupPointCrossingORM.vehicle_id.in_(all_vehicle_identities),
            PickupPointCrossingORM.route_id.in_(route_ids),
            PickupPointCrossingORM.pickup_point_id.in_(first_pickup_ids),
            PickupPointCrossingORM.crossed_at >= from_ts,
            PickupPointCrossingORM.crossed_at < to_ts,
        )
        .group_by(
            PickupPointCrossingORM.vehicle_id,
            PickupPointCrossingORM.route_id,
            PickupPointCrossingORM.pickup_point_id,
            local_cross_date,
        )
        .order_by(local_cross_date.desc(), func.min(PickupPointCrossingORM.crossed_at).asc())
    )
    crossing_rows = (await session.execute(crossing_stmt)).all()

    grace_minutes = max(int(settings.first_pickup_grace_minutes), 0)
    report_rows: list[dict] = []
    seen_keys: set[tuple[str, str, date]] = set()
    for index, row in enumerate(crossing_rows, start=1):
        info = vehicle_info.get(str(row.vehicle_id))
        route_id_str = str(row.route_id)
        if info is None or route_id_str not in first_pickup_by_route:
            continue
        vehicle_key = info["vehicle_id"]
        cross_date = row.cross_date
        unique_key = (vehicle_key, route_id_str, cross_date)
        if unique_key in seen_keys:
            continue
        seen_keys.add(unique_key)

        first_pickup = first_pickup_by_route[route_id_str]
        expected_time = _parse_expected_pickup_time(first_pickup.expected_pickup_time)
        actual_local = row.first_entered_at.astimezone(report_tz)
        expected_at = (
            datetime.combine(cross_date, expected_time, tzinfo=report_tz) if expected_time is not None else None
        )
        threshold_at = expected_at + timedelta(minutes=grace_minutes) if expected_at is not None else None
        delay_minutes = (
            int((actual_local - expected_at).total_seconds() // 60) if expected_at is not None else 0
        )
        late_by_minutes = (
            max(0, int((actual_local - threshold_at).total_seconds() // 60)) if threshold_at is not None else 0
        )
        is_late = threshold_at is not None and actual_local > threshold_at
        report_rows.append(
            {
                "id": f"FPA-{cross_date:%Y%m%d}-{index:03d}",
                "date": cross_date.isoformat(),
                "vehicle_id": vehicle_key,
                "truck": info["truck"],
                "driver": info["driver"],
                "route_id": route_id_str,
                "route": info["route"],
                "routeType": info["routeType"],
                "zone": info["zone"],
                "ward": info["ward"],
                "vendor": info["vendor"],
                "firstPickupPoint": first_pickup.pickup_name or f"Pickup Point {first_pickup.sequence_no}",
                "firstPickupSequence": int(first_pickup.sequence_no or 0),
                "scheduledTime": expected_time.strftime("%H:%M") if expected_time is not None else "-",
                "expectedTime": first_pickup.expected_pickup_time,
                "actualTime": actual_local.strftime("%H:%M"),
                "actualDateTime": actual_local.isoformat(),
                "allowedUntil": threshold_at.strftime("%H:%M") if threshold_at is not None else "-",
                "graceMinutes": grace_minutes,
                "delay": delay_minutes,
                "lateByMinutes": late_by_minutes,
                "isLate": is_late,
                "status": "late" if is_late else "on-time",
                "nearestDistanceM": float(row.nearest_distance_m or 0),
                "crossingCount": int(row.crossing_count or 0),
                "reason": "Entered after expected time + grace" if is_late else "",
            }
        )

    return report_rows


async def _driver_behavior_rows(
    session: AsyncSession,
    *,
    date_from: date | None,
    date_to: date | None,
    zone_id: str | None = None,
    ward_id: str | None = None,
    vehicle_id: str | None = None,
) -> list[dict]:
    report_tz = timezone(timedelta(hours=5, minutes=30))
    _, _, from_ts, to_ts = _report_date_window(date_from, date_to)

    vehicle_stmt = (
        select(VehicleORM, WardORM, ZoneORM, VendorORM, RouteORM)
        .join(WardORM, VehicleORM.ward_id == WardORM.id)
        .join(ZoneORM, WardORM.zone_id == ZoneORM.id)
        .outerjoin(VendorORM, VehicleORM.vendor_id == VendorORM.id)
        .outerjoin(RouteORM, VehicleORM.route_id == RouteORM.id)
    )
    if zone_id:
        vehicle_stmt = vehicle_stmt.where(cast(ZoneORM.id, String) == zone_id)
    if ward_id:
        vehicle_stmt = vehicle_stmt.where(cast(WardORM.id, String) == ward_id)
    if vehicle_id:
        vehicle_stmt = vehicle_stmt.where(
            or_(
                cast(VehicleORM.id, String) == vehicle_id,
                VehicleORM.vehicle_number == vehicle_id,
                VehicleORM.registration_number == vehicle_id,
            )
        )

    vehicle_rows = (await session.execute(vehicle_stmt)).all()
    vehicle_info: dict[str, dict] = {}
    vehicle_ids: set[str] = set()
    for vehicle, ward, zone, vendor, route in vehicle_rows:
        canonical_id = str(vehicle.id)
        vehicle_ids.add(canonical_id)
        info = {
            "vehicle_id": canonical_id,
            "truck": vehicle.vehicle_number or vehicle.registration_number or canonical_id,
            "registration": vehicle.registration_number,
            "route": route.route_name if route is not None else "-",
            "route_id": str(vehicle.route_id) if vehicle.route_id is not None else None,
            "zone": zone.zone_name,
            "ward": ward.ward_name,
            "vendor": vendor.vendor_name if vendor is not None else "-",
            "driver": "Unassigned",
        }
        for identity in (canonical_id, vehicle.vehicle_number, vehicle.registration_number):
            if identity:
                vehicle_info[str(identity)] = info

    if vehicle_ids:
        assignment_rows = (
            await session.execute(
                select(
                    cast(DeviceVehicleAssignmentORM.vehicle_id, String).label("vehicle_id"),
                    cast(DeviceVehicleAssignmentORM.device_id, String).label("device_id"),
                    DeviceORM.imei,
                )
                .select_from(DeviceVehicleAssignmentORM)
                .join(DeviceORM, DeviceVehicleAssignmentORM.device_id == DeviceORM.id)
                .where(cast(DeviceVehicleAssignmentORM.vehicle_id, String).in_(vehicle_ids))
            )
        ).all()
        for row in assignment_rows:
            info = vehicle_info.get(str(row.vehicle_id))
            if info is None:
                continue
            if row.device_id:
                vehicle_info[str(row.device_id)] = info
            if row.imei:
                vehicle_info[str(row.imei)] = info

    allowed_identities = set(vehicle_info.keys())
    stmt = (
        select(AnalyticsOverspeedEventORM)
        .where(
            AnalyticsOverspeedEventORM.event_ts >= from_ts,
            AnalyticsOverspeedEventORM.event_ts < to_ts,
        )
        .order_by(AnalyticsOverspeedEventORM.event_ts.desc())
        .limit(5000)
    )
    if allowed_identities:
        stmt = stmt.where(
            or_(
                AnalyticsOverspeedEventORM.vehicle_id.in_(allowed_identities),
                AnalyticsOverspeedEventORM.imei.in_(allowed_identities),
                AnalyticsOverspeedEventORM.device_id.in_(allowed_identities),
            )
        )
    elif zone_id or ward_id or vehicle_id:
        return []

    rows = (await session.execute(stmt)).scalars().all()
    report_rows: list[dict] = []
    for index, event in enumerate(rows, start=1):
        info = (
            vehicle_info.get(str(event.vehicle_id))
            or vehicle_info.get(str(event.imei))
            or vehicle_info.get(str(event.device_id))
            or {}
        )
        event_local = event.event_ts.astimezone(report_tz)
        over_by = max(0.0, float(event.speed_kph or 0) - float(event.threshold_kph or 0))
        severity = (event.severity or "medium").lower()
        report_rows.append(
            {
                "id": str(event.id),
                "date": event_local.date().isoformat(),
                "time": event_local.strftime("%H:%M:%S"),
                "eventTs": event_local.isoformat(),
                "truck": info.get("truck") or str(event.vehicle_id),
                "vehicle_id": info.get("vehicle_id") or str(event.vehicle_id),
                "imei": event.imei,
                "device_id": event.device_id,
                "driver": info.get("driver") or "Unassigned",
                "incidentType": "Overspeeding",
                "value": f"{float(event.speed_kph or 0):.1f} km/h",
                "speedKph": round(float(event.speed_kph or 0), 2),
                "limit": f"{float(event.threshold_kph or 0):.0f} km/h",
                "thresholdKph": round(float(event.threshold_kph or 0), 2),
                "overByKph": round(over_by, 2),
                "location": f"{float(event.lat):.6f}, {float(event.lng):.6f}",
                "lat": float(event.lat),
                "lng": float(event.lng),
                "severity": severity,
                "zone": info.get("zone") or "-",
                "ward": info.get("ward") or "-",
                "route": info.get("route") or "-",
                "route_id": info.get("route_id"),
                "vendor": info.get("vendor") or str(event.vendor_id),
                "rank": index,
            }
        )

    return report_rows


async def _route_performance_rows(
    session: AsyncSession,
    *,
    date_from: date | None,
    date_to: date | None,
    zone_id: str | None = None,
    ward_id: str | None = None,
    vehicle_id: str | None = None,
) -> list[dict]:
    report_tz = timezone(timedelta(hours=5, minutes=30))
    _, _, from_ts, to_ts = _report_date_window(date_from, date_to)

    vehicle_stmt = (
        select(VehicleORM, WardORM, ZoneORM, VendorORM, RouteORM)
        .join(WardORM, VehicleORM.ward_id == WardORM.id)
        .join(ZoneORM, WardORM.zone_id == ZoneORM.id)
        .outerjoin(VendorORM, VehicleORM.vendor_id == VendorORM.id)
        .outerjoin(RouteORM, VehicleORM.route_id == RouteORM.id)
        .where(VehicleORM.route_id.is_not(None))
    )
    if zone_id:
        vehicle_stmt = vehicle_stmt.where(cast(ZoneORM.id, String) == zone_id)
    if ward_id:
        vehicle_stmt = vehicle_stmt.where(cast(WardORM.id, String) == ward_id)
    if vehicle_id:
        vehicle_stmt = vehicle_stmt.where(
            or_(
                cast(VehicleORM.id, String) == vehicle_id,
                VehicleORM.vehicle_number == vehicle_id,
                VehicleORM.registration_number == vehicle_id,
            )
        )

    vehicle_rows = (await session.execute(vehicle_stmt)).all()
    vehicle_info: dict[str, dict] = {}
    vehicle_ids: set[str] = set()
    for vehicle, ward, zone, vendor, route in vehicle_rows:
        canonical_id = str(vehicle.id)
        vehicle_ids.add(canonical_id)
        info = {
            "vehicle_id": canonical_id,
            "truck": vehicle.vehicle_number or vehicle.registration_number or canonical_id,
            "zone": zone.zone_name,
            "ward": ward.ward_name,
            "route": route.route_name if route is not None else "-",
            "route_id": str(vehicle.route_id) if vehicle.route_id is not None else None,
            "vendor": vendor.vendor_name if vendor is not None else "-",
        }
        for identity in (canonical_id, vehicle.vehicle_number, vehicle.registration_number):
            if identity:
                vehicle_info[str(identity)] = info

    if vehicle_ids:
        assignment_rows = (
            await session.execute(
                select(
                    cast(DeviceVehicleAssignmentORM.vehicle_id, String).label("vehicle_id"),
                    cast(DeviceVehicleAssignmentORM.device_id, String).label("device_id"),
                    DeviceORM.imei,
                )
                .select_from(DeviceVehicleAssignmentORM)
                .join(DeviceORM, DeviceVehicleAssignmentORM.device_id == DeviceORM.id)
                .where(cast(DeviceVehicleAssignmentORM.vehicle_id, String).in_(vehicle_ids))
            )
        ).all()
        for row in assignment_rows:
            info = vehicle_info.get(str(row.vehicle_id))
            if info is None:
                continue
            if row.device_id:
                vehicle_info[str(row.device_id)] = info
            if row.imei:
                vehicle_info[str(row.imei)] = info

    allowed_identities = set(vehicle_info.keys())
    if (zone_id or ward_id or vehicle_id) and not allowed_identities:
        return []

    def _info_for(vehicle_identity: str, imei: str | None = None, device_id: str | None = None) -> dict:
        return vehicle_info.get(str(vehicle_identity)) or vehicle_info.get(str(imei or "")) or vehicle_info.get(str(device_id or "")) or {}

    def _add_group(groups: dict[str, dict], detail: dict, info: dict, event_local: datetime) -> None:
        key = "|".join(
            [
                event_local.date().isoformat(),
                info.get("zone") or "-",
                info.get("ward") or "-",
                info.get("route") or "-",
            ]
        )
        group = groups.setdefault(
            key,
            {
                "id": key,
                "date": event_local.date().isoformat(),
                "zone": info.get("zone") or "-",
                "ward": info.get("ward") or "-",
                "route": info.get("route") or "-",
                "route_id": info.get("route_id"),
                "anomalyCount": 0,
                "overspeedCount": 0,
                "deviationCount": 0,
                "geofenceEntryCount": 0,
                "geofenceExitCount": 0,
                "affectedTrucks": set(),
                "worstSeverity": "low",
                "anomalyDetails": [],
            },
        )
        group["anomalyCount"] += 1
        group["affectedTrucks"].add(detail.get("truck") or "-")
        group["anomalyDetails"].append(detail)
        category = detail.get("category")
        if category == "Overspeeding":
            group["overspeedCount"] += 1
        elif category == "Route Deviation":
            group["deviationCount"] += 1
        elif category == "Geofence Entry":
            group["geofenceEntryCount"] += 1
        elif category == "Geofence Exit":
            group["geofenceExitCount"] += 1
        detail_severity = str(detail.get("severity") or "").lower()
        if detail_severity in {"critical", "high"}:
            group["worstSeverity"] = "high"
        elif detail_severity in {"warning", "medium"} and group["worstSeverity"] != "high":
            group["worstSeverity"] = "medium"

    groups: dict[str, dict] = {}

    overspeed_stmt = (
        select(AnalyticsOverspeedEventORM)
        .where(AnalyticsOverspeedEventORM.event_ts >= from_ts, AnalyticsOverspeedEventORM.event_ts < to_ts)
        .order_by(AnalyticsOverspeedEventORM.event_ts.desc())
        .limit(5000)
    )
    geofence_stmt = (
        select(AnalyticsGeofenceEventORM)
        .where(AnalyticsGeofenceEventORM.event_ts >= from_ts, AnalyticsGeofenceEventORM.event_ts < to_ts)
        .order_by(AnalyticsGeofenceEventORM.event_ts.desc())
        .limit(5000)
    )
    if allowed_identities:
        identity_filter = lambda orm: or_(orm.vehicle_id.in_(allowed_identities), orm.imei.in_(allowed_identities), orm.device_id.in_(allowed_identities))
        overspeed_stmt = overspeed_stmt.where(identity_filter(AnalyticsOverspeedEventORM))
        geofence_stmt = geofence_stmt.where(identity_filter(AnalyticsGeofenceEventORM))

    overspeed_rows = (await session.execute(overspeed_stmt)).scalars().all()
    for event in overspeed_rows:
        info = _info_for(event.vehicle_id, event.imei, event.device_id)
        if not info:
            continue
        event_local = event.event_ts.astimezone(report_tz)
        speed = float(event.speed_kph or 0)
        threshold = float(event.threshold_kph or 0)
        severity = (event.severity or "medium").lower()
        detail = {
            "id": str(event.id),
            "date": event_local.date().isoformat(),
            "time": event_local.strftime("%H:%M:%S"),
            "truck": info.get("truck") or str(event.vehicle_id),
            "imei": event.imei,
            "device_id": event.device_id,
            "category": "Overspeeding",
            "description": f"Speed {speed:.1f} km/h exceeded limit {threshold:.0f} km/h",
            "value": f"{speed:.1f} km/h",
            "threshold": f"{threshold:.0f} km/h",
            "overBy": f"{max(0.0, speed - threshold):.1f} km/h",
            "location": f"{float(event.lat):.6f}, {float(event.lng):.6f}",
            "severity": severity,
        }
        _add_group(groups, detail, info, event_local)

    geofence_rows = (await session.execute(geofence_stmt)).scalars().all()
    for event in geofence_rows:
        info = _info_for(event.vehicle_id, event.imei, event.device_id)
        if not info:
            continue
        event_local = event.event_ts.astimezone(report_tz)
        event_type = (event.event_type or "").lower()
        category = "Route Deviation" if event_type == "route_deviation" else "Geofence Entry" if event_type == "entry" else "Geofence Exit"
        severity = "high" if event_type == "route_deviation" else "medium"
        detail = {
            "id": str(event.id),
            "date": event_local.date().isoformat(),
            "time": event_local.strftime("%H:%M:%S"),
            "truck": info.get("truck") or str(event.vehicle_id),
            "imei": event.imei,
            "device_id": event.device_id,
            "category": category,
            "description": f"{category} at {event.geofence_code or event.geofence_type or 'geofence'}",
            "value": event.geofence_code or event.geofence_type or "-",
            "threshold": "-",
            "overBy": "-",
            "location": f"{float(event.lat):.6f}, {float(event.lng):.6f}",
            "severity": severity,
        }
        _add_group(groups, detail, info, event_local)

    route_rows: list[dict] = []
    for group in groups.values():
        affected_trucks = sorted(group["affectedTrucks"])
        group["affectedTruckCount"] = len(affected_trucks)
        group["affectedTrucks"] = ", ".join(affected_trucks)
        group["completion"] = max(0, 100 - min(group["deviationCount"] * 5, 100))
        group["efficiency"] = max(0, 100 - min(group["anomalyCount"] * 2, 100))
        group["avgTime"] = "-"
        group["deviations"] = group["deviationCount"]
        route_rows.append(group)

    return sorted(route_rows, key=lambda row: (row["date"], row["zone"], row["ward"], row["route"]), reverse=True)


async def _driver_attendance_rows(
    session: AsyncSession,
    *,
    trip_completed: list[dict],
    driver_behavior: list[dict],
    zone_id: str | None = None,
    ward_id: str | None = None,
    vehicle_id: str | None = None,
) -> list[dict]:
    driver_stmt = (
        select(DriverORM, VehicleORM, WardORM, ZoneORM)
        .outerjoin(VehicleORM, DriverORM.assigned_vehicle_id == VehicleORM.id)
        .outerjoin(WardORM, VehicleORM.ward_id == WardORM.id)
        .outerjoin(ZoneORM, WardORM.zone_id == ZoneORM.id)
        .order_by(DriverORM.name.asc())
    )
    if zone_id:
        driver_stmt = driver_stmt.where(cast(ZoneORM.id, String) == zone_id)
    if ward_id:
        driver_stmt = driver_stmt.where(cast(WardORM.id, String) == ward_id)
    if vehicle_id:
        driver_stmt = driver_stmt.where(
            or_(
                cast(VehicleORM.id, String) == vehicle_id,
                VehicleORM.vehicle_number == vehicle_id,
                VehicleORM.registration_number == vehicle_id,
            )
        )

    driver_rows = (await session.execute(driver_stmt)).all()
    trips_by_vehicle: dict[str, list[dict]] = {}
    for trip in trip_completed:
        key = str(trip.get("vehicle_id") or "")
        if key:
            trips_by_vehicle.setdefault(key, []).append(trip)

    violations_by_truck: dict[str, int] = {}
    for incident in driver_behavior:
        truck = str(incident.get("truck") or "")
        if truck:
            violations_by_truck[truck] = violations_by_truck.get(truck, 0) + 1

    rows: list[dict] = []
    seen_driver_ids: set[str] = set()
    for driver, vehicle, ward, zone in driver_rows:
        driver_id = str(driver.id)
        seen_driver_ids.add(driver_id)
        vehicle_id_str = str(driver.assigned_vehicle_id) if driver.assigned_vehicle_id is not None else ""
        driver_trips = trips_by_vehicle.get(vehicle_id_str, [])
        first_trip = min(driver_trips, key=lambda item: item.get("startedAt") or "") if driver_trips else None
        last_trip = max(driver_trips, key=lambda item: item.get("completedAt") or "") if driver_trips else None
        total_minutes = sum(int(trip.get("durationMinutes") or 0) for trip in driver_trips)
        truck = (
            vehicle.vehicle_number or vehicle.registration_number or vehicle_id_str
            if vehicle is not None
            else "-"
        )
        violations = violations_by_truck.get(str(truck), 0)
        score = max(0, min(100, 100 - violations * 2))
        rows.append(
            {
                "id": driver_id,
                "driver": driver.name,
                "truck": truck,
                "zone": zone.zone_name if zone is not None else "-",
                "ward": ward.ward_name if ward is not None else "-",
                "shiftStart": first_trip.get("startTime") if first_trip else "-",
                "shiftEnd": last_trip.get("endTime") if last_trip else "-",
                "hoursWorked": round(total_minutes / 60, 2),
                "routes": len({trip.get("route_id") or trip.get("route") for trip in driver_trips if trip.get("route_id") or trip.get("route")}),
                "trips": len(driver_trips),
                "onTime": True,
                "violations": violations,
                "score": score,
                "status": "present" if driver_trips else "no-trip",
            }
        )

    # If there are completed trips for a driver not yet registered in master data,
    # still surface them rather than hiding report activity.
    for trip in trip_completed:
        if trip.get("driver") and trip.get("driver") != "Unassigned":
            continue
        synthetic_id = f"unassigned-{trip.get('vehicle_id') or trip.get('truck')}"
        if synthetic_id in seen_driver_ids:
            continue
        vehicle_trips = trips_by_vehicle.get(str(trip.get("vehicle_id") or ""), [trip])
        first_trip = min(vehicle_trips, key=lambda item: item.get("startedAt") or "")
        last_trip = max(vehicle_trips, key=lambda item: item.get("completedAt") or "")
        total_minutes = sum(int(item.get("durationMinutes") or 0) for item in vehicle_trips)
        rows.append(
            {
                "id": synthetic_id,
                "driver": "Unassigned",
                "truck": trip.get("truck") or "-",
                "zone": trip.get("zone") or "-",
                "ward": trip.get("ward") or "-",
                "shiftStart": first_trip.get("startTime") or "-",
                "shiftEnd": last_trip.get("endTime") or "-",
                "hoursWorked": round(total_minutes / 60, 2),
                "routes": len({item.get("route_id") or item.get("route") for item in vehicle_trips if item.get("route_id") or item.get("route")}),
                "trips": len(vehicle_trips),
                "onTime": True,
                "violations": violations_by_truck.get(str(trip.get("truck") or ""), 0),
                "score": max(0, 100 - violations_by_truck.get(str(trip.get("truck") or ""), 0) * 2),
                "status": "present",
            }
        )
        seen_driver_ids.add(synthetic_id)

    return rows


async def _vehicle_status_rows(
    session: AsyncSession,
    *,
    date_from: date,
    date_to: date,
    zone_id: str | None = None,
    ward_id: str | None = None,
    vehicle_id: str | None = None,
    route_id: str | None = None,
) -> list[dict]:
    report_tz = timezone(timedelta(hours=5, minutes=30))
    now_utc = datetime.now(timezone.utc)
    from_ts = now_utc - timedelta(hours=24)
    to_ts = now_utc
    stale_gps_seconds = 300
    offline_seconds = 600

    vehicle_stmt = (
        select(VehicleORM, WardORM, ZoneORM, RouteORM, DriverORM)
        .join(WardORM, VehicleORM.ward_id == WardORM.id)
        .join(ZoneORM, WardORM.zone_id == ZoneORM.id)
        .outerjoin(RouteORM, VehicleORM.route_id == RouteORM.id)
        .outerjoin(DriverORM, DriverORM.assigned_vehicle_id == VehicleORM.id)
        .order_by(VehicleORM.vehicle_number.asc())
    )
    if zone_id:
        vehicle_stmt = vehicle_stmt.where(cast(ZoneORM.id, String) == zone_id)
    if ward_id:
        vehicle_stmt = vehicle_stmt.where(cast(WardORM.id, String) == ward_id)
    if route_id:
        vehicle_stmt = vehicle_stmt.where(cast(RouteORM.id, String) == route_id)
    if vehicle_id:
        vehicle_stmt = vehicle_stmt.where(
            or_(
                cast(VehicleORM.id, String) == vehicle_id,
                VehicleORM.vehicle_number == vehicle_id,
                VehicleORM.registration_number == vehicle_id,
            )
        )

    vehicle_rows = (await session.execute(vehicle_stmt)).all()
    vehicles: dict[str, dict] = {}
    vehicle_ids: list[UUID] = []
    for vehicle, ward, zone, route, driver in vehicle_rows:
        vehicle_id_str = str(vehicle.id)
        vehicle_ids.append(vehicle.id)
        vehicles[vehicle_id_str] = {
            "vehicle": vehicle,
            "ward": ward,
            "zone": zone,
            "route": route,
            "driver": driver,
        }

    if not vehicle_ids:
        return []

    assignment_stmt = (
        select(DeviceVehicleAssignmentORM, DeviceORM)
        .join(DeviceORM, DeviceVehicleAssignmentORM.device_id == DeviceORM.id)
        .where(
            DeviceVehicleAssignmentORM.vehicle_id.in_(vehicle_ids),
            DeviceVehicleAssignmentORM.active.is_(True),
            DeviceVehicleAssignmentORM.assigned_to.is_(None),
            DeviceVehicleAssignmentORM.assigned_from <= now_utc,
        )
        .order_by(DeviceVehicleAssignmentORM.assigned_from.asc())
    )
    assignment_rows = (await session.execute(assignment_stmt)).all()
    assignments_by_vehicle: dict[str, list[dict]] = {}
    imei_to_assignment: dict[str, list[dict]] = {}
    for assignment, device in assignment_rows:
        entry = {
            "device_id": str(device.id),
            "imei": device.imei,
            "assigned_from": assignment.assigned_from,
            "assigned_to": assignment.assigned_to,
            "active": bool(assignment.active),
            "battery_percent": device.battery_percent,
            "signal_strength": device.signal_strength,
            "health_status": device.health_status,
            "device_active": bool(device.active),
            "device_last_seen": device.last_seen,
        }
        vehicle_key = str(assignment.vehicle_id)
        assignments_by_vehicle.setdefault(vehicle_key, []).append(entry)
        imei_to_assignment.setdefault(device.imei, []).append({**entry, "vehicle_id": vehicle_key})

    event_rows = []
    if imei_to_assignment:
        event_stmt = (
            select(DeviceEventORM)
            .where(
                DeviceEventORM.ts >= from_ts,
                DeviceEventORM.ts < to_ts,
                DeviceEventORM.device_id.in_(list(imei_to_assignment.keys())),
            )
            .order_by(DeviceEventORM.ts.asc())
        )
        event_rows = (await session.execute(event_stmt)).scalars().all()

    event_stats: dict[tuple[str, str], dict] = {}
    for event in event_rows:
        possible_assignments = imei_to_assignment.get(event.device_id, [])
        matched_assignment = possible_assignments[-1] if possible_assignments else None
        if matched_assignment is None:
            continue

        key = matched_assignment["vehicle_id"]
        stats = event_stats.setdefault(
            key,
            {
                "eventCount": 0,
                "firstSeen": event.ts,
                "lastSeen": event.ts,
                "lastLat": event.lat,
                "lastLon": event.lon,
                "maxSpeedKph": 0.0,
                "avgSpeedTotal": 0.0,
                "ignitionOnCount": 0,
            },
        )
        stats["eventCount"] += 1
        stats["avgSpeedTotal"] += float(event.speed_kph or 0)
        stats["maxSpeedKph"] = max(float(stats["maxSpeedKph"]), float(event.speed_kph or 0))
        if event.ignition:
            stats["ignitionOnCount"] += 1
        if event.ts < stats["firstSeen"]:
            stats["firstSeen"] = event.ts
        if event.ts >= stats["lastSeen"]:
            stats["lastSeen"] = event.ts
            stats["lastLat"] = event.lat
            stats["lastLon"] = event.lon

    def _format_dt(value: datetime | None) -> str:
        if value is None:
            return "-"
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(report_tz).strftime("%Y-%m-%d %H:%M:%S")

    rows: list[dict] = []
    snapshot_at = now_utc.astimezone(report_tz)
    for vehicle_key, info in vehicles.items():
        vehicle = info["vehicle"]
        ward = info["ward"]
        zone = info["zone"]
        route = info["route"]
        driver = info["driver"]
        assignment = assignments_by_vehicle.get(vehicle_key, [])[-1] if assignments_by_vehicle.get(vehicle_key) else None
        stats = event_stats.get(vehicle_key)
        device_last_seen = (assignment or {}).get("device_last_seen")
        last_seen = stats["lastSeen"] if stats else device_last_seen
        battery = (assignment or {}).get("battery_percent")
        signal = (assignment or {}).get("signal_strength")
        health_status = str((assignment or {}).get("health_status") or "offline").lower()
        age_seconds = None
        if last_seen is not None:
            age_seconds = max(0, int((now_utc - last_seen).total_seconds()))
        event_count = int(stats["eventCount"]) if stats else 0

        if not vehicle.active or vehicle.operational_status in {"retired", "breakdown"}:
            status = "failed" if vehicle.operational_status == "breakdown" else "inactive"
            gps_status = "offline"
        elif assignment is None:
            status = "inactive"
            gps_status = "offline"
        elif last_seen is None or age_seconds is None or age_seconds >= offline_seconds or health_status in {"critical", "offline"}:
            status = "inactive" if health_status != "critical" else "failed"
            gps_status = "offline"
        elif age_seconds >= stale_gps_seconds or health_status == "warning" or (battery is not None and battery < 20) or (signal is not None and signal < 30):
            status = "warning"
            gps_status = "warning"
        else:
            status = "active"
            gps_status = "online"

        avg_speed = 0.0
        if stats and event_count > 0:
            avg_speed = round(float(stats["avgSpeedTotal"]) / event_count, 2)
        rows.append(
            {
                "id": f"spot-{vehicle_key}",
                "snapshotAt": snapshot_at.strftime("%Y-%m-%d %H:%M:%S"),
                "vehicle_id": vehicle_key,
                "truck": vehicle.vehicle_number or vehicle.registration_number,
                "registration": vehicle.registration_number,
                "type": vehicle.truck_type or "Vehicle",
                "zone": zone.zone_name,
                "ward": ward.ward_name,
                "route": route.route_name if route is not None else "-",
                "route_id": str(route.id) if route is not None else None,
                "driver": driver.name if driver is not None else "Unassigned",
                "deviceImei": (assignment or {}).get("imei") or "-",
                "gpsStatus": gps_status,
                "status": status,
                "vehicleStatus": vehicle.operational_status,
                "eventCount": event_count,
                "firstSeen": _format_dt(stats["firstSeen"] if stats else None),
                "lastSeen": _format_dt(last_seen),
                "lastUpdate": _format_dt(last_seen),
                "location": (
                    f"{float(stats['lastLat']):.6f}, {float(stats['lastLon']):.6f}"
                    if stats
                    else "-"
                ),
                "batteryLevel": round(float(battery), 1) if battery is not None else 0,
                "signalStrength": round(float(signal), 1) if signal is not None else 0,
                "maxSpeedKph": round(float(stats["maxSpeedKph"]), 2) if stats else 0,
                "avgSpeedKph": avg_speed,
                "ignitionOnCount": int(stats["ignitionOnCount"]) if stats else 0,
                "ageSeconds": age_seconds,
                "ageMinutes": round(age_seconds / 60, 1) if age_seconds is not None else None,
            }
        )

    return sorted(rows, key=lambda row: (row["zone"], row["ward"], row["route"], row["truck"]))


@router.get("/reports/data")
async def reports_data(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    zone_id: str | None = Query(default=None),
    ward_id: str | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
    route_id: str | None = Query(default=None),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    weekly_trend = await _weekly_collection_trend(session)
    zone_wise = await _zone_performance_rows(session)
    report_tz = timezone(timedelta(hours=5, minutes=30))
    if date_from is None and date_to is None:
        date_from, date_to, from_ts, to_ts = _report_date_window(date_from, date_to)
    elif date_from is None:
        date_from = date_to
        _, _, from_ts, to_ts = _report_date_window(date_from, date_to)
    elif date_to is None:
        date_to = date_from
        _, _, from_ts, to_ts = _report_date_window(date_from, date_to)
    else:
        _, _, from_ts, to_ts = _report_date_window(date_from, date_to)

    local_cross_date = func.date(func.timezone("Asia/Kolkata", PickupPointCrossingORM.crossed_at))
    vehicle_filter_values: set[str] = set()
    if vehicle_id:
        vehicle_filter_values.add(vehicle_id)
        vehicle_filter_stmt = select(VehicleORM).where(
            or_(
                cast(VehicleORM.id, String) == vehicle_id,
                VehicleORM.vehicle_number == vehicle_id,
                VehicleORM.registration_number == vehicle_id,
            )
        )
        vehicle_filter_row = (await session.execute(vehicle_filter_stmt)).scalars().first()
        if vehicle_filter_row is not None:
            vehicle_filter_values.update(
                {
                    str(vehicle_filter_row.id),
                    vehicle_filter_row.vehicle_number,
                    vehicle_filter_row.registration_number,
                }
            )

    coverage_stmt = (
        select(
            PickupPointCrossingORM.vehicle_id.label("vehicle_id"),
            PickupPointCrossingORM.route_id.label("route_id"),
            local_cross_date.label("cross_date"),
            func.count(func.distinct(PickupPointCrossingORM.pickup_point_id)).label("covered"),
            func.max(PickupPointCrossingORM.crossed_at).label("last_crossed_at"),
        )
        .group_by(
            PickupPointCrossingORM.vehicle_id,
            PickupPointCrossingORM.route_id,
            local_cross_date,
        )
        .order_by(local_cross_date.desc(), func.max(PickupPointCrossingORM.crossed_at).desc())
    )
    coverage_stmt = coverage_stmt.where(
        PickupPointCrossingORM.crossed_at >= from_ts,
        PickupPointCrossingORM.crossed_at < to_ts,
    )
    if vehicle_id:
        coverage_stmt = coverage_stmt.where(PickupPointCrossingORM.vehicle_id.in_(vehicle_filter_values))
    coverage_rows = (await session.execute(coverage_stmt)).all()

    route_ids = {row.route_id for row in coverage_rows if row.route_id is not None}
    route_total_points: dict[str, int] = {}
    route_pickup_points: dict[str, list[dict]] = {}
    if route_ids:
        route_points_stmt = (
            select(
                PickupPointORM.route_id,
                func.count(PickupPointORM.id).label("total_points"),
            )
            .where(PickupPointORM.route_id.in_(route_ids))
            .group_by(PickupPointORM.route_id)
        )
        route_total_rows = (await session.execute(route_points_stmt)).all()
        for row in route_total_rows:
            route_total_points[str(row.route_id)] = int(row.total_points or 0)

        pickup_points_stmt = (
            select(
                PickupPointORM.id,
                PickupPointORM.route_id,
                PickupPointORM.pickup_name,
                PickupPointORM.sequence_no,
                PickupPointORM.expected_pickup_time,
            )
            .where(PickupPointORM.route_id.in_(route_ids))
            .order_by(PickupPointORM.route_id.asc(), PickupPointORM.sequence_no.asc())
        )
        pickup_point_rows = (await session.execute(pickup_points_stmt)).all()
        for pickup in pickup_point_rows:
            route_key = str(pickup.route_id)
            route_pickup_points.setdefault(route_key, []).append(
                {
                    "id": str(pickup.id),
                    "pickupName": pickup.pickup_name or f"Pickup Point {pickup.sequence_no}",
                    "sequenceNo": int(pickup.sequence_no or 0),
                    "expectedTime": pickup.expected_pickup_time,
                }
            )

    vehicle_stmt = select(
        cast(VehicleORM.id, String).label("vehicle_id"),
        VehicleORM.vehicle_number,
        VehicleORM.registration_number,
        VehicleORM.route_id,
        WardORM.ward_name,
        ZoneORM.zone_name,
    ).join(WardORM, VehicleORM.ward_id == WardORM.id).join(ZoneORM, WardORM.zone_id == ZoneORM.id)
    if zone_id:
        vehicle_stmt = vehicle_stmt.where(cast(ZoneORM.id, String) == zone_id)
    if ward_id:
        vehicle_stmt = vehicle_stmt.where(cast(WardORM.id, String) == ward_id)
    vehicle_rows = (await session.execute(vehicle_stmt)).all()
    vehicle_meta: dict[str, dict] = {}
    for row in vehicle_rows:
        info = {
            "truck": row.vehicle_number,
            "ward": row.ward_name,
            "zone": row.zone_name,
            "route_id": str(row.route_id) if row.route_id is not None else None,
        }
        for key in (row.vehicle_id, row.vehicle_number, row.registration_number):
            if key is not None:
                vehicle_meta[str(key)] = info

    route_stmt = select(RouteORM.id, RouteORM.route_name)
    route_rows = (await session.execute(route_stmt)).all()
    route_name_by_id = {str(row.id): row.route_name for row in route_rows}

    pickup_crossing_details: dict[tuple[str, str, str, str], dict] = {}
    if route_ids:
        detail_stmt = (
            select(
                PickupPointCrossingORM.vehicle_id.label("vehicle_id"),
                PickupPointCrossingORM.route_id.label("route_id"),
                PickupPointCrossingORM.pickup_point_id.label("pickup_point_id"),
                local_cross_date.label("cross_date"),
                func.count(PickupPointCrossingORM.id).label("crossing_count"),
                func.min(PickupPointCrossingORM.crossed_at).label("first_crossed_at"),
                func.max(PickupPointCrossingORM.crossed_at).label("last_crossed_at"),
                func.min(PickupPointCrossingORM.distance_m).label("nearest_distance_m"),
            )
            .where(
                PickupPointCrossingORM.crossed_at >= from_ts,
                PickupPointCrossingORM.crossed_at < to_ts,
                PickupPointCrossingORM.route_id.in_(route_ids),
            )
            .group_by(
                PickupPointCrossingORM.vehicle_id,
                PickupPointCrossingORM.route_id,
                PickupPointCrossingORM.pickup_point_id,
                local_cross_date,
            )
        )
        if vehicle_id:
            detail_stmt = detail_stmt.where(PickupPointCrossingORM.vehicle_id.in_(vehicle_filter_values))
        detail_rows = (await session.execute(detail_stmt)).all()
        for detail in detail_rows:
            pickup_crossing_details[
                (
                    str(detail.cross_date),
                    str(detail.vehicle_id),
                    str(detail.route_id),
                    str(detail.pickup_point_id),
                )
            ] = {
                "crossingCount": int(detail.crossing_count or 0),
                "firstCrossedAt": detail.first_crossed_at,
                "lastCrossedAt": detail.last_crossed_at,
                "nearestDistanceM": float(detail.nearest_distance_m or 0),
            }

    def _format_report_time(value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(report_tz).strftime("%H:%M:%S")

    def _format_report_datetime(value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(report_tz).isoformat()

    daily_pickup_coverage: list[dict] = []
    for index, row in enumerate(coverage_rows, start=1):
        route_id = str(row.route_id) if row.route_id is not None else None
        covered = int(row.covered or 0)
        total_points = route_total_points.get(route_id or "", 0)
        missed = max(total_points - covered, 0)
        status = "completed" if total_points > 0 and covered >= total_points else "partial"
        vehicle_info = vehicle_meta.get(str(row.vehicle_id), {})
        if (zone_id or ward_id) and not vehicle_info:
            continue
        pickup_details: list[dict] = []
        for pickup in route_pickup_points.get(route_id or "", []):
            crossing = pickup_crossing_details.get(
                (
                    str(row.cross_date),
                    str(row.vehicle_id),
                    route_id or "",
                    pickup["id"],
                )
            )
            first_crossed_at = crossing["firstCrossedAt"] if crossing else None
            last_crossed_at = crossing["lastCrossedAt"] if crossing else None
            pickup_details.append(
                {
                    **pickup,
                    "status": "covered" if crossing else "missed",
                    "actualTime": _format_report_time(first_crossed_at),
                    "firstCrossedAt": _format_report_datetime(first_crossed_at),
                    "lastCrossedAt": _format_report_datetime(last_crossed_at),
                    "lastCrossedTime": _format_report_time(last_crossed_at),
                    "crossingCount": crossing["crossingCount"] if crossing else 0,
                    "nearestDistanceM": crossing["nearestDistanceM"] if crossing else None,
                }
            )
        daily_pickup_coverage.append(
            {
                "id": f"{row.cross_date}-{row.vehicle_id}-{route_id or 'na'}-{index}",
                "date": str(row.cross_date),
                "ward": vehicle_info.get("ward") or "-",
                "zone": vehicle_info.get("zone") or "-",
                "truck": vehicle_info.get("truck") or str(row.vehicle_id),
                "driver": "Unassigned",
                "route": route_name_by_id.get(route_id or "", route_id or "-"),
                "totalPoints": total_points,
                "covered": covered,
                "missed": missed,
                "weight": "0.0",
                "status": status,
                "lastCrossedAt": row.last_crossed_at.isoformat() if row.last_crossed_at else None,
                "pickupDetails": pickup_details,
            }
        )

    trip_completed = await _completed_trip_rows(
        session,
        date_from=date_from,
        date_to=date_to,
        zone_id=zone_id,
        ward_id=ward_id,
        vehicle_id=vehicle_id,
    )
    first_pickup_arrivals = await _first_pickup_arrival_rows(
        session,
        date_from=date_from,
        date_to=date_to,
        zone_id=zone_id,
        ward_id=ward_id,
        vehicle_id=vehicle_id,
    )
    driver_behavior = await _driver_behavior_rows(
        session,
        date_from=date_from,
        date_to=date_to,
        zone_id=zone_id,
        ward_id=ward_id,
        vehicle_id=vehicle_id,
    )
    driver_attendance = await _driver_attendance_rows(
        session,
        trip_completed=trip_completed,
        driver_behavior=driver_behavior,
        zone_id=zone_id,
        ward_id=ward_id,
        vehicle_id=vehicle_id,
    )
    route_performance = await _route_performance_rows(
        session,
        date_from=date_from,
        date_to=date_to,
        zone_id=zone_id,
        ward_id=ward_id,
        vehicle_id=vehicle_id,
    )
    vehicle_status = await _vehicle_status_rows(
        session,
        date_from=date_from,
        date_to=date_to,
        zone_id=zone_id,
        ward_id=ward_id,
        vehicle_id=vehicle_id,
        route_id=route_id,
    )
    utilization_by_truck: dict[str, dict] = {}
    for trip in trip_completed:
        truck = trip["truck"]
        row = utilization_by_truck.setdefault(
            truck,
            {
                "truck": truck,
                "type": trip.get("routeType") or "Vehicle",
                "trips": 0,
                "operatingHours": 0.0,
                "idleTime": 0.0,
                "distance": 0.0,
                "utilization": 100,
            },
        )
        row["trips"] += 1
        row["operatingHours"] = round(float(row["operatingHours"]) + (float(trip.get("durationMinutes") or 0) / 60), 2)

    # Compatibility payload for current UI tabs. Provide real aggregates where available.
    return {
        "daily_pickup_coverage": daily_pickup_coverage,
        "route_performance": route_performance,
        "truck_utilization": list(utilization_by_truck.values()),
        "trip_completed": trip_completed,
        "fuel_consumption": [],
        "driver_attendance": driver_attendance,
        "complaints": [],
        "dump_yard": [],
        "weekly_trend": weekly_trend,
        "zone_wise": zone_wise,
        "late_arrival": first_pickup_arrivals,
        "driver_behavior": driver_behavior,
        "vehicle_status": vehicle_status,
        "spare_usage": [],
    }


@router.get("/analytics/performance/overview")
async def analytics_performance_overview(
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    row = (
        await session.execute(
            select(
                func.avg(AnalyticsDailyKPIORM.utilization_pct).label("avg_utilization_pct"),
                func.sum(AnalyticsDailyKPIORM.trips_count).label("total_trips"),
                func.sum(AnalyticsDailyKPIORM.distance_km).label("total_distance_km"),
                func.avg(
                    case(
                        (
                            AnalyticsDailyKPIORM.runtime_seconds > 0,
                            (AnalyticsDailyKPIORM.idle_seconds * 100.0) / AnalyticsDailyKPIORM.runtime_seconds,
                        ),
                        else_=0,
                    )
                ).label("avg_idle_pct"),
            )
        )
    ).first()

    return {
        "efficiency": float(row[0] or 0.0) if row else 0.0,
        "total_trips": int(row[1] or 0) if row else 0,
        "total_distance_km": float(row[2] or 0.0) if row else 0.0,
        "avg_idle_pct": float(row[3] or 0.0) if row else 0.0,
    }


@router.get("/analytics/performance/zone-wise")
async def analytics_zone_wise_performance(
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    return await _zone_performance_rows(session)


@router.get("/analytics/performance/vendor-wise")
async def analytics_vendor_wise_performance(
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    return await _vendor_performance_rows(session)


@router.get("/analytics/predictions/maintenance")
async def analytics_maintenance_predictions(
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
) -> list[dict]:
    # Placeholder until predictive pipeline output is persisted.
    return []


@router.get("/analytics/trends/collection-rate")
async def analytics_collection_rate_trends(
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    return await _weekly_collection_trend(session)


@router.get("/drivers")
async def drivers_list(
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    try:
        db_rows = (await session.execute(select(DriverORM).order_by(DriverORM.name.asc()))).scalars().all()
        if db_rows:
            return [_driver_to_dict(row) for row in db_rows]
    except ProgrammingError:
        # Backward-compatible fallback for deployments where drivers table
        # is not yet migrated.
        await session.rollback()

    # Fallback: derive temporary list from vehicle metadata when drivers table is empty.
    rows = (
        await session.execute(
            select(VehicleORM)
            .where(VehicleORM.active.is_(True))
            .order_by(VehicleORM.vehicle_number.asc())
        )
    ).scalars().all()

    drivers_by_id: dict[str, dict] = {}

    for vehicle in rows:
        metadata = vehicle.metadata_json if isinstance(vehicle.metadata_json, dict) else {}
        driver_name = str(metadata.get("driver_name") or "").strip()
        if not driver_name:
            continue

        driver_id = str(metadata.get("driver_id") or "").strip() or f"drv-{str(vehicle.id)}"
        driver_phone = str(metadata.get("driver_phone") or "").strip() or None
        license_number = str(metadata.get("license_number") or "").strip() or None
        license_expiry = str(metadata.get("license_expiry") or "").strip() or None

        existing = drivers_by_id.get(driver_id)
        if existing is None:
            drivers_by_id[driver_id] = {
                "id": driver_id,
                "name": driver_name,
                "phone": driver_phone,
                "license_number": license_number,
                "license_expiry": license_expiry,
                "vendor_id": str(vehicle.vendor_id),
                "assigned_truck_id": str(vehicle.id),
                "status": "active",
                "active": True,
            }
            continue

        if existing.get("assigned_truck_id") in {None, ""}:
            existing["assigned_truck_id"] = str(vehicle.id)

    return sorted(drivers_by_id.values(), key=lambda item: str(item.get("name") or ""))


@router.get("/drivers/{driver_id}")
async def driver_get(
    driver_id: str,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        driver_uuid = UUID(driver_id)
    except ValueError:
        driver_uuid = None

    if driver_uuid is not None:
        row = (await session.execute(select(DriverORM).where(DriverORM.id == driver_uuid))).scalars().first()
        if row is not None:
            return _driver_to_dict(row)

    drivers = await drivers_list(_, session)
    for driver in drivers:
        if str(driver.get("id") or "") == driver_id:
            return driver
    raise HTTPException(status_code=404, detail="driver not found")


@router.post("/drivers")
async def driver_create(
    payload: DriverCreateRequest,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    license_expiry = None
    if payload.license_expiry:
        try:
            license_expiry = date.fromisoformat(payload.license_expiry)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="license_expiry must be YYYY-MM-DD") from exc

    row = DriverORM(
        name=payload.name.strip(),
        phone=(payload.phone or None),
        license_number=(payload.license_number or None),
        license_expiry=license_expiry,
        vendor_id=_parse_uuid(payload.vendor_id),
        assigned_vehicle_id=_parse_uuid(payload.assigned_truck_id),
        active=_resolve_active(status=payload.status, active=payload.active, default=True),
        metadata_json={
            "email": payload.email,
            "address": payload.address,
            "emergency_contact": payload.emergency_contact,
            "join_date": payload.join_date,
            "status": payload.status or ("active" if _resolve_active(status=payload.status, active=payload.active, default=True) else "inactive"),
        },
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _driver_to_dict(row)


@router.put("/drivers/{driver_id}")
async def driver_update(
    driver_id: str,
    payload: DriverUpdateRequest,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    driver_uuid = _parse_uuid(driver_id)
    if driver_uuid is None:
        raise HTTPException(status_code=404, detail="driver not found")

    row = (await session.execute(select(DriverORM).where(DriverORM.id == driver_uuid))).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="driver not found")

    if payload.name is not None:
        row.name = payload.name.strip()
    if payload.phone is not None:
        row.phone = payload.phone or None
    if payload.license_number is not None:
        row.license_number = payload.license_number or None
    if payload.license_expiry is not None:
        if payload.license_expiry == "":
            row.license_expiry = None
        else:
            try:
                row.license_expiry = date.fromisoformat(payload.license_expiry)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="license_expiry must be YYYY-MM-DD") from exc
    if "vendor_id" in payload.model_fields_set:
        row.vendor_id = _parse_uuid(payload.vendor_id)
    if "assigned_truck_id" in payload.model_fields_set:
        row.assigned_vehicle_id = _parse_uuid(payload.assigned_truck_id)

    row.active = _resolve_active(status=payload.status, active=payload.active, default=row.active)

    metadata = dict(row.metadata_json) if isinstance(row.metadata_json, dict) else {}
    if payload.email is not None:
        metadata["email"] = payload.email
    if payload.address is not None:
        metadata["address"] = payload.address
    if payload.emergency_contact is not None:
        metadata["emergency_contact"] = payload.emergency_contact
    if payload.join_date is not None:
        metadata["join_date"] = payload.join_date
    if payload.status is not None:
        metadata["status"] = payload.status
    row.metadata_json = metadata

    await session.commit()
    await session.refresh(row)
    return _driver_to_dict(row)


@router.delete("/drivers/{driver_id}")
async def driver_delete(
    driver_id: str,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    driver_uuid = _parse_uuid(driver_id)
    if driver_uuid is None:
        raise HTTPException(status_code=404, detail="driver not found")

    row = (await session.execute(select(DriverORM).where(DriverORM.id == driver_uuid))).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="driver not found")
    await session.delete(row)
    await session.commit()
    return {"ok": True}


@router.get("/gtc-checkpoints")
async def gtc_checkpoints_list(
    truck_id: str | None = Query(default=None),
    date: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    exact_date_dt = _parse_datetime(date)
    start = _parse_datetime(date_from)
    end = _parse_datetime(date_to)

    stmt = select(GtcCheckpointORM)
    if truck_id:
        stmt = stmt.where(GtcCheckpointORM.truck_id == truck_id)

    if exact_date_dt is not None:
        target_day: date = exact_date_dt.date()
        next_day_start = datetime.combine(target_day, datetime.min.time(), tzinfo=timezone.utc)
        day_after_start = next_day_start + timedelta(days=1)
        stmt = stmt.where(GtcCheckpointORM.arrived_at >= next_day_start, GtcCheckpointORM.arrived_at < day_after_start)
    else:
        if start is not None:
            stmt = stmt.where(GtcCheckpointORM.arrived_at >= start)
        if end is not None:
            stmt = stmt.where(GtcCheckpointORM.arrived_at <= end)

    rows = (
        await session.execute(stmt.order_by(GtcCheckpointORM.arrived_at.desc(), GtcCheckpointORM.id.desc()))
    ).scalars().all()

    return [
        {
            "id": row.id,
            "truck_id": row.truck_id,
            "arrived_at": row.arrived_at.isoformat() if row.arrived_at is not None else None,
            "is_dry": row.is_dry,
            "is_wet": row.is_wet,
            "is_metal": row.is_metal,
            "is_plastic": row.is_plastic,
            "is_sanitary": row.is_sanitary,
            "truck_cleanliness_score": row.truck_cleanliness_score,
            "gtc_cleanliness_score": row.gtc_cleanliness_score,
            "remarks": row.remarks,
            "truck_registration_number": row.truck_id,
        }
        for row in rows
    ]


@router.post("/gtc-checkpoints")
async def gtc_checkpoints_create(
    payload: GtcCheckpointCreateRequest,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    arrived_at = _parse_datetime(payload.arrived_at) or datetime.now(timezone.utc)
    row = GtcCheckpointORM(
        truck_id=payload.truck_id,
        arrived_at=arrived_at,
        is_dry=payload.is_dry,
        is_wet=payload.is_wet,
        is_metal=payload.is_metal,
        is_plastic=payload.is_plastic,
        is_sanitary=payload.is_sanitary,
        truck_cleanliness_score=payload.truck_cleanliness_score,
        gtc_cleanliness_score=payload.gtc_cleanliness_score,
        remarks=payload.remarks,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return {
        "id": row.id,
        "truck_id": row.truck_id,
        "arrived_at": row.arrived_at.isoformat() if row.arrived_at is not None else None,
        "is_dry": row.is_dry,
        "is_wet": row.is_wet,
        "is_metal": row.is_metal,
        "is_plastic": row.is_plastic,
        "is_sanitary": row.is_sanitary,
        "truck_cleanliness_score": row.truck_cleanliness_score,
        "gtc_cleanliness_score": row.gtc_cleanliness_score,
        "remarks": row.remarks,
        "truck_registration_number": row.truck_id,
    }


@router.get("/pickup-points")
async def pickup_points_list(
    zone_id: str | None = Query(default=None),
    ward_id: str | None = Query(default=None),
    route_id: str | None = Query(default=None),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    stmt = select(PickupPointORM)
    if zone_id:
        try:
            stmt = stmt.where(PickupPointORM.zone_id == UUID(zone_id))
        except ValueError:
            return []
    if ward_id:
        try:
            stmt = stmt.where(PickupPointORM.ward_id == UUID(ward_id))
        except ValueError:
            return []
    if route_id:
        try:
            stmt = stmt.where(PickupPointORM.route_id == UUID(route_id))
        except ValueError:
            return []

    rows = (await session.execute(stmt.order_by(PickupPointORM.route_id.asc(), PickupPointORM.sequence_no.asc()))).scalars().all()
    return [_pickup_point_to_dict(row) for row in rows]


@router.post("/pickup-points")
async def pickup_points_create(
    payload: PickupPointCreateRequest,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    zone_uuid = _parse_uuid(payload.zone_id)
    ward_uuid = _parse_uuid(payload.ward_id)
    route_uuid = _parse_uuid(payload.route_id)
    points = payload.pickup_points or []
    if not points:
        if payload.lat is None or payload.lng is None:
            raise HTTPException(status_code=422, detail="lat/lng or pickup_points is required")
        points = [PickupCoordinate(sequence_no=payload.sequence_no, lat=payload.lat, lng=payload.lng, pickup_name=payload.pickup_name)]

    rows: list[PickupPointORM] = []
    for index, point in enumerate(points, start=1):
        sequence_no = point.sequence_no or index
        rows.append(
            PickupPointORM(
                pickup_name=(point.pickup_name or payload.pickup_name or f"Pickup {sequence_no}").strip(),
                zone_id=zone_uuid,
                ward_id=ward_uuid,
                route_id=route_uuid,
                sequence_no=sequence_no,
                lat=point.lat,
                lng=point.lng,
                expected_pickup_time=(point.expected_pickup_time or payload.expected_pickup_time),
                pickup_radius_m=point.pickup_radius_m if point.pickup_radius_m is not None else payload.pickup_radius_m,
            )
        )
    session.add_all(rows)
    await session.commit()
    for row in rows:
        await session.refresh(row)
    mapped = [_pickup_point_to_dict(row) for row in rows]
    return mapped[0] if len(mapped) == 1 else {"items": mapped, "created": len(mapped)}


@router.put("/pickup-points/{pickup_point_id}")
async def pickup_points_update(
    pickup_point_id: str,
    payload: PickupPointUpdateRequest,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    pickup_uuid = _parse_uuid(pickup_point_id)
    if pickup_uuid is None:
        raise HTTPException(status_code=404, detail="pickup point not found")

    row = (await session.execute(select(PickupPointORM).where(PickupPointORM.id == pickup_uuid))).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="pickup point not found")

    if payload.pickup_name is not None:
        row.pickup_name = payload.pickup_name.strip()
    if payload.zone_id is not None:
        row.zone_id = _parse_uuid(payload.zone_id)
    if payload.ward_id is not None:
        row.ward_id = _parse_uuid(payload.ward_id)
    if payload.route_id is not None:
        row.route_id = _parse_uuid(payload.route_id)
    if payload.sequence_no is not None:
        row.sequence_no = payload.sequence_no
    if payload.lat is not None:
        row.lat = payload.lat
    if payload.lng is not None:
        row.lng = payload.lng
    if payload.expected_pickup_time is not None:
        row.expected_pickup_time = payload.expected_pickup_time.strip()
    if payload.pickup_radius_m is not None:
        row.pickup_radius_m = payload.pickup_radius_m

    await session.commit()
    await session.refresh(row)
    return _pickup_point_to_dict(row)


@router.delete("/pickup-points/{pickup_point_id}")
async def pickup_points_delete(
    pickup_point_id: str,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    pickup_uuid = _parse_uuid(pickup_point_id)
    if pickup_uuid is None:
        raise HTTPException(status_code=404, detail="pickup point not found")

    row = (await session.execute(select(PickupPointORM).where(PickupPointORM.id == pickup_uuid))).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="pickup point not found")

    await session.delete(row)
    await session.commit()
    return {"ok": True}


@router.get("/routes/{route_id}/pickup-points")
async def route_pickup_points(
    route_id: str,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    return await pickup_points_list(zone_id=None, ward_id=None, route_id=route_id, _=_, session=session)


@router.get("/tickets")
async def tickets_list(
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    category: str | None = Query(default=None),
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    stmt = select(TicketORM)
    if status:
        stmt = stmt.where(TicketORM.status == status.strip().lower())
    if priority:
        stmt = stmt.where(TicketORM.priority == priority.strip().lower())
    if category:
        stmt = stmt.where(TicketORM.category == category.strip().lower())

    rows = (await session.execute(stmt.order_by(TicketORM.created_at.desc()))).scalars().all()
    return [_ticket_to_dict(row) for row in rows]


@router.get("/tickets/{ticket_id}")
async def ticket_get(
    ticket_id: str,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    ticket_uuid = _parse_uuid(ticket_id)
    if ticket_uuid is None:
        raise HTTPException(status_code=404, detail="ticket not found")

    row = (await session.execute(select(TicketORM).where(TicketORM.id == ticket_uuid))).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="ticket not found")

    comments = (
        await session.execute(
            select(TicketCommentORM)
            .where(TicketCommentORM.ticket_id == ticket_uuid)
            .order_by(TicketCommentORM.created_at.asc())
        )
    ).scalars().all()
    return _ticket_to_dict(row, comments)


@router.post("/tickets")
async def ticket_create(
    payload: TicketCreateRequest,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    due_at = _parse_datetime(payload.due_date)

    row = TicketORM(
        title=payload.title.strip(),
        description=payload.description,
        category=payload.category,
        priority=payload.priority,
        status=payload.status,
        due_at=due_at,
        assigned_to=payload.assigned_to,
        created_by=payload.created_by,
        related_alert_id=payload.related_alert_id,
        related_truck_id=payload.related_truck_id,
        related_driver_id=payload.related_driver_id,
        escalation_level=payload.escalation_level,
        sla_breached=payload.sla_breached,
        metadata_json={},
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _ticket_to_dict(row)


@router.put("/tickets/{ticket_id}")
async def ticket_update(
    ticket_id: str,
    payload: TicketUpdateRequest,
    _: RoleContext = Depends(require_roles("admin", "ops")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    ticket_uuid = _parse_uuid(ticket_id)
    if ticket_uuid is None:
        raise HTTPException(status_code=404, detail="ticket not found")

    row = (await session.execute(select(TicketORM).where(TicketORM.id == ticket_uuid))).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="ticket not found")

    if payload.title is not None:
        row.title = payload.title.strip()
    if payload.description is not None:
        row.description = payload.description
    if payload.category is not None:
        row.category = payload.category
    if payload.priority is not None:
        row.priority = payload.priority
    if payload.status is not None:
        row.status = payload.status
    if payload.due_date is not None:
        row.due_at = _parse_datetime(payload.due_date)
    if payload.assigned_to is not None:
        row.assigned_to = payload.assigned_to
    if payload.created_by is not None:
        row.created_by = payload.created_by
    if payload.related_alert_id is not None:
        row.related_alert_id = payload.related_alert_id
    if payload.related_truck_id is not None:
        row.related_truck_id = payload.related_truck_id
    if payload.related_driver_id is not None:
        row.related_driver_id = payload.related_driver_id
    if payload.escalation_level is not None:
        row.escalation_level = payload.escalation_level
    if payload.sla_breached is not None:
        row.sla_breached = payload.sla_breached

    await session.commit()
    await session.refresh(row)
    return _ticket_to_dict(row)


@router.get("/tickets/{ticket_id}/comments")
async def ticket_comments_list(
    ticket_id: str,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    ticket_uuid = _parse_uuid(ticket_id)
    if ticket_uuid is None:
        raise HTTPException(status_code=404, detail="ticket not found")

    exists = (await session.execute(select(TicketORM.id).where(TicketORM.id == ticket_uuid))).first()
    if exists is None:
        raise HTTPException(status_code=404, detail="ticket not found")

    rows = (
        await session.execute(
            select(TicketCommentORM)
            .where(TicketCommentORM.ticket_id == ticket_uuid)
            .order_by(TicketCommentORM.created_at.asc())
        )
    ).scalars().all()
    return [_ticket_comment_to_dict(row) for row in rows]


@router.post("/tickets/{ticket_id}/comments")
async def ticket_comment_create(
    ticket_id: str,
    payload: TicketCommentCreateRequest,
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    ticket_uuid = _parse_uuid(ticket_id)
    if ticket_uuid is None:
        raise HTTPException(status_code=404, detail="ticket not found")

    exists = (await session.execute(select(TicketORM.id).where(TicketORM.id == ticket_uuid))).first()
    if exists is None:
        raise HTTPException(status_code=404, detail="ticket not found")

    content = (payload.content or payload.comment or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="comment is required")

    row = TicketCommentORM(
        ticket_id=ticket_uuid,
        author=payload.author,
        content=content,
        is_internal=payload.is_internal,
    )
    session.add(row)

    ticket_row = (await session.execute(select(TicketORM).where(TicketORM.id == ticket_uuid))).scalars().first()
    if ticket_row is not None:
        ticket_row.updated_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(row)
    return _ticket_comment_to_dict(row)


@router.get("/tickets/statistics/summary")
async def tickets_statistics_summary(
    _: RoleContext = Depends(require_roles("admin", "ops", "viewer")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    total = int((await session.execute(select(func.count(TicketORM.id)))).scalar() or 0)
    open_count = int((await session.execute(select(func.count(TicketORM.id)).where(TicketORM.status == "open"))).scalar() or 0)
    in_progress_count = int(
        (await session.execute(select(func.count(TicketORM.id)).where(TicketORM.status == "in_progress"))).scalar() or 0
    )
    pending_count = int((await session.execute(select(func.count(TicketORM.id)).where(TicketORM.status == "pending"))).scalar() or 0)
    resolved_count = int((await session.execute(select(func.count(TicketORM.id)).where(TicketORM.status == "resolved"))).scalar() or 0)
    closed_count = int((await session.execute(select(func.count(TicketORM.id)).where(TicketORM.status == "closed"))).scalar() or 0)
    breached_count = int((await session.execute(select(func.count(TicketORM.id)).where(TicketORM.sla_breached.is_(True)))).scalar() or 0)
    return {
        "total": total,
        "open": open_count,
        "in_progress": in_progress_count,
        "pending": pending_count,
        "resolved": resolved_count,
        "closed": closed_count,
        "sla_breached": breached_count,
    }
