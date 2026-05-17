// Legacy masterData.ts - Re-exports from new modular data files
// This file maintains backward compatibility

// Re-export types
export type { Zone, Ward } from './zones';
export type { Vendor } from './vendors';
export type { Driver } from './drivers';
export type { TruckMaster, TruckType, RouteType, TruckMasterStatus } from './trucks';
export type { Route, PickupPoint } from './routes';
export type { Ticket, TicketComment, TicketStatus, TicketPriority, TicketCategory, EscalationLevel, EscalationConfig, SLAConfig } from './tickets';

// Re-export data with legacy names
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
