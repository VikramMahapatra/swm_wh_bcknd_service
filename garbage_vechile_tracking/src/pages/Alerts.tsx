import { useState, useEffect, useMemo } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader } from "@/components/PageHeader";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AlertTriangle,
  MapPinOff,
  Clock,
  Navigation,
  Shield,
  Gauge,
  Bell,
  BellOff,
  CheckCircle,
  XCircle,
  Eye,
  Filter,
  Download,
  Search,
  TrendingUp,
  TrendingDown,
  Zap,
  MapPin,
  Truck,
  Calendar,
  RefreshCw,
  Phone,
  MessageCircle,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  Legend,
} from "recharts";
import { ActionDropdown } from "@/components/ActionDropdown";
import { useAlerts } from "@/hooks/useDataQueries";
import { Loader2 } from "lucide-react";

// Alert metadata and helpers
type AlertItem = {
  id: number | string;
  type: string;
  truck: string;
  route: string;
  driver: string;
  driverPhone: string;
  vendorName: string;
  vendorPhone: string;
  message: string;
  location: string;
  date: string;
  time: string;
  timestamp: string;
  severity: string;
  zone: string;
  ward: string;
  status: string;
};

const alertTypeMeta: Record<string, { label: string; icon: typeof Bell }> = {
  route_deviation: { label: "Route Deviation", icon: Navigation },
  missed_pickup: { label: "Missed Pickup", icon: MapPinOff },
  unauthorized_halt: { label: "Unauthorized Halt", icon: Clock },
  speed_violation: { label: "Speed Violation", icon: Gauge },
  geofence_breach: { label: "Geofence Breach", icon: Shield },
  device_tamper: { label: "Device Tamper", icon: AlertTriangle },
};

const toTitleCase = (value: string) =>
  value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());

const formatDate = (value: Date) => value.toISOString().split("T")[0];

const getDefaultDateRange = () => {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 9);
  return { start: formatDate(start), end: formatDate(end) };
};


