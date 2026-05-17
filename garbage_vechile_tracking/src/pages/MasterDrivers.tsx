import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useToast } from '@/hooks/use-toast';
import { useDrivers, useTrucks } from '@/hooks/useDataQueries';
import { Driver } from '@/data/masterData';
import { Plus, Search, Edit, Trash2, Phone, Mail, User, Download, Loader2, UserCheck } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';

export default function MasterDrivers() {
  const { toast } = useToast();
  
  // Fetch drivers from API
  const { data: driversFromAPI = [], isLoading: isLoadingDrivers, error: driversError } = useDrivers();
  const { data: trucksFromAPI = [], isLoading: isLoadingTrucks } = useTrucks();
  
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [trucks, setTrucks] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [editingDriver, setEditingDriver] = useState<Driver | null>(null);
  
  // Initialize drivers from API
  useEffect(() => {
    setDrivers(driversFromAPI);
  }, [driversFromAPI]);

  // Initialize trucks from API
  useEffect(() => {
    setTrucks(trucksFromAPI);
  }, [trucksFromAPI]);
  
  const [formData, setFormData] = useState<Partial<Driver>>({
    name: '',
    phone: '',
    email: '',
    licenseNumber: '',
    licenseExpiry: '',
    address: '',
    status: 'active',
    emergencyContact: ''
  });

  const filteredDrivers = drivers.filter(driver => {
    const matchesSearch = driver.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         driver.phone.includes(searchQuery) ||
                         driver.licenseNumber.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || driver.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active': return <Badge className="bg-success/20 text-success border-success/30">Active</Badge>;
      case 'inactive': return <Badge variant="secondary">Inactive</Badge>;
      case 'on_leave': return <Badge className="bg-warning/20 text-warning border-warning/30">On Leave</Badge>;
      default: return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getTruckInfo = (truckId?: string) => {
    if (!truckId) return 'Not Assigned';
    const truck = trucks.find(t => t.id === truckId);
    return truck ? truck.registrationNumber : 'Unknown';
  };

  const handleSubmit = () => {
    if (editingDriver) {
      setDrivers(prev => prev.map(d => d.id === editingDriver.id ? { ...d, ...formData } as Driver : d));
      toast({ title: "Driver Updated", description: "Driver information has been updated." });
    } else {
      const newDriver: Driver = {
        ...formData as Driver,
        id: `DRV${String(drivers.length + 1).padStart(3, '0')}`,
        joinDate: new Date().toISOString().split('T')[0]
      };
      setDrivers(prev => [...prev, newDriver]);
      toast({ title: "Driver Added", description: "New driver has been added successfully." });
    }
    resetForm();
  };

  const handleDelete = (id: string) => {
    setDrivers(prev => prev.filter(d => d.id !== id));
    toast({ title: "Driver Deleted", description: "Driver has been removed from the system." });
  };

  const resetForm = () => {
    setFormData({ name: '', phone: '', email: '', licenseNumber: '', licenseExpiry: '', address: '', status: 'active', emergencyContact: '' });
    setEditingDriver(null);
    setIsAddDialogOpen(false);
  };

  const openEditDialog = (driver: Driver) => {
    setEditingDriver(driver);
    setFormData(driver);
    setIsAddDialogOpen(true);
  };

  const exportToCSV = () => {
    const headers = ['ID', 'Name', 'Phone', 'Email', 'License Number', 'License Expiry', 'Status', 'Assigned Truck'];
    const rows = filteredDrivers.map(d => [d.id, d.name, d.phone, d.email, d.licenseNumber, d.licenseExpiry, d.status, getTruckInfo(d.assignedTruckId)]);
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'drivers.csv';
    a.click();
  };

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      <PageHeader
        category="Master Data"
        title="Driver Management"
        description="Manage driver information, assignments, and licensing"
        icon={UserCheck}
        actions={
          <>
            <Button variant="outline" onClick={exportToCSV}>
              <Download className="h-4 w-4 mr-2" /> Export
            </Button>
            <Dialog open={isAddDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); setIsAddDialogOpen(open); }}>
              <DialogTrigger asChild>
                <Button><Plus className="h-4 w-4 mr-2" /> Add Driver</Button>
              </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>{editingDriver ? 'Edit Driver' : 'Add New Driver'}</DialogTitle>
                <DialogDescription>Enter the driver details below</DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Full Name</Label>
                    <Input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Phone Number</Label>
                    <Input value={formData.phone} onChange={(e) => setFormData({ ...formData, phone: e.target.value })} />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Email</Label>
                    <Input type="email" value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Emergency Contact</Label>
                    <Input value={formData.emergencyContact} onChange={(e) => setFormData({ ...formData, emergencyContact: e.target.value })} />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>License Number</Label>
                    <Input value={formData.licenseNumber} onChange={(e) => setFormData({ ...formData, licenseNumber: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>License Expiry</Label>
                    <Input type="date" value={formData.licenseExpiry} onChange={(e) => setFormData({ ...formData, licenseExpiry: e.target.value })} />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Address</Label>
                    <Input value={formData.address} onChange={(e) => setFormData({ ...formData, address: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Status</Label>
                    <Select value={formData.status} onValueChange={(value) => setFormData({ ...formData, status: value as Driver['status'] })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="active">Active</SelectItem>
                        <SelectItem value="inactive">Inactive</SelectItem>
                        <SelectItem value="on_leave">On Leave</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={resetForm}>Cancel</Button>
                <Button onClick={handleSubmit}>{editingDriver ? 'Update' : 'Add'} Driver</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          </>
        }
      />

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Drivers</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{drivers.length}</div>
          </CardContent>
        </Card>
        <Card className="bg-success/10 border-success/30">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-success">Active</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-success">{drivers.filter(d => d.status === 'active').length}</div>
          </CardContent>
        </Card>
        <Card className="bg-warning/10 border-warning/30">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-warning">On Leave</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-warning">{drivers.filter(d => d.status === 'on_leave').length}</div>
          </CardContent>
        </Card>
        <Card className="bg-muted border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Unassigned</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{drivers.filter(d => !d.assignedTruckId).length}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="bg-card/50 border-border/50">
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Search by name, phone, license..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-10" />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]"><SelectValue placeholder="Filter by status" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
                <SelectItem value="on_leave">On Leave</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card className="bg-card/50 border-border/50">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Driver</TableHead>
                <TableHead>Contact</TableHead>
                <TableHead>License</TableHead>
                <TableHead>Assigned Truck</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredDrivers.map((driver) => (
                <TableRow key={driver.id}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                        <User className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <div className="font-medium">{driver.name}</div>
                        <div className="text-sm text-muted-foreground">{driver.id}</div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      <div className="flex items-center gap-1 text-sm"><Phone className="h-3 w-3" /> {driver.phone}</div>
                      <div className="flex items-center gap-1 text-sm text-muted-foreground"><Mail className="h-3 w-3" /> {driver.email}</div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm">{driver.licenseNumber}</div>
                    <div className="text-xs text-muted-foreground">Exp: {driver.licenseExpiry}</div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{getTruckInfo(driver.assignedTruckId)}</Badge>
                  </TableCell>
                  <TableCell>{getStatusBadge(driver.status)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button variant="ghost" size="icon" onClick={() => openEditDialog(driver)}><Edit className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" className="text-destructive" onClick={() => handleDelete(driver.id)}><Trash2 className="h-4 w-4" /></Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
