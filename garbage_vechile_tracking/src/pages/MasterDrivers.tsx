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
import { apiService } from '@/services/api';
import { useQueryClient } from '@tanstack/react-query';
import { Driver } from '@/data/masterData';
import { Plus, Search, Edit, Trash2, Phone, Mail, User, Download, Loader2, UserCheck } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';

const UNASSIGNED_TRUCK_VALUE = 'unassigned';

function normalizeDriver(driver: any): Driver {
  return {
    id: String(driver?.id ?? ''),
    name: String(driver?.name ?? ''),
    phone: String(driver?.phone ?? ''),
    email: String(driver?.email ?? ''),
    licenseNumber: String(driver?.licenseNumber ?? driver?.license_number ?? ''),
    licenseExpiry: String(driver?.licenseExpiry ?? driver?.license_expiry ?? ''),
    address: String(driver?.address ?? ''),
    status: (driver?.status === 'inactive' || driver?.status === 'on_leave') ? driver.status : 'active',
    assignedTruckId: driver?.assignedTruckId ?? driver?.assigned_truck_id ?? undefined,
    joinDate: String(driver?.joinDate ?? driver?.join_date ?? new Date().toISOString().split('T')[0]),
    emergencyContact: String(driver?.emergencyContact ?? driver?.emergency_contact ?? ''),
  };
}

const getTruckLabel = (truck: any) =>
  String(
    truck?.registrationNumber ||
    truck?.registration_number ||
    truck?.vehicle_number ||
    truck?.vehicleNumber ||
    truck?.truckNumber ||
    truck?.id ||
    ''
  );

const isUuid = (value: unknown) =>
  typeof value === 'string' &&
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);

export default function MasterDrivers() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  
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
    setDrivers((driversFromAPI as any[]).map(normalizeDriver));
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
    assignedTruckId: undefined,
    joinDate: new Date().toISOString().split('T')[0],
    emergencyContact: ''
  });

  const assignableTrucks = trucks.filter((truck) => isUuid(String(truck?.id ?? '')));

  const getTruckInfo = (truckId?: string) => {
    if (!truckId) return 'Not Assigned';
    const truck = trucks.find(t => String(t.id) === String(truckId));
    return truck ? getTruckLabel(truck) : 'Unknown';
  };

  const filteredDrivers = drivers.filter(driver => {
    const matchesSearch = driver.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         driver.phone.includes(searchQuery) ||
                         driver.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         driver.licenseNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         getTruckInfo(driver.assignedTruckId).toLowerCase().includes(searchQuery.toLowerCase());
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

  const handleSubmit = async () => {
    try {
      const payload = {
        name: formData.name,
        phone: formData.phone,
        email: formData.email,
        licenseNumber: formData.licenseNumber,
        licenseExpiry: formData.licenseExpiry,
        address: formData.address,
        status: formData.status,
        assignedTruckId: formData.assignedTruckId || null,
        joinDate: formData.joinDate,
        emergencyContact: formData.emergencyContact,
      };

      if (editingDriver) {
        const updated = normalizeDriver(await apiService.updateDriver(editingDriver.id, payload));
        setDrivers(prev => prev.map(d => d.id === editingDriver.id ? updated : d));
        toast({ title: "Driver Updated", description: "Driver information has been updated." });
      } else {
        const created = normalizeDriver(await apiService.createDriver(payload));
        setDrivers(prev => [...prev, created]);
        toast({ title: "Driver Added", description: "New driver has been added successfully." });
      }
      await queryClient.invalidateQueries({ queryKey: ['drivers'] });
      resetForm();
    } catch (error) {
      toast({
        title: "Unable to save driver",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleDelete = async (id: string) => {
    const driver = drivers.find((item) => item.id === id);
    if (!window.confirm(`Delete driver ${driver?.name || id}? This cannot be undone.`)) {
      return;
    }
    try {
      await apiService.deleteDriver(id);
      setDrivers(prev => prev.filter(d => d.id !== id));
      await queryClient.invalidateQueries({ queryKey: ['drivers'] });
      toast({ title: "Driver Deleted", description: "Driver has been removed from the system." });
    } catch (error) {
      toast({
        title: "Unable to delete driver",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      phone: '',
      email: '',
      licenseNumber: '',
      licenseExpiry: '',
      address: '',
      status: 'active',
      assignedTruckId: undefined,
      joinDate: new Date().toISOString().split('T')[0],
      emergencyContact: ''
    });
    setEditingDriver(null);
    setIsAddDialogOpen(false);
  };

  const openEditDialog = (driver: Driver) => {
    setEditingDriver(driver);
    setFormData(driver);
    setIsAddDialogOpen(true);
  };

  const exportToCSV = () => {
    const headers = ['ID', 'Name', 'Phone', 'Email', 'License Number', 'License Expiry', 'Join Date', 'Status', 'Assigned Truck', 'Emergency Contact', 'Address'];
    const rows = filteredDrivers.map(d => [d.id, d.name, d.phone, d.email, d.licenseNumber, d.licenseExpiry, d.joinDate, d.status, getTruckInfo(d.assignedTruckId), d.emergencyContact, d.address]);
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
                    <Label>Join Date</Label>
                    <Input type="date" value={formData.joinDate} onChange={(e) => setFormData({ ...formData, joinDate: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Assigned Truck</Label>
                    <Select
                      value={formData.assignedTruckId || UNASSIGNED_TRUCK_VALUE}
                      onValueChange={(value) => setFormData({
                        ...formData,
                        assignedTruckId: value === UNASSIGNED_TRUCK_VALUE ? undefined : value,
                      })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder={isLoadingTrucks ? 'Loading trucks...' : 'Select truck'} />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value={UNASSIGNED_TRUCK_VALUE}>Not Assigned</SelectItem>
                        {assignableTrucks.map((truck) => (
                          <SelectItem key={String(truck.id)} value={String(truck.id)}>
                            {getTruckLabel(truck)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
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
                <Button onClick={handleSubmit} disabled={!formData.name?.trim()}>
                  {editingDriver ? 'Update' : 'Add'} Driver
                </Button>
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
              <Input placeholder="Search by name, phone, email, license, truck..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-10" />
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
                <TableHead>Employment</TableHead>
                <TableHead>Address</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoadingDrivers && (
                <TableRow>
                  <TableCell colSpan={8} className="py-8 text-center text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin inline mr-2" />
                    Loading drivers...
                  </TableCell>
                </TableRow>
              )}
              {!isLoadingDrivers && filteredDrivers.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="py-8 text-center text-muted-foreground">
                    No drivers found.
                  </TableCell>
                </TableRow>
              )}
              {!isLoadingDrivers && filteredDrivers.map((driver) => (
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
                  <TableCell>
                    <div className="text-sm">Joined: {driver.joinDate || '-'}</div>
                    <div className="text-xs text-muted-foreground">Emergency: {driver.emergencyContact || '-'}</div>
                  </TableCell>
                  <TableCell className="max-w-[220px] truncate text-sm text-muted-foreground">
                    {driver.address || '-'}
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
