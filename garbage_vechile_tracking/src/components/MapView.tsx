import { useState, useCallback, useRef, useMemo, useEffect } from "react";
import { GoogleMap, Marker, InfoWindow } from "@react-google-maps/api";
import { Card } from "@/components/ui/card";
import { Navigation, Filter, X, Maximize2, Minimize2, AlertCircle, Loader2 } from "lucide-react";
import { KHARADI_CENTER } from "@/data/fleetData";
import { useLiveTrucks, useZones, useZoneWards, useVendors } from "@/hooks/useDataQueries";
import { createTruckMarkerIcon } from "./TruckIcon";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface MapViewProps {
  selectedTruck: string | null;
  allowFullscreen?: boolean;
}

const MapView = ({ selectedTruck: propSelectedTruck, allowFullscreen = false }: MapViewProps) => {
  const { data: liveTrucksData = [] } = useLiveTrucks();
  const { data: zonesData = [] } = useZones();
  const { data: wardsData = [] } = useZoneWards();
  const { data: vendorsData = [] } = useVendors();

  const [zones, setZones] = useState([]);
  const [wards, setWards] = useState([]);
  const [vendors, setVendors] = useState([]);
  const [liveTrucks, setLiveTrucks] = useState([]);

  useEffect(() => {
    setLiveTrucks(liveTrucksData);
  }, [liveTrucksData]);

  useEffect(() => {
    setZones(zonesData);
  }, [zonesData]);

  useEffect(() => {
    setWards(wardsData);
  }, [wardsData]);

  useEffect(() => {
    setVendors(vendorsData);
  }, [vendorsData]);

  // Transform fleet data for map display
  const trucks = useMemo(() => {
    return liveTrucks.map(t => ({
      id: t.id,
      position: t.position,
      status: t.status as "moving" | "idle" | "dumping" | "offline" | "breakdown",
      driver: t.driver,
      route: t.route,
      routeType: t.routeType as "primary" | "secondary",
      speed: t.speed,
      vendorId: t.vendorId,
      vehicleType: t.vehicleType || "compactor",
      zoneId: t.zoneId || "ZN003",
      wardId: t.wardId || "WD001",
    }));
  }, [liveTrucks]);

  const containerStyle = {
    width: '100%',
    height: '100%'
  };

  const [selectedMarker, setSelectedMarker] = useState<string | null>(null);
  const [isMapLoaded, setIsMapLoaded] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const mapRef = useRef<google.maps.Map | null>(null);
  
  // Filter states
  const [selectedZone, setSelectedZone] = useState<string>("all");
  const [selectedWard, setSelectedWard] = useState<string>("all");
  const [selectedVehicleType, setSelectedVehicleType] = useState<string>("all");
  const [selectedVendor, setSelectedVendor] = useState<string>("all");

  // Route types for filter
  const routeTypes = ["primary", "secondary"];

  // Filter wards based on selected zone
  const filteredWards = useMemo(() => {
    if (selectedZone === "all") return wards;
    return wards.filter(w => w.zoneId === selectedZone);
  }, [selectedZone, wards]);

  // Apply filters to trucks
  const filteredTrucks = useMemo(() => {
    return trucks.filter(truck => {
      if (selectedZone !== "all" && truck.zoneId !== selectedZone) return false;
      if (selectedWard !== "all" && truck.wardId !== selectedWard) return false;
      if (selectedVehicleType !== "all" && truck.routeType !== selectedVehicleType) return false;
      if (selectedVendor !== "all" && truck.vendorId !== selectedVendor) return false;
      return true;
    });
  }, [selectedZone, selectedWard, selectedVehicleType, selectedVendor]);

  // Calculate status counts from filtered trucks
  const statusCounts = useMemo(() => {
    return {
      moving: filteredTrucks.filter(t => t.status === "moving").length,
      idle: filteredTrucks.filter(t => t.status === "idle").length,
      dumping: filteredTrucks.filter(t => t.status === "dumping").length,
      offline: filteredTrucks.filter(t => t.status === "offline").length,
      total: filteredTrucks.length,
    };
  }, [filteredTrucks]);

  // Check if any filter is active
  const hasActiveFilters = selectedZone !== "all" || selectedWard !== "all" || 
                           selectedVehicleType !== "all" || selectedVendor !== "all";

  const clearAllFilters = () => {
    setSelectedZone("all");
    setSelectedWard("all");
    setSelectedVehicleType("all");
    setSelectedVendor("all");
  };

  const handleMapClick = useCallback(() => {
    setSelectedMarker(null);
  }, []);

  const onMapLoad = useCallback((map: google.maps.Map) => {
    mapRef.current = map;
    setIsMapLoaded(true);
  }, []);

  return (
    <Card className={`overflow-hidden flex flex-col transition-all duration-300 ${isFullscreen ? 'fixed inset-0 z-50 rounded-none h-screen' : 'h-full'}`}>
      {/* Header */}
      <div className="p-3 border-b border-border bg-muted/30">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Navigation className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold text-foreground">Live Fleet Map</h2>
          </div>
          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={clearAllFilters} className="h-7 text-xs">
              <X className="h-3 w-3 mr-1" />
              Clear Filters
            </Button>
          )}
          {allowFullscreen && (
            <Button variant="ghost" size="sm" onClick={() => setIsFullscreen(!isFullscreen)} className="h-7 text-xs">
              {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
            </Button>
          )}
        </div>

        {/* Filters Row */}
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="h-4 w-4 text-muted-foreground" />
          
          <Select value={selectedZone} onValueChange={(val) => { setSelectedZone(val); setSelectedWard("all"); }}>
            <SelectTrigger className="h-8 w-[130px] text-xs">
              <SelectValue placeholder="Zone" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Zones</SelectItem>
              {zones.filter(z => z.status === 'active').map(zone => (
                <SelectItem key={zone.id} value={zone.id}>{zone.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={selectedWard} onValueChange={setSelectedWard}>
            <SelectTrigger className="h-8 w-[130px] text-xs">
              <SelectValue placeholder="Ward" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Wards</SelectItem>
              {filteredWards.filter(w => w.status === 'active').map(ward => (
                <SelectItem key={ward.id} value={ward.id}>{ward.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={selectedVehicleType} onValueChange={setSelectedVehicleType}>
            <SelectTrigger className="h-8 w-[130px] text-xs">
              <SelectValue placeholder="Vehicle Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              {routeTypes.map(type => (
                <SelectItem key={type} value={type} className="capitalize">{type}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={selectedVendor} onValueChange={setSelectedVendor}>
            <SelectTrigger className="h-8 w-[130px] text-xs">
              <SelectValue placeholder="Vendor" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Vendors</SelectItem>
              {vendors.filter(v => v.status === 'active').map(vendor => (
                <SelectItem key={vendor.id} value={vendor.id}>{vendor.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Map Container */}
      <div className="flex-1 relative">
        <GoogleMap
          mapContainerStyle={containerStyle}
          center={KHARADI_CENTER}
          zoom={15}
          onClick={handleMapClick}
          onLoad={onMapLoad}
          options={{
            styles: [
              { featureType: "poi", elementType: "labels", stylers: [{ visibility: "off" }] }
            ],
            streetViewControl: false,
            mapTypeControl: true,
            zoomControl: true,
            zoomControlOptions: {
              position: google.maps.ControlPosition.TOP_RIGHT,
            },
            fullscreenControl: true,
            fullscreenControlOptions: {
              position: google.maps.ControlPosition.TOP_LEFT,
            },
          }}
        >
            {/* Truck Markers */}
            {isMapLoaded && filteredTrucks.map((truck) => (
              <Marker
                key={truck.id}
                position={truck.position}
                onClick={() => setSelectedMarker(truck.id)}
                icon={{
                  url: createTruckMarkerIcon(truck.status as any, truck.routeType as any, truck.bearing || 0, truck.speed || 0),
                  scaledSize: new google.maps.Size(56, 48),
                  anchor: new google.maps.Point(28, 40),
                }}
              >
                {selectedMarker === truck.id && (
                  <InfoWindow
                    position={truck.position}
                    onCloseClick={() => setSelectedMarker(null)}
                  >
                    <div className="p-2 min-w-[180px]">
                      <h3 className="font-bold text-gray-900 mb-2">{truck.id}</h3>
                      <div className="space-y-1 text-sm text-gray-700">
                        <p><span className="font-medium">Driver:</span> {truck.driver}</p>
                        <p><span className="font-medium">Route:</span> {truck.route}</p>
                        <p><span className="font-medium">Type:</span> {truck.routeType}</p>
                        <p><span className="font-medium">Vehicle:</span> <span className="capitalize">{truck.vehicleType.replace('-', ' ')}</span></p>
                        <p><span className="font-medium">Speed:</span> {truck.speed} km/h</p>
                        <p><span className="font-medium">Status:</span> 
                          <span className={`ml-1 capitalize ${truck.status === 'moving' ? 'text-green-600' : truck.status === 'idle' ? 'text-amber-600' : 'text-blue-600'}`}>
                            {truck.status}
                          </span>
                        </p>
                      </div>
                    </div>
                  </InfoWindow>
                )}
              </Marker>
            ))}
        </GoogleMap>

        {/* Status Overlay */}
        <div className="absolute top-3 right-3 bg-background/95 backdrop-blur-sm rounded-lg border border-border shadow-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-medium text-muted-foreground">Fleet Status</span>
            <Badge variant="outline" className="text-xs h-5">
              {statusCounts.total} trucks
            </Badge>
          </div>
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-1.5">
                <div className="h-2.5 w-2.5 rounded-full bg-success animate-pulse" />
                <span className="text-xs text-muted-foreground">Moving</span>
              </div>
              <span className="text-sm font-semibold text-success">{statusCounts.moving}</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-1.5">
                <div className="h-2.5 w-2.5 rounded-full bg-warning" />
                <span className="text-xs text-muted-foreground">Idle</span>
              </div>
              <span className="text-sm font-semibold text-warning">{statusCounts.idle}</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-1.5">
                <div className="h-2.5 w-2.5 rounded-full bg-chart-1" />
                <span className="text-xs text-muted-foreground">Dumping</span>
              </div>
              <span className="text-sm font-semibold text-chart-1">{statusCounts.dumping}</span>
            </div>
            {statusCounts.offline > 0 && (
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-1.5">
                  <div className="h-2.5 w-2.5 rounded-full bg-destructive" />
                  <span className="text-xs text-muted-foreground">Offline</span>
                </div>
                <span className="text-sm font-semibold text-destructive">{statusCounts.offline}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
};

export default MapView;
