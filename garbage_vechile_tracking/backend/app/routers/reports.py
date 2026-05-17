from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import json
from ..database.database import get_db
from ..models import models

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/statistics")
def get_statistics(db: Session = Depends(get_db)):
    """Get overall system statistics"""
    total_trucks = db.query(func.count(models.Truck.id)).scalar()
    active_trucks = db.query(func.count(models.Truck.id)).filter(
        models.Truck.status == "active",
        models.Truck.current_status == models.TruckStatus.MOVING
    ).scalar()
    
    total_zones = db.query(func.count(models.Zone.id)).scalar()
    total_wards = db.query(func.count(models.Ward.id)).scalar()
    total_vendors = db.query(func.count(models.Vendor.id)).scalar()
    total_routes = db.query(func.count(models.Route.id)).scalar()
    total_pickup_points = db.query(func.count(models.PickupPoint.id)).scalar()
    
    active_alerts = db.query(func.count(models.Alert.id)).filter(
        models.Alert.status == "active"
    ).scalar()
    
    return {
        "total_trucks": total_trucks,
        "active_trucks": active_trucks,
        "idle_trucks": total_trucks - active_trucks,
        "total_zones": total_zones,
        "total_wards": total_wards,
        "total_vendors": total_vendors,
        "total_routes": total_routes,
        "total_pickup_points": total_pickup_points,
        "active_alerts": active_alerts
    }

@router.get("/zone-performance")
def get_zone_performance(db: Session = Depends(get_db)):
    """Get performance metrics by zone"""
    zones = db.query(models.Zone).all()
    
    zone_data = []
    for zone in zones:
        trucks_count = db.query(func.count(models.Truck.id)).filter(
            models.Truck.zone_id == zone.id
        ).scalar()
        
        active_trucks = db.query(func.count(models.Truck.id)).filter(
            models.Truck.zone_id == zone.id,
            models.Truck.current_status == models.TruckStatus.MOVING
        ).scalar()
        
        total_trips = db.query(func.sum(models.Truck.trips_completed)).filter(
            models.Truck.zone_id == zone.id
        ).scalar() or 0
        
        zone_data.append({
            "zone_id": zone.id,
            "zone_name": zone.name,
            "total_trucks": trucks_count,
            "active_trucks": active_trucks,
            "total_trips": total_trips,
            "efficiency": round((active_trucks / trucks_count * 100) if trucks_count > 0 else 0, 2)
        })
    
    return zone_data

@router.get("/vendor-performance")
def get_vendor_performance(db: Session = Depends(get_db)):
    """Get performance metrics by vendor"""
    vendors = db.query(models.Vendor).all()
    
    vendor_data = []
    for vendor in vendors:
        trucks_count = db.query(func.count(models.Truck.id)).filter(
            models.Truck.vendor_id == vendor.id
        ).scalar()
        
        active_trucks = db.query(func.count(models.Truck.id)).filter(
            models.Truck.vendor_id == vendor.id,
            models.Truck.current_status == models.TruckStatus.MOVING
        ).scalar()
        
        total_trips = db.query(func.sum(models.Truck.trips_completed)).filter(
            models.Truck.vendor_id == vendor.id
        ).scalar() or 0
        
        vendor_data.append({
            "vendor_id": vendor.id,
            "vendor_name": vendor.name,
            "total_trucks": trucks_count,
            "active_trucks": active_trucks,
            "total_trips": total_trips
        })
    
    return vendor_data

@router.get("/collection-efficiency")
def get_collection_efficiency(db: Session = Depends(get_db)):
    """Calculate overall collection efficiency"""
    trucks = db.query(models.Truck).filter(models.Truck.status == "active").all()
    
    total_trips_completed = sum(truck.trips_completed for truck in trucks)
    total_trips_allowed = sum(truck.trips_allowed for truck in trucks)
    
    efficiency = (total_trips_completed / total_trips_allowed * 100) if total_trips_allowed > 0 else 0
    
    return {
        "total_trips_completed": total_trips_completed,
        "total_trips_allowed": total_trips_allowed,
        "efficiency_percentage": round(efficiency, 2),
        "total_active_trucks": len(trucks)
    }

@router.get("/data")
def get_reports_data(
    report_type: str = Query(default=None, description="Optional comma-separated report types"),
    db: Session = Depends(get_db)
):
    query = db.query(models.ReportData)
    if report_type:
        types = [value.strip() for value in report_type.split(",") if value.strip()]
        query = query.filter(models.ReportData.report_type.in_(types))

    rows = query.all()
    payload = {}
    for row in rows:
        try:
            payload[row.report_type] = json.loads(row.payload)
        except json.JSONDecodeError:
            payload[row.report_type] = []

    return payload
