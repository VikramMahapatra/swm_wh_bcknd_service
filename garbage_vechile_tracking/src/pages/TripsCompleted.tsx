import { useState, useMemo, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { ArrowLeft, Search, Download, CheckCircle2, Clock, MapPin, Truck, Target } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useZones, useZoneWards, useVendors, useRoutes, useLiveTrucks } from "@/hooks/useDataQueries";
import { PageHeader } from "@/components/PageHeader";

const ITEMS_PER_PAGE = 10;

const parseTimeToMinutes = (time: string) => {
  const [hours, minutes] = time.split(":").map(Number);
  if (!Number.isFinite(hours) || !Number.isFinite(minutes)) return null;
  return hours * 60 + minutes;
};

const formatDuration = (start: string, end: string) => {
  const startMinutes = parseTimeToMinutes(start);
  const endMinutes = parseTimeToMinutes(end);
  if (startMinutes === null || endMinutes === null) return "—";
  const normalizedEnd = endMinutes < startMinutes ? endMinutes + 24 * 60 : endMinutes;
  const totalMinutes = Math.max(0, normalizedEnd - startMinutes);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours > 0 && minutes > 0) return `${hours}h ${minutes}m`;
  if (hours > 0) return `${hours}h`;
  return `${minutes}m`;
};

