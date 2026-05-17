from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database.database import get_db
from ..models import models
from ..schemas import schemas

router = APIRouter(prefix="/zones", tags=["zones"])

@router.get("/", response_model=List[schemas.Zone])
def get_zones(db: Session = Depends(get_db)):
    zones = db.query(models.Zone).all()
    return zones

@router.get("/{zone_id}", response_model=schemas.Zone)
def get_zone(zone_id: str, db: Session = Depends(get_db)):
    zone = db.query(models.Zone).filter(models.Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone

@router.post("/", response_model=schemas.Zone)
def create_zone(zone: schemas.ZoneCreate, db: Session = Depends(get_db)):
    db_zone = models.Zone(**zone.dict())
    db.add(db_zone)
    db.commit()
    db.refresh(db_zone)
    return db_zone

@router.get("/{zone_id}/wards", response_model=List[schemas.Ward])
def get_zone_wards(zone_id: str, db: Session = Depends(get_db)):
    wards = db.query(models.Ward).filter(models.Ward.zone_id == zone_id).all()
    return wards
