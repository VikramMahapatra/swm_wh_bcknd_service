// Tickets and Escalation Configuration

export type TicketStatus = 'open' | 'in_progress' | 'pending' | 'resolved' | 'closed';
export type TicketPriority = 'low' | 'medium' | 'high' | 'critical';
export type TicketCategory = 'complaint' | 'maintenance' | 'driver_issue' | 'vehicle_issue' | 'route_issue' | 'pickup_issue' | 'other';

export interface TicketComment {
  id: string;
  ticketId: string;
  author: string;
  content: string;
  createdAt: string;
  isInternal: boolean;
}

export interface Ticket {
  id: string;
  title: string;
  description: string;
  category: TicketCategory;
  priority: TicketPriority;
  status: TicketStatus;
  createdAt: string;
  updatedAt: string;
  dueDate: string;
  assignedTo?: string;
  createdBy: string;
  relatedAlertId?: string;
  relatedTruckId?: string;
  relatedDriverId?: string;
  escalationLevel: number;
  slaBreached: boolean;
  comments: TicketComment[];
}

export interface EscalationLevel {
  level: number;
  role: string;
  name: string;
  email: string;
  phone: string;
  timeoutMinutes: number;
}

export interface EscalationConfig {
  enabled: boolean;
  levels: EscalationLevel[];
}

export interface SLAConfig {
  priority: TicketPriority;
  responseTimeMinutes: number;
  resolutionTimeMinutes: number;
}

// Tickets with proper truck/driver references
export const tickets: Ticket[] = [
  {
    id: 'TKT001',
    title: 'Truck MH-12-AB-1234 - Repeated Route Deviation',
    description: 'Driver has deviated from assigned route 3 times this week. Need investigation.',
    category: 'driver_issue',
    priority: 'high',
    status: 'in_progress',
    createdAt: '2024-03-10T08:30:00Z',
    updatedAt: '2024-03-10T14:20:00Z',
    dueDate: '2024-03-11T17:00:00Z',
    assignedTo: 'Zone Supervisor',
    createdBy: 'System',
    relatedTruckId: 'TRK001',
    relatedDriverId: 'DRV001',
    escalationLevel: 1,
    slaBreached: false,
    comments: [
      { id: 'CMT001', ticketId: 'TKT001', author: 'System', content: 'Auto-generated from route deviation alert', createdAt: '2024-03-10T08:30:00Z', isInternal: true },
      { id: 'CMT002', ticketId: 'TKT001', author: 'Zone Supervisor', content: 'Contacted driver Rajesh Kumar. Says GPS was malfunctioning.', createdAt: '2024-03-10T14:20:00Z', isInternal: false }
    ]
  },
  {
    id: 'TKT002',
    title: 'Missed Pickup at Viman Nagar Ward',
    description: 'Multiple citizen complaints about a missed pickup in Viman Nagar. Needs immediate attention.',
    category: 'pickup_issue',
    priority: 'critical',
    status: 'open',
    createdAt: '2024-03-10T10:15:00Z',
    updatedAt: '2024-03-10T10:15:00Z',
    dueDate: '2024-03-10T14:00:00Z',
    createdBy: 'Twitter Integration',
    relatedAlertId: 'ALT-2024-0160',
    relatedTruckId: 'TRK001',
    escalationLevel: 0,
    slaBreached: true,
    comments: [
      { id: 'CMT003', ticketId: 'TKT002', author: 'Twitter Integration', content: 'Generated from negative tweet @MunicipalGC', createdAt: '2024-03-10T10:15:00Z', isInternal: true }
    ]
  },
  {
    id: 'TKT003',
    title: 'Vehicle TRK004 - Engine Issue & Scheduled Maintenance',
    description: 'Vehicle MH-12-GH-3456 has engine issues. Currently offline. Maintenance required.',
    category: 'maintenance',
    priority: 'high',
    status: 'pending',
    createdAt: '2024-03-09T09:00:00Z',
    updatedAt: '2024-03-10T11:30:00Z',
    dueDate: '2024-03-12T17:00:00Z',
    assignedTo: 'Fleet Manager',
    createdBy: 'System',
    relatedTruckId: 'TRK004',
    relatedDriverId: 'DRV004',
    escalationLevel: 1,
    slaBreached: false,
    comments: [
      { id: 'CMT004', ticketId: 'TKT003', author: 'System', content: 'Auto-generated: Vehicle went offline at 09:45', createdAt: '2024-03-09T09:00:00Z', isInternal: true },
      { id: 'CMT005', ticketId: 'TKT003', author: 'Fleet Manager', content: 'Scheduled for service on March 11. Spare truck TRK-SPR-001 deployed.', createdAt: '2024-03-10T11:30:00Z', isInternal: false }
    ]
  },
  {
    id: 'TKT004',
    title: 'Citizen Complaint - Late Pickup at Baner',
    description: 'Resident reported late garbage collection near Baner Road. Follow up required.',
    category: 'complaint',
    priority: 'medium',
    status: 'resolved',
    createdAt: '2024-03-08T14:00:00Z',
    updatedAt: '2024-03-09T16:45:00Z',
    dueDate: '2024-03-09T14:00:00Z',
    assignedTo: 'Zone Supervisor',
    createdBy: 'Call Center',
    relatedTruckId: 'TRK008',
    relatedDriverId: 'DRV008',
    escalationLevel: 0,
    slaBreached: false,
    comments: [
      { id: 'CMT006', ticketId: 'TKT004', author: 'Call Center', content: 'Citizen call received. Ticket created.', createdAt: '2024-03-08T14:00:00Z', isInternal: false },
      { id: 'CMT007', ticketId: 'TKT004', author: 'Zone Supervisor', content: 'Contacted driver Vikram Singh. Route timing adjusted.', createdAt: '2024-03-09T16:45:00Z', isInternal: false }
    ]
  },
  {
    id: 'TKT005',
    title: 'Route Optimization Request - Aundh Area',
    description: 'Current route RT005 takes 30 mins longer than estimated. Need route review.',
    category: 'route_issue',
    priority: 'low',
    status: 'closed',
    createdAt: '2024-03-05T11:00:00Z',
    updatedAt: '2024-03-07T15:30:00Z',
    dueDate: '2024-03-10T17:00:00Z',
    assignedTo: 'Route Planner',
    createdBy: 'Driver Feedback',
    relatedTruckId: 'TRK005',
    relatedDriverId: 'DRV005',
    escalationLevel: 0,
    slaBreached: false,
    comments: [
      { id: 'CMT008', ticketId: 'TKT005', author: 'Driver', content: 'Traffic congestion near Westend Mall during morning hours - Vijay Deshmukh', createdAt: '2024-03-05T11:00:00Z', isInternal: false },
      { id: 'CMT009', ticketId: 'TKT005', author: 'Route Planner', content: 'Route optimized. Start time adjusted to 5:30 AM', createdAt: '2024-03-07T15:30:00Z', isInternal: false }
    ]
  }
  ,
  {
    id: 'TKT006',
    title: 'GTC Checkpoint - Low Truck Cleanliness Score',
    description: 'Recent GTC checkpoint shows low cleanliness score for TRK003. Request inspection and cleaning.',
    category: 'vehicle_issue',
    priority: 'medium',
    status: 'open',
    createdAt: '2024-03-11T07:45:00Z',
    updatedAt: '2024-03-11T07:45:00Z',
    dueDate: '2024-03-12T12:00:00Z',
    assignedTo: 'Fleet Manager',
    createdBy: 'GTC Checkpoint',
    relatedTruckId: 'TRK003',
    escalationLevel: 0,
    slaBreached: false,
    comments: [
      { id: 'CMT010', ticketId: 'TKT006', author: 'GTC Checkpoint', content: 'Score recorded below 5.0', createdAt: '2024-03-11T07:45:00Z', isInternal: true }
    ]
  },
  {
    id: 'TKT007',
    title: 'Driver Report - Route Delay Due to Road Closure',
    description: 'Driver reported a temporary road closure affecting RT002. Route timing needs adjustment for today.',
    category: 'route_issue',
    priority: 'low',
    status: 'pending',
    createdAt: '2024-03-11T06:20:00Z',
    updatedAt: '2024-03-11T08:10:00Z',
    dueDate: '2024-03-11T14:00:00Z',
    assignedTo: 'Route Planner',
    createdBy: 'Driver Feedback',
    relatedTruckId: 'TRK002',
    relatedDriverId: 'DRV002',
    escalationLevel: 0,
    slaBreached: false,
    comments: [
      { id: 'CMT011', ticketId: 'TKT007', author: 'Driver', content: 'Detour added 25 minutes to route.', createdAt: '2024-03-11T06:20:00Z', isInternal: false }
    ]
  }
];

