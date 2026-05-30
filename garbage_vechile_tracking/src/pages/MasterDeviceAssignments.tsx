import { useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { PageHeader } from '@/components/PageHeader';
import { useToast } from '@/hooks/use-toast';
import { useDeviceAssignments, useDevices, useVehicles } from '@/hooks/useDataQueries';
import { apiService } from '@/services/api';
import { useQueryClient } from '@tanstack/react-query';
import { Link2, Pencil, Plus, RefreshCw, Search, Unlink } from 'lucide-react';

type DeviceAssignmentAction = {
  type: 'save-edit' | 'unassign';
  assignment?: any;
};

export default function MasterDeviceAssignments() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data: assignments = [], isLoading } = useDeviceAssignments();
  const { data: devices = [] } = useDevices();
  const { data: vehicles = [] } = useVehicles();

  const [search, setSearch] = useState('');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [form, setForm] = useState({ device_id: '', vehicle_id: '', remarks: '' });
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editingAssignment, setEditingAssignment] = useState<any | null>(null);
  const [editForm, setEditForm] = useState({ vehicle_id: '', remarks: '' });
  const [pendingAction, setPendingAction] = useState<DeviceAssignmentAction | null>(null);

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

  const openEdit = (assignment: any) => {
    setEditingAssignment(assignment);
    setEditForm({
      vehicle_id: String(assignment.vehicle_id || ''),
      remarks: assignment.remarks || '',
    });
    setIsEditOpen(true);
  };

  const requestSaveEdit = () => {
    if (!editingAssignment || !editForm.vehicle_id) {
      toast({ title: 'Vehicle is required', variant: 'destructive' });
      return;
    }
    setPendingAction({ type: 'save-edit', assignment: editingAssignment });
  };

  const saveEdit = async () => {
    if (!editingAssignment) return;
    try {
      await apiService.reassignDevice(
        String(editingAssignment.device_id),
        editForm.vehicle_id,
        editForm.remarks || undefined
      );
      await refreshAll();
      setIsEditOpen(false);
      setEditingAssignment(null);
      setEditForm({ vehicle_id: '', remarks: '' });
      toast({ title: 'Assignment updated successfully' });
    } catch (error) {
      toast({ title: 'Update failed', description: error instanceof Error ? error.message : 'Please try again', variant: 'destructive' });
    }
  };

  const requestUnassign = (assignment: any) => {
    setPendingAction({ type: 'unassign', assignment });
  };

  const handleUnassign = async (assignment: any) => {
    try {
      await apiService.unassignDevice(String(assignment.device_id));
      await refreshAll();
      toast({ title: 'Device unassigned' });
    } catch (error) {
      toast({ title: 'Unassign failed', description: error instanceof Error ? error.message : 'Please try again', variant: 'destructive' });
    }
  };

  const confirmPendingAction = async () => {
    const action = pendingAction;
    setPendingAction(null);
    if (!action) return;
    if (action.type === 'save-edit') {
      await saveEdit();
      return;
    }
    if (action.type === 'unassign' && action.assignment) {
      await handleUnassign(action.assignment);
    }
  };

  const getActionCopy = () => {
    if (pendingAction?.type === 'save-edit') {
      return {
        title: 'Update assignment?',
        description: 'This will close the current active assignment and create a new active assignment for the selected vehicle.',
        action: 'Update',
      };
    }
    return {
      title: 'Unassign device?',
      description: 'This will mark the current device-vehicle assignment inactive. Live telemetry will not map to this truck until the device is assigned again.',
      action: 'Unassign',
    };
  };

  const ActionButton = ({
    label,
    children,
    onClick,
    className = '',
    disabled = false,
  }: {
    label: string;
    children: React.ReactNode;
    onClick: () => void;
    className?: string;
    disabled?: boolean;
  }) => (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          size='icon'
          variant='ghost'
          className={className}
          onClick={onClick}
          disabled={disabled}
          aria-label={label}
          title={label}
        >
          {children}
        </Button>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );

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
          {isLoading ? <TableRow><TableCell colSpan={5}>Loading...</TableCell></TableRow> : filtered.map((a) => <TableRow key={`${a.device_id}-${a.vehicle_id}-${a.assigned_from || ''}`}><TableCell>{deviceById.get(String(a.device_id)) || a.device_id}</TableCell><TableCell>{vehicleById.get(String(a.vehicle_id)) || a.vehicle_id}</TableCell><TableCell>{a.assigned_from ? String(a.assigned_from).slice(0, 10) : '-'}</TableCell><TableCell>{a.active ? 'Yes' : 'No'}</TableCell><TableCell className='text-right'><TooltipProvider><div className='flex justify-end gap-1'><ActionButton label={a.active ? 'Edit assignment' : 'Reactivate assignment'} onClick={() => openEdit(a)}><Pencil className='h-4 w-4' /></ActionButton><ActionButton label={a.active ? 'Reassign device' : 'Assign device again'} onClick={() => openEdit(a)}><RefreshCw className='h-4 w-4' /></ActionButton><ActionButton label={a.active ? 'Unassign device' : 'Already unassigned'} className='text-destructive' onClick={() => requestUnassign(a)} disabled={!a.active}><Unlink className='h-4 w-4' /></ActionButton></div></TooltipProvider></TableCell></TableRow>)}
        </TableBody></Table>
      </CardContent></Card>

      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Device-Vehicle Assignment</DialogTitle>
            <DialogDescription>
              Update the active vehicle for this device. Saving will create a fresh active assignment.
            </DialogDescription>
          </DialogHeader>
          <div className='space-y-3'>
            <div>
              <Label>Device</Label>
              <Input value={editingAssignment ? deviceById.get(String(editingAssignment.device_id)) || String(editingAssignment.device_id) : ''} disabled />
            </div>
            <div>
              <Label>Vehicle</Label>
              <Select value={editForm.vehicle_id} onValueChange={(v) => setEditForm({ ...editForm, vehicle_id: v })}>
                <SelectTrigger><SelectValue placeholder='Select vehicle' /></SelectTrigger>
                <SelectContent>{(vehicles as any[]).map((v) => <SelectItem key={v.id} value={String(v.id)}>{v.registration_number}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <Label>Remarks</Label>
              <Input value={editForm.remarks} onChange={(e) => setEditForm({ ...editForm, remarks: e.target.value })} placeholder='Optional update note' />
            </div>
          </div>
          <DialogFooter>
            <Button variant='outline' onClick={() => setIsEditOpen(false)}>Cancel</Button>
            <Button onClick={requestSaveEdit}>Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={Boolean(pendingAction)} onOpenChange={(open) => !open && setPendingAction(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{getActionCopy().title}</AlertDialogTitle>
            <AlertDialogDescription>{getActionCopy().description}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmPendingAction}>{getActionCopy().action}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
