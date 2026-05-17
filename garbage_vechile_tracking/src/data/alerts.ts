// Alerts Data with proper truck references

export type AlertSeverity = 'low' | 'medium' | 'high' | 'warning';
export type AlertType = 'route_deviation' | 'missed_pickup' | 'unauthorized_halt' | 'speed_violation' | 'geofence_breach' | 'device_tamper' | 'late_arrival';

export interface Alert {
  id: string;
  type: AlertType;
  truckId: string;
  truckNumber: string;
  driverId: string;
  driverName: string;
  message: string;
  time: string;
  severity: AlertSeverity;
  routeId?: string;
  wardId?: string;
  zoneId?: string;
  resolved: boolean;
}

// Alerts with proper references to trucks and drivers
export const alerts: Alert[] = [
  {
    id: 'ALT-001',
    type: 'route_deviation',
    truckId: 'TRK002',
    truckNumber: 'MH-12-CD-5678',
    driverId: 'DRV002',
    driverName: 'Suresh Patil',
    message: 'Deviated from assigned route by 350m',
    time: '5 min ago',
    severity: 'warning',
    routeId: 'RT002',
    wardId: 'WD006',
    zoneId: 'ZN003',
    resolved: false
  },
  {
    id: 'ALT-002',
    type: 'missed_pickup',
    truckId: 'TRK001',
    truckNumber: 'MH-12-AB-1234',
    driverId: 'DRV001',
    driverName: 'Rajesh Kumar',
    message: 'Missed pickup at Kharadi Market (PP-KHR-004)',
    time: '12 min ago',
    severity: 'high',
    routeId: 'RT001',
    wardId: 'WD006',
    zoneId: 'ZN003',
    resolved: false
  },
  {
    id: 'ALT-003',
    type: 'unauthorized_halt',
    truckId: 'TRK002',
    truckNumber: 'MH-12-CD-5678',
    driverId: 'DRV002',
    driverName: 'Suresh Patil',
    message: 'Unauthorized halt detected - 15 minutes outside designated zone',
    time: '18 min ago',
    severity: 'medium',
    routeId: 'RT002',
    wardId: 'WD006',
    zoneId: 'ZN003',
    resolved: false
  },
  {
    id: 'ALT-004',
    type: 'route_deviation',
    truckId: 'TRK007',
    truckNumber: 'MH-12-MN-3344',
    driverId: 'DRV007',
    driverName: 'Ravi Deshmukh',
    message: 'Off-route for extended period near Aundh-Baner Link Road',
    time: '25 min ago',
    severity: 'warning',
    routeId: 'RT007',
    wardId: 'WD001',
    zoneId: 'ZN001',
    resolved: false
  },
  {
    id: 'ALT-005',
    type: 'speed_violation',
    truckId: 'TRK005',
    truckNumber: 'MH-12-IJ-7890',
    driverId: 'DRV005',
    driverName: 'Vijay Deshmukh',
    message: 'Speed limit exceeded: 55 km/h in 40 km/h zone near Westend Mall',
    time: '32 min ago',
    severity: 'high',
    routeId: 'RT005',
    wardId: 'WD001',
    zoneId: 'ZN001',
    resolved: false
  },
  {
    id: 'ALT-006',
    type: 'geofence_breach',
    truckId: 'TRK006',
    truckNumber: 'MH-12-KL-1122',
    driverId: 'DRV006',
    driverName: 'Manoj Patil',
    message: 'Exited designated collection zone boundary at Baner',
    time: '45 min ago',
    severity: 'medium',
    routeId: 'RT006',
    wardId: 'WD002',
    zoneId: 'ZN001',
    resolved: false
  },
  {
    id: 'ALT-007',
    type: 'missed_pickup',
    truckId: 'TRK003',
    truckNumber: 'MH-12-EF-9012',
    driverId: 'DRV003',
    driverName: 'Amit Sharma',
    message: 'Skipped 2 consecutive pickup points at Viman Nagar',
    time: '52 min ago',
    severity: 'high',
    routeId: 'RT003',
    wardId: 'WD007',
    zoneId: 'ZN003',
    resolved: false
  },
  {
    id: 'ALT-008',
    type: 'device_tamper',
    truckId: 'TRK004',
    truckNumber: 'MH-12-GH-3456',
    driverId: 'DRV004',
    driverName: 'Prakash Jadhav',
    message: 'GPS device disconnection detected - Vehicle went offline',
    time: '1 hr ago',
    severity: 'high',
    routeId: 'RT004',
    wardId: 'WD007',
    zoneId: 'ZN003',
    resolved: false
  }
];

// Helper functions
export const getAlertsByTruck = (truckId: string): Alert[] => alerts.filter(a => a.truckId === truckId);
export const getAlertsByDriver = (driverId: string): Alert[] => alerts.filter(a => a.driverId === driverId);
export const getAlertsByZone = (zoneId: string): Alert[] => alerts.filter(a => a.zoneId === zoneId);
export const getAlertsBySeverity = (severity: AlertSeverity): Alert[] => alerts.filter(a => a.severity === severity);
export const getUnresolvedAlerts = (): Alert[] => alerts.filter(a => !a.resolved);
