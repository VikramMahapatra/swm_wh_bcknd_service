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
import { useDevices, useVendors } from '@/hooks/useDataQueries';
import { apiService } from '@/services/api';
import { useQueryClient } from '@tanstack/react-query';
import { Cpu, Edit, Plus, Search, Trash2 } from 'lucide-react';

export default function MasterDevices() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data: devicesData = [], isLoading } = useDevices();
  const { data: vendors = [] } = useVendors();

  const [devices, setDevices] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [healthFilter, setHealthFilter] = useState('all');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editing, setEditing] = useState<any | null>(null);
  const [form, setForm] = useState<any>({
    vendor_id: '', imei: '', serial_no: '', model: '', manufacturer: '', firmware_version: '', sim_number: '',
    battery_percent: null, signal_strength: null, health_status: 'healthy', active: true,
  });

  useEffect(() => setDevices(devicesData as any[]), [devicesData]);

  const vendorById = useMemo(() => new Map((vendors as any[]).map((v) => [String(v.id), v.companyName || v.company_name || v.name])), [vendors]);

  const filtered = devices.filter((d) => {
    const q = search.toLowerCase();
    const matchesSearch = (d.imei || '').includes(search) || (d.serial_no || '').toLowerCase().includes(q);
    const matchesHealth = healthFilter === 'all' || d.health_status === healthFilter;
    return matchesSearch && matchesHealth;
  });

  const resetForm = () => {
    setForm({ vendor_id: '', imei: '', serial_no: '', model: '', manufacturer: '', firmware_version: '', sim_number: '', battery_percent: null, signal_strength: null, health_status: 'healthy', active: true });
    setEditing(null);
    setIsDialogOpen(false);
  };

  const openEdit = (device: any) => {
    setEditing(device);
    setForm({ ...device });
    setIsDialogOpen(true);
  };

  const handleSave = async () => {
    if (!form.vendor_id || !form.imei) {
      toast({ title: 'Vendor and IMEI are required', variant: 'destructive' });
      return;
    }
    if (!/^\d{14,17}$/.test(String(form.imei))) {
      toast({ title: 'Invalid IMEI', description: 'IMEI must be 14 to 17 digits.', variant: 'destructive' });
      return;
    }
    try {
      if (editing) {
        await apiService.updateDevice(String(editing.id), form);
        toast({ title: 'Device updated' });
      } else {
        await apiService.createDevice(form);
        toast({ title: 'Device created' });
      }
      await queryClient.invalidateQueries({ queryKey: ['devices'] });
      resetForm();
    } catch (error) {
      toast({ title: 'Unable to save device', description: error instanceof Error ? error.message : 'Please try again', variant: 'destructive' });
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await apiService.deleteDevice(id);
      await queryClient.invalidateQueries({ queryKey: ['devices'] });
      toast({ title: 'Device deleted' });
    } catch (error) {
      toast({ title: 'Unable to delete device', description: error instanceof Error ? error.message : 'Please try again', variant: 'destructive' });
    }
  };

  return (
    <div className='container mx-auto px-4 py-6 space-y-6'>
      <PageHeader
        category='Master Data'
        title='Device Management'
        description='Manage tracking devices and health status'
        icon={Cpu}
        actions={<Dialog open={isDialogOpen} onOpenChange={(open) => { if (!open) resetForm(); setIsDialogOpen(open); }}><DialogTrigger asChild><Button><Plus className='h-4 w-4 mr-2' /> Add Device</Button></DialogTrigger><DialogContent><DialogHeader><DialogTitle>{editing ? 'Edit Device' : 'Add Device'}</DialogTitle><DialogDescription>Use valid vendor and IMEI to save.</DialogDescription></DialogHeader><div className='grid gap-3'>
          <div><Label>Vendor</Label><Select value={form.vendor_id || ''} onValueChange={(v) => setForm({ ...form, vendor_id: v })}><SelectTrigger><SelectValue placeholder='Select vendor' /></SelectTrigger><SelectContent>{(vendors as any[]).map((v) => <SelectItem key={v.id} value={String(v.id)}>{v.companyName || v.company_name || v.name}</SelectItem>)}</SelectContent></Select></div>
          <div><Label>IMEI</Label><Input value={form.imei || ''} onChange={(e) => setForm({ ...form, imei: e.target.value.replace(/\D/g, '') })} /></div>
          <div><Label>Serial No</Label><Input value={form.serial_no || ''} onChange={(e) => setForm({ ...form, serial_no: e.target.value })} /></div>
          <div><Label>Model</Label><Input value={form.model || ''} onChange={(e) => setForm({ ...form, model: e.target.value })} /></div>
          <div><Label>Health Status</Label><Select value={form.health_status || 'healthy'} onValueChange={(v) => setForm({ ...form, health_status: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value='healthy'>Healthy</SelectItem><SelectItem value='warning'>Warning</SelectItem><SelectItem value='critical'>Critical</SelectItem><SelectItem value='offline'>Offline</SelectItem></SelectContent></Select></div>
        </div><DialogFooter><Button variant='outline' onClick={resetForm}>Cancel</Button><Button onClick={handleSave}>{editing ? 'Update' : 'Create'} Device</Button></DialogFooter></DialogContent></Dialog>}
      />

      <Card><CardContent className='pt-6'><div className='flex flex-col sm:flex-row gap-3'><div className='relative flex-1'><Search className='absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground' /><Input className='pl-10' value={search} onChange={(e) => setSearch(e.target.value)} placeholder='Search by IMEI or serial...' /></div><Select value={healthFilter} onValueChange={setHealthFilter}><SelectTrigger className='w-[220px]'><SelectValue /></SelectTrigger><SelectContent><SelectItem value='all'>All Health</SelectItem><SelectItem value='healthy'>Healthy</SelectItem><SelectItem value='warning'>Warning</SelectItem><SelectItem value='critical'>Critical</SelectItem><SelectItem value='offline'>Offline</SelectItem></SelectContent></Select></div></CardContent></Card>

      <Card><CardHeader><CardTitle>Devices ({filtered.length})</CardTitle></CardHeader><CardContent>
        <Table><TableHeader><TableRow><TableHead>IMEI</TableHead><TableHead>Vendor</TableHead><TableHead>Health</TableHead><TableHead>Active</TableHead><TableHead className='text-right'>Actions</TableHead></TableRow></TableHeader><TableBody>
          {isLoading ? <TableRow><TableCell colSpan={5}>Loading...</TableCell></TableRow> : filtered.map((d) => <TableRow key={d.id}><TableCell><div className='font-medium'>{d.imei}</div><div className='text-xs text-muted-foreground'>{d.serial_no || '-'}</div></TableCell><TableCell>{vendorById.get(String(d.vendor_id)) || '-'}</TableCell><TableCell><Badge variant={d.health_status === 'healthy' ? 'default' : 'secondary'}>{d.health_status}</Badge></TableCell><TableCell>{d.active ? 'Yes' : 'No'}</TableCell><TableCell className='text-right space-x-1'><Button size='icon' variant='ghost' onClick={() => openEdit(d)}><Edit className='h-4 w-4' /></Button><Button size='icon' variant='ghost' className='text-destructive' onClick={() => handleDelete(String(d.id))}><Trash2 className='h-4 w-4' /></Button></TableCell></TableRow>)}
        </TableBody></Table>
      </CardContent></Card>
    </div>
  );
}
