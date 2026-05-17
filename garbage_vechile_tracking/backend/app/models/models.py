from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from ..database.database import Base

class TruckStatus(str, enum.Enum):
    MOVING = "moving"
    IDLE = "idle"
    DUMPING = "dumping"
    OFFLINE = "offline"
    BREAKDOWN = "breakdown"

class TruckType(str, enum.Enum):
    MINI_TRUCK = "mini-truck"
    COMPACTOR = "compactor"
    DUMPER = "dumper"
    OPEN_TRUCK = "open-truck"

class RouteType(str, enum.Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"

class Zone(Base):
    __tablename__ = "zones"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)
    description = Column(String)
    supervisor_name = Column(String)
    supervisor_phone = Column(String)
    total_wards = Column(Integer)
    status = Column(String, default="active")
    
    wards = relationship("Ward", back_populates="zone")
    trucks = relationship("Truck", back_populates="zone")
    routes = relationship("Route", back_populates="zone")

class Ward(Base):
    __tablename__ = "wards"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)
    zone_id = Column(String, ForeignKey("zones.id"))
    population = Column(Integer)
    area = Column(Float)
    total_pickup_points = Column(Integer)
    status = Column(String, default="active")
    
    zone = relationship("Zone", back_populates="wards")
    trucks = relationship("Truck", back_populates="ward")
    routes = relationship("Route", back_populates="ward")
    pickup_points = relationship("PickupPoint", back_populates="ward")

class Vendor(Base):
    __tablename__ = "vendors"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    company_name = Column(String)
    phone = Column(String)
    email = Column(String)
    address = Column(String)
    gst_number = Column(String)
    contract_start = Column(String)
    contract_end = Column(String)
    status = Column(String, default="active")
    supervisor_name = Column(String)
    supervisor_phone = Column(String)
    
    trucks = relationship("Truck", back_populates="vendor")

class Driver(Base):
    __tablename__ = "drivers"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    phone = Column(String)
    license_number = Column(String)
    license_expiry = Column(String)
    vendor_id = Column(String, ForeignKey("vendors.id"))
    status = Column(String, default="active")
    
    trucks = relationship("Truck", back_populates="driver")

class Truck(Base):
    __tablename__ = "trucks"
    
    id = Column(String, primary_key=True)
    registration_number = Column(String, nullable=False, unique=True)
    type = Column(SQLEnum(TruckType), nullable=False)
    capacity = Column(Float)
    capacity_unit = Column(String)
    route_type = Column(SQLEnum(RouteType))
    vendor_id = Column(String, ForeignKey("vendors.id"))
    driver_id = Column(String, ForeignKey("drivers.id"), nullable=True)
    imei_number = Column(String)
    fuel_type = Column(String)
    manufacturing_year = Column(Integer)
    insurance_expiry = Column(String)
    fitness_expiry = Column(String)
    status = Column(String, default="active")
    last_service_date = Column(String)
    is_spare = Column(Boolean, default=False)
    zone_id = Column(String, ForeignKey("zones.id"))
    ward_id = Column(String, ForeignKey("wards.id"))
    assigned_route_id = Column(String, ForeignKey("routes.id"), nullable=True)
    
    # Live tracking fields
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    current_status = Column(SQLEnum(TruckStatus), default=TruckStatus.IDLE)
    speed = Column(Float, default=0.0)
    trips_completed = Column(Integer, default=0)
    trips_allowed = Column(Integer, default=5)
    last_update = Column(DateTime, default=datetime.utcnow)
    
    vendor = relationship("Vendor", back_populates="trucks")
    driver = relationship("Driver", back_populates="trucks")
    zone = relationship("Zone", back_populates="trucks")
    ward = relationship("Ward", back_populates="trucks")
    route = relationship("Route", back_populates="trucks")

class Route(Base):
    __tablename__ = "routes"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    code = Column(String)
    type = Column(SQLEnum(RouteType))
    ward_id = Column(String, ForeignKey("wards.id"))
    zone_id = Column(String, ForeignKey("zones.id"))
    total_pickup_points = Column(Integer)
    estimated_distance = Column(Float)
    estimated_time = Column(Integer)
    status = Column(String, default="active")
    
    ward = relationship("Ward", back_populates="routes")
    zone = relationship("Zone", back_populates="routes")
    trucks = relationship("Truck", back_populates="route")
    pickup_points = relationship("PickupPoint", back_populates="route")