export default function Alerts() {
  const { data: alertsData = [], isLoading: isLoadingAlerts } = useAlerts();
  
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [selectedType, setSelectedType] = useState("all");
  const [selectedSeverity, setSelectedSeverity] = useState("all");
  const [selectedZone, setSelectedZone] = useState("all");
  const [selectedWard, setSelectedWard] = useState("all");
  const [selectedStartDate, setSelectedStartDate] = useState(() => getDefaultDateRange().start);
  const [selectedEndDate, setSelectedEndDate] = useState(() => getDefaultDateRange().end);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedAlert, setSelectedAlert] = useState<AlertItem | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  useEffect(() => {
    // Validate and map API data to ensure all fields exist
    const validatedAlerts = alertsData.map((item: any) => ({
      id: item.id || Math.random(),
      type: item.type || item.alert_type || "route_deviation",
      truck: item.truck_registration_number || item.registration_number || item.truck || item.truck_number || item.truck_id || "UNKNOWN",
      route: item.route_name || item.route || item.route_id || "Unknown Route",
      driver: item.driver || item.driver_name || "Unknown",
      driverPhone: item.driverPhone || item.driver_phone || "",
      vendorName: item.vendorName || item.vendor_name || "Unknown",
      vendorPhone: item.vendorPhone || item.vendor_phone || "",
      message: item.message || item.alert_message || "",
      location: item.location || item.coordinates || "0,0",
      date: item.date || (item.timestamp ? item.timestamp.split(" ")[0] : formatDate(new Date())),
      time: item.time || (item.created_at ? new Date(item.created_at).toLocaleTimeString() : "unknown"),
      timestamp: item.timestamp || item.created_at || "unknown",
      severity: item.severity || "medium",
      zone: item.zone_name || item.zone || item.zone_id || "Unknown Zone",
      ward: item.ward_name || item.ward || item.ward_id || "Unknown Ward",
      status: item.status || "active",
    })) as AlertItem[];
    setAlerts(validatedAlerts);
  }, [alertsData]);

  const alertTypeOptions = useMemo(() => {
    const types = Array.from(new Set(alerts.map((alert) => alert.type).filter(Boolean)));
    return types.sort().map((type) => ({
      id: type,
      label: alertTypeMeta[type]?.label ?? toTitleCase(type),
      icon: alertTypeMeta[type]?.icon ?? Bell,
    }));
  }, [alerts]);

  const alertTypeSelectOptions = useMemo(
    () => [{ id: "all", label: "All Alerts", icon: Bell }, ...alertTypeOptions],
    [alertTypeOptions]
  );

  const severityOptions = useMemo(() => {
    const severities = Array.from(new Set(alerts.map((alert) => alert.severity).filter(Boolean)));
    return severities.sort();
  }, [alerts]);

  const zoneOptions = useMemo(() => {
    const zones = Array.from(new Set(alerts.map((alert) => alert.zone).filter(Boolean)));
    return zones.sort();
  }, [alerts]);

  const wardOptions = useMemo(() => {
    const wards = Array.from(new Set(alerts.map((alert) => alert.ward).filter(Boolean)));
    return wards.sort();
  }, [alerts]);

  const getAlertIcon = (type: string) => {
    switch (type) {
      case "route_deviation": return Navigation;
      case "missed_pickup": return MapPinOff;
      case "unauthorized_halt": return Clock;
      case "speed_violation": return Gauge;
      case "geofence_breach": return Shield;
      case "device_tamper": return AlertTriangle;
      default: return Bell;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical": return "bg-destructive/10 text-destructive border-destructive/30";
      case "high": return "bg-orange-500/10 text-orange-500 border-orange-500/30";
      case "medium": return "bg-warning/10 text-warning border-warning/30";
      case "low": return "bg-muted text-muted-foreground border-border";
      default: return "bg-muted text-muted-foreground border-border";
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active": return "bg-destructive/10 text-destructive";
      case "acknowledged": return "bg-warning/10 text-warning";
      case "investigating": return "bg-blue-500/10 text-blue-500";
      case "resolved": return "bg-emerald-500/10 text-emerald-500";
      default: return "bg-muted text-muted-foreground";
    }
  };

  const filteredAlerts = alerts.filter((alert) => {
    const matchesType = selectedType === "all" || (alert.type || "") === selectedType;
    const matchesSeverity = selectedSeverity === "all" || (alert.severity || "") === selectedSeverity;
    const matchesZone = selectedZone === "all" || (alert.zone || "") === selectedZone;
    const matchesWard = selectedWard === "all" || (alert.ward || "") === selectedWard;
    const hasDateRange = Boolean(selectedStartDate && selectedEndDate);
    const matchesDateRange = !hasDateRange || ((alert.date || "") >= selectedStartDate && (alert.date || "") <= selectedEndDate);
    const matchesSearch = searchQuery === "" || 
      (alert.truck || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (alert.driver || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (alert.message || "").toLowerCase().includes(searchQuery.toLowerCase());
    return matchesType && matchesSeverity && matchesZone && matchesWard && matchesDateRange && matchesSearch;
  });

  const alertDistribution = useMemo(() => {
    const counts: Record<string, number> = {};
    filteredAlerts.forEach((alert) => {
      const type = alert.type || "unknown";
      counts[type] = (counts[type] || 0) + 1;
    });

    const typeOrder = Object.keys(alertTypeMeta);
    const extraTypes = Object.keys(counts).filter((type) => !typeOrder.includes(type)).sort();
    const orderedTypes = [...typeOrder.filter((type) => counts[type]), ...extraTypes];
    const colors = [
      "hsl(var(--chart-1))",
      "hsl(var(--chart-2))",
      "hsl(var(--chart-3))",
      "hsl(var(--chart-4))",
      "hsl(var(--chart-5))",
      "hsl(var(--destructive))",
    ];

    return orderedTypes.map((type, index) => ({
      name: alertTypeMeta[type]?.label ?? toTitleCase(type),
      value: counts[type] || 0,
      color: colors[index % colors.length],
    }));
  }, [filteredAlerts]);

  const alertTrendData = useMemo(() => {
    const trendTypeMap: Record<string, string> = {
      route_deviation: "routeDeviation",
      missed_pickup: "missedPickup",
      speed_violation: "speedViolation",
      geofence_breach: "geofenceBreach",
    };
    const targetDate = selectedEndDate || formatDate(new Date());
    const formatHour = (hour: number) => {
      const period = hour >= 12 ? "PM" : "AM";
      const value = hour % 12 || 12;
      return `${value} ${period}`;
    };

    const buckets = Array.from({ length: 24 }, (_, hour) => ({
      time: formatHour(hour),
      routeDeviation: 0,
      missedPickup: 0,
      speedViolation: 0,
      geofenceBreach: 0,
      other: 0,
    }));

    filteredAlerts.forEach((alert) => {
      const alertDate = alert.date || "";
      if (alertDate !== targetDate) {
        return;
      }

      let timestampValue = alert.timestamp || "";
      if (timestampValue && timestampValue.includes(" ")) {
        timestampValue = timestampValue.replace(" ", "T");
      }
      const parsedDate = timestampValue ? new Date(timestampValue) : new Date(`${alertDate}T00:00:00`);
      if (Number.isNaN(parsedDate.getTime())) {
        return;
      }

      const hour = parsedDate.getHours();
      const mappedKey = trendTypeMap[alert.type || ""];
      if (mappedKey && buckets[hour]) {
        buckets[hour][mappedKey] += 1;
      } else if (buckets[hour]) {
        buckets[hour].other += 1;
      }
    });

    return buckets;
  }, [filteredAlerts, selectedEndDate]);

  const zoneAlertData = useMemo(() => {
    const zoneMap: Record<string, { zone: string; critical: number; high: number; medium: number; low: number }> = {};
    filteredAlerts.forEach((alert) => {
      const zone = alert.zone || "Unknown Zone";
      if (!zoneMap[zone]) {
        zoneMap[zone] = { zone, critical: 0, high: 0, medium: 0, low: 0 };
      }
      const severity = alert.severity || "low";
      if (severity in zoneMap[zone]) {
        zoneMap[zone][severity as "critical" | "high" | "medium" | "low"] += 1;
      }
    });

    return Object.values(zoneMap).sort((a, b) => a.zone.localeCompare(b.zone));
  }, [filteredAlerts]);

  const criticalCount = alerts.filter(a => a.severity === "critical").length;
  const highCount = alerts.filter(a => a.severity === "high").length;
  const resolvedToday = 24;
  const avgResponseTime = "4.2 min";

  const handleViewDetails = (alert: AlertItem) => {
    setSelectedAlert(alert);
    setIsDetailOpen(true);
  };

  const handleExportAlerts = () => {
    const csvContent = [
      ["ID", "Type", "Truck", "Driver", "Message", "Zone", "Severity", "Status", "Time"].join(","),
      ...filteredAlerts.map(alert => 
        [alert.id || "", alert.type || "", alert.truck || "", alert.driver || "", `"${alert.message || ""}"`, alert.zone || "", alert.severity || "", alert.status || "", alert.timestamp || ""].join(",")
      )
    ].join("\n");
    
    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "alerts_export.csv";
    a.click();
  };

  return (
    <div className="w-full h-full overflow-auto">
      <div className="container mx-auto px-4 py-6 space-y-6">
        {/* Header */}
        <PageHeader
          category="Monitoring"
          title="Alerts & Violations"
          description="Real-time monitoring of route deviations, missed pickups, and violations"
          icon={AlertTriangle}
          badge={{
            label: `${alerts.filter(a => a.status === "active").length} Active`,
            className: "bg-destructive/10 text-destructive animate-pulse",
          }}
          actions={
            <>
              <Button variant="outline" size="sm" onClick={handleExportAlerts}>
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
              <Button variant="outline" size="sm">
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
            </>
          }
        />

        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="p-4 border-l-4 border-l-destructive">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Critical Alerts</p>
                <p className="text-2xl font-bold text-destructive">{criticalCount}</p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-destructive/10 flex items-center justify-center">
                <AlertTriangle className="h-6 w-6 text-destructive" />
              </div>
            </div>
            <div className="mt-2 flex items-center gap-1 text-xs text-destructive">
              <TrendingUp className="h-3 w-3" />
              <span>+2 from last hour</span>
            </div>
          </Card>

          <Card className="p-4 border-l-4 border-l-orange-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">High Priority</p>
                <p className="text-2xl font-bold text-orange-500">{highCount}</p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-orange-500/10 flex items-center justify-center">
                <Bell className="h-6 w-6 text-orange-500" />
              </div>
            </div>
            <div className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
              <TrendingDown className="h-3 w-3 text-emerald-500" />
              <span>-3 from last hour</span>
            </div>
          </Card>

          <Card className="p-4 border-l-4 border-l-emerald-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Resolved Today</p>
                <p className="text-2xl font-bold text-emerald-500">{resolvedToday}</p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                <CheckCircle className="h-6 w-6 text-emerald-500" />
              </div>
            </div>
            <div className="mt-2 flex items-center gap-1 text-xs text-emerald-500">
              <TrendingUp className="h-3 w-3" />
              <span>85% resolution rate</span>
            </div>
          </Card>

          <Card className="p-4 border-l-4 border-l-blue-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Avg Response Time</p>
                <p className="text-2xl font-bold text-blue-500">{avgResponseTime}</p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-blue-500/10 flex items-center justify-center">
                <Zap className="h-6 w-6 text-blue-500" />
              </div>
            </div>
            <div className="mt-2 flex items-center gap-1 text-xs text-emerald-500">
              <TrendingDown className="h-3 w-3" />
              <span>-30s improvement</span>
            </div>
          </Card>
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue="live" className="space-y-4">
          <TabsList className="bg-muted/50 p-1">
            <TabsTrigger value="live" className="data-[state=active]:bg-background">
              <Zap className="h-4 w-4 mr-2" />
              Live Alerts
            </TabsTrigger>
            <TabsTrigger value="analytics" className="data-[state=active]:bg-background">
              <TrendingUp className="h-4 w-4 mr-2" />
              Analytics
            </TabsTrigger>
          </TabsList>

        {/* Live Alerts Tab */}
        <TabsContent value="live" className="space-y-4">
          {/* Filters */}
          <Card className="p-4">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by truck, driver, or message..."
                  className="pl-10"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <Input
                  type="date"
                  className="w-[140px]"
                  value={selectedStartDate}
                  onChange={(e) => setSelectedStartDate(e.target.value)}
                  max={selectedEndDate}
                />
                <Input
                  type="date"
                  className="w-[140px]"
                  value={selectedEndDate}
                  onChange={(e) => setSelectedEndDate(e.target.value)}
                  min={selectedStartDate}
                />
                <Select value={selectedType} onValueChange={setSelectedType}>
                  <SelectTrigger className="w-[160px]">
                    <Filter className="h-4 w-4 mr-2" />
                    <SelectValue placeholder="Alert Type" />
                  </SelectTrigger>
                  <SelectContent>
                    {alertTypeSelectOptions.map((type) => (
                      <SelectItem key={type.id} value={type.id}>
                        {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={selectedSeverity} onValueChange={setSelectedSeverity}>
                  <SelectTrigger className="w-[140px]">
                    <SelectValue placeholder="Severity" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Severity</SelectItem>
                    {severityOptions.map((severity) => (
                      <SelectItem key={severity} value={severity}>
                        {toTitleCase(severity)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={selectedZone} onValueChange={setSelectedZone}>
                  <SelectTrigger className="w-[130px]">
                    <SelectValue placeholder="Zone" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Zones</SelectItem>
                    {zoneOptions.map((zone) => (
                      <SelectItem key={zone} value={zone}>
                        {zone}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={selectedWard} onValueChange={setSelectedWard}>
                  <SelectTrigger className="w-[140px]">
                    <SelectValue placeholder="Ward" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Wards</SelectItem>
                    {wardOptions.map((ward) => (
                      <SelectItem key={ward} value={ward}>
                        {ward}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </Card>

          {/* Alert Type Pills */}
          <div className="flex flex-wrap gap-2">
            {alertTypeSelectOptions.map((type) => {
              const Icon = type.icon;
              const count = type.id === "all" 
                ? alerts.length 
                : alerts.filter(a => a.type === type.id).length;
              return (
                <Button
                  key={type.id}
                  variant={selectedType === type.id ? "default" : "outline"}
                  size="sm"
                  onClick={() => setSelectedType(type.id)}
                  className="gap-2"
                >
                  <Icon className="h-4 w-4" />
                  {type.label}
                  <Badge variant="secondary" className="ml-1 h-5 px-1.5">
                    {count}
                  </Badge>
                </Button>
              );
            })}
          </div>

          {/* Alerts List */}
          <Card className="overflow-hidden">
            <ScrollArea className="h-[500px]">
              <div className="p-4 space-y-3">
                {filteredAlerts.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <BellOff className="h-12 w-12 mb-4" />
                    <p className="text-lg font-medium">No alerts found</p>
                    <p className="text-sm">Try adjusting your filters</p>
                  </div>
                ) : (
                  filteredAlerts.map((alert) => {
                    const Icon = getAlertIcon(alert.type || "");
                    return (
                      <Card
                        key={alert.id}
                        className={`p-4 border-l-4 hover:shadow-lg transition-all cursor-pointer ${
                          alert.severity === "critical" ? "border-l-destructive" :
                          alert.severity === "high" ? "border-l-orange-500" :
                          alert.severity === "medium" ? "border-l-warning" : "border-l-border"
                        }`}
                        onClick={() => handleViewDetails(alert)}
                      >
                        <div className="flex gap-4">
                          <div className="flex-shrink-0">
                            <div className={`h-10 w-10 rounded-xl flex items-center justify-center ${
                              alert.severity === "critical" ? "bg-destructive/10" :
                              alert.severity === "high" ? "bg-orange-500/10" :
                              alert.severity === "medium" ? "bg-warning/10" : "bg-muted"
                            }`}>
                              <Icon className={`h-5 w-5 ${
                                alert.severity === "critical" ? "text-destructive" :
                                alert.severity === "high" ? "text-orange-500" :
                                alert.severity === "medium" ? "text-warning" : "text-muted-foreground"
                              }`} />
                            </div>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-2 mb-2">
                              <div className="flex items-center gap-3 flex-wrap">
                                <span className="font-semibold text-foreground flex items-center gap-1">
                                  <Truck className="h-4 w-4" />
                                  {alert.truck}
                                </span>
                                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                                  Route: {alert.route}
                                </span>
                                <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">
                                  {alert.zone} • {alert.ward}
                                </span>
                              </div>
                              <div className="flex items-center gap-2 flex-shrink-0">
                                <Badge variant="outline" className={getSeverityColor(alert.severity)}>
                                  {alert.severity}
                                </Badge>
                                <Badge variant="secondary" className={getStatusColor(alert.status)}>
                                  {alert.status}
                                </Badge>
                              </div>
                            </div>
                            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                              <span>{alert.driver}</span>
                              <span>•</span>
                              <Phone className="h-3 w-3" />
                              <span>{alert.driverPhone}</span>
                            </div>
                            <p className="text-sm text-foreground mb-2">{alert.message}</p>
                            <div className="flex items-center gap-4 text-xs text-muted-foreground flex-wrap">
                              <span className="flex items-center gap-1">
                                <Calendar className="h-3 w-3" />
                                {alert.date}
                              </span>
                              <span className="flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                {alert.time}
                              </span>
                              <span className="flex items-center gap-1">
                                <MapPin className="h-3 w-3" />
                                {alert.zone}
                              </span>
                              <span className="flex items-center gap-1">
                                <Shield className="h-3 w-3" />
                                {alert.ward}
                              </span>
                            </div>
                          </div>
                          <div className="flex-shrink-0 flex items-center gap-2">
                            <ActionDropdown
                              truckId={alert.truck}
                              driverName={alert.driver}
                              driverPhone={alert.driverPhone}
                              vendorName={alert.vendorName}
                              vendorPhone={alert.vendorPhone}
                              alertType={(alert.type || "").replace(/_/g, " ").toUpperCase()}
                              alertMessage={alert.message}
                              size="sm"
                            />
                            <Button variant="ghost" size="sm">
                              <Eye className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </Card>
                    );
                  })
                )}
              </div>
            </ScrollArea>
          </Card>
        </TabsContent>

        {/* Analytics Tab */}
        <TabsContent value="analytics" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Alert Trend Chart */}
            <Card className="p-4">
              <h3 className="text-lg font-semibold mb-4">Alert Trend Today</h3>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={alertTrendData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="time" className="text-xs" />
                    <YAxis className="text-xs" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: "hsl(var(--background))", 
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px"
                      }} 
                    />
                    <Area type="monotone" dataKey="routeDeviation" stackId="1" stroke="hsl(var(--chart-1))" fill="hsl(var(--chart-1))" fillOpacity={0.6} name="Route Deviation" />
                    <Area type="monotone" dataKey="missedPickup" stackId="1" stroke="hsl(var(--chart-2))" fill="hsl(var(--chart-2))" fillOpacity={0.6} name="Missed Pickup" />
                    <Area type="monotone" dataKey="speedViolation" stackId="1" stroke="hsl(var(--chart-3))" fill="hsl(var(--chart-3))" fillOpacity={0.6} name="Speed Violation" />
                    <Area type="monotone" dataKey="geofenceBreach" stackId="1" stroke="hsl(var(--chart-4))" fill="hsl(var(--chart-4))" fillOpacity={0.6} name="Geofence Breach" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Alert Distribution Pie */}
            <Card className="p-4">
              <h3 className="text-lg font-semibold mb-4">Alert Distribution</h3>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={alertDistribution}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {alertDistribution.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: "hsl(var(--background))", 
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px"
                      }} 
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Zone Alert Comparison */}
            <Card className="p-4 lg:col-span-2">
              <h3 className="text-lg font-semibold mb-4">Alerts by Zone & Severity</h3>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={zoneAlertData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="zone" className="text-xs" />
                    <YAxis className="text-xs" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: "hsl(var(--background))", 
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px"
                      }} 
                    />
                    <Legend />
                    <Bar dataKey="critical" fill="hsl(var(--destructive))" name="Critical" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="high" fill="hsl(32, 95%, 44%)" name="High" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="medium" fill="hsl(var(--warning))" name="Medium" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="low" fill="hsl(var(--muted-foreground))" name="Low" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Alert Detail Dialog */}
      <Dialog open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedAlert && (
                <>
                  {(() => {
                    const Icon = getAlertIcon(selectedAlert.type || "");
                    return <Icon className="h-5 w-5 text-destructive" />;
                  })()}
                  Alert Details
                </>
              )}
            </DialogTitle>
            <DialogDescription>
              Complete information about this alert
            </DialogDescription>
          </DialogHeader>
          {selectedAlert && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Truck</p>
                  <p className="font-semibold">{selectedAlert.truck}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Route</p>
                  <p className="font-semibold">{selectedAlert.route}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Driver</p>
                  <p className="font-semibold">{selectedAlert.driver}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Driver Phone</p>
                  <p className="font-semibold">{selectedAlert.driverPhone}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Zone</p>
                  <p className="font-semibold">{selectedAlert.zone}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Ward</p>
                  <p className="font-semibold">{selectedAlert.ward}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Date</p>
                  <p className="font-semibold flex items-center gap-1">
                    <Calendar className="h-4 w-4" />
                    {selectedAlert.date}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Time</p>
                  <p className="font-semibold flex items-center gap-1">
                    <Clock className="h-4 w-4" />
                    {selectedAlert.time}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Severity</p>
                  <Badge variant="outline" className={getSeverityColor(selectedAlert.severity)}>
                    {selectedAlert.severity}
                  </Badge>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  <Badge variant="outline" className={getStatusColor(selectedAlert.status)}>
                    {selectedAlert.status}
                  </Badge>
                </div>
                <div className="col-span-2">
                  <p className="text-sm text-muted-foreground">Location</p>
                  <p className="font-semibold flex items-center gap-1">
                    <MapPin className="h-4 w-4" />
                    {selectedAlert.location}
                  </p>
                </div>
                <div className="col-span-2">
                  <p className="text-sm text-muted-foreground">Timestamp</p>
                  <p className="font-semibold flex items-center gap-1">
                    <Calendar className="h-4 w-4" />
                    {selectedAlert.timestamp}
                  </p>
                </div>
              </div>
              <div className="p-3 bg-muted/50 rounded-lg">
                <p className="text-sm text-muted-foreground mb-1">Alert Message</p>
                <p className="text-foreground">{selectedAlert.message}</p>
              </div>
            </div>
          )}
          <DialogFooter className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => setIsDetailOpen(false)}>
              Close
            </Button>
            {selectedAlert && (
              <ActionDropdown
                truckId={selectedAlert.truck}
                driverName={selectedAlert.driver}
                driverPhone={selectedAlert.driverPhone}
                vendorName={selectedAlert.vendorName}
                vendorPhone={selectedAlert.vendorPhone}
                alertType={(selectedAlert.type || "").replace(/_/g, " ").toUpperCase()}
                alertMessage={selectedAlert.message}
              />
            )}
            <Button variant="secondary">
              <CheckCircle className="h-4 w-4 mr-2" />
              Acknowledge
            </Button>
            <Button>
              <Navigation className="h-4 w-4 mr-2" />
              View on Map
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      </div>
    </div>
  );
}
