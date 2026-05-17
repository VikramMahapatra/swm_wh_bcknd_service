import { useState, useMemo, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue 
} from "@/components/ui/select";
import { 
  MapPin, Plus, Building2, Home, Hospital, 
  ShoppingBag, Trash2, Edit, Route, Map, Loader2, AlertCircle
} from "lucide-react";
import { useZones, useZoneWards, useRoutes, usePickupPoints } from "@/hooks/useDataQueries";
import { PageHeader } from "@/components/PageHeader";

const typeConfig = {
  residential: { icon: Home, color: "text-primary", bgColor: "bg-primary/20", label: "Residential" },
  commercial: { icon: Building2, color: "text-chart-1", bgColor: "bg-chart-1/20", label: "Commercial" },
  hospital: { icon: Hospital, color: "text-destructive", bgColor: "bg-destructive/20", label: "Hospital" },
  market: { icon: ShoppingBag, color: "text-warning", bgColor: "bg-warning/20", label: "Market" },
  gtp: { icon: MapPin, color: "text-amber-600", bgColor: "bg-amber-500/20", label: "GTP" },
  dumping: { icon: Trash2, color: "text-red-600", bgColor: "bg-red-500/20", label: "Dumping Yard" },
};

type PickupPointView = {
  id: string;
  name: string;
  type: keyof typeof typeConfig;
  wardId: string;
  wardName: string;
  routeId?: string;
  schedule?: string;
  expectedPickupTime?: string;
  position: { lat: number; lng: number };
  lastCollection?: string;
};

