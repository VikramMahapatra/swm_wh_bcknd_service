# Complete API Migration Guide - File-by-File Instructions

This guide provides exact step-by-step instructions for converting each page/component to use API data.

## Pattern Overview

Each file follows this pattern:

### Step 1: Update Imports
```typescript
// OLD
import { mockXxx } from '@/data/masterData';

// NEW
import { useXxx } from '@/hooks/useDataQueries';
import { mockXxx } from '@/data/masterData'; // Keep as fallback
```

### Step 2: Add Hooks
```typescript
// After other hooks, add:
const { data: xxxFromAPI = [], isLoading: isLoadingXxx, error: xxxError } = useXxx();
```

### Step 3: Initialize State from API
```typescript
const [xxx, setXxx] = useState<Type[]>([]);

useEffect(() => {
  if (xxxFromAPI.length > 0) {
    setXxx(xxxFromAPI);
  } else if (xxxError) {
    setXxx(mockXxx);
  }
}, [xxxFromAPI, xxxError]);
```

### Step 4: Use Loading States in UI
```typescript
{isLoadingXxx ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
```

---

## Master Data Pages

### 1. MasterDrivers.tsx ✅ (In Progress)

Already started - needs completion of useEffect logic.

**Currently done:**
- ✅ Import hooks
- ✅ Add hook calls
- ⏳ Complete useEffect setup

**Complete the component like this:**

```typescript
// After form data initialization, add the useEffect blocks
useEffect(() => {
  if (driversFromAPI?.length > 0) {
    setDrivers(driversFromAPI as Driver[]);
  } else if (!isLoadingDrivers && driversError) {
    setDrivers(mockDrivers);
  }
}, [driversFromAPI, isLoadingDrivers, driversError]);

useEffect(() => {
  if (trucksFromAPI?.length > 0) {
    setTrucks(trucksFromAPI);
  } else {
    setTrucks(mockTrucks);
  }
}, [trucksFromAPI]);
```

---

### 2. MasterTrucks.tsx

**Changes needed:**
```typescript
// Import line 11 - change to:
import { useT ucks, useVendors, useDrivers } from '@/hooks/useDataQueries';
import { mockTrucks, mockVendors, mockDrivers, TruckMaster } from '@/data/masterData';

// In component:
const { data: trucksFromAPI = [], isLoading: isLoadingTrucks } = useTrucks();
const { data: vendorsFromAPI = [], isLoading: isLoadingVendors } = useVendors();
const { data: driversFromAPI = [], isLoading: isLoadingDrivers } = useDrivers();

const [trucks, setTrucks] = useState<TruckMaster[]>([]);
const [vendors, setVendors] = useState<any[]>([]);
const [drivers, setDrivers] = useState<any[]>([]);

// Initialize effects
useEffect(() => {
  if (trucksFromAPI?.length > 0) {
    setTrucks(trucksFromAPI as TruckMaster[]);
  } else {
    setTrucks(mockTrucks);
  }
}, [trucksFromAPI]);

useEffect(() => {
  if (vendorsFromAPI?.length > 0) {
    setVendors(vendorsFromAPI);
  } else {
    setVendors(mockVendors);
  }
}, [vendorsFromAPI]);

useEffect(() => {
  if (driversFromAPI?.length > 0) {
    setDrivers(driversFromAPI);
  } else {
    setDrivers(mockDrivers);
  }
}, [driversFromAPI]);

// Update getVendorName function
const getVendorName = (vendorId: string) => 
  vendors.find(v => v.id === vendorId)?.companyName || vendors.find(v => v.id === vendorId)?.name || 'Unknown';

const getDriverName = (driverId?: string) => 
  driverId ? drivers.find(d => d.id === driverId)?.name || 'Unknown' : 'Not Assigned';
```

---

### 3. MasterVendors.tsx

