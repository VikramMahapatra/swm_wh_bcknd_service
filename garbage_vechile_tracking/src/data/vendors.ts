// Vendor Master Data

export interface Vendor {
  id: string;
  name: string;
  companyName: string;
  phone: string;
  email: string;
  address: string;
  gstNumber: string;
  contractStart: string;
  contractEnd: string;
  status: 'active' | 'inactive' | 'suspended';
  trucksOwned: string[]; // Truck IDs
  spareTrucks: string[]; // Spare truck IDs
  supervisorName: string;
  supervisorPhone: string;
}

// 3 Active Vendors
export const vendors: Vendor[] = [
  {
    id: 'VND001',
    name: 'Mahesh Enterprises',
    companyName: 'Mahesh Fleet Services Pvt Ltd',
    phone: '+91 9888777666',
    email: 'contact@maheshfleet.com',
    address: '100, Industrial Area, Pimpri, Pune',
    gstNumber: '27AABCU9603R1ZX',
    contractStart: '2023-01-01',
    contractEnd: '2025-12-31',
    status: 'active',
    trucksOwned: ['TRK001', 'TRK002', 'TRK003', 'TRK004'],
    spareTrucks: ['TRK-SPR-001'],
    supervisorName: 'Mahesh Kulkarni',
    supervisorPhone: '+91 9888777667'
  },
  {
    id: 'VND002',
    name: 'Green Transport Co',
    companyName: 'Green Transport Solutions',
    phone: '+91 9777666555',
    email: 'info@greentransport.com',
    address: '200, MIDC Bhosari, Pune',
    gstNumber: '27AABCG1234R1ZY',
    contractStart: '2022-06-01',
    contractEnd: '2025-05-31',
    status: 'active',
    trucksOwned: ['TRK005', 'TRK006', 'TRK007'],
    spareTrucks: ['TRK-SPR-002'],
    supervisorName: 'Ramesh Gaikwad',
    supervisorPhone: '+91 9777666556'
  },
  {
    id: 'VND003',
    name: 'City Waste Solutions',
    companyName: 'City Waste Management Services',
    phone: '+91 9666555444',
    email: 'cityswaste@email.com',
    address: '300, Nigdi, Pune',
    gstNumber: '27AABCC5678R1ZZ',
    contractStart: '2023-03-01',
    contractEnd: '2026-02-28',
    status: 'active',
    trucksOwned: ['TRK008', 'TRK009'],
    spareTrucks: [],
    supervisorName: 'Sunil Pawar',
    supervisorPhone: '+91 9666555445'
  }
];

// Helper functions
export const getVendorById = (vendorId: string): Vendor | undefined => vendors.find(v => v.id === vendorId);
export const getActiveVendors = (): Vendor[] => vendors.filter(v => v.status === 'active');
