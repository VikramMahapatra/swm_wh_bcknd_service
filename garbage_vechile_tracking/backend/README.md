# Garbage Vehicle Tracking System - Backend

FastAPI backend for the Garbage Vehicle Tracking System for Pune City.

## Features

- **Real-time Vehicle Tracking**: Live GPS tracking with WebSocket support
- **Vehicle Simulation**: Automated simulation of vehicle movement for testing
- **Zone & Ward Management**: Organize collection areas into zones and wards
- **Vendor Management**: Track vendors providing vehicles and services
- **Route Management**: Define and manage collection routes with pickup points
- **Alert System**: Real-time alerts for breakdowns, delays, and document expiry
- **Reports & Analytics**: Performance metrics and collection efficiency reports

## Technology Stack

- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: ORM for database operations
- **SQLite**: Lightweight database (easily switchable to PostgreSQL)
- **WebSockets**: Real-time data streaming
- **Pydantic**: Data validation and settings management

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file (copy from `.env.example`):
```bash
cp .env.example .env
```

5. Initialize the database with Pune city data:
```bash
python init_db.py
```

### Running the Server

Start the FastAPI server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Interactive API docs: http://localhost:8000/docs
- Alternative API docs: http://localhost:8000/redoc

## API Endpoints

### Zones
- `GET /api/zones/` - List all zones
- `GET /api/zones/{zone_id}` - Get zone details
- `POST /api/zones/` - Create new zone
- `GET /api/zones/{zone_id}/wards` - Get wards in a zone

### Trucks
- `GET /api/trucks/` - List all trucks (with filters)
- `GET /api/trucks/live` - Get live tracking data for all trucks
- `GET /api/trucks/spare` - Get spare trucks
- `GET /api/trucks/{truck_id}` - Get truck details
- `POST /api/trucks/` - Create new truck
- `PUT /api/trucks/{truck_id}` - Update truck

### Vendors
- `GET /api/vendors/` - List all vendors
- `POST /api/vendors/` - Create new vendor

### Routes
- `GET /api/routes/` - List all routes (with filters)
- `POST /api/routes/` - Create new route
- `GET /api/routes/{route_id}/pickup-points` - Get pickup points on a route

### Pickup Points
- `GET /api/pickup-points/` - List all pickup points (with filters)
- `POST /api/pickup-points/` - Create new pickup point

### Alerts
- `GET /api/alerts/` - List all alerts (with filters)
- `POST /api/alerts/` - Create new alert
- `GET /api/alerts/active` - Get active alerts
- `GET /api/alerts/expiry` - Get document expiry alerts

### Reports
- `GET /api/reports/statistics` - Overall system statistics
- `GET /api/reports/zone-performance` - Zone-wise performance metrics
- `GET /api/reports/vendor-performance` - Vendor-wise performance metrics
- `GET /api/reports/collection-efficiency` - Collection efficiency report

### WebSocket
- `WS /ws` - Real-time vehicle position updates

## Data Structure

### Pune City Configuration

The system is configured with **4 zones** covering Pune city:

1. **North Zone (NZ)**: Aundh, Baner, Pashan
2. **South Zone (SZ)**: Hadapsar, Kondhwa
3. **East Zone (EZ)**: Kharadi, Viman Nagar, Wadgaon Sheri
4. **West Zone (WZ)**: Kothrud, Warje

Each zone has:
- Multiple wards
- Assigned vendors
- Primary and secondary collection vehicles
- Spare vehicles for backup
- Collection routes with pickup points

## Vehicle Simulation

The backend includes an automatic vehicle movement simulator that:
- Moves vehicles along routes in real-time
- Simulates different statuses (moving, idle, dumping, offline)
- Updates GPS coordinates every 5 seconds
- Broadcasts updates via WebSocket

The simulation starts automatically when the server starts.

## Development

### Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── database/
│   │   ├── database.py      # Database connection
│   ├── models/
│   │   ├── models.py        # SQLAlchemy models
│   ├── schemas/
│   │   ├── schemas.py       # Pydantic schemas
│   ├── routers/
│   │   ├── zones.py         # Zone endpoints
│   │   ├── trucks.py        # Truck endpoints
│   │   ├── vendors.py       # Vendor endpoints
│   │   ├── routes.py        # Route endpoints
│   │   ├── pickup_points.py # Pickup point endpoints
│   │   ├── alerts.py        # Alert endpoints
│   │   └── reports.py       # Report endpoints
│   └── services/
│       └── vehicle_simulator.py  # Vehicle movement simulation
├── init_db.py               # Database initialization script
├── requirements.txt         # Python dependencies
└── .env.example            # Environment variables template
```

### Adding New Features

1. Create new models in `app/models/models.py`
2. Create corresponding schemas in `app/schemas/schemas.py`
3. Create router in `app/routers/`
4. Register router in `app/main.py`
5. Update `init_db.py` if initial data is needed

## Testing

You can test the API using:
- Built-in Swagger UI: http://localhost:8000/docs
- cURL commands
- Postman or similar tools
- Frontend integration

Example cURL command:
```bash
curl http://localhost:8000/api/trucks/live
```

## Production Deployment

For production deployment:

1. Use PostgreSQL instead of SQLite
2. Update `DATABASE_URL` in `.env`
3. Set strong `SECRET_KEY`
4. Use a production WSGI server (Gunicorn)
5. Enable HTTPS
6. Configure proper CORS origins
7. Set up monitoring and logging

## License

This project is part of the Garbage Vehicle Tracking System.
