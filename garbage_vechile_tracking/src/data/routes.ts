// Routes, Pickup Points, GTPs, and Dumping Sites Data

import { RouteType } from './trucks';

export interface GTPLocation {
  id: string;
  name: string;
  position: { lat: number; lng: number };
  wardId: string;
  zoneId: string;
  ward: string;
  capacity: string;
  currentFill: number;
}

export interface FinalDumpingSite {
  id: string;
  name: string;
  position: { lat: number; lng: number };
  capacity: string;
}

export interface RoutePoint {
  id: string;
  position: { lat: number; lng: number };
  name: string;
  type: 'pickup' | 'gtp' | 'dumping';
  order: number;
  scheduledTime?: string;
}

export interface Route {
  id: string;
  name: string;
  code: string;
  type: RouteType;
  wardId: string;
  zoneId: string;
  assignedTruckId?: string;
  assignedTruck?: string;
  totalPickupPoints: number;
  estimatedDistance: number;
  distance: string;
  estimatedTime: number;
  status: 'active' | 'inactive';
  points: RoutePoint[];
  usesSpare?: boolean;
  originalTruckId?: string;
  spareActivatedAt?: string;
}

export interface PickupPoint {
  id: string;
  pointCode: string;
  name: string;
  address: string;
  latitude: number;
  longitude: number;
  routeId: string;
  wardId: string;
  ward: string;
  wasteType: 'dry' | 'wet' | 'mixed' | 'hazardous';
  type: 'residential' | 'commercial' | 'hospital' | 'market';
  expectedPickupTime: string;
  schedule: string;
  geofenceRadius: number;
  status: 'active' | 'inactive';
  assignedRoute?: string;
  position: { lat: number; lng: number };
  lastCollection?: string;
}

// GTP Locations (5 GTPs across zones)
export const gtpLocations: GTPLocation[] = [
  { id: 'GTP-001', name: 'Kharadi GTP', position: { lat: 18.5580, lng: 73.9420 }, wardId: 'WD006', zoneId: 'ZN003', ward: 'Kharadi', capacity: '50 tons', currentFill: 65 },
  { id: 'GTP-002', name: 'Viman Nagar GTP', position: { lat: 18.5620, lng: 73.9150 }, wardId: 'WD007', zoneId: 'ZN003', ward: 'Viman Nagar', capacity: '60 tons', currentFill: 45 },
  { id: 'GTP-003', name: 'Aundh GTP', position: { lat: 18.5850, lng: 73.8100 }, wardId: 'WD001', zoneId: 'ZN001', ward: 'Aundh', capacity: '55 tons', currentFill: 70 },
  { id: 'GTP-004', name: 'Hadapsar GTP', position: { lat: 18.5000, lng: 73.9300 }, wardId: 'WD004', zoneId: 'ZN002', ward: 'Hadapsar', capacity: '45 tons', currentFill: 55 },
  { id: 'GTP-005', name: 'Baner GTP', position: { lat: 18.5685, lng: 73.7925 }, wardId: 'WD002', zoneId: 'ZN001', ward: 'Baner', capacity: '48 tons', currentFill: 52 }
];

// Final Dumping Sites (2 sites)
export const finalDumpingSites: FinalDumpingSite[] = [
  { id: 'FDS-001', name: 'Hadapsar Waste Processing Plant', position: { lat: 18.5050, lng: 73.9400 }, capacity: '500 tons/day' },
  { id: 'FDS-002', name: 'Uruli Devachi Landfill', position: { lat: 18.4200, lng: 73.9800 }, capacity: '1000 tons/day' }
];