**Changes needed:**
```typescript
// Import line 11 - change to:
import { useVendors } from '@/hooks/useDataQueries';
import { mockVendors, Vendor } from '@/data/masterData';

// In component:
const { data: vendorsFromAPI = [], isLoading: isLoadingVendors } = useVendors();
const [vendors, setVendors] = useState<Vendor[]>([]);

useEffect(() => {
  if (vendorsFromAPI?.length > 0) {
    setVendors(vendorsFromAPI as Vendor[]);
  } else {
    setVendors(mockVendors);
  }
}, [vendorsFromAPI]);
```

---

### 4. MasterZonesWards.tsx

**Changes needed:**
```typescript
// Look for imports of mockZones, mockWards
// Replace with:
import { useZones } from '@/hooks/useDataQueries';
import { mockZones, mockWards } from '@/data/zones'; // Fallback

// In component:
const { data: zonesFromAPI = [], isLoading: isLoadingZones } = useZones();
const [zones, setZones] = useState<any[]>([]);
const [wards, setWards] = useState<any[]>([]);

useEffect(() => {
  if (zonesFromAPI?.length > 0) {
    setZones(zonesFromAPI);
  } else {
    setZones(mockZones);
  }
}, [zonesFromAPI]);

// For wards, you may need to fetch them per zone or combine all wards
// from the API zones data
useEffect(() => {
  const allWards: any[] = [];
  zones.forEach(zone => {
    if (zone.wards) {
      allWards.push(...zone.wards);
    }
  });
  setWards(allWards.length > 0 ? allWards : mockWards);
}, [zones]);
```

---

### 5. MasterRoutesPickups.tsx

**Changes needed:**
```typescript
// Look for imports of mockRoutes, mockPickupPoints, etc.
import { useRoutes, usePickupPoints, useZones } from '@/hooks/useDataQueries';
import { mockRoutes, mockPickupPoints, mockZones, mockWards, mockTrucks } from '@/data/masterData';

// In component:
const { data: routesFromAPI = [], isLoading: isLoadingRoutes } = useRoutes();
const { data: pickupPointsFromAPI = [], isLoading: isLoadingPickupPoints } = usePickupPoints();
const { data: zonesFromAPI = [], isLoading: isLoadingZones } = useZones();

const [routes, setRoutes] = useState(mockRoutes);
const [pickupPoints, setPickupPoints] = useState(mockPickupPoints);
const [zones, setZones] = useState(mockZones);

useEffect(() => {
  if (routesFromAPI?.length > 0) setRoutes(routesFromAPI);
}, [routesFromAPI]);

useEffect(() => {
  if (pickupPointsFromAPI?.length > 0) setPickupPoints(pickupPointsFromAPI);
}, [pickupPointsFromAPI]);

useEffect(() => {
  if (zonesFromAPI?.length > 0) setZones(zonesFromAPI);
}, [zonesFromAPI]);
```

---

## Operational Pages

### 1. ActiveTrucks.tsx

**Changes needed:**
```typescript
// Look for imports around line 40
import { useLiveTrucks, useVendors, useZones } from '@/hooks/useDataQueries';
import { mockVendors, mockWards, mockTrucks } from '@/data/masterData';

// Early in component, add:
const { data: liveTrucksFromAPI = [], isLoading: isLoadingLiveTrucks } = useLiveTrucks();
const { data: vendorsFromAPI = [], isLoading: isLoadingVendors } = useVendors();
const { data: zonesFromAPI = [], isLoading: isLoadingZones } = useZones();

// Initialize state
const [trucks, setTrucks] = useState(mockTrucks);
const [vendors, setVendors] = useState(mockVendors);

useEffect(() => {
  if (liveTrucksFromAPI?.length > 0) {
    setTrucks(liveTrucksFromAPI);
  }
}, [liveTrucksFromAPI]);

useEffect(() => {
  if (vendorsFromAPI?.length > 0) {
    setVendors(vendorsFromAPI);
  } else {
    setVendors(mockVendors);
  }
}, [vendorsFromAPI]);
```

---

### 2. TripsCompleted.tsx

**Already partially updated, but improve:**

