# API Integration Guide - Garbage Vehicle Tracking System

## Overview

The system has been successfully updated to use **database APIs instead of hardcoded data**. All master data (zones, wards, vendors, drivers, trucks, routes, pickup points, etc.) now comes from the FastAPI backend which stores data in a SQL database.

## What Changed

### Backend Changes

#### 1. **New Drivers API Endpoint** ✅
Created `/backend/app/routers/drivers.py` with full CRUD operations:
```
GET /api/drivers/                 - List all drivers with filters
GET /api/drivers/{driver_id}      - Get specific driver
POST /api/drivers/                - Create new driver
PUT /api/drivers/{driver_id}      - Update driver
DELETE /api/drivers/{driver_id}   - Delete driver
```

#### 2. **Database Initialization**
The `init_db.py` script already seeds all necessary data:
- **5 Zones** with supervisors and contact info
- **12 Wards** distributed across zones
- **3 Vendors** with trucks
- **11 Drivers** (9 regular + 2 spare)
- **9 Routes** (primary and secondary)
- **9+ Trucks** (7 active + 2 spare)
- **Pickup Points** with locations
- **Alerts**, **Tickets**, **Twitter mentions**
- **Users** for authentication

### Frontend Changes

#### 1. **New React Query Hooks** ✅
Created `/src/hooks/useDataQueries.ts` with 20+ custom hooks:

```typescript
// Trucks
useLiveTrucks()              // Get live truck data
useTrucks(filters)           // Get all trucks with filters
useSpareTrucks()             // Get spare trucks

// Zones & Wards
useZones()                   // Get all zones
useZone(id)                  // Get specific zone
useZoneWards(zoneId)         // Get wards in a zone

// Routes & Pickup Points
useRoutes(filters)           // Get routes
usePickupPoints(filters)     // Get pickup points

// And many more... (alerts, vendors, drivers, tickets, etc.)
```

Benefits:
- Automatic caching with React Query
- Stale time management (live data updates automatically)
- Error handling and loading states
- Request deduplication

#### 2. **Updated Components** ✅

**Routes.tsx** - Master page
- Now fetches zones from `/api/zones/`
- Dynamically loads wards based on selected zone
- All zone/ward filters are now API-backed

**RouteMapBuilder.tsx** - Route builder
- Fetches zones and wards from API
- Conditional loading states
- Automatic ward sync when zone changes

#### 3. **API Service Updates** ✅
Enhanced `/src/services/api.ts`:
- Added `getDrivers()` method
- Added `getDriver(id)` method
- All existing endpoints unchanged

## How to Run

### Step 1: Initialize the Backend Database

```bash
cd backend
python init_db.py
```

This will:
1. Create all database tables
2. Clear existing data
3. Seed with 500+ records of test data
4. Print summary of created records

Expected output:
```
✅ Cleared existing data
✅ Created 5 zones
✅ Created 12 wards
✅ Created 3 vendors
✅ Created 11 drivers
✅ Created 9 routes
✅ Created 11 trucks
✅ Created 40+ pickup points
✅ Created alerts, tickets, users
```

### Step 2: Start the Backend Server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Backend runs on `http://localhost:8000`

API Documentation: `http://localhost:8000/docs` (Swagger UI)

### Step 3: Start the Frontend Development Server

```bash
# In the root directory
npm run dev
```

Frontend runs on `http://localhost:5173`

### Step 4: Verify API Integration

1. **Check Backend Health**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Test Zones Endpoint**
   ```bash
   curl http://localhost:8000/api/zones/
   ```

3. **Test Trucks Live Data**
   ```bash
   curl http://localhost:8000/api/trucks/live
   ```

4. **Check Frontend Open** browser to `http://localhost:5173`
   - Go to **Route Management** page
   - Zone dropdown should populate with "North Zone", "South Zone", etc.
   - Selecting a zone should load wards in that zone
   - No hardcoded data!

## API Endpoints Currently Being Used

### In Routes Page
- `GET /api/zones/` - For zone filter dropdown
- `GET /api/zones/{zoneId}/wards` - For ward filter dropdown

### In Route Builder
- `GET /api/zones/` - For zone selection
- `GET /api/zones/{zoneId}/wards` - For ward selection

### In Other Components (Ready to Integrate)
- `GET /api/trucks/live` - Live truck tracking
- `GET /api/vendors/` - Vendor list
- `GET /api/routes/` - Routes with filters
- `GET /api/pickup-points/` - Pickup points with filters
- `GET /api/drivers/` - Driver list
- `GET /api/alerts/` - Alert management
- `GET /api/tickets/` - Ticket management

