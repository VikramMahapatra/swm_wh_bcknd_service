# Garbage Vehicle Tracking System

A comprehensive real-time garbage vehicle tracking system for Pune City with live GPS monitoring, route management, and analytics.

## 🚀 Features

### Backend (Python FastAPI)
- **Real-time Vehicle Tracking**: Live GPS tracking with WebSocket support
- **Automated Vehicle Simulation**: Realistic vehicle movement simulation for testing
- **Zone & Ward Management**: Organize Pune city into 4 zones with multiple wards
- **Vendor Management**: Track 3 vendors providing primary, secondary, and spare vehicles
- **Route Management**: Manage collection routes with pickup points
- **Alert System**: Real-time alerts for breakdowns, delays, and document expiry
- **Reports & Analytics**: Performance metrics and collection efficiency reports
- **RESTful API**: Complete CRUD operations for all entities

### Frontend (React + TypeScript)
- **Live Map View**: Real-time vehicle positions on Google Maps
- **Dashboard**: Overview of fleet statistics and operational metrics
- **Fleet Management**: Manage trucks, drivers, and vendors
- **Route Planning**: Create and manage collection routes with pickup points
- **Alert Management**: View and manage system alerts
- **Reports**: Zone performance, vendor performance, and collection efficiency
- **Responsive Design**: Modern UI with Tailwind CSS and shadcn/ui components

## 📊 System Architecture

### Pune City Configuration

The system covers Pune city with **4 zones**:

1. **North Zone (NZ)**: Aundh, Baner, Pashan
2. **South Zone (SZ)**: Hadapsar, Kondhwa
3. **East Zone (EZ)**: Kharadi, Viman Nagar, Wadgaon Sheri
4. **West Zone (WZ)**: Kothrud, Warje

Each zone includes:
- 2-3 wards
- 3 vendors providing services
- 11 vehicles (9 regular + 2 spare)
- Primary and secondary collection routes
- Multiple pickup points

## 🛠️ Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: ORM for database operations
- **SQLite**: Lightweight database (production-ready for PostgreSQL)
- **WebSockets**: Real-time data streaming
- **Pydantic**: Data validation
- **Uvicorn**: ASGI server

### Frontend
- **React 18**: UI library
- **TypeScript**: Type-safe JavaScript
- **Vite**: Fast build tool
- **Tailwind CSS**: Utility-first CSS framework
- **shadcn/ui**: High-quality component library
- **React Router**: Client-side routing
- **Google Maps API**: Map visualization
- **Tanstack Query**: Data fetching and caching

## 📦 Installation & Setup

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or bun

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```bash
cp .env.example .env
```

5. Initialize database with Pune city data:
```bash
python init_db.py
```

6. Start backend server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- WebSocket: ws://localhost:8000/ws

### Frontend Setup

1. Navigate to project root:
```bash
cd ..
```

2. Install dependencies:
```bash
npm install
```

3. Create `.env` file:
```bash
cp .env.example .env
```

4. Start development server:
```bash
npm run dev
```

Frontend will be available at: http://localhost:5173

## 🎯 Usage

### Starting Both Services

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
npm run dev
```

### Default Access
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 📡 API Endpoints

### Key Endpoints

**Trucks:**
- `GET /api/trucks/live` - Get live tracking data for all trucks
- `GET /api/trucks/spare` - Get spare vehicles
- `GET /api/trucks/` - List all trucks with filters

**Zones:**
- `GET /api/zones/` - List all zones
- `GET /api/zones/{zone_id}/wards` - Get wards in a zone

**Alerts:**
- `GET /api/alerts/active` - Get active alerts
- `GET /api/alerts/expiry` - Get document expiry alerts

**Reports:**
- `GET /api/reports/statistics` - Overall system statistics
- `GET /api/reports/zone-performance` - Zone-wise metrics
- `GET /api/reports/collection-efficiency` - Collection efficiency

See complete API documentation at: http://localhost:8000/docs

## 🧪 Testing

### Test Backend API
```bash
# Health check
curl http://localhost:8000/health

# Get zones
curl http://localhost:8000/api/zones/

