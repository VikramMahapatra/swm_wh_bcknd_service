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
import { ArrowLeft, Search, Download, TrendingUp, TrendingDown, MapPin, Target, CheckCircle2, XCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Progress } from "@/components/ui/progress";
import { PageHeader } from "@/components/PageHeader";

const ITEMS_PER_PAGE = 10;

const collectionData = [
  { id: "1", zone: "North Zone", ward: "Aundh", route: "Kharadi Route 1", vendor: "Mahesh Enterprises", routeType: "primary", totalPoints: 45, collected: 42, missed: 3, rate: 93, trend: "up" },
  { id: "2", zone: "East Zone", ward: "Viman Nagar", route: "Viman Nagar Route", vendor: "Mahesh Enterprises", routeType: "primary", totalPoints: 38, collected: 36, missed: 2, rate: 95, trend: "up" },
  { id: "3", zone: "East Zone", ward: "Kharadi", route: "Kharadi Route 2", vendor: "Mahesh Enterprises", routeType: "secondary", totalPoints: 52, collected: 44, missed: 8, rate: 85, trend: "down" },
  { id: "4", zone: "South Zone", ward: "Hadapsar", route: "Hadapsar Route", vendor: "Green Transport Co", routeType: "primary", totalPoints: 60, collected: 54, missed: 6, rate: 90, trend: "stable" },
  { id: "5", zone: "South Zone", ward: "Hadapsar", route: "Magarpatta Route", vendor: "Green Transport Co", routeType: "primary", totalPoints: 35, collected: 32, missed: 3, rate: 91, trend: "up" },
  { id: "6", zone: "North Zone", ward: "Baner", route: "Residential Route", vendor: "Green Transport Co", routeType: "primary", totalPoints: 48, collected: 40, missed: 8, rate: 83, trend: "down" },
  { id: "7", zone: "West Zone", ward: "Kothrud", route: "Hospital Waste Route", vendor: "City Waste Solutions", routeType: "secondary", totalPoints: 20, collected: 19, missed: 1, rate: 95, trend: "up" },
  { id: "8", zone: "Central Zone", ward: "Shivaji Nagar", route: "Commercial Route", vendor: "City Waste Solutions", routeType: "primary", totalPoints: 42, collected: 38, missed: 4, rate: 90, trend: "stable" },
  { id: "9", zone: "West Zone", ward: "Warje", route: "Industrial Route", vendor: "City Waste Solutions", routeType: "secondary", totalPoints: 25, collected: 22, missed: 3, rate: 88, trend: "down" },
  { id: "10", zone: "West Zone", ward: "Warje", route: "Warehouse Route", vendor: "Green Transport Co", routeType: "secondary", totalPoints: 18, collected: 17, missed: 1, rate: 94, trend: "up" },
  { id: "11", zone: "Central Zone", ward: "Deccan", route: "Market Route", vendor: "Mahesh Enterprises", routeType: "primary", totalPoints: 55, collected: 48, missed: 7, rate: 87, trend: "down" },
  { id: "12", zone: "East Zone", ward: "Wadgaon Sheri", route: "Outer Ring Route", vendor: "Mahesh Enterprises", routeType: "primary", totalPoints: 30, collected: 28, missed: 2, rate: 93, trend: "up" },
];

