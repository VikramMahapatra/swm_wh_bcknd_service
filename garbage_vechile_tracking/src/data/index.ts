// Unified Data Exports - All mock data with proper relationships
// This file serves as the central export point for all mock data

// Zone and Ward data
export { zones, wards, getWardsByZone, getZoneById, getWardById } from './zones';
export type { Zone, Ward } from './zones';

// Vendor data
export { vendors, getVendorById, getActiveVendors } from './vendors';
export type { Vendor } from './vendors';

// Driver data
export { drivers, getDriverById, getDriverByTruckId, getActiveDrivers } from './drivers';
export type { Driver } from './drivers';

// Truck data (master and live)
export { 
  trucksMaster, 
  trucksLive, 
  getTruckMasterById, 
  getTruckLiveById, 
  getTrucksByVendor, 
  getTrucksByZone,
  getTrucksByWard,
  getActiveTrucks, 
  getSpareTrucks 
} from './trucks';
export type { 
  TruckMaster, 
  TruckLive, 
  TruckType, 
  RouteType, 
  TruckStatus, 
  TruckMasterStatus, 
  DeviceStatus, 
  GPSDevice 
} from './trucks';

// Routes, Pickup Points, GTPs, Dumping Sites
export { 
  routes, 
  pickupPoints, 
  gtpLocations, 
  finalDumpingSites,
  getRoutesByZone,
  getRoutesByWard,
  getRouteById,
  getPickupPointsByRoute,
  getPickupPointsByWard,
  getGTPByZone,
  GOOGLE_MAPS_API_KEY,
  KHARADI_CENTER
} from './routes';
export type { Route, RoutePoint, PickupPoint, GTPLocation, FinalDumpingSite } from './routes';

// Tickets and Escalation
export { 
  tickets, 
  escalationConfig, 
  slaConfig,
  getTicketsByTruck,
  getTicketsByDriver,
  getOpenTickets
} from './tickets';
export type { 
  Ticket, 
  TicketComment, 
  TicketStatus, 
  TicketPriority, 
  TicketCategory,
  EscalationLevel,
  EscalationConfig,
  SLAConfig
} from './tickets';

// Alerts
export { 
  alerts, 
  getAlertsByTruck, 
  getAlertsByDriver, 
  getAlertsByZone, 
  getAlertsBySeverity,
  getUnresolvedAlerts 
} from './alerts';
export type { Alert, AlertSeverity, AlertType } from './alerts';

// Legacy exports for backward compatibility
// These map the old names to new data structures
export { zones as mockZones } from './zones';
export { wards as mockWards } from './zones';
export { vendors as mockVendors } from './vendors';
export { drivers as mockDrivers } from './drivers';
export { trucksMaster as mockTrucks } from './trucks';
export { routes as mockRoutes } from './routes';
export { pickupPoints as mockPickupPoints } from './routes';
export { tickets as mockTickets } from './tickets';
export { escalationConfig as defaultEscalationConfig } from './tickets';
export { slaConfig as defaultSLAConfig } from './tickets';
export { trucksLive as trucks } from './trucks';

// Data summary for dashboard
export const getDataSummary = () => {
  const { zones } = require('./zones');
  const { wards } = require('./zones');
  const { vendors } = require('./vendors');
  const { drivers } = require('./drivers');
  const { trucksMaster, trucksLive } = require('./trucks');
  const { routes, pickupPoints, gtpLocations } = require('./routes');
  
  return {
    zones: {
      total: zones.length,
      active: zones.filter((z: any) => z.status === 'active').length
    },
    wards: {
      total: wards.length,
      active: wards.filter((w: any) => w.status === 'active').length
    },
    vendors: {
      total: vendors.length,
      active: vendors.filter((v: any) => v.status === 'active').length
    },
    drivers: {
      total: drivers.length,
      active: drivers.filter((d: any) => d.status === 'active').length,
      onLeave: drivers.filter((d: any) => d.status === 'on_leave').length
    },
    trucks: {
      total: trucksMaster.length,
      active: trucksMaster.filter((t: any) => t.status === 'active' && !t.isSpare).length,
      maintenance: trucksMaster.filter((t: any) => t.status === 'maintenance').length,
      spare: trucksMaster.filter((t: any) => t.isSpare).length
    },
    trucksLive: {
      total: trucksLive.length,
      moving: trucksLive.filter((t: any) => t.status === 'moving').length,
      idle: trucksLive.filter((t: any) => t.status === 'idle').length,
      dumping: trucksLive.filter((t: any) => t.status === 'dumping').length,
      offline: trucksLive.filter((t: any) => t.status === 'offline').length
    },
    routes: {
      total: routes.length,
      active: routes.filter((r: any) => r.status === 'active').length,
      primary: routes.filter((r: any) => r.type === 'primary').length,
      secondary: routes.filter((r: any) => r.type === 'secondary').length
    },
    pickupPoints: {
      total: pickupPoints.length,
      active: pickupPoints.filter((p: any) => p.status === 'active').length
    },
    gtpLocations: gtpLocations.length
  };
};
