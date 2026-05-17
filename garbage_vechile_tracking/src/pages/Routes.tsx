import { useState, useMemo, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
import { trucks, gtpLocations, finalDumpingSites, RouteData, TruckType } from "@/data/fleetData";
import { toast } from "sonner";
import RouteMapBuilder from "@/components/RouteMapBuilder";
import RouteListView from "@/components/RouteListView";
import { useZones, useZoneWards, useRoutes, useRoutePickupPoints } from "@/hooks/useDataQueries";
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
  const [isBuilderOpen, setIsBuilderOpen] = useState(false);
  const [editingRoute, setEditingRoute] = useState<RouteData | null>(null);
  const [newRouteType, setNewRouteType] = useState<TruckType>("primary");
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [routeToDelete, setRouteToDelete] = useState<string | null>(null);
  const [routeIdForPoints, setRouteIdForPoints] = useState<string | null>(null);

  // Fetch pickup points for the route being edited or viewed
  const { data: pickupPointsData = [] } = useRoutePickupPoints(routeIdForPoints);

  // Sync API routes to state
  useEffect(() => {
    const normalizedRoutes = (routesAPIData as any[]).map((route) => ({
      ...route,
      zoneId: route.zoneId || route.zone_id,
      wardId: route.wardId || route.ward_id,
      estimatedDistance: route.estimatedDistance ?? route.estimated_distance,
      estimatedTime: route.estimatedTime ?? route.estimated_time,
      totalPickupPoints: route.totalPickupPoints ?? route.total_pickup_points,
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

    const points = pickupPointsData.map((pp: any, index: number) => ({
      id: pp.id,
      position: { lat: pp.latitude, lng: pp.longitude },
      name: pp.name,
      type: (pp.type || 'pickup') as "pickup" | "gtp" | "dumping",
      order: index + 1,
      scheduledTime: pp.expected_pickup_time || pp.expectedPickupTime,
    }));

    return {
      ...selectedRoute,
      points,
    };
  }, [selectedRoute, pickupPointsData]);

  // Transform pickup points for editing route
  const enrichedEditingRoute = useMemo(() => {
    if (!editingRoute) return null;
    if (!pickupPointsData || pickupPointsData.length === 0) return editingRoute;

    const points = pickupPointsData.map((pp: any, index: number) => ({
      id: pp.id,
      position: { lat: pp.latitude, lng: pp.longitude },
      name: pp.name,
      type: (pp.type || 'pickup') as "pickup" | "gtp" | "dumping",
      order: index + 1,
      scheduledTime: pp.expected_pickup_time || pp.expectedPickupTime,
    }));

    return {
      ...editingRoute,
      points,
    };
  }, [editingRoute, pickupPointsData]);

  // Fetch zones and wards from API
  const { data: zonesData = [], isLoading: isLoadingZones } = useZones();
  const { data: wardsData = [], isLoading: isLoadingWards } = useZoneWards(filterZoneId !== "all" ? filterZoneId : "");

  // Memoized wards for selected zone
  const wardsForZone = useMemo(() => {
    if (filterZoneId === "all") {
      // If all zones selected, return all wards (from fleetData as fallback)
      return wardsData.length > 0 ? wardsData : [];
    }
    return wardsData;
  }, [filterZoneId, wardsData]);

  // Apply all filters to routes
  const filteredRoutes = useMemo(() => {
    return routesData.filter(r => {
      // Type filter
      if (filterType !== "all" && r.type !== filterType) return false;
      // Zone filter
      if (filterZoneId !== "all" && r.zoneId !== filterZoneId) return false;
      // Ward filter
      if (filterWardId !== "all" && r.wardId !== filterWardId) return false;
      return true;
    });
  }, [routesData, filterType, filterZoneId, filterWardId]);

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
                      Primary trucks collect garbage from pickup points and dump at GTPs (Garbage Transfer Points).
                    </p>
                    <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                      <MapPin className="h-3 w-3" /> Pickup Points → <ArrowRight className="h-3 w-3" /> GTP
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
                      Secondary trucks pick garbage from GTPs and transport to final dumping yards.
                    </p>
                    <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                      <MapPin className="h-3 w-3" /> GTP → <ArrowRight className="h-3 w-3" /> Final Dumping Yard
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <Tabs defaultValue="routes" className="space-y-4">
            <TabsList>
              <TabsTrigger value="routes">All Routes ({filteredRoutes.length})</TabsTrigger>
              <TabsTrigger value="gtp">GTP Locations ({gtpLocations.length})</TabsTrigger>
              <TabsTrigger value="dumping">Final Dumping Sites ({finalDumpingSites.length})</TabsTrigger>
            </TabsList>

            <TabsContent value="routes">
              <div className="space-y-4">
                {/* Filters Panel */}
                <Card className="p-4">
                  <CardContent className="p-0">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
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

                      {/* Clear Filters Button */}
                      {(filterType !== "all" || filterZoneId !== "all" || filterWardId !== "all") && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setFilterType("all");
                            setFilterZoneId("all");
                            setFilterWardId("all");
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
                {gtpLocations.map((gtp) => (
                  <Card key={gtp.id} className="p-4 border-l-4 border-l-amber-500">
                    <CardContent className="p-0">
                      <div className="flex items-start justify-between mb-3">
                        <div className="h-12 w-12 rounded-xl bg-amber-500/10 flex items-center justify-center">
                          <MapPin className="h-5 w-5 text-amber-500" />
                        </div>
                        <Badge variant="outline">{gtp.ward}</Badge>
                      </div>
                      <h3 className="font-semibold mb-1">{gtp.name}</h3>
                      <p className="text-sm text-muted-foreground mb-3">Capacity: {gtp.capacity}</p>
                      <div className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span>Current Fill</span>
                          <span className={gtp.currentFill > 80 ? "text-destructive" : gtp.currentFill > 60 ? "text-amber-500" : "text-green-500"}>
                            {gtp.currentFill}%
                          </span>
                        </div>
                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full ${gtp.currentFill > 80 ? "bg-destructive" : gtp.currentFill > 60 ? "bg-amber-500" : "bg-green-500"}`}
                            style={{ width: `${gtp.currentFill}%` }}
                          />
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground mt-2">
                        {gtp.position.lat.toFixed(4)}, {gtp.position.lng.toFixed(4)}
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="dumping">
              <div className="grid md:grid-cols-2 gap-4">
                {finalDumpingSites.map((site) => (
                  <Card key={site.id} className="p-4 border-l-4 border-l-destructive">
                    <CardContent className="p-0">
                      <div className="flex items-start gap-4">
                        <div className="h-12 w-12 rounded-xl bg-destructive/10 flex items-center justify-center">
                          <MapPin className="h-6 w-6 text-destructive" />
                        </div>
                        <div className="flex-1">
                          <h3 className="font-semibold text-lg mb-1">{site.name}</h3>
                          <p className="text-muted-foreground mb-2">Final Dumping Site</p>
                          <div className="flex items-center gap-4 text-sm">
                            <span className="flex items-center gap-1">
                              <Truck className="h-4 w-4" /> Capacity: {site.capacity}
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground mt-2">
                            Coordinates: {site.position.lat.toFixed(4)}, {site.position.lng.toFixed(4)}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
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
    </div>
  );
}
