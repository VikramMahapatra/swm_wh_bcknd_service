from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime, timedelta
from ..database.database import get_db
from ..models import models
from ..schemas import schemas

router = APIRouter(prefix="/alerts", tags=["alerts"])

def _serialize_alert_with_names(
    alert: models.Alert,
    registration_number: str = None,
    route_name: str = None,
    zone_name: str = None,
    ward_name: str = None,
):
    data = alert.__dict__.copy()
    data.pop("_sa_instance_state", None)
    data["truck_registration_number"] = registration_number
    data["route_name"] = route_name
    data["zone_name"] = zone_name
    data["ward_name"] = ward_name
    return data

@router.get("/", response_model=List[schemas.AlertWithNames])
def get_alerts(
    status: str = None,
    severity: str = None,
    truck_id: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(
        models.Alert,
        models.Truck.registration_number,
        models.Route.name,
        models.Zone.name,
        models.Ward.name,
    ).outerjoin(models.Truck, models.Alert.truck_id == models.Truck.id)
    query = query.outerjoin(models.Route, models.Alert.route_id == models.Route.id)
    query = query.outerjoin(models.Zone, models.Alert.zone_id == models.Zone.id)
    query = query.outerjoin(models.Ward, models.Alert.ward_id == models.Ward.id)
    
    if status:
        query = query.filter(models.Alert.status == status)
    if severity:
        query = query.filter(models.Alert.severity == severity)
    if truck_id:
        query = query.filter(models.Alert.truck_id == truck_id)
    
    alerts = query.order_by(models.Alert.timestamp.desc()).all()
    return [
        _serialize_alert_with_names(alert, registration_number, route_name, zone_name, ward_name)
        for alert, registration_number, route_name, zone_name, ward_name in alerts
    ]

@router.post("/", response_model=schemas.Alert)
def create_alert(alert: schemas.AlertCreate, db: Session = Depends(get_db)):
    db_alert = models.Alert(**alert.dict())
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

@router.get("/active", response_model=List[schemas.AlertWithNames])
def get_active_alerts(db: Session = Depends(get_db)):
    """Get all active alerts"""
    alerts = db.query(
        models.Alert,
        models.Truck.registration_number,
        models.Route.name,
        models.Zone.name,
        models.Ward.name,
    ).outerjoin(models.Truck, models.Alert.truck_id == models.Truck.id)
    alerts = alerts.outerjoin(models.Route, models.Alert.route_id == models.Route.id)
    alerts = alerts.outerjoin(models.Zone, models.Alert.zone_id == models.Zone.id)
    alerts = alerts.outerjoin(models.Ward, models.Alert.ward_id == models.Ward.id)
    alerts = alerts.filter(models.Alert.status == "active").order_by(models.Alert.timestamp.desc()).all()
    return [
        _serialize_alert_with_names(alert, registration_number, route_name, zone_name, ward_name)
        for alert, registration_number, route_name, zone_name, ward_name in alerts
    ]

@router.get("/expiry", response_model=dict)
def get_expiry_alerts(db: Session = Depends(get_db)):
    """Get trucks with expiring documents"""
    today = datetime.now().strftime("%Y-%m-%d")
    thirty_days_later = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    trucks = db.query(models.Truck).all()
    
    insurance_expiring = []
    fitness_expiring = []
    
    for truck in trucks:
        if truck.insurance_expiry and truck.insurance_expiry <= thirty_days_later:
            insurance_expiring.append({
                "truck_id": truck.id,
                "registration": truck.registration_number,
                "expiry_date": truck.insurance_expiry
            })
        
        if truck.fitness_expiry and truck.fitness_expiry <= thirty_days_later:
            fitness_expiring.append({
                "truck_id": truck.id,
                "registration": truck.registration_number,
                "expiry_date": truck.fitness_expiry
            })
    
    return {
        "insurance_expiring": insurance_expiring,
        "fitness_expiring": fitness_expiring
    }
