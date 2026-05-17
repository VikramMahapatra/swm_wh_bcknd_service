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
import { useRoutes, usePickupPoints, useZones, useZoneWards, useTrucks } from '@/hooks/useDataQueries';
import { Route, PickupPoint } from '@/data/masterData';
import { Plus, Search, Edit, Trash2, MapPin, Route as RouteIcon, Clock, Download, Loader2 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';

export default function MasterRoutesPickups() {
  const { toast } = useToast();
  const { data: routesData = [], isLoading: isLoadingRoutes } = useRoutes();
  const { data: pickupPointsData = [], isLoading: isLoadingPickupPoints } = usePickupPoints();
  const { data: zonesData = [], isLoading: isLoadingZones } = useZones();
  const { data: wardsData = [], isLoading: isLoadingWards } = useZoneWards();
  const { data: trucksData = [], isLoading: isLoadingTrucks } = useTrucks();
  
  const [routes, setRoutes] = useState<Route[]>([]);
  const [pickupPoints, setPickupPoints] = useState<PickupPoint[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isRouteDialogOpen, setIsRouteDialogOpen] = useState(false);
  const [isPickupDialogOpen, setIsPickupDialogOpen] = useState(false);
  const [editingRoute, setEditingRoute] = useState<Route | null>(null);
  const [editingPickup, setEditingPickup] = useState<PickupPoint | null>(null);

  useEffect(() => {
    setRoutes(routesData as Route[]);
  }, [routesData]);

  useEffect(() => {
    setPickupPoints(pickupPointsData as PickupPoint[]);
  }, [pickupPointsData]);
  
  const [zones, setZones] = useState([]);
  const [wards, setWards] = useState([]);
  const [trucks, setTrucks] = useState([]);
  
  const [routeForm, setRouteForm] = useState<Partial<Route>>({ name: '', code: '', type: 'primary', wardId: '', zoneId: '', assignedTruckId: '', totalPickupPoints: 0, estimatedDistance: 0, estimatedTime: 0, status: 'active' });
  const [pickupForm, setPickupForm] = useState<Partial<PickupPoint>>({ pointCode: '', name: '', address: '', latitude: 0, longitude: 0, routeId: '', wardId: '', wasteType: 'mixed', expectedPickupTime: '', geofenceRadius: 30, status: 'active' });

  useEffect(() => {
    setZones(zonesData);
  }, [zonesData]);

  useEffect(() => {
    setWards(wardsData);
  }, [wardsData]);

  useEffect(() => {
    setTrucks(trucksData as any);
  }, [trucksData]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active': return <Badge className="bg-success/20 text-success border-success/30">Active</Badge>;
      case 'inactive': return <Badge variant="secondary">Inactive</Badge>;
      case 'overflow': return <Badge className="bg-destructive/20 text-destructive border-destructive/30">Overflow</Badge>;
      default: return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getWasteTypeBadge = (type: string) => {
    const colors: Record<string, string> = {
      'dry': 'bg-amber-500/20 text-amber-600 border-amber-500/30',
      'wet': 'bg-green-500/20 text-green-600 border-green-500/30',
      'mixed': 'bg-blue-500/20 text-blue-600 border-blue-500/30',
      'hazardous': 'bg-red-500/20 text-red-600 border-red-500/30'
    };
    return <Badge className={colors[type] || ''}>{type}</Badge>;
  };

  const getZoneName = (zoneId: string) => zones.find(z => z.id === zoneId)?.name || 'Unknown';
  const getWardName = (wardId: string) => wards.find(w => w.id === wardId)?.name || 'Unknown';
  const getRouteName = (routeId: string) => routes.find(r => r.id === routeId)?.name || 'Unknown';
  const getTruckReg = (truckId?: string) => truckId ? trucks.find(t => t.id === truckId)?.registrationNumber || 'Unknown' : 'Not Assigned';

  // Route handlers
  const handleRouteSubmit = () => {
    if (editingRoute) {
      setRoutes(prev => prev.map(r => r.id === editingRoute.id ? { ...r, ...routeForm } as Route : r));
      toast({ title: "Route Updated", description: "Route information has been updated." });
    } else {
      const newRoute: Route = { ...routeForm as Route, id: `RT${String(routes.length + 1).padStart(3, '0')}` };
      setRoutes(prev => [...prev, newRoute]);
      toast({ title: "Route Added", description: "New route has been added successfully." });
    }
    resetRouteForm();
  };

  const resetRouteForm = () => {
    setRouteForm({ name: '', code: '', type: 'primary', wardId: '', zoneId: '', assignedTruckId: '', totalPickupPoints: 0, estimatedDistance: 0, estimatedTime: 0, status: 'active' });
    setEditingRoute(null);
    setIsRouteDialogOpen(false);
  };

  // Pickup handlers
  const handlePickupSubmit = () => {
    if (editingPickup) {
      setPickupPoints(prev => prev.map(p => p.id === editingPickup.id ? { ...p, ...pickupForm } as PickupPoint : p));
      toast({ title: "Pickup Point Updated", description: "Pickup point has been updated." });
    } else {
      const newPickup: PickupPoint = { ...pickupForm as PickupPoint, id: `PP${String(pickupPoints.length + 1).padStart(3, '0')}` };
      setPickupPoints(prev => [...prev, newPickup]);
      toast({ title: "Pickup Point Added", description: "New pickup point has been added." });
    }
    resetPickupForm();
  };

  const resetPickupForm = () => {
    setPickupForm({ pointCode: '', name: '', address: '', latitude: 0, longitude: 0, routeId: '', wardId: '', wasteType: 'mixed', expectedPickupTime: '', geofenceRadius: 30, status: 'active' });
    setEditingPickup(null);
    setIsPickupDialogOpen(false);
  };

  const filteredRoutes = routes.filter(r => r.name.toLowerCase().includes(searchQuery.toLowerCase()) || r.code.toLowerCase().includes(searchQuery.toLowerCase()));
  const filteredPickups = pickupPoints.filter(p => p.name.toLowerCase().includes(searchQuery.toLowerCase()) || p.pointCode.toLowerCase().includes(searchQuery.toLowerCase()));

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      <PageHeader
        category="Master Data"
        title="Routes & Pickup Points"
        description="Manage collection routes and pickup locations across zones"
        icon={RouteIcon}
      />

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">Total Routes</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{routes.length}</div></CardContent>
        </Card>
        <Card className="bg-primary/10 border-primary/30">
          <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-primary">Primary Routes</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold text-primary">{routes.filter(r => r.type === 'primary').length}</div></CardContent>
        </Card>
        <Card className="bg-secondary/10 border-secondary/30">
          <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-secondary">Secondary Routes</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold text-secondary">{routes.filter(r => r.type === 'secondary').length}</div></CardContent>
        </Card>
        <Card className="bg-success/10 border-success/30">
          <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-success">Pickup Points</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold text-success">{pickupPoints.length}</div></CardContent>
        </Card>
        <Card className="bg-warning/10 border-warning/30">
          <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-warning">Active Points</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold text-warning">{pickupPoints.filter(p => p.status === 'active').length}</div></CardContent>
        </Card>
      </div>

      <Tabs defaultValue="routes" className="space-y-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <TabsList>
            <TabsTrigger value="routes">Routes</TabsTrigger>
            <TabsTrigger value="pickups">Pickup Points</TabsTrigger>
          </TabsList>
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input placeholder="Search..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-10" />
          </div>
        </div>

        <TabsContent value="routes" className="space-y-4">
          <div className="flex justify-end">
            <Dialog open={isRouteDialogOpen} onOpenChange={(open) => { if (!open) resetRouteForm(); setIsRouteDialogOpen(open); }}>
              <DialogTrigger asChild><Button><Plus className="h-4 w-4 mr-2" /> Add Route</Button></DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader>
                  <DialogTitle>{editingRoute ? 'Edit Route' : 'Add New Route'}</DialogTitle>
                  <DialogDescription>Enter the route details</DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2"><Label>Route Name</Label><Input value={routeForm.name} onChange={(e) => setRouteForm({ ...routeForm, name: e.target.value })} /></div>
                    <div className="space-y-2"><Label>Route Code</Label><Input value={routeForm.code} onChange={(e) => setRouteForm({ ...routeForm, code: e.target.value })} /></div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Type</Label>
                      <Select value={routeForm.type} onValueChange={(v) => setRouteForm({ ...routeForm, type: v as 'primary' | 'secondary' })}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent><SelectItem value="primary">Primary</SelectItem><SelectItem value="secondary">Secondary</SelectItem></SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Zone</Label>
                      <Select value={routeForm.zoneId} onValueChange={(v) => setRouteForm({ ...routeForm, zoneId: v })}>
                        <SelectTrigger><SelectValue placeholder="Select zone" /></SelectTrigger>
                        <SelectContent>{zones.map(z => <SelectItem key={z.id} value={z.id}>{z.name}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Ward</Label>
                      <Select value={routeForm.wardId} onValueChange={(v) => setRouteForm({ ...routeForm, wardId: v })}>
                        <SelectTrigger><SelectValue placeholder="Select ward" /></SelectTrigger>
                        <SelectContent>{wards.filter(w => !routeForm.zoneId || w.zoneId === routeForm.zoneId).map(w => <SelectItem key={w.id} value={w.id}>{w.name}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Assigned Truck</Label>
                      <Select value={routeForm.assignedTruckId || 'none'} onValueChange={(v) => setRouteForm({ ...routeForm, assignedTruckId: v === 'none' ? '' : v })}>
                        <SelectTrigger><SelectValue placeholder="Select truck" /></SelectTrigger>
                        <SelectContent><SelectItem value="none">Not Assigned</SelectItem>{trucks.filter(t => t.status === 'active').map(t => <SelectItem key={t.id} value={t.id}>{t.registrationNumber}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2"><Label>Pickup Points</Label><Input type="number" value={routeForm.totalPickupPoints} onChange={(e) => setRouteForm({ ...routeForm, totalPickupPoints: Number(e.target.value) })} /></div>
                    <div className="space-y-2"><Label>Distance (km)</Label><Input type="number" value={routeForm.estimatedDistance} onChange={(e) => setRouteForm({ ...routeForm, estimatedDistance: Number(e.target.value) })} /></div>
                    <div className="space-y-2"><Label>Time (min)</Label><Input type="number" value={routeForm.estimatedTime} onChange={(e) => setRouteForm({ ...routeForm, estimatedTime: Number(e.target.value) })} /></div>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={resetRouteForm}>Cancel</Button>
                  <Button onClick={handleRouteSubmit}>{editingRoute ? 'Update' : 'Add'} Route</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Route</TableHead>
                    <TableHead>Zone / Ward</TableHead>
                    <TableHead>Truck</TableHead>
                    <TableHead>Points</TableHead>
                    <TableHead>Distance / Time</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRoutes.map((route) => (
                    <TableRow key={route.id}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center"><RouteIcon className="h-5 w-5 text-primary" /></div>
                          <div>
                            <div className="font-medium">{route.name}</div>
                            <Badge variant="outline" className="text-xs">{route.type}</Badge>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">{getZoneName(route.zoneId)}</div>
                        <div className="text-xs text-muted-foreground">{getWardName(route.wardId)}</div>
                      </TableCell>
                      <TableCell><Badge variant="outline">{getTruckReg(route.assignedTruckId)}</Badge></TableCell>
                      <TableCell>{route.totalPickupPoints}</TableCell>
                      <TableCell>
                        <div className="text-sm">{route.estimatedDistance} km</div>
                        <div className="text-xs text-muted-foreground flex items-center gap-1"><Clock className="h-3 w-3" /> {route.estimatedTime} min</div>
                      </TableCell>
                      <TableCell>{getStatusBadge(route.status)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button variant="ghost" size="icon" onClick={() => { setEditingRoute(route); setRouteForm(route); setIsRouteDialogOpen(true); }}><Edit className="h-4 w-4" /></Button>
                          <Button variant="ghost" size="icon" className="text-destructive" onClick={() => setRoutes(prev => prev.filter(r => r.id !== route.id))}><Trash2 className="h-4 w-4" /></Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="pickups" className="space-y-4">
          <div className="flex justify-end">
            <Dialog open={isPickupDialogOpen} onOpenChange={(open) => { if (!open) resetPickupForm(); setIsPickupDialogOpen(open); }}>
              <DialogTrigger asChild><Button><Plus className="h-4 w-4 mr-2" /> Add Pickup Point</Button></DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader>
                  <DialogTitle>{editingPickup ? 'Edit Pickup Point' : 'Add New Pickup Point'}</DialogTitle>
                  <DialogDescription>Enter pickup point details</DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4 max-h-[60vh] overflow-y-auto">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2"><Label>Point Code</Label><Input value={pickupForm.pointCode} onChange={(e) => setPickupForm({ ...pickupForm, pointCode: e.target.value })} /></div>
                    <div className="space-y-2"><Label>Name</Label><Input value={pickupForm.name} onChange={(e) => setPickupForm({ ...pickupForm, name: e.target.value })} /></div>
                  </div>
                  <div className="space-y-2"><Label>Address</Label><Input value={pickupForm.address} onChange={(e) => setPickupForm({ ...pickupForm, address: e.target.value })} /></div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2"><Label>Latitude</Label><Input type="number" step="0.0001" value={pickupForm.latitude} onChange={(e) => setPickupForm({ ...pickupForm, latitude: Number(e.target.value) })} /></div>
                    <div className="space-y-2"><Label>Longitude</Label><Input type="number" step="0.0001" value={pickupForm.longitude} onChange={(e) => setPickupForm({ ...pickupForm, longitude: Number(e.target.value) })} /></div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Route</Label>
                      <Select value={pickupForm.routeId} onValueChange={(v) => setPickupForm({ ...pickupForm, routeId: v })}>
                        <SelectTrigger><SelectValue placeholder="Select route" /></SelectTrigger>
                        <SelectContent>{routes.map(r => <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Waste Type</Label>
                      <Select value={pickupForm.wasteType} onValueChange={(v) => setPickupForm({ ...pickupForm, wasteType: v as PickupPoint['wasteType'] })}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent><SelectItem value="dry">Dry</SelectItem><SelectItem value="wet">Wet</SelectItem><SelectItem value="mixed">Mixed</SelectItem><SelectItem value="hazardous">Hazardous</SelectItem></SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2"><Label>Pickup Time</Label><Input type="time" value={pickupForm.expectedPickupTime} onChange={(e) => setPickupForm({ ...pickupForm, expectedPickupTime: e.target.value })} /></div>
                    <div className="space-y-2"><Label>Geofence (m)</Label><Input type="number" value={pickupForm.geofenceRadius} onChange={(e) => setPickupForm({ ...pickupForm, geofenceRadius: Number(e.target.value) })} /></div>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={resetPickupForm}>Cancel</Button>
                  <Button onClick={handlePickupSubmit}>{editingPickup ? 'Update' : 'Add'} Pickup Point</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Pickup Point</TableHead>
                    <TableHead>Route</TableHead>
                    <TableHead>Waste Type</TableHead>
                    <TableHead>Schedule</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredPickups.map((pickup) => (
                    <TableRow key={pickup.id}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-full bg-success/10 flex items-center justify-center"><MapPin className="h-5 w-5 text-success" /></div>
                          <div>
                            <div className="font-medium">{pickup.name}</div>
                            <div className="text-sm text-muted-foreground">{pickup.pointCode}</div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell><Badge variant="outline">{getRouteName(pickup.routeId)}</Badge></TableCell>
                      <TableCell>{getWasteTypeBadge(pickup.wasteType)}</TableCell>
                      <TableCell><div className="flex items-center gap-1"><Clock className="h-3 w-3" /> {pickup.expectedPickupTime}</div></TableCell>
                      <TableCell>{getStatusBadge(pickup.status)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button variant="ghost" size="icon" onClick={() => { setEditingPickup(pickup); setPickupForm(pickup); setIsPickupDialogOpen(true); }}><Edit className="h-4 w-4" /></Button>
                          <Button variant="ghost" size="icon" className="text-destructive" onClick={() => setPickupPoints(prev => prev.filter(p => p.id !== pickup.id))}><Trash2 className="h-4 w-4" /></Button>
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