```typescript
// Add hooks for missing data sources
import { useLiveTrucks, useZones, useVendors, useRoutes } from '@/hooks/useDataQueries';

// The current implementation already pulls from trucks, so enhance it:
const { data: trucksFromAPI = [] } = useLiveTrucks();
const { data: zonesFromAPI = [] } = useZones();
const { data: vendorsFromAPI = [] } = useVendors();

// Update the maps creation to use API data
useEffect(() => {
  const zoneById = new Map(zonesFromAPI.map((zone) => [zone.id, zone.name]));
  const vendorById = new Map(vendorsFromAPI.map((vendor) => [vendor.id, vendor.name || vendor.companyName]));
  setZoneMap(zoneById);
  setVendorMap(vendorById);
}, [zonesFromAPI, vendorsFromAPI]);
```

---

### 3. Tickets.tsx

**Changes needed:**
```typescript
// Import line 15 - change to:
import { useTickets } from '@/hooks/useDataQueries';
import { mockTickets, Ticket, TicketStatus, TicketPriority, TicketCategory, TicketComment, defaultSLAConfig } from '@/data/masterData';

// In component:
const { data: ticketsFromAPI = [], isLoading: isLoadingTickets } = useTickets();
const [tickets, setTickets] = useState<Ticket[]>([]);

useEffect(() => {
  if (ticketsFromAPI?.length > 0) {
    setTickets(ticketsFromAPI as Ticket[]);
  } else {
    setTickets(mockTickets);
  }
}, [ticketsFromAPI]);
```

---

### 4. Alerts.tsx

**Changes needed:**
```typescript
// Add imports
import { useAlerts } from '@/hooks/useDataQueries';

// In component, find where alerts state is initialized
const { data: alertsFromAPI = [], isLoading: isLoadingAlerts } = useAlerts();
const [alerts, setAlerts] = useState<any[]>([]);

useEffect(() => {
  if (alertsFromAPI?.length > 0) {
    setAlerts(alertsFromAPI);
  } else {
    setAlerts(mockAlerts); // if mockAlerts exists, or empty array
  }
}, [alertsFromAPI]);
```

---

### 5. OperationalStats.tsx (in pages folder, if it exists)

(Check if this is in /pages or /components - the instructions are the same)

```typescript
// Add imports
import { 
  useZones, 
  useVendors, 
  useLiveTrucks, 
  useRoutes, 
  useDrivers 
} from '@/hooks/useDataQueries';

// Add hook calls
const { data: zonesFromAPI = [] } = useZones();
const { data: vendorsFromAPI = [] } = useVendors();
const { data: trucksFromAPI = [] } = useLiveTrucks();
const { data: routesFromAPI = [] } = useRoutes();
const { data: driversFromAPI = [] } = useDrivers();

// Initialize states
const [zones, setZones] = useState(mockZones);
const [vendors, setVendors] = useState(mockVendors);
const [trucks, setTrucks] = useState(mockTrucks);
const [routes, setRoutes] = useState(mockRoutes);
const [drivers, setDrivers] = useState(mockDrivers);

// Add effects
useEffect(() => {
  if (zonesFromAPI?.length > 0) setZones(zonesFromAPI);
}, [zonesFromAPI]);

useEffect(() => {
  if (vendorsFromAPI?.length > 0) setVendors(vendorsFromAPI);
}, [vendorsFromAPI]);

useEffect(() => {
  if (trucksFromAPI?.length > 0) setTrucks(trucksFromAPI);
}, [trucksFromAPI]);

useEffect(() => {
  if (routesFromAPI?.length > 0) setRoutes(routesFromAPI);
}, [routesFromAPI]);

useEffect(() => {
  if (driversFromAPI?.length > 0) setDrivers(driversFromAPI);
}, [driversFromAPI]);
```

---

## Components

### 1. OperationalStats.tsx (in components folder)

Same pattern as above - add hooks and useEffect initializers.

### 2. MapView.tsx

