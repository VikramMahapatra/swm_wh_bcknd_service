"""Update trucks and drivers with various expiry dates to populate Expiry Alerts section."""
import sys
from datetime import datetime, timedelta

from app.database.database import SessionLocal, engine
from app.models import models

models.Base.metadata.create_all(bind=engine)


def seed_expiry_data():
    """Update trucks and drivers with expiry dates for testing expiry alerts."""
    db = SessionLocal()
    
    try:
        today = datetime.now()
        
        # Update trucks with various expiry scenarios
        trucks_updates = [
            # TRK001 - Expired insurance (30 days ago), Critical fitness (5 days)
            {
                "id": "TRK001",
                "insurance_expiry": (today - timedelta(days=30)).strftime("%Y-%m-%d"),
                "fitness_expiry": (today + timedelta(days=5)).strftime("%Y-%m-%d"),
            },
            # TRK002 - Critical insurance (3 days), Warning fitness (20 days)
            {
                "id": "TRK002",
                "insurance_expiry": (today + timedelta(days=3)).strftime("%Y-%m-%d"),
                "fitness_expiry": (today + timedelta(days=20)).strftime("%Y-%m-%d"),
            },
            # TRK003 - Expired both
            {
                "id": "TRK003",
                "insurance_expiry": (today - timedelta(days=15)).strftime("%Y-%m-%d"),
                "fitness_expiry": (today - timedelta(days=10)).strftime("%Y-%m-%d"),
            },
            # TRK004 - Warning insurance (25 days), Critical fitness (6 days)
            {
                "id": "TRK004",
                "insurance_expiry": (today + timedelta(days=25)).strftime("%Y-%m-%d"),
                "fitness_expiry": (today + timedelta(days=6)).strftime("%Y-%m-%d"),
            },
            # TRK005 - Critical insurance (2 days), Expired fitness
            {
                "id": "TRK005",
                "insurance_expiry": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
                "fitness_expiry": (today - timedelta(days=5)).strftime("%Y-%m-%d"),
            },
            # TRK006 - Warning both
            {
                "id": "TRK006",
                "insurance_expiry": (today + timedelta(days=15)).strftime("%Y-%m-%d"),
                "fitness_expiry": (today + timedelta(days=28)).strftime("%Y-%m-%d"),
            },
            # TRK007 - OK (far future)
            {
                "id": "TRK007",
                "insurance_expiry": (today + timedelta(days=180)).strftime("%Y-%m-%d"),
                "fitness_expiry": (today + timedelta(days=200)).strftime("%Y-%m-%d"),
            },
            # TRK008 - Critical insurance (4 days), OK fitness
            {
                "id": "TRK008",
                "insurance_expiry": (today + timedelta(days=4)).strftime("%Y-%m-%d"),
                "fitness_expiry": (today + timedelta(days=120)).strftime("%Y-%m-%d"),
            },
            # TRK009 - Expired insurance, Warning fitness (18 days)
            {
                "id": "TRK009",
                "insurance_expiry": (today - timedelta(days=20)).strftime("%Y-%m-%d"),
                "fitness_expiry": (today + timedelta(days=18)).strftime("%Y-%m-%d"),
            },
        ]
        
        truck_count = 0
        for update_data in trucks_updates:
            truck = db.query(models.Truck).filter(models.Truck.id == update_data["id"]).first()
            if truck:
                truck.insurance_expiry = update_data["insurance_expiry"]
                truck.fitness_expiry = update_data["fitness_expiry"]
                truck_count += 1
        
        # Update drivers with various license expiry scenarios
        drivers_updates = [
            # DRV001 - Expired license (45 days ago)
            {
                "id": "DRV001",
                "license_expiry": (today - timedelta(days=45)).strftime("%Y-%m-%d"),
            },
            # DRV002 - Critical license (5 days)
            {
                "id": "DRV002",
                "license_expiry": (today + timedelta(days=5)).strftime("%Y-%m-%d"),
            },
            # DRV003 - Warning license (22 days)
            {
                "id": "DRV003",
                "license_expiry": (today + timedelta(days=22)).strftime("%Y-%m-%d"),
            },
            # DRV004 - Critical license (7 days)
            {
                "id": "DRV004",
                "license_expiry": (today + timedelta(days=7)).strftime("%Y-%m-%d"),
            },
            # DRV005 - OK license (far future)
            {
                "id": "DRV005",
                "license_expiry": (today + timedelta(days=365)).strftime("%Y-%m-%d"),
            },
            # DRV006 - Warning license (28 days)
            {
                "id": "DRV006",
                "license_expiry": (today + timedelta(days=28)).strftime("%Y-%m-%d"),
            },
            # DRV007 - Expired license (10 days ago)
            {
                "id": "DRV007",
                "license_expiry": (today - timedelta(days=10)).strftime("%Y-%m-%d"),
            },
            # DRV008 - Critical license (3 days)
            {
                "id": "DRV008",
                "license_expiry": (today + timedelta(days=3)).strftime("%Y-%m-%d"),
            },
            # DRV009 - Warning license (15 days)
            {
                "id": "DRV009",
                "license_expiry": (today + timedelta(days=15)).strftime("%Y-%m-%d"),
            },
        ]
        
        driver_count = 0
        for update_data in drivers_updates:
            driver = db.query(models.Driver).filter(models.Driver.id == update_data["id"]).first()
            if driver:
                driver.license_expiry = update_data["license_expiry"]
                driver_count += 1
        
        db.commit()
        print(f"✅ Updated {truck_count} trucks with expiry dates")
        print(f"✅ Updated {driver_count} drivers with license expiry dates")
        print(f"\nExpiry Summary:")
        print(f"  - Trucks: {truck_count} updated with insurance & fitness expiry dates")
        print(f"  - Drivers: {driver_count} updated with license expiry dates")
        print(f"  - Scenarios: Expired, Critical (≤7 days), Warning (≤30 days), OK (>30 days)")
        
        return True
        
    except Exception as exc:
        db.rollback()
        print(f"❌ Failed to seed expiry data: {exc}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = seed_expiry_data()
    sys.exit(0 if success else 1)
