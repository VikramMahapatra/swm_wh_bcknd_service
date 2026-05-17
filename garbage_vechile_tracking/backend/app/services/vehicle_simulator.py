import asyncio
import random
import math
from datetime import datetime
from typing import Dict, List
from sqlalchemy.orm import Session
from ..models.models import Truck, TruckStatus
from ..database.database import SessionLocal

class VehicleSimulator:
    def __init__(self):
        self.simulation_running = False
        self.trucks_data: Dict[str, dict] = {}
        
    def calculate_new_position(self, lat: float, lng: float, speed_kmh: float, heading: float) -> tuple:
        """Calculate new GPS position based on speed and heading"""
        # Convert speed from km/h to degrees per second (approximate)
        speed_deg_per_sec = speed_kmh / 111000 / 3600  # 1 degree ≈ 111km
        
        # Calculate movement in degrees
        lat_change = speed_deg_per_sec * math.cos(math.radians(heading)) * 5  # 5 second intervals
        lng_change = speed_deg_per_sec * math.sin(math.radians(heading)) * 5
        
        return lat + lat_change, lng + lng_change
    
    def get_route_bounds(self, zone_id: str) -> dict:
        """Get geographical bounds for each zone"""
        bounds = {
            "ZN001": {"lat_min": 18.56, "lat_max": 18.60, "lng_min": 73.78, "lng_max": 73.83},  # North Zone
            "ZN002": {"lat_min": 18.48, "lat_max": 18.52, "lng_min": 73.92, "lng_max": 73.96},  # South Zone
            "ZN003": {"lat_min": 18.55, "lat_max": 18.58, "lng_min": 73.91, "lng_max": 73.95},  # East Zone
            "ZN004": {"lat_min": 18.48, "lat_max": 18.52, "lng_min": 73.82, "lng_max": 73.88},  # West Zone
            "ZN005": {"lat_min": 18.51, "lat_max": 18.54, "lng_min": 73.84, "lng_max": 73.87},  # Central Zone
        }
        return bounds.get(zone_id, bounds["ZN003"])
    
    def simulate_truck_movement(self, truck: Truck, bounds: dict):
        """Simulate realistic truck movement patterns"""
        if not truck.latitude or not truck.longitude:
            # Initialize position within zone bounds
            truck.latitude = random.uniform(bounds["lat_min"], bounds["lat_max"])
            truck.longitude = random.uniform(bounds["lng_min"], bounds["lng_max"])
            truck.current_status = TruckStatus.IDLE
            truck.speed = 0.0
            return
        
        # Simulate different behaviors based on current status
        if truck.current_status == TruckStatus.MOVING:
            # Moving trucks
            if truck.trips_completed >= truck.trips_allowed:
                # Completed all trips, go idle
                truck.current_status = TruckStatus.IDLE
                truck.speed = 0.0
            else:
                # Continue moving
                speed = random.uniform(15, 40)  # km/h
                heading = random.uniform(0, 360)
                new_lat, new_lng = self.calculate_new_position(
                    truck.latitude, truck.longitude, speed, heading
                )
                
                # Keep within bounds
                truck.latitude = max(bounds["lat_min"], min(bounds["lat_max"], new_lat))
                truck.longitude = max(bounds["lng_min"], min(bounds["lng_max"], new_lng))
                truck.speed = speed
                
                # Random chance to go dumping
                if random.random() < 0.1:
                    truck.current_status = TruckStatus.DUMPING
                    truck.speed = 0.0
        
        elif truck.current_status == TruckStatus.IDLE:
            truck.speed = 0.0
            # Random chance to start moving
            if random.random() < 0.3:
                truck.current_status = TruckStatus.MOVING
        
        elif truck.current_status == TruckStatus.DUMPING:
            truck.speed = 0.0
            # Random chance to finish dumping
            if random.random() < 0.4:
                truck.current_status = TruckStatus.MOVING
                truck.trips_completed += 1
        
        elif truck.current_status == TruckStatus.OFFLINE:
            truck.speed = 0.0
            # Random chance to come back online
            if random.random() < 0.05:
                truck.current_status = TruckStatus.IDLE
        
        truck.last_update = datetime.utcnow()
    
    async def run_simulation(self):
        """Main simulation loop"""
        self.simulation_running = True
        print("🚛 Vehicle simulation started")
        
        while self.simulation_running:
            try:
                db = SessionLocal()
                trucks = db.query(Truck).filter(Truck.status == "active").all()
                
                for truck in trucks:
                    if truck.current_status != TruckStatus.BREAKDOWN:
                        bounds = self.get_route_bounds(truck.zone_id)
                        self.simulate_truck_movement(truck, bounds)
                
                db.commit()
                db.close()
                
                # Update every 5 seconds
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"Error in simulation: {e}")
                await asyncio.sleep(5)
    
    def stop_simulation(self):
        """Stop the simulation"""
        self.simulation_running = False
        print("🛑 Vehicle simulation stopped")

# Global simulator instance
vehicle_simulator = VehicleSimulator()
