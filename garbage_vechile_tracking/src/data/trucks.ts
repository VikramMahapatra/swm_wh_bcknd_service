// Truck Master Data and Live Fleet Data

export type TruckType = 'mini-truck' | 'compactor' | 'dumper' | 'open-truck';
export type RouteType = 'primary' | 'secondary';
export type TruckStatus = 'moving' | 'idle' | 'dumping' | 'offline' | 'breakdown';
export type TruckMasterStatus = 'active' | 'maintenance' | 'inactive';
export type DeviceStatus = 'online' | 'offline' | 'warning';

export interface GPSDevice {
  imei: string;
  status: DeviceStatus;
  lastPing: string;
  signalStrength: number;
  batteryLevel: number;
}

export interface TruckMaster {
  id: string;
  registrationNumber: string;
  type: TruckType;
  capacity: number;
  capacityUnit: 'tons' | 'cubic-meters';
  routeType: RouteType;
  vendorId: string;
  driverId?: string;
  imeiNumber: string;
  fuelType: 'diesel' | 'cng' | 'electric';
  manufacturingYear: number;
  insuranceExpiry: string;
  fitnessExpiry: string;
  status: TruckMasterStatus;
  lastServiceDate: string;
  isSpare?: boolean;
  zoneId: string;
  wardId: string;
  assignedRouteId?: string;
}

export interface TruckLive {
  id: string;
  truckNumber: string;
  truckType: RouteType;
  vehicleType: TruckType;
  position: { lat: number; lng: number };
  status: TruckStatus;
  driver: string;
  driverId: string;
  route: string;
  routeId: string;
  speed: number;
  assignedGTP?: string;
  assignedDumpingSite?: string;
  tripsCompleted: number;
  tripsAllowed: number;
  gpsDevice: GPSDevice;
  vehicleCapacity: string;
  lastUpdate: string;
  vendorId: string;
  zoneId: string;
  wardId: string;
  isSpare?: boolean;
  replacingTruckId?: string;
  replacedBySpareId?: string;
  breakdownTime?: string;
  breakdownReason?: string;
}

