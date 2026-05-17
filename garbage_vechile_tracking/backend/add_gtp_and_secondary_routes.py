#!/usr/bin/env python3
"""
Add a GTP pickup point to existing routes and create a secondary route per ward
from GTP to the final dumping yard.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database.database import SessionLocal
from app.models import models

# GTP locations by ward_id
WARD_GTP: Dict[str, dict] = {
    "WD006": {"name": "Kharadi GTP", "lat": 18.5580, "lng": 73.9420},
    "WD007": {"name": "Viman Nagar GTP", "lat": 18.5620, "lng": 73.9150},
    "WD001": {"name": "Aundh GTP", "lat": 18.5850, "lng": 73.8100},
    "WD004": {"name": "Hadapsar GTP", "lat": 18.5000, "lng": 73.9300},
    "WD002": {"name": "Baner GTP", "lat": 18.5685, "lng": 73.7925},
}

# Final dumping yard
DUMPING_YARD = {
    "name": "Hadapsar Waste Processing Plant",
    "lat": 18.5050,
    "lng": 73.9400,
}


def add_gtp_to_route(db: SessionLocal, route: models.Route) -> bool:
    existing_gtp = (
        db.query(models.PickupPoint)
        .filter(models.PickupPoint.route_id == route.id)
        .filter(models.PickupPoint.type == "gtp")
        .first()
    )
    if existing_gtp:
        return False

    gtp = WARD_GTP.get(route.ward_id)
    if not gtp:
        print(f"! No GTP mapping for ward {route.ward_id} (route {route.id}); skipping")
        return False

    gtp_point = models.PickupPoint(
        id=f"{route.id}-GTP",
        point_code=f"{route.code or route.id}-GTP",
        name=gtp["name"],
        address="GTP",
        latitude=gtp["lat"],
        longitude=gtp["lng"],
        route_id=route.id,
        ward_id=route.ward_id,
        waste_type="mixed",
        type="gtp",
        expected_pickup_time=None,
        schedule="daily",
        geofence_radius=50,
        status="active",
        last_collection=datetime.utcnow().isoformat(),
    )
    db.add(gtp_point)

    # Update route total_pickup_points if present
    if route.total_pickup_points is not None:
        route.total_pickup_points += 1

    return True


def create_secondary_route(db: SessionLocal, ward_id: str, zone_id: str) -> bool:
    existing_secondary = (
        db.query(models.Route)
        .filter(models.Route.ward_id == ward_id)
        .filter(models.Route.type == models.RouteType.SECONDARY)
        .first()
    )
    if existing_secondary:
        return False

    gtp = WARD_GTP.get(ward_id)
    if not gtp:
        print(f"! No GTP mapping for ward {ward_id}; secondary route not created")
        return False

    route_id = f"SEC-{ward_id}"
    route = models.Route(
        id=route_id,
        name=f"{ward_id} Secondary Route 1",
        code=f"{ward_id}-S1",
        type=models.RouteType.SECONDARY,
        ward_id=ward_id,
        zone_id=zone_id,
        total_pickup_points=2,
        estimated_distance=20.0,
        estimated_time=75,
        status="active",
    )
    db.add(route)
    db.flush()

    gtp_point = models.PickupPoint(
        id=f"{route_id}-GTP",
        point_code=f"{route.code}-GTP",
        name=gtp["name"],
        address="GTP",
        latitude=gtp["lat"],
        longitude=gtp["lng"],
        route_id=route_id,
        ward_id=ward_id,
        waste_type="mixed",
        type="gtp",
        expected_pickup_time=None,
        schedule="daily",
        geofence_radius=50,
        status="active",
        last_collection=datetime.utcnow().isoformat(),
    )

    dump_point = models.PickupPoint(
        id=f"{route_id}-DUMP",
        point_code=f"{route.code}-DUMP",
        name=DUMPING_YARD["name"],
        address="Final Dumping Yard",
        latitude=DUMPING_YARD["lat"],
        longitude=DUMPING_YARD["lng"],
        route_id=route_id,
        ward_id=ward_id,
        waste_type="mixed",
        type="dumping",
        expected_pickup_time=None,
        schedule="daily",
        geofence_radius=75,
        status="active",
        last_collection=datetime.utcnow().isoformat(),
    )

    db.add(gtp_point)
    db.add(dump_point)
    return True


def main() -> None:
    db = SessionLocal()
    try:
        routes = db.query(models.Route).all()
        updated_routes = 0
        created_secondary = 0

        for route in routes:
            if add_gtp_to_route(db, route):
                updated_routes += 1

        ward_zone_pairs = {
            (route.ward_id, route.zone_id)
            for route in routes
            if route.ward_id and route.zone_id
        }
        for ward_id, zone_id in ward_zone_pairs:
            if create_secondary_route(db, ward_id, zone_id):
                created_secondary += 1

        db.commit()
        print(f"✅ Added GTP to {updated_routes} routes")
        print(f"✅ Created {created_secondary} secondary routes")
    except Exception as exc:
        db.rollback()
        print(f"❌ Failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
