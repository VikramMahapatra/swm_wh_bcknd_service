import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Progress } from "@/components/ui/progress";
import { PageHeader } from "@/components/PageHeader";
import { 
  Download, 
  FileText, 
  Truck, 
  MapPin, 
  Users, 
  Fuel, 
  AlertTriangle, 
  Scale,
  Calendar,
  Filter,
  FileSpreadsheet,
  Printer,
  TrendingUp,
  TrendingDown,
  Clock,
  Route,
  Trash2,
  Building,
  Shield,
  IdCard,
  Gauge,
  XCircle,
  WifiOff,
  Zap,
  ArrowRightLeft,
  Wrench,
  Mail,
  Send
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import { useTrucks, useDrivers, useReportsData } from "@/hooks/useDataQueries";
import { differenceInDays, parseISO, format } from "date-fns";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from "recharts";

// Reports data is loaded from the backend.

const ITEMS_PER_PAGE = 5;

const getDateValue = (value: unknown): string | undefined =>
  typeof value === "string" && value.trim() ? value : undefined;

const safeParseISO = (value?: string) => (value ? parseISO(value) : null);

const getTruckInsuranceDate = (truck: any) =>
  getDateValue(truck.insuranceExpiry ?? truck.insurance_expiry);

const getTruckFitnessDate = (truck: any) =>
  getDateValue(truck.fitnessExpiry ?? truck.fitness_expiry);

const getDriverLicenseDate = (driver: any) =>
  getDateValue(driver.licenseExpiry ?? driver.license_expiry);

export default function Reports() {
  const [searchParams] = useSearchParams();
  const initialTab = searchParams.get("tab") || "daily";
  const { toast } = useToast();
  
  // API Hooks
  const { data: trucksData = [] } = useTrucks();
  const { data: driversData = [] } = useDrivers();
  const { data: reportsData = {}, isLoading: isLoadingReports } = useReportsData();
  
  // State for API data
  const [trucks, setTrucks] = useState<any[]>([]);
  const [drivers, setDrivers] = useState<any[]>([]);
  
  // Sync API data to state
  useEffect(() => {
    setTrucks(trucksData);
  }, [trucksData]);
  
  useEffect(() => {
    setDrivers(driversData);
  }, [driversData]);
  
  const today = format(new Date(), "yyyy-MM-dd");
  const [activeTab, setActiveTab] = useState(initialTab);
  const [dateFrom, setDateFrom] = useState(today);
  const [dateTo, setDateTo] = useState(today);
  const [selectedZone, setSelectedZone] = useState("all");
  const [selectedWard, setSelectedWard] = useState("all");
  const [selectedTruck, setSelectedTruck] = useState("all");

  const dailyPickupCoverageData: any[] = (reportsData as any).daily_pickup_coverage || [];
  const routePerformanceData: any[] = (reportsData as any).route_performance || [];
  const truckUtilizationData: any[] = (reportsData as any).truck_utilization || [];
  const fuelConsumptionData: any[] = (reportsData as any).fuel_consumption || [];
  const driverAttendanceData: any[] = (reportsData as any).driver_attendance || [];
  const complaintsData: any[] = (reportsData as any).complaints || [];
  const dumpYardData: any[] = (reportsData as any).dump_yard || [];
  const weeklyTrendData: any[] = (reportsData as any).weekly_trend || [];
  const zoneWiseData: any[] = (reportsData as any).zone_wise || [];
  const lateArrivalData: any[] = (reportsData as any).late_arrival || [];
  const driverBehaviorData: any[] = (reportsData as any).driver_behavior || [];
  const vehicleStatusData: any[] = (reportsData as any).vehicle_status || [];
  const spareUsageData: any[] = (reportsData as any).spare_usage || [];
  
  // Email export dialog state
  const [emailDialogOpen, setEmailDialogOpen] = useState(false);
  const [emailAddress, setEmailAddress] = useState("");
  const [emailReportType, setEmailReportType] = useState("");
  const [sendingEmail, setSendingEmail] = useState(false);
  
  // Pagination states for each report
  const [dailyPage, setDailyPage] = useState(1);
  const [routePage, setRoutePage] = useState(1);
  const [truckPage, setTruckPage] = useState(1);
  const [fuelPage, setFuelPage] = useState(1);
  const [driverPage, setDriverPage] = useState(1);
  const [lateArrivalPage, setLateArrivalPage] = useState(1);
  const [behaviorPage, setBehaviorPage] = useState(1);
  const [vehicleStatusPage, setVehicleStatusPage] = useState(1);
  const [spareUsagePage, setSpareUsagePage] = useState(1);
  const [complaintsPage, setComplaintsPage] = useState(1);
  const [dumpYardPage, setDumpYardPage] = useState(1);
  const [expiryTruckPage, setExpiryTruckPage] = useState(1);
  const [expiryDriverPage, setExpiryDriverPage] = useState(1);

  // Filter states for each report
  const [dailyStatusFilter, setDailyStatusFilter] = useState("all");
  const [routeEfficiencyFilter, setRouteEfficiencyFilter] = useState("all");
  const [truckTypeFilter, setTruckTypeFilter] = useState("all");
  const [fuelAnomalyFilter, setFuelAnomalyFilter] = useState("all");
  const [driverOnTimeFilter, setDriverOnTimeFilter] = useState("all");
  const [lateStatusFilter, setLateStatusFilter] = useState("all");
  const [behaviorTypeFilter, setBehaviorTypeFilter] = useState("all");
  const [behaviorSeverityFilter, setBehaviorSeverityFilter] = useState("all");
  const [vehicleStatusFilter, setVehicleStatusFilter] = useState("all");
  const [spareStatusFilter, setSpareStatusFilter] = useState("all");
  const [complaintsStatusFilter, setComplaintsStatusFilter] = useState("all");
  const [complaintsTypeFilter, setComplaintsTypeFilter] = useState("all");
  const [expiryStatusFilter, setExpiryStatusFilter] = useState("all");
  const [dumpYardSiteFilter, setDumpYardSiteFilter] = useState("all");
  const [lateZoneFilter, setLateZoneFilter] = useState("all");
  const [lateWardFilter, setLateWardFilter] = useState("all");
  const [lateVendorFilter, setLateVendorFilter] = useState("all");
  const [lateRouteTypeFilter, setLateRouteTypeFilter] = useState("all");
  
  // Sync with URL param
  useEffect(() => {
    const tab = searchParams.get("tab");
    if (tab) {
      setActiveTab(tab);
    }
  }, [searchParams]);

  // Pagination helper
  const paginate = <T,>(data: T[], page: number): T[] => {
    const start = (page - 1) * ITEMS_PER_PAGE;
    return data.slice(start, start + ITEMS_PER_PAGE);
  };

  const getTotalPages = (totalItems: number): number => {
    return Math.ceil(totalItems / ITEMS_PER_PAGE);
  };

  const renderPagination = (currentPage: number, totalItems: number, setPage: (page: number) => void) => {
    const totalPages = getTotalPages(totalItems);
    if (totalPages <= 1) return null;

    const handlePageChange = (e: React.MouseEvent, newPage: number) => {
      e.preventDefault();
      e.stopPropagation();
      setPage(newPage);
    };

    return (
      <div className="flex flex-col items-center gap-3 mt-4 pt-4 border-t">
        <Pagination>
          <PaginationContent className="gap-1">
            <PaginationItem>
              <PaginationPrevious 
                onClick={(e) => handlePageChange(e, Math.max(1, currentPage - 1))}
                className={`h-8 text-xs px-2 ${currentPage === 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}`}
              />
            </PaginationItem>
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              let pageNum: number;
              if (totalPages <= 5) {
                pageNum = i + 1;
              } else if (currentPage <= 3) {
                pageNum = i + 1;
              } else if (currentPage >= totalPages - 2) {
                pageNum = totalPages - 4 + i;
              } else {
                pageNum = currentPage - 2 + i;
              }
              return (
                <PaginationItem key={pageNum}>
                  <PaginationLink
                    onClick={(e) => handlePageChange(e, pageNum)}
                    isActive={currentPage === pageNum}
                    className="h-8 w-8 text-xs cursor-pointer"
                  >
                    {pageNum}
                  </PaginationLink>
                </PaginationItem>
              );
            })}
            <PaginationItem>
              <PaginationNext 
                onClick={(e) => handlePageChange(e, Math.min(totalPages, currentPage + 1))}
                className={`h-8 text-xs px-2 ${currentPage === totalPages ? "pointer-events-none opacity-50" : "cursor-pointer"}`}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
        <span className="text-xs text-muted-foreground whitespace-nowrap">
          Showing {Math.min((currentPage - 1) * ITEMS_PER_PAGE + 1, totalItems)}-{Math.min(currentPage * ITEMS_PER_PAGE, totalItems)} of {totalItems} items
        </span>
      </div>
    );
  };

  const handleDownload = (reportType: string, format: string) => {
    toast({
      title: "Download Started",
      description: `Downloading ${reportType.replace(/_/g, ' ')} report as ${format.toUpperCase()} (with current filters applied)`,
    });
  };

  const handlePrint = (reportType: string) => {
    window.print();
  };
  
  const handleEmailExport = (reportType: string) => {
    setEmailReportType(reportType);
    setEmailDialogOpen(true);
  };
  
  const sendEmailReport = async () => {
    if (!emailAddress || !emailAddress.includes('@')) {
      toast({
        title: "Invalid Email",
        description: "Please enter a valid email address",
        variant: "destructive",
      });
      return;
    }
    
    setSendingEmail(true);
    // Simulate sending email
    await new Promise(resolve => setTimeout(resolve, 1500));
    setSendingEmail(false);
    setEmailDialogOpen(false);
    setEmailAddress("");
    
    toast({
      title: "Email Sent Successfully",
      description: `${emailReportType.replace(/_/g, ' ')} report has been sent to ${emailAddress} with current filters applied`,
    });
  };

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      {/* Email Export Dialog */}
      <Dialog open={emailDialogOpen} onOpenChange={setEmailDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Mail className="h-5 w-5" />
              Email Report
            </DialogTitle>
            <DialogDescription>
              Send the {emailReportType.replace(/_/g, ' ')} report with current filters to an email address.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Email Address</label>
              <Input
                type="email"
                placeholder="Enter email address"
                value={emailAddress}
                onChange={(e) => setEmailAddress(e.target.value)}
              />
            </div>
            <div className="text-sm text-muted-foreground">
              <p>Report will include:</p>
              <ul className="list-disc list-inside mt-1 space-y-1">
                <li>Current filter selections applied</li>
                <li>Date range: {dateFrom} to {dateTo}</li>
                <li>Format: PDF attachment</li>
              </ul>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEmailDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={sendEmailReport} disabled={sendingEmail}>
              {sendingEmail ? (
                <>Sending...</>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Send Email
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Header */}
      <PageHeader
        category="Analytics"
        title="Reports Center"
        description="Generate, filter and download comprehensive fleet reports"
        icon={FileText}
        badge={{
          label: "12 Report Types",
          variant: "outline",
          className: "bg-primary/10 text-primary border-primary/20",
        }}
      />

      {/* Global Filters */}
      <Card className="border-primary/20 bg-gradient-to-r from-primary/5 to-transparent">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Filter className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">Report Filters</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">From Date</label>
              <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">To Date</label>
              <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Zone</label>
              <Select value={selectedZone} onValueChange={setSelectedZone}>
                <SelectTrigger>
                  <SelectValue placeholder="All Zones" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Zones</SelectItem>
                  <SelectItem value="zone-a">Zone A</SelectItem>
                  <SelectItem value="zone-b">Zone B</SelectItem>
                  <SelectItem value="zone-c">Zone C</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Ward</label>
              <Select value={selectedWard} onValueChange={setSelectedWard}>
                <SelectTrigger>
                  <SelectValue placeholder="All Wards" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Wards</SelectItem>
                  <SelectItem value="kharadi-east">Kharadi East</SelectItem>
                  <SelectItem value="kharadi-west">Kharadi West</SelectItem>
                  <SelectItem value="viman-nagar">Viman Nagar</SelectItem>
                  <SelectItem value="kalyani-nagar">Kalyani Nagar</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Truck</label>
              <Select value={selectedTruck} onValueChange={setSelectedTruck}>
                <SelectTrigger>
                  <SelectValue placeholder="All Trucks" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Trucks</SelectItem>
                  <SelectItem value="MH-12-AB-1234">MH-12-AB-1234</SelectItem>
                  <SelectItem value="MH-12-CD-5678">MH-12-CD-5678</SelectItem>
                  <SelectItem value="MH-12-EF-9012">MH-12-EF-9012</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Report Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid grid-cols-4 md:grid-cols-12 h-auto gap-1 bg-muted/50 p-1">
          <TabsTrigger value="daily" className="flex items-center gap-1 text-xs md:text-sm">
            <MapPin className="h-3 w-3 md:h-4 md:w-4" />
            <span className="hidden md:inline">Pickup</span> Coverage
          </TabsTrigger>
          <TabsTrigger value="route" className="flex items-center gap-1 text-xs md:text-sm">
            <Route className="h-3 w-3 md:h-4 md:w-4" />
            Route
          </TabsTrigger>
          <TabsTrigger value="truck" className="flex items-center gap-1 text-xs md:text-sm">
            <Truck className="h-3 w-3 md:h-4 md:w-4" />
            Truck
          </TabsTrigger>
          <TabsTrigger value="fuel" className="flex items-center gap-1 text-xs md:text-sm">
            <Fuel className="h-3 w-3 md:h-4 md:w-4" />
            Fuel
          </TabsTrigger>
          <TabsTrigger value="driver" className="flex items-center gap-1 text-xs md:text-sm">
            <Users className="h-3 w-3 md:h-4 md:w-4" />
            Driver
          </TabsTrigger>
          <TabsTrigger value="late-arrival" className="flex items-center gap-1 text-xs md:text-sm">
            <Clock className="h-3 w-3 md:h-4 md:w-4" />
            Late Arrival
          </TabsTrigger>
          <TabsTrigger value="behavior" className="flex items-center gap-1 text-xs md:text-sm">
            <Gauge className="h-3 w-3 md:h-4 md:w-4" />
            Behavior
          </TabsTrigger>
          <TabsTrigger value="vehicle-status" className="flex items-center gap-1 text-xs md:text-sm">
            <WifiOff className="h-3 w-3 md:h-4 md:w-4" />
            Vehicle Status
          </TabsTrigger>
          <TabsTrigger value="spare-usage" className="flex items-center gap-1 text-xs md:text-sm">
            <ArrowRightLeft className="h-3 w-3 md:h-4 md:w-4" />
            Spare Usage
          </TabsTrigger>
          <TabsTrigger value="complaints" className="flex items-center gap-1 text-xs md:text-sm">
            <AlertTriangle className="h-3 w-3 md:h-4 md:w-4" />
            Complaints
          </TabsTrigger>
          <TabsTrigger value="dumpyard" className="flex items-center gap-1 text-xs md:text-sm">
            <Building className="h-3 w-3 md:h-4 md:w-4" />
            Dump Yard
          </TabsTrigger>
          <TabsTrigger value="expiry" className="flex items-center gap-1 text-xs md:text-sm">
            <Shield className="h-3 w-3 md:h-4 md:w-4" />
            Expiry
          </TabsTrigger>
        </TabsList>

        {/* Daily Collection Report */}
        <TabsContent value="daily" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <MapPin className="h-5 w-5 text-primary" />
                  Daily Pickup Coverage Report
                </CardTitle>
                <CardDescription>Pickup points coverage by ward, zone, and truck with completion status</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("daily_collection", "csv")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> CSV
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("daily_collection", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleEmailExport("Daily Pickup Coverage")}>
                  <Mail className="h-4 w-4 mr-1" /> Email
                </Button>
                <Button variant="outline" size="sm" onClick={() => handlePrint("daily_collection")}>
                  <Printer className="h-4 w-4 mr-1" /> Print
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Filter Tabs */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-muted-foreground">Filter by Status:</span>
                <div className="flex gap-1">
                  {["all", "completed", "partial"].map((status) => (
                    <Badge
                      key={status}
                      variant={dailyStatusFilter === status ? "default" : "outline"}
                      className={`cursor-pointer capitalize ${dailyStatusFilter === status ? "" : "hover:bg-muted"}`}
                      onClick={() => { setDailyStatusFilter(status); setDailyPage(1); }}
                    >
                      {status === "all" ? "All" : status}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <Card className="bg-emerald-500/10 border-emerald-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-emerald-600">211</p>
                    <p className="text-xs text-muted-foreground">Total Pickup Points</p>
                  </CardContent>
                </Card>
                <Card className="bg-green-500/10 border-green-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-green-600">201</p>
                    <p className="text-xs text-muted-foreground">Covered</p>
                  </CardContent>
                </Card>
                <Card className="bg-red-500/10 border-red-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-red-600">10</p>
                    <p className="text-xs text-muted-foreground">Missed</p>
                  </CardContent>
                </Card>
                <Card className="bg-blue-500/10 border-blue-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-blue-600">10.9</p>
                    <p className="text-xs text-muted-foreground">Total Tons</p>
                  </CardContent>
                </Card>
                <Card className="bg-purple-500/10 border-purple-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-purple-600">95.3%</p>
                    <p className="text-xs text-muted-foreground">Completion</p>
                  </CardContent>
                </Card>
              </div>

              {/* Chart */}
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={weeklyTrendData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="day" className="text-xs" />
                    <YAxis className="text-xs" />
                    <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--background))', border: '1px solid hsl(var(--border))' }} />
                    <Bar dataKey="collected" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} name="Collected (tons)" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Table */}
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead>Date</TableHead>
                      <TableHead>Ward</TableHead>
                      <TableHead>Zone</TableHead>
                      <TableHead>Truck</TableHead>
                      <TableHead>Driver</TableHead>
                      <TableHead className="text-center">Pickup Points</TableHead>
                      <TableHead className="text-center">Covered</TableHead>
                      <TableHead className="text-center">Missed</TableHead>
                      <TableHead className="text-right">Weight (T)</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(() => {
                      const filteredData = dailyStatusFilter === "all" 
                        ? dailyPickupCoverageData 
                        : dailyPickupCoverageData.filter(d => d.status === dailyStatusFilter);
                      return paginate(filteredData, dailyPage).map((row) => (
                        <TableRow key={row.id}>
                          <TableCell className="font-medium">{row.date}</TableCell>
                          <TableCell>{row.ward}</TableCell>
                          <TableCell>{row.zone}</TableCell>
                          <TableCell className="font-mono text-xs">{row.truck}</TableCell>
                          <TableCell>{row.driver}</TableCell>
                          <TableCell className="text-center">{row.totalPoints}</TableCell>
                          <TableCell className="text-center text-green-600 font-medium">{row.covered}</TableCell>
                          <TableCell className="text-center text-red-600 font-medium">{row.missed}</TableCell>
                          <TableCell className="text-right">{row.weight}</TableCell>
                          <TableCell>
                            <Badge variant={row.status === "completed" ? "default" : "secondary"} 
                                   className={row.status === "completed" ? "bg-green-500/20 text-green-700 border-green-500/30" : "bg-yellow-500/20 text-yellow-700 border-yellow-500/30"}>
                              {row.status}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ));
                    })()}
                  </TableBody>
                </Table>
              </div>
              {(() => {
                const filteredData = dailyStatusFilter === "all" 
                  ? dailyPickupCoverageData 
                  : dailyPickupCoverageData.filter(d => d.status === dailyStatusFilter);
                return renderPagination(dailyPage, filteredData.length, setDailyPage);
              })()}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Route Performance Report */}
        <TabsContent value="route" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Route className="h-5 w-5 text-primary" />
                  Route Performance Report
                </CardTitle>
                <CardDescription>Route completion rates, deviations, and efficiency metrics</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("route_performance", "csv")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> CSV
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("route_performance", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Filter Tabs */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-muted-foreground">Filter by Efficiency:</span>
                <div className="flex gap-1">
                  {[
                    { key: "all", label: "All" },
                    { key: "high", label: "High (≥90%)" },
                    { key: "medium", label: "Medium (80-89%)" },
                    { key: "low", label: "Low (<80%)" }
                  ].map((filter) => (
                    <Badge
                      key={filter.key}
                      variant={routeEfficiencyFilter === filter.key ? "default" : "outline"}
                      className={`cursor-pointer ${routeEfficiencyFilter === filter.key ? "" : "hover:bg-muted"}`}
                      onClick={() => { setRouteEfficiencyFilter(filter.key); setRoutePage(1); }}
                    >
                      {filter.label}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="bg-primary/10 border-primary/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-primary">94.6%</p>
                    <p className="text-xs text-muted-foreground">Avg Completion</p>
                  </CardContent>
                </Card>
                <Card className="bg-orange-500/10 border-orange-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-orange-600">19</p>
                    <p className="text-xs text-muted-foreground">Total Deviations</p>
                  </CardContent>
                </Card>
                <Card className="bg-blue-500/10 border-blue-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-blue-600">4.3 hrs</p>
                    <p className="text-xs text-muted-foreground">Avg Route Time</p>
                  </CardContent>
                </Card>
                <Card className="bg-green-500/10 border-green-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-green-600">91.2%</p>
                    <p className="text-xs text-muted-foreground">Avg Efficiency</p>
                  </CardContent>
                </Card>
              </div>

              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead>Route</TableHead>
                      <TableHead className="text-center">Completion %</TableHead>
                      <TableHead className="text-center">Avg Time</TableHead>
                      <TableHead className="text-center">Deviations</TableHead>
                      <TableHead>Efficiency</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(() => {
                      const filteredData = routePerformanceData.filter(row => {
                        if (routeEfficiencyFilter === "all") return true;
                        if (routeEfficiencyFilter === "high") return row.efficiency >= 90;
                        if (routeEfficiencyFilter === "medium") return row.efficiency >= 80 && row.efficiency < 90;
                        return row.efficiency < 80;
                      });
                      return paginate(filteredData, routePage).map((row, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-medium">{row.route}</TableCell>
                          <TableCell className="text-center">
                            <div className="flex items-center gap-2 justify-center">
                              <span className={row.completion >= 95 ? "text-green-600" : row.completion >= 90 ? "text-yellow-600" : "text-red-600"}>
                                {row.completion}%
                              </span>
                              {row.completion >= 95 ? <TrendingUp className="h-4 w-4 text-green-600" /> : <TrendingDown className="h-4 w-4 text-red-600" />}
                            </div>
                          </TableCell>
                          <TableCell className="text-center">{row.avgTime}</TableCell>
                          <TableCell className="text-center">
                            <Badge variant={row.deviations === 0 ? "default" : "destructive"} className={row.deviations === 0 ? "bg-green-500/20 text-green-700" : ""}>
                              {row.deviations}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Progress value={row.efficiency} className="h-2 w-20" />
                              <span className="text-sm font-medium">{row.efficiency}%</span>
                            </div>
                          </TableCell>
                        </TableRow>
                      ));
                    })()}
                  </TableBody>
                </Table>
              </div>
              {(() => {
                const filteredData = routePerformanceData.filter(row => {
                  if (routeEfficiencyFilter === "all") return true;
                  if (routeEfficiencyFilter === "high") return row.efficiency >= 90;
                  if (routeEfficiencyFilter === "medium") return row.efficiency >= 80 && row.efficiency < 90;
                  return row.efficiency < 80;
                });
                return renderPagination(routePage, filteredData.length, setRoutePage);
              })()}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Truck Utilization Report */}
        <TabsContent value="truck" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Truck className="h-5 w-5 text-primary" />
                  Truck Utilization Report
                </CardTitle>
                <CardDescription>Trips, operating hours, idle time, and vehicle utilization</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("truck_utilization", "csv")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> CSV
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("truck_utilization", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Filter Tabs */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-muted-foreground">Filter by Type:</span>
                <div className="flex gap-1">
                  {["all", "Compactor", "Mini Truck", "Dumper", "Open Truck"].map((type) => (
                    <Badge
                      key={type}
                      variant={truckTypeFilter === type ? "default" : "outline"}
                      className={`cursor-pointer ${truckTypeFilter === type ? "" : "hover:bg-muted"}`}
                      onClick={() => { setTruckTypeFilter(type); setTruckPage(1); }}
                    >
                      {type === "all" ? "All Types" : type}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="bg-primary/10 border-primary/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-primary">15</p>
                    <p className="text-xs text-muted-foreground">Total Trips</p>
                  </CardContent>
                </Card>
                <Card className="bg-blue-500/10 border-blue-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-blue-600">41.5 hrs</p>
                    <p className="text-xs text-muted-foreground">Operating Hours</p>
                  </CardContent>
                </Card>
                <Card className="bg-orange-500/10 border-orange-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-orange-600">6.1 hrs</p>
                    <p className="text-xs text-muted-foreground">Total Idle Time</p>
                  </CardContent>
                </Card>
                <Card className="bg-green-500/10 border-green-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-green-600">89.2%</p>
                    <p className="text-xs text-muted-foreground">Avg Utilization</p>
                  </CardContent>
                </Card>
              </div>

              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead>Truck</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead className="text-center">Trips</TableHead>
                      <TableHead className="text-center">Operating Hrs</TableHead>
                      <TableHead className="text-center">Idle Time</TableHead>
                      <TableHead className="text-center">Distance (km)</TableHead>
                      <TableHead>Utilization</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(() => {
                      const filteredData = truckTypeFilter === "all" 
                        ? truckUtilizationData 
                        : truckUtilizationData.filter(d => d.type === truckTypeFilter);
                      return paginate(filteredData, truckPage).map((row, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-mono text-xs font-medium">{row.truck}</TableCell>
                          <TableCell>
                            <Badge variant="outline">{row.type}</Badge>
                          </TableCell>
                          <TableCell className="text-center">{row.trips}</TableCell>
                          <TableCell className="text-center">{row.operatingHours}</TableCell>
                          <TableCell className="text-center">
                            <span className={row.idleTime > 1.5 ? "text-red-600" : "text-green-600"}>
                              {row.idleTime} hrs
                            </span>
                          </TableCell>
                          <TableCell className="text-center">{row.distance}</TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Progress value={row.utilization} className="h-2 w-20" />
                              <span className={`text-sm font-medium ${row.utilization >= 90 ? "text-green-600" : row.utilization >= 80 ? "text-yellow-600" : "text-red-600"}`}>
                                {row.utilization}%
                              </span>
                            </div>
                          </TableCell>
                        </TableRow>
                      ));
                    })()}
                  </TableBody>
                </Table>
              </div>
              {(() => {
                const filteredData = truckTypeFilter === "all" 
                  ? truckUtilizationData 
                  : truckUtilizationData.filter(d => d.type === truckTypeFilter);
                return renderPagination(truckPage, filteredData.length, setTruckPage);
              })()}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Fuel Consumption Report */}
        <TabsContent value="fuel" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Fuel className="h-5 w-5 text-primary" />
                  Fuel Consumption Report
                </CardTitle>
                <CardDescription>Fuel usage, efficiency metrics, anomaly detection, and costs</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("fuel_consumption", "csv")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> CSV
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("fuel_consumption", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Filter Tabs */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-muted-foreground">Filter by Status:</span>
                <div className="flex gap-1">
                  {[
                    { key: "all", label: "All" },
                    { key: "normal", label: "Normal" },
                    { key: "anomaly", label: "Anomalies" }
                  ].map((filter) => (
                    <Badge
                      key={filter.key}
                      variant={fuelAnomalyFilter === filter.key ? "default" : "outline"}
                      className={`cursor-pointer ${fuelAnomalyFilter === filter.key ? "" : "hover:bg-muted"}`}
                      onClick={() => { setFuelAnomalyFilter(filter.key); setFuelPage(1); }}
                    >
                      {filter.label}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <Card className="bg-primary/10 border-primary/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-primary">105L</p>
                    <p className="text-xs text-muted-foreground">Total Fuel</p>
                  </CardContent>
                </Card>
                <Card className="bg-blue-500/10 border-blue-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-blue-600">224 km</p>
                    <p className="text-xs text-muted-foreground">Total Distance</p>
                  </CardContent>
                </Card>
                <Card className="bg-green-500/10 border-green-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-green-600">2.21</p>
                    <p className="text-xs text-muted-foreground">Avg km/L</p>
                  </CardContent>
                </Card>
                <Card className="bg-orange-500/10 border-orange-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-orange-600">₹10,500</p>
                    <p className="text-xs text-muted-foreground">Total Cost</p>
                  </CardContent>
                </Card>
                <Card className="bg-red-500/10 border-red-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-red-600">1</p>
                    <p className="text-xs text-muted-foreground">Anomalies</p>
                  </CardContent>
                </Card>
              </div>

              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead>Truck</TableHead>
                      <TableHead className="text-center">Fuel (L)</TableHead>
                      <TableHead className="text-center">Distance (km)</TableHead>
                      <TableHead className="text-center">Efficiency (km/L)</TableHead>
                      <TableHead className="text-right">Cost (₹)</TableHead>
                      <TableHead className="text-center">Anomaly</TableHead>
                      <TableHead>Score</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(() => {
                      const filteredData = fuelConsumptionData.filter(row => {
                        if (fuelAnomalyFilter === "all") return true;
                        if (fuelAnomalyFilter === "anomaly") return row.anomaly;
                        return !row.anomaly;
                      });
                      return paginate(filteredData, fuelPage).map((row, idx) => (
                        <TableRow key={idx} className={row.anomaly ? "bg-red-500/5" : ""}>
                          <TableCell className="font-mono text-xs font-medium">{row.truck}</TableCell>
                          <TableCell className="text-center">{row.fuelUsed}</TableCell>
                          <TableCell className="text-center">{row.distance}</TableCell>
                          <TableCell className="text-center">
                            <span className={row.efficiency >= 2.0 ? "text-green-600" : "text-red-600"}>
                              {row.efficiency.toFixed(2)}
                            </span>
                          </TableCell>
                          <TableCell className="text-right">₹{row.cost.toLocaleString()}</TableCell>
                          <TableCell className="text-center">
                            {row.anomaly ? (
                              <Badge variant="destructive" className="gap-1">
                                <AlertTriangle className="h-3 w-3" /> Detected
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="bg-green-500/20 text-green-700 border-green-500/30">Normal</Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Progress value={row.score} className="h-2 w-16" />
                              <span className={`text-sm font-medium ${row.score >= 80 ? "text-green-600" : row.score >= 60 ? "text-yellow-600" : "text-red-600"}`}>
                                {row.score}
                              </span>
                            </div>
                          </TableCell>
                        </TableRow>
                      ));
                    })()}
                  </TableBody>
                </Table>
              </div>
              {(() => {
                const filteredData = fuelConsumptionData.filter(row => {
                  if (fuelAnomalyFilter === "all") return true;
                  if (fuelAnomalyFilter === "anomaly") return row.anomaly;
                  return !row.anomaly;
                });
                return renderPagination(fuelPage, filteredData.length, setFuelPage);
              })()}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Driver Attendance Report */}
        <TabsContent value="driver" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5 text-primary" />
                  Driver Attendance & Performance Report
                </CardTitle>
                <CardDescription>Shift timings, routes completed, violations, and driver scores</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("driver_attendance", "csv")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> CSV
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("driver_attendance", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Filter Tabs */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-muted-foreground">Filter by Attendance:</span>
                <div className="flex gap-1">
                  {[
                    { key: "all", label: "All" },
                    { key: "on-time", label: "On Time" },
                    { key: "late", label: "Late" }
                  ].map((filter) => (
                    <Badge
                      key={filter.key}
                      variant={driverOnTimeFilter === filter.key ? "default" : "outline"}
                      className={`cursor-pointer ${driverOnTimeFilter === filter.key ? "" : "hover:bg-muted"}`}
                      onClick={() => { setDriverOnTimeFilter(filter.key); setDriverPage(1); }}
                    >
                      {filter.label}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="bg-primary/10 border-primary/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-primary">5</p>
                    <p className="text-xs text-muted-foreground">Active Drivers</p>
                  </CardContent>
                </Card>
                <Card className="bg-green-500/10 border-green-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-green-600">41 hrs</p>
                    <p className="text-xs text-muted-foreground">Total Hours</p>
                  </CardContent>
                </Card>
                <Card className="bg-red-500/10 border-red-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-red-600">4</p>
                    <p className="text-xs text-muted-foreground">Violations</p>
                  </CardContent>
                </Card>
                <Card className="bg-blue-500/10 border-blue-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-blue-600">87</p>
                    <p className="text-xs text-muted-foreground">Avg Score</p>
                  </CardContent>
                </Card>
              </div>

              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead>Driver</TableHead>
                      <TableHead>ID</TableHead>
                      <TableHead className="text-center">Shift Start</TableHead>
                      <TableHead className="text-center">Shift End</TableHead>
                      <TableHead className="text-center">Hours</TableHead>
                      <TableHead className="text-center">Routes</TableHead>
                      <TableHead className="text-center">On Time</TableHead>
                      <TableHead className="text-center">Violations</TableHead>
                      <TableHead>Score</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(() => {
                      const filteredData = driverAttendanceData.filter(row => {
                        if (driverOnTimeFilter === "all") return true;
                        if (driverOnTimeFilter === "on-time") return row.onTime;
                        return !row.onTime;
                      });
                      return paginate(filteredData, driverPage).map((row, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-medium">{row.driver}</TableCell>
                          <TableCell className="font-mono text-xs">{row.id}</TableCell>
                          <TableCell className="text-center">{row.shiftStart}</TableCell>
                          <TableCell className="text-center">{row.shiftEnd}</TableCell>
                          <TableCell className="text-center">{row.hoursWorked}</TableCell>
                          <TableCell className="text-center">{row.routes}</TableCell>
                          <TableCell className="text-center">
                            {row.onTime ? (
                              <Badge className="bg-green-500/20 text-green-700 border-green-500/30">Yes</Badge>
                            ) : (
                              <Badge variant="destructive">Late</Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-center">
                            <span className={row.violations > 0 ? "text-red-600 font-medium" : "text-green-600"}>
                              {row.violations}
                            </span>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Progress value={row.score} className="h-2 w-16" />
                              <span className={`text-sm font-medium ${row.score >= 90 ? "text-green-600" : row.score >= 75 ? "text-yellow-600" : "text-red-600"}`}>
                                {row.score}
                              </span>
                            </div>
                          </TableCell>
                        </TableRow>
                      ));
                    })()}
                  </TableBody>
                </Table>
              </div>
              {(() => {
                const filteredData = driverAttendanceData.filter(row => {
                  if (driverOnTimeFilter === "all") return true;
                  if (driverOnTimeFilter === "on-time") return row.onTime;
                  return !row.onTime;
                });
                return renderPagination(driverPage, filteredData.length, setDriverPage);
              })()}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Late Arrival Report */}
        <TabsContent value="late-arrival" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5 text-primary" />
                  Late Arrival Report
                </CardTitle>
                <CardDescription>Trucks that did not reach first pickup point on time (Buffer: {localStorage.getItem('lateArrivalBuffer') || '10'} min)</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("late_arrival", "csv")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> CSV
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("late_arrival", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {(() => {
                const buffer = parseInt(localStorage.getItem('lateArrivalBuffer') || '10');
                const allData = lateArrivalData.filter(row => {
                  const zoneMatch = lateZoneFilter === "all" || row.zone === lateZoneFilter;
                  const wardMatch = lateWardFilter === "all" || row.ward === lateWardFilter;
                  const vendorMatch = lateVendorFilter === "all" || row.vendor === lateVendorFilter;
                  const routeTypeMatch = lateRouteTypeFilter === "all" || row.routeType === lateRouteTypeFilter;
                  return zoneMatch && wardMatch && vendorMatch && routeTypeMatch;
                });
                const filteredByStatus = allData.filter(row => {
                  if (lateStatusFilter === "all") return true;
                  const isLate = row.delay > buffer;
                  if (lateStatusFilter === "late") return isLate;
                  return !isLate;
                });
                const lateCount = allData.filter(d => d.delay > buffer).length;
                const onTimeCount = allData.filter(d => d.delay <= buffer).length;
                const avgDelay = Math.round(allData.filter(d => d.delay > buffer).reduce((sum, d) => sum + d.delay, 0) / Math.max(lateCount, 1));

                const uniqueZones = [...new Set(lateArrivalData.map(d => d.zone))];
                const uniqueWards = [...new Set(lateArrivalData.filter(d => lateZoneFilter === "all" || d.zone === lateZoneFilter).map(d => d.ward))];
                const uniqueVendors = [...new Set(lateArrivalData.map(d => d.vendor))];

                return (
                  <>
                    {/* Filters */}
                    <div className="flex flex-wrap items-center gap-3">
                      <Select value={lateZoneFilter} onValueChange={(v) => { setLateZoneFilter(v); setLateWardFilter("all"); setLateArrivalPage(1); }}>
                        <SelectTrigger className="w-[160px] h-8 text-xs">
                          <SelectValue placeholder="Zone" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Zones</SelectItem>
                          {uniqueZones.map(z => <SelectItem key={z} value={z}>{z}</SelectItem>)}
                        </SelectContent>
                      </Select>
                      <Select value={lateWardFilter} onValueChange={(v) => { setLateWardFilter(v); setLateArrivalPage(1); }}>
                        <SelectTrigger className="w-[160px] h-8 text-xs">
                          <SelectValue placeholder="Ward" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Wards</SelectItem>
                          {uniqueWards.map(w => <SelectItem key={w} value={w}>{w}</SelectItem>)}
                        </SelectContent>
                      </Select>
                      <Select value={lateVendorFilter} onValueChange={(v) => { setLateVendorFilter(v); setLateArrivalPage(1); }}>
                        <SelectTrigger className="w-[180px] h-8 text-xs">
                          <SelectValue placeholder="Vendor" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Vendors</SelectItem>
                          {uniqueVendors.map(v => <SelectItem key={v} value={v}>{v}</SelectItem>)}
                        </SelectContent>
                      </Select>
                      <Select value={lateRouteTypeFilter} onValueChange={(v) => { setLateRouteTypeFilter(v); setLateArrivalPage(1); }}>
                        <SelectTrigger className="w-[160px] h-8 text-xs">
                          <SelectValue placeholder="Route Type" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Types</SelectItem>
                          <SelectItem value="primary">Primary</SelectItem>
                          <SelectItem value="secondary">Secondary</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Status Filter */}
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-medium text-muted-foreground">Filter by Status:</span>
                      <div className="flex gap-1">
                        {[
                          { key: "all", label: "All" },
                          { key: "on-time", label: "On Time" },
                          { key: "late", label: "Late" }
                        ].map((filter) => (
                          <Badge
                            key={filter.key}
                            variant={lateStatusFilter === filter.key ? "default" : "outline"}
                            className={`cursor-pointer ${lateStatusFilter === filter.key ? "" : "hover:bg-muted"}`}
                            onClick={() => { setLateStatusFilter(filter.key); setLateArrivalPage(1); }}
                          >
                            {filter.label}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <Card className="bg-green-500/10 border-green-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-green-600">{onTimeCount}</p>
                          <p className="text-xs text-muted-foreground">On Time</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-red-500/10 border-red-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-red-600">{lateCount}</p>
                          <p className="text-xs text-muted-foreground">Late Arrivals</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-orange-500/10 border-orange-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-orange-600">{avgDelay} min</p>
                          <p className="text-xs text-muted-foreground">Avg Delay</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-primary/10 border-primary/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-primary">{allData.length > 0 ? Math.round((onTimeCount / allData.length) * 100) : 0}%</p>
                          <p className="text-xs text-muted-foreground">On-Time Rate</p>
                        </CardContent>
                      </Card>
                    </div>

                    <div className="rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow className="bg-muted/50">
                            <TableHead>Date</TableHead>
                            <TableHead>Zone</TableHead>
                            <TableHead>Truck</TableHead>
                            <TableHead>Driver</TableHead>
                            <TableHead>Route</TableHead>
                            <TableHead>Type</TableHead>
                            <TableHead className="text-center">Scheduled</TableHead>
                            <TableHead className="text-center">Actual</TableHead>
                            <TableHead className="text-center">Delay</TableHead>
                            <TableHead>Reason</TableHead>
                            <TableHead>Status</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {paginate(filteredByStatus, lateArrivalPage).map((row) => {
                            const isLate = row.delay > buffer;
                            return (
                              <TableRow key={row.id} className={isLate ? "bg-red-500/5" : ""}>
                                <TableCell className="font-medium">{row.date}</TableCell>
                                <TableCell className="text-xs">{row.zone}</TableCell>
                                <TableCell className="font-mono text-xs">{row.truck}</TableCell>
                                <TableCell>{row.driver}</TableCell>
                                <TableCell>{row.route}</TableCell>
                                <TableCell>
                                  <Badge variant="outline" className="text-xs">
                                    {row.routeType === "primary" ? "P" : "S"}
                                  </Badge>
                                </TableCell>
                                <TableCell className="text-center">{row.scheduledTime}</TableCell>
                                <TableCell className="text-center">{row.actualTime}</TableCell>
                                <TableCell className="text-center">
                                  <span className={`font-medium ${isLate ? "text-red-600" : row.delay <= 0 ? "text-green-600" : "text-yellow-600"}`}>
                                    {row.delay > 0 ? `+${row.delay}` : row.delay} min
                                  </span>
                                </TableCell>
                                <TableCell className="text-xs text-muted-foreground">{row.reason || "-"}</TableCell>
                                <TableCell>
                                  <Badge className={isLate ? "bg-red-500/20 text-red-700 border-red-500/30" : "bg-green-500/20 text-green-700 border-green-500/30"}>
                                    {isLate ? "Late" : "On Time"}
                                  </Badge>
                                </TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </div>
                    {renderPagination(lateArrivalPage, filteredByStatus.length, setLateArrivalPage)}
                  </>
                );
              })()}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Driver Behavior Report */}
        <TabsContent value="behavior" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Gauge className="h-5 w-5 text-primary" />
                  Driver Behavior Report
                </CardTitle>
                <CardDescription>Overspeeding, harsh braking, and rapid acceleration incidents</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("driver_behavior", "csv")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> CSV
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("driver_behavior", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleEmailExport("Driver Behavior")}>
                  <Mail className="h-4 w-4 mr-1" /> Email
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Filter Tabs */}
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-muted-foreground">Type:</span>
                  <div className="flex gap-1">
                    {[
                      { key: "all", label: "All" },
                      { key: "Overspeeding", label: "Overspeeding" },
                      { key: "Harsh Braking", label: "Harsh Braking" },
                      { key: "Rapid Acceleration", label: "Rapid Accel" }
                    ].map((filter) => (
                      <Badge
                        key={filter.key}
                        variant={behaviorTypeFilter === filter.key ? "default" : "outline"}
                        className={`cursor-pointer ${behaviorTypeFilter === filter.key ? "" : "hover:bg-muted"}`}
                        onClick={() => { setBehaviorTypeFilter(filter.key); setBehaviorPage(1); }}
                      >
                        {filter.label}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-muted-foreground">Severity:</span>
                  <div className="flex gap-1">
                    {[
                      { key: "all", label: "All" },
                      { key: "high", label: "High" },
                      { key: "medium", label: "Medium" },
                      { key: "low", label: "Low" }
                    ].map((filter) => (
                      <Badge
                        key={filter.key}
                        variant={behaviorSeverityFilter === filter.key ? "default" : "outline"}
                        className={`cursor-pointer ${behaviorSeverityFilter === filter.key ? "" : "hover:bg-muted"}`}
                        onClick={() => { setBehaviorSeverityFilter(filter.key); setBehaviorPage(1); }}
                      >
                        {filter.label}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>

              {(() => {
                const filteredData = driverBehaviorData.filter(row => {
                  const typeMatch = behaviorTypeFilter === "all" || row.incidentType === behaviorTypeFilter;
                  const severityMatch = behaviorSeverityFilter === "all" || row.severity === behaviorSeverityFilter;
                  return typeMatch && severityMatch;
                });
                
                const overspeedCount = filteredData.filter(d => d.incidentType === "Overspeeding").length;
                const harshBrakingCount = filteredData.filter(d => d.incidentType === "Harsh Braking").length;
                const rapidAccelCount = filteredData.filter(d => d.incidentType === "Rapid Acceleration").length;
                const highSeverityCount = filteredData.filter(d => d.severity === "high").length;

                return (
                  <>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <Card className="bg-red-500/10 border-red-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-red-600">{overspeedCount}</p>
                          <p className="text-xs text-muted-foreground">Overspeeding</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-orange-500/10 border-orange-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-orange-600">{harshBrakingCount}</p>
                          <p className="text-xs text-muted-foreground">Harsh Braking</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-yellow-500/10 border-yellow-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-yellow-600">{rapidAccelCount}</p>
                          <p className="text-xs text-muted-foreground">Rapid Acceleration</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-purple-500/10 border-purple-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-purple-600">{highSeverityCount}</p>
                          <p className="text-xs text-muted-foreground">High Severity</p>
                        </CardContent>
                      </Card>
                    </div>

                    <div className="rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow className="bg-muted/50">
                            <TableHead>Date</TableHead>
                            <TableHead>Time</TableHead>
                            <TableHead>Truck</TableHead>
                            <TableHead>Driver</TableHead>
                            <TableHead>Incident Type</TableHead>
                            <TableHead className="text-center">Recorded</TableHead>
                            <TableHead className="text-center">Limit</TableHead>
                            <TableHead>Location</TableHead>
                            <TableHead>Severity</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {paginate(filteredData, behaviorPage).map((row) => (
                            <TableRow key={row.id} className={row.severity === "high" ? "bg-red-500/5" : ""}>
                              <TableCell className="font-medium">{row.date}</TableCell>
                              <TableCell>{row.time}</TableCell>
                              <TableCell className="font-mono text-xs">{row.truck}</TableCell>
                              <TableCell>{row.driver}</TableCell>
                              <TableCell>
                                <Badge variant="outline" className="gap-1">
                                  {row.incidentType === "Overspeeding" && <Zap className="h-3 w-3" />}
                                  {row.incidentType === "Harsh Braking" && <AlertTriangle className="h-3 w-3" />}
                                  {row.incidentType === "Rapid Acceleration" && <TrendingUp className="h-3 w-3" />}
                                  {row.incidentType}
                                </Badge>
                              </TableCell>
                              <TableCell className="text-center text-red-600 font-medium">{row.value}</TableCell>
                              <TableCell className="text-center text-muted-foreground">{row.limit}</TableCell>
                              <TableCell className="text-xs">{row.location}</TableCell>
                              <TableCell>
                                <Badge 
                                  className={
                                    row.severity === "high" 
                                      ? "bg-red-500/20 text-red-700 border-red-500/30"
                                      : row.severity === "medium"
                                      ? "bg-orange-500/20 text-orange-700 border-orange-500/30"
                                      : "bg-yellow-500/20 text-yellow-700 border-yellow-500/30"
                                  }
                                >
                                  {row.severity}
                                </Badge>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                    {renderPagination(behaviorPage, filteredData.length, setBehaviorPage)}
                  </>
                );
              })()}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Vehicle Status Report */}
        <TabsContent value="vehicle-status" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <WifiOff className="h-5 w-5 text-primary" />
                  Vehicle Status Report
                </CardTitle>
                <CardDescription>Live status of all vehicles including inactive and failed devices</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("vehicle_status", "csv")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> CSV
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("vehicle_status", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleEmailExport("Vehicle Status")}>
                  <Mail className="h-4 w-4 mr-1" /> Email
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Filter Tabs */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-muted-foreground">Filter by Status:</span>
                <div className="flex gap-1">
                  {[
                    { key: "all", label: "All" },
                    { key: "active", label: "Active" },
                    { key: "warning", label: "Warning" },
                    { key: "inactive", label: "Inactive" },
                    { key: "failed", label: "Failed" }
                  ].map((filter) => (
                    <Badge
                      key={filter.key}
                      variant={vehicleStatusFilter === filter.key ? "default" : "outline"}
                      className={`cursor-pointer ${vehicleStatusFilter === filter.key ? "" : "hover:bg-muted"}`}
                      onClick={() => { setVehicleStatusFilter(filter.key); setVehicleStatusPage(1); }}
                    >
                      {filter.label}
                    </Badge>
                  ))}
                </div>
              </div>

              {(() => {
                const filteredData = vehicleStatusFilter === "all" 
                  ? vehicleStatusData 
                  : vehicleStatusData.filter(d => d.status === vehicleStatusFilter);
                  
                const activeCount = filteredData.filter(d => d.status === "active").length;
                const inactiveCount = filteredData.filter(d => d.status === "inactive").length;
                const warningCount = filteredData.filter(d => d.status === "warning").length;
                const failedCount = filteredData.filter(d => d.status === "failed").length;

                return (
                  <>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <Card className="bg-green-500/10 border-green-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-green-600">{activeCount}</p>
                          <p className="text-xs text-muted-foreground">Active</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-yellow-500/10 border-yellow-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-yellow-600">{warningCount}</p>
                          <p className="text-xs text-muted-foreground">Warning</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-gray-500/10 border-gray-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-gray-600">{inactiveCount}</p>
                          <p className="text-xs text-muted-foreground">Inactive</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-red-500/10 border-red-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-red-600">{failedCount}</p>
                          <p className="text-xs text-muted-foreground">Failed</p>
                        </CardContent>
                      </Card>
                    </div>

                    <div className="rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow className="bg-muted/50">
                            <TableHead>Truck</TableHead>
                            <TableHead>Type</TableHead>
                            <TableHead>Driver</TableHead>
                            <TableHead>Route</TableHead>
                            <TableHead>GPS Status</TableHead>
                            <TableHead className="text-center">Battery</TableHead>
                            <TableHead className="text-center">Signal</TableHead>
                            <TableHead>Last Update</TableHead>
                            <TableHead>Status</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {paginate(filteredData, vehicleStatusPage).map((row) => (
                            <TableRow key={row.id} className={row.status === "failed" || row.status === "inactive" ? "bg-red-500/5" : ""}>
                              <TableCell className="font-mono text-xs font-medium">{row.truck}</TableCell>
                              <TableCell>
                                <Badge variant="outline" className="capitalize">{row.type}</Badge>
                              </TableCell>
                              <TableCell>{row.driver}</TableCell>
                              <TableCell>{row.route}</TableCell>
                              <TableCell>
                                <Badge 
                                  className={
                                    row.gpsStatus === "online"
                                      ? "bg-green-500/20 text-green-700 border-green-500/30"
                                      : row.gpsStatus === "warning"
                                      ? "bg-yellow-500/20 text-yellow-700 border-yellow-500/30"
                                      : "bg-red-500/20 text-red-700 border-red-500/30"
                                  }
                                >
                                  {row.gpsStatus === "online" ? "Online" : row.gpsStatus === "warning" ? "Weak Signal" : "Offline"}
                                </Badge>
                              </TableCell>
                              <TableCell className="text-center">
                                <div className="flex items-center justify-center gap-1">
                                  <Progress value={row.batteryLevel} className="h-2 w-12" />
                                  <span className={`text-xs font-medium ${row.batteryLevel < 20 ? "text-red-600" : row.batteryLevel < 50 ? "text-yellow-600" : "text-green-600"}`}>
                                    {row.batteryLevel}%
                                  </span>
                                </div>
                              </TableCell>
                              <TableCell className="text-center">
                                <span className={`font-medium ${row.signalStrength < 30 ? "text-red-600" : row.signalStrength < 60 ? "text-yellow-600" : "text-green-600"}`}>
                                  {row.signalStrength}%
                                </span>
                              </TableCell>
                              <TableCell className="text-xs text-muted-foreground">{row.lastUpdate}</TableCell>
                              <TableCell>
                                <Badge 
                                  className={
                                    row.status === "active"
                                      ? "bg-green-500/20 text-green-700 border-green-500/30"
                                      : row.status === "warning"
                                      ? "bg-yellow-500/20 text-yellow-700 border-yellow-500/30"
                                      : row.status === "inactive"
                                      ? "bg-gray-500/20 text-gray-700 border-gray-500/30"
                                      : "bg-red-500/20 text-red-700 border-red-500/30"
                                  }
                                >
                                  {row.status === "failed" && <XCircle className="h-3 w-3 mr-1" />}
                                  {row.status === "inactive" && <WifiOff className="h-3 w-3 mr-1" />}
                                  {row.status.charAt(0).toUpperCase() + row.status.slice(1)}
                                </Badge>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                    {renderPagination(vehicleStatusPage, filteredData.length, setVehicleStatusPage)}
                  </>
                );
              })()}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Complaints Report */}
        <TabsContent value="complaints" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-primary" />
                  Citizen Complaints Report
                </CardTitle>
                <CardDescription>Complaints mapped to truck movements and response times</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("complaints", "csv")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> CSV
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("complaints", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleEmailExport("Complaints")}>
                  <Mail className="h-4 w-4 mr-1" /> Email
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Filter Tabs */}
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-muted-foreground">Status:</span>
                  <div className="flex gap-1">
                    {[
                      { key: "all", label: "All" },
                      { key: "resolved", label: "Resolved" },
                      { key: "in-progress", label: "In Progress" },
                      { key: "pending", label: "Pending" }
                    ].map((filter) => (
                      <Badge
                        key={filter.key}
                        variant={complaintsStatusFilter === filter.key ? "default" : "outline"}
                        className={`cursor-pointer ${complaintsStatusFilter === filter.key ? "" : "hover:bg-muted"}`}
                        onClick={() => { setComplaintsStatusFilter(filter.key); setComplaintsPage(1); }}
                      >
                        {filter.label}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-muted-foreground">Type:</span>
                  <div className="flex gap-1">
                    {[
                      { key: "all", label: "All" },
                      { key: "Missed Pickup", label: "Missed Pickup" },
                      { key: "Irregular Timing", label: "Irregular Timing" },
                      { key: "Spillage", label: "Spillage" }
                    ].map((filter) => (
                      <Badge
                        key={filter.key}
                        variant={complaintsTypeFilter === filter.key ? "default" : "outline"}
                        className={`cursor-pointer ${complaintsTypeFilter === filter.key ? "" : "hover:bg-muted"}`}
                        onClick={() => { setComplaintsTypeFilter(filter.key); setComplaintsPage(1); }}
                      >
                        {filter.label}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>

              {(() => {
                const filteredData = complaintsData.filter(row => {
                  const statusMatch = complaintsStatusFilter === "all" || row.status === complaintsStatusFilter;
                  const typeMatch = complaintsTypeFilter === "all" || row.type === complaintsTypeFilter;
                  return statusMatch && typeMatch;
                });
                
                return (
                  <>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <Card className="bg-primary/10 border-primary/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-primary">{filteredData.length}</p>
                          <p className="text-xs text-muted-foreground">Total Complaints</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-green-500/10 border-green-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-green-600">{filteredData.filter(d => d.status === "resolved").length}</p>
                          <p className="text-xs text-muted-foreground">Resolved</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-yellow-500/10 border-yellow-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-yellow-600">{filteredData.filter(d => d.status === "in-progress").length}</p>
                          <p className="text-xs text-muted-foreground">In Progress</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-red-500/10 border-red-500/20">
                        <CardContent className="p-4 text-center">
                          <p className="text-2xl font-bold text-red-600">{filteredData.filter(d => d.status === "pending").length}</p>
                          <p className="text-xs text-muted-foreground">Pending</p>
                        </CardContent>
                      </Card>
                    </div>

                    <div className="rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow className="bg-muted/50">
                            <TableHead>ID</TableHead>
                            <TableHead>Date</TableHead>
                            <TableHead>Ward</TableHead>
                            <TableHead>Type</TableHead>
                            <TableHead>Truck</TableHead>
                            <TableHead className="text-center">Response Time</TableHead>
                            <TableHead>Status</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {paginate(filteredData, complaintsPage).map((row) => (
                            <TableRow key={row.id}>
                              <TableCell className="font-mono text-xs font-medium">{row.id}</TableCell>
                              <TableCell>{row.date}</TableCell>
                              <TableCell>{row.ward}</TableCell>
                              <TableCell>
                                <Badge variant="outline">{row.type}</Badge>
                              </TableCell>
                              <TableCell className="font-mono text-xs">{row.truck}</TableCell>
                              <TableCell className="text-center">{row.responseTime}</TableCell>
                              <TableCell>
                                <Badge 
                                  className={
                                    row.status === "resolved" 
                                      ? "bg-green-500/20 text-green-700 border-green-500/30" 
                                      : row.status === "in-progress" 
                                      ? "bg-yellow-500/20 text-yellow-700 border-yellow-500/30"
                                      : "bg-red-500/20 text-red-700 border-red-500/30"
                                  }
                                >
                                  {row.status}
                                </Badge>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                    {renderPagination(complaintsPage, filteredData.length, setComplaintsPage)}
                  </>
                );
              })()}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Dump Yard Log Report */}
        <TabsContent value="dumpyard" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Scale className="h-5 w-5 text-primary" />
                  Dump Yard & GTP Log Report
                </CardTitle>
                <CardDescription>Entry counts, weight per trip, and site capacity utilization</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("dumpyard_log", "csv")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> CSV
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("dumpyard_log", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleEmailExport("Dump Yard")}>
                  <Mail className="h-4 w-4 mr-1" /> Email
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="bg-primary/10 border-primary/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-primary">123</p>
                    <p className="text-xs text-muted-foreground">Total Entries</p>
                  </CardContent>
                </Card>
                <Card className="bg-blue-500/10 border-blue-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-blue-600">561.7 T</p>
                    <p className="text-xs text-muted-foreground">Total Weight</p>
                  </CardContent>
                </Card>
                <Card className="bg-green-500/10 border-green-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-green-600">4.57 T</p>
                    <p className="text-xs text-muted-foreground">Avg per Entry</p>
                  </CardContent>
                </Card>
                <Card className="bg-orange-500/10 border-orange-500/20">
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-orange-600">56.5%</p>
                    <p className="text-xs text-muted-foreground">Avg Capacity</p>
                  </CardContent>
                </Card>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                <div className="h-64">
                  <p className="text-sm font-medium mb-2 text-muted-foreground">Zone-wise Distribution</p>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={zoneWiseData}
                        cx="50%"
                        cy="50%"
                        innerRadius={40}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      >
                        {zoneWiseData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>

                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead>Site</TableHead>
                        <TableHead className="text-center">Entries</TableHead>
                        <TableHead className="text-center">Total (T)</TableHead>
                        <TableHead className="text-center">Avg (T)</TableHead>
                        <TableHead>Capacity</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {dumpYardData.map((row, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-medium">{row.site}</TableCell>
                          <TableCell className="text-center">{row.entries}</TableCell>
                          <TableCell className="text-center">{row.totalWeight}</TableCell>
                          <TableCell className="text-center">{row.avgWeight}</TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Progress value={row.capacity} className="h-2 w-16" />
                              <span className={`text-xs ${row.capacity >= 70 ? "text-orange-600" : "text-green-600"}`}>
                                {row.capacity}%
                              </span>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Expiry Report */}
        <TabsContent value="expiry" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-primary" />
                  Insurance & License Expiry Report
                </CardTitle>
                <CardDescription>Track truck insurance, fitness certificates, and driver license expiration dates</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("expiry_report", "csv")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> CSV
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("expiry_report", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleEmailExport("Expiry Report")}>
                  <Mail className="h-4 w-4 mr-1" /> Email
                </Button>
                <Button variant="outline" size="sm" onClick={() => handlePrint("expiry_report")}>
                  <Printer className="h-4 w-4 mr-1" /> Print
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Summary Cards */}
              {(() => {
                const today = new Date();
                const truckInsuranceExpiring = trucks.filter((t) => {
                  const insuranceDate = getTruckInsuranceDate(t);
                  const insuranceParsed = safeParseISO(insuranceDate);
                  if (!insuranceParsed) return false;
                  const days = differenceInDays(insuranceParsed, today);
                  return days >= 0 && days <= 30;
                }).length;
                const truckInsuranceExpired = trucks.filter((t) => {
                  const insuranceDate = getTruckInsuranceDate(t);
                  const insuranceParsed = safeParseISO(insuranceDate);
                  if (!insuranceParsed) return false;
                  return differenceInDays(insuranceParsed, today) < 0;
                }).length;
                const truckFitnessExpiring = trucks.filter((t) => {
                  const fitnessDate = getTruckFitnessDate(t);
                  const fitnessParsed = safeParseISO(fitnessDate);
                  if (!fitnessParsed) return false;
                  const days = differenceInDays(fitnessParsed, today);
                  return days >= 0 && days <= 30;
                }).length;
                const truckFitnessExpired = trucks.filter((t) => {
                  const fitnessDate = getTruckFitnessDate(t);
                  const fitnessParsed = safeParseISO(fitnessDate);
                  if (!fitnessParsed) return false;
                  return differenceInDays(fitnessParsed, today) < 0;
                }).length;
                const driverLicenseExpiring = drivers.filter((d) => {
                  const licenseDate = getDriverLicenseDate(d);
                  const licenseParsed = safeParseISO(licenseDate);
                  if (!licenseParsed) return false;
                  const days = differenceInDays(licenseParsed, today);
                  return days >= 0 && days <= 30;
                }).length;
                const driverLicenseExpired = drivers.filter((d) => {
                  const licenseDate = getDriverLicenseDate(d);
                  const licenseParsed = safeParseISO(licenseDate);
                  if (!licenseParsed) return false;
                  return differenceInDays(licenseParsed, today) < 0;
                }).length;

                return (
                  <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
                    <Card className="bg-red-500/10 border-red-500/20">
                      <CardContent className="p-4 text-center">
                        <p className="text-2xl font-bold text-red-600">{truckInsuranceExpired}</p>
                        <p className="text-xs text-muted-foreground">Insurance Expired</p>
                      </CardContent>
                    </Card>
                    <Card className="bg-orange-500/10 border-orange-500/20">
                      <CardContent className="p-4 text-center">
                        <p className="text-2xl font-bold text-orange-600">{truckInsuranceExpiring}</p>
                        <p className="text-xs text-muted-foreground">Insurance Expiring</p>
                      </CardContent>
                    </Card>
                    <Card className="bg-red-500/10 border-red-500/20">
                      <CardContent className="p-4 text-center">
                        <p className="text-2xl font-bold text-red-600">{truckFitnessExpired}</p>
                        <p className="text-xs text-muted-foreground">Fitness Expired</p>
                      </CardContent>
                    </Card>
                    <Card className="bg-orange-500/10 border-orange-500/20">
                      <CardContent className="p-4 text-center">
                        <p className="text-2xl font-bold text-orange-600">{truckFitnessExpiring}</p>
                        <p className="text-xs text-muted-foreground">Fitness Expiring</p>
                      </CardContent>
                    </Card>
                    <Card className="bg-red-500/10 border-red-500/20">
                      <CardContent className="p-4 text-center">
                        <p className="text-2xl font-bold text-red-600">{driverLicenseExpired}</p>
                        <p className="text-xs text-muted-foreground">License Expired</p>
                      </CardContent>
                    </Card>
                    <Card className="bg-orange-500/10 border-orange-500/20">
                      <CardContent className="p-4 text-center">
                        <p className="text-2xl font-bold text-orange-600">{driverLicenseExpiring}</p>
                        <p className="text-xs text-muted-foreground">License Expiring</p>
                      </CardContent>
                    </Card>
                  </div>
                );
              })()}

              {/* Truck Insurance & Fitness Table */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Truck className="h-5 w-5 text-primary" />
                    Truck Insurance & Fitness Expiry
                  </h3>
                  <Badge variant="outline" className="text-xs">
                    {trucks.length} Trucks
                  </Badge>
                </div>
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead>Vehicle No.</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Vendor</TableHead>
                        <TableHead>Insurance Expiry</TableHead>
                        <TableHead>Insurance Status</TableHead>
                        <TableHead>Fitness Expiry</TableHead>
                        <TableHead>Fitness Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {paginate(trucks, expiryTruckPage).map((truck) => {
                        const today = new Date();
                        const insuranceDate = getTruckInsuranceDate(truck);
                        const fitnessDate = getTruckFitnessDate(truck);
                        const insuranceParsed = safeParseISO(insuranceDate);
                        const fitnessParsed = safeParseISO(fitnessDate);
                        const insuranceDays = insuranceParsed ? differenceInDays(insuranceParsed, today) : null;
                        const fitnessDays = fitnessParsed ? differenceInDays(fitnessParsed, today) : null;
                        
                        const getStatusBadge = (days: number | null) => {
                          if (days === null) return <Badge variant="secondary">Unknown</Badge>;
                          if (days < 0) return <Badge variant="destructive">Expired</Badge>;
                          if (days <= 7) return <Badge className="bg-orange-500 text-white">Critical ({days}d)</Badge>;
                          if (days <= 30) return <Badge variant="secondary" className="bg-yellow-500/20 text-yellow-700">Warning ({days}d)</Badge>;
                          return <Badge variant="secondary" className="bg-green-500/20 text-green-700">Valid ({days}d)</Badge>;
                        };

                        return (
                          <TableRow key={truck.id}>
                            <TableCell className="font-mono font-medium">{truck.registrationNumber ?? truck.registration_number ?? truck.id}</TableCell>
                            <TableCell className="capitalize">{(truck.type || "").replace('-', ' ')}</TableCell>
                            <TableCell>{truck.vendorId ?? truck.vendor_id ?? "-"}</TableCell>
                            <TableCell>{insuranceParsed ? format(insuranceParsed, 'dd MMM yyyy') : "N/A"}</TableCell>
                            <TableCell>{getStatusBadge(insuranceDays)}</TableCell>
                            <TableCell>{fitnessParsed ? format(fitnessParsed, 'dd MMM yyyy') : "N/A"}</TableCell>
                            <TableCell>{getStatusBadge(fitnessDays)}</TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
                {renderPagination(expiryTruckPage, trucks.length, setExpiryTruckPage)}
              </div>

              {/* Driver License Table */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <IdCard className="h-5 w-5 text-primary" />
                    Driver License Expiry
                  </h3>
                  <Badge variant="outline" className="text-xs">
                    {drivers.length} Drivers
                  </Badge>
                </div>
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead>Driver ID</TableHead>
                        <TableHead>Name</TableHead>
                        <TableHead>Phone</TableHead>
                        <TableHead>License Number</TableHead>
                        <TableHead>License Expiry</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Days Left</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {paginate(drivers, expiryDriverPage).map((driver) => {
                        const today = new Date();
                        const licenseDate = getDriverLicenseDate(driver);
                        const licenseParsed = safeParseISO(licenseDate);
                        const licenseDays = licenseParsed ? differenceInDays(licenseParsed, today) : null;
                        
                        const getStatusBadge = (days: number | null) => {
                          if (days === null) return <Badge variant="secondary">Unknown</Badge>;
                          if (days < 0) return <Badge variant="destructive">Expired</Badge>;
                          if (days <= 7) return <Badge className="bg-orange-500 text-white">Critical</Badge>;
                          if (days <= 30) return <Badge variant="secondary" className="bg-yellow-500/20 text-yellow-700">Warning</Badge>;
                          return <Badge variant="secondary" className="bg-green-500/20 text-green-700">Valid</Badge>;
                        };

                        return (
                          <TableRow key={driver.id}>
                            <TableCell className="font-mono">{driver.id}</TableCell>
                            <TableCell className="font-medium">{driver.name}</TableCell>
                            <TableCell>{driver.phone}</TableCell>
                            <TableCell className="font-mono text-xs">{driver.licenseNumber ?? driver.license_number ?? "-"}</TableCell>
                            <TableCell>{licenseParsed ? format(licenseParsed, 'dd MMM yyyy') : "N/A"}</TableCell>
                            <TableCell>{getStatusBadge(licenseDays)}</TableCell>
                            <TableCell className={`font-medium ${licenseDays === null ? 'text-muted-foreground' : licenseDays < 0 ? 'text-red-600' : licenseDays <= 7 ? 'text-orange-600' : licenseDays <= 30 ? 'text-yellow-600' : 'text-green-600'}`}>
                              {licenseDays === null ? "N/A" : licenseDays < 0 ? `${Math.abs(licenseDays)} days ago` : `${licenseDays} days`}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
                {renderPagination(expiryDriverPage, drivers.length, setExpiryDriverPage)}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Spare Truck Usage Report */}
        <TabsContent value="spare-usage" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <ArrowRightLeft className="h-5 w-5 text-primary" />
                  Spare Truck Usage Report
                </CardTitle>
                <CardDescription>Track spare truck deployments and breakdown replacements</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleDownload("spare_usage", "csv")}>
                  <FileSpreadsheet className="h-4 w-4 mr-1" /> CSV
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleDownload("spare_usage", "pdf")}>
                  <Download className="h-4 w-4 mr-1" /> PDF
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleEmailExport("Spare Usage")}>
                  <Mail className="h-4 w-4 mr-1" /> Email
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Filter Tabs */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-muted-foreground">Filter by Status:</span>
                <div className="flex gap-1">
                  {[
                    { key: "all", label: "All" },
                    { key: "active", label: "Active" },
                    { key: "completed", label: "Completed" }
                  ].map((filter) => (
                    <Badge
                      key={filter.key}
                      variant={spareStatusFilter === filter.key ? "default" : "outline"}
                      className={`cursor-pointer ${spareStatusFilter === filter.key ? "" : "hover:bg-muted"}`}
                      onClick={() => { setSpareStatusFilter(filter.key); setSpareUsagePage(1); }}
                    >
                      {filter.label}
                    </Badge>
                  ))}
                </div>
              </div>

              {(() => {
                const filteredData = spareStatusFilter === "all" 
                  ? spareUsageData 
                  : spareUsageData.filter(d => d.status === spareStatusFilter);
                  
                return (
                  <>
                    {/* Summary Cards */}
                    <div className="grid gap-4 md:grid-cols-4">
                      <Card className="bg-primary/10 border-primary/30">
                        <CardContent className="pt-4">
                          <div className="text-2xl font-bold text-primary">{filteredData.length}</div>
                          <p className="text-sm text-muted-foreground">Total Deployments</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-green-500/10 border-green-500/30">
                        <CardContent className="pt-4">
                          <div className="text-2xl font-bold text-green-600">{filteredData.filter(s => s.status === "completed").length}</div>
                          <p className="text-sm text-muted-foreground">Completed</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-yellow-500/10 border-yellow-500/30">
                        <CardContent className="pt-4">
                          <div className="text-2xl font-bold text-yellow-600">{filteredData.filter(s => s.status === "active").length}</div>
                          <p className="text-sm text-muted-foreground">Currently Active</p>
                        </CardContent>
                      </Card>
                      <Card className="bg-muted">
                        <CardContent className="pt-4">
                          <div className="text-2xl font-bold">~5.5h</div>
                          <p className="text-sm text-muted-foreground">Avg Duration</p>
                        </CardContent>
                      </Card>
                    </div>

                    <div className="rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow className="bg-muted/50">
                            <TableHead>Date</TableHead>
                            <TableHead>Spare Truck</TableHead>
                            <TableHead>Original Truck</TableHead>
                            <TableHead>Route</TableHead>
                            <TableHead>Vendor</TableHead>
                            <TableHead>Breakdown Reason</TableHead>
                            <TableHead>Activated</TableHead>
                            <TableHead>Duration</TableHead>
                            <TableHead>Status</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {paginate(filteredData, spareUsagePage).map((record) => (
                            <TableRow key={record.id}>
                              <TableCell>{record.date}</TableCell>
                              <TableCell className="font-medium">
                                <div className="flex items-center gap-2">
                                  <Badge className="bg-primary/20 text-primary border-primary/30 text-xs">SPARE</Badge>
                                  {record.spareTruck}
                                </div>
                              </TableCell>
                              <TableCell>{record.originalTruck}</TableCell>
                              <TableCell>{record.route}</TableCell>
                              <TableCell className="text-sm">{record.vendor}</TableCell>
                              <TableCell>
                                <div className="flex items-center gap-1">
                                  <Wrench className="h-3 w-3 text-muted-foreground" />
                                  {record.breakdownReason}
                                </div>
                              </TableCell>
                              <TableCell>{record.activatedAt}</TableCell>
                              <TableCell className="font-medium">{record.duration}</TableCell>
                              <TableCell>
                                {record.status === "active" ? (
                                  <Badge className="bg-yellow-500/20 text-yellow-700">Active</Badge>
                                ) : (
                                  <Badge className="bg-green-500/20 text-green-700">Completed</Badge>
                                )}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                    {renderPagination(spareUsagePage, filteredData.length, setSpareUsagePage)}
                  </>
                );
              })()}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
