import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useToast } from '@/hooks/use-toast';
import { useVendors, useVehicles } from '@/hooks/useDataQueries';
import { apiService } from '@/services/api';
import { useQueryClient } from '@tanstack/react-query';
import { useMemo } from 'react';
import { Vendor } from '@/data/masterData';
import { Plus, Search, Edit, Trash2, Phone, Mail, Building2, Download, Truck, Loader2 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { FieldError, RequiredMark, ValidationAlert, errorClass as validationErrorClass } from '@/components/FormValidation';

export default function MasterVendors() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data: vendorsData = [], isLoading: isLoadingVendors } = useVendors();
  const { data: vehiclesData = [] } = useVehicles();
  
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [editingVendor, setEditingVendor] = useState<Vendor | null>(null);
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [validationOpen, setValidationOpen] = useState(false);
  const [validationSummary, setValidationSummary] = useState<string[]>([]);

  const normalizeDateValue = (value?: string | null) => (value ? value.slice(0, 10) : '');

  const normalizeVendor = (vendor: any): Vendor => {
    const metadata = vendor?.metadata && typeof vendor.metadata === 'object' ? vendor.metadata : {};
    return {
      ...vendor,
      name: vendor.contact_person || vendor.contactPerson || vendor.name || '',
      companyName: vendor.companyName || vendor.company_name || vendor.vendor_name || '',
      gstNumber: vendor.gstNumber || vendor.gst_number || metadata.gstNumber || metadata.gst_number || '',
      address: vendor.address || metadata.address || '',
      contractStart: normalizeDateValue(
        vendor.contractStart || vendor.contract_start || metadata.contractStart || metadata.contract_start,
      ),
      contractEnd: normalizeDateValue(
        vendor.contractEnd || vendor.contract_end || metadata.contractEnd || metadata.contract_end,
      ),
      supervisorName: '',
      supervisorPhone: '',
      trucksOwned: vendor.trucksOwned || [],
    } as Vendor;
  };

  useEffect(() => {
    const normalizedVendors = (vendorsData as any[]).map(normalizeVendor);

    setVendors(normalizedVendors);
  }, [vendorsData]);
  
  const [formData, setFormData] = useState<Partial<Vendor>>({
    name: '',
    companyName: '',
    phone: '',
    email: '',
    address: '',
    gstNumber: '',
    contractStart: '',
    contractEnd: '',
    status: 'active',
    trucksOwned: []
  });

  const filteredVendors = vendors.filter(vendor => {
    const name = (vendor.name || "").toLowerCase();
    const companyName = (vendor.companyName || "").toLowerCase();
    const phone = vendor.phone || "";
    const matchesSearch = name.includes(searchQuery.toLowerCase()) ||
                         companyName.includes(searchQuery.toLowerCase()) ||
                         phone.includes(searchQuery);
    const matchesStatus = statusFilter === 'all' || vendor.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const vendorTruckCount = useMemo(() => {
    const map = new Map<string, number>();
    (vehiclesData as any[]).forEach((vehicle) => {
      const vendorId = String(vehicle.vendor_id || vehicle.vendorId || '').trim();
      if (!vendorId) return;
      map.set(vendorId, (map.get(vendorId) || 0) + 1);
    });
    return map;
  }, [vehiclesData]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active': return <Badge className="bg-success/20 text-success border-success/30">Active</Badge>;
      case 'inactive': return <Badge variant="secondary">Inactive</Badge>;
      case 'suspended': return <Badge className="bg-destructive/20 text-destructive border-destructive/30">Suspended</Badge>;
      default: return <Badge variant="outline">{status}</Badge>;
    }
  };

  const buildVendorCode = (seed?: string) => {
    const normalized = (seed || 'VENDOR')
      .toUpperCase()
      .replace(/[^A-Z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '');
    const base = normalized.length >= 3 ? normalized.slice(0, 24) : `VND_${normalized}`;
    return base.length >= 3 ? base : 'VND_VENDOR';
  };

  const setField = (field: keyof Vendor, value: any) => {
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
    const vendorName = String(formData.companyName || '').trim();
    const email = String(formData.email || '').trim();
    const phone = String(formData.phone || '').trim();
    const contractStart = String(formData.contractStart || '').trim();
    const contractEnd = String(formData.contractEnd || '').trim();
    if (!vendorName) errors.companyName = 'Company Name is required.';
    if (!phone) errors.phone = 'Phone Number is required.';
    if (!email) errors.email = 'Email is required.';
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = 'Email must be a valid email address.';
    if (contractStart && contractEnd && contractEnd < contractStart) {
      errors.contractEnd = 'Contract End Date must be greater than or equal to Contract Start Date.';
    }
    return errors;
  };

  const handleSubmit = async () => {
    try {
      const vendorName = String(formData.companyName || '').trim();
      const errors = validateForm();
      if (Object.keys(errors).length > 0) {
        setFormErrors(errors);
        setValidationSummary(Object.values(errors));
        setValidationOpen(true);
        return;
      }
      setFormErrors({});
      setValidationSummary([]);

      if (editingVendor) {
        const existing = await apiService.getVendor(editingVendor.id);
        const mergedMetadata = {
          ...(existing?.metadata_json || existing?.metadata || {}),
          gst_number: formData.gstNumber || null,
          address: formData.address || null,
        };
        const updated = await apiService.updateVendor(editingVendor.id, {
          vendor_code: existing?.vendor_code || buildVendorCode(vendorName),
          vendor_name: vendorName,
          contact_person: formData.name || null,
          phone: formData.phone || null,
          email: formData.email || null,
          gst_number: formData.gstNumber || null,
          address: formData.address || null,
          contract_start: formData.contractStart || null,
          contract_end: formData.contractEnd || null,
          active: formData.status !== 'inactive' && formData.status !== 'suspended',
          auth_type: existing?.auth_type || 'header',
          allowed_ips: Array.isArray(existing?.allowed_ips) ? existing.allowed_ips : [],
          callback_format: existing?.callback_format || {},
          metadata: mergedMetadata,
          webhook_secret: existing?.webhook_secret || null,
          signature_key: existing?.signature_key || null,
        });

        setVendors(prev => prev.map(v => v.id === editingVendor.id ? normalizeVendor({
          ...v,
          ...formData,
          ...updated,
          id: String(updated?.id || editingVendor.id),
          companyName: updated?.vendor_name || vendorName,
          name: updated?.contact_person || formData.name || '',
          status: updated?.active === false ? 'inactive' : 'active',
          metadata: updated?.metadata || updated?.metadata_json || existing?.metadata_json || existing?.metadata || {},
        }) : v));
        toast({ title: "Vendor Updated", description: "Vendor information has been updated." });
      } else {
        const created = await apiService.createVendor({
          vendor_code: buildVendorCode(vendorName),
          vendor_name: vendorName,
          contact_person: formData.name || null,
          phone: formData.phone || null,
          email: formData.email || null,
          gst_number: formData.gstNumber || null,
          address: formData.address || null,
          contract_start: formData.contractStart || null,
          contract_end: formData.contractEnd || null,
          active: formData.status !== 'inactive' && formData.status !== 'suspended',
          auth_type: 'header',
          allowed_ips: [],
          callback_format: {},
          metadata: {
            gst_number: formData.gstNumber || null,
            address: formData.address || null,
          },
        });

        const newVendor: Vendor = normalizeVendor({
          ...(formData as Vendor),
          ...created,
          id: String(created?.id || ''),
          companyName: created?.vendor_name || vendorName,
          name: created?.contact_person || formData.name || '',
          status: created?.active === false ? 'inactive' : 'active',
          metadata: created?.metadata || created?.metadata_json || {},
          trucksOwned: [],
        });
        setVendors(prev => [...prev, newVendor]);
        toast({ title: "Vendor Added", description: "New vendor has been added successfully." });
      }

      await queryClient.invalidateQueries({ queryKey: ['vendors'] });
      resetForm();
    } catch (error) {
      toast({
        title: "Unable to save vendor",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await apiService.deleteVendor(id);
      setVendors(prev => prev.filter(v => v.id !== id));
      await queryClient.invalidateQueries({ queryKey: ['vendors'] });
      toast({ title: "Vendor Deleted", description: "Vendor has been removed from the system." });
    } catch (error) {
      toast({
        title: "Unable to delete vendor",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    }
  };

  const resetForm = () => {
    setFormData({ name: '', companyName: '', phone: '', email: '', address: '', gstNumber: '', contractStart: '', contractEnd: '', status: 'active', trucksOwned: [] });
    setEditingVendor(null);
    setIsAddDialogOpen(false);
    setFormErrors({});
    setValidationOpen(false);
    setValidationSummary([]);
  };

  const openEditDialog = (vendor: Vendor) => {
    const normalizedVendor = normalizeVendor(vendor);
    setEditingVendor(normalizedVendor);
    setFormData(normalizedVendor);
    setFormErrors({});
    setValidationOpen(false);
    setValidationSummary([]);
    setIsAddDialogOpen(true);
  };

  const exportToCSV = () => {
    const headers = ['ID', 'Name', 'Company', 'Phone', 'Email', 'GST Number', 'Contract Start', 'Contract End', 'Status', 'Trucks Owned'];
    const rows = filteredVendors.map(v => [v.id, v.name || '', v.companyName || v.name || '', v.phone || '', v.email || '', v.gstNumber || '', v.contractStart || '', v.contractEnd || '', v.status || '', vendorTruckCount.get(String(v.id)) || 0]);
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'vendors.csv';
    a.click();
  };

  const expiringSoonCount = vendors.filter((v) => {
    if (!v.contractEnd) return false;
    const endDate = new Date(v.contractEnd);
    if (Number.isNaN(endDate.getTime())) return false;
    const now = new Date();
    const diffMs = endDate.getTime() - now.getTime();
    const diffDays = diffMs / (1000 * 60 * 60 * 24);
    return diffDays >= 0 && diffDays <= 30;
  }).length;

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      <PageHeader
        category="Master Data"
        title="Vendor Management"
        description="Manage vendor contracts, information, and service agreements"
        icon={Building2}
        actions={
          <>
            <Button variant="outline" onClick={exportToCSV}>
              <Download className="h-4 w-4 mr-2" /> Export
            </Button>
            <Dialog open={isAddDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); setIsAddDialogOpen(open); }}>
              <DialogTrigger asChild>
                <Button><Plus className="h-4 w-4 mr-2" /> Add Vendor</Button>
              </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>{editingVendor ? 'Edit Vendor' : 'Add New Vendor'}</DialogTitle>
                <DialogDescription>Enter the vendor details below</DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4 max-h-[60vh] overflow-y-auto">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Contact Person Name</Label>
                    <Input value={formData.name} onChange={(e) => setField('name', e.target.value)} />
                  </div>
                  <div className="space-y-2">
                    <Label>Company Name <RequiredMark /></Label>
                    <Input className={validationErrorClass(formErrors, 'companyName')} value={formData.companyName} onChange={(e) => setField('companyName', e.target.value)} />
                    <FieldError errors={formErrors} field="companyName" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Phone Number <RequiredMark /></Label>
                    <Input className={validationErrorClass(formErrors, 'phone')} value={formData.phone} onChange={(e) => setField('phone', e.target.value)} />
                    <FieldError errors={formErrors} field="phone" />
                  </div>
                  <div className="space-y-2">
                    <Label>Email <RequiredMark /></Label>
                    <Input className={validationErrorClass(formErrors, 'email')} type="email" value={formData.email} onChange={(e) => setField('email', e.target.value)} />
                    <FieldError errors={formErrors} field="email" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>GST Number</Label>
                    <Input value={formData.gstNumber} onChange={(e) => setFormData({ ...formData, gstNumber: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Address</Label>
                    <Input value={formData.address} onChange={(e) => setFormData({ ...formData, address: e.target.value })} />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Contract Start Date</Label>
                    <Input type="date" value={formData.contractStart} onChange={(e) => setField('contractStart', e.target.value)} />
                  </div>
                  <div className="space-y-2">
                    <Label>Contract End Date</Label>
                    <Input className={validationErrorClass(formErrors, 'contractEnd')} type="date" value={formData.contractEnd} onChange={(e) => setField('contractEnd', e.target.value)} />
                    <FieldError errors={formErrors} field="contractEnd" />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Status</Label>
                  <Select value={formData.status} onValueChange={(value) => setField('status', value as Vendor['status'])}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="inactive">Inactive</SelectItem>
                      <SelectItem value="suspended">Suspended</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={resetForm}>Cancel</Button>
                <Button onClick={handleSubmit}>{editingVendor ? 'Update' : 'Add'} Vendor</Button>
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
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Vendors</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{vendors.length}</div>
          </CardContent>
        </Card>
        <Card className="bg-success/10 border-success/30">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-success">Active Contracts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-success">{vendors.filter(v => v.status === 'active').length}</div>
          </CardContent>
        </Card>
        <Card className="bg-warning/10 border-warning/30">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-warning">Expiring Soon</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-warning">{expiringSoonCount}</div>
          </CardContent>
        </Card>
        <Card className="bg-primary/10 border-primary/30">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-primary">Total Trucks</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">{vendors.reduce((acc, v) => acc + (vendorTruckCount.get(String(v.id)) || 0), 0)}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="bg-card/50 border-border/50">
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Search by name, company, phone..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-10" />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]"><SelectValue placeholder="Filter by status" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
                <SelectItem value="suspended">Suspended</SelectItem>
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
                <TableHead>Vendor</TableHead>
                <TableHead>Contact</TableHead>
                <TableHead>Contract Period</TableHead>
                <TableHead>Trucks</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredVendors.map((vendor) => (
                <TableRow key={vendor.id}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                        <Building2 className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <div className="font-medium">{vendor.companyName || vendor.name}</div>
                        <div className="text-sm text-muted-foreground">{vendor.companyName ? vendor.name : 'Company name not set'}</div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      <div className="flex items-center gap-1 text-sm"><Phone className="h-3 w-3" /> {vendor.phone}</div>
                      <div className="flex items-center gap-1 text-sm text-muted-foreground"><Mail className="h-3 w-3" /> {vendor.email}</div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm">{vendor.contractStart || '-'}</div>
                    <div className="text-xs text-muted-foreground">to {vendor.contractEnd || '-'}</div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Truck className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{vendorTruckCount.get(String(vendor.id)) || 0}</span>
                    </div>
                  </TableCell>
                  <TableCell>{getStatusBadge(vendor.status)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button variant="ghost" size="icon" onClick={() => openEditDialog(vendor)}><Edit className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" className="text-destructive" onClick={() => handleDelete(vendor.id)}><Trash2 className="h-4 w-4" /></Button>
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
