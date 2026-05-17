from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Zone Schemas
class ZoneBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    supervisor_name: Optional[str] = None
    supervisor_phone: Optional[str] = None
    total_wards: int = 0
    status: str = "active"

class ZoneCreate(ZoneBase):
    id: str

class Zone(ZoneBase):
    id: str
    
    class Config:
        from_attributes = True

# Ward Schemas
class WardBase(BaseModel):
    name: str
    code: str
    zone_id: str
    population: int = 0
    area: float = 0.0
    total_pickup_points: int = 0
    status: str = "active"

class WardCreate(WardBase):
    id: str

class Ward(WardBase):
    id: str
    
    class Config:
        from_attributes = True

# Vendor Schemas
class VendorBase(BaseModel):
    name: str
    company_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    gst_number: Optional[str] = None
    contract_start: Optional[str] = None
    contract_end: Optional[str] = None
    status: str = "active"
    supervisor_name: Optional[str] = None
    supervisor_phone: Optional[str] = None

class VendorCreate(VendorBase):
    id: str

class Vendor(VendorBase):
    id: str
    
    class Config:
        from_attributes = True

# Driver Schemas
class DriverBase(BaseModel):
    name: str
    phone: Optional[str] = None
    license_number: Optional[str] = None
    license_expiry: Optional[str] = Field(None, serialization_alias="licenseExpiry")
    vendor_id: str
    status: str = "active"

class DriverCreate(DriverBase):
    id: str

class Driver(DriverBase):
    id: str
    
    class Config:
        from_attributes = True
        populate_by_name = True

# Truck Schemas
class TruckBase(BaseModel):
    registration_number: str
    type: str
    capacity: float
    capacity_unit: str
    route_type: str
    vendor_id: str
    driver_id: Optional[str] = None
    imei_number: str
    fuel_type: str
    manufacturing_year: int
    insurance_expiry: str = Field(..., serialization_alias="insuranceExpiry")
    fitness_expiry: str = Field(..., serialization_alias="fitnessExpiry")
    status: str = "active"
    last_service_date: Optional[str] = None
    is_spare: bool = False
    zone_id: Optional[str] = None
    ward_id: Optional[str] = None
    assigned_route_id: Optional[str] = None

class TruckCreate(TruckBase):
    id: str

class TruckAssignRoute(BaseModel):
    assigned_route_id: Optional[str] = None

class TruckLive(BaseModel):
    id: str
    registration_number: str
    type: str
    route_type: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    current_status: str = "idle"
    speed: float = 0.0
    trips_completed: int = 0
    trips_allowed: int = 5
    driver_name: Optional[str] = None
    route_name: Optional[str] = None
    vendor_id: str
    zone_id: Optional[str] = None
    ward_id: Optional[str] = None
    is_spare: bool = False
    last_update: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class Truck(TruckBase):
    id: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    current_status: str = "idle"
    speed: float = 0.0
    trips_completed: int = 0
    trips_allowed: int = 5
    last_update: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True

# Route Schemas
class RouteBase(BaseModel):
    name: str
    code: str
    type: str
    ward_id: str
    zone_id: str
    total_pickup_points: int = 0
    estimated_distance: float = 0.0
    estimated_time: int = 0
    status: str = "active"

class RouteCreate(RouteBase):
    id: str

class Route(RouteBase):
    id: str
    pickup_points: List = []
    
    class Config:
        from_attributes = True

# Pickup Point Schemas
class PickupPointBase(BaseModel):
    point_code: str
    name: str
    address: Optional[str] = None
    latitude: float
    longitude: float
    route_id: str
    ward_id: str
    waste_type: str
    type: str
    expected_pickup_time: Optional[str] = None
    schedule: Optional[str] = None
    geofence_radius: int = 30
    status: str = "active"
    last_collection: Optional[str] = None

class PickupPointCreate(PickupPointBase):
    id: str

class PickupPoint(PickupPointBase):
    id: str
    
    class Config:
        from_attributes = True

# Alert Schemas
class AlertBase(BaseModel):
    truck_id: str
    route_id: Optional[str] = None
    zone_id: Optional[str] = None
    ward_id: Optional[str] = None
    alert_type: str
    severity: str
    message: str
    location: Optional[str] = None
    date: Optional[str] = None
    status: str = "active"

class AlertCreate(AlertBase):
    pass

class Alert(AlertBase):
    id: int
    timestamp: datetime
    resolved_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class AlertWithTruck(Alert):
    truck_registration_number: Optional[str] = None

class AlertWithNames(AlertWithTruck):
    route_name: Optional[str] = None
    zone_name: Optional[str] = None
    ward_name: Optional[str] = None

# Response Models
class TruckWithDetails(Truck):
    vendor_name: Optional[str] = None
    driver_name: Optional[str] = None
    route_name: Optional[str] = None
    zone_name: Optional[str] = None
    ward_name: Optional[str] = None

# User Schemas
class UserBase(BaseModel):
    email: str
    name: str
    role: str = "user"
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class User(UserBase):
    id: str
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

# Ticket Schemas
class TicketBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: str
    priority: str = "medium"
    status: str = "open"
    reporter_name: Optional[str] = None
    reporter_phone: Optional[str] = None
    reporter_email: Optional[str] = None
    location: Optional[str] = None
    zone_id: Optional[str] = None
    ward_id: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None

class TicketCreate(TicketBase):
    pass

class Ticket(TicketBase):
    id: str
    ticket_number: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    sla_breached: bool = False
    
    class Config:
        from_attributes = True

class TicketCommentBase(BaseModel):
    comment: str
    is_internal: bool = False

class TicketCommentCreate(TicketCommentBase):
    ticket_id: str
    user_id: str

class TicketComment(TicketCommentBase):
    id: int
    ticket_id: str
    user_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Twitter Mention Schemas
class TwitterMentionBase(BaseModel):
    tweet_id: str
    author: str
    author_name: str
    content: str
    timestamp: datetime
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    sentiment: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None

class TwitterMentionCreate(TwitterMentionBase):
    pass

class TwitterMention(TwitterMentionBase):
    id: str
    is_responded: bool = False
    response_text: Optional[str] = None
    response_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Analytics Schemas
class AnalyticsBase(BaseModel):
    date: datetime
    metric_name: str
    metric_value: float
    metric_type: str
    zone_id: Optional[str] = None
    vendor_id: Optional[str] = None
    additional_data: Optional[str] = None

class AnalyticsCreate(AnalyticsBase):
    pass

class Analytics(AnalyticsBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# GTC Checkpoint Schemas
class GtcCheckpointBase(BaseModel):
    truck_id: str
    arrived_at: Optional[datetime] = None
    is_dry: bool = False
    is_wet: bool = False
    is_metal: bool = False
    is_plastic: bool = False
    is_sanitary: bool = False
    truck_cleanliness_score: Optional[int] = None
    gtc_cleanliness_score: Optional[int] = None
    remarks: Optional[str] = None

class GtcCheckpointCreate(GtcCheckpointBase):
    pass

class GtcCheckpoint(GtcCheckpointBase):
    id: int
    arrived_at: datetime

    class Config:
        from_attributes = True

class GtcCheckpointWithTruck(GtcCheckpoint):
    truck_registration_number: Optional[str] = None
