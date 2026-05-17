import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useToast } from '@/hooks/use-toast';
import { useZones, useZoneWards } from '@/hooks/useDataQueries';
import { Zone, Ward } from '@/data/masterData';
import { Plus, Search, Edit, Trash2, MapPin, Users, Download, Loader2 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';

export default function MasterZonesWards() {
  const { toast } = useToast();
  const { data: zonesData = [], isLoading: isLoadingZones } = useZones();
  const [selectedZoneId, setSelectedZoneId] = useState<string>("");
  const { data: wardsData = [], isLoading: isLoadingWards } = useZoneWards(selectedZoneId);
  
  const [zones, setZones] = useState<Zone[]>([]);
  const [wards, setWards] = useState<Ward[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isZoneDialogOpen, setIsZoneDialogOpen] = useState(false);
  const [isWardDialogOpen, setIsWardDialogOpen] = useState(false);
  const [editingZone, setEditingZone] = useState<Zone | null>(null);
  const [editingWard, setEditingWard] = useState<Ward | null>(null);

  useEffect(() => {
    setZones(zonesData);
  }, [zonesData]);

  useEffect(() => {
    if (!selectedZoneId && zonesData.length > 0) {
      setSelectedZoneId(zonesData[0].id);
    }
  }, [selectedZoneId, zonesData]);

  useEffect(() => {
    setWards(wardsData);
  }, [wardsData]);
  
  const [zoneForm, setZoneForm] = useState<Partial<Zone>>({ name: '', code: '', description: '', supervisorName: '', supervisorPhone: '', totalWards: 0, status: 'active' });
  const [wardForm, setWardForm] = useState<Partial<Ward>>({ name: '', code: '', zoneId: '', population: 0, area: 0, totalPickupPoints: 0, status: 'active' });

  const getStatusBadge = (status: string) => {
    return status === 'active' 
      ? <Badge className="bg-success/20 text-success border-success/30">Active</Badge>
      : <Badge variant="secondary">Inactive</Badge>;
  };

  const getZoneName = (zoneId: string) => zones.find(z => z.id === zoneId)?.name || 'Unknown';

  // Zone handlers
  const handleZoneSubmit = () => {
    if (editingZone) {
      setZones(prev => prev.map(z => z.id === editingZone.id ? { ...z, ...zoneForm } as Zone : z));
      toast({ title: "Zone Updated", description: "Zone information has been updated." });
    } else {
      const newZone: Zone = { ...zoneForm as Zone, id: `ZN${String(zones.length + 1).padStart(3, '0')}` };
      setZones(prev => [...prev, newZone]);
      toast({ title: "Zone Added", description: "New zone has been added successfully." });
    }
    resetZoneForm();
  };

  const resetZoneForm = () => {
    setZoneForm({ name: '', code: '', description: '', supervisorName: '', supervisorPhone: '', totalWards: 0, status: 'active' });
    setEditingZone(null);
    setIsZoneDialogOpen(false);
  };

  const openEditZoneDialog = (zone: Zone) => {
    setEditingZone(zone);
    setZoneForm(zone);
    setIsZoneDialogOpen(true);
  };

  // Ward handlers
  const handleWardSubmit = () => {
    if (editingWard) {
      setWards(prev => prev.map(w => w.id === editingWard.id ? { ...w, ...wardForm } as Ward : w));
      toast({ title: "Ward Updated", description: "Ward information has been updated." });
    } else {
      const newWard: Ward = { ...wardForm as Ward, id: `WD${String(wards.length + 1).padStart(3, '0')}` };
      setWards(prev => [...prev, newWard]);
      toast({ title: "Ward Added", description: "New ward has been added successfully." });
    }
    resetWardForm();
  };

  const resetWardForm = () => {
    setWardForm({ name: '', code: '', zoneId: '', population: 0, area: 0, totalPickupPoints: 0, status: 'active' });
    setEditingWard(null);
    setIsWardDialogOpen(false);
  };

  const openEditWardDialog = (ward: Ward) => {
    setEditingWard(ward);
    setWardForm(ward);
    setIsWardDialogOpen(true);
  };

  const filteredZones = zones.filter(z => z.name.toLowerCase().includes(searchQuery.toLowerCase()) || z.code.toLowerCase().includes(searchQuery.toLowerCase()));
  const filteredWards = wards.filter(w => w.name.toLowerCase().includes(searchQuery.toLowerCase()) || w.code.toLowerCase().includes(searchQuery.toLowerCase()));

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      <PageHeader
        category="Master Data"
        title="Zones & Wards"
        description="Manage geographical divisions, zones, and ward boundaries"
        icon={MapPin}
      />

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">Total Zones</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{zones.length}</div></CardContent>
        </Card>
        <Card className="bg-primary/10 border-primary/30">
          <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-primary">Total Wards</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold text-primary">{wards.length}</div></CardContent>
        </Card>
        <Card className="bg-secondary/10 border-secondary/30">
          <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-secondary">Total Population</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold text-secondary">{(wards.reduce((a, w) => a + w.population, 0) / 1000).toFixed(0)}K</div></CardContent>
        </Card>
        <Card className="bg-success/10 border-success/30">
          <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-success">Total Pickup Points</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold text-success">{wards.reduce((a, w) => a + w.totalPickupPoints, 0)}</div></CardContent>
        </Card>
      </div>

      <Tabs defaultValue="zones" className="space-y-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <TabsList>
            <TabsTrigger value="zones">Zones</TabsTrigger>
            <TabsTrigger value="wards">Wards</TabsTrigger>
          </TabsList>
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input placeholder="Search..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-10" />
          </div>
        </div>

        <TabsContent value="zones" className="space-y-4">
          <div className="flex justify-end">
            <Dialog open={isZoneDialogOpen} onOpenChange={(open) => { if (!open) resetZoneForm(); setIsZoneDialogOpen(open); }}>
              <DialogTrigger asChild><Button><Plus className="h-4 w-4 mr-2" /> Add Zone</Button></DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>{editingZone ? 'Edit Zone' : 'Add New Zone'}</DialogTitle>
                  <DialogDescription>Enter the zone details</DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2"><Label>Zone Name</Label><Input value={zoneForm.name} onChange={(e) => setZoneForm({ ...zoneForm, name: e.target.value })} /></div>
                    <div className="space-y-2"><Label>Zone Code</Label><Input value={zoneForm.code} onChange={(e) => setZoneForm({ ...zoneForm, code: e.target.value })} /></div>
                  </div>
                  <div className="space-y-2"><Label>Description</Label><Input value={zoneForm.description} onChange={(e) => setZoneForm({ ...zoneForm, description: e.target.value })} /></div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2"><Label>Supervisor Name</Label><Input value={zoneForm.supervisorName} onChange={(e) => setZoneForm({ ...zoneForm, supervisorName: e.target.value })} /></div>
                    <div className="space-y-2"><Label>Supervisor Phone</Label><Input value={zoneForm.supervisorPhone} onChange={(e) => setZoneForm({ ...zoneForm, supervisorPhone: e.target.value })} /></div>
                  </div>
                  <div className="space-y-2">
                    <Label>Status</Label>
                    <Select value={zoneForm.status} onValueChange={(v) => setZoneForm({ ...zoneForm, status: v as 'active' | 'inactive' })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent><SelectItem value="active">Active</SelectItem><SelectItem value="inactive">Inactive</SelectItem></SelectContent>
                    </Select>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={resetZoneForm}>Cancel</Button>
                  <Button onClick={handleZoneSubmit}>{editingZone ? 'Update' : 'Add'} Zone</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Zone</TableHead>
                    <TableHead>Supervisor</TableHead>
                    <TableHead>Wards</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredZones.map((zone) => (
                    <TableRow key={zone.id}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center"><MapPin className="h-5 w-5 text-primary" /></div>
                          <div>
                            <div className="font-medium">{zone.name}</div>
                            <div className="text-sm text-muted-foreground">{zone.code} • {zone.description}</div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">{zone.supervisorName}</div>
                        <div className="text-xs text-muted-foreground">{zone.supervisorPhone}</div>
                      </TableCell>
                      <TableCell><Badge variant="outline">{wards.filter(w => w.zoneId === zone.id).length} wards</Badge></TableCell>
                      <TableCell>{getStatusBadge(zone.status)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button variant="ghost" size="icon" onClick={() => openEditZoneDialog(zone)}><Edit className="h-4 w-4" /></Button>
                          <Button variant="ghost" size="icon" className="text-destructive" onClick={() => setZones(prev => prev.filter(z => z.id !== zone.id))}><Trash2 className="h-4 w-4" /></Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="wards" className="space-y-4">
          <div className="flex justify-end">
            <Dialog open={isWardDialogOpen} onOpenChange={(open) => { if (!open) resetWardForm(); setIsWardDialogOpen(open); }}>
              <DialogTrigger asChild><Button><Plus className="h-4 w-4 mr-2" /> Add Ward</Button></DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>{editingWard ? 'Edit Ward' : 'Add New Ward'}</DialogTitle>
                  <DialogDescription>Enter the ward details</DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2"><Label>Ward Name</Label><Input value={wardForm.name} onChange={(e) => setWardForm({ ...wardForm, name: e.target.value })} /></div>
                    <div className="space-y-2"><Label>Ward Code</Label><Input value={wardForm.code} onChange={(e) => setWardForm({ ...wardForm, code: e.target.value })} /></div>
                  </div>
                  <div className="space-y-2">
                    <Label>Zone</Label>
                    <Select value={wardForm.zoneId} onValueChange={(v) => setWardForm({ ...wardForm, zoneId: v })}>
                      <SelectTrigger><SelectValue placeholder="Select zone" /></SelectTrigger>
                      <SelectContent>{zones.map(z => <SelectItem key={z.id} value={z.id}>{z.name}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2"><Label>Population</Label><Input type="number" value={wardForm.population} onChange={(e) => setWardForm({ ...wardForm, population: Number(e.target.value) })} /></div>
                    <div className="space-y-2"><Label>Area (km²)</Label><Input type="number" value={wardForm.area} onChange={(e) => setWardForm({ ...wardForm, area: Number(e.target.value) })} /></div>
                    <div className="space-y-2"><Label>Pickup Points</Label><Input type="number" value={wardForm.totalPickupPoints} onChange={(e) => setWardForm({ ...wardForm, totalPickupPoints: Number(e.target.value) })} /></div>
                  </div>
                  <div className="space-y-2">
                    <Label>Status</Label>
                    <Select value={wardForm.status} onValueChange={(v) => setWardForm({ ...wardForm, status: v as 'active' | 'inactive' })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent><SelectItem value="active">Active</SelectItem><SelectItem value="inactive">Inactive</SelectItem></SelectContent>
                    </Select>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={resetWardForm}>Cancel</Button>
                  <Button onClick={handleWardSubmit}>{editingWard ? 'Update' : 'Add'} Ward</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Ward</TableHead>
                    <TableHead>Zone</TableHead>
                    <TableHead>Population</TableHead>
                    <TableHead>Area</TableHead>
                    <TableHead>Pickup Points</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredWards.map((ward) => (
                    <TableRow key={ward.id}>
                      <TableCell>
                        <div className="font-medium">{ward.name}</div>
                        <div className="text-sm text-muted-foreground">{ward.code}</div>
                      </TableCell>
                      <TableCell><Badge variant="outline">{getZoneName(ward.zoneId)}</Badge></TableCell>
                      <TableCell><div className="flex items-center gap-1"><Users className="h-3 w-3" /> {(ward.population / 1000).toFixed(1)}K</div></TableCell>
                      <TableCell>{ward.area} km²</TableCell>
                      <TableCell>{ward.totalPickupPoints}</TableCell>
                      <TableCell>{getStatusBadge(ward.status)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button variant="ghost" size="icon" onClick={() => openEditWardDialog(ward)}><Edit className="h-4 w-4" /></Button>
                          <Button variant="ghost" size="icon" className="text-destructive" onClick={() => setWards(prev => prev.filter(w => w.id !== ward.id))}><Trash2 className="h-4 w-4" /></Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
