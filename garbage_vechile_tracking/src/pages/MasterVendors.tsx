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
import { useVendors } from '@/hooks/useDataQueries';
import { Vendor } from '@/data/masterData';
import { Plus, Search, Edit, Trash2, Phone, Mail, Building2, Download, Truck, Loader2 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';

export default function MasterVendors() {
  const { toast } = useToast();
  const { data: vendorsData = [], isLoading: isLoadingVendors } = useVendors();
  
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [editingVendor, setEditingVendor] = useState<Vendor | null>(null);

  useEffect(() => {
    const normalizedVendors = (vendorsData as any[]).map((vendor) => ({
      ...vendor,
      companyName: vendor.companyName || vendor.company_name,
      gstNumber: vendor.gstNumber || vendor.gst_number,
      contractStart: vendor.contractStart || vendor.contract_start,
      contractEnd: vendor.contractEnd || vendor.contract_end,
      supervisorName: vendor.supervisorName || vendor.supervisor_name,
      supervisorPhone: vendor.supervisorPhone || vendor.supervisor_phone,
      trucksOwned: vendor.trucksOwned || [],
    })) as Vendor[];

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
    supervisorName: '',
    supervisorPhone: '',
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

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active': return <Badge className="bg-success/20 text-success border-success/30">Active</Badge>;
      case 'inactive': return <Badge variant="secondary">Inactive</Badge>;
      case 'suspended': return <Badge className="bg-destructive/20 text-destructive border-destructive/30">Suspended</Badge>;
      default: return <Badge variant="outline">{status}</Badge>;
    }
  };

  const handleSubmit = () => {
    if (editingVendor) {
      setVendors(prev => prev.map(v => v.id === editingVendor.id ? { ...v, ...formData } as Vendor : v));
      toast({ title: "Vendor Updated", description: "Vendor information has been updated." });
    } else {
      const newVendor: Vendor = {
        ...formData as Vendor,
        id: `VND${String(vendors.length + 1).padStart(3, '0')}`,
        trucksOwned: []
      };
      setVendors(prev => [...prev, newVendor]);
      toast({ title: "Vendor Added", description: "New vendor has been added successfully." });
    }
    resetForm();
  };

  const handleDelete = (id: string) => {
    setVendors(prev => prev.filter(v => v.id !== id));
    toast({ title: "Vendor Deleted", description: "Vendor has been removed from the system." });
  };

  const resetForm = () => {
    setFormData({ name: '', companyName: '', phone: '', email: '', address: '', gstNumber: '', contractStart: '', contractEnd: '', status: 'active', supervisorName: '', supervisorPhone: '', trucksOwned: [] });
    setEditingVendor(null);
    setIsAddDialogOpen(false);
  };

  const openEditDialog = (vendor: Vendor) => {
    setEditingVendor(vendor);
    setFormData(vendor);
    setIsAddDialogOpen(true);
  };

  const exportToCSV = () => {
    const headers = ['ID', 'Name', 'Company', 'Phone', 'Email', 'GST Number', 'Contract Start', 'Contract End', 'Status', 'Trucks Owned'];
    const rows = filteredVendors.map(v => [v.id, v.name || '', v.companyName || v.name || '', v.phone || '', v.email || '', v.gstNumber || '', v.contractStart || '', v.contractEnd || '', v.status || '', v.trucksOwned?.length || 0]);
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'vendors.csv';
    a.click();
  };

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
                    <Input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Company Name</Label>
                    <Input value={formData.companyName} onChange={(e) => setFormData({ ...formData, companyName: e.target.value })} />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Phone Number</Label>
                    <Input value={formData.phone} onChange={(e) => setFormData({ ...formData, phone: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Email</Label>
                    <Input type="email" value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} />
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
                    <Input type="date" value={formData.contractStart} onChange={(e) => setFormData({ ...formData, contractStart: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Contract End Date</Label>
                    <Input type="date" value={formData.contractEnd} onChange={(e) => setFormData({ ...formData, contractEnd: e.target.value })} />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Supervisor Name</Label>
                    <Input value={formData.supervisorName} onChange={(e) => setFormData({ ...formData, supervisorName: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Supervisor Phone</Label>
                    <Input value={formData.supervisorPhone} onChange={(e) => setFormData({ ...formData, supervisorPhone: e.target.value })} />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Status</Label>
                  <Select value={formData.status} onValueChange={(value) => setFormData({ ...formData, status: value as Vendor['status'] })}>
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
            <div className="text-2xl font-bold text-warning">1</div>
          </CardContent>
        </Card>
        <Card className="bg-primary/10 border-primary/30">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-primary">Total Trucks</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">{vendors.reduce((acc, v) => acc + (v.trucksOwned?.length || 0), 0)}</div>
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
                    <div className="text-sm">{vendor.contractStart}</div>
                    <div className="text-xs text-muted-foreground">to {vendor.contractEnd}</div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Truck className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{vendor.trucksOwned?.length || 0}</span>
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
    </div>
  );
}