const CollectionRate = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [zoneFilter, setZoneFilter] = useState("all");
  const [wardFilter, setWardFilter] = useState("all");
  const [vendorFilter, setVendorFilter] = useState("all");
  const [routeTypeFilter, setRouteTypeFilter] = useState("all");
  const [performanceFilter, setPerformanceFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);

  const uniqueZones = [...new Set(collectionData.map(d => d.zone))];
  const uniqueWards = [...new Set(collectionData.filter(d => zoneFilter === "all" || d.zone === zoneFilter).map(d => d.ward))];
  const uniqueVendors = [...new Set(collectionData.map(d => d.vendor))];

  const filteredData = useMemo(() => {
    return collectionData.filter(item => {
      const matchesSearch = searchQuery === "" || 
        item.route.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.zone.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesZone = zoneFilter === "all" || item.zone === zoneFilter;
      const matchesWard = wardFilter === "all" || item.ward === wardFilter;
      const matchesVendor = vendorFilter === "all" || item.vendor === vendorFilter;
      const matchesRouteType = routeTypeFilter === "all" || item.routeType === routeTypeFilter;
      let matchesPerformance = true;
      if (performanceFilter === "excellent") matchesPerformance = item.rate >= 95;
      else if (performanceFilter === "good") matchesPerformance = item.rate >= 90 && item.rate < 95;
      else if (performanceFilter === "needs_improvement") matchesPerformance = item.rate < 90;
      return matchesSearch && matchesZone && matchesWard && matchesVendor && matchesRouteType && matchesPerformance;
    });
  }, [searchQuery, zoneFilter, wardFilter, vendorFilter, routeTypeFilter, performanceFilter]);

  const totalPages = Math.ceil(filteredData.length / ITEMS_PER_PAGE);
  const paginatedData = filteredData.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

  const overallRate = filteredData.length > 0 ? Math.round(filteredData.reduce((acc, d) => acc + d.rate, 0) / filteredData.length) : 0;
  const totalCollected = filteredData.reduce((acc, d) => acc + d.collected, 0);
  const totalPoints = filteredData.reduce((acc, d) => acc + d.totalPoints, 0);
  const totalMissed = filteredData.reduce((acc, d) => acc + d.missed, 0);

  const getRateBadge = (rate: number) => {
    if (rate >= 95) return <Badge className="bg-success/10 text-success border-success/30">Excellent</Badge>;
    if (rate >= 90) return <Badge className="bg-chart-2/10 text-chart-2 border-chart-2/30">Good</Badge>;
    if (rate >= 85) return <Badge className="bg-warning/10 text-warning border-warning/30">Fair</Badge>;
    return <Badge className="bg-destructive/10 text-destructive border-destructive/30">Poor</Badge>;
  };

  const getTrendIcon = (trend: string) => {
    if (trend === "up") return <TrendingUp className="h-4 w-4 text-success" />;
    if (trend === "down") return <TrendingDown className="h-4 w-4 text-destructive" />;
    return <span className="h-4 w-4 text-muted-foreground">—</span>;
  };

  const handleExport = () => {
    const csvContent = [
      ["Zone", "Block", "Route", "Vendor", "Type", "Total Points", "Collected", "Missed", "Rate (%)", "Trend"].join(","),
      ...filteredData.map(item => 
        [item.zone, item.ward, item.route, item.vendor, item.routeType, item.totalPoints, item.collected, item.missed, item.rate, item.trend].join(",")
      )
    ].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "collection_rate.csv";
    a.click();
  };

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      <PageHeader
        category="Operations"
        title="Collection Rate"
        description="Waste collection efficiency by zone and route with performance metrics"
        icon={Target}
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
        <Card className="p-4 border-l-4 border-l-primary">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center"><TrendingUp className="h-5 w-5 text-primary" /></div>
            <div><p className="text-sm text-muted-foreground">Overall Rate</p><p className="text-xl font-bold">{overallRate}%</p></div>
          </div>
        </Card>
        <Card className="p-4 border-l-4 border-l-success">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-success/10 flex items-center justify-center"><CheckCircle2 className="h-5 w-5 text-success" /></div>
            <div><p className="text-sm text-muted-foreground">Total Collected</p><p className="text-xl font-bold">{totalCollected}</p></div>
          </div>
        </Card>
        <Card className="p-4 border-l-4 border-l-chart-2">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-chart-2/10 flex items-center justify-center"><Target className="h-5 w-5 text-chart-2" /></div>
            <div><p className="text-sm text-muted-foreground">Total Points</p><p className="text-xl font-bold">{totalPoints}</p></div>
          </div>
        </Card>
        <Card className="p-4 border-l-4 border-l-destructive">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-destructive/10 flex items-center justify-center"><XCircle className="h-5 w-5 text-destructive" /></div>
            <div><p className="text-sm text-muted-foreground">Missed</p><p className="text-xl font-bold">{totalMissed}</p></div>
          </div>
        </Card>
      </div>

      <Card className="p-4">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input placeholder="Search by zone or route..." className="pl-10" value={searchQuery}
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
          <Select value={performanceFilter} onValueChange={(v) => { setPerformanceFilter(v); setCurrentPage(1); }}>
            <SelectTrigger className="w-[180px]"><SelectValue placeholder="All Performance" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Performance</SelectItem>
              <SelectItem value="excellent">Excellent (≥95%)</SelectItem>
              <SelectItem value="good">Good (90-94%)</SelectItem>
              <SelectItem value="needs_improvement">Needs Improvement (&lt;90%)</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Card>

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Zone</TableHead>
              <TableHead>Block</TableHead>
              <TableHead>Route</TableHead>
              <TableHead>Vendor</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Total Points</TableHead>
              <TableHead>Collected</TableHead>
              <TableHead>Missed</TableHead>
              <TableHead>Rate</TableHead>
              <TableHead>Progress</TableHead>
              <TableHead>Performance</TableHead>
              <TableHead>Trend</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {paginatedData.map((item) => (
              <TableRow key={item.id}>
                <TableCell className="text-xs">{item.zone}</TableCell>
                <TableCell className="text-xs">{item.ward}</TableCell>
                <TableCell className="font-medium">{item.route}</TableCell>
                <TableCell className="text-xs">{item.vendor}</TableCell>
                <TableCell><Badge variant="outline" className="text-xs">{item.routeType === "primary" ? "P" : "S"}</Badge></TableCell>
                <TableCell>{item.totalPoints}</TableCell>
                <TableCell className="text-success">{item.collected}</TableCell>
                <TableCell className="text-destructive">{item.missed}</TableCell>
                <TableCell className="font-semibold">{item.rate}%</TableCell>
                <TableCell className="min-w-[120px]"><Progress value={item.rate} className="h-2" /></TableCell>
                <TableCell>{getRateBadge(item.rate)}</TableCell>
                <TableCell>{getTrendIcon(item.trend)}</TableCell>
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
                    <PaginationLink onClick={() => setCurrentPage(page)} isActive={currentPage === page} className="cursor-pointer">{page}</PaginationLink>
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

export default CollectionRate;