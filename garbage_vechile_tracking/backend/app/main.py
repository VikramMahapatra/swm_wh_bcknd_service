from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import json
from datetime import datetime

from .database.database import engine, SessionLocal
from .models import models
from .routers import zones, trucks, vendors, routes, pickup_points, alerts, reports, drivers, gtc_checkpoints
from .services.vehicle_simulator import vehicle_simulator

# Create database tables
models.Base.metadata.create_all(bind=engine)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# Background task for broadcasting live positions
async def broadcast_truck_positions():
    while True:
        try:
            db = SessionLocal()
            trucks = db.query(models.Truck).filter(models.Truck.status == "active").all()
            
            truck_data = []
            for truck in trucks:
                if truck.latitude and truck.longitude:
                    truck_data.append({
                        "id": truck.id,
                        "registration_number": truck.registration_number,
                        "latitude": truck.latitude,
                        "longitude": truck.longitude,
                        "status": truck.current_status.value if truck.current_status else "idle",
                        "speed": truck.speed or 0.0,
                        "trips_completed": truck.trips_completed,
                        "last_update": truck.last_update.isoformat() if truck.last_update else None
                    })
            
            db.close()
            
            if truck_data:
                await manager.broadcast({
                    "type": "truck_positions",
                    "data": truck_data,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            await asyncio.sleep(5)  # Broadcast every 5 seconds
        except Exception as e:
            print(f"Error broadcasting: {e}")
            await asyncio.sleep(5)

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    simulation_task = asyncio.create_task(vehicle_simulator.run_simulation())
    broadcast_task = asyncio.create_task(broadcast_truck_positions())
    
    yield
    
    # Shutdown
    vehicle_simulator.stop_simulation()
    simulation_task.cancel()
    broadcast_task.cancel()

# Create FastAPI app
app = FastAPI(
    title="Garbage Vehicle Tracking API",
    description="API for managing garbage vehicle tracking system in Pune",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# https://swm.zentrixel.com
# https://api-swm.zentrixel.com

# Include routers
app.include_router(zones.router, prefix="/api")
app.include_router(trucks.router, prefix="/api")
app.include_router(vendors.router, prefix="/api")
app.include_router(drivers.router, prefix="/api")
app.include_router(routes.router, prefix="/api")
app.include_router(pickup_points.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(gtc_checkpoints.router, prefix="/api")

# Import new routers
from .routers import auth, tickets, social_media, analytics

# Include new routers
app.include_router(auth.router, prefix="/api")
app.include_router(tickets.router, prefix="/api")
app.include_router(social_media.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Root endpoint
@app.get("/")
def read_root():
    return {
        "message": "Garbage Vehicle Tracking API",
        "version": "1.0.0",
        "status": "running"
    }

# Health check
@app.get("/health")
def health_check():
    return {"status": "healthy"}