// 9 Routes (5 Primary + 4 Secondary)
export const routes: Route[] = [
  // East Zone - Kharadi & Viman Nagar (4 routes)
  {
    id: 'RT001', name: 'Kharadi Primary Route 1', code: 'KHR-P1', type: 'primary', wardId: 'WD006', zoneId: 'ZN003',
    assignedTruckId: 'TRK001', assignedTruck: 'TRK001', totalPickupPoints: 8, estimatedDistance: 15, distance: '15 km', estimatedTime: 150, status: 'active',
    points: [
      { id: 'RP-001', position: { lat: 18.5500, lng: 73.9380 }, name: 'EON IT Park', type: 'pickup', order: 1, scheduledTime: '06:00' },
      { id: 'RP-002', position: { lat: 18.5520, lng: 73.9400 }, name: 'World Trade Center', type: 'pickup', order: 2, scheduledTime: '06:30' },
      { id: 'RP-003', position: { lat: 18.5535, lng: 73.9415 }, name: 'Kharadi Society A', type: 'pickup', order: 3, scheduledTime: '07:00' },
      { id: 'RP-004', position: { lat: 18.5550, lng: 73.9430 }, name: 'Kharadi Market', type: 'pickup', order: 4, scheduledTime: '07:30' },
      { id: 'RP-005', position: { lat: 18.5580, lng: 73.9420 }, name: 'Kharadi GTP', type: 'gtp', order: 5, scheduledTime: '08:30' }
    ]
  },
  {
    id: 'RT002', name: 'Kharadi Secondary Route 1', code: 'KHR-S1', type: 'secondary', wardId: 'WD006', zoneId: 'ZN003',
    assignedTruckId: 'TRK002', assignedTruck: 'TRK002', totalPickupPoints: 2, estimatedDistance: 25, distance: '25 km', estimatedTime: 90, status: 'active',
    points: [
      { id: 'RP-006', position: { lat: 18.5580, lng: 73.9420 }, name: 'Kharadi GTP', type: 'gtp', order: 1, scheduledTime: '09:00' },
      { id: 'RP-007', position: { lat: 18.5050, lng: 73.9400 }, name: 'Hadapsar Waste Processing Plant', type: 'dumping', order: 2, scheduledTime: '10:30' }
    ]
  },
  {
    id: 'RT003', name: 'Viman Nagar Primary Route 1', code: 'VMN-P1', type: 'primary', wardId: 'WD007', zoneId: 'ZN003',
    assignedTruckId: 'TRK003', assignedTruck: 'TRK003', totalPickupPoints: 6, estimatedDistance: 12, distance: '12 km', estimatedTime: 135, status: 'active',
    points: [
      { id: 'RP-008', position: { lat: 18.5680, lng: 73.9200 }, name: 'Phoenix Mall', type: 'pickup', order: 1, scheduledTime: '06:30' },
      { id: 'RP-009', position: { lat: 18.5665, lng: 73.9180 }, name: 'Viman Nagar Society B', type: 'pickup', order: 2, scheduledTime: '07:00' },
      { id: 'RP-010', position: { lat: 18.5640, lng: 73.9160 }, name: 'Airport Road Market', type: 'pickup', order: 3, scheduledTime: '07:45' },
      { id: 'RP-011', position: { lat: 18.5620, lng: 73.9150 }, name: 'Viman Nagar GTP', type: 'gtp', order: 4, scheduledTime: '08:30' }
    ]
  },
  {
    id: 'RT004', name: 'Viman Nagar Secondary Route 1', code: 'VMN-S1', type: 'secondary', wardId: 'WD007', zoneId: 'ZN003',
    assignedTruckId: 'TRK004', assignedTruck: 'TRK004', totalPickupPoints: 2, estimatedDistance: 28, distance: '28 km', estimatedTime: 100, status: 'active',
    points: [
      { id: 'RP-012', position: { lat: 18.5620, lng: 73.9150 }, name: 'Viman Nagar GTP', type: 'gtp', order: 1, scheduledTime: '09:00' },
      { id: 'RP-013', position: { lat: 18.5050, lng: 73.9400 }, name: 'Hadapsar Waste Processing Plant', type: 'dumping', order: 2, scheduledTime: '10:40' }
    ]
  },
  // North Zone - Aundh & Baner (3 routes)
  {
    id: 'RT005', name: 'Aundh Primary Route 1', code: 'AND-P1', type: 'primary', wardId: 'WD001', zoneId: 'ZN001',
    assignedTruckId: 'TRK005', assignedTruck: 'TRK005', totalPickupPoints: 7, estimatedDistance: 18, distance: '18 km', estimatedTime: 165, status: 'active',
    points: [
      { id: 'RP-014', position: { lat: 18.5920, lng: 73.8100 }, name: 'Aundh IT Hub', type: 'pickup', order: 1, scheduledTime: '05:30' },
      { id: 'RP-015', position: { lat: 18.5900, lng: 73.8120 }, name: 'Aundh Society C', type: 'pickup', order: 2, scheduledTime: '06:00' },
      { id: 'RP-016', position: { lat: 18.5880, lng: 73.8080 }, name: 'Westend Mall', type: 'pickup', order: 3, scheduledTime: '06:45' },
      { id: 'RP-017', position: { lat: 18.5850, lng: 73.8100 }, name: 'Aundh GTP', type: 'gtp', order: 4, scheduledTime: '08:00' }
    ]
  },
  {
    id: 'RT006', name: 'Baner Primary Route 1', code: 'BNR-P1', type: 'primary', wardId: 'WD002', zoneId: 'ZN001',
    assignedTruckId: 'TRK006', assignedTruck: 'TRK006', totalPickupPoints: 6, estimatedDistance: 14, distance: '14 km', estimatedTime: 140, status: 'active',
    points: [
      { id: 'RP-018', position: { lat: 18.5700, lng: 73.7900 }, name: 'Baner Highstreet', type: 'pickup', order: 1, scheduledTime: '06:00' },
      { id: 'RP-019', position: { lat: 18.5680, lng: 73.7920 }, name: 'Baner Society D', type: 'pickup', order: 2, scheduledTime: '06:30' },
      { id: 'RP-020', position: { lat: 18.5650, lng: 73.7950 }, name: 'Balewadi Stadium', type: 'pickup', order: 3, scheduledTime: '07:15' },
      { id: 'RP-021', position: { lat: 18.5685, lng: 73.7925 }, name: 'Baner GTP', type: 'gtp', order: 4, scheduledTime: '08:15' }
    ]
  },
  {
    id: 'RT007', name: 'Aundh Secondary Route 1', code: 'AND-S1', type: 'secondary', wardId: 'WD001', zoneId: 'ZN001',
    assignedTruckId: 'TRK007', assignedTruck: 'TRK007', totalPickupPoints: 2, estimatedDistance: 35, distance: '35 km', estimatedTime: 110, status: 'active',
    points: [
      { id: 'RP-022', position: { lat: 18.5850, lng: 73.8100 }, name: 'Aundh GTP', type: 'gtp', order: 1, scheduledTime: '09:00' },
      { id: 'RP-023', position: { lat: 18.4200, lng: 73.9800 }, name: 'Uruli Devachi Landfill', type: 'dumping', order: 2, scheduledTime: '10:50' }
    ]
  },
  // South Zone - Hadapsar (2 routes)
  {
    id: 'RT008', name: 'Hadapsar Primary Route 1', code: 'HDP-P1', type: 'primary', wardId: 'WD004', zoneId: 'ZN002',
    assignedTruckId: 'TRK008', assignedTruck: 'TRK008', totalPickupPoints: 8, estimatedDistance: 20, distance: '20 km', estimatedTime: 180, status: 'active',
    points: [
      { id: 'RP-024', position: { lat: 18.5100, lng: 73.9400 }, name: 'Magarpatta City', type: 'pickup', order: 1, scheduledTime: '05:30' },
      { id: 'RP-025', position: { lat: 18.5080, lng: 73.9380 }, name: 'Amanora Mall', type: 'pickup', order: 2, scheduledTime: '06:15' },
      { id: 'RP-026', position: { lat: 18.5050, lng: 73.9350 }, name: 'Hadapsar Industrial Estate', type: 'pickup', order: 3, scheduledTime: '07:00' },
      { id: 'RP-027', position: { lat: 18.5000, lng: 73.9300 }, name: 'Hadapsar GTP', type: 'gtp', order: 4, scheduledTime: '08:30' }
    ]
  },
  {
    id: 'RT009', name: 'Hadapsar Secondary Route 1', code: 'HDP-S1', type: 'secondary', wardId: 'WD004', zoneId: 'ZN002',
    assignedTruckId: 'TRK009', assignedTruck: 'TRK009', totalPickupPoints: 2, estimatedDistance: 15, distance: '15 km', estimatedTime: 60, status: 'active',
    points: [
      { id: 'RP-028', position: { lat: 18.5000, lng: 73.9300 }, name: 'Hadapsar GTP', type: 'gtp', order: 1, scheduledTime: '09:00' },
      { id: 'RP-029', position: { lat: 18.5050, lng: 73.9400 }, name: 'Hadapsar Waste Processing Plant', type: 'dumping', order: 2, scheduledTime: '10:00' }
    ]
  }
];

