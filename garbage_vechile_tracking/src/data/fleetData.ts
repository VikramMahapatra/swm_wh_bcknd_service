// Legacy fleetData.ts - Re-exports from new modular data files
// This file maintains backward compatibility

export type { TruckStatus, DeviceStatus, RouteType } from './trucks';
export type { GPSDevice, TruckLive as TruckData } from './trucks';
export type { Route as RouteData, RoutePoint, GTPLocation, FinalDumpingSite } from './routes';
export type { PickupPoint } from './routes';

// Re-export RouteType as TruckType for backward compatibility in components that use it for primary/secondary
export type { RouteType as TruckType } from './trucks';

export { trucksLive as trucks } from './trucks';
export { routes } from './routes';
export { gtpLocations, finalDumpingSites, pickupPoints } from './routes';
export { GOOGLE_MAPS_API_KEY, KHARADI_CENTER } from './routes';
