import { useState, useEffect } from 'react';
import { GoogleMap, Polyline, Marker, Polygon } from '@react-google-maps/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { useToast } from '@/hooks/use-toast';
import { useRoutes, usePickupPoints, useZones, useWards, useTrucks } from '@/hooks/useDataQueries';
import { apiService } from '@/services/api';
import { useQueryClient } from '@tanstack/react-query';
import { Route, PickupPoint } from '@/data/masterData';
import { Plus, Search, Edit, Trash2, MapPin, Route as RouteIcon, Clock, Globe, Maximize2, Minimize2 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { FieldError, RequiredMark, ValidationAlert, errorClass as validationErrorClass } from '@/components/FormValidation';

function normalizeRoute(route: any): Route {
  const routeId = String(route?.id ?? '');
  const path = Array.isArray(route?.polyline_coordinates)
    ? route.polyline_coordinates.map((point: any) => ({ lat: Number(point?.[1]), lng: Number(point?.[0]) })).filter((p: any) => Number.isFinite(p.lat) && Number.isFinite(p.lng))
    : [];

  return {
    id: routeId,
    name: String(route?.name ?? route?.route_name ?? ''),
    code: String(route?.code ?? route?.route_code ?? `R-${routeId.slice(0, 8)}`),
    type: (String(route?.type ?? route?.route_type ?? 'primary') === 'secondary' ? 'secondary' : 'primary') as Route['type'],
    wardId: String(route?.wardId ?? route?.ward_id ?? ''),
    zoneId: String(route?.zoneId ?? route?.zone_id ?? ''),
    assignedTruckId: route?.assignedTruckId ?? route?.assigned_truck_id,
    assignedTruck: route?.assignedTruck,
    totalPickupPoints: Number(route?.totalPickupPoints ?? route?.total_pickup_points ?? 0),
    estimatedDistance: 0,
    distance: '0 km',
    estimatedTime: 0,
    status: 'active',
    points: path,
    usesSpare: Boolean(route?.usesSpare),
    originalTruckId: route?.originalTruckId,
    spareActivatedAt: route?.spareActivatedAt,
  };
}

function normalizePickupPoint(point: any): PickupPoint {
  const latitude = Number(point?.latitude ?? point?.lat ?? 0);
  const longitude = Number(point?.longitude ?? point?.lng ?? 0);
  const sequenceNo = Number(point?.sequenceNo ?? point?.sequence_no ?? point?.order ?? 0) || 0;
  const geofenceRadius = Number(point?.geofenceRadius ?? point?.pickupRadiusM ?? point?.pickup_radius_m ?? point?.radius_m ?? point?.radiusM ?? 0) || 0;
  return {
    id: String(point?.id ?? ''),
    pointCode: sequenceNo ? `#${sequenceNo}` : String(point?.pointCode ?? point?.pickupCode ?? point?.pickup_code ?? ''),
    name: String(point?.name ?? point?.pickupName ?? point?.pickup_name ?? (sequenceNo ? `Pickup ${sequenceNo}` : 'Pickup Point')),
    address: '',
    latitude,
    longitude,
    zoneId: String(point?.zoneId ?? point?.zone_id ?? ''),
    routeId: String(point?.routeId ?? point?.route_id ?? ''),
    wardId: String(point?.wardId ?? point?.ward_id ?? ''),
    ward: String(point?.ward ?? ''),
    sequenceNo,
    wasteType: 'mixed',
    type: 'residential',
    expectedPickupTime: String(point?.expectedPickupTime ?? point?.expected_pickup_time ?? point?.pickupTimes ?? point?.pickup_times ?? ''),
    schedule: '',
    geofenceRadius,
    status: 'active',
    assignedRoute: String(point?.assignedRoute ?? ''),
    position: { lat: latitude, lng: longitude },
    lastCollection: point?.lastCollection,
  };
}

export default function MasterRoutesPickups() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data: routesData = [], isLoading: isLoadingRoutes } = useRoutes();
  const { data: pickupPointsData = [], isLoading: isLoadingPickupPoints } = usePickupPoints();
  const { data: zonesData = [], isLoading: isLoadingZones } = useZones();
  const { data: wardsData = [], isLoading: isLoadingWards } = useWards();
  const { data: trucksData = [], isLoading: isLoadingTrucks } = useTrucks();
  
  const [routes, setRoutes] = useState<Route[]>([]);
  const [pickupPoints, setPickupPoints] = useState<PickupPoint[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isRouteDialogOpen, setIsRouteDialogOpen] = useState(false);
  const [isPickupDialogOpen, setIsPickupDialogOpen] = useState(false);
  const [editingRoute, setEditingRoute] = useState<Route | null>(null);
  const [mapRoute, setMapRoute] = useState<Route | null>(null);
  const [mapPickupPoints, setMapPickupPoints] = useState<PickupPoint[]>([]);
  const [mapWardGeofencePath, setMapWardGeofencePath] = useState<Array<{ lat: number; lng: number }>>([]);
  const [isRouteMapOpen, setIsRouteMapOpen] = useState(false);
  const [isMapMaximized, setIsMapMaximized] = useState(false);
  const [routeMapInstance, setRouteMapInstance] = useState<any>(null);
  const [editingPickup, setEditingPickup] = useState<PickupPoint | null>(null);

  useEffect(() => {
    setRoutes((routesData as any[]).map(normalizeRoute));
  }, [routesData]);

  useEffect(() => {
    setPickupPoints((pickupPointsData as any[]).map(normalizePickupPoint));
  }, [pickupPointsData]);
  
  const [zones, setZones] = useState<any[]>([]);
  const [wards, setWards] = useState<any[]>([]);
  const [trucks, setTrucks] = useState<any[]>([]);
  
  const [routeForm, setRouteForm] = useState<Partial<Route> & { coordinates?: string }>({ name: '', code: '', type: 'primary', wardId: '', zoneId: '', assignedTruckId: '', totalPickupPoints: 0, estimatedDistance: 0, estimatedTime: 0, status: 'active', coordinates: '' });
  const [pickupForm, setPickupForm] = useState<Partial<PickupPoint> & { coordinates?: string; pickupTimes?: string; pickupRadiusM?: string | number }>({ name: '', zoneId: '', wardId: '', routeId: '', coordinates: '', pickupTimes: '', pickupRadiusM: '' });
  const [routeFormErrors, setRouteFormErrors] = useState<Record<string, string>>({});
  const [pickupFormErrors, setPickupFormErrors] = useState<Record<string, string>>({});
  const [validationOpen, setValidationOpen] = useState(false);
  const [validationSummary, setValidationSummary] = useState<string[]>([]);
  const [batchEditPoints, setBatchEditPoints] = useState<PickupPoint[] | null>(null);
  const [batchEditText, setBatchEditText] = useState('');

  useEffect(() => {
    setZones(zonesData);
  }, [zonesData]);

  useEffect(() => {
    setWards((wardsData as any[]).filter((w: any) => w?.zoneId || w?.zone_id));
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
  const setRouteField = (field: string, value: any) => {
    setRouteForm((current) => ({ ...current, [field]: value }));
    setRouteFormErrors((current) => {
      if (!current[field]) return current;
      const next = { ...current };
      delete next[field];
      return next;
    });
  };

  const setPickupField = (field: string, value: any) => {
    setPickupForm((current) => ({ ...current, [field]: value }));
    setPickupFormErrors((current) => {
      if (!current[field]) return current;
      const next = { ...current };
      delete next[field];
      return next;
    });
  };

  const handleRouteSubmit = async () => {
    try {
      const polylineCoordinates = String(routeForm.coordinates || '')
        .split(';')
        .map((part) => part.trim())
        .filter(Boolean)
        .map((part) => {
          const [lat, lng] = part.split(',').map((x) => Number(x.trim()));
          return [lng, lat];
        })
        .filter((point) => Number.isFinite(point[0]) && Number.isFinite(point[1]));
      const errors: Record<string, string> = {};
      if (!String(routeForm.name || '').trim()) errors.name = 'Route Name is required.';
      if (!routeForm.zoneId) errors.zoneId = 'Zone is required.';
      if (!routeForm.wardId) errors.wardId = 'Ward is required.';
      if (polylineCoordinates.length < 2) errors.coordinates = 'Please provide at least 2 coordinate points for route path.';
      if (Object.keys(errors).length > 0) {
        setRouteFormErrors(errors);
        setValidationSummary(Object.values(errors));
        setValidationOpen(true);
        return;
      }
      setRouteFormErrors({});
      setValidationSummary([]);
      const payload = {
        route_name: routeForm.name || '',
        route_type: (routeForm.type || 'primary') as 'primary' | 'secondary',
        zone_id: String(routeForm.zoneId || ''),
        ward_id: String(routeForm.wardId || ''),
        polyline_coordinates: polylineCoordinates,
      };

      let routeId = editingRoute?.id;
      if (editingRoute) {
        await apiService.updateRoute(editingRoute.id, payload);
      } else {
        const created = await apiService.createRoute(payload);
        routeId = String(created?.id || '');
      }

      if (routeForm.assignedTruckId && routeId) {
        await apiService.assignTruckRoute(routeForm.assignedTruckId, routeId);
      }

      const latestRoutes = await apiService.getRoutes();
      setRoutes((latestRoutes as any[]).map(normalizeRoute));
      await queryClient.invalidateQueries({ queryKey: ['routes'] });
      await queryClient.refetchQueries({ queryKey: ['routes'] });
      await queryClient.invalidateQueries({ queryKey: ['trucks'] });

      toast({
        title: editingRoute ? "Route Updated" : "Route Added",
        description: editingRoute
          ? "Route information has been updated."
          : "New route has been added successfully.",
      });
      resetRouteForm();
    } catch (error) {
      toast({
        title: "Unable to save route",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleRouteDelete = async (routeId: string) => {
    try {
      await apiService.deleteRoute(routeId);
      const latestRoutes = await apiService.getRoutes();
      setRoutes((latestRoutes as any[]).map(normalizeRoute));
      await queryClient.invalidateQueries({ queryKey: ['routes'] });
      await queryClient.invalidateQueries({ queryKey: ['trucks'] });
      toast({ title: "Route Deleted", description: "Route has been removed." });
    } catch (error) {
      toast({
        title: "Unable to delete route",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    }
  };

  const resetRouteForm = () => {
    setRouteForm({ name: '', code: '', type: 'primary', wardId: '', zoneId: '', assignedTruckId: '', totalPickupPoints: 0, estimatedDistance: 0, estimatedTime: 0, status: 'active', coordinates: '' });
    setEditingRoute(null);
    setRouteFormErrors({});
    setValidationOpen(false);
    setValidationSummary([]);
    setIsRouteDialogOpen(false);
  };

  // Pickup handlers
  const handlePickupSubmit = async () => {
    try {
      const parsedPoints = String(pickupForm.coordinates || '')
        .split(';')
        .map((part) => part.trim())
        .filter(Boolean)
        .map((part, index) => {
          const [lat, lng] = part.split(',').map((x) => Number(x.trim()));
          return { sequence_no: index + 1, lat, lng, pickup_name: pickupForm.name || undefined };
        })
        .filter((point) => Number.isFinite(point.lat) && Number.isFinite(point.lng));

      const errors: Record<string, string> = {};
      if (!pickupForm.zoneId) errors.zoneId = 'Zone is required.';
      if (!pickupForm.wardId) errors.wardId = 'Ward is required.';
      if (!pickupForm.routeId) errors.routeId = 'Route is required.';
      if (!editingPickup && parsedPoints.length === 0) errors.coordinates = 'Please provide at least one pickup coordinate.';
      if (Object.keys(errors).length > 0) {
        setPickupFormErrors(errors);
        setValidationSummary(Object.values(errors));
        setValidationOpen(true);
        return;
      }
      setPickupFormErrors({});
      setValidationSummary([]);

      const payload = {
        pickup_name: pickupForm.name || undefined,
        zone_id: pickupForm.zoneId,
        ward_id: pickupForm.wardId,
        route_id: pickupForm.routeId,
        expected_pickup_time: pickupForm.pickupTimes,
        pickup_radius_m:
          pickupForm.pickupRadiusM !== undefined && pickupForm.pickupRadiusM !== null && String(pickupForm.pickupRadiusM).trim() !== ''
            ? Number(pickupForm.pickupRadiusM)
            : undefined,
        ...(editingPickup
          ? {
              sequence_no: editingPickup.sequenceNo || 1,
              lat: parsedPoints[0]?.lat ?? pickupForm.latitude,
              lng: parsedPoints[0]?.lng ?? pickupForm.longitude,
            }
          : { pickup_points: parsedPoints }),
      };

      if (editingPickup) {
        await apiService.updatePickupPoint(editingPickup.id, payload);
        toast({ title: "Pickup Point Updated", description: "Pickup point has been updated." });
      } else {
        const created = await apiService.createPickupPoint(payload);
        const createdCount = Number(created?.created ?? parsedPoints.length) || parsedPoints.length;
        toast({ title: "Pickup Points Added", description: `${createdCount} pickup point${createdCount === 1 ? '' : 's'} added.` });
      }
      const latestPickups = await apiService.getPickupPoints();
      setPickupPoints((latestPickups as any[]).map(normalizePickupPoint));
      await queryClient.invalidateQueries({ queryKey: ['pickup-points'] });
      await queryClient.invalidateQueries({ queryKey: ['route-pickup-points'] });
      resetPickupForm();
    } catch (error) {
      toast({
        title: "Unable to save pickup point",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    }
  };

  const handlePickupDelete = async (pickupId: string) => {
    try {
      await apiService.deletePickupPoint(pickupId);
      setPickupPoints(prev => prev.filter(p => p.id !== pickupId));
      await queryClient.invalidateQueries({ queryKey: ['pickup-points'] });
      await queryClient.invalidateQueries({ queryKey: ['route-pickup-points'] });
      toast({ title: "Pickup Point Deleted", description: "Pickup point has been removed." });
    } catch (error) {
      toast({
        title: "Unable to delete pickup point",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    }
  };

  const resetPickupForm = () => {
    setPickupForm({ name: '', zoneId: '', wardId: '', routeId: '', coordinates: '', pickupTimes: '', pickupRadiusM: '' });
    setEditingPickup(null);
    setPickupFormErrors({});
    setValidationOpen(false);
    setValidationSummary([]);
    setIsPickupDialogOpen(false);
  };

  const formatBatchEditText = (points: PickupPoint[]) =>
    points
      .slice()
      .sort((a, b) => (a.sequenceNo || 0) - (b.sequenceNo || 0))
      .map((point) => {
        const pickupTime = point.pickupTimes || point.expectedPickupTime || '';
        return `${point.name || ''} | ${point.latitude},${point.longitude} | ${pickupTime}`;
      })
      .join('\n');

  const parseBatchEditText = (text: string, points: PickupPoint[]) => {
    const lines = text
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean);

    if (lines.length !== points.length) {
      throw new Error(`Please keep exactly ${points.length} line${points.length === 1 ? '' : 's'} for this route.`);
    }

    return lines.map((line, index) => {
      const [rawName = '', rawCoords = '', rawPickupTime = ''] = line.split('|').map((part) => part.trim());
      const [latRaw, lngRaw] = rawCoords.split(',').map((part) => part.trim());
      const lat = Number(latRaw);
      const lng = Number(lngRaw);
      if (!rawName) {
        throw new Error(`Line ${index + 1}: pickup name is required.`);
      }
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
        throw new Error(`Line ${index + 1}: please enter valid coordinates as lat,lng.`);
      }
      return {
        sourcePoint: points[index],
        pickup_name: rawName,
        lat,
        lng,
        expected_pickup_time: rawPickupTime,
      };
    });
  };

  const filteredRoutes = routes.filter(r => r.name.toLowerCase().includes(searchQuery.toLowerCase()) || r.code.toLowerCase().includes(searchQuery.toLowerCase()));
  const filteredPickups = pickupPoints.filter(p => {
    const query = searchQuery.toLowerCase();
    return (
      p.name.toLowerCase().includes(query) ||
      getRouteName(p.routeId).toLowerCase().includes(query) ||
      getWardName(p.wardId).toLowerCase().includes(query) ||
      getZoneName(p.zoneId || '').toLowerCase().includes(query)
    );
  });

  const parseGeofencePolygonPath = (geofence: any): Array<{ lat: number; lng: number }> => {
    let polygonValue = geofence?.polygon;
    if (typeof polygonValue === 'string') {
      try {
        polygonValue = JSON.parse(polygonValue);
      } catch {
        polygonValue = null;
      }
    }
    const ring = polygonValue?.coordinates?.[0];
    if (!Array.isArray(ring)) return [];
    return ring
      .map((point: any) => ({ lat: Number(point?.[1]), lng: Number(point?.[0]) }))
      .filter((point: any) => Number.isFinite(point.lat) && Number.isFinite(point.lng));
  };

  const openRouteMap = async (route: Route, points: PickupPoint[] = []) => {
    setMapRoute(route);
    setMapPickupPoints([...points].sort((a, b) => (a.sequenceNo || 0) - (b.sequenceNo || 0)));
    setMapWardGeofencePath([]);
    setIsRouteMapOpen(true);

    if (route.wardId) {
      try {
        const geofences = await apiService.getGeofences({
          geofence_for: 'ward',
          ward_id: route.wardId,
          page: 1,
          page_size: 20,
        });
        const wardGeofence = geofences.find((geofence: any) => String(geofence.ward_id || geofence.wardId || '') === route.wardId) || geofences[0];
        setMapWardGeofencePath(parseGeofencePolygonPath(wardGeofence));
      } catch (error) {
        console.warn('Ward geofence unavailable for route map.', error);
      }
    }
  };

  const openPickupMap = (pickup: PickupPoint) => {
    const route = routes.find((item) => item.id === pickup.routeId);
    if (!route) {
      toast({ title: "Route not found", description: "Unable to load route polyline for this pickup point.", variant: "destructive" });
      return;
    }
    void openRouteMap(route, pickupPoints.filter((point) => point.routeId === pickup.routeId));
  };

  const fitRouteMapBounds = (map: any, route: Route, points: PickupPoint[], wardPath: Array<{ lat: number; lng: number }>) => {
    if (!window.google?.maps || !map) return;
    const bounds = new window.google.maps.LatLngBounds();
    wardPath.forEach((point) => bounds.extend({ lat: point.lat, lng: point.lng }));
    route.points.forEach((point: any) => bounds.extend({ lat: point.lat, lng: point.lng }));
    points.forEach((point) => bounds.extend({ lat: point.latitude, lng: point.longitude }));
    map.fitBounds(bounds);
  };

  const adjustRouteMapZoom = (delta: number) => {
    if (!routeMapInstance) return;
    const currentZoom = Number(routeMapInstance.getZoom?.() ?? 14);
    routeMapInstance.setZoom(Math.max(3, Math.min(22, currentZoom + delta)));
  };

  const pickupGroups = routes
    .map((route) => {
      const points = filteredPickups
        .filter((point) => point.routeId === route.id)
        .sort((a, b) => (a.sequenceNo || 0) - (b.sequenceNo || 0));
      return { route, points };
    })
    .filter(({ route, points }) => {
      const query = searchQuery.toLowerCase();
      const routeMatch = (
        route.name.toLowerCase().includes(query) ||
        getZoneName(route.zoneId).toLowerCase().includes(query) ||
        getWardName(route.wardId).toLowerCase().includes(query)
      );
      return points.length > 0 || (query && routeMatch);
    });

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">

      <div className="flex items-center justify-between gap-4 mb-2">
        <PageHeader
          category="Master Data"
          title="Routes & Pickup Points"
          description="Manage collection routes and pickup locations across zones"
          icon={RouteIcon}
        />
        <Button
          variant="outline"
          className="flex items-center gap-2"
          onClick={() => setIsPickupDialogOpen(true)}
          title="Edit Pickup Points"
        >
          <Edit className="h-4 w-4" /> Edit Pickup Points
        </Button>
      </div>

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
          <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-warning">Mapped Routes</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold text-warning">{new Set(pickupPoints.map(p => p.routeId).filter(Boolean)).size}</div></CardContent>
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
                    <div className="space-y-2"><Label>Route Name <RequiredMark /></Label><Input className={validationErrorClass(routeFormErrors, 'name')} value={routeForm.name} onChange={(e) => setRouteField('name', e.target.value)} /><FieldError errors={routeFormErrors} field="name" /></div>
                    <div className="space-y-2"><Label>Route Code</Label><Input value={routeForm.code} onChange={(e) => setRouteField('code', e.target.value)} /></div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Type</Label>
                      <Select value={routeForm.type} onValueChange={(v) => setRouteField('type', v as 'primary' | 'secondary')}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent><SelectItem value="primary">Primary</SelectItem><SelectItem value="secondary">Secondary</SelectItem></SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Zone <RequiredMark /></Label>
                      <Select value={routeForm.zoneId} onValueChange={(v) => { setRouteField('zoneId', v); setRouteField('wardId', ''); }}>
                        <SelectTrigger className={validationErrorClass(routeFormErrors, 'zoneId')}><SelectValue placeholder="Select zone" /></SelectTrigger>
                        <SelectContent>{zones.map(z => <SelectItem key={z.id} value={z.id}>{z.name}</SelectItem>)}</SelectContent>
                      </Select>
                      <FieldError errors={routeFormErrors} field="zoneId" />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Ward <RequiredMark /></Label>
                      <Select value={routeForm.wardId} onValueChange={(v) => setRouteField('wardId', v)}>
                        <SelectTrigger className={validationErrorClass(routeFormErrors, 'wardId')}><SelectValue placeholder="Select ward" /></SelectTrigger>
                        <SelectContent>{wards.filter(w => !routeForm.zoneId || w.zoneId === routeForm.zoneId).map(w => <SelectItem key={w.id} value={w.id}>{w.name}</SelectItem>)}</SelectContent>
                      </Select>
                      <FieldError errors={routeFormErrors} field="wardId" />
                    </div>
                    <div className="space-y-2">
                      <Label>Assigned Truck</Label>
                      <Select value={routeForm.assignedTruckId || 'none'} onValueChange={(v) => setRouteField('assignedTruckId', v === 'none' ? '' : v)}>
                        <SelectTrigger><SelectValue placeholder="Select truck" /></SelectTrigger>
                        <SelectContent><SelectItem value="none">Not Assigned</SelectItem>{trucks.filter(t => t.status === 'active').map(t => <SelectItem key={t.id} value={t.id}>{t.registrationNumber}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2"><Label>Pickup Points</Label><Input type="number" value={routeForm.totalPickupPoints} onChange={(e) => setRouteField('totalPickupPoints', Number(e.target.value))} /></div>
                    <div className="space-y-2"><Label>Distance (km)</Label><Input type="number" value={routeForm.estimatedDistance} onChange={(e) => setRouteField('estimatedDistance', Number(e.target.value))} /></div>
                    <div className="space-y-2"><Label>Time (min)</Label><Input type="number" value={routeForm.estimatedTime} onChange={(e) => setRouteField('estimatedTime', Number(e.target.value))} /></div>
                  </div>
                  <div className="space-y-2">
                    <Label>Route Coordinates (lat,lng;lat,lng) <RequiredMark /></Label>
                    <Input
                      className={validationErrorClass(routeFormErrors, 'coordinates')}
                      value={routeForm.coordinates || ''}
                      onChange={(e) => setRouteField('coordinates', e.target.value)}
                      placeholder="18.6559,73.7714;18.6564,73.7715;18.6571,73.7716"
                    />
                    <FieldError errors={routeFormErrors} field="coordinates" />
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
                          <Button
                            variant="ghost"
                            size="icon"
                            title="View on map"
                            onClick={() => void openRouteMap(route, pickupPoints.filter((point) => point.routeId === route.id))}
                          >
                            <Globe className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => {
                              const coordinates = (Array.isArray(route.points) ? route.points : [])
                                .map((p: any) => `${p.lat},${p.lng}`)
                                .join(';');
                              setEditingRoute(route);
                              setRouteFormErrors({});
                              setValidationOpen(false);
                              setValidationSummary([]);
                              setRouteForm({ ...route, coordinates });
                              setIsRouteDialogOpen(true);
                            }}
                          ><Edit className="h-4 w-4" /></Button>
                          <Button variant="ghost" size="icon" className="text-destructive" onClick={() => handleRouteDelete(route.id)}><Trash2 className="h-4 w-4" /></Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
          <Dialog open={isRouteMapOpen} onOpenChange={(open) => { setIsRouteMapOpen(open); if (!open) setIsMapMaximized(false); }}>
            <DialogContent className={isMapMaximized ? "max-w-[96vw] w-[96vw]" : "max-w-4xl"}>
              <DialogHeader className="pr-12">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <DialogTitle>Route Map View</DialogTitle>
                    <DialogDescription>
                      {mapRoute
                        ? `${mapRoute.name} • ${getZoneName(mapRoute.zoneId)} / ${getWardName(mapRoute.wardId)} • ${mapPickupPoints.length} pickup points`
                        : 'Selected route path'}
                    </DialogDescription>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    title={isMapMaximized ? "Restore map" : "Maximize map"}
                    onClick={() => setIsMapMaximized((value) => !value)}
                  >
                    {isMapMaximized ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                  </Button>
                </div>
              </DialogHeader>
              <div className={`${isMapMaximized ? 'h-[78vh]' : 'h-[480px]'} relative w-full rounded-md overflow-hidden border border-border/60`}>
                <div className="absolute right-3 top-3 z-10 flex flex-col overflow-hidden rounded-md border border-border/70 bg-background/95 shadow-sm">
                  <Button variant="ghost" size="icon" title="Zoom in" onClick={() => adjustRouteMapZoom(0.5)} className="h-9 w-9 rounded-none">+</Button>
                  <div className="h-px bg-border/70" />
                  <Button variant="ghost" size="icon" title="Zoom out" onClick={() => adjustRouteMapZoom(-0.5)} className="h-9 w-9 rounded-none">-</Button>
                </div>
                {mapRoute && Array.isArray(mapRoute.points) && mapRoute.points.length > 1 ? (
                  <GoogleMap
                    key={`${mapRoute.id}-${mapWardGeofencePath.length}-${mapPickupPoints.length}`}
                    mapContainerStyle={{ width: '100%', height: '100%' }}
                    center={mapRoute.points[0] as any}
                    zoom={14}
                    onLoad={(map) => {
                      setRouteMapInstance(map);
                      fitRouteMapBounds(map, mapRoute, mapPickupPoints, mapWardGeofencePath);
                    }}
                    onUnmount={() => setRouteMapInstance(null)}
                    options={{
                      streetViewControl: false,
                      mapTypeControl: false,
                      fullscreenControl: false,
                      zoomControl: false,
                      isFractionalZoomEnabled: true,
                    }}
                  >
                    {mapWardGeofencePath.length > 2 ? (
                      <Polygon
                        path={mapWardGeofencePath as any}
                        options={{
                          fillColor: '#c084fc',
                          fillOpacity: 0.18,
                          strokeColor: '#7e22ce',
                          strokeOpacity: 0.7,
                          strokeWeight: 2,
                        }}
                      />
                    ) : null}
                    <Polyline
                      path={mapRoute.points as any}
                      options={{
                        strokeColor: '#2563eb',
                        strokeOpacity: 0.9,
                        strokeWeight: 3,
                        icons: window.google?.maps
                          ? [
                              {
                                icon: {
                                  path: window.google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
                                  scale: 2,
                                  strokeColor: '#1d4ed8',
                                  strokeOpacity: 0.85,
                                },
                                offset: '0%',
                                repeat: '95px',
                              },
                            ]
                          : undefined,
                      }}
                    />
                    {mapRoute.points.length > 0 ? (
                      <Marker
                        position={mapRoute.points[0] as any}
                        icon={{
                          url: 'http://maps.google.com/mapfiles/ms/icons/green-dot.png',
                          scaledSize: { width: 44, height: 44 } as any,
                          labelOrigin: { x: 22, y: 14 } as any,
                        }}
                        label={{ text: 'S', color: '#166534', fontWeight: '700' }}
                        title="Start"
                      />
                    ) : null}
                    {mapRoute.points.length > 1 ? (
                      <Marker
                        position={mapRoute.points[mapRoute.points.length - 1] as any}
                        icon={{
                          url: 'http://maps.google.com/mapfiles/ms/icons/red-dot.png',
                          scaledSize: { width: 44, height: 44 } as any,
                          labelOrigin: { x: 22, y: 14 } as any,
                        }}
                        label={{ text: 'E', color: '#991b1b', fontWeight: '700' }}
                        title="End"
                      />
                    ) : null}
                    {mapPickupPoints.map((point) => (
                      <Marker
                        key={point.id}
                        position={{ lat: point.latitude, lng: point.longitude } as any}
                        label={{ text: String(point.sequenceNo || ''), color: '#111827', fontWeight: '700' }}
                        title={`${point.name} (${point.latitude}, ${point.longitude})`}
                      />
                    ))}
                  </GoogleMap>
                ) : (
                  <div className="h-full w-full flex items-center justify-center text-sm text-muted-foreground">
                    No valid polyline coordinates found for this route.
                  </div>
                )}
              </div>
            </DialogContent>
          </Dialog>
        </TabsContent>

        <TabsContent value="pickups" className="space-y-4">
          <div className="flex justify-end">
            <Dialog open={isPickupDialogOpen} onOpenChange={(open) => {
              if (!open) {
                resetPickupForm();
                setBatchEditPoints(null);
                setBatchEditText('');
              }
              setIsPickupDialogOpen(open);
            }}>
              <DialogTrigger asChild><Button><Plus className="h-4 w-4 mr-2" /> Add Pickup Point</Button></DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>{batchEditPoints ? 'Edit All Pickup Points' : (editingPickup ? 'Edit Pickup Point' : 'Add New Pickup Point')}</DialogTitle>
                  <DialogDescription>
                    {batchEditPoints ? 'Edit all pickup points in one text box. One line per pickup point.' : 'Map pickup coordinates to a zone, ward and route'}
                  </DialogDescription>
                </DialogHeader>
                {batchEditPoints ? (
                  <div className="grid gap-6 max-h-[60vh] overflow-y-auto">
                    <div className="space-y-2">
                      <Label>Pickup points in one text box</Label>
                      <Textarea
                        value={batchEditText}
                        onChange={(e) => setBatchEditText(e.target.value)}
                        className="min-h-[280px] font-mono text-sm"
                        placeholder={`Pickup Name | lat,lng | expected pickup time\nEON IT Park | 18.5500,73.9380 | 06:00\nWorld Trade Center | 18.5520,73.9400 | 06:30`}
                      />
                      <p className="text-xs text-muted-foreground">
                        One pickup point per line. Format: <span className="font-medium">Name | lat,lng | expected pickup time(optional)</span>
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="grid gap-4 py-4 max-h-[60vh] overflow-y-auto">
                    <div className="space-y-2"><Label>Pickup Name</Label><Input value={pickupForm.name || ''} onChange={(e) => setPickupField('name', e.target.value)} placeholder="R1 Pickup Points" /></div>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="space-y-2">
                        <Label>Zone <RequiredMark /></Label>
                        <Select value={pickupForm.zoneId || ''} onValueChange={(v) => { setPickupField('zoneId', v); setPickupField('wardId', ''); setPickupField('routeId', ''); }}>
                          <SelectTrigger className={validationErrorClass(pickupFormErrors, 'zoneId')}><SelectValue placeholder="Select zone" /></SelectTrigger>
                          <SelectContent>{zones.map(z => <SelectItem key={z.id} value={z.id}>{z.name}</SelectItem>)}</SelectContent>
                        </Select>
                        <FieldError errors={pickupFormErrors} field="zoneId" />
                      </div>
                      <div className="space-y-2">
                        <Label>Ward <RequiredMark /></Label>
                        <Select value={pickupForm.wardId || ''} onValueChange={(v) => { setPickupField('wardId', v); setPickupField('routeId', ''); }}>
                          <SelectTrigger className={validationErrorClass(pickupFormErrors, 'wardId')}><SelectValue placeholder="Select ward" /></SelectTrigger>
                          <SelectContent>{wards.filter(w => !pickupForm.zoneId || w.zoneId === pickupForm.zoneId).map(w => <SelectItem key={w.id} value={w.id}>{w.name}</SelectItem>)}</SelectContent>
                        </Select>
                        <FieldError errors={pickupFormErrors} field="wardId" />
                      </div>
                      <div className="space-y-2">
                        <Label>Route <RequiredMark /></Label>
                        <Select value={pickupForm.routeId || ''} onValueChange={(v) => setPickupField('routeId', v)}>
                          <SelectTrigger className={validationErrorClass(pickupFormErrors, 'routeId')}><SelectValue placeholder="Select route" /></SelectTrigger>
                          <SelectContent>
                            {routes
                              .filter(r => (!pickupForm.zoneId || r.zoneId === pickupForm.zoneId) && (!pickupForm.wardId || r.wardId === pickupForm.wardId))
                              .map(r => <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>)}
                          </SelectContent>
                        </Select>
                        <FieldError errors={pickupFormErrors} field="routeId" />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label>{editingPickup ? 'Pickup Coordinate (lat,lng)' : 'Pickup Coordinates (lat,lng;lat,lng)'} {!editingPickup && <RequiredMark />}</Label>
                      <Input
                        className={validationErrorClass(pickupFormErrors, 'coordinates')}
                        value={pickupForm.coordinates || ''}
                        onChange={(e) => setPickupField('coordinates', e.target.value)}
                        placeholder="18.65590324664102,73.77146106998136;18.65645416108611,73.77153575645825"
                      />
                      <FieldError errors={pickupFormErrors} field="coordinates" />
                    </div>
                    <div className="space-y-2">
                      <Label>Pickup Times (comma separated)</Label>
                      <Input
                        value={pickupForm.pickupTimes || ''}
                        onChange={(e) => setPickupField('pickupTimes', e.target.value)}
                        placeholder="06:00,07:00,08:00"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Pickup Radius (meters)</Label>
                      <Input
                        type="number"
                        min={0}
                        step="1"
                        value={pickupForm.pickupRadiusM ?? ''}
                        onChange={(e) => setPickupField('pickupRadiusM', e.target.value)}
                        placeholder="30"
                      />
                    </div>
                  </div>
                )}
                <DialogFooter>
                  <Button variant="outline" onClick={() => { resetPickupForm(); setBatchEditPoints(null); setBatchEditText(''); setIsPickupDialogOpen(false); }}>Cancel</Button>
                  {batchEditPoints ? (
                    <Button onClick={async () => {
                      try {
                        const updates = parseBatchEditText(batchEditText, batchEditPoints);
                        for (let index = 0; index < updates.length; index += 1) {
                          const update = updates[index];
                          await apiService.updatePickupPoint(update.sourcePoint.id, {
                            pickup_name: update.pickup_name,
                            sequence_no: index + 1,
                            lat: update.lat,
                            lng: update.lng,
                            expected_pickup_time: update.expected_pickup_time,
                            expectedPickupTime: update.expected_pickup_time,
                            zone_id: update.sourcePoint.zoneId,
                            ward_id: update.sourcePoint.wardId,
                            route_id: update.sourcePoint.routeId,
                          });
                        }
                        const latestPickups = await apiService.getPickupPoints();
                        setPickupPoints((latestPickups as any[]).map(normalizePickupPoint));
                        await queryClient.invalidateQueries({ queryKey: ['pickup-points'] });
                        await queryClient.invalidateQueries({ queryKey: ['route-pickup-points'] });
                        setBatchEditPoints(null);
                        setBatchEditText('');
                        setIsPickupDialogOpen(false);
                        toast({ title: 'Pickup Points Updated', description: 'All pickup points have been updated.' });
                      } catch (error) {
                        toast({
                          title: 'Unable to update pickup points',
                          description: error instanceof Error ? error.message : 'Please try again.',
                          variant: 'destructive',
                        });
                      }
                    }}>Save All</Button>
                  ) : (
                    <Button onClick={handlePickupSubmit}>{editingPickup ? 'Update' : 'Add'} Pickup Point</Button>
                  )}
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-0">
              <Accordion type="multiple" className="divide-y divide-border/60">
                {pickupGroups.map(({ route, points }) => (
                  <AccordionItem key={route.id} value={route.id} className="border-b-0">
                    <div className="grid grid-cols-[1fr_auto_auto] items-center gap-3 px-4 py-3">
                      <AccordionTrigger className="py-0 hover:no-underline">
                        <div className="grid w-full grid-cols-1 gap-3 text-left md:grid-cols-[1.4fr_1fr_0.6fr] md:items-center">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-success/10 flex items-center justify-center"><MapPin className="h-5 w-5 text-success" /></div>
                            <div>
                              <div className="font-medium">{route.name}</div>
                              <div className="text-sm text-muted-foreground">{route.code}</div>
                            </div>
                          </div>
                          <div>
                            <div className="text-sm">{getZoneName(route.zoneId)}</div>
                            <div className="text-xs text-muted-foreground">{getWardName(route.wardId)}</div>
                          </div>
                          <Badge variant="outline" className="w-fit">{points.length} points</Badge>
                        </div>
                      </AccordionTrigger>
                      <Button
                        variant="ghost"
                        size="icon"
                        title="Edit pickup points for this route"
                        onClick={() => {
                          const sortedPoints = points.slice().sort((a, b) => (a.sequenceNo || 0) - (b.sequenceNo || 0));
                          setBatchEditPoints(sortedPoints.map(p => ({ ...p })));
                          setBatchEditText(formatBatchEditText(sortedPoints));
                          setIsPickupDialogOpen(true);
                        }}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        title="View route and pickup points on map"
                        onClick={() => void openRouteMap(route, points)}
                      >
                        <Globe className="h-4 w-4" />
                      </Button>
                    </div>
                    <AccordionContent className="px-4 pb-4">
                      <div className="rounded-md border border-border/60 overflow-hidden">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead className="w-28">Sequence</TableHead>
                              <TableHead>Pickup Point</TableHead>
                              <TableHead>Coordinates</TableHead>
                              <TableHead>Pickup Times</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {points.map((pickup) => (
                              <TableRow key={pickup.id}>
                                <TableCell><Badge variant="secondary">{pickup.sequenceNo || '-'}</Badge></TableCell>
                                <TableCell>{pickup.name}</TableCell>
                                <TableCell>{pickup.latitude.toFixed(6)}, {pickup.longitude.toFixed(6)}</TableCell>
                                <TableCell>{pickup.pickupTimes || pickup.expectedPickupTime || ''}</TableCell>
                                <TableCell>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    title="Edit this pickup point"
                                    onClick={() => {
                                      setEditingPickup(pickup);
                                      setPickupFormErrors({});
                                      setValidationOpen(false);
                                      setValidationSummary([]);
                                      setPickupForm({
                                        name: pickup.name,
                                        zoneId: pickup.zoneId,
                                        wardId: pickup.wardId,
                                        routeId: pickup.routeId,
                                        coordinates: `${pickup.latitude},${pickup.longitude}`,
                                        pickupTimes: pickup.pickupTimes || pickup.expectedPickupTime || '',
                                        pickupRadiusM: pickup.geofenceRadius ?? '',
                                      });
                                      setIsPickupDialogOpen(true);
                                    }}
                                  >
                                    <Edit className="h-4 w-4" />
                                  </Button>
                                </TableCell>
                              </TableRow>
                            ))}
                            {points.length === 0 ? (
                              <TableRow>
                                <TableCell colSpan={3} className="text-center text-muted-foreground">No pickup points found for this route.</TableCell>
                              </TableRow>
                            ) : null}
                          </TableBody>
                        </Table>
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
              {pickupGroups.length === 0 ? (
                <div className="px-4 py-10 text-center text-sm text-muted-foreground">
                  No pickup point groups found.
                </div>
              ) : null}
            </CardContent>
          </Card>
          <Dialog open={isRouteMapOpen} onOpenChange={(open) => { setIsRouteMapOpen(open); if (!open) setIsMapMaximized(false); }}>
            <DialogContent className={isMapMaximized ? "max-w-[96vw] w-[96vw]" : "max-w-4xl"}>
              <DialogHeader className="pr-12">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <DialogTitle>Route Map View</DialogTitle>
                    <DialogDescription>
                      {mapRoute
                        ? `${mapRoute.name} - ${getZoneName(mapRoute.zoneId)} / ${getWardName(mapRoute.wardId)} - ${mapPickupPoints.length} pickup points`
                        : 'Selected route path'}
                    </DialogDescription>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    title={isMapMaximized ? "Restore map" : "Maximize map"}
                    onClick={() => setIsMapMaximized((value) => !value)}
                  >
                    {isMapMaximized ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                  </Button>
                </div>
              </DialogHeader>
              <div className={`${isMapMaximized ? 'h-[78vh]' : 'h-[480px]'} relative w-full rounded-md overflow-hidden border border-border/60`}>
                <div className="absolute right-3 top-3 z-10 flex flex-col overflow-hidden rounded-md border border-border/70 bg-background/95 shadow-sm">
                  <Button variant="ghost" size="icon" title="Zoom in" onClick={() => adjustRouteMapZoom(0.5)} className="h-9 w-9 rounded-none">+</Button>
                  <div className="h-px bg-border/70" />
                  <Button variant="ghost" size="icon" title="Zoom out" onClick={() => adjustRouteMapZoom(-0.5)} className="h-9 w-9 rounded-none">-</Button>
                </div>
                {mapRoute && Array.isArray(mapRoute.points) && mapRoute.points.length > 1 ? (
                  <GoogleMap
                    key={`pickup-${mapRoute.id}-${mapWardGeofencePath.length}-${mapPickupPoints.length}`}
                    mapContainerStyle={{ width: '100%', height: '100%' }}
                    center={mapRoute.points[0] as any}
                    zoom={14}
                    onLoad={(map) => {
                      setRouteMapInstance(map);
                      fitRouteMapBounds(map, mapRoute, mapPickupPoints, mapWardGeofencePath);
                    }}
                    onUnmount={() => setRouteMapInstance(null)}
                    options={{
                      streetViewControl: false,
                      mapTypeControl: false,
                      fullscreenControl: false,
                      zoomControl: false,
                      isFractionalZoomEnabled: true,
                    }}
                  >
                    {mapWardGeofencePath.length > 2 ? (
                      <Polygon
                        path={mapWardGeofencePath as any}
                        options={{
                          fillColor: '#c084fc',
                          fillOpacity: 0.18,
                          strokeColor: '#7e22ce',
                          strokeOpacity: 0.7,
                          strokeWeight: 2,
                        }}
                      />
                    ) : null}
                    <Polyline
                      path={mapRoute.points as any}
                      options={{
                        strokeColor: '#2563eb',
                        strokeOpacity: 0.9,
                        strokeWeight: 3,
                        icons: window.google?.maps
                          ? [
                              {
                                icon: {
                                  path: window.google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
                                  scale: 2,
                                  strokeColor: '#1d4ed8',
                                  strokeOpacity: 0.85,
                                },
                                offset: '0%',
                                repeat: '95px',
                              },
                            ]
                          : undefined,
                      }}
                    />
                    {mapRoute.points.length > 0 ? (
                      <Marker
                        position={mapRoute.points[0] as any}
                        icon={{
                          url: 'http://maps.google.com/mapfiles/ms/icons/green-dot.png',
                          scaledSize: { width: 44, height: 44 } as any,
                          labelOrigin: { x: 22, y: 14 } as any,
                        }}
                        label={{ text: 'S', color: '#166534', fontWeight: '700' }}
                        title="Start"
                      />
                    ) : null}
                    {mapRoute.points.length > 1 ? (
                      <Marker
                        position={mapRoute.points[mapRoute.points.length - 1] as any}
                        icon={{
                          url: 'http://maps.google.com/mapfiles/ms/icons/red-dot.png',
                          scaledSize: { width: 44, height: 44 } as any,
                          labelOrigin: { x: 22, y: 14 } as any,
                        }}
                        label={{ text: 'E', color: '#991b1b', fontWeight: '700' }}
                        title="End"
                      />
                    ) : null}
                    {mapPickupPoints.map((point) => (
                      <Marker
                        key={point.id}
                        position={{ lat: point.latitude, lng: point.longitude } as any}
                        label={{ text: String(point.sequenceNo || ''), color: '#111827', fontWeight: '700' }}
                        title={`${point.name} (${point.latitude}, ${point.longitude})`}
                      />
                    ))}
                  </GoogleMap>
                ) : (
                  <div className="h-full w-full flex items-center justify-center text-sm text-muted-foreground">
                    No valid polyline coordinates found for this route.
                  </div>
                )}
              </div>
            </DialogContent>
          </Dialog>
        </TabsContent>
      </Tabs>

      <ValidationAlert open={validationOpen} onOpenChange={setValidationOpen} messages={validationSummary} />
    </div>
  );
}