# Get live trucks
curl http://localhost:8000/api/trucks/live
```

### Frontend Testing
The frontend automatically connects to the backend when both services are running. Open http://localhost:5173 to see live vehicle tracking.

## 📁 Project Structure

```
garbage_vechile_tracking/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI application
│   │   ├── models/            # Database models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── routers/           # API endpoints
│   │   ├── services/          # Business logic
│   │   └── database/          # Database connection
│   ├── init_db.py             # Database initialization
│   ├── requirements.txt       # Python dependencies
│   └── README.md              # Backend documentation
│
├── src/                       # React frontend
│   ├── components/            # React components
│   ├── pages/                 # Page components
│   ├── hooks/                 # Custom hooks
│   ├── services/              # API services
│   ├── config/                # Configuration
│   ├── data/                  # Static data (fallback)
│   └── lib/                   # Utilities
│
├── public/                    # Static assets
├── package.json               # Node dependencies
└── README.md                  # Project documentation
```

## 🔧 Configuration

### Backend Configuration (.env)
```env
DATABASE_URL=sqlite:///./garbage_tracking.db
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Frontend Configuration (.env)
```env
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
```

## 🚚 Features Walkthrough

### 1. Live Vehicle Tracking
- Real-time GPS positions updated every 5 seconds
- WebSocket connection for instant updates
- Map markers show vehicle status (moving, idle, dumping, offline)
- Vehicle speed and trip completion tracking

### 2. Vehicle Simulation
- Automatic simulation of vehicle movement
- Realistic speed and direction changes
- Status changes (moving → dumping → idle)
- Operates within zone boundaries

### 3. Zone Management
- 4 zones covering Pune city
- 10 wards distributed across zones
- Zone supervisors and contact information
- Performance metrics per zone

### 4. Vendor Management
- 3 vendors providing services
- Track contract details and GST numbers
- Vendor-wise performance reports
- Supervisor contact information

### 5. Fleet Management
- 11 vehicles (9 regular + 2 spare)
- Primary and secondary collection vehicles
- Vehicle details (registration, capacity, fuel type)
- Maintenance and document tracking

### 6. Route Management
- 9 collection routes across zones
- Primary and secondary routes
- Pickup point assignments
- Estimated distance and time

### 7. Alert System
- Breakdown alerts
- Document expiry warnings (insurance, fitness)
- Real-time notifications
- Alert severity levels

### 8. Reports & Analytics
- Overall system statistics
- Zone-wise performance
- Vendor performance metrics
- Collection efficiency tracking

## 🔄 Real-time Updates

The system uses WebSockets for real-time updates:
- Vehicle positions updated every 5 seconds
- Automatic reconnection on disconnect
- Broadcast to all connected clients
- Low latency updates

## 🌐 Production Deployment

### Backend
1. Use PostgreSQL instead of SQLite
2. Update DATABASE_URL in .env
3. Set strong SECRET_KEY
4. Use Gunicorn with Uvicorn workers
5. Configure HTTPS and CORS properly
6. Set up monitoring and logging

### Frontend
1. Build production bundle: `npm run build`
2. Deploy to hosting service (Vercel, Netlify, etc.)
3. Update API_URL and WS_URL for production
4. Configure domain and SSL

## 📝 Future Enhancements

- [ ] Mobile app (React Native)
- [ ] Route optimization algorithms
- [ ] Citizen complaint management
- [ ] SMS/Email notifications
- [ ] Advanced analytics and ML predictions
- [ ] Integration with waste management APIs
- [ ] Multi-language support
- [ ] Offline mode support

## 🤝 Contributing

This is a demonstration project for garbage vehicle tracking in Pune city.

## 📄 License

MIT License - See LICENSE file for details

## 👥 Authors

Built as part of the Garbage Vehicle Tracking System initiative for Pune City.

## 📞 Support

For issues and questions, please open an issue in the repository.

---

**Note**: This system is designed for Pune city with realistic data for 4 zones, 10 wards, 3 vendors, and 11 vehicles. The vehicle simulation provides realistic movement patterns for testing and demonstration purposes.
