import { API_BASE_URL } from '../config/api';
import { clearAuthTokens, getAccessToken, getRefreshToken, saveAuthTokens } from '@/lib/authStorage';

export interface TruckLive {
  id: string;
  registration_number: string;
  type: string;
  route_type: string;
  latitude: number | null;
  longitude: number | null;
  current_status: string;
  speed: number;
  trips_completed: number;
  trips_allowed: number;
  driver_name: string | null;
  route_name: string | null;
  vendor_id: string;
  zone_id: string;
  ward_id: string;
  is_spare: boolean;
  last_update: string | null;
  bearing?: number;
}

export interface Zone {
  id: string;
  name: string;
  code: string;
  description: string;
  supervisor_name: string;
  supervisor_phone: string;
  total_wards: number;
  status: string;
}

export interface Alert {
  id: number;
  truck_id: string;
  alert_type: string;
  severity: string;
  message: string;
  timestamp: string;
  status: string;
  resolved_at: string | null;
}

export interface Statistics {
  total_trucks: number;
  active_trucks: number;
  idle_trucks: number;
  total_zones: number;
  total_wards: number;
  total_vendors: number;
  total_routes: number;
  total_pickup_points: number;
  active_alerts: number;
}

export interface GtcCheckpointEntry {
  id: number;
  truck_id: string;
  arrived_at: string;
  is_dry: boolean;
  is_wet: boolean;
  is_metal: boolean;
  is_plastic: boolean;
  is_sanitary: boolean;
  truck_cleanliness_score: number | null;
  gtc_cleanliness_score: number | null;
  remarks: string | null;
  truck_registration_number?: string | null;
}

type RealtimeSnapshotTruck = {
  imei: string;
  vehicle_id?: string | null;
  lat: number;
  lng: number;
  speed_kph?: number | null;
  status?: string | null;
  event_ts?: string | null;
  vendor_id?: string | null;
};

type RealtimeSnapshotResponse = {
  items: RealtimeSnapshotTruck[];
  total: number;
};

