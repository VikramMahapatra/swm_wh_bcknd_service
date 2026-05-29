import { useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { PageHeader } from '@/components/PageHeader';
import { useToast } from '@/hooks/use-toast';
import { useDeviceAssignments, useDevices, useVehicles } from '@/hooks/useDataQueries';
import { apiService } from '@/services/api';
import { useQueryClient } from '@tanstack/react-query';
import { Link2, Plus, RefreshCw, Search, Unlink } from 'lucide-react';

export default function MasterDeviceAssignments() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data: assignments = [], isLoading } = useDeviceAssignments();
  const { data: devices = [] } = useDevices();
  const { data: vehicles = [] } = useVehicles();

  const [search, setSearch] = useState('');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [form, setForm] = useState({ device_id: '', vehicle_id: '', remarks: '' });

  const deviceById = useMemo(() => new Map((devices as any[]).map((d) => [String(d.id), d.imei])), [devices]);
  const vehicleById = useMemo(() => new Map((vehicles as any[]).map((v) => [String(v.id), v.registration_number])), [vehicles]);

  const filtered = (assignments as any[]).filter((a) => {
    const q = search.toLowerCase();
    const imei = (deviceById.get(String(a.device_id)) || '').toLowerCase();
    const vehicle = (vehicleById.get(String(a.vehicle_id)) || '').toLowerCase();
    return imei.includes(q) || vehicle.includes(q);
  });

  const refreshAll = async () => {
    await queryClient.invalidateQueries({ queryKey: ['device-assignments'] });
    await queryClient.invalidateQueries({ queryKey: ['vehicles'] });
    await queryClient.invalidateQueries({ queryKey: ['devices'] });
  };

  const handleAssign = async () => {
    if (!form.device_id || !form.vehicle_id) {
      toast({ title: 'Device and Vehicle are required', variant: 'destructive' });
      return;
    }
    try {
      await apiService.createDeviceAssignment({
        device_id: form.device_id,
        vehicle_id: form.vehicle_id,
        remarks: form.remarks || undefined,
      });
      await refreshAll();
      setIsDialogOpen(false);
      setForm({ device_id: '', vehicle_id: '', remarks: '' });
      toast({ title: 'Device assigned successfully' });
    } catch (error) {
      toast({ title: 'Assignment failed', description: error instanceof Error ? error.message : 'Please try again', variant: 'destructive' });
    }
  };

  const handleReassign = async (deviceId: string, currentVehicleId: string) => {
    const target = window.prompt('Enter target vehicle ID for reassignment', currentVehicleId);
    if (!target || target === currentVehicleId) return;
    try {
      await apiService.reassignDevice(deviceId, target);
      await refreshAll();
      toast({ title: 'Device reassigned' });
    } catch (error) {
      toast({ title: 'Reassignment failed', description: error instanceof Error ? error.message : 'Please try again', variant: 'destructive' });
    }
  };

  const handleUnassign = async (deviceId: string) => {
    try {
      await apiService.unassignDevice(deviceId);
      await refreshAll();
      toast({ title: 'Device unassigned' });
    } catch (error) {
      toast({ title: 'Unassign failed', description: error instanceof Error ? error.message : 'Please try again', variant: 'destructive' });
    }
  };

  return (
    <div className='container mx-auto px-4 py-6 space-y-6'>
      <PageHeader
        category='Master Data'
        title='Device-Vehicle Assignment'
        description='Assign, reassign and unassign tracking devices to vehicles'
        icon={Link2}
        actions={<Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}><DialogTrigger asChild><Button><Plus className='h-4 w-4 mr-2' /> New Assignment</Button></DialogTrigger><DialogContent><DialogHeader><DialogTitle>Assign Device</DialogTitle><DialogDescription>Choose one device and one vehicle.</DialogDescription></DialogHeader><div className='space-y-3'>
          <div><Label>Device</Label><Select value={form.device_id} onValueChange={(v) => setForm({ ...form, device_id: v })}><SelectTrigger><SelectValue placeholder='Select device' /></SelectTrigger><SelectContent>{(devices as any[]).map((d) => <SelectItem key={d.id} value={String(d.id)}>{d.imei}</SelectItem>)}</SelectContent></Select></div>
          <div><Label>Vehicle</Label><Select value={form.vehicle_id} onValueChange={(v) => setForm({ ...form, vehicle_id: v })}><SelectTrigger><SelectValue placeholder='Select vehicle' /></SelectTrigger><SelectContent>{(vehicles as any[]).map((v) => <SelectItem key={v.id} value={String(v.id)}>{v.registration_number}</SelectItem>)}</SelectContent></Select></div>
          <div><Label>Remarks</Label><Input value={form.remarks} onChange={(e) => setForm({ ...form, remarks: e.target.value })} /></div>
        </div><DialogFooter><Button variant='outline' onClick={() => setIsDialogOpen(false)}>Cancel</Button><Button onClick={handleAssign}>Assign</Button></DialogFooter></DialogContent></Dialog>}
      />

      <Card><CardContent className='pt-6'><div className='relative'><Search className='absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground' /><Input className='pl-10' value={search} onChange={(e) => setSearch(e.target.value)} placeholder='Search by IMEI or vehicle...' /></div></CardContent></Card>

      <Card><CardHeader><CardTitle>Assignments ({filtered.length})</CardTitle></CardHeader><CardContent>
        <Table><TableHeader><TableRow><TableHead>Device</TableHead><TableHead>Vehicle</TableHead><TableHead>Assigned From</TableHead><TableHead>Active</TableHead><TableHead className='text-right'>Actions</TableHead></TableRow></TableHeader><TableBody>
          {isLoading ? <TableRow><TableCell colSpan={5}>Loading...</TableCell></TableRow> : filtered.map((a) => <TableRow key={a.id}><TableCell>{deviceById.get(String(a.device_id)) || a.device_id}</TableCell><TableCell>{vehicleById.get(String(a.vehicle_id)) || a.vehicle_id}</TableCell><TableCell>{a.assigned_from ? String(a.assigned_from).slice(0, 10) : '-'}</TableCell><TableCell>{a.active ? 'Yes' : 'No'}</TableCell><TableCell className='text-right space-x-1'><Button size='icon' variant='ghost' onClick={() => handleReassign(String(a.device_id), String(a.vehicle_id))}><RefreshCw className='h-4 w-4' /></Button><Button size='icon' variant='ghost' className='text-destructive' onClick={() => handleUnassign(String(a.device_id))}><Unlink className='h-4 w-4' /></Button></TableCell></TableRow>)}
        </TableBody></Table>
      </CardContent></Card>
    </div>
  );
}
