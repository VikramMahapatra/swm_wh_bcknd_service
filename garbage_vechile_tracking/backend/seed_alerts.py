"""Seed Alert data for the last 10 days"""
import sys
from datetime import datetime, timedelta
from app.database.database import SessionLocal, engine
from app.models import models
from sqlalchemy import delete

# Create tables
models.Base.metadata.create_all(bind=engine)

def seed_alerts():
    """Populate alerts table with realistic data"""
    db = SessionLocal()
    
    try:
        # Clear existing alerts
        db.execute(delete(models.Alert))
        db.commit()
        
        # Alert configurations
        alert_types = ["route_deviation", "missed_pickup", "unauthorized_halt", "speed_violation", "geofence_breach", "device_tamper"]
        severity_levels = ["critical", "high", "medium", "low"]
        statuses = ["active", "acknowledged", "investigating", "resolved"]
        
        trucks = ["TRK001", "TRK002", "TRK003", "TRK004", "TRK005", "TRK006", "TRK007", "TRK008", "TRK009"]
        routes = ["KHR-1", "KHR-2", "KHR-3", "KHR-4"]
        zones = ["ZN003"]  # East Zone
        wards = ["WD006"]  # NAGAR ROAD-VADGAONSHERI
        
        messages = {
            "route_deviation": "Deviated from assigned route",
            "missed_pickup": "Missed scheduled pickup point",
            "unauthorized_halt": "Unauthorized halt detected",
            "speed_violation": "Speed limit exceeded",
            "geofence_breach": "Exited designated service zone",
            "device_tamper": "GPS device disconnection detected"
        }
        
        alert_id = 1
        base_date = datetime.now() - timedelta(days=9)
        
        # Create alerts spanning 10 days including today
        for day_offset in range(10):
            current_date = base_date + timedelta(days=day_offset)
            
            # Create 2-3 alerts per day
            for hour in [6, 9, 14, 17]:
                if day_offset == 0 and hour > 9:  # First day has fewer alerts
                    break
                    
                alert_time = current_date.replace(hour=hour, minute=0, second=0)
                
                alert = models.Alert(
                    id=alert_id,
                    truck_id=trucks[alert_id % len(trucks)],
                    route_id=routes[alert_id % len(routes)],
                    zone_id=zones[0],
                    ward_id=wards[0],
                    alert_type=alert_types[alert_id % len(alert_types)],
                    severity=severity_levels[alert_id % len(severity_levels)],
                    message=messages[alert_types[alert_id % len(alert_types)]],
                    location=f"18.559{alert_id % 10}, 73.936{alert_id % 10}",
                    timestamp=alert_time,
                    date=alert_time.strftime("%Y-%m-%d"),
                    status=statuses[alert_id % len(statuses)]
                )
                
                db.add(alert)
                alert_id += 1
        
        db.commit()
        print(f"✅ Successfully seeded {alert_id - 1} alerts into the database")
        
        # Verify
        count = db.query(models.Alert).count()
        print(f"📊 Total alerts in database: {count}")
        
        # Show sample
        print("\n📋 Sample alerts:")
        sample_alerts = db.query(models.Alert).limit(5).all()
        for alert in sample_alerts:
            print(f"  - {alert.alert_type} ({alert.severity}): {alert.message} on {alert.date}")
        
    except Exception as e:
        print(f"❌ Error seeding alerts: {e}")
        db.rollback()
        return False
    finally:
        db.close()
    
    return True

if __name__ == "__main__":
    success = seed_alerts()
    sys.exit(0 if success else 1)
