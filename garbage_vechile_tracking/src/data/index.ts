// Local imports for dashboard summary
import { zones as mockZones, wards as mockWards } from './zones';
import { vendors as mockVendors } from './vendors';
import { drivers as mockDrivers } from './drivers';
import { trucksMaster as mockTrucks, trucksLive as trucks } from './trucks';
import { routes as mockRoutes, pickupPoints as mockPickupPoints, gtpLocations } from './routes';
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
// Data summary for dashboard

// Data summary for dashboard (must be after all mock* exports)
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
export { gtpLocations } from './routes';


// Data summary for dashboard
export const getDataSummary = () => {
  return {
    zones: {
      total: mockZones.length,
      active: mockZones.filter((z: any) => z.status === 'active').length
    },
    wards: {
      total: mockWards.length,
      active: mockWards.filter((w: any) => w.status === 'active').length
    },
    vendors: {
      total: mockVendors.length,
      active: mockVendors.filter((v: any) => v.status === 'active').length
    },
    drivers: {
      total: mockDrivers.length,
      active: mockDrivers.filter((d: any) => d.status === 'active').length,
      onLeave: mockDrivers.filter((d: any) => d.status === 'on_leave').length
    },
    trucks: {
      total: mockTrucks.length,
      active: mockTrucks.filter((t: any) => t.status === 'active' && !t.isSpare).length,
      maintenance: mockTrucks.filter((t: any) => t.status === 'maintenance').length,
      spare: mockTrucks.filter((t: any) => t.isSpare).length
    },
    trucksLive: {
      total: trucks.length,
      moving: trucks.filter((t: any) => t.status === 'moving').length,
      idle: trucks.filter((t: any) => t.status === 'idle').length,
      dumping: trucks.filter((t: any) => t.status === 'dumping').length,
      offline: trucks.filter((t: any) => t.status === 'offline').length
    },
    routes: {
      total: mockRoutes.length,
      active: mockRoutes.filter((r: any) => r.status === 'active').length,
      primary: mockRoutes.filter((r: any) => r.type === 'primary').length,
      secondary: mockRoutes.filter((r: any) => r.type === 'secondary').length
    },
    pickupPoints: {
      total: mockPickupPoints.length,
      active: mockPickupPoints.filter((p: any) => p.status === 'active').length
    },
    gtpLocations: gtpLocations.length
  };
};
