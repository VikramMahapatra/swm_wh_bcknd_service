from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..models import models
from ..schemas import schemas

router = APIRouter(prefix="/gtc-checkpoints", tags=["gtc-checkpoints"])

SCORE_MIN = 0
SCORE_MAX = 10


def _validate_score(score: Optional[int], label: str) -> None:
    if score is None:
        return
    if score < SCORE_MIN or score > SCORE_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"{label} must be between {SCORE_MIN} and {SCORE_MAX}."
        )


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.") from exc


@router.get("/", response_model=List[schemas.GtcCheckpointWithTruck])
def list_gtc_checkpoints(
    truck_id: Optional[str] = Query(default=None),
    date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    date_from: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    query = db.query(models.GtcCheckpointEntry, models.Truck.registration_number).join(models.Truck)

    if truck_id and truck_id != "undefined":
        query = query.filter(models.GtcCheckpointEntry.truck_id == truck_id)

    if date:
        query = query.filter(func.date(models.GtcCheckpointEntry.arrived_at) == date)

    start_date = _parse_date(date_from)
    end_date = _parse_date(date_to)
    if start_date:
        query = query.filter(models.GtcCheckpointEntry.arrived_at >= start_date)
    if end_date:
        end_limit = end_date + timedelta(days=1) - timedelta(microseconds=1)
        query = query.filter(models.GtcCheckpointEntry.arrived_at <= end_limit)

    rows = query.order_by(models.GtcCheckpointEntry.arrived_at.desc()).all()
    results: List[schemas.GtcCheckpointWithTruck] = []

    for entry, registration_number in rows:
        results.append(
            schemas.GtcCheckpointWithTruck(
                id=entry.id,
                truck_id=entry.truck_id,
                arrived_at=entry.arrived_at,
                is_dry=entry.is_dry,
                is_wet=entry.is_wet,
                is_metal=entry.is_metal,
                is_plastic=entry.is_plastic,
                is_sanitary=entry.is_sanitary,
                truck_cleanliness_score=entry.truck_cleanliness_score,
                gtc_cleanliness_score=entry.gtc_cleanliness_score,
                remarks=entry.remarks,
                truck_registration_number=registration_number,
            )
        )

    return results


@router.post("/", response_model=schemas.GtcCheckpoint)
def create_gtc_checkpoint(
    payload: schemas.GtcCheckpointCreate,
    db: Session = Depends(get_db),
):
    truck = db.query(models.Truck).filter(models.Truck.id == payload.truck_id).first()
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")

    if not any([
        payload.is_dry,
        payload.is_wet,
        payload.is_metal,
        payload.is_plastic,
        payload.is_sanitary,
    ]):
        raise HTTPException(status_code=400, detail="Select at least one garbage type.")

    _validate_score(payload.truck_cleanliness_score, "Truck cleanliness score")
    _validate_score(payload.gtc_cleanliness_score, "GTC cleanliness score")

    arrived_at = payload.arrived_at or datetime.utcnow()
    entry = models.GtcCheckpointEntry(
        truck_id=payload.truck_id,
        arrived_at=arrived_at,
        is_dry=payload.is_dry,
        is_wet=payload.is_wet,
        is_metal=payload.is_metal,
        is_plastic=payload.is_plastic,
        is_sanitary=payload.is_sanitary,
        truck_cleanliness_score=payload.truck_cleanliness_score,
        gtc_cleanliness_score=payload.gtc_cleanliness_score,
        remarks=payload.remarks,
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
