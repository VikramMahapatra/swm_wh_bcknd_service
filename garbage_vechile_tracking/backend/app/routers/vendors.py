from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from ..database.database import get_db
from ..models import models
from ..schemas import schemas

router = APIRouter(prefix="/vendors", tags=["vendors"])

@router.get("/", response_model=List[schemas.Vendor])
def get_vendors(db: Session = Depends(get_db)):
    vendors = db.query(models.Vendor).all()
    return vendors

@router.post("/", response_model=schemas.Vendor)
def create_vendor(vendor: schemas.VendorCreate, db: Session = Depends(get_db)):
    db_vendor = models.Vendor(**vendor.dict())
    db.add(db_vendor)
    db.commit()
    db.refresh(db_vendor)
    return db_vendor
