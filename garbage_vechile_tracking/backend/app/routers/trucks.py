from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database.database import get_db
from ..models import models
from ..schemas import schemas

router = APIRouter(prefix="/trucks", tags=["trucks"])

@router.get("/", response_model=List[schemas.Truck])
def get_trucks(
    zone_id: str = None,
    vendor_id: str = None,
    status: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Truck)
    
    if zone_id:
        query = query.filter(models.Truck.zone_id == zone_id)
    if vendor_id:
        query = query.filter(models.Truck.vendor_id == vendor_id)
    if status:
        query = query.filter(models.Truck.status == status)
    
    trucks = query.all()
    return trucks

@router.get("/live", response_model=List[schemas.TruckLive])
def get_live_trucks(db: Session = Depends(get_db)):
    """Get all trucks with live tracking data"""
    trucks = db.query(models.Truck).filter(
        models.Truck.status == "active"
    ).all()
    
    result = []
    for truck in trucks:
        driver = db.query(models.Driver).filter(models.Driver.id == truck.driver_id).first()
        route = db.query(models.Route).filter(models.Route.id == truck.assigned_route_id).first()
        
        truck_live = schemas.TruckLive(
            id=truck.id,
            registration_number=truck.registration_number,
            type=truck.type.value,
            route_type=truck.route_type.value,
            latitude=truck.latitude,
            longitude=truck.longitude,
            current_status=truck.current_status.value if truck.current_status else "idle",
            speed=truck.speed or 0.0,
            trips_completed=truck.trips_completed,
            trips_allowed=truck.trips_allowed,
            driver_name=driver.name if driver else None,
            route_name=route.name if route else "Unassigned",
            vendor_id=truck.vendor_id,
            zone_id=truck.zone_id,
            ward_id=truck.ward_id,
            is_spare=truck.is_spare,
            last_update=truck.last_update
        )
        result.append(truck_live)
    
    return result

@router.get("/spare", response_model=List[schemas.Truck])
def get_spare_trucks(db: Session = Depends(get_db)):
    """Get all spare trucks"""
    trucks = db.query(models.Truck).filter(
        models.Truck.is_spare == True
    ).all()
    return trucks

@router.get("/{truck_id}", response_model=schemas.Truck)
def get_truck(truck_id: str, db: Session = Depends(get_db)):
    truck = db.query(models.Truck).filter(models.Truck.id == truck_id).first()
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")
    return truck

@router.post("/", response_model=schemas.Truck)
def create_truck(truck: schemas.TruckCreate, db: Session = Depends(get_db)):
    db_truck = models.Truck(**truck.dict())
    db.add(db_truck)
    db.commit()
    db.refresh(db_truck)
    return db_truck

@router.put("/{truck_id}", response_model=schemas.Truck)
def update_truck(truck_id: str, truck: schemas.TruckBase, db: Session = Depends(get_db)):
    db_truck = db.query(models.Truck).filter(models.Truck.id == truck_id).first()
    if not db_truck:
        raise HTTPException(status_code=404, detail="Truck not found")
    
    for key, value in truck.dict(exclude_unset=True).items():
        setattr(db_truck, key, value)
    
    db.commit()
    db.refresh(db_truck)
    return db_truck

@router.put("/{truck_id}/assign-route", response_model=schemas.Truck)
def assign_route(truck_id: str, payload: schemas.TruckAssignRoute, db: Session = Depends(get_db)):
    db_truck = db.query(models.Truck).filter(models.Truck.id == truck_id).first()
    if not db_truck:
        raise HTTPException(status_code=404, detail="Truck not found")

    if payload.assigned_route_id:
        route = db.query(models.Route).filter(models.Route.id == payload.assigned_route_id).first()
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        db_truck.assigned_route_id = route.id
        db_truck.zone_id = route.zone_id
        db_truck.ward_id = route.ward_id
    else:
        db_truck.assigned_route_id = None

    db.commit()
    db.refresh(db_truck)
    return db_truck
