import { API_BASE_URL } from '../config/api';

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
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      });

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
    const payload = await this.fetchApi<RealtimeSnapshotResponse>(`/v1/realtime/trucks?limit=${limit}`, {
      headers: {
        'x-role': 'viewer',
      },
    });
    return Array.isArray(payload.items) ? payload.items : [];
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
    const items = await this.getLiveTrucks();
    return items.filter((truck) => {
      if (filters?.zone_id && truck.zone_id !== filters.zone_id) return false;
      if (filters?.vendor_id && truck.vendor_id !== filters.vendor_id) return false;
      if (filters?.status && truck.current_status !== filters.status) return false;
      return true;
    });
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
    return [];
  }

  async getZone(zoneId: string): Promise<Zone> {
    return {
      id: zoneId,
      name: zoneId,
      code: zoneId,
      description: '',
      supervisor_name: '',
      supervisor_phone: '',
      total_wards: 0,
      status: 'unknown',
    };
  }

  async getZoneWards(zoneId: string): Promise<any[]> {
    void zoneId;
    return [];
  }

  // Alerts
  async getAlerts(filters?: { status?: string; severity?: string; truck_id?: string }): Promise<Alert[]> {
    void filters;
    // Migration mode: alerts backend contract is not available on admin-api yet.
    return [];
  }

  async getActiveAlerts(): Promise<Alert[]> {
    return [];
  }

  async getExpiryAlerts(): Promise<any> {
    return { items: [], total: 0 };
  }

  async getReportsData(): Promise<Record<string, any>> {
    return this.fetchApi('/reports/data');
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
    // SWM-only migration mode: vendor master endpoint is not required for live map flow.
    // Return an empty list to avoid CORS/404 noise from non-migrated screens.
    return [];
  }

  // Routes
  async getRoutes(filters?: { zone_id?: string; ward_id?: string }): Promise<any[]> {
    void filters;
    return [];
  }

  async getRoutePickupPoints(routeId: string): Promise<any[]> {
    return this.fetchApi(`/routes/${routeId}/pickup-points`);
  }

  // Pickup Points
  async getPickupPoints(filters?: { ward_id?: string; route_id?: string }): Promise<any[]> {
    const params = new URLSearchParams(filters as Record<string, string>);
    return this.fetchApi(`/pickup-points/?${params.toString()}`);
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
    const params = new URLSearchParams(filters as Record<string, string>);
    return this.fetchApi(`/tickets/?${params.toString()}`);
  }

  // Drivers
  async getDrivers(): Promise<any[]> {
    return [];
  }

  async getDriver(driverId: string): Promise<any> {
    return this.fetchApi(`/drivers/${driverId}`);
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

  async addTicketComment(ticketId: string, comment: string, token: string): Promise<any> {
    return this.fetchApi(`/tickets/${ticketId}/comments`, {
      method: 'POST',
      body: JSON.stringify({ comment, is_internal: false }),
      headers: {
        'Authorization': `Bearer ${token}`,
      },
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
    return this.fetchApi(`/gtc-checkpoints/${suffix}`);
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
    return this.fetchApi('/gtc-checkpoints/', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }
}

export const apiService = new ApiService();