export default function PickupPoints() {
  const { data: zonesData = [], isLoading: isLoadingZones } = useZones();
  const [filterZone, setFilterZone] = useState<string>("all");
  const { data: wardsData = [], isLoading: isLoadingWards } = useZoneWards(filterZone !== "all" ? filterZone : (zonesData[0]?.id || ""));
  const { data: routesData = [], isLoading: isLoadingRoutes } = useRoutes();
  const { data: pickupPointsData = [], isLoading: isLoadingPickupPoints } = usePickupPoints();

  const [zones, setZones] = useState([]);
  const [wards, setWards] = useState([]);
  const [apiRoutes, setApiRoutes] = useState([]);

  useEffect(() => {
    if (zonesData.length > 0) setZones(zonesData);
  }, [zonesData]);

  useEffect(() => {
    if (wardsData.length > 0) {
      const normalizedWards = (wardsData as any[]).map((ward) => ({
        ...ward,
        zoneId: ward.zoneId || ward.zone_id,
      }));
      setWards(normalizedWards);
    }
  }, [wardsData]);

  useEffect(() => {
    if (routesData.length > 0) {
      const normalizedRoutes = (routesData as any[]).map((route) => ({
        ...route,
        zoneId: route.zoneId || route.zone_id,
        wardId: route.wardId || route.ward_id,
      }));
      setApiRoutes(normalizedRoutes);
    }
  }, [routesData]);

  const [filterWard, setFilterWard] = useState<string>("all");
  const [filterRoute, setFilterRoute] = useState<string>("all");
  const [selectedPoint, setSelectedPoint] = useState<PickupPointView | null>(null);

  // Get unique zones
  const allZones = useMemo(() => zones.filter(z => z.status === 'active'), [zones]);
  
  // Get wards based on selected zone
  const filteredWards = useMemo(() => {
    if (filterZone === "all") {
      return wards.filter(w => w.status === 'active');
    }
    return wards.filter(w => w.zoneId === filterZone && w.status === 'active');
  }, [filterZone, wards]);

  const normalizedPoints = useMemo(() => {
    return (pickupPointsData as any[]).map((point) => {
      const wardId = point.ward_id || point.wardId;
      const wardName = wards.find((ward) => ward.id === wardId)?.name || wardId || 'Unknown';
      return {
        id: point.id,
        name: point.name,
        type: (point.type || 'residential') as keyof typeof typeConfig,
        wardId,
        wardName,
        routeId: point.route_id || point.routeId,
        schedule: point.schedule,
        expectedPickupTime: point.expected_pickup_time || point.expectedPickupTime,
        position: { lat: point.latitude, lng: point.longitude },
        lastCollection: point.last_collection || point.lastCollection,
      } as PickupPointView;
    });
  }, [pickupPointsData, wards]);

  // Filter points based on selections
  const filteredPoints = useMemo(() => {
    return normalizedPoints.filter(point => {
      const matchesZone = filterZone === "all" || wards.find(w => w.id === point.wardId)?.zoneId === filterZone;
      const matchesWard = filterWard === "all" || point.wardId === filterWard;
      const matchesRoute = filterRoute === "all" || point.routeId === filterRoute;
      return matchesZone && matchesWard && matchesRoute;
    });
  }, [filterZone, filterWard, filterRoute, normalizedPoints, wards]);

  // Calculate stats based on filtered points
  const stats = useMemo(() => ({
    totalPoints: filteredPoints.length,
    gtpCount: filteredPoints.filter(p => p.type === "gtp").length,
    assignedToRoutes: filteredPoints.filter(p => p.routeId).length,
  }), [filteredPoints]);

  useEffect(() => {
    if (filteredPoints.length === 0) {
      setSelectedPoint(null);
      return;
    }

    const stillVisible = selectedPoint && filteredPoints.some(point => point.id === selectedPoint.id);
    if (!stillVisible) {
      setSelectedPoint(filteredPoints[0]);
    }
  }, [filteredPoints, selectedPoint]);

  const getRouteInfo = (routeId?: string) => apiRoutes.find((route: any) => route.id === routeId);

  // Reset ward when zone changes
  const handleZoneChange = (value: string) => {
    setFilterZone(value);
    setFilterWard("all");
  };

  const hasActiveFilters = filterZone !== "all" || filterWard !== "all" || filterRoute !== "all";

  const clearFilters = () => {
    setFilterZone("all");
    setFilterWard("all");
    setFilterRoute("all");
  };

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      <PageHeader
        category="Master Data"
        title="Pickup Points"
        description="Manage pickup point locations and schedules"
        icon={MapPin}
        actions={
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            Add Pickup Point
          </Button>
        }
      />

      {/* Stats */}
      <div className="grid md:grid-cols-3 gap-4">
        <Card className="p-4 border-l-4 border-l-primary">
          <CardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Points</p>
                <p className="text-2xl font-bold text-foreground">{stats.totalPoints}</p>
                <p className="text-xs text-muted-foreground mt-1">Across all active wards</p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
                <MapPin className="h-6 w-6 text-primary" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="p-4 border-l-4 border-l-warning">
          <CardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">GTP Locations</p>
                <p className="text-2xl font-bold text-warning">{stats.gtpCount}</p>
                <p className="text-xs text-muted-foreground mt-1">Transfer points in this view</p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-warning/10 flex items-center justify-center">
                <Map className="h-6 w-6 text-warning" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="p-4 border-l-4 border-l-success">
          <CardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Assigned to Routes</p>
                <p className="text-2xl font-bold text-success">{stats.assignedToRoutes}</p>
                <p className="text-xs text-muted-foreground mt-1">Linked to active routes</p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-success/10 flex items-center justify-center">
                <Route className="h-6 w-6 text-success" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <CardContent className="p-0">
          <div className="flex flex-wrap gap-4 items-center">
            <Select value={filterZone} onValueChange={handleZoneChange}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Zone" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Zones</SelectItem>
                {allZones.map(zone => (
                  <SelectItem key={zone.id} value={zone.id}>{zone.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={filterWard} onValueChange={setFilterWard}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Ward" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Wards</SelectItem>
                {filteredWards.map(ward => (
                  <SelectItem key={ward.id} value={ward.id}>{ward.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={filterRoute} onValueChange={setFilterRoute}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Route" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Routes</SelectItem>
                {apiRoutes.map((route: any) => (
                  <SelectItem key={route.id} value={route.id}>{route.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {hasActiveFilters && (
              <Button variant="ghost" size="sm" onClick={clearFilters} className="text-muted-foreground">
                Clear Filters
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Main Content */}
      <div className="grid lg:grid-cols-3 gap-4">
        {/* Points List */}
        <Card className="lg:col-span-2 p-4">
          <CardHeader className="p-0 pb-3">
            <CardTitle>Pickup Points ({filteredPoints.length})</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[500px]">
              <div className="grid md:grid-cols-2 gap-3">
                {filteredPoints.map((point) => {
                  const config = typeConfig[point.type] || typeConfig.residential;
                  const TypeIcon = config.icon;
                  const route = getRouteInfo(point.routeId);
                  const borderClass =
                    point.type === "residential" ? "border-l-primary" :
                    point.type === "commercial" ? "border-l-chart-1" :
                    point.type === "hospital" ? "border-l-destructive" :
                    point.type === "market" ? "border-l-warning" :
                    point.type === "gtp" ? "border-l-amber-500" :
                    "border-l-red-500";
                  
                  return (
                    <div
                      key={point.id}
                      onClick={() => setSelectedPoint(point)}
                      className={`p-4 border border-border border-l-4 ${borderClass} rounded-lg cursor-pointer hover:shadow-lg transition-all ${
                        selectedPoint?.id === point.id ? "bg-primary/10 border-primary" : ""
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div className={`h-8 w-8 rounded-lg ${config.bgColor} flex items-center justify-center`}>
                            <TypeIcon className={`h-4 w-4 ${config.color}`} />
                          </div>
                          <div>
                            <h4 className="font-medium text-sm">{point.name}</h4>
                            <p className="text-xs text-muted-foreground">{point.id}</p>
                          </div>
                        </div>
                        <Badge variant="outline" className="text-xs">{point.wardName}</Badge>
                      </div>
                      
                      <div className="space-y-2 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="text-muted-foreground">Schedule:</span>
                          <span>{point.schedule}</span>
                        </div>
                        
                        {route && (
                          <div className="flex items-center justify-between pt-1 border-t border-border">
                            <span className="text-muted-foreground">Route:</span>
                            <Badge variant="outline" className="text-xs">{route.name}</Badge>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Details Panel */}
        <Card className="p-4">
          {selectedPoint ? (
            <>
              <CardHeader className="p-0 pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{selectedPoint.name}</CardTitle>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="icon">
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="text-destructive">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-0 space-y-4">
                <div className="flex items-center gap-2">
                  {(() => {
                    const config = typeConfig[selectedPoint.type] || typeConfig.residential;
                    const TypeIcon = config.icon;
                    return (
                      <>
                        <div className={`h-10 w-10 rounded-xl ${config.bgColor} flex items-center justify-center`}>
                          <TypeIcon className={`h-5 w-5 ${config.color}`} />
                        </div>
                        <div>
                          <Badge variant="outline" className="capitalize">{config.label}</Badge>
                          <p className="text-xs text-muted-foreground mt-1">{selectedPoint.wardName}</p>
                        </div>
                      </>
                    );
                  })()}
                </div>

                <div className="space-y-3">
                  <div className="flex justify-between py-2 border-b border-border">
                    <span className="text-muted-foreground">ID</span>
                    <span className="font-medium">{selectedPoint.id}</span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-border">
                    <span className="text-muted-foreground">Schedule</span>
                    <span className="font-medium">{selectedPoint.schedule}</span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-border">
                    <span className="text-muted-foreground">Coordinates</span>
                    <span className="font-medium text-xs">
                      {selectedPoint.position.lat.toFixed(4)}, {selectedPoint.position.lng.toFixed(4)}
                    </span>
                  </div>
                  {selectedPoint.lastCollection && (
                    <div className="flex justify-between py-2 border-b border-border">
                      <span className="text-muted-foreground">Last Collection</span>
                      <span className="font-medium text-sm">{selectedPoint.lastCollection}</span>
                    </div>
                  )}
                </div>

                  {selectedPoint.routeId && (
                  <div className="p-4 bg-primary/10 rounded-lg">
                    <h4 className="font-medium mb-2">Assigned Route</h4>
                    {(() => {
                        const route = getRouteInfo(selectedPoint.routeId);
                      return route ? (
                        <div className="flex items-center justify-between">
                          <span>{route.name}</span>
                          <Badge variant="outline" className="capitalize">{route.type}</Badge>
                        </div>
                      ) : (
                        <span className="text-muted-foreground">Not assigned</span>
                      );
                    })()}
                  </div>
                )}
              </CardContent>
            </>
          ) : (
            <CardContent className="p-0 h-[500px] flex items-center justify-center text-muted-foreground">
              <div className="text-center">
                <MapPin className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Select a pickup point to view details</p>
              </div>
            </CardContent>
          )}
        </Card>
      </div>
    </div>
  );
}