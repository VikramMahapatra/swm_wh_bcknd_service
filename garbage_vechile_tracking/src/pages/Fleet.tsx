import { useState, useCallback, useEffect, useMemo } from "react";
import { GoogleMap, Marker, InfoWindow, Polygon } from "@react-google-maps/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { PageHeader } from "@/components/PageHeader";
import { 
  Truck, MapPin, Signal, Battery, AlertTriangle, 
  CheckCircle, XCircle, Search, ChevronRight,
  Activity, TrendingUp, Zap, Navigation2, Gauge, Clock, Users
} from "lucide-react";
import { 
  gtpLocations, finalDumpingSites,
  KHARADI_CENTER, TruckData, TruckStatus 
} from "@/data/fleetData";
import { createTruckMarkerIcon } from "@/components/TruckIcon";
import { useSwmLiveFleet } from "@/hooks/useSwmLiveFleet";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const containerStyle = { width: '100%', height: '100%' };

const statusConfig: Record<TruckStatus, { color: string; label: string; bgClass: string }> = {
  moving: { color: "#22c55e", label: "Moving", bgClass: "bg-success" },
  idle: { color: "#f59e0b", label: "Idle", bgClass: "bg-warning" },
  dumping: { color: "#3b82f6", label: "Dumping", bgClass: "bg-chart-1" },
  offline: { color: "#6b7280", label: "Offline", bgClass: "bg-muted-foreground" },
  breakdown: { color: "#ef4444", label: "Breakdown", bgClass: "bg-destructive" },
};