export const escalationConfig: EscalationConfig = {
  enabled: true,
  levels: [
    { level: 1, role: 'Supervisor', name: 'Zone Supervisor', email: 'supervisor@municipal.gov', phone: '+91 9111222333', timeoutMinutes: 15 },
    { level: 2, role: 'Manager', name: 'Area Manager', email: 'manager@municipal.gov', phone: '+91 9111222334', timeoutMinutes: 30 },
    { level: 3, role: 'Admin', name: 'City Admin', email: 'admin@municipal.gov', phone: '+91 9111222335', timeoutMinutes: 60 }
  ]
};

export const slaConfig: SLAConfig[] = [
  { priority: 'critical', responseTimeMinutes: 15, resolutionTimeMinutes: 120 },
  { priority: 'high', responseTimeMinutes: 30, resolutionTimeMinutes: 240 },
  { priority: 'medium', responseTimeMinutes: 60, resolutionTimeMinutes: 480 },
  { priority: 'low', responseTimeMinutes: 120, resolutionTimeMinutes: 1440 }
];

// Helper functions
export const getTicketsByTruck = (truckId: string): Ticket[] => tickets.filter(t => t.relatedTruckId === truckId);
export const getTicketsByDriver = (driverId: string): Ticket[] => tickets.filter(t => t.relatedDriverId === driverId);
export const getOpenTickets = (): Ticket[] => tickets.filter(t => t.status === 'open' || t.status === 'in_progress');
