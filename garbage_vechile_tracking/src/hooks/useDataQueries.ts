import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { apiService } from '@/services/api';

// Hook for fetching live trucks
export function useLiveTrucks(): UseQueryResult<any[], Error> {
  return useQuery({
    queryKey: ['trucks', 'live'],
    queryFn: () => apiService.getLiveTrucks(),
    staleTime: 10 * 1000, // 10 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Hook for fetching all trucks with filters
export function useTrucks(filters?: {
  zone_id?: string;
  vendor_id?: string;
  status?: string;
}): UseQueryResult<any[], Error> {
  return useQuery({
    queryKey: ['trucks', filters],
    queryFn: () => apiService.getTrucks(filters),
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Hook for fetching spare trucks
export function useSpareTrucks(): UseQueryResult<any[], Error> {
  return useQuery({
    queryKey: ['trucks', 'spare'],
    queryFn: () => apiService.getSpareTrucks(),
    staleTime: 60 * 1000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Hook for fetching all zones
export function useZones(): UseQueryResult<any[], Error> {
  return useQuery({
    queryKey: ['zones'],
    queryFn: () => apiService.getZones(),
    staleTime: 60 * 60 * 1000, // 1 hour
    gcTime: 24 * 60 * 60 * 1000, // 24 hours
  });
}

// Hook for fetching specific zone
export function useZone(zoneId: string): UseQueryResult<any, Error> {
  return useQuery({
    queryKey: ['zones', zoneId],
    queryFn: () => apiService.getZone(zoneId),
    staleTime: 60 * 60 * 1000, // 1 hour
    gcTime: 24 * 60 * 60 * 1000, // 24 hours
    enabled: !!zoneId,
  });
}

// Hook for fetching wards in a zone
export function useZoneWards(zoneId: string): UseQueryResult<any[], Error> {
  return useQuery({
    queryKey: ['zones', zoneId, 'wards'],
    queryFn: () => apiService.getZoneWards(zoneId),
    staleTime: 60 * 60 * 1000, // 1 hour
    gcTime: 24 * 60 * 60 * 1000, // 24 hours
    enabled: !!zoneId,
  });
}

// Hook for fetching all alerts
export function useAlerts(filters?: {
  status?: string;
  severity?: string;
  truck_id?: string;
}): UseQueryResult<any[], Error> {
  return useQuery({
    queryKey: ['alerts', filters],
    queryFn: () => apiService.getAlerts(filters),
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Hook for fetching active alerts
export function useActiveAlerts(): UseQueryResult<any[], Error> {
  return useQuery({
    queryKey: ['alerts', 'active'],
    queryFn: () => apiService.getActiveAlerts(),
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Hook for fetching expiry alerts
export function useExpiryAlerts(): UseQueryResult<any[], Error> {
  return useQuery({
    queryKey: ['alerts', 'expiry'],
    queryFn: () => apiService.getExpiryAlerts(),
    staleTime: 60 * 60 * 1000, // 1 hour
    gcTime: 24 * 60 * 60 * 1000, // 24 hours
  });
}

export function useReportsData(): UseQueryResult<Record<string, any>, Error> {
  return useQuery({
    queryKey: ['reports', 'data'],
    queryFn: () => apiService.getReportsData(),
    staleTime: 60 * 1000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Hook for fetching statistics
export function useStatistics(): UseQueryResult<any, Error> {
  return useQuery({
    queryKey: ['reports', 'statistics'],
    queryFn: () => apiService.getStatistics(),
    staleTime: 60 * 1000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Hook for fetching zone performance
export function useZonePerformance(): UseQueryResult<any[], Error> {
  return useQuery({
    queryKey: ['reports', 'zone-performance'],
    queryFn: () => apiService.getZonePerformance(),
    staleTime: 60 * 1000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Hook for fetching vendor performance
export function useVendorPerformance(): UseQueryResult<any[], Error> {
  return useQuery({
    queryKey: ['reports', 'vendor-performance'],
    queryFn: () => apiService.getVendorPerformance(),
    staleTime: 60 * 1000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Hook for fetching collection efficiency
export function useCollectionEfficiency(): UseQueryResult<any, Error> {
  return useQuery({
    queryKey: ['reports', 'collection-efficiency'],
    queryFn: () => apiService.getCollectionEfficiency(),
    staleTime: 60 * 1000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Hook for fetching vendors
export function useVendors(): UseQueryResult<any[], Error> {
  return useQuery({
    queryKey: ['vendors'],
    queryFn: () => apiService.getVendors(),
    staleTime: 60 * 60 * 1000, // 1 hour
    gcTime: 24 * 60 * 60 * 1000, // 24 hours
  });
}

// Hook for fetching routes
export function useRoutes(filters?: {
  zone_id?: string;
  ward_id?: string;
}): UseQueryResult<any[], Error> {
  return useQuery({
    queryKey: ['routes', filters],
    queryFn: () => apiService.getRoutes(filters),
    staleTime: 60 * 1000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Hook for fetching pickup points for a specific route
export function useRoutePickupPoints(routeId: string | null | undefined): UseQueryResult<any[], Error> {
  return useQuery({
    queryKey: ['route-pickup-points', routeId],
    queryFn: () => routeId ? apiService.getRoutePickupPoints(routeId) : Promise.resolve([]),
    enabled: !!routeId,
    staleTime: 60 * 1000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Hook for fetching pickup points
export function usePickupPoints(filters?: {
  route_id?: string;
  ward_id?: string;
}): UseQueryResult<any[], Error> {
  return useQuery({
    queryKey: ['pickup-points', filters],
    queryFn: () => apiService.getPickupPoints(filters),
    staleTime: 60 * 1000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Hook for fetching tickets
export function useTickets(filters?: {
  status?: string;
  priority?: string;
  zone_id?: string;
}): UseQueryResult<any[], Error> {
  return useQuery({
    queryKey: ['tickets', filters],
    queryFn: () => apiService.getTickets(filters),
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Hook for fetching drivers
export function useDrivers(): UseQueryResult<any[], Error> {
  return useQuery({
    queryKey: ['drivers'],
    queryFn: () => apiService.getDrivers(),
    staleTime: 60 * 60 * 1000, // 1 hour
    gcTime: 24 * 60 * 60 * 1000, // 24 hours
  });
}

// Hook for fetching GTC checkpoint entries
export function useGtcCheckpoints(filters?: {
  truck_id?: string;
  date?: string;
  date_from?: string;
  date_to?: string;
}): UseQueryResult<any[], Error> {
  return useQuery({
    queryKey: ['gtc-checkpoints', filters],
    queryFn: () => apiService.getGtcCheckpoints(filters),
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
}
