from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database.database import get_db
from ..models import models
from ..schemas import schemas

router = APIRouter(prefix="/drivers", tags=["drivers"])

@router.get("/", response_model=List[schemas.Driver])
def get_drivers(
    vendor_id: str = None,
    status: str = None,
    db: Session = Depends(get_db)
):
    """Get all drivers with optional filters"""
    query = db.query(models.Driver)
    
    if vendor_id:
        query = query.filter(models.Driver.vendor_id == vendor_id)
    if status:
        query = query.filter(models.Driver.status == status)
    
    drivers = query.all()
    return drivers

@router.get("/{driver_id}", response_model=schemas.Driver)
def get_driver(driver_id: str, db: Session = Depends(get_db)):
    """Get a specific driver"""
    driver = db.query(models.Driver).filter(models.Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return driver

@router.post("/", response_model=schemas.Driver)
def create_driver(driver: schemas.DriverCreate, db: Session = Depends(get_db)):
    """Create a new driver"""
    db_driver = models.Driver(**driver.dict())
    db.add(db_driver)
    db.commit()
    db.refresh(db_driver)
    return db_driver

@router.put("/{driver_id}", response_model=schemas.Driver)
def update_driver(driver_id: str, driver: schemas.DriverCreate, db: Session = Depends(get_db)):
    """Update a driver"""
    db_driver = db.query(models.Driver).filter(models.Driver.id == driver_id).first()
    if not db_driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    for field, value in driver.dict().items():
        setattr(db_driver, field, value)
    
    db.commit()
    db.refresh(db_driver)
    return db_driver

@router.delete("/{driver_id}")
def delete_driver(driver_id: str, db: Session = Depends(get_db)):
    """Delete a driver"""
    db_driver = db.query(models.Driver).filter(models.Driver.id == driver_id).first()
    if not db_driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    db.delete(db_driver)
    db.commit()
    return {"message": "Driver deleted successfully"}
