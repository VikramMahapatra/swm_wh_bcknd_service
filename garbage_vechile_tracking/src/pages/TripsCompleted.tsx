import { useState, useMemo } from "react";
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
import { useCompletedTrips } from "@/hooks/useDataQueries";
import { PageHeader } from "@/components/PageHeader";
import { format } from "date-fns";

const ITEMS_PER_PAGE = 10;

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
  const today = format(new Date(), "yyyy-MM-dd");
  const [dateFrom, setDateFrom] = useState(today);
  const [dateTo, setDateTo] = useState(today);
  const { data: completedTripsPayload = { items: [] }, isLoading } = useCompletedTrips({
    date_from: dateFrom,
    date_to: dateTo,
  });
  const tripsData = useMemo(() => {
    const rows = Array.isArray(completedTripsPayload?.items) ? completedTripsPayload.items : [];
    return rows.map((trip: any) => ({
      id: trip.id,
      truck: trip.truck || "-",
      driver: trip.driver || "Unassigned",
      route: trip.route || "-",
      startTime: trip.startTime || "-",
      endTime: trip.endTime || "-",
      pickups: Number(trip.pickups || 0),
      status: trip.status || "completed",
      duration: trip.duration || "-",
      zone: trip.zone || "Unknown",
      ward: trip.ward || "Unknown",
      vendor: trip.vendor || "Unknown",
      routeType: trip.routeType || "Vehicle",
      gtcPoint: trip.gtcPoint || "-",
    }));
  }, [completedTripsPayload]);

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
          <Input type="date" className="md:w-[160px]" value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); setCurrentPage(1); }} />
          <Input type="date" className="md:w-[160px]" value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); setCurrentPage(1); }} />
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


