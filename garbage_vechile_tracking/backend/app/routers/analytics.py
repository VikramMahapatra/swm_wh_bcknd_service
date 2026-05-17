from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta
from ..database.database import get_db
from ..models import models
from ..schemas import schemas

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/", response_model=List[schemas.Analytics])
def get_analytics(
    metric_type: Optional[str] = None,
    zone_id: Optional[str] = None,
    vendor_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Analytics)
    
    if metric_type:
        query = query.filter(models.Analytics.metric_type == metric_type)
    if zone_id:
        query = query.filter(models.Analytics.zone_id == zone_id)
    if vendor_id:
        query = query.filter(models.Analytics.vendor_id == vendor_id)
    if start_date:
        query = query.filter(models.Analytics.date >= start_date)
    if end_date:
        query = query.filter(models.Analytics.date <= end_date)
    
    analytics = query.order_by(models.Analytics.date.desc()).all()
    return analytics

@router.post("/", response_model=schemas.Analytics)
def create_analytics(analytic: schemas.AnalyticsCreate, db: Session = Depends(get_db)):
    db_analytic = models.Analytics(**analytic.dict())
    db.add(db_analytic)
    db.commit()
    db.refresh(db_analytic)
    return db_analytic

@router.get("/performance/overview")
def get_performance_overview(db: Session = Depends(get_db)):
    """Get overall system performance metrics"""
    today = datetime.utcnow().date()
    last_7_days = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)
    
    # Collection efficiency
    trucks = db.query(models.Truck).filter(models.Truck.status == "active").all()
    total_trips_completed = sum(truck.trips_completed for truck in trucks)
    total_trips_allowed = sum(truck.trips_allowed for truck in trucks)
    efficiency = (total_trips_completed / total_trips_allowed * 100) if total_trips_allowed > 0 else 0
    
    # Active trucks vs total
    total_trucks = len(trucks)
    active_trucks = len([t for t in trucks if t.current_status == models.TruckStatus.MOVING])
    
    # Alerts summary
    active_alerts = db.query(models.Alert).filter(models.Alert.status == "active").count()
    
    return {
        "collection_efficiency": round(efficiency, 2),
        "total_trucks": total_trucks,
        "active_trucks": active_trucks,
        "idle_trucks": total_trucks - active_trucks,
        "active_alerts": active_alerts,
        "total_trips_completed": total_trips_completed,
        "total_trips_allowed": total_trips_allowed
    }

@router.get("/performance/zone-wise")
def get_zone_wise_performance(db: Session = Depends(get_db)):
    """Get performance metrics grouped by zone"""
    zones = db.query(models.Zone).all()
    
    zone_performance = []
    for zone in zones:
        trucks = db.query(models.Truck).filter(models.Truck.zone_id == zone.id).all()
        active_trucks = len([t for t in trucks if t.current_status == models.TruckStatus.MOVING])
        
        total_trips = sum(truck.trips_completed for truck in trucks)
        allowed_trips = sum(truck.trips_allowed for truck in trucks)
        efficiency = (total_trips / allowed_trips * 100) if allowed_trips > 0 else 0
        
        zone_performance.append({
            "zone_id": zone.id,
            "zone_name": zone.name,
            "total_trucks": len(trucks),
            "active_trucks": active_trucks,
            "total_trips_completed": total_trips,
            "collection_efficiency": round(efficiency, 2)
        })
    
    return zone_performance

@router.get("/performance/vendor-wise")
def get_vendor_wise_performance(db: Session = Depends(get_db)):
    """Get performance metrics grouped by vendor"""
    vendors = db.query(models.Vendor).all()
    
    vendor_performance = []
    for vendor in vendors:
        trucks = db.query(models.Truck).filter(models.Truck.vendor_id == vendor.id).all()
        active_trucks = len([t for t in trucks if t.current_status == models.TruckStatus.MOVING])
        
        total_trips = sum(truck.trips_completed for truck in trucks)
        allowed_trips = sum(truck.trips_allowed for truck in trucks)
        efficiency = (total_trips / allowed_trips * 100) if allowed_trips > 0 else 0
        
        vendor_performance.append({
            "vendor_id": vendor.id,
            "vendor_name": vendor.name,
            "total_trucks": len(trucks),
            "active_trucks": active_trucks,
            "total_trips_completed": total_trips,
            "collection_efficiency": round(efficiency, 2)
        })
    
    return vendor_performance

@router.get("/predictions/maintenance")
def get_maintenance_predictions(db: Session = Depends(get_db)):
    """Predict trucks that may need maintenance soon"""
    trucks = db.query(models.Truck).filter(models.Truck.status == "active").all()
    
    # Simple prediction based on trips completed vs allowed
    maintenance_predictions = []
    for truck in trucks:
        if truck.trips_completed >= truck.trips_allowed * 0.9:
            maintenance_predictions.append({
                "truck_id": truck.id,
                "registration_number": truck.registration_number,
                "trips_completed": truck.trips_completed,
                "trips_allowed": truck.trips_allowed,
                "utilization": round((truck.trips_completed / truck.trips_allowed) * 100, 2),
                "recommendation": "Schedule maintenance soon - high utilization"
            })
    
    return maintenance_predictions

@router.get("/trends/collection-rate")
def get_collection_rate_trends(db: Session = Depends(get_db)):
    """Get collection rate trends over time"""
    # For now, return current snapshot
    # In production, this would query historical data
    zones = db.query(models.Zone).all()
    
    trends = []
    for zone in zones:
        wards = db.query(models.Ward).filter(models.Ward.zone_id == zone.id).all()
        total_pickup_points = sum(ward.total_pickup_points for ward in wards)
        
        # Mock completion rate
        completion_rate = 85 + (hash(zone.id) % 15)  # 85-100%
        
        trends.append({
            "zone_id": zone.id,
            "zone_name": zone.name,
            "total_pickup_points": total_pickup_points,
            "collection_rate": completion_rate,
            "trend": "improving" if completion_rate > 90 else "stable"
        })
    
    return trends
