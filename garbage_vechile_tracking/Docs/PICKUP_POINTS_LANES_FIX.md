# Pickup Points & Lane Coordinates Integration - FIXED

## Issues Resolved

### 1. **Pickup Points Not Coming from Database**
**Problem:** The frontend was using hardcoded mock pickup points instead of fetching real data from the database.

**Solution Implemented:**
- Updated `TruckJourneyReplayModal.tsx` to use the `useRoutes()` hook which fetches actual routes with their `pickup_points` array from the database API
- Modified `useRouteBasedSimulation.ts` to properly consume the `pickup_points` from the API response (which already had the logic, just needed proper integration)
- All 66 real pickup points are now loaded from the database and organized by route

**Changes Made:**
1. **Fleet.tsx**: Already assigns trucks to routes via `assigned_route_id`
2. **Backend Routes API** (`app/routers/routes.py`): Already returns pickup_points in the response
3. **Database**: Seeded with actual Kharadi ward pickup points from GeoJSON coordinates
4. **Truck-Route Assignment**: All 11 trucks now have assigned routes (previously only 3 did)

### 2. **Proper Lane Coordinates for Realistic Movement**
**Problem:** Vehicles were moving in straight lines between pickup points instead of following actual street/lane coordinates.

**Solution Implemented:**
- The `export.geojson` file contains actual Kharadi street network data with lane coordinates
- `useRouteBasedSimulation.ts` already implements the `findRoadPath()` function which:
  - Loads `export.geojson` from the public folder
  - Finds nearest road segments between pickup points
  - Generates realistic curved paths following actual streets/lanes
  - Interpolates truck position along the road path segment-by-segment

**Data Flow:**
```
export.geojson (street network)
    ↓
useRouteBasedSimulation.findRoadPath()
    ↓
Extracts road coordinates between pickup points
    ↓
Interpolates truck position smoothly along lanes
    ↓
Updates truck bearing based on road direction
```

## Current Implementation Details

### Backend Database Structure
```
Route {
  id: "KHR-1",
  name: "Kharadi Route 1",
  pickup_points: [
    {
      id: "KHR-PP01-01",
      latitude: 18.5500,
      longitude: 73.9380,
      name: "Kharadi Pickup Point 1-1",
      type: "residential",
      waste_type: "dry"
    },
    ... (multiple pickup points per route)
  ]
}

Truck {
  id: "TRK001",
  registration_number: "MH-12-AB-1234",
  assigned_route_id: "KHR-1",  // ← Links to route
  latitude: 18.5500,
  longitude: 73.9380,
  current_status: "moving"
}
```

### Frontend Simulation Flow
1. **Fleet.tsx** fetches trucks and routes from API
2. **useRouteBasedSimulation.ts** receives trucks with `routeId`
3. For each truck:
   - Fetches route data including `pickup_points`
   - Calls `findRoadPath()` for each segment between pickup points
   - Loads lane coordinates from `export.geojson`
   - Simulates smooth movement along actual streets
   - Calculates realistic bearing based on road direction

### Journey Replay
1. **TruckJourneyReplayModal.tsx** uses `useRoutes()` hook
2. Finds truck's route and extracts real `pickup_points`
3. Generates path through actual pickup points using `generateRealisticPath()`
4. Uses `useSmoothTruckAnimation` to animate movement with proper bearing

## Files Modified

### Frontend
- ✅ `src/components/TruckJourneyReplayModal.tsx` - Now uses API routes with real pickup points
- ✅ `src/hooks/useRouteBasedSimulation.ts` - Updated interface to handle both DB and mock formats
- ✅ `src/pages/Fleet.tsx` - Uses normalized truck data with proper routeId

### Backend
- ✅ `backend/assign_trucks_to_routes.py` - NEW: Assigns all trucks to routes (11/11 assigned)
- ✅ `backend/app/routers/routes.py` - Already returns pickup_points in API response
- ✅ `backend/seed_kharadi_routes.py` - Creates routes with real pickup points from GeoJSON

## Database Status
```
✅ 5 Routes with real pickup points
✅ 66 Pickup points created from Kharadi GeoJSON
✅ 11 Trucks assigned to routes
✅ Each truck has assigned_route_id set
```

## Testing the Implementation

### To verify pickup points are loaded:
1. Open Fleet page
2. Open browser DevTools → Network tab
3. Look for `/api/routes/` request
4. Response includes `pickup_points` array for each route

### To verify lane-based movement:
1. Select a truck on the Fleet map
2. Observe truck path following actual street curves
3. Check TruckJourneyReplayModal
4. Play replay and see realistic movement along streets

## Next Steps (Optional Enhancements)
- Add street-level detail to pickup points (street name, lane number)
- Optimize road path finding algorithm for faster queries
- Cache road paths to reduce computation
- Add real-time GPS data import for actual tracker paths
