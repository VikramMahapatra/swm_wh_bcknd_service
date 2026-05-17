// Zone and Ward Master Data

export interface Zone {
  id: string;
  name: string;
  code: string;
  description: string;
  supervisorName: string;
  supervisorPhone: string;
  totalWards: number;
  status: 'active' | 'inactive';
}

export interface Ward {
  id: string;
  name: string;
  code: string;
  zoneId: string;
  population: number;
  area: number;
  totalPickupPoints: number;
  status: 'active' | 'inactive';
}

// 5 Zones covering the city
export const zones: Zone[] = [
  { id: 'ZN001', name: 'North Zone', code: 'NZ', description: 'Northern area including Aundh, Baner, Pashan', supervisorName: 'Arvind Rao', supervisorPhone: '+91 9555444333', totalWards: 3, status: 'active' },
  { id: 'ZN002', name: 'South Zone', code: 'SZ', description: 'Southern area including Katraj, Kondhwa, Hadapsar', supervisorName: 'Priya Sharma', supervisorPhone: '+91 9555444334', totalWards: 2, status: 'active' },
  { id: 'ZN003', name: 'East Zone', code: 'EZ', description: 'Eastern area including Kharadi, Viman Nagar, Wadgaon Sheri', supervisorName: 'Kiran Patil', supervisorPhone: '+91 9555444335', totalWards: 3, status: 'active' },
  { id: 'ZN004', name: 'West Zone', code: 'WZ', description: 'Western area including Kothrud, Karve Nagar, Warje', supervisorName: 'Sanjay Kulkarni', supervisorPhone: '+91 9555444336', totalWards: 2, status: 'active' },
  { id: 'ZN005', name: 'Central Zone', code: 'CZ', description: 'Central business district including Shivaji Nagar, Deccan', supervisorName: 'Meera Joshi', supervisorPhone: '+91 9555444337', totalWards: 2, status: 'active' }
];

// 12 Wards distributed across zones
export const wards: Ward[] = [
  // North Zone - 3 wards
  { id: 'WD001', name: 'Aundh', code: 'AND', zoneId: 'ZN001', population: 52000, area: 14.8, totalPickupPoints: 45, status: 'active' },
  { id: 'WD002', name: 'Baner', code: 'BNR', zoneId: 'ZN001', population: 48000, area: 11.5, totalPickupPoints: 40, status: 'active' },
  { id: 'WD003', name: 'Pashan', code: 'PSN', zoneId: 'ZN001', population: 35000, area: 9.2, totalPickupPoints: 30, status: 'active' },
  
  // South Zone - 2 wards
  { id: 'WD004', name: 'Hadapsar', code: 'HDP', zoneId: 'ZN002', population: 65000, area: 18.2, totalPickupPoints: 55, status: 'active' },
  { id: 'WD005', name: 'Kondhwa', code: 'KDW', zoneId: 'ZN002', population: 42000, area: 12.0, totalPickupPoints: 35, status: 'active' },
  
  // East Zone - 3 wards (Main operational area - Kharadi)
  { id: 'WD006', name: 'Kharadi', code: 'KHR', zoneId: 'ZN003', population: 45000, area: 12.5, totalPickupPoints: 50, status: 'active' },
  { id: 'WD007', name: 'Viman Nagar', code: 'VMN', zoneId: 'ZN003', population: 38000, area: 8.5, totalPickupPoints: 40, status: 'active' },
  { id: 'WD008', name: 'Wadgaon Sheri', code: 'WGS', zoneId: 'ZN003', population: 32000, area: 7.8, totalPickupPoints: 30, status: 'active' },
  
  // West Zone - 2 wards
  { id: 'WD009', name: 'Kothrud', code: 'KTR', zoneId: 'ZN004', population: 58000, area: 15.5, totalPickupPoints: 48, status: 'active' },
  { id: 'WD010', name: 'Warje', code: 'WRJ', zoneId: 'ZN004', population: 40000, area: 10.2, totalPickupPoints: 32, status: 'active' },
  
  // Central Zone - 2 wards
  { id: 'WD011', name: 'Shivaji Nagar', code: 'SJN', zoneId: 'ZN005', population: 32000, area: 5.8, totalPickupPoints: 38, status: 'active' },
  { id: 'WD012', name: 'Deccan', code: 'DCN', zoneId: 'ZN005', population: 28000, area: 4.5, totalPickupPoints: 30, status: 'active' }
];

// Helper functions
export const getWardsByZone = (zoneId: string): Ward[] => wards.filter(w => w.zoneId === zoneId);
export const getZoneById = (zoneId: string): Zone | undefined => zones.find(z => z.id === zoneId);
export const getWardById = (wardId: string): Ward | undefined => wards.find(w => w.id === wardId);
