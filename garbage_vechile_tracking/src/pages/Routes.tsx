import { useState, useMemo, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { GoogleMap, Marker } from "@react-google-maps/api";
import { PageHeader } from "@/components/PageHeader";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { 
  Route, MapPin, Truck, Clock, ArrowRight, 
  Plus, Edit, Trash2, X, Loader2
} from "lucide-react";
import { RouteData, TruckType } from "@/data/fleetData";
import { toast } from "sonner";
import RouteMapBuilder from "@/components/RouteMapBuilder";
import RouteListView from "@/components/RouteListView";
import { useQuery } from "@tanstack/react-query";
import { useZones, useWards, useRoutes, useRoutePickupPoints } from "@/hooks/useDataQueries";
import { apiService } from "@/services/api";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export default function Routes() {
  // Fetch routes from API
  const { data: routesAPIData = [] } = useRoutes();
  
  const [routesData, setRoutes] = useState<RouteData[]>([]);
  const [selectedRoute, setSelectedRoute] = useState<RouteData | null>(null);
  const [filterType, setFilterType] = useState<"all" | "primary" | "secondary">("all");
  const [filterZoneId, setFilterZoneId] = useState<string>("all");
  const [filterWardId, setFilterWardId] = useState<string>("all");
  const [filterRouteId, setFilterRouteId] = useState<string>("all");
  const [isBuilderOpen, setIsBuilderOpen] = useState(false);
  const [editingRoute, setEditingRoute] = useState<RouteData | null>(null);
  const [newRouteType, setNewRouteType] = useState<TruckType>("primary");
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [routeToDelete, setRouteToDelete] = useState<string | null>(null);
  const [routeIdForPoints, setRouteIdForPoints] = useState<string | null>(null);
  const [singleMapPoint, setSingleMapPoint] = useState<{ title: string; lat: number; lng: number; type: "gts" | "dump" } | null>(null);

  // Fetch pickup points for the route being edited or viewed
  const { data: pickupPointsData = [] } = useRoutePickupPoints(routeIdForPoints);
  const { data: gtsPayload = { items: [] } } = useQuery({
    queryKey: ["gts", "route-management"],
    queryFn: () => apiService.getGts({ active: "true", page_size: "200" }),
  });
  const { data: dumpYards = [] } = useQuery({
    queryKey: ["dump-yards", "route-management"],
    queryFn: () => apiService.getDumpYards({ active: "true" }),
  });
  const gtsLocations = Array.isArray((gtsPayload as any)?.items) ? (gtsPayload as any).items : [];

  const calculateRouteDistanceKm = (points: any[]) => {
    if (points.length < 2) return 0;
    const toRad = (value: number) => (value * Math.PI) / 180;
    return points.slice(1).reduce((sum, point, index) => {
      const previous = points[index];
      const p1 = previous.position;
      const p2 = point.position;
      if (!p1 || !p2) return sum;
      const radiusKm = 6371;
      const dLat = toRad(p2.lat - p1.lat);
      const dLng = toRad(p2.lng - p1.lng);
      const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(p1.lat)) * Math.cos(toRad(p2.lat)) * Math.sin(dLng / 2) ** 2;
      return sum + radiusKm * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    }, 0);
  };

  const toMinutes = (time?: string) => {
    if (!time) return null;
    const [hours, minutes] = time.slice(0, 5).split(":").map(Number);
    return Number.isFinite(hours) && Number.isFinite(minutes) ? hours * 60 + minutes : null;
  };

  const enrichRouteWithPoints = (route: RouteData, rawPoints: any[]) => {
    const points = rawPoints.map((pp: any, index: number) => {
      const isGts = Boolean(pp.is_gts ?? pp.isGts ?? pp.is_GTS);
      return {
        id: pp.id,
        position: { lat: Number(pp.latitude ?? pp.lat), lng: Number(pp.longitude ?? pp.lng) },
        name: pp.name || pp.pickup_name || `Pickup ${pp.sequence_no ?? index + 1}`,
        type: (isGts ? "gtp" : pp.type || "pickup") as "pickup" | "gtp" | "dumping",
        isGts,
        order: Number(pp.sequence_no ?? pp.sequenceNo ?? index + 1),
        scheduledTime: pp.expected_pickup_time || pp.expectedPickupTime,
      };
    }).sort((a, b) => a.order - b.order);

    const distanceKm = calculateRouteDistanceKm(points);
    const scheduled = points.map((point) => toMinutes(point.scheduledTime)).filter((value): value is number => value !== null);
    const estimatedTime = scheduled.length >= 2
      ? Math.max(...scheduled) - Math.min(...scheduled)
      : Math.round((distanceKm / 14) * 60 + points.length * 5);

    return {
      ...route,
      points,
      totalPickupPoints: points.length || route.totalPickupPoints || 0,
      estimatedDistance: Number(distanceKm.toFixed(2)),
      distance: `${distanceKm.toFixed(1)} km`,
      estimatedTime,
    };
  };

  // Sync API routes to state
  useEffect(() => {
    const normalizedRoutes = (routesAPIData as any[]).map((route) => ({
      ...route,
      zoneId: route.zoneId || route.zone_id,
      wardId: route.wardId || route.ward_id,
      estimatedDistance: route.estimatedDistance ?? route.estimated_distance,
      estimatedTime: route.estimatedTime ?? route.estimated_time,
      totalPickupPoints: route.totalPickupPoints ?? route.total_pickup_points,
      distance: route.distance ?? `${route.estimatedDistance ?? route.estimated_distance ?? 0} km`,
    })) as RouteData[];

    setRoutes(normalizedRoutes);
    if (normalizedRoutes.length > 0) {
      const firstRoute = normalizedRoutes[0];
      setSelectedRoute(firstRoute);
      setRouteIdForPoints(firstRoute.id);
    }
  }, [routesAPIData]);

  // Transform pickup points into RoutePoint format and enrich selected route
  const enrichedSelectedRoute = useMemo(() => {
    if (!selectedRoute) return null;
    if (!pickupPointsData || pickupPointsData.length === 0) return selectedRoute;

    return enrichRouteWithPoints(selectedRoute, pickupPointsData);
  }, [selectedRoute, pickupPointsData]);

  // Transform pickup points for editing route
  const enrichedEditingRoute = useMemo(() => {
    if (!editingRoute) return null;
    if (!pickupPointsData || pickupPointsData.length === 0) return editingRoute;

    return enrichRouteWithPoints(editingRoute, pickupPointsData);
  }, [editingRoute, pickupPointsData]);

  // Fetch zones and wards from API
  const { data: zonesData = [], isLoading: isLoadingZones } = useZones();
  const { data: wardsData = [], isLoading: isLoadingWards } = useWards();

  // Memoized wards for selected zone
  const wardsForZone = useMemo(() => {
    if (filterZoneId === "all") return wardsData;
    return wardsData.filter((ward: any) => String(ward.zoneId || ward.zone_id) === filterZoneId);
  }, [filterZoneId, wardsData]);

  const routesForWard = useMemo(() => {
    return routesData.filter((route) => {
      if (filterZoneId !== "all" && route.zoneId !== filterZoneId) return false;
      if (filterWardId !== "all" && route.wardId !== filterWardId) return false;
      return true;
    });
  }, [routesData, filterZoneId, filterWardId]);

  useEffect(() => {
    setFilterWardId("all");
    setFilterRouteId("all");
  }, [filterZoneId]);

  useEffect(() => {
    setFilterRouteId("all");
  }, [filterWardId]);

  // Apply all filters to routes
  const filteredRoutes = useMemo(() => {
    return routesData.filter(r => {
      // Type filter
      if (filterType !== "all" && r.type !== filterType) return false;
      if (filterZoneId !== "all" && r.zoneId !== filterZoneId) return false;
      if (filterWardId !== "all" && r.wardId !== filterWardId) return false;
      if (filterRouteId !== "all" && r.id !== filterRouteId) return false;
      return true;
    });
  }, [routesData, filterType, filterZoneId, filterWardId, filterRouteId]);

  const primaryRoutes = routesData.filter(r => r.type === "primary");
  const secondaryRoutes = routesData.filter(r => r.type === "secondary");

  // Handle creating a new route
  const handleCreateRoute = (type: TruckType) => {
    setNewRouteType(type);
    setEditingRoute(null);
    setRouteIdForPoints(null);
    setIsBuilderOpen(true);
  };

  // Handle editing a route
  const handleEditRoute = (route: RouteData) => {
    setNewRouteType(route.type);
    setEditingRoute(route);
    setRouteIdForPoints(route.id);
    setIsBuilderOpen(true);
  };

  // Handle selecting a route
  const handleSelectRoute = (route: RouteData) => {
    setSelectedRoute(route);
    setRouteIdForPoints(route.id);
  };

  // Handle saving route from builder
  const handleSaveRoute = (route: RouteData) => {
    if (editingRoute) {
      // Update existing route
      setRoutes(routesData.map(r => r.id === route.id ? route : r));
      toast.success(`Route "${route.name}" updated successfully`);
    } else {
      // Add new route
      setRoutes([...routesData, route]);
      toast.success(`Route "${route.name}" created successfully`);
    }
    setIsBuilderOpen(false);
    setEditingRoute(null);
    setRouteIdForPoints(null);
    setSelectedRoute(route);
  };

  // Handle delete confirmation
  const handleDeleteRoute = (routeId: string) => {
    setRouteToDelete(routeId);
    setDeleteConfirmOpen(true);
  };

  // Confirm delete
  const confirmDelete = () => {
    if (routeToDelete) {
      const routeName = routesData.find(r => r.id === routeToDelete)?.name;
      setRoutes(routesData.filter(r => r.id !== routeToDelete));
      if (selectedRoute?.id === routeToDelete) {
        setSelectedRoute(null);
      }
      toast.success(`Route "${routeName}" deleted`);
    }
    setDeleteConfirmOpen(false);
    setRouteToDelete(null);
  };

  // Cancel builder
  const handleCancelBuilder = () => {
    setIsBuilderOpen(false);
    setEditingRoute(null);
    setRouteIdForPoints(selectedRoute?.id || null);
  };

  const openSinglePointMap = (title: string, latValue: any, lngValue: any, type: "gts" | "dump") => {
    const lat = Number(latValue);
    const lng = Number(lngValue);
    if (!Number.isFinite(lat) || !Number.isFinite(lng) || (lat === 0 && lng === 0)) {
      toast.error("Valid coordinates are not available for this location");
      return;
    }
    setSingleMapPoint({ title, lat, lng, type });
  };

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <PageHeader
        category="Operations"
        title="Route Management"
        description={
          isBuilderOpen 
            ? `${editingRoute ? "Edit" : "Create"} ${newRouteType} collection route`
            : "Create and manage collection routes for primary and secondary trucks"
        }
        icon={Route}
        actions={
          !isBuilderOpen ? (
            <>
              <Button variant="outline" className="gap-2" onClick={() => handleCreateRoute("primary")}>
                <Plus className="h-4 w-4" />
                Primary Route
              </Button>
              <Button className="gap-2" onClick={() => handleCreateRoute("secondary")}>
                <Plus className="h-4 w-4" />
                Secondary Route
              </Button>
            </>
          ) : undefined
        }
      />

      {isBuilderOpen ? (
        // Route Builder View
        <RouteMapBuilder
          route={enrichedEditingRoute}
          routeType={newRouteType}
          onSave={handleSaveRoute}
          onCancel={handleCancelBuilder}
        />
      ) : (
        <>
          {/* Route Type Explanation */}
          <div className="grid md:grid-cols-2 gap-4">
            <Card className="p-4 border-l-4 border-l-primary">
              <CardContent className="p-0">
                <div className="flex items-start gap-3">
                  <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
                    <Truck className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-primary">Primary Routes ({primaryRoutes.length})</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      Primary trucks collect garbage from pickup points and end at GTS locations (Garbage Transport Stations).
                    </p>
                    <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                      <MapPin className="h-3 w-3" /> Pickup Points <ArrowRight className="h-3 w-3" /> GTS
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="p-4 border-l-4 border-l-secondary">
              <CardContent className="p-0">
                <div className="flex items-start gap-3">
                  <div className="h-12 w-12 rounded-xl bg-secondary/10 flex items-center justify-center">
                    <Truck className="h-5 w-5 text-secondary" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-secondary">Secondary Routes ({secondaryRoutes.length})</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      Secondary trucks pick garbage from GTS locations and transport to final dump yards.
                    </p>
                    <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                      <MapPin className="h-3 w-3" /> GTS <ArrowRight className="h-3 w-3" /> Dump Yard
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <Tabs defaultValue="routes" className="space-y-4">
            <TabsList>
              <TabsTrigger value="routes">All Routes ({filteredRoutes.length})</TabsTrigger>
              <TabsTrigger value="gtp">GTS Locations ({gtsLocations.length})</TabsTrigger>
              <TabsTrigger value="dumping">Dumping Yards ({dumpYards.length})</TabsTrigger>
            </TabsList>

            <TabsContent value="routes">
              <div className="space-y-4">
                {/* Filters Panel */}
                <Card className="p-4">
                  <CardContent className="p-0">
                    <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-end">
                      {/* Route Type Filter */}
                      <div>
                        <label className="text-sm font-medium mb-2 block">Route Type</label>
                        <Select value={filterType} onValueChange={(value: any) => setFilterType(value)}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="all">All Routes</SelectItem>
                            <SelectItem value="primary">Primary Routes</SelectItem>
                            <SelectItem value="secondary">Secondary Routes</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      {/* Zone Filter */}
                      <div>
                        <label className="text-sm font-medium mb-2 block">Zone</label>
                        <Select value={filterZoneId} onValueChange={setFilterZoneId} disabled={isLoadingZones}>
                          <SelectTrigger>
                            <SelectValue placeholder={isLoadingZones ? "Loading zones..." : "Select zone"} />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="all">All Zones</SelectItem>
                            {zonesData.map(zone => (
                              <SelectItem key={zone.id} value={zone.id}>
                                {zone.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      {/* Ward Filter */}
                      <div>
                        <label className="text-sm font-medium mb-2 block">Ward</label>
                        <Select 
                          value={filterWardId} 
                          onValueChange={setFilterWardId}
                          disabled={filterZoneId === "all" || isLoadingWards}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder={
                              filterZoneId === "all" 
                                ? "Select zone first" 
                                : isLoadingWards 
                                ? "Loading wards..." 
                                : "Select ward"
                            } />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="all">All Wards</SelectItem>
                            {wardsForZone.map(ward => (
                              <SelectItem key={ward.id} value={ward.id}>
                                {ward.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div>
                        <label className="text-sm font-medium mb-2 block">Route</label>
                        <Select value={filterRouteId} onValueChange={setFilterRouteId}>
                          <SelectTrigger>
                            <SelectValue placeholder="Select route" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="all">All Routes</SelectItem>
                            {routesForWard.map(route => (
                              <SelectItem key={route.id} value={route.id}>
                                {route.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      {/* Clear Filters Button */}
                      {(filterType !== "all" || filterZoneId !== "all" || filterWardId !== "all" || filterRouteId !== "all") && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setFilterType("all");
                            setFilterZoneId("all");
                            setFilterWardId("all");
                            setFilterRouteId("all");
                          }}
                          className="gap-1"
                        >
                          <X className="h-4 w-4" />
                          Clear
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>

                {/* Routes List */}
                <RouteListView
                  routes={filteredRoutes}
                  selectedRoute={enrichedSelectedRoute}
                  filterType={filterType}
                  onFilterChange={setFilterType}
                  onSelectRoute={handleSelectRoute}
                  onEditRoute={handleEditRoute}
                  onDeleteRoute={handleDeleteRoute}
                  onCreateRoute={handleCreateRoute}
                />
              </div>
            </TabsContent>

            <TabsContent value="gtp">
              <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
                {gtsLocations.map((gtp: any) => (
                  <Card key={gtp.id} className="p-4 border-l-4 border-l-sky-500 bg-sky-50/40">
                    <CardContent className="p-0">
                      <div className="flex items-start justify-between mb-3">
                        <button
                          type="button"
                          className="h-12 w-12 rounded-xl bg-sky-500/10 flex items-center justify-center transition hover:bg-sky-500/20"
                          title="Open GTS location on map"
                          onClick={() => openSinglePointMap(gtp.name || "GTS Location", gtp.latitude ?? gtp.lat, gtp.longitude ?? gtp.lng, "gts")}
                        >
                          <MapPin className="h-5 w-5 text-sky-600" />
                        </button>
                        <Badge className="bg-sky-100 text-sky-700 border-sky-200">GTS</Badge>
                      </div>
                      <h3 className="font-semibold mb-1">{gtp.name}</h3>
                      <p className="text-sm text-muted-foreground mb-3">{gtp.address || "Garbage Transport Station"}</p>
                      <p className="text-xs text-muted-foreground mt-2">
                        {Number(gtp.latitude ?? gtp.lat ?? 0).toFixed(4)}, {Number(gtp.longitude ?? gtp.lng ?? 0).toFixed(4)}
                      </p>
                    </CardContent>
                  </Card>
                ))}
                {gtsLocations.length === 0 && <Card className="p-6 text-muted-foreground">No GTS locations found.</Card>}
              </div>
            </TabsContent>

            <TabsContent value="dumping">
              <div className="grid md:grid-cols-2 gap-4">
                {(dumpYards as any[]).map((site) => (
                  <Card key={site.id} className="p-4 border-l-4 border-l-destructive">
                    <CardContent className="p-0">
                      <div className="flex items-start gap-4">
                        <button
                          type="button"
                          className="h-12 w-12 rounded-xl bg-destructive/10 flex items-center justify-center transition hover:bg-destructive/20"
                          title="Open dump yard on map"
                          onClick={() => openSinglePointMap(site.name || site.dump_yard_name || "Dump Yard", site.latitude ?? site.lat, site.longitude ?? site.lng, "dump")}
                        >
                          <MapPin className="h-6 w-6 text-destructive" />
                        </button>
                        <div className="flex-1">
                          <h3 className="font-semibold text-lg mb-1">{site.name || site.dump_yard_name}</h3>
                          <p className="text-muted-foreground mb-2">{site.address || "Dump Yard"}</p>
                          <div className="flex items-center gap-4 text-sm">
                            <span className="flex items-center gap-1">
                              <Truck className="h-4 w-4" /> Capacity: {site.capacity ? `${site.capacity} tons` : "Not set"}
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground mt-2">
                            Coordinates: {Number(site.latitude ?? site.lat ?? 0).toFixed(4)}, {Number(site.longitude ?? site.lng ?? 0).toFixed(4)}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
                {(dumpYards as any[]).length === 0 && <Card className="p-6 text-muted-foreground">No dump yards found.</Card>}
              </div>
            </TabsContent>
          </Tabs>
        </>
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Route?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the route
              and remove it from assigned trucks.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={!!singleMapPoint} onOpenChange={(open) => !open && setSingleMapPoint(null)}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>{singleMapPoint?.title || "Location Map"}</DialogTitle>
          </DialogHeader>
          <div className="h-[520px] overflow-hidden rounded-xl border">
            {singleMapPoint && window.google?.maps ? (
              <GoogleMap
                mapContainerStyle={{ width: "100%", height: "100%" }}
                center={{ lat: singleMapPoint.lat, lng: singleMapPoint.lng }}
                zoom={17}
                options={{ streetViewControl: false, mapTypeControl: true, fullscreenControl: true }}
              >
                <Marker
                  position={{ lat: singleMapPoint.lat, lng: singleMapPoint.lng }}
                  title={singleMapPoint.title}
                  icon={{
                    path: window.google.maps.SymbolPath.CIRCLE,
                    fillColor: singleMapPoint.type === "gts" ? "#0284c7" : "#dc2626",
                    fillOpacity: 1,
                    strokeColor: "#ffffff",
                    strokeWeight: 3,
                    scale: 12,
                  }}
                />
              </GoogleMap>
            ) : (
              <div className="flex h-full items-center justify-center text-muted-foreground">Map is loading...</div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
