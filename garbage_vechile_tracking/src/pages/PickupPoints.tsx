import { useEffect, useMemo, useState } from "react";
import { GoogleMap, InfoWindow, Marker } from "@react-google-maps/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Building2, Clock, Edit, Home, Hospital, Map, MapPin, Route, Search, ShoppingBag, Trash2, X } from "lucide-react";
import { usePickupPoints, useRoutes, useWards, useZones } from "@/hooks/useDataQueries";
import { PageHeader } from "@/components/PageHeader";

const mapContainerStyle = { width: "100%", height: "100%" };
const defaultCenter = { lat: 18.6559, lng: 73.7714 };

type PointKind = "residential" | "commercial" | "hospital" | "market" | "gts" | "dumping";

const typeConfig: Record<PointKind, { icon: any; color: string; bgColor: string; border: string; label: string; marker: string }> = {
  residential: { icon: Home, color: "text-emerald-700", bgColor: "bg-emerald-100", border: "border-l-emerald-500", label: "Residential", marker: "#10b981" },
  commercial: { icon: Building2, color: "text-cyan-700", bgColor: "bg-cyan-100", border: "border-l-cyan-500", label: "Commercial", marker: "#0891b2" },
  hospital: { icon: Hospital, color: "text-rose-700", bgColor: "bg-rose-100", border: "border-l-rose-500", label: "Hospital", marker: "#e11d48" },
  market: { icon: ShoppingBag, color: "text-amber-700", bgColor: "bg-amber-100", border: "border-l-amber-500", label: "Market", marker: "#f59e0b" },
  gts: { icon: MapPin, color: "text-sky-700", bgColor: "bg-sky-100", border: "border-l-sky-500", label: "GTS", marker: "#0284c7" },
  dumping: { icon: Trash2, color: "text-red-700", bgColor: "bg-red-100", border: "border-l-red-500", label: "Dumping Yard", marker: "#dc2626" },
};

type PickupPointView = {
  id: string;
  name: string;
  type: PointKind;
  wardId: string;
  wardName: string;
  zoneId: string;
  routeId?: string;
  routeName?: string;
  expectedPickupTime?: string;
  schedule?: string;
  sequenceNo?: number;
  isGts: boolean;
  radiusM?: number;
  position: { lat: number; lng: number };
  lastCollection?: string;
};