export default function Fleet() {
  // State
  const [selectedTruck, setSelectedTruck] = useState<TruckData | null>(null);
  const [selectedMarker, setSelectedMarker] = useState<string | null>(null);
  const [isMapLoaded, setIsMapLoaded] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterZone, setFilterZone] = useState<string>("all");
  const [filterWard, setFilterWard] = useState<string>("all");
  const [filterType, setFilterType] = useState<"all" | "primary" | "secondary">("all");
  const [filterStatus, setFilterStatus] = useState<"all" | TruckStatus>("all");
  const [wardPolygons, setWardPolygons] = useState<Array<Array<{ lat: number; lng: number }>>>([]);
  const [wardMatchLabel, setWardMatchLabel] = useState<string | null>(null);
  const { trucks: liveMapTrucks, isConnected: isLiveFeedConnected } = useSwmLiveFleet();

  const availableZones = useMemo(() => {
    const seen = new Set<string>();
    const zones: Array<{ id: string; name: string }> = [];
    for (const truck of liveMapTrucks) {
      const id = (truck.zoneId || "").trim();
      if (!id || seen.has(id)) continue;
      seen.add(id);
      zones.push({ id, name: id });
    }
    return zones;
  }, [liveMapTrucks]);

  const availableWards = useMemo(() => {
    if (filterZone === "all") return [] as Array<{ id: string; name: string; zoneId: string }>;
    const seen = new Set<string>();
    const wards: Array<{ id: string; name: string; zoneId: string }> = [];
    for (const truck of liveMapTrucks) {
      if ((truck.zoneId || "") !== filterZone) continue;
      const id = (truck.wardId || "").trim();
      if (!id || seen.has(id)) continue;
      seen.add(id);
      wards.push({ id, name: id, zoneId: filterZone });
    }
    return wards;
  }, [liveMapTrucks, filterZone]);

  useEffect(() => {
    setFilterWard("all");
  }, [filterZone]);

  // Load KML ward boundaries when zone/ward filter changes
  useEffect(() => {
    if (filterZone === "all" || filterWard === "all") {
      setWardPolygons([]);
      setWardMatchLabel(null);
      return;
    }

    const selectedWard = availableWards.find((ward) => ward.id === filterWard);
    if (!selectedWard) {
      setWardPolygons([]);
      setWardMatchLabel(null);
      return;
    }

    const normalizeText = (value: string) => value.toLowerCase().replace(/[^a-z0-9]/g, "");
    const parseCoordinates = (value: string) => value
      .trim()
      .split(/\s+/)
      .map((pair) => {
        const [lng, lat] = pair.split(",").map(Number);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
        return { lat, lng };
      })
      .filter((point): point is { lat: number; lng: number } => point !== null);

    const loadWardBoundary = async () => {
      try {
        const response = await fetch("/ward-boundaries.kml");
        if (!response.ok) {
          setWardPolygons([]);
          setWardMatchLabel(null);
          return;
        }
        const kmlText = await response.text();
        const parser = new DOMParser();
        const xml = parser.parseFromString(kmlText, "application/xml");
        const placemarks = Array.from(xml.getElementsByTagName("Placemark"));
        const target = normalizeText(selectedWard.name);

        const extractSimpleData = (placemark: Element, name: string) => {
          const entries = Array.from(placemark.getElementsByTagName("SimpleData"));
          const match = entries.find((entry) => entry.getAttribute("name") === name);
          return match?.textContent?.trim() || "";
        };

        const matchPlacemark = placemarks.find((placemark) => {
          const wardName = normalizeText(extractSimpleData(placemark, "ward"));
          const prabhagName = normalizeText(extractSimpleData(placemark, "prabhag"));
          return wardName.includes(target) || prabhagName.includes(target) || target.includes(wardName) || target.includes(prabhagName);
        });

        if (!matchPlacemark) {
          console.warn('No KML placemark found for ward:', selectedWard.name);
          setWardPolygons([]);
          setWardMatchLabel(null);
          return;
        }

        const wardName = extractSimpleData(matchPlacemark, "ward");
        const prabhagName = extractSimpleData(matchPlacemark, "prabhag");
        setWardMatchLabel(prabhagName ? `${wardName} (${prabhagName})` : wardName || selectedWard.name);

        const boundaries = Array.from(matchPlacemark.getElementsByTagName("outerBoundaryIs"));
        const polygons = boundaries
          .map((boundary) => boundary.getElementsByTagName("coordinates")[0]?.textContent || "")
          .map((coords) => parseCoordinates(coords))
          .filter((path) => path.length > 0);

        console.log('Ward boundary loaded:', wardName, 'polygons:', polygons.length);
        setWardPolygons(polygons);
      } catch (error) {
        console.error('Error loading ward boundary:', error);
        setWardPolygons([]);
        setWardMatchLabel(null);
      }
    };

    loadWardBoundary();
  }, [filterZone, filterWard, availableWards]);

  const onMapLoad = useCallback(() => {
    setIsMapLoaded(true);
  }, []);

  // Filter trucks based on all filter criteria
  const filteredTrucks = useMemo(() => {
    return liveMapTrucks.filter(truck => {
      const matchesSearch = truck.truckNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           truck.driver.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesType = filterType === "all" || truck.truckType === filterType;
      const matchesZone = filterZone === "all" || truck.zoneId === filterZone;
      const matchesWard = filterWard === "all" || truck.wardId === filterWard;
      const matchesStatus = filterStatus === "all" || truck.status === filterStatus;
      
      return matchesSearch && matchesType && matchesZone && matchesWard && matchesStatus;
    });
  }, [liveMapTrucks, searchTerm, filterType, filterZone, filterWard, filterStatus]);

  // Update selected truck data when filters change
  const currentSelectedTruck = selectedTruck 
    ? filteredTrucks.find(t => t.id === selectedTruck.id) || selectedTruck
    : null;

  const handleTruckSelect = (truck: TruckData) => {
    setSelectedTruck(truck);
    setSelectedMarker(truck.id);
  };

  // Calculate online/offline status based on live truck status
  const onlineDevices = filteredTrucks.filter(t => t.status !== "offline" && t.status !== "breakdown");
  const offlineDevices = filteredTrucks.filter(t => t.status === "offline" || t.status === "breakdown");
  const warningDevices = filteredTrucks.filter(t => t.status === "idle");

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      <PageHeader
        category="Fleet"
        title="Fleet Management"
        description="Real-time vehicle tracking and fleet performance monitoring"
        icon={Truck}
        actions={
          <>
            <Badge variant="outline" className="gap-1 animate-in fade-in slide-in-from-top-2 duration-300">
              <Truck className="h-3 w-3" />
              {liveMapTrucks.length} Trucks
            </Badge>
            <Badge variant="outline" className="gap-1 text-success border-success animate-in fade-in slide-in-from-top-2 duration-300 delay-75">
              <CheckCircle className="h-3 w-3" />
              {onlineDevices.length} Online
            </Badge>
            {!isLiveFeedConnected && (
              <Badge variant="destructive" className="gap-1 animate-in fade-in slide-in-from-top-2 duration-300 delay-100">
                <XCircle className="h-3 w-3" />
                Live feed disconnected
              </Badge>
            )}
            {offlineDevices.length > 0 && (
              <Badge variant="destructive" className="gap-1 animate-in fade-in slide-in-from-top-2 duration-300 delay-150">
                <XCircle className="h-3 w-3" />
                {offlineDevices.length} Offline
              </Badge>
            )}
          </>
        }
      />

      <Tabs defaultValue="map" className="space-y-4">
        <TabsList>
          <TabsTrigger value="map" className="gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-success"></span>
            </span>
            Live Map
          </TabsTrigger>
          <TabsTrigger value="list">Truck List</TabsTrigger>
          <TabsTrigger value="devices">GPS Devices Report</TabsTrigger>
        </TabsList>

        <TabsContent value="map" className="space-y-4 animate-in fade-in duration-500">
          <div className="grid lg:grid-cols-4 gap-4">
            {/* Truck List Sidebar */}
            <Card className="lg:col-span-1 shadow-xl border-muted/40 rounded-3xl border-2 border-primary/20 bg-white/80 backdrop-blur-md">
              <CardHeader className="pb-3 space-y-3">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-success animate-pulse" />
                  <p className="text-sm font-semibold text-foreground">Live Fleet Monitor</p>
                  <Badge variant="secondary" className="ml-auto text-xs">{filteredTrucks.length}</Badge>
                </div>
                <div className="relative group">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
                  <Input
                    placeholder="Search trucks..."
                    className="pl-9 h-9 border-muted focus-visible:ring-primary"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>
                
                {/* Zone Filter */}
                <div className="mt-2">
                  <Select value={filterZone} onValueChange={(value) => {
                    setFilterZone(value);
                    setFilterWard("all");
                  }}>
                    <SelectTrigger className="text-xs">
                      <SelectValue placeholder="Select zone" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Zones</SelectItem>
                      {availableZones.map((zone) => (
                        <SelectItem key={zone.id} value={zone.id}>
                          {zone.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                {/* Ward Filter (only show when zone is selected) */}
                {filterZone !== "all" && availableWards.length > 0 && (
                  <div className="mt-2">
                    <Select value={filterWard} onValueChange={setFilterWard}>
                      <SelectTrigger className="text-xs">
                        <SelectValue placeholder="Select ward" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Wards</SelectItem>
                        {availableWards.map((ward: any) => (
                          <SelectItem key={ward.id} value={ward.id}>
                            {ward.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
                
                {/* Route Type Filter */}
                <div className="flex gap-1.5 mt-2">
                  {["all", "primary", "secondary"].map((type) => (
                    <Button
                      key={type}
                      variant={filterType === type ? "default" : "outline"}
                      size="sm"
                      className={`flex-1 text-xs capitalize transition-all duration-200 ${
                        filterType === type 
                          ? 'shadow-md scale-105' 
                          : 'hover:scale-105'
                      }`}
                      onClick={() => setFilterType(type as typeof filterType)}
                    >
                      {type}
                    </Button>
                  ))}
                </div>
                
                {/* Status Filter */}
                <div className="mt-2">
                  <Select value={filterStatus} onValueChange={(value) => setFilterStatus(value as typeof filterStatus)}>
                    <SelectTrigger className="text-xs">
                      <SelectValue placeholder="Select status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Status</SelectItem>
                      <SelectItem value="moving">Moving</SelectItem>
                      <SelectItem value="idle">Idle</SelectItem>
                      <SelectItem value="dumping">Dumping</SelectItem>
                      <SelectItem value="offline">Offline</SelectItem>
                      <SelectItem value="breakdown">Breakdown</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <ScrollArea className="h-[500px]">
                  {filteredTrucks.map((truck, index) => {
                    // Use more visible even/odd row coloring
                    const rowBg = index % 2 === 0
                      ? "bg-slate-50/80"
                      : "bg-slate-100/70";
                    return (
                      <div
                        key={truck.id}
                        onClick={() => handleTruckSelect(truck)}
                        style={{ animationDelay: `${index * 30}ms` }}
                        className={`group relative mb-2 last:mb-0 rounded-2xl border border-border/60 ${rowBg} backdrop-blur-md shadow-md transition-all duration-200 animate-in fade-in slide-in-from-left-3 cursor-pointer overflow-hidden
                          ${selectedTruck?.id === truck.id ? "ring-2 ring-primary/60 scale-[1.025] bg-gradient-to-r from-primary/10 to-white/60" : "hover:scale-[1.015] hover:shadow-lg"}`}
                      >
                        <div className="flex items-center gap-3 px-3 py-2">
                          <div className="relative flex-shrink-0">
                            <div className={`h-9 w-9 rounded-xl flex items-center justify-center bg-gradient-to-br ${truck.truckType === "primary" ? "from-primary/10 to-primary/30" : "from-secondary/10 to-secondary/30"} shadow-sm`}>
                              <Truck className={`h-5 w-5 ${truck.truckType === "primary" ? "text-primary" : "text-secondary"}`} />
                            </div>
                            <span className={`absolute -bottom-1 -right-1 h-3 w-3 rounded-full border-2 border-background ${statusConfig[truck.status].bgClass}`} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-sm truncate text-foreground drop-shadow-sm">
                                {truck.truckNumber}
                              </span>
                              <Badge variant="outline" className="text-[9px] px-1 rounded-full border-2 border-primary/30 bg-primary/5 font-bold">
                                {truck.truckType === "primary" ? "P" : "S"}
                              </Badge>
                            </div>
                            <p className="text-[11px] text-muted-foreground truncate font-medium">{truck.driver}</p>
                            <div className="flex items-center gap-2 mt-1">
                              <Badge className={`text-[9px] px-1 rounded-full ${statusConfig[truck.status].bgClass} font-semibold`}>
                                {statusConfig[truck.status].label}
                              </Badge>
                              <span className="text-[9px] text-muted-foreground font-semibold">{truck.speed} km/h</span>
                            </div>
                          </div>
                          <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
                        </div>
                        {/* Glow effect on select */}
                        {selectedTruck?.id === truck.id && (
                          <div className="absolute inset-0 pointer-events-none rounded-2xl border-2 border-primary/30 animate-pulse" style={{boxShadow: '0 0 32px 0 rgba(16,185,129,0.12)'}} />
                        )}
                      </div>
                    );
                  })}
                </ScrollArea>
              </CardContent>
            </Card>

            {/* Map */}
            <Card className="lg:col-span-3 overflow-hidden shadow-2xl border-muted/40 relative rounded-[2.5rem] border-2 border-primary/30 bg-white/90 backdrop-blur-xl">
              {/* Floating Legend */}
              <div className="absolute top-20 left-4 z-10 flex flex-col gap-2 max-w-[180px]">
                <Card className="backdrop-blur-xl bg-background/90 border-muted/40 shadow-lg">
                  <CardContent className="p-2">
                    <p className="text-[10px] font-semibold text-foreground mb-1.5">Status</p>
                    <div className="grid grid-cols-2 gap-x-2 gap-y-1">
                      <div className="flex items-center gap-1.5 text-[10px]">
                        <div className="h-2 w-2 rounded-full bg-success flex-shrink-0" />
                        <span className="text-muted-foreground truncate">Moving</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-[10px]">
                        <div className="h-2 w-2 rounded-full bg-warning flex-shrink-0" />
                        <span className="text-muted-foreground truncate">Idle</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-[10px]">
                        <div className="h-2 w-2 rounded-full bg-chart-1 flex-shrink-0" />
                        <span className="text-muted-foreground truncate">Dumping</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-[10px]">
                        <div className="h-2 w-2 rounded-full bg-destructive flex-shrink-0" />
                        <span className="text-muted-foreground truncate">Offline</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                {wardMatchLabel && (
                  <Card className="backdrop-blur-xl bg-primary/10 border-primary/20 shadow-lg">
                    <CardContent className="p-2">
                      <div className="flex items-center gap-1.5 text-[10px]">
                        <MapPin className="h-3 w-3 text-primary flex-shrink-0" />
                        <span className="font-medium text-primary line-clamp-2 break-words">{wardMatchLabel}</span>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>

              {/* Stats Overlay */}
              <div className="absolute bottom-4 left-4 z-10">
                <Card className="backdrop-blur-xl bg-background/80 border-muted/40 shadow-lg">
                  <CardContent className="p-3">
                    <div className="flex items-center gap-4 text-xs">
                      <div className="flex items-center gap-1.5">
                        <Activity className="h-3.5 w-3.5 text-success" />
                        <span className="font-semibold">{filteredTrucks.length}</span>
                        <span className="text-muted-foreground">visible</span>
                      </div>
                      <div className="h-4 w-px bg-border" />
                      <div className="flex items-center gap-1.5">
                        <Zap className="h-3.5 w-3.5 text-chart-1" />
                        <span className="font-semibold">{filteredTrucks.filter(t => t.status === 'moving').length}</span>
                        <span className="text-muted-foreground">moving</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="h-[560px]">
                <GoogleMap
                  mapContainerStyle={containerStyle}
                  center={KHARADI_CENTER}
                  zoom={14}
                  onLoad={onMapLoad}
                  options={{
                    styles: [{ featureType: "poi", elementType: "labels", stylers: [{ visibility: "off" }] }],
                    streetViewControl: false,
                    zoomControl: true,
                    fullscreenControl: true,
                  }}
                >
                    {/* Ward Boundary Polygons */}
                    {isMapLoaded && window.google && wardPolygons.map((path, index) => (
                      <Polygon
                        key={`ward-boundary-${index}`}
                        paths={path}
                        options={{
                          fillColor: "#60a5fa",
                          fillOpacity: 0.25,
                          strokeColor: "#2563eb",
                          strokeOpacity: 0.8,
                          strokeWeight: 3,
                          clickable: false,
                        }}
                      />
                    ))}
                
                    {/* GTP Markers */}
                    {isMapLoaded && window.google && gtpLocations.map((gtp) => (
                      <Marker
                        key={gtp.id}
                        position={gtp.position}
                        icon={{
                          url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(`
                            <svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                              <circle cx="12" cy="12" r="10" fill="#f59e0b" stroke="white" stroke-width="2"/>
                              <text x="12" y="16" text-anchor="middle" font-size="8" fill="white" font-weight="bold">GTP</text>
                            </svg>
                          `)}`,
                          scaledSize: new window.google.maps.Size(24, 24),
                        }}
                        title={gtp.name}
                      />
                    ))}

                    {/* Final Dumping Sites */}
                    {isMapLoaded && window.google && finalDumpingSites.map((site) => (
                      <Marker
                        key={site.id}
                        position={site.position}
                        icon={{
                          url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(`
                            <svg width="28" height="28" viewBox="0 0 28 28" xmlns="http://www.w3.org/2000/svg">
                              <rect x="2" y="2" width="24" height="24" rx="4" fill="#ef4444" stroke="white" stroke-width="2"/>
                              <text x="14" y="18" text-anchor="middle" font-size="10" fill="white" font-weight="bold">FD</text>
                            </svg>
                          `)}`,
                          scaledSize: new window.google.maps.Size(28, 28),
                        }}
                        title={site.name}
                      />
                    ))}

                    {/* Truck Markers */}
                    {isMapLoaded && window.google && filteredTrucks.map((truck) => (
                      <Marker
                        key={truck.id}
                        position={truck.position}
                        onClick={() => setSelectedMarker(truck.id)}
                        icon={{
                          url: createTruckMarkerIcon(truck.status, truck.truckType, truck.bearing || 0, truck.speed || 0),
                          scaledSize: new window.google.maps.Size(56, 48),
                          anchor: new window.google.maps.Point(28, 40),
                        }}
                      >
                        {selectedMarker === truck.id && (
                          <InfoWindow onCloseClick={() => setSelectedMarker(null)}>
                            <div className="p-2 min-w-[220px]">
                              <h3 className="font-bold text-gray-900">{truck.truckNumber}</h3>
                              <p className="text-sm text-gray-600 capitalize">{truck.truckType} Truck</p>
                              <div className="mt-2 space-y-1 text-sm">
                                <p><span className="font-medium">Driver:</span> {truck.driver}</p>
                                <p><span className="font-medium">Route:</span> {truck.route}</p>
                                <p><span className="font-medium">Speed:</span> {truck.speed} km/h</p>
                                <p><span className="font-medium">Trips:</span> {truck.tripsCompleted}/{truck.tripsAllowed}</p>
                                {truck.assignedGTP && <p><span className="font-medium">GTP:</span> {truck.assignedGTP}</p>}
                                <p className="text-xs text-blue-600">Live stream update</p>
                              </div>
                            </div>
                          </InfoWindow>
                        )}
                      </Marker>
                    ))}

                </GoogleMap>
              </div>
            </Card>
          </div>

          {/* Selected Truck Details */}
          {currentSelectedTruck && (
            <Card className="animate-in fade-in slide-in-from-bottom-4 duration-300 shadow-lg border-muted/40">
              <CardHeader className="pb-3 bg-gradient-to-r from-muted/30 to-transparent">
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center ring-4 ring-primary/10">
                      <Truck className="h-5 w-5 text-primary" />
                    </div>
                    <div className="flex flex-col">
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-bold">{currentSelectedTruck.truckNumber}</span>
                        <Badge variant="outline" className="capitalize">{currentSelectedTruck.truckType}</Badge>
                        <Badge className={`${statusConfig[currentSelectedTruck.status].bgClass}`}>
                          {statusConfig[currentSelectedTruck.status].label}
                        </Badge>
                      </div>
                      <span className="text-sm font-normal text-muted-foreground flex items-center gap-1.5">
                        <Gauge className="h-3 w-3" />
                        {currentSelectedTruck.speed} km/h
                      </span>
                    </div>
                  </CardTitle>
                  <div className="text-xs text-muted-foreground">Live route replay is disabled for production stream mode.</div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-4 gap-4">
                  <Card className="border-l-4 border-l-primary/50 shadow-sm animate-in fade-in slide-in-from-bottom-2 duration-300">
                    <CardContent className="p-4 space-y-2">
                      <p className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                        <Users className="h-3 w-3" />
                        Driver
                      </p>
                      <p className="font-semibold text-foreground">{currentSelectedTruck.driver}</p>
                      <p className="text-xs text-muted-foreground">{currentSelectedTruck.driverId}</p>
                    </CardContent>
                  </Card>
                  
                  <Card className="border-l-4 border-l-chart-2/50 shadow-sm animate-in fade-in slide-in-from-bottom-2 duration-300 delay-75">
                    <CardContent className="p-4 space-y-2">
                      <p className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                        <Navigation2 className="h-3 w-3" />
                        Route
                      </p>
                      <p className="font-semibold text-foreground">{currentSelectedTruck.route}</p>
                      <p className="text-xs text-muted-foreground">Capacity: {currentSelectedTruck.vehicleCapacity}</p>
                    </CardContent>
                  </Card>
                  
                  <Card className="border-l-4 border-l-success/50 shadow-sm animate-in fade-in slide-in-from-bottom-2 duration-300 delay-150">
                    <CardContent className="p-4 space-y-2">
                      <p className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                        <TrendingUp className="h-3 w-3" />
                        Trips Today
                      </p>
                      <p className="font-semibold text-foreground">{currentSelectedTruck.tripsCompleted} / {currentSelectedTruck.tripsAllowed}</p>
                      <div className="relative h-2 bg-muted rounded-full overflow-hidden">
                        <div 
                          className="absolute inset-0 bg-gradient-to-r from-success to-success/80 rounded-full transition-all duration-500"
                          style={{ width: `${(currentSelectedTruck.tripsCompleted / currentSelectedTruck.tripsAllowed) * 100}%` }}
                        />
                      </div>
                    </CardContent>
                  </Card>
                  
                  <Card className="border-l-4 border-l-chart-1/50 shadow-sm animate-in fade-in slide-in-from-bottom-2 duration-300 delay-200">
                    <CardContent className="p-4 space-y-2">
                      <p className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                        <Signal className="h-3 w-3" />
                        GPS Device
                      </p>
                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-1">
                          <Signal className={`h-4 w-4 ${currentSelectedTruck.gpsDevice.status === "online" ? "text-success" : "text-destructive"}`} />
                          <span className="text-sm font-medium">{currentSelectedTruck.gpsDevice.signalStrength}%</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Battery className={`h-4 w-4 ${currentSelectedTruck.gpsDevice.batteryLevel > 20 ? "text-success" : "text-destructive"}`} />
                          <span className="text-sm font-medium">{currentSelectedTruck.gpsDevice.batteryLevel}%</span>
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground">IMEI: {currentSelectedTruck.gpsDevice.imei}</p>
                    </CardContent>
                  </Card>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="list">
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="p-3 text-left text-sm font-medium">Truck</th>
                      <th className="p-3 text-left text-sm font-medium">Type</th>
                      <th className="p-3 text-left text-sm font-medium">Driver</th>
                      <th className="p-3 text-left text-sm font-medium">Route</th>
                      <th className="p-3 text-left text-sm font-medium">Status</th>
                      <th className="p-3 text-left text-sm font-medium">Trips</th>
                      <th className="p-3 text-left text-sm font-medium">GPS</th>
                      <th className="p-3 text-left text-sm font-medium">Last Update</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTrucks.map((truck) => (
                      <tr key={truck.id} className="border-b border-border hover:bg-muted/30">
                        <td className="p-3">
                          <div className="flex items-center gap-2">
                            <Truck className="h-4 w-4 text-primary" />
                            <span className="font-medium">{truck.truckNumber}</span>
                          </div>
                        </td>
                        <td className="p-3">
                          <Badge variant="outline" className="capitalize">{truck.truckType}</Badge>
                        </td>
                        <td className="p-3">{truck.driver}</td>
                        <td className="p-3">{truck.route}</td>
                        <td className="p-3">
                          <Badge className={statusConfig[truck.status].bgClass}>
                            {statusConfig[truck.status].label}
                          </Badge>
                        </td>
                        <td className="p-3">{truck.tripsCompleted}/{truck.tripsAllowed}</td>
                        <td className="p-3">
                          <div className="flex items-center gap-1">
                            <Signal className={`h-3 w-3 ${truck.gpsDevice.status === "online" ? "text-success" : truck.gpsDevice.status === "warning" ? "text-warning" : "text-destructive"}`} />
                            <span className="text-xs">{truck.gpsDevice.signalStrength}%</span>
                          </div>
                        </td>
                        <td className="p-3 text-sm text-muted-foreground">{truck.lastUpdate}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="devices" className="space-y-4">
          {/* Hero Fleet Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="relative overflow-hidden border-l-4 border-l-success animate-in fade-in slide-in-from-left-4 duration-500">
              <div className="absolute inset-0 bg-gradient-to-br from-success/5 to-transparent" />
              <CardContent className="relative p-5">
                <div className="flex items-start justify-between">
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                      <Activity className="h-3.5 w-3.5" />
                      Active Now
                    </p>
                    <p className="text-3xl font-bold tracking-tight">{onlineDevices.length}</p>
                    <div className="flex items-center gap-1.5 text-xs">
                      <TrendingUp className="h-3 w-3 text-success" />
                      <span className="text-success font-semibold">Live</span>
                      <span className="text-muted-foreground">fleet tracking</span>
                    </div>
                  </div>
                  <div className="h-12 w-12 rounded-xl bg-success/10 flex items-center justify-center ring-4 ring-success/10">
                    <Truck className="h-6 w-6 text-success" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="relative overflow-hidden border-l-4 border-l-chart-1 animate-in fade-in slide-in-from-left-4 duration-500 delay-75">
              <div className="absolute inset-0 bg-gradient-to-br from-chart-1/5 to-transparent" />
              <CardContent className="relative p-5">
                <div className="flex items-start justify-between">
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                      <Zap className="h-3.5 w-3.5" />
                      Moving
                    </p>
                    <p className="text-3xl font-bold tracking-tight">{filteredTrucks.filter(t => t.status === 'moving').length}</p>
                    <div className="flex items-center gap-1.5 text-xs">
                      <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-chart-1 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-chart-1"></span>
                      </span>
                      <span className="text-muted-foreground">in transit</span>
                    </div>
                  </div>
                  <div className="h-12 w-12 rounded-xl bg-chart-1/10 flex items-center justify-center ring-4 ring-chart-1/10">
                    <Navigation2 className="h-6 w-6 text-chart-1" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="relative overflow-hidden border-l-4 border-l-primary animate-in fade-in slide-in-from-left-4 duration-500 delay-150">
              <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent" />
              <CardContent className="relative p-5">
                <div className="flex items-start justify-between">
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                      <Gauge className="h-3.5 w-3.5" />
                      Avg Speed
                    </p>
                    <p className="text-3xl font-bold tracking-tight">
                      {Math.round(filteredTrucks.reduce((sum, t) => sum + (t.speed || 0), 0) / filteredTrucks.length || 0)}
                      <span className="text-lg text-muted-foreground ml-1">km/h</span>
                    </p>
                    <div className="flex items-center gap-1.5 text-xs">
                      <Signal className="h-3 w-3 text-primary" />
                      <span className="text-muted-foreground">fleet velocity</span>
                    </div>
                  </div>
                  <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center ring-4 ring-primary/10">
                    <Gauge className="h-6 w-6 text-primary" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="relative overflow-hidden border-l-4 border-l-warning animate-in fade-in slide-in-from-left-4 duration-500 delay-200">
              <div className="absolute inset-0 bg-gradient-to-br from-warning/5 to-transparent" />
              <CardContent className="relative p-5">
                <div className="flex items-start justify-between">
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5" />
                      Idle Vehicles
                    </p>
                    <p className="text-3xl font-bold tracking-tight">{warningDevices.length}</p>
                    <div className="flex items-center gap-1.5 text-xs">
                      <AlertTriangle className="h-3 w-3 text-warning" />
                      <span className="text-muted-foreground">requires attention</span>
                    </div>
                  </div>
                  <div className="h-12 w-12 rounded-xl bg-warning/10 flex items-center justify-center ring-4 ring-warning/10">
                    <AlertTriangle className="h-6 w-6 text-warning" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Signal className="h-5 w-5" />
                GPS Device Status Report
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="p-3 text-left text-sm font-medium">IMEI</th>
                      <th className="p-3 text-left text-sm font-medium">Truck</th>
                      <th className="p-3 text-left text-sm font-medium">Status</th>
                      <th className="p-3 text-left text-sm font-medium">Signal</th>
                      <th className="p-3 text-left text-sm font-medium">Battery</th>
                      <th className="p-3 text-left text-sm font-medium">Last Ping</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTrucks.map((truck) => (
                      <tr key={truck.id} className={`border-b border-border ${truck.gpsDevice.status === "offline" ? "bg-destructive/5" : truck.gpsDevice.status === "warning" ? "bg-warning/5" : ""}`}>
                        <td className="p-3 font-mono text-sm">{truck.gpsDevice.imei}</td>
                        <td className="p-3">{truck.truckNumber}</td>
                        <td className="p-3">
                          <Badge className={
                            truck.gpsDevice.status === "online" ? "bg-success" : 
                            truck.gpsDevice.status === "warning" ? "bg-warning" : "bg-destructive"
                          }>
                            {truck.gpsDevice.status}
                          </Badge>
                        </td>
                        <td className="p-3">
                          <div className="flex items-center gap-2">
                            <div className="w-16 h-2 bg-muted rounded-full overflow-hidden">
                              <div 
                                className={`h-full rounded-full ${truck.gpsDevice.signalStrength > 50 ? "bg-success" : truck.gpsDevice.signalStrength > 20 ? "bg-warning" : "bg-destructive"}`}
                                style={{ width: `${truck.gpsDevice.signalStrength}%` }}
                              />
                            </div>
                            <span className="text-sm">{truck.gpsDevice.signalStrength}%</span>
                          </div>
                        </td>
                        <td className="p-3">
                          <div className="flex items-center gap-2">
                            <Battery className={`h-4 w-4 ${truck.gpsDevice.batteryLevel > 20 ? "text-success" : "text-destructive"}`} />
                            <span className="text-sm">{truck.gpsDevice.batteryLevel}%</span>
                          </div>
                        </td>
                        <td className="p-3 text-sm text-muted-foreground">{truck.gpsDevice.lastPing}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

    </div>
  );
}