// Master Truck Data - 9 regular + 2 spare = 11 trucks
export const trucksMaster: TruckMaster[] = [
  // Vendor 1 (Mahesh Enterprises) - 4 trucks + 1 spare
  {
    id: 'TRK001',
    registrationNumber: 'MH-12-AB-1234',
    type: 'compactor',
    capacity: 8,
    capacityUnit: 'tons',
    routeType: 'primary',
    vendorId: 'VND001',
    driverId: 'DRV001',
    imeiNumber: '356938035643809',
    fuelType: 'diesel',
    manufacturingYear: 2021,
    insuranceExpiry: '2025-03-15',
    fitnessExpiry: '2025-06-20',
    status: 'active',
    lastServiceDate: '2024-01-10',
    zoneId: 'ZN003',
    wardId: 'WD006',
    assignedRouteId: 'RT001'
  },
  {
    id: 'TRK002',
    registrationNumber: 'MH-12-CD-5678',
    type: 'mini-truck',
    capacity: 3,
    capacityUnit: 'tons',
    routeType: 'secondary',
    vendorId: 'VND001',
    driverId: 'DRV002',
    imeiNumber: '356938035643810',
    fuelType: 'cng',
    manufacturingYear: 2022,
    insuranceExpiry: '2025-05-20',
    fitnessExpiry: '2025-08-15',
    status: 'active',
    lastServiceDate: '2024-02-05',
    zoneId: 'ZN003',
    wardId: 'WD006',
    assignedRouteId: 'RT002'
  },
  {
    id: 'TRK003',
    registrationNumber: 'MH-12-EF-9012',
    type: 'compactor',
    capacity: 8,
    capacityUnit: 'tons',
    routeType: 'primary',
    vendorId: 'VND001',
    driverId: 'DRV003',
    imeiNumber: '356938035643811',
    fuelType: 'diesel',
    manufacturingYear: 2020,
    insuranceExpiry: '2024-11-10',
    fitnessExpiry: '2024-12-05',
    status: 'active',
    lastServiceDate: '2024-03-01',
    zoneId: 'ZN003',
    wardId: 'WD007',
    assignedRouteId: 'RT003'
  },
  {
    id: 'TRK004',
    registrationNumber: 'MH-12-GH-3456',
    type: 'dumper',
    capacity: 12,
    capacityUnit: 'tons',
    routeType: 'secondary',
    vendorId: 'VND001',
    driverId: 'DRV004',
    imeiNumber: '356938035643812',
    fuelType: 'diesel',
    manufacturingYear: 2019,
    insuranceExpiry: '2024-08-25',
    fitnessExpiry: '2024-10-30',
    status: 'maintenance',
    lastServiceDate: '2024-01-25',
    zoneId: 'ZN003',
    wardId: 'WD007',
    assignedRouteId: 'RT004'
  },
  // Vendor 2 (Green Transport) - 3 trucks + 1 spare
  {
    id: 'TRK005',
    registrationNumber: 'MH-12-IJ-7890',
    type: 'compactor',
    capacity: 10,
    capacityUnit: 'tons',
    routeType: 'primary',
    vendorId: 'VND002',
    driverId: 'DRV005',
    imeiNumber: '356938035643813',
    fuelType: 'electric',
    manufacturingYear: 2023,
    insuranceExpiry: '2026-01-15',
    fitnessExpiry: '2026-04-20',
    status: 'active',
    lastServiceDate: '2024-02-20',
    zoneId: 'ZN001',
    wardId: 'WD001',
    assignedRouteId: 'RT005'
  },
  {
    id: 'TRK006',
    registrationNumber: 'MH-12-KL-1122',
    type: 'open-truck',
    capacity: 5,
    capacityUnit: 'tons',
    routeType: 'primary',
    vendorId: 'VND002',
    driverId: 'DRV006',
    imeiNumber: '356938035643814',
    fuelType: 'diesel',
    manufacturingYear: 2021,
    insuranceExpiry: '2025-07-10',
    fitnessExpiry: '2025-09-15',
    status: 'active',
    lastServiceDate: '2024-01-15',
    zoneId: 'ZN001',
    wardId: 'WD002',
    assignedRouteId: 'RT006'
  },
  {
    id: 'TRK007',
    registrationNumber: 'MH-12-MN-3344',
    type: 'mini-truck',
    capacity: 4,
    capacityUnit: 'tons',
    routeType: 'secondary',
    vendorId: 'VND002',
    driverId: 'DRV007',
    imeiNumber: '356938035643815',
    fuelType: 'cng',
    manufacturingYear: 2022,
    insuranceExpiry: '2025-10-20',
    fitnessExpiry: '2025-12-25',
    status: 'active',
    lastServiceDate: '2024-02-28',
    zoneId: 'ZN001',
    wardId: 'WD001',
    assignedRouteId: 'RT007'
  },
  // Vendor 3 (City Waste Solutions) - 2 trucks
  {
    id: 'TRK008',
    registrationNumber: 'MH-12-OP-5566',
    type: 'compactor',
    capacity: 8,
    capacityUnit: 'tons',
    routeType: 'primary',
    vendorId: 'VND003',
    driverId: 'DRV008',
    imeiNumber: '356938035643816',
    fuelType: 'diesel',
    manufacturingYear: 2020,
    insuranceExpiry: '2025-04-15',
    fitnessExpiry: '2025-06-20',
    status: 'active',
    lastServiceDate: '2024-01-20',
    zoneId: 'ZN002',
    wardId: 'WD004',
    assignedRouteId: 'RT008'
  },
  {
    id: 'TRK009',
    registrationNumber: 'MH-12-QR-7788',
    type: 'dumper',
    capacity: 15,
    capacityUnit: 'tons',
    routeType: 'secondary',
    vendorId: 'VND003',
    driverId: 'DRV009',
    imeiNumber: '356938035643817',
    fuelType: 'diesel',
    manufacturingYear: 2021,
    insuranceExpiry: '2025-08-30',
    fitnessExpiry: '2025-11-05',
    status: 'active',
    lastServiceDate: '2024-03-05',
    zoneId: 'ZN002',
    wardId: 'WD004',
    assignedRouteId: 'RT009'
  },
  // Spare Trucks
  {
    id: 'TRK-SPR-001',
    registrationNumber: 'MH-12-SP-1001',
    type: 'compactor',
    capacity: 8,
    capacityUnit: 'tons',
    routeType: 'primary',
    vendorId: 'VND001',
    driverId: 'DRV-SPR-001',
    imeiNumber: '356938035643818',
    fuelType: 'diesel',
    manufacturingYear: 2022,
    insuranceExpiry: '2025-12-15',
    fitnessExpiry: '2026-02-20',
    status: 'active',
    lastServiceDate: '2024-02-15',
    isSpare: true,
    zoneId: 'ZN003',
    wardId: 'WD006'
  },
  {
    id: 'TRK-SPR-002',
    registrationNumber: 'MH-12-SP-2001',
    type: 'dumper',
    capacity: 12,
    capacityUnit: 'tons',
    routeType: 'secondary',
    vendorId: 'VND002',
    driverId: 'DRV-SPR-002',
    imeiNumber: '356938035643819',
    fuelType: 'diesel',
    manufacturingYear: 2022,
    insuranceExpiry: '2025-11-10',
    fitnessExpiry: '2026-01-15',
    status: 'active',
    lastServiceDate: '2024-02-20',
    isSpare: true,
    zoneId: 'ZN001',
    wardId: 'WD001'
  }
];

