// Driver Master Data

export interface Driver {
  id: string;
  name: string;
  phone: string;
  email: string;
  licenseNumber: string;
  licenseExpiry: string;
  address: string;
  status: 'active' | 'inactive' | 'on_leave';
  assignedTruckId?: string;
  joinDate: string;
  emergencyContact: string;
}

// 12 Drivers - 9 assigned to trucks, 2 assigned to spares, 1 on leave
export const drivers: Driver[] = [
  {
    id: 'DRV001',
    name: 'Rajesh Kumar',
    phone: '+91 9876543210',
    email: 'rajesh.kumar@email.com',
    licenseNumber: 'MH12 2020 0001234',
    licenseExpiry: '2025-06-15',
    address: '123, Kharadi, Pune',
    status: 'active',
    assignedTruckId: 'TRK001',
    joinDate: '2020-03-15',
    emergencyContact: '+91 9876543211'
  },
  {
    id: 'DRV002',
    name: 'Suresh Patil',
    phone: '+91 9876543220',
    email: 'suresh.patil@email.com',
    licenseNumber: 'MH12 2019 0005678',
    licenseExpiry: '2024-12-20',
    address: '456, Hadapsar, Pune',
    status: 'active',
    assignedTruckId: 'TRK002',
    joinDate: '2019-08-10',
    emergencyContact: '+91 9876543221'
  },
  {
    id: 'DRV003',
    name: 'Amit Sharma',
    phone: '+91 9876543230',
    email: 'amit.sharma@email.com',
    licenseNumber: 'MH12 2021 0009012',
    licenseExpiry: '2026-03-25',
    address: '789, Viman Nagar, Pune',
    status: 'active',
    assignedTruckId: 'TRK003',
    joinDate: '2021-01-20',
    emergencyContact: '+91 9876543231'
  },
  {
    id: 'DRV004',
    name: 'Prakash Jadhav',
    phone: '+91 9876543240',
    email: 'prakash.jadhav@email.com',
    licenseNumber: 'MH12 2018 0003456',
    licenseExpiry: '2024-09-10',
    address: '321, Koregaon Park, Pune',
    status: 'active',
    assignedTruckId: 'TRK004',
    joinDate: '2018-05-05',
    emergencyContact: '+91 9876543241'
  },
  {
    id: 'DRV005',
    name: 'Vijay Deshmukh',
    phone: '+91 9876543250',
    email: 'vijay.deshmukh@email.com',
    licenseNumber: 'MH12 2022 0007890',
    licenseExpiry: '2027-01-30',
    address: '654, Aundh, Pune',
    status: 'active',
    assignedTruckId: 'TRK005',
    joinDate: '2022-06-15',
    emergencyContact: '+91 9876543251'
  },
  {
    id: 'DRV006',
    name: 'Manoj Patil',
    phone: '+91 9876543260',
    email: 'manoj.patil@email.com',
    licenseNumber: 'MH12 2020 0004567',
    licenseExpiry: '2025-08-20',
    address: '987, Baner, Pune',
    status: 'active',
    assignedTruckId: 'TRK006',
    joinDate: '2020-09-12',
    emergencyContact: '+91 9876543261'
  },
  {
    id: 'DRV007',
    name: 'Ravi Deshmukh',
    phone: '+91 9876543270',
    email: 'ravi.deshmukh@email.com',
    licenseNumber: 'MH12 2019 0008901',
    licenseExpiry: '2025-04-15',
    address: '147, Kothrud, Pune',
    status: 'active',
    assignedTruckId: 'TRK007',
    joinDate: '2019-11-25',
    emergencyContact: '+91 9876543271'
  },
  {
    id: 'DRV008',
    name: 'Vikram Singh',
    phone: '+91 9876543280',
    email: 'vikram.singh@email.com',
    licenseNumber: 'MH12 2021 0002345',
    licenseExpiry: '2026-02-10',
    address: '258, Shivaji Nagar, Pune',
    status: 'active',
    assignedTruckId: 'TRK008',
    joinDate: '2021-04-18',
    emergencyContact: '+91 9876543281'
  },
  {
    id: 'DRV009',
    name: 'Deepak Jadhav',
    phone: '+91 9876543290',
    email: 'deepak.jadhav@email.com',
    licenseNumber: 'MH12 2020 0006789',
    licenseExpiry: '2025-11-05',
    address: '369, Deccan, Pune',
    status: 'active',
    assignedTruckId: 'TRK009',
    joinDate: '2020-07-22',
    emergencyContact: '+91 9876543291'
  },
  // Spare drivers
  {
    id: 'DRV-SPR-001',
    name: 'Ganesh More',
    phone: '+91 9876543300',
    email: 'ganesh.more@email.com',
    licenseNumber: 'MH12 2021 0001111',
    licenseExpiry: '2026-05-20',
    address: '111, Kharadi, Pune',
    status: 'active',
    assignedTruckId: 'TRK-SPR-001',
    joinDate: '2021-08-15',
    emergencyContact: '+91 9876543301'
  },
  {
    id: 'DRV-SPR-002',
    name: 'Santosh Kulkarni',
    phone: '+91 9876543310',
    email: 'santosh.kulkarni@email.com',
    licenseNumber: 'MH12 2022 0002222',
    licenseExpiry: '2027-03-15',
    address: '222, Viman Nagar, Pune',
    status: 'active',
    assignedTruckId: 'TRK-SPR-002',
    joinDate: '2022-02-10',
    emergencyContact: '+91 9876543311'
  },
  // On leave driver
  {
    id: 'DRV010',
    name: 'Rahul Shinde',
    phone: '+91 9876543320',
    email: 'rahul.shinde@email.com',
    licenseNumber: 'MH12 2019 0003333',
    licenseExpiry: '2025-09-30',
    address: '333, Hadapsar, Pune',
    status: 'on_leave',
    joinDate: '2019-05-10',
    emergencyContact: '+91 9876543321'
  }
];

// Helper functions
export const getDriverById = (driverId: string): Driver | undefined => drivers.find(d => d.id === driverId);
export const getDriverByTruckId = (truckId: string): Driver | undefined => drivers.find(d => d.assignedTruckId === truckId);
export const getActiveDrivers = (): Driver[] => drivers.filter(d => d.status === 'active');