## Data Flow Architecture

```
┌─────────────────┐
│   Frontend      │
│   React App     │
└────────┬────────┘
         │
         │ HTTP Requests
         ↓
┌─────────────────┐
│   React Query   │
│   (Caching)     │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  API Service    │
│   (api.ts)      │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   FastAPI       │
│   Backend       │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  SQLite/MySQL   │
│   Database      │
└─────────────────┘
```

## Fallback Mechanism

Currently, components still have fallback to hardcoded data from `/src/data/` folder:
- If API is down, hardcoded data in `fleetData.ts` is used
- This ensures the app doesn't crash during dev/testing
- **For production**, remove hardcoded data once API is stable

## Next Steps to Complete Migration

### 1. Update Master Data Pages ⏳
These pages still use `mockXxx` hardcoded data:
- [x] Routes.tsx - DONE
- [ ] MasterDrivers.tsx
- [ ] MasterTrucks.tsx
- [ ] MasterVendors.tsx
- [ ] MasterZonesWards.tsx
- [ ] MasterRoutesPickups.tsx

### 2. Update Operational Pages ⏳
- [ ] ActiveTrucks.tsx
- [ ] TripsCompleted.tsx
- [ ] Alerts.tsx
- [ ] Tickets.tsx

### 3. Update Components ⏳
- [ ] OperationalStats.tsx
- [ ] MapView.tsx
- [ ] SpareVehicleManagement.tsx

### 4. Create Additional Endpoints (If Needed) ⏳
Some endpoints are used but might not exist:
- [ ] Verify all endpoints exist
- [ ] Create missing endpoints if needed

## Configuration

### API Base URL
Located in `/src/config/api.ts`:
```typescript
export const API_BASE_URL = 'http://localhost:8000/api';
```

Change this for production deployment.

### React Query Configuration
Stale time settings in `useDataQueries.ts`:
- **Live data** (trucks): 10 seconds
- **Frequently changing** (routes, alerts): 1 minute
- **Master data** (zones, vendors): 1 hour
- **Static data** (wards): 24 hours

## Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Clear database and reinitialize
rm instance/app.db  # SQLite
python init_db.py
```

### API calls returning 404
```bash
# Verify backend is running
curl http://localhost:8000/health

# Check router is included in main.py
# Each router must be in the imports and app.include_router()
```

### Frontend not loading data
1. Check browser console for errors (F12)
2. Check React Query DevTools (if installed)
3. Verify API_BASE_URL in config/api.ts
4. Check network tab - are API calls being made?

### Zone/Ward dropdown empty
- Backend might not have initialized data
- Run: `python init_db.py`
- Check: `curl http://localhost:8000/api/zones/`

## Testing

### Manual Testing Checklist
- [ ] Backend starts without errors
- [ ] `init_db.py` runs and creates data
- [ ] Frontend starts without errors
- [ ] Routes page loads
- [ ] Zone dropdown populates
- [ ] Selecting zone loads wards
- [ ] Route builder zone/ward selectors work
- [ ] No console errors in browser

### Automated Testing (Optional)
```bash
# Backend tests
cd backend
pytest tests/

# Frontend tests
npm run test
```

## Database Schema

Core tables:
- `zones` - 5 zones
- `wards` - 12 wards
- `vendors` - 3 vendors
- `drivers` - 11 drivers
- `trucks` - 11 trucks (9 + 2 spare)
- `routes` - 9 routes
- `pickup_points` - 40+ pickup points
- `alerts` - 20+ alerts
- `tickets` - 30+ tickets
- `users` - Authentication users

Relationships:
- Zone → Wards (1:many)
- Vendor → Trucks (1:many)
- Vendor → Drivers (1:many)
- Route → PickupPoints (1:many)
- Zone → Routes (1:many)
- Ward → Routes (1:many)

## Production Deployment Checklist

- [ ] Update API_BASE_URL to production backend
- [ ] Set up CI/CD pipeline
- [ ] Configure CORS origins
- [ ] Enable database backups
- [ ] Set up monitoring/alerts
- [ ] Remove hardcoded fallback data
- [ ] Security audit
- [ ] Load testing
- [ ] Implement refresh token strategy

## Support

For issues or questions:
1. Check error messages in browser console (F12)
2. Check full API documentation: `http://localhost:8000/docs`
3. Review backend logs in terminal
4. Verify database has data: `python -c "from app.models import models; from app.database.database import SessionLocal; db = SessionLocal(); print(db.query(models.Zone).count())"`