class PickupPoint(Base):
    __tablename__ = "pickup_points"
    
    id = Column(String, primary_key=True)
    point_code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    address = Column(String)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    route_id = Column(String, ForeignKey("routes.id"))
    ward_id = Column(String, ForeignKey("wards.id"))
    waste_type = Column(String)
    type = Column(String)
    expected_pickup_time = Column(String)
    schedule = Column(String)
    geofence_radius = Column(Integer)
    status = Column(String, default="active")
    last_collection = Column(String, nullable=True)
    
    route = relationship("Route", back_populates="pickup_points")
    ward = relationship("Ward", back_populates="pickup_points")

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    truck_id = Column(String, ForeignKey("trucks.id"))
    route_id = Column(String, ForeignKey("routes.id"), nullable=True)
    zone_id = Column(String, ForeignKey("zones.id"), nullable=True)
    ward_id = Column(String, ForeignKey("wards.id"), nullable=True)
    alert_type = Column(String)
    severity = Column(String)
    message = Column(String)
    location = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    date = Column(String, nullable=True)
    status = Column(String, default="active")
    resolved_at = Column(DateTime, nullable=True)

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user")  # admin or user
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(String, primary_key=True)
    ticket_number = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    category = Column(String)  # complaint, request, feedback, query
    priority = Column(String, default="medium")  # low, medium, high, critical
    status = Column(String, default="open")  # open, in_progress, pending, resolved, closed
    reporter_name = Column(String)
    reporter_phone = Column(String)
    reporter_email = Column(String)
    location = Column(String)
    zone_id = Column(String, ForeignKey("zones.id"), nullable=True)
    ward_id = Column(String, ForeignKey("wards.id"), nullable=True)
    assigned_to = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    sla_breached = Column(Boolean, default=False)

class TicketComment(Base):
    __tablename__ = "ticket_comments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String, ForeignKey("tickets.id"))
    user_id = Column(String, ForeignKey("users.id"))
    comment = Column(String, nullable=False)
    is_internal = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class TwitterMention(Base):
    __tablename__ = "twitter_mentions"
    
    id = Column(String, primary_key=True)
    tweet_id = Column(String, unique=True, nullable=False)
    author = Column(String)
    author_name = Column(String)
    content = Column(String, nullable=False)
    timestamp = Column(DateTime)
    likes = Column(Integer, default=0)
    retweets = Column(Integer, default=0)
    replies = Column(Integer, default=0)
    sentiment = Column(String)  # positive, negative, neutral
    category = Column(String)  # complaint, appreciation, query, suggestion
    location = Column(String, nullable=True)
    is_responded = Column(Boolean, default=False)
    response_text = Column(String, nullable=True)
    response_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Analytics(Base):
    __tablename__ = "analytics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)
    metric_name = Column(String, nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_type = Column(String)  # performance, efficiency, compliance, prediction
    zone_id = Column(String, ForeignKey("zones.id"), nullable=True)
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=True)
    additional_data = Column(String, nullable=True)  # JSON string for additional data
    created_at = Column(DateTime, default=datetime.utcnow)

class ReportData(Base):
    __tablename__ = "report_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String, nullable=False, unique=True)
    payload = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class GtcCheckpointEntry(Base):
    __tablename__ = "gtc_checkpoint_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    truck_id = Column(String, ForeignKey("trucks.id"), nullable=False, index=True)
    arrived_at = Column(DateTime, default=datetime.utcnow, index=True)
    is_dry = Column(Boolean, default=False)
    is_wet = Column(Boolean, default=False)
    is_metal = Column(Boolean, default=False)
    is_plastic = Column(Boolean, default=False)
    is_sanitary = Column(Boolean, default=False)
    truck_cleanliness_score = Column(Integer, nullable=True)
    gtc_cleanliness_score = Column(Integer, nullable=True)
    remarks = Column(String, nullable=True)

    truck = relationship("Truck")
