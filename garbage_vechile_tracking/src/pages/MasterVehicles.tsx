import { useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { PageHeader } from '@/components/PageHeader';
import { useToast } from '@/hooks/use-toast';
import { useRoutes, useVehicles, useVendors, useWards } from '@/hooks/useDataQueries';
import { apiService } from '@/services/api';
import { useQueryClient } from '@tanstack/react-query';
import { Car, Edit, Plus, Search, Trash2, Route as RouteIcon } from 'lucide-react';

export default function MasterVehicles() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data: vehiclesData = [], isLoading } = useVehicles();
  const { data: vendors = [] } = useVendors();
  const { data: wards = [] } = useWards();
  const { data: routes = [] } = useRoutes();

  const [vehicles, setVehicles] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editing, setEditing] = useState<any | null>(null);
  const [routeAssignVehicle, setRouteAssignVehicle] = useState<any | null>(null);
  const [routeToAssign, setRouteToAssign] = useState('');

  const [form, setForm] = useState<any>({
    vehicle_number: '',
    registration_number: '',
    vendor_id: '',
    ward_id: '',
    route_id: '',
    truck_type: 'compactor',
    capacity_kg: 0,
    capacity_cubic_meter: 0,
    fuel_type: 'diesel',
    operational_status: 'operational',
    chassis_number: '',
    engine_number: '',
    manufacture_year: new Date().getFullYear(),
    active: true,
  });

  useEffect(() => {
    const normalized = (vehiclesData as any[]).map((vehicle) => ({
      ...vehicle,
      vendor_id: vehicle.vendor_id || vehicle.vendorId || '',
    }));
    setVehicles(normalized);
  }, [vehiclesData]);

  const vendorById = useMemo(
    () => new Map((vendors as any[]).map((v) => [String(v.id), v.companyName || v.company_name || v.name])),
    [vendors]
  );
  const wardById = useMemo(() => new Map((wards as any[]).map((w) => [String(w.id), w.ward_name || w.name])), [wards]);
  const routeById = useMemo(() => new Map((routes as any[]).map((r) => [String(r.id), r.name || r.route_name])), [routes]);

  const filtered = vehicles.filter((v) => {
    const q = search.toLowerCase();
    const matchesSearch = (v.registration_number || '').toLowerCase().includes(q) || (v.vehicle_number || '').toLowerCase().includes(q);
    const matchesStatus = statusFilter === 'all' || v.operational_status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const resetForm = () => {
    setForm({
      vehicle_number: '', registration_number: '', vendor_id: '', ward_id: '', route_id: '', truck_type: 'compactor',
      capacity_kg: 0, capacity_cubic_meter: 0, fuel_type: 'diesel', operational_status: 'operational', chassis_number: '',
      engine_number: '', manufacture_year: new Date().getFullYear(), active: true,
    });
    setEditing(null);
    setIsDialogOpen(false);
  };

  const openEdit = (vehicle: any) => {
    setEditing(vehicle);
    setForm({
      ...vehicle,
      vendor_id: vehicle.vendor_id || vehicle.vendorId || '',
    });
    setIsDialogOpen(true);
  };

  const handleSave = async () => {
    if (!form.vehicle_number || !form.registration_number || !form.vendor_id || !form.ward_id) {
      toast({ title: 'Missing required fields', description: 'Vehicle Number, Registration, Vendor, and Ward are required.', variant: 'destructive' });
      return;
    }
    try {
      const payload = {
        ...form,
        vendor_id: form.vendor_id || form.vendorId,
      };
      if (editing) {
        const updated = await apiService.updateVehicle(String(editing.id), { ...payload, route_id: payload.route_id || null });
        setVehicles((prev) => prev.map((v) => String(v.id) === String(editing.id) ? {
          ...v,
          ...updated,
          vendor_id: updated.vendor_id || payload.vendor_id,
        } : v));
        toast({ title: 'Vehicle updated' });
      } else {
        const created = await apiService.createVehicle({ ...payload, route_id: payload.route_id || null });
        setVehicles((prev) => [{ ...created, vendor_id: created.vendor_id || payload.vendor_id }, ...prev]);
        toast({ title: 'Vehicle created' });
      }
      await queryClient.invalidateQueries({ queryKey: ['vehicles'] });
      resetForm();
    } catch (error) {
      toast({ title: 'Unable to save vehicle', description: error instanceof Error ? error.message : 'Please try again', variant: 'destructive' });
    }
  };

  const handleDelete = async (vehicleId: string) => {
    try {
      await apiService.deleteVehicle(vehicleId);
      await queryClient.invalidateQueries({ queryKey: ['vehicles'] });
      toast({ title: 'Vehicle deleted' });
    } catch (error) {
      toast({ title: 'Unable to delete vehicle', description: error instanceof Error ? error.message : 'Please try again', variant: 'destructive' });
    }
  };

  const handleRouteAssign = async () => {
    if (!routeAssignVehicle || !routeToAssign) {
      toast({ title: 'Select route', description: 'Please choose a route to assign.', variant: 'destructive' });
      return;
    }
    try {
      const existing = await apiService.getVehicle(String(routeAssignVehicle.id));
      await apiService.updateVehicle(String(routeAssignVehicle.id), { ...existing, route_id: routeToAssign });
      await queryClient.invalidateQueries({ queryKey: ['vehicles'] });
      toast({ title: 'Route assigned successfully' });
      setRouteAssignVehicle(null);
      setRouteToAssign('');
    } catch (error) {
      toast({ title: 'Route assignment failed', description: error instanceof Error ? error.message : 'Please try again', variant: 'destructive' });
    }
  };

  return (
    <div className='container mx-auto px-4 py-6 space-y-6'>
      <PageHeader
        category='Master Data'
        title='Vehicle Management'
        description='Manage vehicles and route mappings end-to-end'
        icon={Car}
        actions={
          <Dialog open={isDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); setIsDialogOpen(open); }}>
            <DialogTrigger asChild>
              <Button><Plus className='h-4 w-4 mr-2' /> Add Vehicle</Button>
            </DialogTrigger>
            <DialogContent className='max-w-3xl'>
              <DialogHeader><DialogTitle>{editing ? 'Edit Vehicle' : 'Add Vehicle'}</DialogTitle><DialogDescription>Required fields are validated before save.</DialogDescription></DialogHeader>
              <div className='grid gap-4 max-h-[65vh] overflow-y-auto py-2'>
                <div className='grid grid-cols-2 gap-4'>
                  <div><Label>Vehicle Number</Label><Input value={form.vehicle_number || ''} onChange={(e) => setForm({ ...form, vehicle_number: e.target.value.toUpperCase() })} /></div>
                  <div><Label>Registration Number</Label><Input value={form.registration_number || ''} onChange={(e) => setForm({ ...form, registration_number: e.target.value.toUpperCase() })} /></div>
                </div>
                <div className='grid grid-cols-2 gap-4'>
                  <div><Label>Vendor</Label><Select value={form.vendor_id || ''} onValueChange={(v) => setForm({ ...form, vendor_id: v })}><SelectTrigger><SelectValue placeholder='Select vendor' /></SelectTrigger><SelectContent>{(vendors as any[]).map((v) => <SelectItem key={v.id} value={String(v.id)}>{v.companyName || v.company_name || v.name}</SelectItem>)}</SelectContent></Select></div>
                  <div><Label>Ward</Label><Select value={form.ward_id || ''} onValueChange={(v) => setForm({ ...form, ward_id: v })}><SelectTrigger><SelectValue placeholder='Select ward' /></SelectTrigger><SelectContent>{(wards as any[]).map((w) => <SelectItem key={w.id} value={String(w.id)}>{w.ward_name || w.name}</SelectItem>)}</SelectContent></Select></div>
                </div>
                <div className='grid grid-cols-2 gap-4'>
                  <div><Label>Route</Label><Select value={form.route_id || 'none'} onValueChange={(v) => setForm({ ...form, route_id: v === 'none' ? '' : v })}><SelectTrigger><SelectValue placeholder='Optional route' /></SelectTrigger><SelectContent><SelectItem value='none'>Not Assigned</SelectItem>{(routes as any[]).map((r) => <SelectItem key={r.id} value={String(r.id)}>{r.name || r.route_name}</SelectItem>)}</SelectContent></Select></div>
                  <div><Label>Truck Type</Label><Input value={form.truck_type || ''} onChange={(e) => setForm({ ...form, truck_type: e.target.value })} /></div>
                </div>
                <div className='grid grid-cols-3 gap-4'>
                  <div><Label>Capacity KG</Label><Input type='number' value={form.capacity_kg ?? 0} onChange={(e) => setForm({ ...form, capacity_kg: Number(e.target.value) })} /></div>
                  <div><Label>Fuel</Label><Select value={form.fuel_type || 'diesel'} onValueChange={(v) => setForm({ ...form, fuel_type: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value='diesel'>Diesel</SelectItem><SelectItem value='petrol'>Petrol</SelectItem><SelectItem value='cng'>CNG</SelectItem><SelectItem value='electric'>Electric</SelectItem><SelectItem value='lng'>LNG</SelectItem></SelectContent></Select></div>
                  <div><Label>Status</Label><Select value={form.operational_status || 'operational'} onValueChange={(v) => setForm({ ...form, operational_status: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value='operational'>Operational</SelectItem><SelectItem value='maintenance'>Maintenance</SelectItem><SelectItem value='breakdown'>Breakdown</SelectItem><SelectItem value='retired'>Retired</SelectItem></SelectContent></Select></div>
                </div>
              </div>
              <DialogFooter><Button variant='outline' onClick={resetForm}>Cancel</Button><Button onClick={handleSave}>{editing ? 'Update' : 'Create'} Vehicle</Button></DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />

      <Card>
        <CardContent className='pt-6'>
          <div className='flex flex-col sm:flex-row gap-3'>
            <div className='relative flex-1'><Search className='absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground' /><Input className='pl-10' placeholder='Search vehicle or registration...' value={search} onChange={(e) => setSearch(e.target.value)} /></div>
            <Select value={statusFilter} onValueChange={setStatusFilter}><SelectTrigger className='w-[220px]'><SelectValue placeholder='Filter by status' /></SelectTrigger><SelectContent><SelectItem value='all'>All Status</SelectItem><SelectItem value='operational'>Operational</SelectItem><SelectItem value='maintenance'>Maintenance</SelectItem><SelectItem value='breakdown'>Breakdown</SelectItem><SelectItem value='retired'>Retired</SelectItem></SelectContent></Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Vehicles ({filtered.length})</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader><TableRow><TableHead>Vehicle</TableHead><TableHead>Vendor</TableHead><TableHead>Ward</TableHead><TableHead>Route</TableHead><TableHead>Status</TableHead><TableHead className='text-right'>Actions</TableHead></TableRow></TableHeader>
            <TableBody>
              {isLoading ? <TableRow><TableCell colSpan={6}>Loading...</TableCell></TableRow> : filtered.map((v) => (
                <TableRow key={v.id}>
                  <TableCell><div className='font-medium'>{v.registration_number}</div><div className='text-xs text-muted-foreground'>{v.vehicle_number}</div></TableCell>
                  <TableCell>{vendorById.get(String(v.vendor_id || '')) || '-'}</TableCell>
                  <TableCell>{wardById.get(String(v.ward_id)) || '-'}</TableCell>
                  <TableCell>{routeById.get(String(v.route_id || '')) || '-'}</TableCell>
                  <TableCell><Badge variant={v.operational_status === 'operational' ? 'default' : 'secondary'}>{v.operational_status}</Badge></TableCell>
                  <TableCell className='text-right space-x-1'>
                    <Button size='icon' variant='ghost' onClick={() => openEdit(v)}><Edit className='h-4 w-4' /></Button>
                    <Button size='icon' variant='ghost' onClick={() => { setRouteAssignVehicle(v); setRouteToAssign(String(v.route_id || '')); }}><RouteIcon className='h-4 w-4' /></Button>
                    <Button size='icon' variant='ghost' className='text-destructive' onClick={() => handleDelete(String(v.id))}><Trash2 className='h-4 w-4' /></Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={!!routeAssignVehicle} onOpenChange={(open) => { if (!open) { setRouteAssignVehicle(null); setRouteToAssign(''); } }}>
        <DialogContent>
          <DialogHeader><DialogTitle>Assign Route to Vehicle</DialogTitle><DialogDescription>Select the route to map to this vehicle.</DialogDescription></DialogHeader>
          <div className='space-y-2'>
            <Label>Route</Label>
            <Select value={routeToAssign || 'none'} onValueChange={(v) => setRouteToAssign(v === 'none' ? '' : v)}>
              <SelectTrigger><SelectValue placeholder='Select route' /></SelectTrigger>
              <SelectContent>
                <SelectItem value='none'>Unassign route</SelectItem>
                {(routes as any[]).map((r) => <SelectItem key={r.id} value={String(r.id)}>{r.name || r.route_name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter><Button variant='outline' onClick={() => setRouteAssignVehicle(null)}>Cancel</Button><Button onClick={handleRouteAssign}>Save Assignment</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
