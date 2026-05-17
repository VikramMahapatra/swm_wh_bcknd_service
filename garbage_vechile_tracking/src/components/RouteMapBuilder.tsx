import { useState, useCallback, useEffect, useMemo } from "react";
import { GoogleMap, Marker, Polyline, InfoWindow, Polygon } from "@react-google-maps/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  MapPin, Save, Trash2, X, Plus, GripVertical, 
  Navigation, Target, CircleDot, Building2, Clock, Loader2
} from "lucide-react";
import { toast } from "sonner";
import { KHARADI_CENTER, gtpLocations, finalDumpingSites, RoutePoint, RouteData, TruckType } from "@/data/fleetData";
import { useZones, useZoneWards } from "@/hooks/useDataQueries";

interface RouteMapBuilderProps {
  route?: RouteData | null;
  routeType: TruckType;
  onSave: (route: RouteData) => void;
  onCancel: () => void;
}

const containerStyle = {
  width: "100%",
  height: "100%",
};

export default function RouteMapBuilder({ route, routeType, onSave, onCancel }: RouteMapBuilderProps) {
  const [routeName, setRouteName] = useState(route?.name || "");
  const [zoneId, setZoneId] = useState(route?.zoneId || "");
  const [wardId, setWardId] = useState(route?.wardId || "");
  const [points, setPoints] = useState<RoutePoint[]>(route?.points || []);
  const [selectedPoint, setSelectedPoint] = useState<RoutePoint | null>(null);
  const [isAddingPoint, setIsAddingPoint] = useState(false);
  const [newPointName, setNewPointName] = useState("");
  const [newPointType, setNewPointType] = useState<"pickup" | "gtp" | "dumping">("pickup");
  const [newPointTime, setNewPointTime] = useState("07:00");
  const [tempMarker, setTempMarker] = useState<{ lat: number; lng: number } | null>(null);
  const [wardPolygons, setWardPolygons] = useState<Array<Array<{ lat: number; lng: number }>>>([]);
  const [wardMatchLabel, setWardMatchLabel] = useState<string | null>(null);
  const [mapInstance, setMapInstance] = useState<google.maps.Map | null>(null);

  // Fetch zones and wards from API
  const { data: zonesData = [], isLoading: isLoadingZones } = useZones();
  const { data: wardsData = [], isLoading: isLoadingWards } = useZoneWards(zoneId);

  // Set default zone if not set and zones are loaded
  useEffect(() => {
    if (!zoneId && zonesData.length > 0) {
      setZoneId(zonesData[0].id);
    }
  }, [zonesData, zoneId]);

  // Filter wards for selected zone
  const wardsForZone = useMemo(() => wardsData, [wardsData]);

  // Set default ward if not set
  useEffect(() => {
    if (!wardId && wardsForZone.length > 0) {
      setWardId(wardsForZone[0].id);
    }
  }, [wardId, wardsForZone]);

  useEffect(() => {
    const selectedWard = wardsForZone.find((ward) => ward.id === wardId);
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

        setWardPolygons(polygons);
      } catch {
        setWardPolygons([]);
        setWardMatchLabel(null);
      }
    };

    loadWardBoundary();
  }, [wardId]);

  useEffect(() => {
    if (!mapInstance || wardPolygons.length === 0 || !window.google?.maps) return;
    const bounds = new window.google.maps.LatLngBounds();
    wardPolygons.forEach((path) => path.forEach((point) => bounds.extend(point)));
    if (!bounds.isEmpty()) {
      mapInstance.fitBounds(bounds);
    }
  }, [mapInstance, wardPolygons]);

  // Get point type color
  const getPointColor = (type: string) => {
    switch (type) {
      case "pickup": return "#22c55e";
      case "gtp": return "#f59e0b";
      case "dumping": return "#ef4444";
      default: return "#6b7280";
    }
  };

  // Get point icon
  const getPointIcon = (type: string, order: number) => {
    const color = getPointColor(type);
    return {
      path: window.google?.maps?.SymbolPath?.CIRCLE || 0,
      fillColor: color,
      fillOpacity: 1,
      strokeColor: "#ffffff",
      strokeWeight: 3,
      scale: 12,
    };
  };

  const isPointInPolygon = (point: { lat: number; lng: number }, polygon: Array<{ lat: number; lng: number }>) => {
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      const xi = polygon[i].lng;
      const yi = polygon[i].lat;
      const xj = polygon[j].lng;
      const yj = polygon[j].lat;
      const intersects = (yi > point.lat) !== (yj > point.lat)
        && point.lng < ((xj - xi) * (point.lat - yi)) / (yj - yi + 0.0) + xi;
      if (intersects) inside = !inside;
    }
    return inside;
  };

  const isPointInWard = (point: { lat: number; lng: number }) => {
    if (wardPolygons.length === 0) return true;
    return wardPolygons.some((polygon) => isPointInPolygon(point, polygon));
  };

  // Handle map click
  const handleMapClick = useCallback((e: google.maps.MapMouseEvent) => {
    if (!isAddingPoint || !e.latLng) return;

    const candidate = {
      lat: e.latLng.lat(),
      lng: e.latLng.lng(),
    };

    if (!isPointInWard(candidate)) {
      toast.error("Pickup point must be inside the selected ward boundary");
      return;
    }

    setTempMarker(candidate);
  }, [isAddingPoint, wardPolygons]);

  // Add point from temp marker
  const confirmAddPoint = () => {
    if (!tempMarker || !newPointName.trim()) {
      toast.error("Please provide a name for the point");
      return;
    }

    const newPoint: RoutePoint = {
      id: `RP-${Date.now()}`,
      position: tempMarker,
      name: newPointName,
      type: newPointType,
      order: points.length + 1,
      scheduledTime: newPointTime,
    };

    setPoints([...points, newPoint]);
    setTempMarker(null);
    setNewPointName("");
    setNewPointTime("07:00");
    setIsAddingPoint(false);
    toast.success("Point added to route");
  };

  // Add GTP/Dumping site from existing locations
  const addExistingLocation = (location: { id: string; name: string; position: { lat: number; lng: number } }, type: "gtp" | "dumping") => {
    // Calculate suggested time based on previous point
    const suggestedTime = points.length > 0 
      ? calculateNextTime(points[points.length - 1].scheduledTime || "07:00", 30)
      : "07:00";

    const newPoint: RoutePoint = {
      id: `RP-${Date.now()}`,
      position: location.position,
      name: location.name,
      type,
      order: points.length + 1,
      scheduledTime: suggestedTime,
    };
    setPoints([...points, newPoint]);
    toast.success(`${location.name} added to route`);
  };

  // Calculate next time (add minutes to a time string)
  const calculateNextTime = (time: string, addMinutes: number): string => {
    const [hours, mins] = time.split(":").map(Number);
    const totalMins = hours * 60 + mins + addMinutes;
    const newHours = Math.floor(totalMins / 60) % 24;
    const newMins = totalMins % 60;
    return `${newHours.toString().padStart(2, "0")}:${newMins.toString().padStart(2, "0")}`;
  };

  // Update point time
  const updatePointTime = (pointId: string, time: string) => {
    setPoints(points.map(p => p.id === pointId ? { ...p, scheduledTime: time } : p));
  };

  // Remove point
  const removePoint = (pointId: string) => {
    const updatedPoints = points
      .filter(p => p.id !== pointId)
      .map((p, idx) => ({ ...p, order: idx + 1 }));
    setPoints(updatedPoints);
    setSelectedPoint(null);
    toast.success("Point removed");
  };

  // Move point up/down
  const movePoint = (index: number, direction: "up" | "down") => {
    if (
      (direction === "up" && index === 0) ||
      (direction === "down" && index === points.length - 1)
    ) return;

    const newPoints = [...points];
    const swapIndex = direction === "up" ? index - 1 : index + 1;
    [newPoints[index], newPoints[swapIndex]] = [newPoints[swapIndex], newPoints[index]];
    
    // Update order numbers
    const reordered = newPoints.map((p, idx) => ({ ...p, order: idx + 1 }));
    setPoints(reordered);
  };

  // Calculate route distance (simple estimation)
  const calculateDistance = () => {
    if (points.length < 2) return "0 km";
    let total = 0;
    for (let i = 0; i < points.length - 1; i++) {
      const p1 = points[i].position;
      const p2 = points[i + 1].position;
      const R = 6371; // Earth's radius in km
      const dLat = (p2.lat - p1.lat) * Math.PI / 180;
      const dLng = (p2.lng - p1.lng) * Math.PI / 180;
      const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(p1.lat * Math.PI / 180) * Math.cos(p2.lat * Math.PI / 180) *
                Math.sin(dLng/2) * Math.sin(dLng/2);
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
      total += R * c;
    }
    return `${total.toFixed(1)} km`;
  };

  // Estimate time
  const calculateTime = () => {
    const distance = parseFloat(calculateDistance());
    const avgSpeed = 20; // km/h for garbage trucks
    const stopTime = points.length * 5; // 5 min per stop
    const travelTime = (distance / avgSpeed) * 60;
    const totalMins = Math.round(travelTime + stopTime);
    const hours = Math.floor(totalMins / 60);
    const mins = totalMins % 60;
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  };

  // Validate route based on type
  const validateRoute = () => {
    if (!zoneId || !wardId) {
      toast.error("Please select a zone and ward");
      return false;
    }
    if (!routeName.trim()) {
      toast.error("Please provide a route name");
      return false;
    }
    if (points.length < 2) {
      toast.error("Route must have at least 2 points");
      return false;
    }

    if (routeType === "primary") {
      // Primary: should end with GTP and include only one GTP
      const lastPoint = points[points.length - 1];
      const gtpPoints = points.filter((point) => point.type === "gtp");
      if (gtpPoints.length !== 1 || lastPoint.type !== "gtp") {
        toast.error("Primary routes must end with exactly one GTP (Garbage Transfer Point)");
        return false;
      }
    } else {
      // Secondary: should start with GTP and end with dumping
      const firstPoint = points[0];
      const lastPoint = points[points.length - 1];
      if (firstPoint.type !== "gtp") {
        toast.error("Secondary routes must start with a GTP");
        return false;
      }
      if (lastPoint.type !== "dumping") {
        toast.error("Secondary routes must end with a Dumping Yard");
        return false;
      }
    }

    return true;
  };

  // Save route
  const handleSave = () => {
    if (!validateRoute()) return;

    const routeData: RouteData = {
      id: route?.id || `RT-${Date.now()}`,
      name: routeName,
      code: routeName.substring(0, 6).toUpperCase().replace(/\s/g, '-'),
      type: routeType,
      wardId: wardId || route?.wardId || 'WD006',
      zoneId: zoneId || route?.zoneId || 'ZN003',
      points,
      distance: calculateDistance(),
      estimatedDistance: parseInt(calculateDistance()) || 10,
      estimatedTime: parseInt(calculateTime()) || 60,
      totalPickupPoints: points.filter(p => p.type === 'pickup').length,
      status: "active",
      assignedTruck: route?.assignedTruck,
      assignedTruckId: route?.assignedTruckId,
    };

    onSave(routeData);
  };

  // Polyline path
  const polylinePath = points.map(p => p.position);

  return (
    <div className="h-[calc(100vh-200px)] flex gap-4">
      {/* Left Panel - Route Details */}
      <Card className="w-80 flex flex-col">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Navigation className="h-5 w-5" />
            {route ? "Edit Route" : "Create Route"}
          </CardTitle>
          <Badge variant="outline" className={routeType === "primary" ? "border-primary text-primary" : "border-secondary text-secondary"}>
            {routeType} route
          </Badge>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col gap-4 overflow-hidden">
          <div className="flex-1 min-h-0 overflow-auto pr-2">
            {/* Zone and Ward */}
            <div className="space-y-3">
              <div>
                <Label>Zone</Label>
                <Select value={zoneId} onValueChange={(value) => setZoneId(value)} disabled={isLoadingZones}>
                  <SelectTrigger>
                    <SelectValue placeholder={isLoadingZones ? "Loading zones..." : "Select zone"} />
                  </SelectTrigger>
                  <SelectContent>
                    {zonesData.map((zone) => (
                      <SelectItem key={zone.id} value={zone.id}>
                        {zone.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Ward</Label>
                <Select value={wardId} onValueChange={(value) => setWardId(value)} disabled={isLoadingWards || !zoneId}>
                  <SelectTrigger>
                    <SelectValue placeholder={isLoadingWards ? "Loading wards..." : "Select ward"} />
                  </SelectTrigger>
                  <SelectContent>
                    {wardsForZone.map((ward) => (
                      <SelectItem key={ward.id} value={ward.id}>
                        {ward.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {wardMatchLabel && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Boundary: {wardMatchLabel}
                  </p>
                )}
              </div>
            </div>

            {/* Route Name */}
            <div>
              <Label>Route Name</Label>
              <Input 
                value={routeName}
                onChange={(e) => setRouteName(e.target.value)}
                placeholder="e.g., Kharadi Primary Route 1"
              />
            </div>

            {/* Route Info */}
            <div className="grid grid-cols-2 gap-2 text-center">
              <div className="p-2 bg-muted rounded-lg">
                <p className="text-lg font-bold text-primary">{points.length}</p>
                <p className="text-xs text-muted-foreground">Points</p>
              </div>
              <div className="p-2 bg-muted rounded-lg">
                <p className="text-lg font-bold text-primary">{calculateDistance()}</p>
                <p className="text-xs text-muted-foreground">Distance</p>
              </div>
            </div>

            {/* Quick Add GTP/Dumping */}
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">Quick Add Location</Label>
              <div className="flex gap-2">
                <Select onValueChange={(v) => {
                  const gtp = gtpLocations.find(g => g.id === v);
                  if (gtp) addExistingLocation(gtp, "gtp");
                }}>
                  <SelectTrigger className="flex-1 h-8 text-xs">
                    <SelectValue placeholder="Add GTP" />
                  </SelectTrigger>
                  <SelectContent>
                    {gtpLocations.map(gtp => (
                      <SelectItem key={gtp.id} value={gtp.id}>{gtp.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select onValueChange={(v) => {
                  const site = finalDumpingSites.find(s => s.id === v);
                  if (site) addExistingLocation(site, "dumping");
                }}>
                  <SelectTrigger className="flex-1 h-8 text-xs">
                    <SelectValue placeholder="Add Dump" />
                  </SelectTrigger>
                  <SelectContent>
                    {finalDumpingSites.map(site => (
                      <SelectItem key={site.id} value={site.id}>{site.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Points List */}
            <div className="flex-1 overflow-auto">
              <div className="flex items-center justify-between mb-2">
                <Label className="text-xs text-muted-foreground">Route Points</Label>
                <Button 
                  size="sm" 
                  variant={isAddingPoint ? "secondary" : "outline"}
                  className="h-7 text-xs"
                  onClick={() => {
                    setIsAddingPoint(!isAddingPoint);
                    setTempMarker(null);
                  }}
                >
                  {isAddingPoint ? <X className="h-3 w-3 mr-1" /> : <Plus className="h-3 w-3 mr-1" />}
                  {isAddingPoint ? "Cancel" : "Add Pickup"}
                </Button>
              </div>
              
              {isAddingPoint && (
                <div className="p-3 mb-3 bg-primary/10 rounded-lg border border-primary/30">
                  <p className="text-xs text-muted-foreground mb-2">Click on map to place point</p>
                  <Input
                    value={newPointName}
                    onChange={(e) => setNewPointName(e.target.value)}
                    placeholder="Point name"
                    className="mb-2 h-8"
                  />
                  <Select value={newPointType} onValueChange={(v) => setNewPointType(v as any)}>
                    <SelectTrigger className="h-8 text-xs mb-2">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pickup">Pickup Point</SelectItem>
                      <SelectItem value="gtp">GTP</SelectItem>
                      <SelectItem value="dumping">Dumping Site</SelectItem>
                    </SelectContent>
                  </Select>
                  <div className="flex items-center gap-2 mb-2">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <Input
                      type="time"
                      value={newPointTime}
                      onChange={(e) => setNewPointTime(e.target.value)}
                      className="h-8 flex-1"
                    />
                  </div>
                  {tempMarker && (
                    <Button size="sm" className="w-full h-8" onClick={confirmAddPoint}>
                      Confirm Location
                    </Button>
                  )}
                </div>
              )}

              <div className="space-y-2">
                {points.map((point, index) => (
                  <div 
                    key={point.id}
                    className={`flex items-center gap-2 p-2 rounded-lg border transition-colors cursor-pointer
                      ${selectedPoint?.id === point.id ? "border-primary bg-primary/10" : "border-border hover:bg-muted"}`}
                    onClick={() => setSelectedPoint(point)}
                  >
                    <div className="flex flex-col gap-0.5">
                      <button 
                        className="text-muted-foreground hover:text-foreground disabled:opacity-30"
                        onClick={(e) => { e.stopPropagation(); movePoint(index, "up"); }}
                        disabled={index === 0}
                      >
                        ▲
                      </button>
                      <button 
                        className="text-muted-foreground hover:text-foreground disabled:opacity-30"
                        onClick={(e) => { e.stopPropagation(); movePoint(index, "down"); }}
                        disabled={index === points.length - 1}
                      >
                        ▼
                      </button>
                    </div>
                    <div 
                      className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0"
                      style={{ backgroundColor: getPointColor(point.type) }}
                    >
                      {point.order}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{point.name}</p>
                      <div className="flex items-center gap-2">
                        <p className="text-xs text-muted-foreground capitalize">{point.type}</p>
                        <span className="text-xs text-muted-foreground">•</span>
                        <div className="flex items-center gap-1">
                          <Clock className="h-3 w-3 text-primary" />
                          <input
                            type="time"
                            value={point.scheduledTime || "07:00"}
                            onChange={(e) => { e.stopPropagation(); updatePointTime(point.id, e.target.value); }}
                            onClick={(e) => e.stopPropagation()}
                            className="text-xs font-medium text-primary bg-transparent border-none p-0 w-14 focus:outline-none focus:ring-0"
                          />
                        </div>
                      </div>
                    </div>
                    <button 
                      className="text-muted-foreground hover:text-destructive shrink-0"
                      onClick={(e) => { e.stopPropagation(); removePoint(point.id); }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}

                {points.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground text-sm">
                    <MapPin className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>No points added yet</p>
                    <p className="text-xs mt-1">
                      {routeType === "primary" 
                        ? "Add pickup points, then a GTP as final point"
                        : "Start with GTP, add points, end with Dumping Yard"}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-2 border-t">
            <Button variant="outline" className="flex-1" onClick={onCancel}>
              Cancel
            </Button>
            <Button className="flex-1" onClick={handleSave}>
              <Save className="h-4 w-4 mr-1" />
              Save Route
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Right Panel - Map */}
      <Card className="flex-1">
        <CardContent className="p-0 h-full relative">
          {window.google?.maps ? (
            <GoogleMap
              mapContainerStyle={containerStyle}
              center={points.length > 0 ? points[0].position : KHARADI_CENTER}
              zoom={14}
              onClick={handleMapClick}
              onLoad={(map) => setMapInstance(map)}
              options={{
                streetViewControl: false,
                mapTypeControl: true,
                fullscreenControl: true,
                zoomControl: true,
                draggableCursor: isAddingPoint ? "crosshair" : undefined,
              }}
            >
              {wardPolygons.map((path, index) => (
                <Polygon
                  key={`ward-boundary-${index}`}
                  paths={path}
                  options={{
                    fillColor: "#60a5fa",
                    fillOpacity: 0.15,
                    strokeColor: "#2563eb",
                    strokeOpacity: 0.6,
                    strokeWeight: 2,
                    clickable: false,
                  }}
                />
              ))}
              {/* Existing GTPs */}
              {gtpLocations.map(gtp => (
                <Marker
                  key={gtp.id}
                  position={gtp.position}
                  icon={{
                    path: window.google?.maps?.SymbolPath?.BACKWARD_CLOSED_ARROW || 0,
                    fillColor: "#f59e0b",
                    fillOpacity: 0.6,
                    strokeColor: "#ffffff",
                    strokeWeight: 2,
                    scale: 5,
                  }}
                  title={gtp.name}
                />
              ))}

              {/* Existing Dumping Sites */}
              {finalDumpingSites.map(site => (
                <Marker
                  key={site.id}
                  position={site.position}
                  icon={{
                    path: window.google?.maps?.SymbolPath?.BACKWARD_CLOSED_ARROW || 0,
                    fillColor: "#ef4444",
                    fillOpacity: 0.6,
                    strokeColor: "#ffffff",
                    strokeWeight: 2,
                    scale: 5,
                  }}
                  title={site.name}
                />
              ))}

              {/* Route Points */}
              {points.map((point) => (
                <Marker
                  key={point.id}
                  position={point.position}
                  icon={getPointIcon(point.type, point.order)}
                  label={{
                    text: String(point.order),
                    color: "#ffffff",
                    fontSize: "11px",
                    fontWeight: "bold",
                  }}
                  onClick={() => setSelectedPoint(point)}
                />
              ))}

              {/* Temp Marker */}
              {tempMarker && (
                <Marker
                  position={tempMarker}
                  icon={{
                    path: window.google?.maps?.SymbolPath?.CIRCLE || 0,
                    fillColor: "#3b82f6",
                    fillOpacity: 0.8,
                    strokeColor: "#ffffff",
                    strokeWeight: 3,
                    scale: 14,
                  }}
                  animation={window.google?.maps?.Animation?.BOUNCE}
                />
              )}

              {/* Route Polyline */}
              {points.length > 1 && (
                <Polyline
                  path={polylinePath}
                  options={{
                    strokeColor: routeType === "primary" ? "#22c55e" : "#3b82f6",
                    strokeOpacity: 0.8,
                    strokeWeight: 4,
                    icons: [{
                      icon: {
                        path: window.google?.maps?.SymbolPath?.FORWARD_CLOSED_ARROW || 0,
                        scale: 3,
                        strokeColor: routeType === "primary" ? "#16a34a" : "#2563eb",
                      },
                      offset: "50%",
                    }],
                  }}
                />
              )}

              {/* Info Window for selected point */}
              {selectedPoint && (
                <InfoWindow
                  position={selectedPoint.position}
                  onCloseClick={() => setSelectedPoint(null)}
                >
                  <div className="p-1">
                    <h4 className="font-semibold">{selectedPoint.name}</h4>
                    <p className="text-xs text-gray-600 capitalize">
                      {selectedPoint.type} Point #{selectedPoint.order}
                    </p>
                    {selectedPoint.scheduledTime && (
                      <p className="text-xs text-blue-600 font-medium mt-1">
                        ⏰ Scheduled: {selectedPoint.scheduledTime}
                      </p>
                    )}
                    <p className="text-xs text-gray-500 mt-1">
                      {selectedPoint.position.lat.toFixed(6)}, {selectedPoint.position.lng.toFixed(6)}
                    </p>
                  </div>
                </InfoWindow>
              )}
            </GoogleMap>
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full mx-auto mb-2" />
                <p className="text-muted-foreground">Loading map...</p>
              </div>
            </div>
          )}

          {/* Map Legend */}
          <div className="absolute bottom-4 left-4 bg-background/95 backdrop-blur-sm rounded-lg p-3 shadow-lg border">
            <p className="text-xs font-semibold mb-2">Legend</p>
            <div className="space-y-1 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-green-500" />
                <span>Pickup Point</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-amber-500" />
                  <span>GTP (Transfer Point)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <span>Dumping Site</span>
              </div>
            </div>
          </div>

          {/* Add Point Instructions */}
          {isAddingPoint && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-primary text-primary-foreground px-4 py-2 rounded-full shadow-lg animate-pulse">
              Click on map to place pickup point
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
