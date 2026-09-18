"""
Builds a small, structured snapshot of live operational data from the database.

This is intentionally simple and read-only: it exists so the "reporting" chat
mode can ground its answers in real numbers instead of the model guessing.
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...models import models


def build_operations_snapshot(db: Session) -> dict:
    total_trucks = db.query(func.count(models.Truck.id)).scalar() or 0
    active_trucks = db.query(func.count(models.Truck.id)).filter(
        models.Truck.current_status == models.TruckStatus.MOVING
    ).scalar() or 0
    idle_trucks = db.query(func.count(models.Truck.id)).filter(
        models.Truck.current_status == models.TruckStatus.IDLE
    ).scalar() or 0
    breakdown_trucks = db.query(func.count(models.Truck.id)).filter(
        models.Truck.current_status == models.TruckStatus.BREAKDOWN
    ).scalar() or 0

    total_zones = db.query(func.count(models.Zone.id)).scalar() or 0
    total_wards = db.query(func.count(models.Ward.id)).scalar() or 0
    total_vendors = db.query(func.count(models.Vendor.id)).scalar() or 0
    total_routes = db.query(func.count(models.Route.id)).scalar() or 0

    active_alerts = db.query(func.count(models.Alert.id)).filter(
        models.Alert.status == "active"
    ).scalar() or 0

    recent_alerts = (
        db.query(models.Alert)
        .filter(models.Alert.status == "active")
        .order_by(models.Alert.timestamp.desc())
        .limit(5)
        .all()
    )

    total_trips = db.query(func.sum(models.Truck.trips_completed)).scalar() or 0

    return {
        "fleet": {
            "total_trucks": total_trucks,
            "active_trucks": active_trucks,
            "idle_trucks": idle_trucks,
            "breakdown_trucks": breakdown_trucks,
            "total_trips_completed": int(total_trips),
        },
        "coverage": {
            "zones": total_zones,
            "wards": total_wards,
            "vendors": total_vendors,
            "routes": total_routes,
        },
        "alerts": {
            "active_count": active_alerts,
            "recent": [
                {
                    "type": a.alert_type,
                    "severity": a.severity,
                    "message": a.message,
                    "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                }
                for a in recent_alerts
            ],
        },
    }
