import { useState, useEffect } from 'react';
import { GoogleMap, Polygon } from '@react-google-maps/api';
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
import { useRoutes, useWards, useZones } from '@/hooks/useDataQueries';
import { Zone, Ward } from '@/data/masterData';
import { Plus, Search, Edit, Trash2, MapPin, Users, Download, Loader2, Globe } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { apiService } from '@/services/api';

export default function MasterZonesWards() {
  const { toast } = useToast();
  const { data: zonesData, isLoading: isLoadingZones, refetch: refetchZones } = useZones();
  const [selectedZoneId, setSelectedZoneId] = useState<string>("");
  const { data: wardsData, isLoading: isLoadingWards, refetch: refetchWards } = useWards();
  const [geofenceFor, setGeofenceFor] = useState<'zone' | 'ward' | 'route'>('zone');
  const [geofenceZoneId, setGeofenceZoneId] = useState<string>('');
  const [geofenceWardId, setGeofenceWardId] = useState<string>('');
  const [geofenceRouteId, setGeofenceRouteId] = useState<string>('');
  const { data: routesData } = useRoutes({
    zone_id: geofenceZoneId || undefined,
    ward_id: geofenceWardId || undefined,
  });
  
  const [zones, setZones] = useState<Zone[]>([]);
  const [wards, setWards] = useState<Ward[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isZoneDialogOpen, setIsZoneDialogOpen] = useState(false);
  const [isWardDialogOpen, setIsWardDialogOpen] = useState(false);
  const [editingZone, setEditingZone] = useState<Zone | null>(null);
  const [editingWard, setEditingWard] = useState<Ward | null>(null);
  const [geofences, setGeofences] = useState<any[]>([]);
  const [isGeofenceDialogOpen, setIsGeofenceDialogOpen] = useState(false);
  const [editingGeofence, setEditingGeofence] = useState<any | null>(null);
  const [isGeofenceMapOpen, setIsGeofenceMapOpen] = useState(false);
  const [selectedGeofenceForMap, setSelectedGeofenceForMap] = useState<any | null>(null);
  const [geofenceCsvFile, setGeofenceCsvFile] = useState<File | null>(null);
  const [isUploadingGeofenceCsv, setIsUploadingGeofenceCsv] = useState(false);
  const [isSubmittingGeofence, setIsSubmittingGeofence] = useState(false);
  const [isLoadingGeofences, setIsLoadingGeofences] = useState(false);
  const [geofenceForm, setGeofenceForm] = useState({
    geofenceCode: '',
    geofenceName: '',
    geofenceType: 'zone' as 'zone' | 'depot' | 'landfill' | 'parking' | 'maintenance',
    coordinates: '',
  });

  useEffect(() => {
    if (zonesData) {
      setZones(zonesData);
    }
  }, [zonesData]);

  useEffect(() => {
    if (!selectedZoneId && zonesData && zonesData.length > 0) {
      setSelectedZoneId(zonesData[0].id);
    }
  }, [selectedZoneId, zonesData]);

  useEffect(() => {
    if (wardsData) {
      setWards(wardsData);
    }
  }, [wardsData]);

  useEffect(() => {
    if (!geofenceZoneId && zonesData && zonesData.length > 0) {
      setGeofenceZoneId(zonesData[0].id);
    }
  }, [geofenceZoneId, zonesData]);

  useEffect(() => {
    setGeofenceWardId('');
    setGeofenceRouteId('');
  }, [geofenceZoneId, geofenceFor]);

  useEffect(() => {
    setGeofenceRouteId('');
  }, [geofenceWardId]);

  const loadGeofences = async () => {
    setIsLoadingGeofences(true);
    try {
      // Load all pages so existing DB records are visible even when
      // they don't match currently selected create-form filters.
      const pageSize = 200;
      let page = 1;
      let allRows: any[] = [];
      while (true) {
        const rows = await apiService.getGeofences({
          page,
          page_size: pageSize,
        });
        allRows = allRows.concat(rows);
        if (rows.length < pageSize) break;
        page += 1;
      }
      setGeofences(allRows);
    } catch (error) {
      toast({
        title: "Load Failed",
        description: error instanceof Error ? error.message : "Unable to load geofences.",
        variant: "destructive",
      });
    } finally {
      setIsLoadingGeofences(false);
    }
  };
  
  useEffect(() => {
    loadGeofences();
  }, []);
  
  const [zoneForm, setZoneForm] = useState<Partial<Zone>>({ name: '', code: '', description: '', supervisorName: '', supervisorPhone: '', totalWards: 0, status: 'active' });
  const [wardForm, setWardForm] = useState<Partial<Ward>>({ name: '', code: '', zoneId: '', population: 0, area: 0, totalPickupPoints: 0, status: 'active' });

  const getStatusBadge = (status: string) => {
    return status === 'active' 
      ? <Badge className="bg-success/20 text-success border-success/30">Active</Badge>
      : <Badge variant="secondary">Inactive</Badge>;
  };

  const getZoneName = (zoneId: string) => zones.find(z => z.id === zoneId)?.name || 'Unknown';

  // Zone handlers
  const handleZoneSubmit = async () => {
    if (editingZone) {
      setZones(prev => prev.map(z => z.id === editingZone.id ? { ...z, ...zoneForm } as Zone : z));
      toast({ title: "Zone Updated", description: "Zone information has been updated." });
    } else {
      const normalizedCode = String(zoneForm.code || '').trim().toUpperCase();
      const normalizedName = String(zoneForm.name || '').trim();
      if (!normalizedName) {
        toast({ title: "Validation Error", description: "Zone name is required.", variant: "destructive" });
        return;
      }
      if (!normalizedCode || !/^[A-Z0-9_-]{2,32}$/.test(normalizedCode)) {
        toast({
          title: "Validation Error",
          description: "Zone code must be 2-32 chars and use A-Z, 0-9, _ or -.",
          variant: "destructive",
        });
        return;
      }
      await apiService.createZone({
        code: normalizedCode,
        name: normalizedName,
        status: (zoneForm.status as 'active' | 'inactive') || 'active',
      });
      await refetchZones();
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
  const handleWardSubmit = async () => {
    if (editingWard) {
      setWards(prev => prev.map(w => w.id === editingWard.id ? { ...w, ...wardForm } as Ward : w));
      toast({ title: "Ward Updated", description: "Ward information has been updated." });
    } else {
      const targetZoneId = String(wardForm.zoneId || '').trim();
      const zoneName = zones.find((z) => z.id === targetZoneId)?.name || '';
      if (!targetZoneId || !zoneName) {
        toast({ title: "Validation Error", description: "Please select a valid zone.", variant: "destructive" });
        return;
      }
      await apiService.createWard({
        code: String(wardForm.code || '').trim(),
        name: String(wardForm.name || '').trim(),
        zoneName,
        status: (wardForm.status as 'active' | 'inactive') || 'active',
      });
      if (selectedZoneId !== targetZoneId) {
        setSelectedZoneId(targetZoneId);
      } else {
        await refetchWards();
      }
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

  const filteredZones = zones.filter(z =>
    (z.name && z.name.toLowerCase().includes(searchQuery.toLowerCase())) ||
    (z.code && z.code.toLowerCase().includes(searchQuery.toLowerCase()))
  );
  const filteredWards = wards.filter(w =>
    (w.name && w.name.toLowerCase().includes(searchQuery.toLowerCase())) ||
    (w.code && w.code.toLowerCase().includes(searchQuery.toLowerCase()))
  );
  const totalPopulation = wards.reduce((a, w) => a + (Number(w.population) || 0), 0);
  const totalPickupPoints = wards.reduce((a, w) => a + (Number(w.totalPickupPoints) || 0), 0);
  const wardOptionsForGeofence = wards.filter((w) => !geofenceZoneId || w.zoneId === geofenceZoneId);
  const routeOptionsForGeofence = (Array.isArray(routesData) ? routesData : []).filter((route: any) => {
    const routeZoneId = String(route.zone_id ?? route.zoneId ?? '');
    const routeWardId = String(route.ward_id ?? route.wardId ?? '');
    const zoneMatches = !geofenceZoneId || routeZoneId === geofenceZoneId;
    const wardMatches = !geofenceWardId || routeWardId === geofenceWardId;
    return zoneMatches && wardMatches;
  });
  const parseGeofencePolygonPath = (geofence: any): Array<{ lat: number; lng: number }> => {
    const source = geofence?.polygon;
    let polygonValue: any = source;
    if (typeof source === 'string') {
      try {
        polygonValue = JSON.parse(source);
      } catch {
        polygonValue = null;
      }
    }
    const ring = polygonValue?.coordinates?.[0];
    if (!Array.isArray(ring)) return [];
    return ring
      .map((point: any) => {
        const lng = Number(point?.[0]);
        const lat = Number(point?.[1]);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
        return { lat, lng };
      })
      .filter(Boolean) as Array<{ lat: number; lng: number }>;
  };
  const selectedGeofencePath = selectedGeofenceForMap ? parseGeofencePolygonPath(selectedGeofenceForMap) : [];
  const selectedGeofenceCenter =
    selectedGeofencePath.length > 0
      ? {
          lat: selectedGeofencePath.reduce((sum, p) => sum + p.lat, 0) / selectedGeofencePath.length,
          lng: selectedGeofencePath.reduce((sum, p) => sum + p.lng, 0) / selectedGeofencePath.length,
        }
      : { lat: 18.5204, lng: 73.8567 };

  const parseCoordinatesToPolygon = (raw: string) => {
    const chunks = raw.split(';').map((part) => part.trim()).filter(Boolean);
    if (chunks.length < 3) {
      throw new Error('Coordinates must include at least 3 points.');
    }
    const points: number[][] = chunks.map((chunk) => {
      const pair = chunk.split(',').map((token) => token.trim());
      if (pair.length !== 2) {
        throw new Error('Invalid coordinates format. Use lat,lng;lat,lng;...');
      }
      const lat = Number(pair[0]);
      const lng = Number(pair[1]);
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
        throw new Error('Coordinates must be valid numbers.');
      }
      return [lng, lat];
    });
    if (points[0][0] !== points[points.length - 1][0] || points[0][1] !== points[points.length - 1][1]) {
      points.push(points[0]);
    }
    return { type: 'Polygon', coordinates: [points] };
  };

  const resetGeofenceForm = () => {
    setGeofenceForm({ geofenceCode: '', geofenceName: '', geofenceType: 'zone', coordinates: '' });
    setEditingGeofence(null);
    setIsGeofenceDialogOpen(false);
  };

  const handleCreateGeofence = async () => {
    if (!geofenceForm.geofenceCode.trim() || !geofenceForm.geofenceName.trim() || !geofenceForm.coordinates.trim()) {
      toast({ title: "Validation Error", description: "Code, name and coordinates are required.", variant: "destructive" });
      return;
    }
    if (!geofenceZoneId || (geofenceFor !== 'zone' && !geofenceWardId) || (geofenceFor === 'route' && !geofenceRouteId)) {
      toast({ title: "Validation Error", description: "Please select required Zone/Ward/Route context.", variant: "destructive" });
      return;
    }
    setIsSubmittingGeofence(true);
    try {
      const payload = {
        geofence_code: geofenceForm.geofenceCode.trim().toUpperCase(),
        geofence_name: geofenceForm.geofenceName.trim(),
        type: geofenceForm.geofenceType,
        geometry_type: 'polygon' as const,
        geofence_for: geofenceFor,
        zone_id: geofenceZoneId,
        ward_id: geofenceFor === 'zone' ? null : geofenceWardId || null,
        route_id: geofenceFor === 'route' ? geofenceRouteId || null : null,
        polygon: parseCoordinatesToPolygon(geofenceForm.coordinates),
      };
      if (editingGeofence) {
        await apiService.updateGeofence(String(editingGeofence.id), payload);
      } else {
        await apiService.createGeofence(payload);
      }
      await loadGeofences();
      toast({ title: editingGeofence ? "Geofence Updated" : "Geofence Added", description: "Geofence has been saved successfully." });
      resetGeofenceForm();
    } catch (error) {
      toast({
        title: "Create Failed",
        description: error instanceof Error ? error.message : "Unable to create geofence.",
        variant: "destructive",
      });
    } finally {
      setIsSubmittingGeofence(false);
    }
  };
  
  const handleGeofenceCsvUpload = async () => {
    if (!geofenceCsvFile) {
      toast({ title: "File Required", description: "Please choose a CSV file first.", variant: "destructive" });
      return;
    }
    if (!geofenceZoneId || (geofenceFor !== 'zone' && !geofenceWardId) || (geofenceFor === 'route' && !geofenceRouteId)) {
      toast({ title: "Validation Error", description: "Please select required Zone/Ward/Route context.", variant: "destructive" });
      return;
    }
    setIsUploadingGeofenceCsv(true);
    try {
      const text = await geofenceCsvFile.text();
      const rows = text
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean)
        .filter((line) => line.toLowerCase() !== 'coordinates');

      const csvLines = [
        "geofence_code,geofence_name,type,geometry_type,geofence_for,zone_id,ward_id,route_id,coordinates",
      ];
      rows.forEach((coordinates, index) => {
        const suffix = String(index + 1).padStart(3, '0');
        const codeBase = (geofenceForm.geofenceCode || 'GEO').trim().toUpperCase().replace(/[^A-Z0-9_-]/g, '');
        const nameBase = (geofenceForm.geofenceName || 'Geofence').trim();
        csvLines.push(
          `${codeBase}_${suffix},${nameBase} ${suffix},${geofenceForm.geofenceType},polygon,${geofenceFor},${geofenceZoneId},${geofenceFor === 'zone' ? '' : geofenceWardId},${geofenceFor === 'route' ? geofenceRouteId : ''},"${coordinates}"`,
        );
      });
      if (csvLines.length === 1) {
        throw new Error('CSV has no coordinate rows.');
      }
      const payloadFile = new File([csvLines.join("\n")], "geofence_import.csv", { type: "text/csv" });
      const result = await apiService.uploadGeofencesCsv(payloadFile);
      const created = Number(result?.created ?? 0);
      toast({
        title: "Geofences Uploaded",
        description: `Imported ${created} geofence row(s) successfully.`,
      });
      setGeofenceCsvFile(null);
      await loadGeofences();
    } catch (error) {
      toast({
        title: "Upload Failed",
        description: error instanceof Error ? error.message : "Unable to upload geofence CSV.",
        variant: "destructive",
      });
    } finally {
      setIsUploadingGeofenceCsv(false);
    }
  };

  const downloadGeofenceCsvSample = () => {
    const sample = [
      "coordinates",
      "\"18.5302,73.8567;18.5312,73.8577;18.5322,73.8565;18.5302,73.8567\"",
      "\"18.5401,73.8601;18.5410,73.8614;18.5420,73.8600;18.5401,73.8601\"",
    ].join("\n");
    const blob = new Blob([sample], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "geofence_import_sample.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const openEditGeofenceDialog = (geofence: any) => {
    const forType = String(geofence.geofence_for || (geofence.route_id ? 'route' : geofence.ward_id ? 'ward' : 'zone')) as
      | 'zone'
      | 'ward'
      | 'route';
    const polygonPath = parseGeofencePolygonPath(geofence);
    const coords = polygonPath.map((p) => `${p.lat},${p.lng}`).join(';');
    setEditingGeofence(geofence);
    setGeofenceFor(forType);
    setGeofenceZoneId(String(geofence.zone_id || ''));
    setGeofenceWardId(String(geofence.ward_id || ''));
    setGeofenceRouteId(String(geofence.route_id || ''));
    setGeofenceForm({
      geofenceCode: String(geofence.geofence_code || ''),
      geofenceName: String(geofence.geofence_name || ''),
      geofenceType: (String(geofence.type || 'zone') as 'zone' | 'depot' | 'landfill' | 'parking' | 'maintenance'),
      coordinates: coords,
    });
    setIsGeofenceDialogOpen(true);
  };

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
          <CardContent><div className="text-2xl font-bold text-secondary">{(totalPopulation / 1000).toFixed(0)}K</div></CardContent>
        </Card>
        <Card className="bg-success/10 border-success/30">
          <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-success">Total Pickup Points</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold text-success">{totalPickupPoints}</div></CardContent>
        </Card>
      </div>

      <Tabs defaultValue="zones" className="space-y-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <TabsList>
            <TabsTrigger value="zones">Zones</TabsTrigger>
            <TabsTrigger value="wards">Wards</TabsTrigger>
            <TabsTrigger value="geofences">Geofences</TabsTrigger>
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

        <TabsContent value="geofences" className="space-y-4">
          <div className="flex justify-end">
            <Dialog open={isGeofenceDialogOpen} onOpenChange={(open) => { if (!open) resetGeofenceForm(); setIsGeofenceDialogOpen(open); }}>
              <DialogTrigger asChild><Button><Plus className="h-4 w-4 mr-2" /> Add Geofence</Button></DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>{editingGeofence ? 'Edit Geofence' : 'Add New Geofence'}</DialogTitle>
                  <DialogDescription>Create a polygon geofence for Zone, Ward, or Route context.</DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="space-y-2">
                    <Label>Geofence For</Label>
                    <Select value={geofenceFor} onValueChange={(value) => setGeofenceFor(value as 'zone' | 'ward' | 'route')}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="zone">Zone</SelectItem>
                        <SelectItem value="ward">Ward</SelectItem>
                        <SelectItem value="route">Route</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Select Zone</Label>
                    <Select value={geofenceZoneId} onValueChange={setGeofenceZoneId}>
                      <SelectTrigger><SelectValue placeholder="Select zone" /></SelectTrigger>
                      <SelectContent>
                        {zones.map((zone) => <SelectItem key={zone.id} value={zone.id}>{zone.name}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  {geofenceFor !== 'zone' ? (
                    <div className="space-y-2">
                      <Label>Select Ward</Label>
                      <Select value={geofenceWardId} onValueChange={setGeofenceWardId}>
                        <SelectTrigger><SelectValue placeholder="Select ward" /></SelectTrigger>
                        <SelectContent>
                          {wardOptionsForGeofence.map((ward) => <SelectItem key={ward.id} value={ward.id}>{ward.name}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                  ) : null}
                  {geofenceFor === 'route' ? (
                    <div className="space-y-2">
                      <Label>Select Route</Label>
                      <Select value={geofenceRouteId} onValueChange={setGeofenceRouteId}>
                        <SelectTrigger><SelectValue placeholder="Select route" /></SelectTrigger>
                        <SelectContent>
                          {routeOptionsForGeofence.map((route: any) => (
                            <SelectItem key={String(route.id ?? route.route_id)} value={String(route.id ?? route.route_id)}>
                              {String(route.route_name ?? route.name ?? route.route_code ?? route.code ?? route.id)}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  ) : null}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2"><Label>Geofence Code</Label><Input value={geofenceForm.geofenceCode} onChange={(e) => setGeofenceForm((prev) => ({ ...prev, geofenceCode: e.target.value }))} /></div>
                    <div className="space-y-2"><Label>Geofence Name</Label><Input value={geofenceForm.geofenceName} onChange={(e) => setGeofenceForm((prev) => ({ ...prev, geofenceName: e.target.value }))} /></div>
                  </div>
                  <div className="space-y-2">
                    <Label>Geofence Type</Label>
                    <Select value={geofenceForm.geofenceType} onValueChange={(value) => setGeofenceForm((prev) => ({ ...prev, geofenceType: value as 'zone' | 'depot' | 'landfill' | 'parking' | 'maintenance' }))}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="zone">Zone</SelectItem>
                        <SelectItem value="depot">Depot</SelectItem>
                        <SelectItem value="landfill">Landfill</SelectItem>
                        <SelectItem value="parking">Parking</SelectItem>
                        <SelectItem value="maintenance">Maintenance</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Coordinates</Label>
                    <Input
                      value={geofenceForm.coordinates}
                      onChange={(e) => setGeofenceForm((prev) => ({ ...prev, coordinates: e.target.value }))}
                      placeholder="lat,lng;lat,lng;lat,lng;lat,lng"
                    />
                  </div>
                  <div className="space-y-2 pt-2 border-t border-border/60">
                    <Label>Bulk Coordinates CSV</Label>
                    <div className="flex flex-col sm:flex-row gap-2">
                      <Input
                        type="file"
                        accept=".csv,text/csv"
                        onChange={(e) => setGeofenceCsvFile(e.target.files?.[0] || null)}
                      />
                      <Button type="button" variant="outline" onClick={downloadGeofenceCsvSample}>
                        <Download className="h-4 w-4 mr-2" />
                        Download Template
                      </Button>
                      <Button type="button" onClick={handleGeofenceCsvUpload} disabled={!geofenceCsvFile || isUploadingGeofenceCsv}>
                        {isUploadingGeofenceCsv ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                        Upload
                      </Button>
                    </div>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={resetGeofenceForm}>Cancel</Button>
                  <Button onClick={handleCreateGeofence} disabled={isSubmittingGeofence}>
                    {isSubmittingGeofence ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                    {editingGeofence ? 'Update Geofence' : 'Add Geofence'}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Geofence</TableHead>
                    <TableHead>Scope</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Geometry</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(isLoadingGeofences ? [] : geofences).map((geofence) => (
                    <TableRow key={String(geofence.id)}>
                      <TableCell>
                        <div className="font-medium">{String(geofence.geofence_name ?? '')}</div>
                        <div className="text-sm text-muted-foreground">{String(geofence.geofence_code ?? '')}</div>
                      </TableCell>
                      <TableCell><Badge variant="outline">{String(geofence.geofence_for ?? geofence.scope_type ?? '-')}</Badge></TableCell>
                      <TableCell>{String(geofence.type ?? '-')}</TableCell>
                      <TableCell>{String(geofence.geometry_type ?? '-')}</TableCell>
                      <TableCell>{getStatusBadge(geofence.active === false ? 'inactive' : 'active')}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Edit geofence"
                            onClick={() => openEditGeofenceDialog(geofence)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            title="View on map"
                            onClick={() => {
                              setSelectedGeofenceForMap(geofence);
                              setIsGeofenceMapOpen(true);
                            }}
                          >
                            <Globe className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-destructive"
                            onClick={async () => {
                              try {
                                await apiService.deleteGeofence(String(geofence.id));
                                await loadGeofences();
                                toast({ title: "Geofence Deleted", description: "Geofence removed successfully." });
                              } catch (error) {
                                toast({
                                  title: "Delete Failed",
                                  description: error instanceof Error ? error.message : "Unable to delete geofence.",
                                  variant: "destructive",
                                });
                              }
                            }}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                  {isLoadingGeofences ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-muted-foreground py-6">Loading geofences...</TableCell>
                    </TableRow>
                  ) : null}
                  {!isLoadingGeofences && geofences.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-muted-foreground py-6">No geofences found for selected filters.</TableCell>
                    </TableRow>
                  ) : null}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
          <Dialog open={isGeofenceMapOpen} onOpenChange={setIsGeofenceMapOpen}>
            <DialogContent className="max-w-4xl">
              <DialogHeader>
                <DialogTitle>Geofence Map View</DialogTitle>
                <DialogDescription>
                  {selectedGeofenceForMap
                    ? `${String(selectedGeofenceForMap.geofence_name ?? '')} (${String(selectedGeofenceForMap.geofence_code ?? '')})`
                    : 'Selected geofence polygon'}
                </DialogDescription>
              </DialogHeader>
              <div className="h-[480px] w-full rounded-md overflow-hidden border border-border/60">
                {selectedGeofencePath.length > 0 ? (
                  <GoogleMap
                    mapContainerStyle={{ width: '100%', height: '100%' }}
                    center={selectedGeofenceCenter}
                    zoom={15}
                    onLoad={(map) => {
                      if (!window.google?.maps || selectedGeofencePath.length === 0) return;
                      const bounds = new window.google.maps.LatLngBounds();
                      selectedGeofencePath.forEach((point) => bounds.extend(point));
                      map.fitBounds(bounds);
                    }}
                    options={{
                      streetViewControl: false,
                      mapTypeControl: false,
                      fullscreenControl: false,
                    }}
                  >
                    <Polygon
                      path={selectedGeofencePath}
                      options={{
                        fillColor: '#22c55e',
                        fillOpacity: 0.25,
                        strokeColor: '#15803d',
                        strokeOpacity: 0.95,
                        strokeWeight: 2,
                      }}
                    />
                  </GoogleMap>
                ) : (
                  <div className="h-full w-full flex items-center justify-center text-sm text-muted-foreground">
                    No valid polygon coordinates found for this geofence.
                  </div>
                )}
              </div>
            </DialogContent>
          </Dialog>

        </TabsContent>
      </Tabs>
    </div>
  );
}