```typescript
import { useLiveTrucks, useZones, useVendors } from '@/hooks/useDataQueries';

// In component:
const { data: liveTrucksFromAPI = [] } = useLiveTrucks();
const { data: zonesFromAPI = [] } = useZones();
const { data: vendorsFromAPI = [] } = useVendors();

const [trucks, setTrucks] = useState(fleetTrucks); // fleetTrucks is from routes/geo data

useEffect(() => {
  if (liveTrucksFromAPI?.length > 0) {
    setTrucks(liveTrucksFromAPI);
  }
}, [liveTrucksFromAPI]);
```

### 3. SpareVehicleManagement.tsx

```typescript
import { useLiveTrucks, useSpareTrucks, useVendors, useZones } from '@/hooks/useDataQueries';

const { data: trucksLiveFromAPI = [] } = useLiveTrucks();
const { data: spareTrucksFromAPI = [] } = useSpareTrucks();
const { data: vendorsFromAPI = [] } = useVendors();
const { data: zonesFromAPI = [] } = useZones();

const [trucksData, setTrucksData] = useState(trucksData || []);
const [vendors, setVendors] = useState(mockVendors);

useEffect(() => {
  if (trucksLiveFromAPI?.length > 0) setTrucksData(trucksLiveFromAPI);
}, [trucksLiveFromAPI]);

useEffect(() => {
  if (vendorsFromAPI?.length > 0) setVendors(vendorsFromAPI);
}, [vendorsFromAPI]);
```

---

## Summary Table

| File | Status | Hook(s) Needed | Notes |
|------|--------|----------------|-------|
| MasterDrivers | ⏳ In Progress | useDrivers, useTrucks | Complete useEffect setup |
| MasterTrucks | ❌ Not Started | useTrucks, useVendors, useDrivers | Update vendor/driver getters |
| MasterVendors | ❌ Not Started | useVendors | Simple 1:1 replacement |
| MasterZonesWards | ❌ Not Started | useZones | May need custom ward loading |
| MasterRoutesPickups | ❌ Not Started | useRoutes, usePickupPoints | Complex relationships |
| ActiveTrucks | ❌ Not Started | useLiveTrucks, useVendors, useZones | Live data prioritized |
| TripsCompleted | ⏳ Partial | Already using useLiveTrucks | Enhance zone/vendor maps |
| Tickets | ❌ Not Started | useTickets | Simple replacement |
| Alerts | ❌ Not Started | useAlerts | Simple replacement |
| OperationalStats (page) | ❌ Not Started | useZones, useVendors, useLiveTrucks, etc. | Multiple dependencies |
| OperationalStats (component) | ❌ Not Started | Same as above | Same logic |
| MapView | ❌ Not Started | useLiveTrucks | Truck position data |
| SpareVehicleManagement | ❌ Not Started | useLiveTrucks, useSpareTrucks | Manage spare vehicles |

---

## Common Patterns to Apply

### Pattern A: Simple Data Replacement
Use this when a component just displays a list of items:
```typescript
const { data: xxxFromAPI = [] } = useXxx();
const [xxx, setXxx] = useState<Type[]>([]);

useEffect(() => {
  setXxx(xxxFromAPI?.length > 0 ? xxxFromAPI : mockXxx);
}, [xxxFromAPI]);
```

### Pattern B: Loading State
Add to render where appropriate:
```tsx
{isLoadingXxx && <Loader2 className="h-4 w-4 animate-spin" />}
{xxxError && <p className="text-red-500">Error loading data</p>}
```

### Pattern C: Lookup Functions
Update these to use API data:
```typescript
const getVendorName = (id: string) => 
  vendors.find(v => v.id === id)?.name ?? 'Unknown';
```

---

## Testing Each File

After updating each file:
1. ✅ No TypeScript errors: `npm run lint`
2. ✅ Page loads: Check browser console for errors
3. ✅ Data displays: Verify zones, vendors, etc. show correct values
4. ✅ Fallback works: If API is down, mock data displays

---

##Next Steps

1. Use this guide to update remaining files
2. Test each page individually
3. Run `npm run build` to catch any issues
4. Verify all pages load and display data correctly
5. Once stable, remove hardcoded mock data imports (keep as fallback for now)

Need help with a specific file? Refer to the exact copy-paste code examples above!
