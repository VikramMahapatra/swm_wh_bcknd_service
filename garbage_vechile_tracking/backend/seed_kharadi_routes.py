#!/usr/bin/env python3
"""
Seed Kharadi ward with multiple routes and pickup points from GeoJSON
"""

import json
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, '/Users/vikik/Projects/PyProjects/Zentrixel/garbage/garbage_vechile_tracking/backend')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import models
from app.database.database import SessionLocal, SQLALCHEMY_DATABASE_URL

# Load and process GeoJSON
geojson_path = r'c:\Users\vikik\Downloads\export.geojson'

with open(geojson_path, 'r', encoding='utf-8') as f:
    geojson = json.load(f)

# Extract coordinates from GeoJSON
all_coords = []
for feature in geojson['features']:
    if feature['geometry']['type'] == 'LineString':
        for coord in feature['geometry']['coordinates']:
            all_coords.append({'lng': coord[0], 'lat': coord[1]})

# Sample evenly distributed coordinates for pickup points (60 total)
step = len(all_coords) // 60 if len(all_coords) > 60 else 1
pickup_points_coords = [all_coords[i] for i in range(0, len(all_coords), step)][:60]

print(f"Extracted {len(pickup_points_coords)} coordinates from GeoJSON")

# Fixed locations for GTP and dumping yard
GTP_POINT = {"name": "Kharadi GTP", "lat": 18.5580, "lng": 73.9420}
DUMPING_YARD = {"name": "Hadapsar Waste Processing Plant", "lat": 18.5050, "lng": 73.9400}

# Create routes data structure
routes_data = []

for route_num in range(4):
    route_points = pickup_points_coords[route_num * 15:(route_num + 1) * 15]
    if route_points:
        pickup_points = [
            {
                "id": f"KHR-PP{route_num+1:02d}-{i+1:02d}",
                "point_code": f"KHR-{route_num+1}-PP{i+1:02d}",
                "name": f"Kharadi Pickup Point {route_num+1}-{i+1}",
                "address": f"Kharadi Ward, Location {i+1}",
                "latitude": float(point['lat']),
                "longitude": float(point['lng']),
                "ward_id": "WD006",
                "waste_type": ["dry", "wet", "mixed"][i % 3],
                "type": ["residential", "commercial"][i % 2],
                "expected_pickup_time": f"{7 + (i // 5):02d}:{(i * 6) % 60:02d}",
                "schedule": "daily",
                "geofence_radius": 30,
                "status": "active",
                "last_collection": datetime(2026, 2, 10, 8, 30, 0).isoformat()
            }
            for i, point in enumerate(route_points)
        ]

        gtp_index = len(route_points)
        pickup_points.append({
            "id": f"KHR-GTP-{route_num+1:02d}",
            "point_code": f"KHR-{route_num+1}-GTP",
            "name": GTP_POINT["name"],
            "address": "Kharadi Ward, GTP",
            "latitude": GTP_POINT["lat"],
            "longitude": GTP_POINT["lng"],
            "ward_id": "WD006",
            "waste_type": "mixed",
            "type": "gtp",
            "expected_pickup_time": f"{7 + (gtp_index // 5):02d}:{(gtp_index * 6) % 60:02d}",
            "schedule": "daily",
            "geofence_radius": 50,
            "status": "active",
            "last_collection": datetime(2026, 2, 10, 9, 15, 0).isoformat()
        })

        route = {
            "id": f"KHR-{route_num+1}",
            "name": f"Kharadi Route {route_num+1}",
            "code": f"KHR-P{route_num+1}",
            "type": "primary",
            "ward_id": "WD006",
            "zone_id": "ZN003",
            "total_pickup_points": len(pickup_points),
            "estimated_distance": 15.5 + (route_num * 2),
            "estimated_time": 90 + (route_num * 15),
            "status": "active",
            "pickup_points": pickup_points
        }
        routes_data.append(route)

secondary_route = {
    "id": "KHR-S1",
    "name": "Kharadi Secondary Route 1",
    "code": "KHR-S1",
    "type": "secondary",
    "ward_id": "WD006",
    "zone_id": "ZN003",
    "total_pickup_points": 2,
    "estimated_distance": 22.0,
    "estimated_time": 75,
    "status": "active",
    "pickup_points": [
        {
            "id": "KHR-S1-GTP",
            "point_code": "KHR-S1-GTP",
            "name": GTP_POINT["name"],
            "address": "Kharadi Ward, GTP",
            "latitude": GTP_POINT["lat"],
            "longitude": GTP_POINT["lng"],
            "ward_id": "WD006",
            "waste_type": "mixed",
            "type": "gtp",
            "expected_pickup_time": "09:30",
            "schedule": "daily",
            "geofence_radius": 50,
            "status": "active",
            "last_collection": datetime(2026, 2, 10, 9, 30, 0).isoformat()
        },
        {
            "id": "KHR-S1-DUMP",
            "point_code": "KHR-S1-DUMP",
            "name": DUMPING_YARD["name"],
            "address": "Final Dumping Yard",
            "latitude": DUMPING_YARD["lat"],
            "longitude": DUMPING_YARD["lng"],
            "ward_id": "WD006",
            "waste_type": "mixed",
            "type": "dumping",
            "expected_pickup_time": "10:15",
            "schedule": "daily",
            "geofence_radius": 75,
            "status": "active",
            "last_collection": datetime(2026, 2, 10, 10, 15, 0).isoformat()
        }
    ]
}
routes_data.append(secondary_route)

print(f"Created {len(routes_data)} routes with pickup points")

# Connect to database
engine = create_engine(SQLALCHEMY_DATABASE_URL)
db = SessionLocal()

try:
    # Insert routes
    for route_data in routes_data:
        # Create route
        db_route = models.Route(
            id=route_data["id"],
            name=route_data["name"],
            code=route_data["code"],
            type=route_data["type"],
            ward_id=route_data["ward_id"],
            zone_id=route_data["zone_id"],
            total_pickup_points=route_data["total_pickup_points"],
            estimated_distance=route_data["estimated_distance"],
            estimated_time=route_data["estimated_time"],
            status=route_data["status"]
        )
        db.add(db_route)
        db.flush()
        
        print(f"✓ Created route: {route_data['name']} with {route_data['total_pickup_points']} pickup points")
        
        # Create pickup points for this route
        for pp_data in route_data["pickup_points"]:
            db_pickup = models.PickupPoint(
                id=pp_data["id"],
                point_code=pp_data["point_code"],
                name=pp_data["name"],
                address=pp_data["address"],
                latitude=pp_data["latitude"],
                longitude=pp_data["longitude"],
                route_id=route_data["id"],
                ward_id=pp_data["ward_id"],
                waste_type=pp_data["waste_type"],
                type=pp_data["type"],
                expected_pickup_time=pp_data["expected_pickup_time"],
                schedule=pp_data["schedule"],
                geofence_radius=pp_data["geofence_radius"],
                status=pp_data["status"],
                last_collection=pp_data["last_collection"]
            )
            db.add(db_pickup)
        
        db.flush()
    
    # Commit all changes
    db.commit()
    print("\n✅ Successfully seeded Kharadi routes and pickup points!")
    
except Exception as e:
    db.rollback()
    print(f"❌ Error seeding data: {e}")
    import traceback
    traceback.print_exc()

finally:
    db.close()
