from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from ..database.database import get_db
from ..models import models
from ..schemas import schemas

router = APIRouter(prefix="/routes", tags=["routes"])

@router.get("/")
def get_routes(
    zone_id: str = None,
    ward_id: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Route)
    
    if zone_id:
        query = query.filter(models.Route.zone_id == zone_id)
    if ward_id:
        query = query.filter(models.Route.ward_id == ward_id)
    
    routes = query.all()
    
    # Manually construct response with pickup points
    result = []
    for route in routes:
        pickup_points = db.query(models.PickupPoint).filter(
            models.PickupPoint.route_id == route.id
        ).all()
        
        route_dict = {
            "id": route.id,
            "name": route.name,
            "code": route.code,
            "type": route.type,
            "ward_id": route.ward_id,
            "zone_id": route.zone_id,
            "total_pickup_points": route.total_pickup_points,
            "estimated_distance": route.estimated_distance,
            "estimated_time": route.estimated_time,
            "status": route.status,
            "pickup_points": [
                {
                    "id": pp.id,
                    "point_code": pp.point_code,
                    "name": pp.name,
                    "address": pp.address,
                    "latitude": pp.latitude,
                    "longitude": pp.longitude,
                    "route_id": pp.route_id,
                    "ward_id": pp.ward_id,
                    "waste_type": pp.waste_type,
                    "type": pp.type,
                    "expected_pickup_time": pp.expected_pickup_time,
                    "schedule": pp.schedule,
                    "geofence_radius": pp.geofence_radius,
                    "status": pp.status,
                    "last_collection": pp.last_collection,
                }
                for pp in pickup_points
            ]
        }
        result.append(route_dict)
    
    return result

@router.post("/", response_model=schemas.Route)
def create_route(route: schemas.RouteCreate, db: Session = Depends(get_db)):
    db_route = models.Route(**route.dict())
    db.add(db_route)
    db.commit()
    db.refresh(db_route)
    return db_route

@router.get("/{route_id}/pickup-points", response_model=List[schemas.PickupPoint])
def get_route_pickup_points(route_id: str, db: Session = Depends(get_db)):
    pickup_points = db.query(models.PickupPoint).filter(
        models.PickupPoint.route_id == route_id
    ).all()
    return pickup_points
