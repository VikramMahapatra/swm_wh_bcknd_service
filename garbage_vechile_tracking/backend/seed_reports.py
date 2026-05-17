"""Seed report_data table with report payloads."""
import json
import sys
from datetime import datetime, timedelta
from app.database.database import SessionLocal, engine
from app.models import models
from sqlalchemy import delete

models.Base.metadata.create_all(bind=engine)


def _date_str(days_ago: int) -> str:
    return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def seed_reports() -> bool:
    db = SessionLocal()

    try:
        db.execute(delete(models.ReportData))
        db.commit()

        daily_pickup_coverage = [
            {
                "id": 1,
                "date": _date_str(0),
                "ward": "NAGAR ROAD-VADGAONSHERI",
                "zone": "East Zone",
                "truck": "MH-12-AB-1234",
                "driver": "Rajesh Kumar",
                "totalPoints": 45,
                "covered": 43,
                "missed": 2,
                "weight": 2.4,
                "status": "completed",
            },
            {
                "id": 2,
                "date": _date_str(0),
                "ward": "NAGAR ROAD-VADGAONSHERI",
                "zone": "East Zone",
                "truck": "MH-12-CD-5678",
                "driver": "Amit Singh",
                "totalPoints": 52,
                "covered": 50,
                "missed": 2,
                "weight": 2.8,
                "status": "partial",
            },
            {
                "id": 3,
                "date": _date_str(1),
                "ward": "NAGAR ROAD-VADGAONSHERI",
                "zone": "East Zone",
                "truck": "MH-12-EF-9012",
                "driver": "Suresh Patil",
                "totalPoints": 38,
                "covered": 35,
                "missed": 3,
                "weight": 1.9,
                "status": "partial",
            },
            {
                "id": 4,
                "date": _date_str(1),
                "ward": "NAGAR ROAD-VADGAONSHERI",
                "zone": "East Zone",
                "truck": "MH-12-GH-3456",
                "driver": "Mahesh Yadav",
                "totalPoints": 41,
                "covered": 41,
                "missed": 0,
                "weight": 2.2,
                "status": "completed",
            },
            {
                "id": 5,
                "date": _date_str(2),
                "ward": "NAGAR ROAD-VADGAONSHERI",
                "zone": "East Zone",
                "truck": "MH-12-IJ-7890",
                "driver": "Ravi Sharma",
                "totalPoints": 35,
                "covered": 30,
                "missed": 5,
                "weight": 1.6,
                "status": "partial",
            },
        ]

        route_performance = [
            {"route": "KHR-1", "completion": 98, "avgTime": "4.2 hrs", "deviations": 2, "efficiency": 96},
            {"route": "KHR-2", "completion": 95, "avgTime": "3.8 hrs", "deviations": 5, "efficiency": 91},
            {"route": "KHR-3", "completion": 100, "avgTime": "4.5 hrs", "deviations": 0, "efficiency": 99},
            {"route": "KHR-4", "completion": 88, "avgTime": "5.1 hrs", "deviations": 8, "efficiency": 82},
        ]

        truck_utilization = [
            {"truck": "MH-12-AB-1234", "type": "Compactor", "trips": 3, "operatingHours": 8.5, "idleTime": 1.2, "distance": 45, "utilization": 92},
            {"truck": "MH-12-CD-5678", "type": "Mini Truck", "trips": 4, "operatingHours": 9.0, "idleTime": 0.8, "distance": 52, "utilization": 95},
            {"truck": "MH-12-EF-9012", "type": "Dumper", "trips": 2, "operatingHours": 7.2, "idleTime": 2.1, "distance": 38, "utilization": 78},
            {"truck": "MH-12-GH-3456", "type": "Open Truck", "trips": 3, "operatingHours": 8.0, "idleTime": 1.5, "distance": 41, "utilization": 85},
        ]

        fuel_consumption = [
            {"truck": "MH-12-AB-1234", "fuelUsed": 18.5, "distance": 45, "efficiency": 2.43, "cost": 1850, "anomaly": False, "score": 92},
            {"truck": "MH-12-CD-5678", "fuelUsed": 22.0, "distance": 52, "efficiency": 2.36, "cost": 2200, "anomaly": False, "score": 95},
            {"truck": "MH-12-EF-9012", "fuelUsed": 28.5, "distance": 38, "efficiency": 1.33, "cost": 2850, "anomaly": True, "score": 45},
            {"truck": "MH-12-GH-3456", "fuelUsed": 16.8, "distance": 41, "efficiency": 2.44, "cost": 1680, "anomaly": False, "score": 94},
        ]

        driver_attendance = [
            {"driver": "Rajesh Kumar", "id": "DRV001", "shiftStart": "06:00", "shiftEnd": "14:30", "hoursWorked": 8.5, "routes": 2, "onTime": True, "violations": 0, "score": 95},
            {"driver": "Amit Singh", "id": "DRV002", "shiftStart": "06:15", "shiftEnd": "15:00", "hoursWorked": 8.75, "routes": 2, "onTime": True, "violations": 1, "score": 88},
            {"driver": "Suresh Patil", "id": "DRV003", "shiftStart": "06:45", "shiftEnd": "14:00", "hoursWorked": 7.25, "routes": 1, "onTime": False, "violations": 2, "score": 72},
            {"driver": "Mahesh Yadav", "id": "DRV004", "shiftStart": "06:00", "shiftEnd": "14:15", "hoursWorked": 8.25, "routes": 2, "onTime": True, "violations": 0, "score": 98},
        ]

        complaints = [
            {"id": "CMP001", "date": _date_str(0), "ward": "NAGAR ROAD-VADGAONSHERI", "type": "Missed Pickup", "status": "resolved", "truck": "MH-12-AB-1234", "responseTime": "2 hrs"},
            {"id": "CMP002", "date": _date_str(0), "ward": "NAGAR ROAD-VADGAONSHERI", "type": "Irregular Timing", "status": "pending", "truck": "MH-12-EF-9012", "responseTime": "-"},
            {"id": "CMP003", "date": _date_str(1), "ward": "NAGAR ROAD-VADGAONSHERI", "type": "Spillage", "status": "in-progress", "truck": "MH-12-IJ-7890", "responseTime": "1 hr"},
        ]

        dump_yard = [
            {"site": "GTP Kharadi", "entries": 45, "totalWeight": 112.5, "avgWeight": 2.5, "peakHour": "10:00-11:00", "capacity": 78},
            {"site": "GTP Viman Nagar", "entries": 38, "totalWeight": 89.2, "avgWeight": 2.35, "peakHour": "11:00-12:00", "capacity": 65},
            {"site": "Dump Site Alpha", "entries": 22, "totalWeight": 198.0, "avgWeight": 9.0, "peakHour": "14:00-15:00", "capacity": 45},
        ]

        weekly_trend = [
            {"day": "Mon", "collected": 45.2, "missed": 8, "efficiency": 94},
            {"day": "Tue", "collected": 48.5, "missed": 5, "efficiency": 96},
            {"day": "Wed", "collected": 42.8, "missed": 12, "efficiency": 88},
            {"day": "Thu", "collected": 50.1, "missed": 4, "efficiency": 97},
            {"day": "Fri", "collected": 47.3, "missed": 6, "efficiency": 95},
            {"day": "Sat", "collected": 52.0, "missed": 3, "efficiency": 98},
            {"day": "Sun", "collected": 35.2, "missed": 2, "efficiency": 96},
        ]

        zone_wise = [
            {"name": "East Zone", "value": 35, "color": "hsl(var(--chart-1))"},
            {"name": "North Zone", "value": 28, "color": "hsl(var(--chart-2))"},
            {"name": "South Zone", "value": 22, "color": "hsl(var(--chart-3))"},
            {"name": "West Zone", "value": 15, "color": "hsl(var(--chart-4))"},
        ]

        late_arrival = [
            {"id": 1, "date": _date_str(0), "truck": "MH-12-AB-1234", "driver": "Rajesh Kumar", "route": "KHR-1", "scheduledTime": "06:00", "actualTime": "06:25", "delay": 25, "reason": "Traffic congestion", "status": "late", "zone": "East Zone", "ward": "NAGAR ROAD-VADGAONSHERI", "vendor": "City Transport Co", "routeType": "primary"},
            {"id": 2, "date": _date_str(0), "truck": "MH-12-CD-5678", "driver": "Amit Singh", "route": "KHR-2", "scheduledTime": "06:30", "actualTime": "06:35", "delay": 5, "reason": "", "status": "on-time", "zone": "East Zone", "ward": "NAGAR ROAD-VADGAONSHERI", "vendor": "City Transport Co", "routeType": "primary"},
            {"id": 3, "date": _date_str(1), "truck": "MH-12-EF-9012", "driver": "Suresh Patil", "route": "KHR-3", "scheduledTime": "07:00", "actualTime": "07:45", "delay": 45, "reason": "Vehicle breakdown", "status": "late", "zone": "East Zone", "ward": "NAGAR ROAD-VADGAONSHERI", "vendor": "City Transport Co", "routeType": "secondary"},
        ]

        driver_behavior = [
            {"id": 1, "date": _date_str(0), "time": "08:45", "truck": "MH-12-AB-1234", "driver": "Rajesh Kumar", "driverId": "DRV001", "incidentType": "Overspeeding", "value": "72 km/h", "limit": "60 km/h", "location": "Kharadi Main Road", "severity": "medium"},
            {"id": 2, "date": _date_str(0), "time": "09:12", "truck": "MH-12-EF-9012", "driver": "Suresh Patil", "driverId": "DRV003", "incidentType": "Harsh Braking", "value": "9.2 m/s2", "limit": "8 m/s2", "location": "Viman Nagar Junction", "severity": "low"},
            {"id": 3, "date": _date_str(1), "time": "10:30", "truck": "MH-12-GH-3456", "driver": "Mahesh Yadav", "driverId": "DRV004", "incidentType": "Overspeeding", "value": "85 km/h", "limit": "60 km/h", "location": "Highway Section", "severity": "high"},
        ]

        vehicle_status = [
            {"id": "TRK-001", "truck": "MH-12-AB-1234", "type": "primary", "driver": "Rajesh Kumar", "status": "active", "gpsStatus": "online", "lastUpdate": "2 mins ago", "batteryLevel": 92, "signalStrength": 85, "route": "KHR-1"},
            {"id": "TRK-002", "truck": "MH-12-CD-5678", "type": "secondary", "driver": "Amit Singh", "status": "active", "gpsStatus": "online", "lastUpdate": "5 mins ago", "batteryLevel": 78, "signalStrength": 72, "route": "KHR-2"},
            {"id": "TRK-003", "truck": "MH-12-EF-9012", "type": "primary", "driver": "Suresh Patil", "status": "warning", "gpsStatus": "warning", "lastUpdate": "8 mins ago", "batteryLevel": 25, "signalStrength": 45, "route": "KHR-3"},
        ]

        spare_usage = [
            {"id": 1, "date": _date_str(0), "spareTruck": "MH-12-SP-1001", "originalTruck": "MH-12-AB-1234", "driver": "Spare Driver 1", "route": "KHR-1", "vendor": "City Transport Co", "breakdownReason": "Engine failure", "activatedAt": "07:30", "releasedAt": "14:45", "duration": "7h 15m", "status": "completed"},
            {"id": 2, "date": _date_str(1), "spareTruck": "MH-12-SP-2001", "originalTruck": "MH-12-EF-9012", "driver": "Spare Driver 2", "route": "KHR-3", "vendor": "City Transport Co", "breakdownReason": "Brake issue", "activatedAt": "06:45", "releasedAt": "16:00", "duration": "9h 15m", "status": "completed"},
        ]

        reports_payload = {
            "daily_pickup_coverage": daily_pickup_coverage,
            "route_performance": route_performance,
            "truck_utilization": truck_utilization,
            "fuel_consumption": fuel_consumption,
            "driver_attendance": driver_attendance,
            "complaints": complaints,
            "dump_yard": dump_yard,
            "weekly_trend": weekly_trend,
            "zone_wise": zone_wise,
            "late_arrival": late_arrival,
            "driver_behavior": driver_behavior,
            "vehicle_status": vehicle_status,
            "spare_usage": spare_usage,
        }

        for report_type, payload in reports_payload.items():
            db.add(models.ReportData(report_type=report_type, payload=json.dumps(payload)))

        db.commit()
        print("✅ Reports data seeded successfully")
        return True
    except Exception as exc:
        print(f"❌ Failed to seed reports data: {exc}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = seed_reports()
    sys.exit(0 if success else 1)
