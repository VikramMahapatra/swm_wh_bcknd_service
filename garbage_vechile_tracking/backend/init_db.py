import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import SessionLocal, engine
from app.models import models

def init_database():
    """Initialize database with Pune city data"""
    
    # Create all tables
    models.Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Clear existing data
        db.query(models.Analytics).delete()
        db.query(models.TwitterMention).delete()
        db.query(models.TicketComment).delete()
        db.query(models.Ticket).delete()
        db.query(models.User).delete()
        db.query(models.Alert).delete()
        db.query(models.PickupPoint).delete()
        db.query(models.Truck).delete()
        db.query(models.Route).delete()
        db.query(models.Driver).delete()
        db.query(models.Ward).delete()
        db.query(models.Vendor).delete()
        db.query(models.Zone).delete()
        db.commit()
        
        print("✅ Cleared existing data")
        
        # Create Zones (4 zones for Pune)
        zones_data = [
            models.Zone(id="ZN001", name="North Zone", code="NZ", 
                       description="Northern area including Aundh, Baner, Pashan",
                       supervisor_name="Arvind Rao", supervisor_phone="+91 9555444333",
                       total_wards=3, status="active"),
            models.Zone(id="ZN002", name="South Zone", code="SZ",
                       description="Southern area including Katraj, Kondhwa, Hadapsar",
                       supervisor_name="Priya Sharma", supervisor_phone="+91 9555444334",
                       total_wards=2, status="active"),
            models.Zone(id="ZN003", name="East Zone", code="EZ",
                       description="Eastern area including Kharadi, Viman Nagar, Wadgaon Sheri",
                       supervisor_name="Kiran Patil", supervisor_phone="+91 9555444335",
                       total_wards=3, status="active"),
            models.Zone(id="ZN004", name="West Zone", code="WZ",
                       description="Western area including Kothrud, Karve Nagar, Warje",
                       supervisor_name="Sanjay Kulkarni", supervisor_phone="+91 9555444336",
                       total_wards=2, status="active"),
        ]
        db.add_all(zones_data)
        db.commit()
        print(f"✅ Created {len(zones_data)} zones")
        
        # Create Wards
        wards_data = [
            # North Zone - 3 wards
            models.Ward(id="WD001", name="Aundh", code="AND", zone_id="ZN001",
                       population=52000, area=14.8, total_pickup_points=45, status="active"),
            models.Ward(id="WD002", name="Baner", code="BNR", zone_id="ZN001",
                       population=48000, area=11.5, total_pickup_points=40, status="active"),
            models.Ward(id="WD003", name="Pashan", code="PSN", zone_id="ZN001",
                       population=35000, area=9.2, total_pickup_points=30, status="active"),
            
            # South Zone - 2 wards
            models.Ward(id="WD004", name="Hadapsar", code="HDP", zone_id="ZN002",
                       population=65000, area=18.2, total_pickup_points=55, status="active"),
            models.Ward(id="WD005", name="Kondhwa", code="KDW", zone_id="ZN002",
                       population=42000, area=12.0, total_pickup_points=35, status="active"),
            
            # East Zone - 3 wards
            models.Ward(id="WD006", name="Kharadi", code="KHR", zone_id="ZN003",
                       population=45000, area=12.5, total_pickup_points=50, status="active"),
            models.Ward(id="WD007", name="Viman Nagar", code="VMN", zone_id="ZN003",
                       population=38000, area=8.5, total_pickup_points=40, status="active"),
            models.Ward(id="WD008", name="Wadgaon Sheri", code="WGS", zone_id="ZN003",
                       population=32000, area=7.8, total_pickup_points=30, status="active"),
            
            # West Zone - 2 wards
            models.Ward(id="WD009", name="Kothrud", code="KTR", zone_id="ZN004",
                       population=58000, area=15.5, total_pickup_points=48, status="active"),
            models.Ward(id="WD010", name="Warje", code="WRJ", zone_id="ZN004",
                       population=40000, area=10.2, total_pickup_points=32, status="active"),
        ]
        db.add_all(wards_data)
        db.commit()
        print(f"✅ Created {len(wards_data)} wards")
        
        # Create Vendors
        vendors_data = [
            models.Vendor(id="VND001", name="Mahesh Enterprises",
                         company_name="Mahesh Fleet Services Pvt Ltd",
                         phone="+91 9888777666", email="contact@maheshfleet.com",
                         address="100, Industrial Area, Pimpri, Pune",
                         gst_number="27AABCU9603R1ZX",
                         contract_start="2023-01-01", contract_end="2025-12-31",
                         status="active", supervisor_name="Mahesh Kulkarni",
                         supervisor_phone="+91 9888777667"),
            models.Vendor(id="VND002", name="Green Transport Co",
                         company_name="Green Transport Solutions",
                         phone="+91 9777666555", email="info@greentransport.com",
                         address="200, MIDC Bhosari, Pune",
                         gst_number="27AABCG1234R1ZY",
                         contract_start="2022-06-01", contract_end="2025-05-31",
                         status="active", supervisor_name="Ramesh Gaikwad",
                         supervisor_phone="+91 9777666556"),
            models.Vendor(id="VND003", name="City Waste Solutions",
                         company_name="City Waste Management Services",
                         phone="+91 9666555444", email="cityswaste@email.com",
                         address="300, Nigdi, Pune",
                         gst_number="27AABCC5678R1ZZ",
                         contract_start="2023-03-01", contract_end="2026-02-28",
                         status="active", supervisor_name="Sunil Pawar",
                         supervisor_phone="+91 9666555445"),
        ]
        db.add_all(vendors_data)
        db.commit()
        print(f"✅ Created {len(vendors_data)} vendors")
        
        # Create Drivers
        drivers_data = [
            models.Driver(id="DRV001", name="Rajesh Kumar", phone="+91 9876543210",
                         license_number="MH12-2020-0001234", license_expiry="2026-03-15",
                         vendor_id="VND001", status="active"),
            models.Driver(id="DRV002", name="Suresh Patil", phone="+91 9876543211",
                         license_number="MH12-2019-0005678", license_expiry="2025-08-20",
                         vendor_id="VND001", status="active"),
            models.Driver(id="DRV003", name="Amit Sharma", phone="+91 9876543212",
                         license_number="MH12-2021-0009012", license_expiry="2027-01-10",
                         vendor_id="VND001", status="active"),
            models.Driver(id="DRV004", name="Prakash Jadhav", phone="+91 9876543213",
                         license_number="MH12-2018-0003456", license_expiry="2025-06-15",
                         vendor_id="VND001", status="active"),
            models.Driver(id="DRV005", name="Vijay Deshmukh", phone="+91 9876543214",
                         license_number="MH12-2022-0007890", license_expiry="2028-02-20",
                         vendor_id="VND002", status="active"),
            models.Driver(id="DRV006", name="Manoj Patil", phone="+91 9876543215",
                         license_number="MH12-2020-0001122", license_expiry="2026-07-25",
                         vendor_id="VND002", status="active"),
            models.Driver(id="DRV007", name="Ravi Deshmukh", phone="+91 9876543216",
                         license_number="MH12-2021-0003344", license_expiry="2027-09-30",
                         vendor_id="VND002", status="active"),
            models.Driver(id="DRV008", name="Vikram Singh", phone="+91 9876543217",
                         license_number="MH12-2019-0005566", license_expiry="2025-11-05",
                         vendor_id="VND003", status="active"),
            models.Driver(id="DRV009", name="Deepak Jadhav", phone="+91 9876543218",
                         license_number="MH12-2020-0007788", license_expiry="2026-04-10",
                         vendor_id="VND003", status="active"),
            # Spare drivers
            models.Driver(id="DRV-SPR-001", name="Ganesh More", phone="+91 9876543219",
                         license_number="MH12-2021-0001001", license_expiry="2027-12-15",
                         vendor_id="VND001", status="active"),
            models.Driver(id="DRV-SPR-002", name="Santosh Kulkarni", phone="+91 9876543220",
                         license_number="MH12-2022-0002001", license_expiry="2028-05-20",
                         vendor_id="VND002", status="active"),
        ]
        db.add_all(drivers_data)
        db.commit()
        print(f"✅ Created {len(drivers_data)} drivers")
        
        # Create Routes
        routes_data = [
            # East Zone routes
            models.Route(id="RT001", name="Kharadi Primary Route 1", code="KHR-P1",
                        type=models.RouteType.PRIMARY, ward_id="WD006", zone_id="ZN003",
                        total_pickup_points=8, estimated_distance=15, estimated_time=150, status="active"),
            models.Route(id="RT002", name="Kharadi Secondary Route 1", code="KHR-S1",
                        type=models.RouteType.SECONDARY, ward_id="WD006", zone_id="ZN003",
                        total_pickup_points=2, estimated_distance=25, estimated_time=90, status="active"),
            models.Route(id="RT003", name="Viman Nagar Primary Route 1", code="VMN-P1",
                        type=models.RouteType.PRIMARY, ward_id="WD007", zone_id="ZN003",
                        total_pickup_points=6, estimated_distance=12, estimated_time=135, status="active"),
            models.Route(id="RT004", name="Viman Nagar Secondary Route 1", code="VMN-S1",
                        type=models.RouteType.SECONDARY, ward_id="WD007", zone_id="ZN003",
                        total_pickup_points=2, estimated_distance=28, estimated_time=100, status="active"),
            
            # North Zone routes
            models.Route(id="RT005", name="Aundh Primary Route 1", code="AND-P1",
                        type=models.RouteType.PRIMARY, ward_id="WD001", zone_id="ZN001",
                        total_pickup_points=7, estimated_distance=18, estimated_time=165, status="active"),
            models.Route(id="RT006", name="Baner Primary Route 1", code="BNR-P1",
                        type=models.RouteType.PRIMARY, ward_id="WD002", zone_id="ZN001",
                        total_pickup_points=6, estimated_distance=14, estimated_time=140, status="active"),
            models.Route(id="RT007", name="Aundh Secondary Route 1", code="AND-S1",
                        type=models.RouteType.SECONDARY, ward_id="WD001", zone_id="ZN001",
                        total_pickup_points=2, estimated_distance=35, estimated_time=110, status="active"),
            
            # South Zone routes
            models.Route(id="RT008", name="Hadapsar Primary Route 1", code="HDP-P1",
                        type=models.RouteType.PRIMARY, ward_id="WD004", zone_id="ZN002",
                        total_pickup_points=8, estimated_distance=20, estimated_time=180, status="active"),
            models.Route(id="RT009", name="Hadapsar Secondary Route 1", code="HDP-S1",
                        type=models.RouteType.SECONDARY, ward_id="WD004", zone_id="ZN002",
                        total_pickup_points=2, estimated_distance=15, estimated_time=60, status="active"),
        ]
        db.add_all(routes_data)
        db.commit()
        print(f"✅ Created {len(routes_data)} routes")
        
        # Create Trucks (9 regular + 2 spare)
        trucks_data = [
            # Vendor 1 trucks
            models.Truck(id="TRK001", registration_number="MH-12-AB-1234",
                        type=models.TruckType.COMPACTOR, capacity=8, capacity_unit="tons",
                        route_type=models.RouteType.PRIMARY, vendor_id="VND001", driver_id="DRV001",
                        imei_number="356938035643809", fuel_type="diesel", manufacturing_year=2021,
                        insurance_expiry="2025-03-15", fitness_expiry="2025-06-20",
                        status="active", last_service_date="2024-01-10",
                        zone_id="ZN003", ward_id="WD006", assigned_route_id="RT001",
                        latitude=18.5520, longitude=73.9400, current_status=models.TruckStatus.MOVING,
                        speed=25.0, trips_completed=3, trips_allowed=5),
            
            models.Truck(id="TRK002", registration_number="MH-12-CD-5678",
                        type=models.TruckType.MINI_TRUCK, capacity=3, capacity_unit="tons",
                        route_type=models.RouteType.SECONDARY, vendor_id="VND001", driver_id="DRV002",
                        imei_number="356938035643810", fuel_type="cng", manufacturing_year=2022,
                        insurance_expiry="2025-05-20", fitness_expiry="2025-08-15",
                        status="active", last_service_date="2024-02-05",
                        zone_id="ZN003", ward_id="WD006", assigned_route_id="RT002",
                        latitude=18.5560, longitude=73.9450, current_status=models.TruckStatus.IDLE,
                        speed=0.0, trips_completed=2, trips_allowed=4),
            
            models.Truck(id="TRK003", registration_number="MH-12-EF-9012",
                        type=models.TruckType.COMPACTOR, capacity=8, capacity_unit="tons",
                        route_type=models.RouteType.PRIMARY, vendor_id="VND001", driver_id="DRV003",
                        imei_number="356938035643811", fuel_type="diesel", manufacturing_year=2020,
                        insurance_expiry="2024-11-10", fitness_expiry="2024-12-05",
                        status="active", last_service_date="2024-03-01",
                        zone_id="ZN003", ward_id="WD007", assigned_route_id="RT003",
                        latitude=18.5620, longitude=73.9150, current_status=models.TruckStatus.DUMPING,
                        speed=0.0, trips_completed=4, trips_allowed=5),
            
            models.Truck(id="TRK004", registration_number="MH-12-GH-3456",
                        type=models.TruckType.DUMPER, capacity=12, capacity_unit="tons",
                        route_type=models.RouteType.SECONDARY, vendor_id="VND001", driver_id="DRV004",
                        imei_number="356938035643812", fuel_type="diesel", manufacturing_year=2019,
                        insurance_expiry="2024-08-25", fitness_expiry="2024-10-30",
                        status="maintenance", last_service_date="2024-01-25",
                        zone_id="ZN003", ward_id="WD007", assigned_route_id="RT004",
                        latitude=18.5580, longitude=73.9300, current_status=models.TruckStatus.OFFLINE,
                        speed=0.0, trips_completed=1, trips_allowed=3),
            
            # Vendor 2 trucks
            models.Truck(id="TRK005", registration_number="MH-12-IJ-7890",
                        type=models.TruckType.COMPACTOR, capacity=10, capacity_unit="tons",
                        route_type=models.RouteType.PRIMARY, vendor_id="VND002", driver_id="DRV005",
                        imei_number="356938035643813", fuel_type="electric", manufacturing_year=2023,
                        insurance_expiry="2026-01-15", fitness_expiry="2026-04-20",
                        status="active", last_service_date="2024-02-20",
                        zone_id="ZN001", ward_id="WD001", assigned_route_id="RT005",
                        latitude=18.5890, longitude=73.8150, current_status=models.TruckStatus.MOVING,
                        speed=30.0, trips_completed=2, trips_allowed=5),
            
            models.Truck(id="TRK006", registration_number="MH-12-KL-1122",
                        type=models.TruckType.OPEN_TRUCK, capacity=5, capacity_unit="tons",
                        route_type=models.RouteType.PRIMARY, vendor_id="VND002", driver_id="DRV006",
                        imei_number="356938035643814", fuel_type="diesel", manufacturing_year=2021,
                        insurance_expiry="2025-07-10", fitness_expiry="2025-09-15",
                        status="active", last_service_date="2024-01-15",
                        zone_id="ZN001", ward_id="WD002", assigned_route_id="RT006",
                        latitude=18.5650, longitude=73.7950, current_status=models.TruckStatus.MOVING,
                        speed=22.0, trips_completed=3, trips_allowed=5),
            
            models.Truck(id="TRK007", registration_number="MH-12-MN-3344",
                        type=models.TruckType.MINI_TRUCK, capacity=4, capacity_unit="tons",
                        route_type=models.RouteType.SECONDARY, vendor_id="VND002", driver_id="DRV007",
                        imei_number="356938035643815", fuel_type="cng", manufacturing_year=2022,
                        insurance_expiry="2025-10-20", fitness_expiry="2025-12-25",
                        status="active", last_service_date="2024-02-28",
                        zone_id="ZN001", ward_id="WD001", assigned_route_id="RT007",
                        latitude=18.5880, longitude=73.8200, current_status=models.TruckStatus.MOVING,
                        speed=18.0, trips_completed=2, trips_allowed=4),
            
            # Vendor 3 trucks
            models.Truck(id="TRK008", registration_number="MH-12-OP-5566",
                        type=models.TruckType.COMPACTOR, capacity=8, capacity_unit="tons",
                        route_type=models.RouteType.PRIMARY, vendor_id="VND003", driver_id="DRV008",
                        imei_number="356938035643816", fuel_type="diesel", manufacturing_year=2020,
                        insurance_expiry="2025-04-15", fitness_expiry="2025-06-20",
                        status="active", last_service_date="2024-01-20",
                        zone_id="ZN002", ward_id="WD004", assigned_route_id="RT008",
                        latitude=18.5010, longitude=73.9350, current_status=models.TruckStatus.MOVING,
                        speed=28.0, trips_completed=2, trips_allowed=5),
            
            models.Truck(id="TRK009", registration_number="MH-12-QR-7788",
                        type=models.TruckType.DUMPER, capacity=15, capacity_unit="tons",
                        route_type=models.RouteType.SECONDARY, vendor_id="VND003", driver_id="DRV009",
                        imei_number="356938035643817", fuel_type="diesel", manufacturing_year=2021,
                        insurance_expiry="2025-08-30", fitness_expiry="2025-11-05",
                        status="active", last_service_date="2024-03-05",
                        zone_id="ZN002", ward_id="WD004", assigned_route_id="RT009",
                        latitude=18.5050, longitude=73.9400, current_status=models.TruckStatus.DUMPING,
                        speed=0.0, trips_completed=3, trips_allowed=4),
            
            # Spare trucks
            models.Truck(id="TRK-SPR-001", registration_number="MH-12-SP-1001",
                        type=models.TruckType.COMPACTOR, capacity=8, capacity_unit="tons",
                        route_type=models.RouteType.PRIMARY, vendor_id="VND001", driver_id="DRV-SPR-001",
                        imei_number="356938035643818", fuel_type="diesel", manufacturing_year=2022,
                        insurance_expiry="2025-12-15", fitness_expiry="2026-02-20",
                        status="active", last_service_date="2024-02-15", is_spare=True,
                        zone_id="ZN003", ward_id="WD006",
                        latitude=18.5450, longitude=73.9350, current_status=models.TruckStatus.IDLE,
                        speed=0.0, trips_completed=0, trips_allowed=5),
            
            models.Truck(id="TRK-SPR-002", registration_number="MH-12-SP-2001",
                        type=models.TruckType.DUMPER, capacity=12, capacity_unit="tons",
                        route_type=models.RouteType.SECONDARY, vendor_id="VND002", driver_id="DRV-SPR-002",
                        imei_number="356938035643819", fuel_type="diesel", manufacturing_year=2022,
                        insurance_expiry="2025-11-10", fitness_expiry="2026-01-15",
                        status="active", last_service_date="2024-02-20", is_spare=True,
                        zone_id="ZN001", ward_id="WD001",
                        latitude=18.5870, longitude=73.8180, current_status=models.TruckStatus.IDLE,
                        speed=0.0, trips_completed=0, trips_allowed=4),
        ]
        db.add_all(trucks_data)
        db.commit()
        print(f"✅ Created {len(trucks_data)} trucks")
        
        # Create Pickup Points
        pickup_points_data = [
            # Kharadi
            models.PickupPoint(id="PP001", point_code="PP-KHR-001", name="EON IT Park",
                             address="EON Free Zone, Kharadi", latitude=18.5500, longitude=73.9380,
                             route_id="RT001", ward_id="WD006", waste_type="dry", type="commercial",
                             expected_pickup_time="06:00", schedule="Daily 6AM", geofence_radius=30,
                             status="active", last_collection="Today 6:05 AM"),
            models.PickupPoint(id="PP002", point_code="PP-KHR-002", name="World Trade Center",
                             address="WTC, Kharadi", latitude=18.5520, longitude=73.9400,
                             route_id="RT001", ward_id="WD006", waste_type="mixed", type="commercial",
                             expected_pickup_time="06:30", schedule="Daily 6:30AM", geofence_radius=25,
                             status="active", last_collection="Today 6:32 AM"),
            
            # Viman Nagar
            models.PickupPoint(id="PP003", point_code="PP-VMN-001", name="Phoenix Mall",
                             address="Phoenix Marketcity, Viman Nagar", latitude=18.5680, longitude=73.9200,
                             route_id="RT003", ward_id="WD007", waste_type="mixed", type="commercial",
                             expected_pickup_time="06:30", schedule="Daily 6:30AM", geofence_radius=40,
                             status="active", last_collection="Today 6:35 AM"),
            
            # Aundh
            models.PickupPoint(id="PP004", point_code="PP-AND-001", name="Aundh IT Hub",
                             address="Aundh IT Park", latitude=18.5920, longitude=73.8100,
                             route_id="RT005", ward_id="WD001", waste_type="dry", type="commercial",
                             expected_pickup_time="05:30", schedule="Daily 5:30AM", geofence_radius=35,
                             status="active", last_collection="Today 5:35 AM"),
            
            # Baner
            models.PickupPoint(id="PP005", point_code="PP-BNR-001", name="Baner Highstreet",
                             address="Baner Highstreet Mall", latitude=18.5700, longitude=73.7900,
                             route_id="RT006", ward_id="WD002", waste_type="mixed", type="commercial",
                             expected_pickup_time="06:00", schedule="Daily 6AM", geofence_radius=35,
                             status="active", last_collection="Today 6:05 AM"),
            
            # Hadapsar
            models.PickupPoint(id="PP006", point_code="PP-HDP-001", name="Magarpatta City",
                             address="Magarpatta City, Hadapsar", latitude=18.5100, longitude=73.9400,
                             route_id="RT008", ward_id="WD004", waste_type="mixed", type="commercial",
                             expected_pickup_time="05:30", schedule="Daily 5:30AM", geofence_radius=45,
                             status="active", last_collection="Today 5:35 AM"),
        ]
        db.add_all(pickup_points_data)
        db.commit()
        print(f"✅ Created {len(pickup_points_data)} pickup points")
        
        # Create some sample alerts
        alerts_data = [
            models.Alert(truck_id="TRK004", alert_type="breakdown", severity="high",
                        message="Engine issue - Truck offline", status="active"),
            models.Alert(truck_id="TRK003", alert_type="document_expiry", severity="medium",
                        message="Insurance expiring in 30 days", status="active"),
        ]
        db.add_all(alerts_data)
        db.commit()
        print(f"✅ Created {len(alerts_data)} alerts")
        
        # Create sample users (with pre-hashed passwords for demo)
        # In production, use proper bcrypt hashing
        users_data = [
            models.User(
                id="user-1",
                email="admin@city.gov",
                name="Admin User",
                hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyWpQvGZbN4m",  # admin123
                role="admin",
                is_active=True
            ),
            models.User(
                id="user-2",
                email="operator@city.gov",
                name="System Operator",
                hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyWpQvGZbN4m",  # operator123
                role="user",
                is_active=True
            ),
        ]
        db.add_all(users_data)
        db.commit()
        print(f"✅ Created {len(users_data)} users")
        
        # Create sample tickets
        from datetime import datetime, timedelta
        tickets_data = [
            models.Ticket(
                id="ticket-1",
                ticket_number="TKT-000001",
                title="Missed pickup reported in Viman Nagar",
                description="Multiple residents reported missed collection over the last two days.",
                category="complaint",
                priority="high",
                status="open",
                reporter_name="Ramesh Kumar",
                reporter_phone="+91 9876543210",
                reporter_email="ramesh@example.com",
                location="Viman Nagar",
                zone_id="ZN003",
                ward_id="WD006",
                due_date=datetime.utcnow() + timedelta(hours=24)
            ),
            models.Ticket(
                id="ticket-2",
                ticket_number="TKT-000002",
                title="Request for additional bin in Aundh",
                description="Request to place an additional bin near the society entrance.",
                category="request",
                priority="medium",
                status="in_progress",
                reporter_name="Priya Singh",
                reporter_phone="+91 9876543211",
                reporter_email="priya@example.com",
                location="Aundh, DP Road",
                zone_id="ZN001",
                ward_id="WD001",
                assigned_to="user-1"
            ),
            models.Ticket(
                id="ticket-3",
                ticket_number="TKT-000003",
                title="Excellent service by collection team",
                description="Timely collection and courteous staff reported by residents.",
                category="feedback",
                priority="low",
                status="resolved",
                reporter_name="Suresh Patil",
                reporter_email="suresh@example.com",
                location="Baner",
                zone_id="ZN001",
                ward_id="WD002",
                resolved_at=datetime.utcnow()
            ),
            models.Ticket(
                id="ticket-4",
                ticket_number="TKT-000004",
                title="Route delay due to road closure",
                description="Driver reported a temporary road closure affecting route timing today.",
                category="route_issue",
                priority="low",
                status="pending",
                reporter_name="Driver Feedback",
                location="Pashan",
                zone_id="ZN002",
                ward_id="WD004",
                due_date=datetime.utcnow() + timedelta(hours=8)
            ),
            models.Ticket(
                id="ticket-5",
                ticket_number="TKT-000005",
                title="GTC checkpoint cleanliness below threshold",
                description="Recent checkpoint shows truck cleanliness below acceptable score. Needs inspection.",
                category="vehicle_issue",
                priority="medium",
                status="open",
                reporter_name="GTC Checkpoint",
                location="GTC Facility",
                zone_id="ZN002",
                ward_id="WD005",
                due_date=datetime.utcnow() + timedelta(hours=18)
            ),
        ]
        db.add_all(tickets_data)
        db.commit()
        print(f"✅ Created {len(tickets_data)} tickets")
        
        # Create sample Twitter mentions
        twitter_data = [
            models.TwitterMention(
                id="mention-1",
                tweet_id="1234567890",
                author="@citizen_pune",
                author_name="Pune Citizen",
                content="@MunicipalGC Garbage truck hasn't arrived in Kharadi sector 5 for 2 days now. Please look into this urgently!",
                timestamp=datetime.utcnow() - timedelta(hours=2),
                likes=45,
                retweets=12,
                replies=8,
                sentiment="negative",
                category="complaint",
                location="Kharadi, Sector 5",
                is_responded=False
            ),
            models.TwitterMention(
                id="mention-2",
                tweet_id="1234567891",
                author="@green_warrior",
                author_name="Green Warrior",
                content="@MunicipalGC Thank you for the quick response yesterday! The new collection schedule is working great in our area.",
                timestamp=datetime.utcnow() - timedelta(hours=4),
                likes=89,
                retweets=23,
                replies=5,
                sentiment="positive",
                category="appreciation",
                location="Aundh",
                is_responded=True,
                response_text="Thank you for your feedback! We're glad the new schedule is working well.",
                response_at=datetime.utcnow() - timedelta(hours=3)
            ),
            models.TwitterMention(
                id="mention-3",
                tweet_id="1234567892",
                author="@eco_pune",
                author_name="Eco Pune",
                content="@MunicipalGC What is the process for scheduling bulk waste pickup in Baner area?",
                timestamp=datetime.utcnow() - timedelta(hours=1),
                likes=15,
                retweets=3,
                replies=2,
                sentiment="neutral",
                category="query",
                location="Baner",
                is_responded=False
            ),
        ]
        db.add_all(twitter_data)
        db.commit()
        print(f"✅ Created {len(twitter_data)} twitter mentions")
        
        print("\n🎉 Database initialization completed successfully!")
        print(f"📊 Summary:")
        print(f"   - Zones: {len(zones_data)}")
        print(f"   - Wards: {len(wards_data)}")
        print(f"   - Vendors: {len(vendors_data)}")
        print(f"   - Drivers: {len(drivers_data)}")
        print(f"   - Routes: {len(routes_data)}")
        print(f"   - Trucks: {len(trucks_data)}")
        print(f"   - Pickup Points: {len(pickup_points_data)}")
        print(f"   - Alerts: {len(alerts_data)}")
        print(f"   - Users: {len(users_data)}")
        print(f"   - Tickets: {len(tickets_data)}")
        print(f"   - Twitter Mentions: {len(twitter_data)}")
        print(f"\n👤 Login Credentials:")
        print(f"   Admin: admin@city.gov / admin123")
        print(f"   Operator: operator@city.gov / operator123")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