// Live Fleet Data - Real-time positions and status
export const trucksLive: TruckLive[] = [
  {
    id: 'TRK001',
    truckNumber: 'MH-12-AB-1234',
    truckType: 'primary',
    vehicleType: 'compactor',
    position: { lat: 18.5520, lng: 73.9400 },
    status: 'moving',
    driver: 'Rajesh Kumar',
    driverId: 'DRV001',
    route: 'Kharadi Primary Route 1',
    routeId: 'RT001',
    speed: 25,
    assignedGTP: 'GTP-001',
    tripsCompleted: 3,
    tripsAllowed: 5,
    vehicleCapacity: '8 tons',
    lastUpdate: '2 mins ago',
    vendorId: 'VND001',
    zoneId: 'ZN003',
    wardId: 'WD006',
    gpsDevice: {
      imei: '356938035643809',
      status: 'online',
      lastPing: '2024-01-15 10:30:00',
      signalStrength: 85,
      batteryLevel: 92
    }
  },
  {
    id: 'TRK002',
    truckNumber: 'MH-12-CD-5678',
    truckType: 'secondary',
    vehicleType: 'mini-truck',
    position: { lat: 18.5560, lng: 73.9450 },
    status: 'idle',
    driver: 'Suresh Patil',
    driverId: 'DRV002',
    route: 'Kharadi Secondary Route 1',
    routeId: 'RT002',
    speed: 0,
    assignedGTP: 'GTP-001',
    assignedDumpingSite: 'FDS-001',
    tripsCompleted: 2,
    tripsAllowed: 4,
    vehicleCapacity: '3 tons',
    lastUpdate: '5 mins ago',
    vendorId: 'VND001',
    zoneId: 'ZN003',
    wardId: 'WD006',
    gpsDevice: {
      imei: '356938035643810',
      status: 'online',
      lastPing: '2024-01-15 10:28:00',
      signalStrength: 72,
      batteryLevel: 78
    }
  },
  {
    id: 'TRK003',
    truckNumber: 'MH-12-EF-9012',
    truckType: 'primary',
    vehicleType: 'compactor',
    position: { lat: 18.5620, lng: 73.9150 },
    status: 'dumping',
    driver: 'Amit Sharma',
    driverId: 'DRV003',
    route: 'Viman Nagar Primary Route 1',
    routeId: 'RT003',
    speed: 0,
    assignedGTP: 'GTP-002',
    tripsCompleted: 4,
    tripsAllowed: 5,
    vehicleCapacity: '8 tons',
    lastUpdate: '1 min ago',
    vendorId: 'VND001',
    zoneId: 'ZN003',
    wardId: 'WD007',
    gpsDevice: {
      imei: '356938035643811',
      status: 'online',
      lastPing: '2024-01-15 10:31:00',
      signalStrength: 90,
      batteryLevel: 65
    }
  },
  {
    id: 'TRK004',
    truckNumber: 'MH-12-GH-3456',
    truckType: 'secondary',
    vehicleType: 'dumper',
    position: { lat: 18.5580, lng: 73.9300 },
    status: 'offline',
    driver: 'Prakash Jadhav',
    driverId: 'DRV004',
    route: 'Viman Nagar Secondary Route 1',
    routeId: 'RT004',
    speed: 0,
    assignedGTP: 'GTP-002',
    assignedDumpingSite: 'FDS-001',
    tripsCompleted: 1,
    tripsAllowed: 3,
    vehicleCapacity: '12 tons',
    lastUpdate: '45 mins ago',
    vendorId: 'VND001',
    zoneId: 'ZN003',
    wardId: 'WD007',
    breakdownTime: '2024-01-15 09:45:00',
    breakdownReason: 'Engine issue',
    gpsDevice: {
      imei: '356938035643812',
      status: 'offline',
      lastPing: '2024-01-15 09:45:00',
      signalStrength: 0,
      batteryLevel: 12
    }
  },
  {
    id: 'TRK005',
    truckNumber: 'MH-12-IJ-7890',
    truckType: 'primary',
    vehicleType: 'compactor',
    position: { lat: 18.5890, lng: 73.8150 },
    status: 'moving',
    driver: 'Vijay Deshmukh',
    driverId: 'DRV005',
    route: 'Aundh Primary Route 1',
    routeId: 'RT005',
    speed: 30,
    assignedGTP: 'GTP-003',
    tripsCompleted: 2,
    tripsAllowed: 5,
    vehicleCapacity: '10 tons',
    lastUpdate: 'Just now',
    vendorId: 'VND002',
    zoneId: 'ZN001',
    wardId: 'WD001',
    gpsDevice: {
      imei: '356938035643813',
      status: 'online',
      lastPing: '2024-01-15 10:32:00',
      signalStrength: 95,
      batteryLevel: 88
    }
  },
  {
    id: 'TRK006',
    truckNumber: 'MH-12-KL-1122',
    truckType: 'primary',
    vehicleType: 'open-truck',
    position: { lat: 18.5650, lng: 73.7950 },
    status: 'moving',
    driver: 'Manoj Patil',
    driverId: 'DRV006',
    route: 'Baner Primary Route 1',
    routeId: 'RT006',
    speed: 22,
    assignedGTP: 'GTP-003',
    tripsCompleted: 3,
    tripsAllowed: 5,
    vehicleCapacity: '5 tons',
    lastUpdate: '3 mins ago',
    vendorId: 'VND002',
    zoneId: 'ZN001',
    wardId: 'WD002',
    gpsDevice: {
      imei: '356938035643814',
      status: 'online',
      lastPing: '2024-01-15 10:29:00',
      signalStrength: 80,
      batteryLevel: 70
    }
  },
  {
    id: 'TRK007',
    truckNumber: 'MH-12-MN-3344',
    truckType: 'secondary',
    vehicleType: 'mini-truck',
    position: { lat: 18.5880, lng: 73.8200 },
    status: 'moving',
    driver: 'Ravi Deshmukh',
    driverId: 'DRV007',
    route: 'Aundh Secondary Route 1',
    routeId: 'RT007',
    speed: 18,
    assignedGTP: 'GTP-003',
    assignedDumpingSite: 'FDS-002',
    tripsCompleted: 2,
    tripsAllowed: 4,
    vehicleCapacity: '4 tons',
    lastUpdate: '1 min ago',
    vendorId: 'VND002',
    zoneId: 'ZN001',
    wardId: 'WD001',
    gpsDevice: {
      imei: '356938035643815',
      status: 'online',
      lastPing: '2024-01-15 10:31:00',
      signalStrength: 75,
      batteryLevel: 82
    }
  },
  {
    id: 'TRK008',
    truckNumber: 'MH-12-OP-5566',
    truckType: 'primary',
    vehicleType: 'compactor',
    position: { lat: 18.5010, lng: 73.9350 },
    status: 'moving',
    driver: 'Vikram Singh',
    driverId: 'DRV008',
    route: 'Hadapsar Primary Route 1',
    routeId: 'RT008',
    speed: 28,
    assignedGTP: 'GTP-004',
    tripsCompleted: 2,
    tripsAllowed: 5,
    vehicleCapacity: '8 tons',
    lastUpdate: '2 mins ago',
    vendorId: 'VND003',
    zoneId: 'ZN002',
    wardId: 'WD004',
    gpsDevice: {
      imei: '356938035643816',
      status: 'online',
      lastPing: '2024-01-15 10:30:00',
      signalStrength: 88,
      batteryLevel: 75
    }
  },
  {
    id: 'TRK009',
    truckNumber: 'MH-12-QR-7788',
    truckType: 'secondary',
    vehicleType: 'dumper',
    position: { lat: 18.5050, lng: 73.9400 },
    status: 'dumping',
    driver: 'Deepak Jadhav',
    driverId: 'DRV009',
    route: 'Hadapsar Secondary Route 1',
    routeId: 'RT009',
    speed: 0,
    assignedGTP: 'GTP-004',
    assignedDumpingSite: 'FDS-001',
    tripsCompleted: 3,
    tripsAllowed: 4,
    vehicleCapacity: '15 tons',
    lastUpdate: '1 min ago',
    vendorId: 'VND003',
    zoneId: 'ZN002',
    wardId: 'WD004',
    gpsDevice: {
      imei: '356938035643817',
      status: 'online',
      lastPing: '2024-01-15 10:31:00',
      signalStrength: 92,
      batteryLevel: 68
    }
  },
  // Spare trucks
  {
    id: 'TRK-SPR-001',
    truckNumber: 'MH-12-SP-1001',
    truckType: 'primary',
    vehicleType: 'compactor',
    position: { lat: 18.5450, lng: 73.9350 },
    status: 'idle',
    driver: 'Ganesh More',
    driverId: 'DRV-SPR-001',
    route: 'Unassigned',
    routeId: '',
    speed: 0,
    tripsCompleted: 0,
    tripsAllowed: 5,
    vehicleCapacity: '8 tons',
    lastUpdate: 'Available',
    vendorId: 'VND001',
    zoneId: 'ZN003',
    wardId: 'WD006',
    isSpare: true,
    gpsDevice: {
      imei: '356938035643818',
      status: 'online',
      lastPing: '2024-01-15 10:30:00',
      signalStrength: 90,
      batteryLevel: 100
    }
  },
  {
    id: 'TRK-SPR-002',
    truckNumber: 'MH-12-SP-2001',
    truckType: 'secondary',
    vehicleType: 'dumper',
    position: { lat: 18.5870, lng: 73.8180 },
    status: 'idle',
    driver: 'Santosh Kulkarni',
    driverId: 'DRV-SPR-002',
    route: 'Unassigned',
    routeId: '',
    speed: 0,
    assignedDumpingSite: 'FDS-002',
    tripsCompleted: 0,
    tripsAllowed: 4,
    vehicleCapacity: '12 tons',
    lastUpdate: 'Available',
    vendorId: 'VND002',
    zoneId: 'ZN001',
    wardId: 'WD001',
    isSpare: true,
    gpsDevice: {
      imei: '356938035643819',
      status: 'online',
      lastPing: '2024-01-15 10:30:00',
      signalStrength: 88,
      batteryLevel: 95
    }
  }
];

// Helper functions
export const getTruckMasterById = (truckId: string): TruckMaster | undefined => trucksMaster.find(t => t.id === truckId);
export const getTruckLiveById = (truckId: string): TruckLive | undefined => trucksLive.find(t => t.id === truckId);
export const getTrucksByVendor = (vendorId: string): TruckMaster[] => trucksMaster.filter(t => t.vendorId === vendorId);
export const getTrucksByZone = (zoneId: string): TruckMaster[] => trucksMaster.filter(t => t.zoneId === zoneId);
export const getTrucksByWard = (wardId: string): TruckMaster[] => trucksMaster.filter(t => t.wardId === wardId);
export const getActiveTrucks = (): TruckMaster[] => trucksMaster.filter(t => t.status === 'active' && !t.isSpare);
export const getSpareTrucks = (): TruckMaster[] => trucksMaster.filter(t => t.isSpare);