const TripsCompleted = () => {
  // Export filtered trips as CSV
  const handleExport = () => {
    if (!filteredTrips.length) return;
    const headers = [
      "Trip ID",
      "Truck",
      "Driver",
      "Route",
      "Zone",
      "Block",
      "Type",
      "Start",
      "End",
      "Duration",
      "Pickups",
      "Status"
    ];
    const rows = filteredTrips.map(trip => [
      trip.id,
      trip.truck,
      trip.driver,
      trip.route,
      trip.zone,
      trip.ward,
      trip.routeType,
      trip.startTime,
      trip.endTime,
      trip.duration,
      trip.pickups,
      trip.status
    ]);
    const csvContent = [
      headers.join(","),
      ...rows.map(row => row.map(val => `"${String(val).replace(/"/g, '""')}"`).join(","))
    ].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `trips_completed_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const navigate = useNavigate();
  const { data: zonesData = [], isLoading: isLoadingZones } = useZones();
  const { data: wardsData = [], isLoading: isLoadingWards } = useZoneWards();
  const { data: vendorsData = [], isLoading: isLoadingVendors } = useVendors();
  const { data: routesData = [], isLoading: isLoadingRoutes } = useRoutes();
  const { data: trucksLiveData = [], isLoading: isLoadingTrucks } = useLiveTrucks();

  const zones = zonesData;
  const wards = wardsData;
  const vendors = vendorsData;
  const routes = routesData;
  const trucksLive = trucksLiveData;

  const isLoading = isLoadingZones || isLoadingWards || isLoadingVendors || isLoadingRoutes || isLoadingTrucks;

  const zoneById = useMemo(() => new Map(zones.map((zone) => [zone.id, zone.name])), [zones]);
  const wardById = useMemo(() => new Map(wards.map((ward) => [ward.id, ward.name])), [wards]);
  const vendorById = useMemo(() => new Map(vendors.map((vendor) => [vendor.id, vendor.companyName])), [vendors]);
  const routeById = useMemo(() => new Map(routes.map((route) => [route.id, route.name])), [routes]);
  const tripsData = useMemo(() => {
    if (isLoading) return [];
    return trucksLive.map((truck, index) => {
      const route = routeById.get(truck.routeId);
      const routePoints = route?.points || [];
      const startTime = routePoints[0]?.scheduledTime || "06:00";
      const endTimeCandidate = routePoints[routePoints.length - 1]?.scheduledTime || "09:00";
      const status = truck.status === "moving" || truck.status === "dumping" ? "in_progress" : "completed";
      const endTime = status === "completed" ? endTimeCandidate : "—";
      return {
        id: `TRP-${String(index + 1).padStart(3, "0")}`,
        truck: truck.truckNumber,
        driver: truck.driver,
        route: route?.name || truck.route,
        startTime,
        endTime,
        pickups: route?.totalPickupPoints || 0,
        status,
        duration: status === "completed" ? formatDuration(startTime, endTimeCandidate) : "—",
        zone: zoneById.get(truck.zoneId) || "Unknown",
        ward: wardById.get(truck.wardId) || "Unknown",
        vendor: vendorById.get(truck.vendorId) || "Unknown",
        routeType: truck.truckType,
      };
    });
  }, [zoneById, wardById, vendorById, routeById, trucksLive, isLoading]);

  const [searchQuery, setSearchQuery] = useState("");
  const [zoneFilter, setZoneFilter] = useState("all");
  const [wardFilter, setWardFilter] = useState("all");
  const [vendorFilter, setVendorFilter] = useState("all");
  const [routeTypeFilter, setRouteTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);

  const uniqueZones = useMemo(() => [...new Set(tripsData.map(d => d.zone))], [tripsData]);
  const uniqueWards = useMemo(() => [...new Set(tripsData.filter(d => zoneFilter === "all" || d.zone === zoneFilter).map(d => d.ward))], [tripsData, zoneFilter]);
  const uniqueVendors = useMemo(() => [...new Set(tripsData.map(d => d.vendor))], [tripsData]);

  const filteredTrips = useMemo(() => {
    return tripsData.filter(trip => {
      const matchesSearch = searchQuery === "" || 
        trip.truck.toLowerCase().includes(searchQuery.toLowerCase()) ||
        trip.driver.toLowerCase().includes(searchQuery.toLowerCase()) ||
        trip.route.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesZone = zoneFilter === "all" || trip.zone === zoneFilter;
      const matchesWard = wardFilter === "all" || trip.ward === wardFilter;
      const matchesVendor = vendorFilter === "all" || trip.vendor === vendorFilter;
      const matchesRouteType = routeTypeFilter === "all" || trip.routeType === routeTypeFilter;
      const matchesStatus = statusFilter === "all" || trip.status === statusFilter;
      return matchesSearch && matchesZone && matchesWard && matchesVendor && matchesRouteType && matchesStatus;
    });
  }, [searchQuery, zoneFilter, wardFilter, vendorFilter, routeTypeFilter, statusFilter, tripsData]);

  const totalPages = Math.ceil(filteredTrips.length / ITEMS_PER_PAGE);
  const paginatedTrips = filteredTrips.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  const completedCount = filteredTrips.filter(t => t.status === "completed").length;
  const inProgressCount = filteredTrips.filter(t => t.status === "in_progress").length;
  const totalPickups = filteredTrips.filter(t => t.status === "completed").reduce((acc, t) => acc + t.pickups, 0);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return <Badge className="bg-success/10 text-success border-success/30">Completed</Badge>;
      case "in_progress":
        return <Badge className="bg-chart-2/10 text-chart-2 border-chart-2/30">In Progress</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <span className="text-lg text-muted-foreground">Loading trips data...</span>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      <PageHeader
        category="Operations"
        title="Trips Completed"
        description="Today's trip completion status and performance metrics"
        icon={CheckCircle2}
        actions={
          <>
            <Button variant="ghost" size="icon" onClick={() => navigate("/")}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <Button variant="outline" onClick={handleExport}>
              <Download className="h-4 w-4 mr-2" />
              Export CSV
            </Button>
          </>
        }
      />
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <Card className="p-4 border-l-4 border-l-success">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-success/10 flex items-center justify-center">
              <CheckCircle2 className="h-5 w-5 text-success" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Completed</p>
              <p className="text-xl font-bold">{completedCount}</p>
            </div>
          </div>
        </Card>
        <Card className="p-4 border-l-4 border-l-chart-2">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-chart-2/10 flex items-center justify-center">
              <Clock className="h-5 w-5 text-chart-2" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">In Progress</p>
              <p className="text-xl font-bold">{inProgressCount}</p>
            </div>
          </div>
        </Card>
        <Card className="p-4 border-l-4 border-l-primary">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Target className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Daily Target</p>
              <p className="text-xl font-bold">180</p>
            </div>
          </div>
        </Card>
        <Card className="p-4 border-l-4 border-l-warning">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-warning/10 flex items-center justify-center">
              <MapPin className="h-5 w-5 text-warning" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Total Pickups</p>
              <p className="text-xl font-bold">{totalPickups}</p>
            </div>
          </div>
        </Card>
      </div>

      <Card className="p-4">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input placeholder="Search by truck, driver, or route..." className="pl-10" value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }} />
          </div>
          <Select value={zoneFilter} onValueChange={(v) => { setZoneFilter(v); setWardFilter("all"); setCurrentPage(1); }}>
            <SelectTrigger className="w-[160px]"><SelectValue placeholder="All Zones" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Zones</SelectItem>
              {uniqueZones.map(z => <SelectItem key={z} value={z}>{z}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={wardFilter} onValueChange={(v) => { setWardFilter(v); setCurrentPage(1); }}>
            <SelectTrigger className="w-[160px]"><SelectValue placeholder="All Wards" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Wards</SelectItem>
              {uniqueWards.map(w => <SelectItem key={w} value={w}>{w}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={vendorFilter} onValueChange={(v) => { setVendorFilter(v); setCurrentPage(1); }}>
            <SelectTrigger className="w-[180px]"><SelectValue placeholder="All Vendors" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Vendors</SelectItem>
              {uniqueVendors.map(v => <SelectItem key={v} value={v}>{v}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={routeTypeFilter} onValueChange={(v) => { setRouteTypeFilter(v); setCurrentPage(1); }}>
            <SelectTrigger className="w-[150px]"><SelectValue placeholder="All Types" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="primary">Primary</SelectItem>
              <SelectItem value="secondary">Secondary</SelectItem>
            </SelectContent>
          </Select>
          <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setCurrentPage(1); }}>
            <SelectTrigger className="w-[150px]"><SelectValue placeholder="All Status" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="in_progress">In Progress</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Card>

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Trip ID</TableHead>
              <TableHead>Truck</TableHead>
              <TableHead>Driver</TableHead>
              <TableHead>Route</TableHead>
              <TableHead>Zone</TableHead>
              <TableHead>Block</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Start</TableHead>
              <TableHead>End</TableHead>
              <TableHead>Duration</TableHead>
              <TableHead>Pickups</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {paginatedTrips.map((trip) => (
              <TableRow key={trip.id}>
                <TableCell className="font-medium">{trip.id}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Truck className="h-4 w-4 text-muted-foreground" />
                    {trip.truck}
                  </div>
                </TableCell>
                <TableCell>{trip.driver}</TableCell>
                <TableCell>{trip.route}</TableCell>
                <TableCell className="text-xs">{trip.zone}</TableCell>
                <TableCell className="text-xs">{trip.ward}</TableCell>
                <TableCell>
                  <Badge variant="outline" className="text-xs">{trip.routeType === "primary" ? "P" : "S"}</Badge>
                </TableCell>
                <TableCell>{trip.startTime}</TableCell>
                <TableCell>{trip.endTime}</TableCell>
                <TableCell>{trip.duration}</TableCell>
                <TableCell>{trip.pickups}</TableCell>
                <TableCell>{getStatusBadge(trip.status)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        {totalPages > 1 && (
          <div className="p-4 border-t">
            <Pagination>
              <PaginationContent>
                <PaginationItem>
                  <PaginationPrevious onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    className={currentPage === 1 ? "pointer-events-none opacity-50" : "cursor-pointer"} />
                </PaginationItem>
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                  <PaginationItem key={page}>
                    <PaginationLink onClick={() => setCurrentPage(page)} isActive={currentPage === page} className="cursor-pointer">
                      {page}
                    </PaginationLink>
                  </PaginationItem>
                ))}
                <PaginationItem>
                  <PaginationNext onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    className={currentPage === totalPages ? "pointer-events-none opacity-50" : "cursor-pointer"} />
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          </div>
        )}
      </Card>
    </div>
  );
};

export default TripsCompleted;