// Pickup Points with all required fields
export const pickupPoints: PickupPoint[] = [
  // Kharadi (WD006) - 4 points
  { id: 'PP001', pointCode: 'PP-KHR-001', name: 'EON IT Park', address: 'EON Free Zone, Kharadi', latitude: 18.5500, longitude: 73.9380, routeId: 'RT001', wardId: 'WD006', ward: 'Kharadi', wasteType: 'dry', type: 'commercial', expectedPickupTime: '06:00', schedule: 'Daily 6AM', geofenceRadius: 30, status: 'active', assignedRoute: 'RT001', position: { lat: 18.5500, lng: 73.9380 }, lastCollection: 'Today 6:05 AM' },
  { id: 'PP002', pointCode: 'PP-KHR-002', name: 'World Trade Center', address: 'WTC, Kharadi', latitude: 18.5520, longitude: 73.9400, routeId: 'RT001', wardId: 'WD006', ward: 'Kharadi', wasteType: 'mixed', type: 'commercial', expectedPickupTime: '06:30', schedule: 'Daily 6:30AM', geofenceRadius: 25, status: 'active', assignedRoute: 'RT001', position: { lat: 18.5520, lng: 73.9400 }, lastCollection: 'Today 6:32 AM' },
  { id: 'PP003', pointCode: 'PP-KHR-003', name: 'Kharadi Society A', address: 'Kharadi Bypass Road', latitude: 18.5535, longitude: 73.9415, routeId: 'RT001', wardId: 'WD006', ward: 'Kharadi', wasteType: 'wet', type: 'residential', expectedPickupTime: '07:00', schedule: 'Daily 7AM', geofenceRadius: 20, status: 'active', assignedRoute: 'RT001', position: { lat: 18.5535, lng: 73.9415 }, lastCollection: 'Today 7:02 AM' },
  { id: 'PP004', pointCode: 'PP-KHR-004', name: 'Kharadi Market', address: 'Kharadi Main Market', latitude: 18.5550, longitude: 73.9430, routeId: 'RT001', wardId: 'WD006', ward: 'Kharadi', wasteType: 'mixed', type: 'market', expectedPickupTime: '07:30', schedule: 'Twice Daily', geofenceRadius: 35, status: 'active', assignedRoute: 'RT001', position: { lat: 18.5550, lng: 73.9430 }, lastCollection: 'Today 7:35 AM' },
  
  // Viman Nagar (WD007) - 3 points
  { id: 'PP005', pointCode: 'PP-VMN-001', name: 'Phoenix Mall', address: 'Phoenix Marketcity, Viman Nagar', latitude: 18.5680, longitude: 73.9200, routeId: 'RT003', wardId: 'WD007', ward: 'Viman Nagar', wasteType: 'mixed', type: 'commercial', expectedPickupTime: '06:30', schedule: 'Daily 6:30AM', geofenceRadius: 40, status: 'active', assignedRoute: 'RT003', position: { lat: 18.5680, lng: 73.9200 }, lastCollection: 'Today 6:35 AM' },
  { id: 'PP006', pointCode: 'PP-VMN-002', name: 'Viman Nagar Society B', address: 'Datta Mandir Road, Viman Nagar', latitude: 18.5665, longitude: 73.9180, routeId: 'RT003', wardId: 'WD007', ward: 'Viman Nagar', wasteType: 'wet', type: 'residential', expectedPickupTime: '07:00', schedule: 'Daily 7AM', geofenceRadius: 20, status: 'active', assignedRoute: 'RT003', position: { lat: 18.5665, lng: 73.9180 }, lastCollection: 'Today 7:05 AM' },
  { id: 'PP007', pointCode: 'PP-VMN-003', name: 'Airport Road Market', address: 'Airport Road, Viman Nagar', latitude: 18.5640, longitude: 73.9160, routeId: 'RT003', wardId: 'WD007', ward: 'Viman Nagar', wasteType: 'mixed', type: 'market', expectedPickupTime: '07:45', schedule: 'Twice Daily', geofenceRadius: 30, status: 'active', assignedRoute: 'RT003', position: { lat: 18.5640, lng: 73.9160 }, lastCollection: 'Today 7:48 AM' },
  
  // Aundh (WD001) - 3 points
  { id: 'PP008', pointCode: 'PP-AND-001', name: 'Aundh IT Hub', address: 'Aundh IT Park', latitude: 18.5920, longitude: 73.8100, routeId: 'RT005', wardId: 'WD001', ward: 'Aundh', wasteType: 'dry', type: 'commercial', expectedPickupTime: '05:30', schedule: 'Daily 5:30AM', geofenceRadius: 35, status: 'active', assignedRoute: 'RT005', position: { lat: 18.5920, lng: 73.8100 }, lastCollection: 'Today 5:35 AM' },
  { id: 'PP009', pointCode: 'PP-AND-002', name: 'Aundh Society C', address: 'DP Road, Aundh', latitude: 18.5900, longitude: 73.8120, routeId: 'RT005', wardId: 'WD001', ward: 'Aundh', wasteType: 'wet', type: 'residential', expectedPickupTime: '06:00', schedule: 'Daily 6AM', geofenceRadius: 20, status: 'active', assignedRoute: 'RT005', position: { lat: 18.5900, lng: 73.8120 }, lastCollection: 'Today 6:02 AM' },
  { id: 'PP010', pointCode: 'PP-AND-003', name: 'Westend Mall', address: 'Westend Mall, Aundh', latitude: 18.5880, longitude: 73.8080, routeId: 'RT005', wardId: 'WD001', ward: 'Aundh', wasteType: 'mixed', type: 'commercial', expectedPickupTime: '06:45', schedule: 'Daily 6:45AM', geofenceRadius: 40, status: 'active', assignedRoute: 'RT005', position: { lat: 18.5880, lng: 73.8080 }, lastCollection: 'Today 6:48 AM' },
  
  // Baner (WD002) - 3 points
  { id: 'PP011', pointCode: 'PP-BNR-001', name: 'Baner Highstreet', address: 'Baner Highstreet Mall', latitude: 18.5700, longitude: 73.7900, routeId: 'RT006', wardId: 'WD002', ward: 'Baner', wasteType: 'mixed', type: 'commercial', expectedPickupTime: '06:00', schedule: 'Daily 6AM', geofenceRadius: 35, status: 'active', assignedRoute: 'RT006', position: { lat: 18.5700, lng: 73.7900 }, lastCollection: 'Today 6:05 AM' },
  { id: 'PP012', pointCode: 'PP-BNR-002', name: 'Baner Society D', address: 'Baner Road', latitude: 18.5680, longitude: 73.7920, routeId: 'RT006', wardId: 'WD002', ward: 'Baner', wasteType: 'wet', type: 'residential', expectedPickupTime: '06:30', schedule: 'Daily 6:30AM', geofenceRadius: 20, status: 'active', assignedRoute: 'RT006', position: { lat: 18.5680, lng: 73.7920 }, lastCollection: 'Today 6:32 AM' },
  { id: 'PP013', pointCode: 'PP-BNR-003', name: 'Balewadi Stadium', address: 'Balewadi Sports Complex', latitude: 18.5650, longitude: 73.7950, routeId: 'RT006', wardId: 'WD002', ward: 'Baner', wasteType: 'dry', type: 'commercial', expectedPickupTime: '07:15', schedule: 'Daily 7:15AM', geofenceRadius: 50, status: 'active', assignedRoute: 'RT006', position: { lat: 18.5650, lng: 73.7950 }, lastCollection: 'Today 7:18 AM' },
  
  // Hadapsar (WD004) - 3 points
  { id: 'PP014', pointCode: 'PP-HDP-001', name: 'Magarpatta City', address: 'Magarpatta City, Hadapsar', latitude: 18.5100, longitude: 73.9400, routeId: 'RT008', wardId: 'WD004', ward: 'Hadapsar', wasteType: 'mixed', type: 'commercial', expectedPickupTime: '05:30', schedule: 'Daily 5:30AM', geofenceRadius: 45, status: 'active', assignedRoute: 'RT008', position: { lat: 18.5100, lng: 73.9400 }, lastCollection: 'Today 5:35 AM' },
  { id: 'PP015', pointCode: 'PP-HDP-002', name: 'Amanora Mall', address: 'Amanora Park Town, Hadapsar', latitude: 18.5080, longitude: 73.9380, routeId: 'RT008', wardId: 'WD004', ward: 'Hadapsar', wasteType: 'mixed', type: 'commercial', expectedPickupTime: '06:15', schedule: 'Daily 6:15AM', geofenceRadius: 40, status: 'active', assignedRoute: 'RT008', position: { lat: 18.5080, lng: 73.9380 }, lastCollection: 'Today 6:18 AM' },
  { id: 'PP016', pointCode: 'PP-HDP-003', name: 'Hadapsar Industrial Estate', address: 'MIDC Hadapsar', latitude: 18.5050, longitude: 73.9350, routeId: 'RT008', wardId: 'WD004', ward: 'Hadapsar', wasteType: 'hazardous', type: 'commercial', expectedPickupTime: '07:00', schedule: 'Daily 7AM', geofenceRadius: 50, status: 'active', assignedRoute: 'RT008', position: { lat: 18.5050, lng: 73.9350 }, lastCollection: 'Today 7:05 AM' }
];

// Helper functions
export const getRoutesByZone = (zoneId: string): Route[] => routes.filter(r => r.zoneId === zoneId);
export const getRoutesByWard = (wardId: string): Route[] => routes.filter(r => r.wardId === wardId);
export const getRouteById = (routeId: string): Route | undefined => routes.find(r => r.id === routeId);
export const getPickupPointsByRoute = (routeId: string): PickupPoint[] => pickupPoints.filter(p => p.routeId === routeId);
export const getPickupPointsByWard = (wardId: string): PickupPoint[] => pickupPoints.filter(p => p.wardId === wardId);
export const getGTPByZone = (zoneId: string): GTPLocation[] => gtpLocations.filter(g => g.zoneId === zoneId);

// Map constants
// export const GOOGLE_MAPS_API_KEY = "AIzaSyBm6KoD4T-fdLkIHvxwqsQq3EPjz14V2Sw";
export const GOOGLE_MAPS_API_KEY = "AIzaSyBKtWFlctPd62aMtTjfc4wNl31xUA6NTBQ";
export const KHARADI_CENTER = { lat: 18.5540, lng: 73.9425 };
