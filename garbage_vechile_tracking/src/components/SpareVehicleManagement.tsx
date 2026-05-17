import { useState, useEffect, useMemo } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogHeader, 
  DialogTitle, 
  DialogFooter 
} from "@/components/ui/dialog";
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { 
  Truck, 
  AlertTriangle, 
  ArrowRightLeft, 
  CheckCircle, 
  XCircle,
  Wrench,
  Clock
} from "lucide-react";
import { TruckData, TruckStatus } from "@/data/fleetData";
import { Vendor, Zone, Ward } from "@/data/masterData";
import { apiService } from "@/services/api";
import { useDrivers, useRoutes, useTrucks, useVendors, useZones } from "@/hooks/useDataQueries";

interface SpareAssignment {
  breakdownTruckId: string;
  spareTruckId: string;
  routeId: string;
  assignedAt: string;
  reason: string;
}

export function SpareVehicleManagement() {
  const { toast } = useToast();
  
  // API Hooks
  const { data: vendorsData = [] } = useVendors();
  const { data: zonesData = [] } = useZones();
  const { data: trucksApiData = [] } = useTrucks();
  const { data: routesData = [] } = useRoutes();
  const { data: driversData = [] } = useDrivers();
  
  // State for API data
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [wards, setWards] = useState<Ward[]>([]);
  
  // Sync API data to state
  useEffect(() => {
    if (vendorsData.length === 0) return;
    const normalizedVendors = (vendorsData as any[]).map((vendor) => ({
      ...vendor,
      companyName: vendor.companyName ?? vendor.company_name ?? vendor.name,
    }));
    setVendors(normalizedVendors);
  }, [vendorsData]);

  useEffect(() => {
    if (zonesData.length === 0) return;
    const normalizedZones = (zonesData as any[]).map((zone) => ({
      ...zone,
      totalWards: zone.totalWards ?? zone.total_wards,
      supervisorName: zone.supervisorName ?? zone.supervisor_name,
      supervisorPhone: zone.supervisorPhone ?? zone.supervisor_phone,
    }));
    setZones(normalizedZones);
  }, [zonesData]);

  useEffect(() => {
    if (zonesData.length === 0) return;
    const loadAllWards = async () => {
      const wardBatches = await Promise.all(
        (zonesData as any[]).map((zone) => apiService.getZoneWards(zone.id))
      );
      const flattened = wardBatches.flat();
      const normalizedWards = flattened.map((ward: any) => ({
        ...ward,
        zoneId: ward.zoneId ?? ward.zone_id,
        totalPickupPoints: ward.totalPickupPoints ?? ward.total_pickup_points,
      }));
      const uniqueById = Array.from(
        new Map(normalizedWards.map((ward: any) => [ward.id, ward])).values()
      );
      setWards(uniqueById);
    };

    loadAllWards();
  }, [zonesData]);

  const [trucksData, setTrucksData] = useState<TruckData[]>([]);
  const [isAssignDialogOpen, setIsAssignDialogOpen] = useState(false);
  const [selectedBreakdownTruck, setSelectedBreakdownTruck] = useState<TruckData | null>(null);
  const [selectedSpareTruck, setSelectedSpareTruck] = useState<string>("");
  const [breakdownReason, setBreakdownReason] = useState("");
  const [spareAssignments, setSpareAssignments] = useState<SpareAssignment[]>([]);

  const normalizedTrucks = useMemo(() => {
    const routesById = new Map((routesData as any[]).map((route) => [route.id, route]));
    const driversById = new Map((driversData as any[]).map((driver) => [driver.id, driver]));

    return (trucksApiData as any[]).map((truck) => {
      const route = routesById.get(truck.assigned_route_id);
      const driver = driversById.get(truck.driver_id);
      const currentStatus = truck.current_status || truck.currentStatus || "idle";

      return {
        id: truck.id,
        truckNumber: truck.registration_number || truck.registrationNumber || truck.id,
        truckType: truck.route_type || truck.routeType || "primary",
        vehicleType: truck.type || "compactor",
        position: {
          lat: truck.latitude ?? 0,
          lng: truck.longitude ?? 0,
        },
        status: currentStatus,
        driver: driver?.name || "Unassigned",
        driverId: truck.driver_id || "-",
        route: route?.name || "Unassigned",
        routeId: truck.assigned_route_id || "",
        speed: truck.speed ?? 0,
        assignedGTP: undefined,
        assignedDumpingSite: undefined,
        tripsCompleted: truck.trips_completed ?? 0,
        tripsAllowed: truck.trips_allowed ?? 5,
        gpsDevice: {
          imei: truck.imei_number || "-",
          status: "offline",
          lastPing: "-",
          signalStrength: 0,
          batteryLevel: 0,
        },
        vehicleCapacity: truck.capacity ? `${truck.capacity} ${truck.capacity_unit || ""}`.trim() : "-",
        lastUpdate: truck.last_update || "-",
        vendorId: truck.vendor_id || "",
        zoneId: truck.zone_id || "",
        wardId: truck.ward_id || "",
        isSpare: truck.is_spare ?? false,
      } as TruckData;
    });
  }, [trucksApiData, routesData, driversData]);

  useEffect(() => {
    setTrucksData(normalizedTrucks);
  }, [normalizedTrucks]);
  
  // Filters for breakdown table
  const [brkZoneFilter, setBrkZoneFilter] = useState("all");
  const [brkWardFilter, setBrkWardFilter] = useState("all");
  const [brkVendorFilter, setBrkVendorFilter] = useState("all");
  const [brkRouteTypeFilter, setBrkRouteTypeFilter] = useState("all");

  const filteredWards = brkZoneFilter !== "all" 
    ? wards.filter(w => w.zoneId === brkZoneFilter) 
    : wards;

  // Get breakdown trucks
  const breakdownTrucks = trucksData.filter(t => t.status === "breakdown" && !t.replacedBySpareId);
  
  // Get available spare trucks (not currently replacing any truck)
  const availableSpares = trucksData.filter(t => t.isSpare && !t.replacingTruckId && t.status !== "offline");
  
  // Get active spare replacements
  const activeReplacements = trucksData.filter(t => t.isSpare && t.replacingTruckId);
  
  // Get all spare trucks
  const allSpareTrucks = trucksData.filter(t => t.isSpare);

  // Calculate vendor spare truck requirements
  const vendorSpareStatus = vendors.map(vendor => {
    const vendorTrucks = trucksData.filter(t => t.vendorId === vendor.id && !t.isSpare);
    const vendorSpares = trucksData.filter(t => t.vendorId === vendor.id && t.isSpare);
    const spareTruckPercentage = parseInt(localStorage.getItem('spareTruckPercentage') || '10');
    const requiredSpares = Math.ceil(vendorTrucks.length * (spareTruckPercentage / 100));
    const availableSpareCount = vendorSpares.filter(s => !s.replacingTruckId).length;
    
    return {
      vendor,
      totalTrucks: vendorTrucks.length,
      requiredSpares,
      totalSpares: vendorSpares.length,
      availableSpares: availableSpareCount,
      activeSpares: vendorSpares.filter(s => s.replacingTruckId).length,
      isCompliant: vendorSpares.length >= requiredSpares
    };
  });

  const handleMarkBreakdown = (truck: TruckData) => {
    setSelectedBreakdownTruck(truck);
    setIsAssignDialogOpen(true);
  };

  const handleAssignSpare = () => {
    if (!selectedBreakdownTruck || !selectedSpareTruck) return;

    const spareTruck = trucksData.find(t => t.id === selectedSpareTruck);
    if (!spareTruck) return;

    // Update truck states
    setTrucksData(prev => prev.map(truck => {
      if (truck.id === selectedBreakdownTruck.id) {
        return {
          ...truck,
          status: "breakdown" as TruckStatus,
          replacedBySpareId: selectedSpareTruck,
          breakdownTime: new Date().toISOString(),
          breakdownReason: breakdownReason
        };
      }
      if (truck.id === selectedSpareTruck) {
        return {
          ...truck,
          replacingTruckId: selectedBreakdownTruck.id,
          route: selectedBreakdownTruck.route,
          routeId: selectedBreakdownTruck.routeId,
          assignedGTP: selectedBreakdownTruck.assignedGTP,
          assignedDumpingSite: selectedBreakdownTruck.assignedDumpingSite,
          status: "moving" as TruckStatus
        };
      }
      return truck;
    }));

    // Record assignment
    setSpareAssignments(prev => [...prev, {
      breakdownTruckId: selectedBreakdownTruck.id,
      spareTruckId: selectedSpareTruck,
      routeId: selectedBreakdownTruck.routeId,
      assignedAt: new Date().toISOString(),
      reason: breakdownReason
    }]);

    toast({
      title: "Spare Truck Assigned",
      description: `${spareTruck.truckNumber} is now assigned to ${selectedBreakdownTruck.route}`,
    });

    // Reset dialog
    setIsAssignDialogOpen(false);
    setSelectedBreakdownTruck(null);
    setSelectedSpareTruck("");
    setBreakdownReason("");
  };

  const handleReleaseSpare = (spareTruck: TruckData) => {
    const originalTruck = trucksData.find(t => t.id === spareTruck.replacingTruckId);
    
    setTrucksData(prev => prev.map(truck => {
      if (truck.id === spareTruck.id) {
        return {
          ...truck,
          replacingTruckId: undefined,
          route: "Unassigned",
          routeId: "",
          assignedGTP: undefined,
          assignedDumpingSite: truck.truckType === "secondary" ? truck.assignedDumpingSite : undefined,
          status: "idle" as TruckStatus
        };
      }
      if (truck.id === spareTruck.replacingTruckId) {
        return {
          ...truck,
          status: "idle" as TruckStatus,
          replacedBySpareId: undefined,
          breakdownTime: undefined,
          breakdownReason: undefined
        };
      }
      return truck;
    }));

    toast({
      title: "Spare Truck Released",
      description: `${spareTruck.truckNumber} has been released back to spare pool`,
    });
  };

  const getCompatibleSpares = (breakdownTruck: TruckData | null) => {
    if (!breakdownTruck) return [];
    return availableSpares.filter(spare => spare.truckType === breakdownTruck.truckType);
  };

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="p-4 border-l-4 border-l-primary">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Total Spare Trucks</p>
              <p className="text-2xl font-bold text-foreground">{allSpareTrucks.length}</p>
            </div>
            <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
              <Truck className="h-6 w-6 text-primary" />
            </div>
          </div>
          <div className="mt-2 text-xs text-muted-foreground">Available in fleet</div>
        </Card>
        <Card className="p-4 border-l-4 border-l-success">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Available Spares</p>
              <p className="text-2xl font-bold text-success">{availableSpares.length}</p>
            </div>
            <div className="h-12 w-12 rounded-xl bg-success/10 flex items-center justify-center">
              <CheckCircle className="h-6 w-6 text-success" />
            </div>
          </div>
          <div className="mt-2 text-xs text-success/80">Ready for deployment</div>
        </Card>
        <Card className="p-4 border-l-4 border-l-warning">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Active Replacements</p>
              <p className="text-2xl font-bold text-warning">{activeReplacements.length}</p>
            </div>
            <div className="h-12 w-12 rounded-xl bg-warning/10 flex items-center justify-center">
              <ArrowRightLeft className="h-6 w-6 text-warning" />
            </div>
          </div>
          <div className="mt-2 text-xs text-warning/80">Currently on routes</div>
        </Card>
        <Card className="p-4 border-l-4 border-l-destructive">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Breakdown Trucks</p>
              <p className="text-2xl font-bold text-destructive">{breakdownTrucks.length}</p>
            </div>
            <div className="h-12 w-12 rounded-xl bg-destructive/10 flex items-center justify-center">
              <AlertTriangle className="h-6 w-6 text-destructive" />
            </div>
          </div>
          <div className="mt-2 text-xs text-destructive/80">Awaiting repair</div>
        </Card>
      </div>

      {/* Vendor Compliance */}
      <Card className="p-4">
        <CardHeader className="p-0 pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Truck className="h-5 w-5" />
            Vendor Spare Truck Compliance
          </CardTitle>
          <CardDescription>
            Each vendor must maintain {localStorage.getItem('spareTruckPercentage') || '10'}% of their fleet as spare trucks
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Vendor</TableHead>
                <TableHead>Total Trucks</TableHead>
                <TableHead>Required Spares</TableHead>
                <TableHead>Total Spares</TableHead>
                <TableHead>Available</TableHead>
                <TableHead>Active</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {vendorSpareStatus.map((item) => (
                <TableRow key={item.vendor.id}>
                  <TableCell className="font-medium">{item.vendor.companyName}</TableCell>
                  <TableCell>{item.totalTrucks}</TableCell>
                  <TableCell>{item.requiredSpares}</TableCell>
                  <TableCell>{item.totalSpares}</TableCell>
                  <TableCell>{item.availableSpares}</TableCell>
                  <TableCell>{item.activeSpares}</TableCell>
                  <TableCell>
                    {item.isCompliant ? (
                      <Badge className="bg-success/20 text-success border-success/30">
                        <CheckCircle className="h-3 w-3 mr-1" /> Compliant
                      </Badge>
                    ) : (
                      <Badge className="bg-destructive/20 text-destructive border-destructive/30">
                        <XCircle className="h-3 w-3 mr-1" /> Non-Compliant
                      </Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Active Truck List with Breakdown Option */}
      <Card className="p-4">
        <CardHeader className="p-0 pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Wrench className="h-5 w-5" />
            Mark Truck as Breakdown
          </CardTitle>
          <CardDescription>
            Select a truck to mark as breakdown and assign a spare
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {/* Filters */}
          <div className="grid gap-3 md:grid-cols-4 mb-4">
            <Select value={brkZoneFilter} onValueChange={(v) => { setBrkZoneFilter(v); setBrkWardFilter("all"); }}>
              <SelectTrigger><SelectValue placeholder="Zone" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Zones</SelectItem>
                {zones.map(z => <SelectItem key={z.id} value={z.id}>{z.name}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={brkWardFilter} onValueChange={setBrkWardFilter}>
              <SelectTrigger><SelectValue placeholder="Ward" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Wards</SelectItem>
                {filteredWards.map(w => <SelectItem key={w.id} value={w.id}>{w.name}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={brkVendorFilter} onValueChange={setBrkVendorFilter}>
              <SelectTrigger><SelectValue placeholder="Vendor" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Vendors</SelectItem>
                {vendors.map(v => <SelectItem key={v.id} value={v.id}>{v.companyName}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={brkRouteTypeFilter} onValueChange={setBrkRouteTypeFilter}>
              <SelectTrigger><SelectValue placeholder="Route Type" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="primary">Primary</SelectItem>
                <SelectItem value="secondary">Secondary</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Truck</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Zone</TableHead>
                <TableHead>Block</TableHead>
                <TableHead>Driver</TableHead>
                <TableHead>Route</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {trucksData
                .filter(t => !t.isSpare && t.status !== "breakdown")
                .filter(t => brkZoneFilter === "all" || t.zoneId === brkZoneFilter)
                .filter(t => brkWardFilter === "all" || t.wardId === brkWardFilter)
                .filter(t => brkVendorFilter === "all" || t.vendorId === brkVendorFilter)
                .filter(t => brkRouteTypeFilter === "all" || t.truckType === brkRouteTypeFilter)
                .slice(0, 20)
                .map((truck) => {
                  const zone = zones.find(z => z.id === truck.zoneId);
                  const ward = wards.find(w => w.id === truck.wardId);
                  return (
                    <TableRow key={truck.id}>
                      <TableCell className="font-medium">{truck.truckNumber}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="capitalize">{truck.truckType}</Badge>
                      </TableCell>
                      <TableCell>{zone?.name || "-"}</TableCell>
                      <TableCell>{ward?.name || "-"}</TableCell>
                      <TableCell>{truck.driver}</TableCell>
                      <TableCell>{truck.route}</TableCell>
                      <TableCell>
                        <Badge className={`capitalize ${
                          truck.status === "moving" ? "bg-success/20 text-success" :
                          truck.status === "idle" ? "bg-warning/20 text-warning" :
                          "bg-muted"
                        }`}>
                          {truck.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button 
                          variant="destructive" 
                          size="sm"
                          onClick={() => handleMarkBreakdown(truck)}
                        >
                          <AlertTriangle className="h-4 w-4 mr-1" />
                          Report Breakdown
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Active Spare Assignments */}
      {activeReplacements.length > 0 && (
        <Card className="p-4">
          <CardHeader className="p-0 pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <ArrowRightLeft className="h-5 w-5" />
              Active Spare Assignments
              <Badge variant="secondary">{activeReplacements.length}</Badge>
            </CardTitle>
            <CardDescription>
              Spare trucks currently replacing breakdown vehicles
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Spare Truck</TableHead>
                  <TableHead>Replacing</TableHead>
                  <TableHead>Route</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {activeReplacements.map((spare) => {
                  const originalTruck = trucksData.find(t => t.id === spare.replacingTruckId);
                  return (
                    <TableRow key={spare.id}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          <Badge className="bg-primary/20 text-primary border-primary/30">SPARE</Badge>
                          {spare.truckNumber}
                        </div>
                      </TableCell>
                      <TableCell>{originalTruck?.truckNumber || "Unknown"}</TableCell>
                      <TableCell>{spare.route}</TableCell>
                      <TableCell>
                        <Badge className="bg-success/20 text-success">Active</Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => handleReleaseSpare(spare)}
                        >
                          <CheckCircle className="h-4 w-4 mr-1" />
                          Release
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Assign Spare Dialog */}
      <Dialog open={isAssignDialogOpen} onOpenChange={setIsAssignDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              Report Breakdown & Assign Spare
            </DialogTitle>
            <DialogDescription>
              Mark truck as breakdown and assign an available spare truck to take over its route
            </DialogDescription>
          </DialogHeader>

          {selectedBreakdownTruck && (
            <div className="space-y-4 py-4">
              <div className="p-3 bg-muted rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{selectedBreakdownTruck.truckNumber}</p>
                    <p className="text-sm text-muted-foreground">{selectedBreakdownTruck.route}</p>
                  </div>
                  <Badge variant="destructive">Breakdown</Badge>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Breakdown Reason</Label>
                <Textarea
                  placeholder="Describe the breakdown issue..."
                  value={breakdownReason}
                  onChange={(e) => setBreakdownReason(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label>Assign Spare Truck</Label>
                <Select value={selectedSpareTruck} onValueChange={setSelectedSpareTruck}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a spare truck" />
                  </SelectTrigger>
                  <SelectContent>
                    {getCompatibleSpares(selectedBreakdownTruck).map((spare) => (
                      <SelectItem key={spare.id} value={spare.id}>
                        {spare.truckNumber} ({spare.truckType}) - {spare.driver}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {getCompatibleSpares(selectedBreakdownTruck).length === 0 && (
                  <p className="text-sm text-destructive">
                    No compatible spare trucks available for {selectedBreakdownTruck.truckType} type
                  </p>
                )}
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAssignDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleAssignSpare}
              disabled={!selectedSpareTruck}
            >
              <ArrowRightLeft className="h-4 w-4 mr-2" />
              Assign Spare
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}