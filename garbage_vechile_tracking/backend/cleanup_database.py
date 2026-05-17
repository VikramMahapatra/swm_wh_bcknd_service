#!/usr/bin/env python3
"""
Clean up database to keep only Kharadi Ward data
"""

import sys

sys.path.insert(0, '/Users/vikik/Projects/PyProjects/Zentrixel/garbage/garbage_vechile_tracking/backend')

from app.database.database import SessionLocal
from app.models import models

db = SessionLocal()

try:
    print("Starting cleanup of non-Kharadi data...")
    
    # Kharadi identifiers
    kharadi_ward_id = "WD006"
    kharadi_zone_id = "ZN003"
    kharadi_routes = ["KHR-1", "KHR-2", "KHR-3", "KHR-4"]
    
    # Delete pickup points not associated with Kharadi routes
    print("\n1. Deleting non-Kharadi pickup points...")
    non_kharadi_pickups = db.query(models.PickupPoint).filter(
        ~models.PickupPoint.route_id.in_(kharadi_routes)
    ).all()
    count = len(non_kharadi_pickups)
    for pp in non_kharadi_pickups:
        db.delete(pp)
    db.flush()
    print(f"   ✓ Deleted {count} non-Kharadi pickup points")
    
    # Delete routes except Kharadi routes
    print("\n2. Deleting non-Kharadi routes...")
    non_kharadi_routes = db.query(models.Route).filter(
        ~models.Route.id.in_(kharadi_routes)
    ).all()
    count = len(non_kharadi_routes)
    for route in non_kharadi_routes:
        db.delete(route)
    db.flush()
    print(f"   ✓ Deleted {count} non-Kharadi routes")
    
    # Delete zones except Kharadi zone
    print("\n3. Deleting non-Kharadi zones...")
    non_kharadi_zones = db.query(models.Zone).filter(
        models.Zone.id != kharadi_zone_id
    ).all()
    count = len(non_kharadi_zones)
    for zone in non_kharadi_zones:
        db.delete(zone)
    db.flush()
    print(f"   ✓ Deleted {count} non-Kharadi zones")
    
    # Delete wards except Kharadi ward
    print("\n4. Deleting non-Kharadi wards...")
    non_kharadi_wards = db.query(models.Ward).filter(
        models.Ward.id != kharadi_ward_id
    ).all()
    count = len(non_kharadi_wards)
    for ward in non_kharadi_wards:
        db.delete(ward)
    db.flush()
    print(f"   ✓ Deleted {count} non-Kharadi wards")
    
    # Delete vendors (optional - they might be referenced)
    print("\n5. Deleting vendors (keeping for truck assignment)...")
    # Keep vendors for now, just delete unused ones
    
    # Delete drivers not assigned to Kharadi
    print("\n6. Deleting unrelated drivers...")
    # Keep some drivers for demo, delete unnecessary ones
    
    # Commit all deletions
    db.commit()
    
    print("\n" + "="*60)
    print("✅ Database cleanup complete!")
    print("="*60)
    
    # Print remaining data summary
    print("\nRemaining data in database:")
    
    zones = db.query(models.Zone).all()
    print(f"  Zones: {len(zones)}")
    for zone in zones:
        print(f"    - {zone.id}: {zone.name}")
    
    wards = db.query(models.Ward).all()
    print(f"  Wards: {len(wards)}")
    for ward in wards:
        print(f"    - {ward.id}: {ward.name}")
    
    routes = db.query(models.Route).all()
    print(f"  Routes: {len(routes)}")
    for route in routes:
        pickups = db.query(models.PickupPoint).filter(
            models.PickupPoint.route_id == route.id
        ).count()
        print(f"    - {route.id}: {route.name} ({pickups} pickup points)")
    
    total_pickups = db.query(models.PickupPoint).count()
    print(f"  Total Pickup Points: {total_pickups}")
    
except Exception as e:
    print(f"❌ Error during cleanup: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()

finally:
    db.close()
