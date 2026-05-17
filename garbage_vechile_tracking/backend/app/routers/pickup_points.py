from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from ..database.database import get_db
from ..models import models
from ..schemas import schemas

router = APIRouter(prefix="/pickup-points", tags=["pickup-points"])

@router.get("/", response_model=List[schemas.PickupPoint])
def get_pickup_points(
    ward_id: str = None,
    route_id: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.PickupPoint)
    
    if ward_id:
        query = query.filter(models.PickupPoint.ward_id == ward_id)
    if route_id:
        query = query.filter(models.PickupPoint.route_id == route_id)
    
    pickup_points = query.all()
    return pickup_points

@router.post("/", response_model=schemas.PickupPoint)
def create_pickup_point(
    pickup_point: schemas.PickupPointCreate,
    db: Session = Depends(get_db)
):
    db_pickup_point = models.PickupPoint(**pickup_point.dict())
    db.add(db_pickup_point)
    db.commit()
    db.refresh(db_pickup_point)
    return db_pickup_point
