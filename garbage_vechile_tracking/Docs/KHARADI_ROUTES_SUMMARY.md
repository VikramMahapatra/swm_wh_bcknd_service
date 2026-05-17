# Kharadi Ward Routes - Data Seeding Summary

## Overview
Successfully created 4 routes for Kharadi Ward (WD006, Zone ZN003) with real geographic coordinates extracted from OpenStreetMap GeoJSON data.

## Routes Created

### Route 1: Kharadi Route 1
- **ID**: KHR-1
- **Code**: KHR-P1
- **Type**: Primary
- **Pickup Points**: 15
- **Estimated Distance**: 15.5 km
- **Estimated Time**: 90 minutes
- **Status**: Active

### Route 2: Kharadi Route 2
- **ID**: KHR-2
- **Code**: KHR-P2
- **Type**: Primary
- **Pickup Points**: 15
- **Estimated Distance**: 17.5 km
- **Estimated Time**: 105 minutes
- **Status**: Active

### Route 3: Kharadi Route 3
- **ID**: KHR-3
- **Code**: KHR-P3
- **Type**: Primary
- **Pickup Points**: 15
- **Estimated Distance**: 19.5 km
- **Estimated Time**: 120 minutes
- **Status**: Active

### Route 4: Kharadi Route 4
- **ID**: KHR-4
- **Code**: KHR-P4
- **Type**: Primary
- **Pickup Points**: 15
- **Estimated Distance**: 21.5 km
- **Estimated Time**: 135 minutes
- **Status**: Active

## Total Data

- **Total Routes**: 4
- **Total Pickup Points**: 60
- **Geographic Coverage**: Kharadi Ward, Pune (Coordinates range: Lat 18.547 to 18.562, Lng 73.933 to 73.958)

## Pickup Points Details

Each pickup point includes:
- **Unique ID**: Format `KHR-PP{route}-{number}`
- **Name**: Descriptive name (e.g., "Kharadi Pickup Point 1-1")
- **Address**: Kharadi Ward location reference
- **Coordinates**: Real lat/lng from OpenStreetMap
- **Waste Types**: Dry, Wet, or Mixed (rotated)
- **Location Type**: Residential or Commercial (rotated)
- **Expected Pickup Time**: Scheduled between 7:00 AM and 9:00 AM
- **Schedule**: Daily
- **Geofence Radius**: 30 meters
- **Status**: Active
- **Last Collection**: 2026-02-10 08:30:00

## Usage

### View Routes in Frontend
1. Navigate to Routes page (`/routes`)
2. Select "Kharadi Ward" from zone/ward filters
3. All 4 Kharadi routes will be displayed
4. Click on any route to see its 15 pickup points on the map

### API Endpoints Available

- **Get all Kharadi routes**: `GET /api/routes?ward_id=WD006`
- **Get route pickup points**: `GET /api/routes/{route_id}/pickup-points`
  - Example: `GET /api/routes/KHR-1/pickup-points`

### Fleet Page with Map
- Navigate to Fleet page (`/fleet`) to see live truck tracking
- Routes can be assigned to trucks for optimized garbage collection

## Data Source
- **Source**: OpenStreetMap GeoJSON export for Kharadi area
- **Extracted Coordinates**: 7,807 points sampled to 60 evenly distributed locations
- **Accuracy**: High (based on actual street networks and landmarks)

## Next Steps

1. **Assign Trucks**: Go to Master > Trucks to assign trucks to these routes
2. **Monitor Collections**: Use Routes page to track pickup progress
3. **View on Map**: Use Fleet page to see real-time truck locations and routes
4. **Analytics**: Check Routes statistics to monitor efficiency