export default function PickupPoints() {
  const { data: zonesData = [], isLoading: isLoadingZones } = useZones();
  const { data: wardsData = [], isLoading: isLoadingWards } = useWards();
  const { data: routesData = [], isLoading: isLoadingRoutes } = useRoutes();
  const { data: pickupPointsData = [], isLoading: isLoadingPickupPoints } = usePickupPoints();

  const [filterZone, setFilterZone] = useState("all");
  const [filterWard, setFilterWard] = useState("all");
  const [filterRoute, setFilterRoute] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPoint, setSelectedPoint] = useState<PickupPointView | null>(null);
  const [hoverPoint, setHoverPoint] = useState<PickupPointView | null>(null);

  const zones = useMemo(() => (zonesData as any[]).map((zone) => ({
    ...zone,
    id: String(zone.id),
    name: String(zone.name || zone.zone_name || "Zone"),
    status: String(zone.status || (zone.active === false ? "inactive" : "active")),
  })), [zonesData]);

  const wards = useMemo(() => (wardsData as any[]).map((ward) => ({
    ...ward,
    id: String(ward.id),
    name: String(ward.name || ward.ward_name || "Ward"),
    zoneId: String(ward.zoneId || ward.zone_id || ""),
    status: String(ward.status || (ward.active === false ? "inactive" : "active")),
  })), [wardsData]);

  const routes = useMemo(() => (routesData as any[]).map((route) => ({
    ...route,
    id: String(route.id),
    name: String(route.name || route.route_name || "Route"),
    zoneId: String(route.zoneId || route.zone_id || ""),
    wardId: String(route.wardId || route.ward_id || ""),
  })), [routesData]);

  const filteredWards = useMemo(() => {
    if (filterZone === "all") return wards.filter((ward) => ward.status === "active");
    return wards.filter((ward) => ward.zoneId === filterZone && ward.status === "active");
  }, [filterZone, wards]);

  const filteredRoutesForControls = useMemo(() => {
    return routes.filter((route) => {
      if (filterZone !== "all" && route.zoneId !== filterZone) return false;
      if (filterWard !== "all" && route.wardId !== filterWard) return false;
      return true;
    });
  }, [routes, filterZone, filterWard]);

  useEffect(() => {
    setFilterWard("all");
    setFilterRoute("all");
  }, [filterZone]);

  useEffect(() => {
    setFilterRoute("all");
  }, [filterWard]);

  const normalizedPoints = useMemo(() => {
    return (pickupPointsData as any[]).map((point) => {
      const wardId = String(point.ward_id || point.wardId || "");
      const routeId = String(point.route_id || point.routeId || "");
      const ward = wards.find((item) => item.id === wardId);
      const route = routes.find((item) => item.id === routeId);
      const isGts = Boolean(point.is_gts ?? point.isGts ?? point.is_GTS);
      const rawType = String(point.type || "residential").toLowerCase();
      const type = (isGts ? "gts" : rawType === "dumping" ? "dumping" : rawType in typeConfig ? rawType : "residential") as PointKind;
      return {
        id: String(point.id || ""),
        name: String(point.name || point.pickup_name || point.pickupName || "Pickup Point"),
        type,
        wardId,
        wardName: ward?.name || wardId || "Unassigned ward",
        zoneId: String(point.zone_id || point.zoneId || ward?.zoneId || route?.zoneId || ""),
        routeId: routeId || undefined,
        routeName: route?.name,
        expectedPickupTime: point.expected_pickup_time || point.expectedPickupTime || "",
        schedule: point.schedule || (point.expected_pickup_time || point.expectedPickupTime ? `Daily ${point.expected_pickup_time || point.expectedPickupTime}` : "Daily"),
        sequenceNo: Number(point.sequence_no ?? point.sequenceNo ?? point.order ?? 0) || undefined,
        isGts,
        radiusM: Number(point.pickup_radius_m ?? point.pickupRadiusM ?? 0) || undefined,
        position: { lat: Number(point.latitude ?? point.lat ?? 0), lng: Number(point.longitude ?? point.lng ?? 0) },
        lastCollection: point.last_collection || point.lastCollection,
      } as PickupPointView;
    }).filter((point) => Number.isFinite(point.position.lat) && Number.isFinite(point.position.lng));
  }, [pickupPointsData, routes, wards]);

  const filteredPoints = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return normalizedPoints.filter((point) => {
      if (filterZone !== "all" && point.zoneId !== filterZone) return false;
      if (filterWard !== "all" && point.wardId !== filterWard) return false;
      if (filterRoute !== "all" && point.routeId !== filterRoute) return false;
      if (!q) return true;
      return [point.name, point.id, point.wardName, point.routeName, point.expectedPickupTime].filter(Boolean).some((value) => String(value).toLowerCase().includes(q));
    });
  }, [filterRoute, filterWard, filterZone, normalizedPoints, searchQuery]);

  useEffect(() => {
    if (filteredPoints.length === 0) {
      setSelectedPoint(null);
      return;
    }
    if (!selectedPoint || !filteredPoints.some((point) => point.id === selectedPoint.id)) {
      setSelectedPoint(filteredPoints[0]);
    }
  }, [filteredPoints, selectedPoint]);

  const stats = useMemo(() => ({
    totalPoints: filteredPoints.length,
    gtsCount: filteredPoints.filter((point) => point.isGts).length,
    assignedToRoutes: filteredPoints.filter((point) => point.routeId).length,
    timedPoints: filteredPoints.filter((point) => point.expectedPickupTime).length,
  }), [filteredPoints]);

  const mapCenter = selectedPoint?.position || filteredPoints[0]?.position || defaultCenter;
  const hasActiveFilters = filterZone !== "all" || filterWard !== "all" || filterRoute !== "all" || searchQuery.trim() !== "";
  const isLoading = isLoadingZones || isLoadingWards || isLoadingRoutes || isLoadingPickupPoints;

  const clearFilters = () => {
    setFilterZone("all");
    setFilterWard("all");
    setFilterRoute("all");
    setSearchQuery("");
  };

  const markerIcon = (point: PickupPointView) => {
    if (!window.google?.maps) return undefined;
    return {
      path: window.google.maps.SymbolPath.CIRCLE,
      fillColor: typeConfig[point.type].marker,
      fillOpacity: 1,
      strokeColor: "#ffffff",
      strokeWeight: 3,
      scale: point.isGts ? 13 : 10,
    };
  };

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      <PageHeader
        category="Master Data"
        title="Pickup Points"
        description="Route-wise pickup locations, GTS endpoints, schedules, and map visibility"
        icon={MapPin}
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Card className="overflow-hidden border-l-4 border-l-emerald-500 bg-gradient-to-br from-emerald-50 via-white to-teal-50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Points</p>
                <p className="text-3xl font-bold text-emerald-700">{stats.totalPoints}</p>
              </div>
              <div className="h-12 w-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center">
                <MapPin className="h-6 w-6 text-emerald-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="overflow-hidden border-l-4 border-l-sky-500 bg-gradient-to-br from-sky-50 via-white to-cyan-50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">GTS Points</p>
                <p className="text-3xl font-bold text-sky-700">{stats.gtsCount}</p>
              </div>
              <div className="h-12 w-12 rounded-2xl bg-sky-500/10 flex items-center justify-center">
                <Map className="h-6 w-6 text-sky-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="overflow-hidden border-l-4 border-l-teal-500 bg-gradient-to-br from-teal-50 via-white to-emerald-50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Assigned Routes</p>
                <p className="text-3xl font-bold text-teal-700">{stats.assignedToRoutes}</p>
              </div>
              <div className="h-12 w-12 rounded-2xl bg-teal-500/10 flex items-center justify-center">
                <Route className="h-6 w-6 text-teal-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="overflow-hidden border-l-4 border-l-amber-500 bg-gradient-to-br from-amber-50 via-white to-orange-50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Timed Points</p>
                <p className="text-3xl font-bold text-amber-700">{stats.timedPoints}</p>
              </div>
              <div className="h-12 w-12 rounded-2xl bg-amber-500/10 flex items-center justify-center">
                <Clock className="h-6 w-6 text-amber-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-emerald-100 bg-gradient-to-r from-white via-emerald-50/40 to-sky-50/50 shadow-sm">
        <CardContent className="p-4">
          <div className="grid gap-3 md:grid-cols-5">
            <div className="relative md:col-span-2">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input className="pl-10" value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder="Search pickup name, route, ward, time..." />
            </div>
            <Select value={filterZone} onValueChange={setFilterZone}>
              <SelectTrigger><SelectValue placeholder="Zone" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Zones</SelectItem>
                {zones.filter((zone) => zone.status === "active").map((zone) => <SelectItem key={zone.id} value={zone.id}>{zone.name}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={filterWard} onValueChange={setFilterWard} disabled={filterZone === "all"}>
              <SelectTrigger><SelectValue placeholder="Ward" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Wards</SelectItem>
                {filteredWards.map((ward) => <SelectItem key={ward.id} value={ward.id}>{ward.name}</SelectItem>)}
              </SelectContent>
            </Select>
            <div className="flex gap-2">
              <Select value={filterRoute} onValueChange={setFilterRoute}>
                <SelectTrigger><SelectValue placeholder="Route" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Routes</SelectItem>
                  {filteredRoutesForControls.map((route) => <SelectItem key={route.id} value={route.id}>{route.name}</SelectItem>)}
                </SelectContent>
              </Select>
              {hasActiveFilters && <Button variant="outline" size="icon" onClick={clearFilters}><X className="h-4 w-4" /></Button>}
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[1.15fr_1fr]">
        <Card className="overflow-hidden border-emerald-100 shadow-sm">
          <CardHeader className="border-b bg-gradient-to-r from-emerald-50 to-sky-50 py-4">
            <CardTitle className="flex items-center justify-between text-base">
              <span>Pickup Register ({filteredPoints.length})</span>
              {isLoading && <Badge variant="outline">Loading...</Badge>}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[610px]">
              <div className="divide-y">
                {filteredPoints.map((point) => {
                  const config = typeConfig[point.type];
                  const TypeIcon = config.icon;
                  return (
                    <button
                      key={point.id}
                      type="button"
                      onClick={() => setSelectedPoint(point)}
                      className={`w-full border-l-4 ${config.border} p-4 text-left transition hover:bg-emerald-50/50 ${selectedPoint?.id === point.id ? "bg-emerald-50 ring-1 ring-inset ring-emerald-200" : "bg-white"}`}
                    >
                      <div className="flex items-start gap-3">
                        <div className={`h-11 w-11 shrink-0 rounded-2xl ${config.bgColor} flex items-center justify-center`}>
                          <TypeIcon className={`h-5 w-5 ${config.color}`} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <h4 className="font-semibold text-slate-900 truncate">{point.sequenceNo ? `${point.sequenceNo}. ` : ""}{point.name}</h4>
                            <Badge className={point.isGts ? "bg-sky-100 text-sky-700 border-sky-200" : "bg-emerald-100 text-emerald-700 border-emerald-200"}>{config.label}</Badge>
                          </div>
                          <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                            <span>{point.wardName}</span>
                            {point.routeName && <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">{point.routeName}</span>}
                            {point.expectedPickupTime && <span className="font-medium text-amber-700">{point.expectedPickupTime}</span>}
                            {point.radiusM && <span>{point.radiusM}m radius</span>}
                          </div>
                        </div>
                        <MapPin className={`mt-1 h-4 w-4 ${config.color}`} />
                      </div>
                    </button>
                  );
                })}
                {filteredPoints.length === 0 && (
                  <div className="p-10 text-center text-muted-foreground">
                    <MapPin className="mx-auto mb-3 h-10 w-10 opacity-50" />
                    No pickup points match the current filters.
                  </div>
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="overflow-hidden border-sky-100 shadow-sm">
            <CardHeader className="border-b bg-gradient-to-r from-sky-50 to-emerald-50 py-4">
              <CardTitle className="flex items-center gap-2 text-base"><Map className="h-5 w-5 text-sky-600" /> Pickup Map</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="h-[410px]">
                {window.google?.maps ? (
                  <GoogleMap mapContainerStyle={mapContainerStyle} center={mapCenter} zoom={selectedPoint ? 16 : 13} options={{ streetViewControl: false, mapTypeControl: true, fullscreenControl: true }}>
                    {filteredPoints.map((point) => (
                      <Marker
                        key={point.id}
                        position={point.position}
                        title={point.name}
                        icon={markerIcon(point)}
                        label={point.isGts ? { text: "GTS", color: "#ffffff", fontSize: "9px", fontWeight: "bold" } : undefined}
                        onClick={() => setSelectedPoint(point)}
                        onMouseOver={() => setHoverPoint(point)}
                        onMouseOut={() => setHoverPoint(null)}
                      />
                    ))}
                    {(hoverPoint || selectedPoint) && (
                      <InfoWindow position={(hoverPoint || selectedPoint)!.position} onCloseClick={() => setHoverPoint(null)}>
                        <div className="space-y-1 text-xs">
                          <p className="font-semibold">{(hoverPoint || selectedPoint)!.name}</p>
                          <p>{typeConfig[(hoverPoint || selectedPoint)!.type].label}</p>
                          {(hoverPoint || selectedPoint)!.expectedPickupTime && <p>Time: {(hoverPoint || selectedPoint)!.expectedPickupTime}</p>}
                        </div>
                      </InfoWindow>
                    )}
                  </GoogleMap>
                ) : (
                  <div className="flex h-full items-center justify-center text-muted-foreground">Map is loading...</div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="border-emerald-100 shadow-sm">
            {selectedPoint ? (
              <>
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <CardTitle className="text-lg">{selectedPoint.name}</CardTitle>
                      <p className="text-sm text-muted-foreground">{selectedPoint.id}</p>
                    </div>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="icon"><Edit className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" className="text-destructive"><Trash2 className="h-4 w-4" /></Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center gap-3 rounded-2xl bg-gradient-to-r from-emerald-50 to-sky-50 p-3">
                    {(() => {
                      const config = typeConfig[selectedPoint.type];
                      const TypeIcon = config.icon;
                      return <div className={`h-12 w-12 rounded-2xl ${config.bgColor} flex items-center justify-center`}><TypeIcon className={`h-6 w-6 ${config.color}`} /></div>;
                    })()}
                    <div>
                      <Badge className={selectedPoint.isGts ? "bg-sky-100 text-sky-700 border-sky-200" : "bg-emerald-100 text-emerald-700 border-emerald-200"}>{typeConfig[selectedPoint.type].label}</Badge>
                      <p className="mt-1 text-xs text-muted-foreground">{selectedPoint.wardName}</p>
                    </div>
                  </div>
                  <div className="grid gap-2 text-sm">
                    <div className="flex justify-between border-b py-2"><span className="text-muted-foreground">Route</span><span className="font-medium">{selectedPoint.routeName || "Not assigned"}</span></div>
                    <div className="flex justify-between border-b py-2"><span className="text-muted-foreground">Expected Time</span><span className="font-medium">{selectedPoint.expectedPickupTime || "Not set"}</span></div>
                    <div className="flex justify-between border-b py-2"><span className="text-muted-foreground">Geofence Radius</span><span className="font-medium">{selectedPoint.radiusM ? `${selectedPoint.radiusM} m` : "Not set"}</span></div>
                    <div className="flex justify-between border-b py-2"><span className="text-muted-foreground">Coordinates</span><span className="font-medium text-xs">{selectedPoint.position.lat.toFixed(6)}, {selectedPoint.position.lng.toFixed(6)}</span></div>
                    {selectedPoint.lastCollection && <div className="flex justify-between border-b py-2"><span className="text-muted-foreground">Last Collection</span><span className="font-medium">{selectedPoint.lastCollection}</span></div>}
                  </div>
                </CardContent>
              </>
            ) : (
              <CardContent className="flex h-[220px] items-center justify-center text-muted-foreground">
                <div className="text-center"><MapPin className="mx-auto mb-3 h-10 w-10 opacity-50" /><p>Select a pickup point to view details</p></div>
              </CardContent>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
