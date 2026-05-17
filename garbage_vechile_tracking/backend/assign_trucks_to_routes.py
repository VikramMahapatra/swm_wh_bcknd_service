#!/usr/bin/env python3
"""
Assign all trucks to routes
"""

import sys
sys.path.insert(0, '/Users/vikik/Projects/PyProjects/Zentrixel/garbage/garbage_vechile_tracking/backend')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.database import SessionLocal, SQLALCHEMY_DATABASE_URL
from app.models import models

db = SessionLocal()

try:
    # Get all routes
    routes = db.query(models.Route).all()
    route_list = list(routes)
    
    if not route_list:
        print("❌ No routes found in database")
        sys.exit(1)
    
    print(f"📋 Found {len(route_list)} routes")
    
    # Get all trucks
    trucks = db.query(models.Truck).all()
    print(f"🚛 Found {len(trucks)} trucks")
    
    # Assign trucks to routes (round-robin)
    for idx, truck in enumerate(trucks):
        route = route_list[idx % len(route_list)]
        truck.assigned_route_id = route.id
        print(f"  ✓ Assigned {truck.registration_number} to {route.name}")
    
    db.commit()
    print(f"\n✅ Successfully assigned all {len(trucks)} trucks to routes!")
    
    # Verify
    trucks_with_routes = db.query(models.Truck).filter(models.Truck.assigned_route_id.isnot(None)).count()
    print(f"📊 Trucks with assigned routes: {trucks_with_routes}/{len(trucks)}")
    
except Exception as e:
    db.rollback()
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    db.close()
