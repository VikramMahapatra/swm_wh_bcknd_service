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
import { FieldError, RequiredMark, ValidationAlert, errorClass as validationErrorClass } from '@/components/FormValidation';

const UNASSIGNED_TRUCK_VALUE = 'unassigned';
const CREW_TYPE_OPTIONS = [
  { value: 'driver', label: 'Driver' },
  { value: 'helper', label: 'Helper' },
  { value: 'ic_member', label: 'IC Member' },
] as const;

const getCrewTypeLabel = (type?: string) =>
  CREW_TYPE_OPTIONS.find((item) => item.value === type)?.label || 'Driver';

function normalizeDriver(driver: any): Driver {
  const personType = ['driver', 'helper', 'ic_member'].includes(String(driver?.personType ?? driver?.person_type ?? driver?.type ?? ''))
    ? String(driver?.personType ?? driver?.person_type ?? driver?.type)
    : 'driver';
  return {
    id: String(driver?.id ?? ''),
    name: String(driver?.name ?? ''),
    personType: personType as Driver['personType'],
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
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [editingDriver, setEditingDriver] = useState<Driver | null>(null);
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [validationOpen, setValidationOpen] = useState(false);
  const [validationSummary, setValidationSummary] = useState<string[]>([]);
  
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
    personType: 'driver',
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
                         getCrewTypeLabel(driver.personType).toLowerCase().includes(searchQuery.toLowerCase()) ||
                         getTruckInfo(driver.assignedTruckId).toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || driver.status === statusFilter;
    const matchesType = typeFilter === 'all' || driver.personType === typeFilter;
    return matchesSearch && matchesStatus && matchesType;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active': return <Badge className="bg-success/20 text-success border-success/30">Active</Badge>;
      case 'inactive': return <Badge variant="secondary">Inactive</Badge>;
      case 'on_leave': return <Badge className="bg-warning/20 text-warning border-warning/30">On Leave</Badge>;
      default: return <Badge variant="outline">{status}</Badge>;
    }
  };

  const setField = (field: keyof Driver, value: any) => {
    setFormData((current) => ({ ...current, [field]: value }));
    setFormErrors((current) => {
      if (!current[field as string]) return current;
      const next = { ...current };
      delete next[field as string];
      return next;
    });
  };

  const validateForm = () => {
    const errors: Record<string, string> = {};
    const email = String(formData.email || '').trim();
    const phone = String(formData.phone || '').trim();
    if (!String(formData.name || '').trim()) errors.name = 'Full Name is required.';
    if (!phone) errors.phone = 'Phone Number is required.';
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = 'Email must be a valid email address.';
    return errors;
  };

  const handleSubmit = async () => {
    const errors = validateForm();
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      setValidationSummary(Object.values(errors));
      setValidationOpen(true);
      return;
    }
    setFormErrors({});
    setValidationSummary([]);
    try {
      const payload = {
        name: formData.name,
        personType: formData.personType || 'driver',
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
        toast({ title: "Crew Member Updated", description: "Crew member information has been updated." });
      } else {
        const created = normalizeDriver(await apiService.createDriver(payload));
        setDrivers(prev => [...prev, created]);
        toast({ title: "Crew Member Added", description: "New crew member has been added successfully." });
      }
      await queryClient.invalidateQueries({ queryKey: ['drivers'] });
      resetForm();
    } catch (error) {
      toast({
        title: "Unable to save crew member",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleDelete = async (id: string) => {
    const driver = drivers.find((item) => item.id === id);
    if (!window.confirm(`Delete crew member ${driver?.name || id}? This cannot be undone.`)) {
      return;
    }
    try {
      await apiService.deleteDriver(id);
      setDrivers(prev => prev.filter(d => d.id !== id));
      await queryClient.invalidateQueries({ queryKey: ['drivers'] });
      toast({ title: "Crew Member Deleted", description: "Crew member has been removed from the system." });
    } catch (error) {
      toast({
        title: "Unable to delete crew member",
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
      personType: 'driver',
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
    setFormErrors({});
    setValidationOpen(false);
    setValidationSummary([]);
  };

  const openEditDialog = (driver: Driver) => {
    setEditingDriver(driver);
    setFormData(driver);
    setFormErrors({});
    setValidationOpen(false);
    setValidationSummary([]);
    setIsAddDialogOpen(true);
  };

  const exportToCSV = () => {
    const headers = ['ID', 'Name', 'Type', 'Phone', 'Email', 'License Number', 'License Expiry', 'Join Date', 'Status', 'Assigned Truck', 'Emergency Contact', 'Address'];
    const rows = filteredDrivers.map(d => [d.id, d.name, getCrewTypeLabel(d.personType), d.phone, d.email, d.licenseNumber, d.licenseExpiry, d.joinDate, d.status, getTruckInfo(d.assignedTruckId), d.emergencyContact, d.address]);
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'crew-members.csv';
    a.click();
  };

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      <PageHeader
        category="Master Data"
        title="Crew Management"
        description="Manage drivers, helpers, IC members, assignments, and licensing"
        icon={UserCheck}
        actions={
          <>
            <Button variant="outline" onClick={exportToCSV}>
              <Download className="h-4 w-4 mr-2" /> Export
            </Button>
            <Dialog open={isAddDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); setIsAddDialogOpen(open); }}>
              <DialogTrigger asChild>
                <Button><Plus className="h-4 w-4 mr-2" /> Add Crew Member</Button>
              </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>{editingDriver ? 'Edit Crew Member' : 'Add New Crew Member'}</DialogTitle>
                <DialogDescription>Enter the crew member details below</DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Full Name <RequiredMark /></Label>
                    <Input className={validationErrorClass(formErrors, 'name')} value={formData.name} onChange={(e) => setField('name', e.target.value)} />
                    <FieldError errors={formErrors} field="name" />
                  </div>
                  <div className="space-y-2">
                    <Label>Phone Number <RequiredMark /></Label>
                    <Input className={validationErrorClass(formErrors, 'phone')} value={formData.phone} onChange={(e) => setField('phone', e.target.value)} />
                    <FieldError errors={formErrors} field="phone" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Type</Label>
                    <Select value={formData.personType || 'driver'} onValueChange={(value) => setField('personType', value as Driver['personType'])}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {CREW_TYPE_OPTIONS.map((item) => (
                          <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Status</Label>
                    <Select value={formData.status} onValueChange={(value) => setField('status', value as Driver['status'])}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="active">Active</SelectItem>
                        <SelectItem value="inactive">Inactive</SelectItem>
                        <SelectItem value="on_leave">On Leave</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Email</Label>
                    <Input className={validationErrorClass(formErrors, 'email')} type="email" value={formData.email} onChange={(e) => setField('email', e.target.value)} />
                    <FieldError errors={formErrors} field="email" />
                  </div>
                  <div className="space-y-2">
                    <Label>Emergency Contact</Label>
                    <Input value={formData.emergencyContact} onChange={(e) => setField('emergencyContact', e.target.value)} />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>License Number</Label>
                    <Input value={formData.licenseNumber} onChange={(e) => setField('licenseNumber', e.target.value)} />
                  </div>
                  <div className="space-y-2">
                    <Label>License Expiry</Label>
                    <Input type="date" value={formData.licenseExpiry} onChange={(e) => setField('licenseExpiry', e.target.value)} />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Join Date</Label>
                    <Input type="date" value={formData.joinDate} onChange={(e) => setField('joinDate', e.target.value)} />
                  </div>
                  <div className="space-y-2">
                    <Label>Assigned Truck</Label>
                    <Select
                      value={formData.assignedTruckId || UNASSIGNED_TRUCK_VALUE}
                      onValueChange={(value) => setField('assignedTruckId', value === UNASSIGNED_TRUCK_VALUE ? undefined : value)}
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
                    <Input value={formData.address} onChange={(e) => setField('address', e.target.value)} />
                  </div>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={resetForm}>Cancel</Button>
                <Button onClick={handleSubmit}>
                  {editingDriver ? 'Update' : 'Add'} Crew Member
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
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Crew</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{drivers.length}</div>
            <div className="mt-1 text-xs text-muted-foreground">
              {drivers.filter(d => d.personType === 'driver').length} drivers / {drivers.filter(d => d.personType === 'helper').length} helpers / {drivers.filter(d => d.personType === 'ic_member').length} IC
            </div>
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
              <Input placeholder="Search by name, type, phone, email, license, truck..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-10" />
            </div>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-[180px]"><SelectValue placeholder="Filter by type" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                {CREW_TYPE_OPTIONS.map((item) => (
                  <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
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
                <TableHead>Crew Member</TableHead>
                <TableHead>Type</TableHead>
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
                  <TableCell colSpan={9} className="py-8 text-center text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin inline mr-2" />
                    Loading crew members...
                  </TableCell>
                </TableRow>
              )}
              {!isLoadingDrivers && filteredDrivers.length === 0 && (
                <TableRow>
                  <TableCell colSpan={9} className="py-8 text-center text-muted-foreground">
                    No crew members found.
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
                    <Badge variant="secondary">{getCrewTypeLabel(driver.personType)}</Badge>
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

      <ValidationAlert open={validationOpen} onOpenChange={setValidationOpen} messages={validationSummary} />
    </div>
  );
}