class ApiService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  private async fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const doFetch = async (accessToken?: string | null) =>
      fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(accessToken ? { 'Authorization': `Bearer ${accessToken}` } : {}),
          ...options?.headers,
        },
      });

    try {
      const token = getAccessToken();
      let response = await doFetch(token);

      if (response.status === 401 && token && !endpoint.startsWith('/v1/auth/refresh')) {
        const nextToken = await this.tryRefreshToken();
        if (nextToken) {
          response = await doFetch(nextToken);
        }
      }

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API fetch error for ${endpoint}:`, error);
      throw error;
    }
  }

  private toQueryString(filters?: Record<string, string | undefined>): string {
    if (!filters) return "";
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        params.set(key, value);
      }
    });
    const query = params.toString();
    return query ? `?${query}` : "";
  }

  private async getRealtimeSnapshot(limit = 20000): Promise<RealtimeSnapshotTruck[]> {
    const payload = await this.fetchApi<RealtimeSnapshotResponse>(`/v1/realtime/trucks?limit=${limit}`);
    return Array.isArray(payload.items) ? payload.items : [];
  }

  private async tryRefreshToken(): Promise<string | null> {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return null;

    try {
      const response = await fetch(`${this.baseUrl}/v1/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) {
        clearAuthTokens();
        return null;
      }

      const payload = await response.json();
      const accessToken = String(payload?.access_token || '');
      const nextRefreshToken = String(payload?.refresh_token || '');
      if (!accessToken || !nextRefreshToken) {
        clearAuthTokens();
        return null;
      }

      saveAuthTokens(accessToken, nextRefreshToken);
      return accessToken;
    } catch {
      return null;
    }
  }

  private toLegacyTruckModel(item: RealtimeSnapshotTruck): TruckLive {
    return {
      id: item.imei,
      registration_number: item.vehicle_id || item.imei,
      type: 'compactor',
      route_type: (item.vehicle_id || '').toLowerCase().includes('s') ? 'secondary' : 'primary',
      latitude: Number.isFinite(Number(item.lat)) ? Number(item.lat) : null,
      longitude: Number.isFinite(Number(item.lng)) ? Number(item.lng) : null,
      current_status: item.status || 'idle',
      speed: Number(item.speed_kph ?? 0),
      trips_completed: 0,
      trips_allowed: 0,
      driver_name: null,
      route_name: 'Live Feed',
      vendor_id: item.vendor_id || '',
      zone_id: '',
      ward_id: '',
      is_spare: false,
      last_update: item.event_ts || null,
    };
  }

  // Trucks
  async getLiveTrucks(): Promise<TruckLive[]> {
    const items = await this.getRealtimeSnapshot();
    return items.map((item) => this.toLegacyTruckModel(item));
  }

  async getTrucks(filters?: { zone_id?: string; vendor_id?: string; status?: string }): Promise<any[]> {
    const suffix = this.toQueryString(filters);
    return this.fetchApi(`/trucks${suffix}`);
  }

  async getSpareTrucks(): Promise<any[]> {
    return this.fetchApi('/trucks/spare');
  }

  async assignTruckRoute(truckId: string, routeId: string): Promise<any> {
    return this.fetchApi(`/trucks/${truckId}/assign-route`, {
      method: 'PUT',
      body: JSON.stringify({ assigned_route_id: routeId }),
    });
  }

  // Zones
  async getZones(): Promise<Zone[]> {
    const rows = await this.fetchApi<any[]>('/zones');
    return (Array.isArray(rows) ? rows : []).map((row: any) => ({
      id: String(row.id ?? ''),
      name: String(row.name ?? row.zone_name ?? ''),
      code: String(row.code ?? row.zone_code ?? ''),
      description: String(row.description ?? ''),
      supervisor_name: String(row.supervisor_name ?? ''),
      supervisor_phone: String(row.supervisor_phone ?? ''),
      total_wards: Number(row.total_wards ?? 0) || 0,
      status: String(row.status ?? (row.active === false ? 'inactive' : 'active')),
      supervisorName: String(row.supervisorName ?? row.supervisor_name ?? ''),
      supervisorPhone: String(row.supervisorPhone ?? row.supervisor_phone ?? ''),
      totalWards: Number(row.totalWards ?? row.total_wards ?? 0) || 0,
    })) as Zone[];
  }

  async getZone(zoneId: string): Promise<Zone> {
    const zones = await this.getZones();
    const matched = zones.find((zone) => zone.id === zoneId || zone.code === zoneId || zone.name === zoneId);
    if (!matched) {
      throw new Error(`Zone not found: ${zoneId}`);
    }
    return matched;
  }

  async getZoneWards(zoneId: string): Promise<any[]> {
    const rows = await this.fetchApi<any[]>(`/zones/${zoneId}/wards`);
    return (Array.isArray(rows) ? rows : []).map((row: any) => ({
      id: String(row.id ?? ''),
      name: String(row.name ?? row.ward_name ?? ''),
      code: String(row.code ?? row.ward_code ?? ''),
      zoneId: String(row.zoneId ?? row.zone_id ?? ''),
      population: Number(row.population ?? 0) || 0,
      area: Number(row.area ?? 0) || 0,
      totalPickupPoints: Number(row.totalPickupPoints ?? row.total_pickup_points ?? 0) || 0,
      status: String(row.status ?? (row.active === false ? 'inactive' : 'active')),
      ward_name: row.ward_name,
      ward_code: row.ward_code,
      zone_id: row.zone_id,
    }));
  }

  async getWards(): Promise<any[]> {
    const payload = await this.fetchApi<{ items?: any[] }>('/wards?page=1&page_size=200');
    const rows = Array.isArray(payload?.items) ? payload.items : [];
    return rows.map((row: any) => ({
      id: String(row.id ?? ''),
      name: String(row.name ?? row.ward_name ?? ''),
      code: String(row.code ?? row.ward_code ?? ''),
      zoneId: String(row.zoneId ?? row.zone_id ?? ''),
      population: Number(row.population ?? 0) || 0,
      area: Number(row.area ?? 0) || 0,
      totalPickupPoints: Number(row.totalPickupPoints ?? row.total_pickup_points ?? 0) || 0,
      status: String(row.status ?? (row.active === false ? 'inactive' : 'active')),
    }));
  }

  async createZone(payload: { code: string; name: string; status?: 'active' | 'inactive' }): Promise<any> {
    return this.fetchApi('/zones', {
      method: 'POST',
      body: JSON.stringify({
        zone_code: payload.code,
        zone_name: payload.name,
        active: payload.status !== 'inactive',
      }),
    });
  }

  async createWard(payload: {
    code: string;
    name: string;
    zoneName: string;
    status?: 'active' | 'inactive';
  }): Promise<any> {
    return this.fetchApi('/wards', {
      method: 'POST',
      body: JSON.stringify({
        ward_code: payload.code,
        ward_name: payload.name,
        zone_name: payload.zoneName,
        active: payload.status !== 'inactive',
      }),
    });
  }

  async uploadGeofencesCsv(file: File): Promise<any> {
    const token = getAccessToken();
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${this.baseUrl}/geofences/import`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      body: formData,
    });
    if (!response.ok) {
      throw new Error(`Geofence upload failed: ${response.statusText}`);
    }
    return response.json();
  }

  async getGeofences(filters?: {
    geofence_for?: string;
    zone_id?: string;
    ward_id?: string;
    route_id?: string;
    q?: string;
    page?: number;
    page_size?: number;
  }): Promise<any[]> {
    const suffix = this.toQueryString({
      geofence_for: filters?.geofence_for,
      zone_id: filters?.zone_id,
      ward_id: filters?.ward_id,
      route_id: filters?.route_id,
      q: filters?.q,
      page: String(filters?.page ?? 1),
      page_size: String(filters?.page_size ?? 200),
    });
    const payload = await this.fetchApi<{ items?: any[] }>(`/geofences${suffix}`);
    return Array.isArray(payload?.items) ? payload.items : [];
  }

  async createGeofence(payload: {
    geofence_code: string;
    geofence_name: string;
    type: 'zone' | 'depot' | 'landfill' | 'parking' | 'maintenance';
    geometry_type: 'polygon' | 'circle';
    geofence_for: 'zone' | 'ward' | 'route';
    zone_id: string;
    ward_id?: string | null;
    route_id?: string | null;
    polygon?: Record<string, any> | null;
    center_lat?: number | null;
    center_lng?: number | null;
    radius_meter?: number | null;
    active?: boolean;
  }): Promise<any> {
    return this.fetchApi('/geofences', {
      method: 'POST',
      body: JSON.stringify({
        geofence_code: payload.geofence_code,
        geofence_name: payload.geofence_name,
        type: payload.type,
        geometry_type: payload.geometry_type,
        geofence_for: payload.geofence_for,
        zone_id: payload.zone_id,
        ward_id: payload.ward_id ?? null,
        route_id: payload.route_id ?? null,
        polygon: payload.polygon ?? null,
        center_lat: payload.center_lat ?? null,
        center_lng: payload.center_lng ?? null,
        radius_meter: payload.radius_meter ?? null,
        active: payload.active ?? true,
      }),
    });
  }

  async deleteGeofence(geofenceId: string): Promise<any> {
    return this.fetchApi(`/geofences/${geofenceId}`, {
      method: 'DELETE',
    });
  }

  async updateGeofence(geofenceId: string, payload: {
    geofence_code: string;
    geofence_name: string;
    type: 'zone' | 'depot' | 'landfill' | 'parking' | 'maintenance';
    geometry_type: 'polygon' | 'circle';
    geofence_for: 'zone' | 'ward' | 'route';
    zone_id: string;
    ward_id?: string | null;
    route_id?: string | null;
    polygon?: Record<string, any> | null;
    center_lat?: number | null;
    center_lng?: number | null;
    radius_meter?: number | null;
    active?: boolean;
  }): Promise<any> {
    return this.fetchApi(`/geofences/${geofenceId}`, {
      method: 'PUT',
      body: JSON.stringify({
        geofence_code: payload.geofence_code,
        geofence_name: payload.geofence_name,
        type: payload.type,
        geometry_type: payload.geometry_type,
        geofence_for: payload.geofence_for,
        zone_id: payload.zone_id,
        ward_id: payload.ward_id ?? null,
        route_id: payload.route_id ?? null,
        polygon: payload.polygon ?? null,
        center_lat: payload.center_lat ?? null,
        center_lng: payload.center_lng ?? null,
        radius_meter: payload.radius_meter ?? null,
        active: payload.active ?? true,
      }),
    });
  }

  // Alerts
  async getAlerts(filters?: { status?: string; severity?: string; truck_id?: string }): Promise<Alert[]> {
    const suffix = this.toQueryString(filters);
    return this.fetchApi(`/alerts${suffix}`);
  }

  async getAlertsPage(filters?: {
    status?: string;
    severity?: string;
    truck_id?: string;
    alert_type?: string;
    zone_id?: string;
    ward_id?: string;
    route_id?: string;
    search?: string;
    date_from?: string;
    date_to?: string;
    page?: number;
    page_size?: number;
  }): Promise<any> {
    const suffix = this.toQueryString(filters);
    return this.fetchApi(`/alerts/page${suffix}`);
  }

  async getActiveAlerts(): Promise<Alert[]> {
    return this.fetchApi('/alerts/active');
  }

  async getAlertSummary(): Promise<any> {
    return this.fetchApi('/alerts/summary');
  }

  async acknowledgeAlert(alertId: string, notes?: string): Promise<any> {
    return this.fetchApi(`/alerts/${alertId}/acknowledge`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    });
  }

  async resolveAlert(alertId: string, notes?: string): Promise<any> {
    return this.fetchApi(`/alerts/${alertId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    });
  }

  async escalateAlert(alertId: string, notes?: string): Promise<any> {
    return this.fetchApi(`/alerts/${alertId}/escalate`, {
      method: 'POST',
      body: JSON.stringify({ notes, escalation_status: 'escalated' }),
    });
  }

  async getExpiryAlerts(): Promise<any> {
    return this.fetchApi('/alerts/expiry');
  }

  async getReportsData(filters?: {
    date_from?: string;
    date_to?: string;
    zone_id?: string;
    ward_id?: string;
    vehicle_id?: string;
    route_id?: string;
  }): Promise<Record<string, any>> {
    const suffix = this.toQueryString(filters);
    return this.fetchApi(`/reports/data${suffix}`);
  }

  async getCompletedTrips(filters?: {
    date_from?: string;
    date_to?: string;
    zone_id?: string;
    ward_id?: string;
    vehicle_id?: string;
  }): Promise<any> {
    const suffix = this.toQueryString(filters);
    return this.fetchApi(`/trips/completed${suffix}`);
  }

  // Reports
  async getStatistics(): Promise<Statistics> {
    return this.fetchApi<Statistics>('/reports/statistics');
  }

  async getZonePerformance(): Promise<any[]> {
    return this.fetchApi('/reports/zone-performance');
  }

  async getVendorPerformance(): Promise<any[]> {
    return this.fetchApi('/reports/vendor-performance');
  }

  async getCollectionEfficiency(): Promise<any> {
    return this.fetchApi('/reports/collection-efficiency');
  }

  // Vendors
  async getVendors(): Promise<any[]> {
    return this.fetchApi('/vendors?ui_compat=true');
  }

  async getVendor(vendorId: string): Promise<any> {
    return this.fetchApi(`/vendors/${vendorId}`);
  }

  async createVendor(payload: {
    vendor_code: string;
    vendor_name: string;
    contact_person?: string | null;
    email?: string | null;
    phone?: string | null;
    active?: boolean;
    auth_type?: 'header' | 'signature' | 'ip';
    allowed_ips?: string[];
    callback_format?: Record<string, any>;
    metadata?: Record<string, any>;
    webhook_secret?: string | null;
    signature_key?: string | null;
  }): Promise<any> {
    return this.fetchApi('/vendors', {
      method: 'POST',
      body: JSON.stringify({
        vendor_code: payload.vendor_code,
        vendor_name: payload.vendor_name,
        contact_person: payload.contact_person ?? null,
        email: payload.email ?? null,
        phone: payload.phone ?? null,
        active: payload.active ?? true,
        auth_type: payload.auth_type ?? 'header',
        allowed_ips: payload.allowed_ips ?? [],
        callback_format: payload.callback_format ?? {},
        metadata: payload.metadata ?? {},
        webhook_secret: payload.webhook_secret ?? null,
        signature_key: payload.signature_key ?? null,
      }),
    });
  }

  async updateVendor(
    vendorId: string,
    payload: {
      vendor_code: string;
      vendor_name: string;
      contact_person?: string | null;
      email?: string | null;
      phone?: string | null;
      active?: boolean;
      auth_type?: 'header' | 'signature' | 'ip';
      allowed_ips?: string[];
      callback_format?: Record<string, any>;
      metadata?: Record<string, any>;
      webhook_secret?: string | null;
      signature_key?: string | null;
    }
  ): Promise<any> {
    return this.fetchApi(`/vendors/${vendorId}`, {
      method: 'PUT',
      body: JSON.stringify({
        vendor_code: payload.vendor_code,
        vendor_name: payload.vendor_name,
        contact_person: payload.contact_person ?? null,
        email: payload.email ?? null,
        phone: payload.phone ?? null,
        active: payload.active ?? true,
        auth_type: payload.auth_type ?? 'header',
        allowed_ips: payload.allowed_ips ?? [],
        callback_format: payload.callback_format ?? {},
        metadata: payload.metadata ?? {},
        webhook_secret: payload.webhook_secret ?? null,
        signature_key: payload.signature_key ?? null,
      }),
    });
  }

  async deleteVendor(vendorId: string): Promise<any> {
    return this.fetchApi(`/vendors/${vendorId}`, {
      method: 'DELETE',
    });
  }

  // Routes
  async getRoutes(filters?: { zone_id?: string; ward_id?: string }): Promise<any[]> {
    const routeFilters = {
      ui_compat: 'true',
      zone_id: filters?.zone_id,
      ward_id: filters?.ward_id,
    };
    const suffix = this.toQueryString(routeFilters);
    return this.fetchApi(`/routes${suffix}`);
  }

  async getRoutePickupPoints(routeId: string): Promise<any[]> {
    return this.fetchApi(`/routes/${routeId}/pickup-points`);
  }

  async createRoute(payload: {
    route_name: string;
    zone_id: string;
    ward_id: string;
    polyline_coordinates: number[][];
  }): Promise<any> {
    return this.fetchApi('/routes', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async updateRoute(routeId: string, payload: {
    route_name: string;
    zone_id: string;
    ward_id: string;
    polyline_coordinates: number[][];
  }): Promise<any> {
    return this.fetchApi(`/routes/${routeId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  async deleteRoute(routeId: string): Promise<any> {
    return this.fetchApi(`/routes/${routeId}`, {
      method: 'DELETE',
    });
  }

  // Pickup Points
  async getPickupPoints(filters?: { zone_id?: string; ward_id?: string; route_id?: string }): Promise<any[]> {
    const suffix = this.toQueryString(filters);
    return this.fetchApi(`/pickup-points${suffix}`);
  }

  // Devices
  async getDevices(): Promise<any[]> {
    const payload = await this.fetchApi<{ items?: any[] }>('/devices?page=1&page_size=200');
    return Array.isArray(payload?.items) ? payload.items : [];
  }

  async getDevice(deviceId: string): Promise<any> {
    return this.fetchApi(`/devices/${deviceId}`);
  }

  async createDevice(payload: any): Promise<any> {
    return this.fetchApi('/devices', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async updateDevice(deviceId: string, payload: any): Promise<any> {
    return this.fetchApi(`/devices/${deviceId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  async deleteDevice(deviceId: string): Promise<any> {
    return this.fetchApi(`/devices/${deviceId}`, {
      method: 'DELETE',
    });
  }

  // Vehicles
  async getVehicles(): Promise<any[]> {
    const payload = await this.fetchApi<{ items?: any[] }>('/vehicles?page=1&page_size=200');
    return Array.isArray(payload?.items) ? payload.items : [];
  }

  async getVehicle(vehicleId: string): Promise<any> {
    return this.fetchApi(`/vehicles/${vehicleId}`);
  }

  async createVehicle(payload: any): Promise<any> {
    return this.fetchApi('/vehicles', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async updateVehicle(vehicleId: string, payload: any): Promise<any> {
    return this.fetchApi(`/vehicles/${vehicleId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  async deleteVehicle(vehicleId: string): Promise<any> {
    return this.fetchApi(`/vehicles/${vehicleId}`, {
      method: 'DELETE',
    });
  }

  // Device Assignments
  async getDeviceAssignments(): Promise<any[]> {
    const payload = await this.fetchApi<{ items?: any[] }>('/device-assignments?page=1&page_size=200');
    return Array.isArray(payload?.items) ? payload.items : [];
  }

  async createDeviceAssignment(payload: {
    device_id: string;
    vehicle_id: string;
    assigned_from?: string;
    remarks?: string;
  }): Promise<any> {
    return this.fetchApi('/device-assignments', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async reassignDevice(deviceId: string, vehicleId: string, remarks?: string): Promise<any> {
    const params = new URLSearchParams();
    params.set('vehicle_id', vehicleId);
    if (remarks) params.set('remarks', remarks);
    return this.fetchApi(`/device-assignments/${deviceId}?${params.toString()}`, {
      method: 'PUT',
    });
  }

  async unassignDevice(deviceId: string, remarks?: string): Promise<any> {
    const suffix = remarks ? `?remarks=${encodeURIComponent(remarks)}` : '';
    return this.fetchApi(`/device-assignments/${deviceId}${suffix}`, {
      method: 'DELETE',
    });
  }

  async createPickupPoint(payload: any): Promise<any> {
    return this.fetchApi('/pickup-points', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async updatePickupPoint(pickupPointId: string, payload: any): Promise<any> {
    return this.fetchApi(`/pickup-points/${pickupPointId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  async deletePickupPoint(pickupPointId: string): Promise<any> {
    return this.fetchApi(`/pickup-points/${pickupPointId}`, {
      method: 'DELETE',
    });
  }

  // Authentication
  async login(email: string, password: string): Promise<any> {
    return this.fetchApi('/auth/login-json', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  }

  async register(userData: { email: string; password: string; name: string; role?: string }): Promise<any> {
    return this.fetchApi('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  }

  async logout(refreshToken: string): Promise<any> {
    return this.fetchApi('/v1/auth/logout', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  }

  async getCurrentUser(token: string): Promise<any> {
    return this.fetchApi('/auth/me', {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
  }

  async getUsers(): Promise<any[]> {
    return this.fetchApi('/auth/users');
  }

  // Tickets
  async getTickets(filters?: { status?: string; priority?: string; category?: string }): Promise<any[]> {
    const suffix = this.toQueryString(filters);
    return this.fetchApi(`/tickets${suffix}`);
  }

  // Drivers
  async getDrivers(): Promise<any[]> {
    try {
      return await this.fetchApi('/drivers');
    } catch (error) {
      console.warn('Drivers API unavailable, continuing with empty driver list.', error);
      return [];
    }
  }

  async getDriver(driverId: string): Promise<any> {
    return this.fetchApi(`/drivers/${driverId}`);
  }

  async createDriver(payload: any): Promise<any> {
    return this.fetchApi('/drivers', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async updateDriver(driverId: string, payload: any): Promise<any> {
    return this.fetchApi(`/drivers/${driverId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  async deleteDriver(driverId: string): Promise<any> {
    return this.fetchApi(`/drivers/${driverId}`, {
      method: 'DELETE',
    });
  }

  async getTicket(ticketId: string): Promise<any> {
    return this.fetchApi(`/tickets/${ticketId}`);
  }

  async createTicket(ticketData: any): Promise<any> {
    return this.fetchApi('/tickets/', {
      method: 'POST',
      body: JSON.stringify(ticketData),
    });
  }

  async updateTicket(ticketId: string, ticketData: any): Promise<any> {
    return this.fetchApi(`/tickets/${ticketId}`, {
      method: 'PUT',
      body: JSON.stringify(ticketData),
    });
  }

  async getTicketComments(ticketId: string): Promise<any[]> {
    return this.fetchApi(`/tickets/${ticketId}/comments`);
  }

  async addTicketComment(ticketId: string, comment: string, token?: string): Promise<any> {
    const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
    return this.fetchApi(`/tickets/${ticketId}/comments`, {
      method: 'POST',
      body: JSON.stringify({ comment, is_internal: false }),
      headers,
    });
  }

  async getTicketStatistics(): Promise<any> {
    return this.fetchApi('/tickets/statistics/summary');
  }

  // Twitter/Social Media
  async getTwitterMentions(filters?: { sentiment?: string; category?: string }): Promise<any[]> {
    const params = new URLSearchParams(filters as Record<string, string>);
    return this.fetchApi(`/social-media/twitter-mentions?${params.toString()}`);
  }

  async getTwitterStatistics(): Promise<any> {
    return this.fetchApi('/social-media/twitter-mentions/statistics/summary');
  }

  async respondToTwitterMention(mentionId: string, responseText: string): Promise<any> {
    return this.fetchApi(`/social-media/twitter-mentions/${mentionId}/respond`, {
      method: 'PUT',
      body: JSON.stringify({ response_text: responseText }),
    });
  }

  // Analytics
  async getAnalytics(filters?: { metric_type?: string; zone_id?: string }): Promise<any[]> {
    const params = new URLSearchParams(filters as Record<string, string>);
    return this.fetchApi(`/analytics/?${params.toString()}`);
  }

  async getPerformanceOverview(): Promise<any> {
    return this.fetchApi('/analytics/performance/overview');
  }

  async getZoneWisePerformance(): Promise<any[]> {
    return this.fetchApi('/analytics/performance/zone-wise');
  }

  async getVendorWisePerformance(): Promise<any[]> {
    return this.fetchApi('/analytics/performance/vendor-wise');
  }

  async getMaintenancePredictions(): Promise<any[]> {
    return this.fetchApi('/analytics/predictions/maintenance');
  }

  async getCollectionRateTrends(): Promise<any[]> {
    return this.fetchApi('/analytics/trends/collection-rate');
  }

  async getAnalyticsReport(period: 'daily' | 'monthly' | 'quarterly' | 'half-yearly' | 'annual', filters?: {
    date_from?: string;
    date_to?: string;
    vehicle_id?: string;
    vendor_id?: string;
  }): Promise<any> {
    const suffix = this.toQueryString(filters);
    return this.fetchApi(`/analytics/reports/${period}${suffix}`);
  }

  async getAnalyticsTrips(filters?: {
    started_from?: string;
    started_to?: string;
    vehicle_id?: string;
    vendor_id?: string;
    limit?: string;
  }): Promise<any> {
    const suffix = this.toQueryString(filters);
    return this.fetchApi(`/analytics/trips${suffix}`);
  }

  async getAnalyticsIdleSegments(filters?: {
    started_from?: string;
    started_to?: string;
    vehicle_id?: string;
    vendor_id?: string;
    limit?: string;
  }): Promise<any> {
    const suffix = this.toQueryString(filters);
    return this.fetchApi(`/analytics/idle-segments${suffix}`);
  }

  async getAnalyticsOverspeedEvents(filters?: {
    from_ts?: string;
    to_ts?: string;
    vehicle_id?: string;
    vendor_id?: string;
    limit?: string;
  }): Promise<any> {
    const suffix = this.toQueryString(filters);
    return this.fetchApi(`/analytics/overspeed-events${suffix}`);
  }

  async getAnalyticsGeofenceEvents(filters?: {
    from_ts?: string;
    to_ts?: string;
    vehicle_id?: string;
    event_type?: string;
    limit?: string;
  }): Promise<any> {
    const suffix = this.toQueryString(filters);
    return this.fetchApi(`/analytics/geofence-events${suffix}`);
  }

  async getAnalyticsVehicleStates(filters?: {
    vehicle_id?: string;
    limit?: string;
  }): Promise<any> {
    const suffix = this.toQueryString(filters);
    return this.fetchApi(`/analytics/vehicle-state${suffix}`);
  }

  async getAnalyticsGeofenceSummary(filters?: {
    from_ts?: string;
    to_ts?: string;
    vehicle_id?: string;
    geofence_code?: string;
    limit?: string;
  }): Promise<any> {
    const suffix = this.toQueryString(filters);
    return this.fetchApi(`/analytics/geofence-summary${suffix}`);
  }

  async getAnalyticsVehicleUtilization(filters?: {
    date_from?: string;
    date_to?: string;
    vehicle_id?: string;
    vendor_id?: string;
    limit?: string;
  }): Promise<any> {
    const suffix = this.toQueryString(filters);
    return this.fetchApi(`/analytics/vehicle-utilization${suffix}`);
  }

  async getAnalyticsRouteDeviationSummary(filters?: {
    from_ts?: string;
    to_ts?: string;
    vehicle_id?: string;
    limit?: string;
  }): Promise<any> {
    const suffix = this.toQueryString(filters);
    return this.fetchApi(`/analytics/route-deviation-summary${suffix}`);
  }

  async getAnalyticsFuelEfficiency(filters?: {
    date_from?: string;
    date_to?: string;
    vehicle_id?: string;
    vendor_id?: string;
    limit?: string;
  }): Promise<any> {
    const suffix = this.toQueryString(filters);
    return this.fetchApi(`/analytics/fuel-efficiency${suffix}`);
  }

  async getAnalyticsSpeedAnalysis(filters?: {
    from_ts?: string;
    to_ts?: string;
    vehicle_id?: string;
    vendor_id?: string;
    limit?: string;
  }): Promise<any> {
    const suffix = this.toQueryString(filters);
    return this.fetchApi(`/analytics/speed-analysis${suffix}`);
  }

  async getAnalyticsIdleSummary(filters?: {
    date_from?: string;
    date_to?: string;
    vehicle_id?: string;
    vendor_id?: string;
    limit?: string;
  }): Promise<any> {
    const suffix = this.toQueryString(filters);
    return this.fetchApi(`/analytics/idle-summary${suffix}`);
  }

  async getAnalyticsPickupPointCrossings(filters?: {
    from_ts?: string;
    to_ts?: string;
    vehicle_id?: string;
    route_id?: string;
    pickup_point_id?: string;
    limit?: string;
  }): Promise<any> {
    const suffix = this.toQueryString(filters);
    return this.fetchApi(`/analytics/pickup-point-crossings${suffix}`);
  }

  // GTC Checkpoints
  async getGtcCheckpoints(filters?: {
    truck_id?: string;
    date?: string;
    date_from?: string;
    date_to?: string;
  }): Promise<GtcCheckpointEntry[]> {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value) {
          params.append(key, value);
        }
      });
    }
    const query = params.toString();
    const suffix = query ? `?${query}` : "";
    return this.fetchApi(`/gtc-checkpoints${suffix}`);
  }

  async createGtcCheckpoint(payload: {
    truck_id: string;
    arrived_at?: string;
    is_dry: boolean;
    is_wet: boolean;
    is_metal: boolean;
    is_plastic: boolean;
    is_sanitary: boolean;
    truck_cleanliness_score?: number | null;
    gtc_cleanliness_score?: number | null;
    remarks?: string | null;
  }): Promise<GtcCheckpointEntry> {
    return this.fetchApi('/gtc-checkpoints', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }
}

export const apiService = new ApiService();
