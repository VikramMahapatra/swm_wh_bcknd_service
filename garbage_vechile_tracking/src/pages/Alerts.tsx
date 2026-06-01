import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Bell,
  CheckCircle,
  Clock,
  Download,
  Eye,
  Filter,
  Gauge,
  Loader2,
  MapPin,
  Navigation,
  RefreshCw,
  Search,
  Shield,
  Truck,
  Zap,
} from "lucide-react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { ActionDropdown } from "@/components/ActionDropdown";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { apiService } from "@/services/api";

type AlertRow = {
  id: string;
  alert_type?: string;
  category?: string;
  title?: string;
  message?: string | null;
  severity?: string;
  status?: string;
  vehicle_id?: string | null;
  imei?: string | null;
  route_id?: string | null;
  ward_id?: string | null;
  triggered_at?: string;
  acknowledged_at?: string | null;
  resolved_at?: string | null;
  acknowledged_by?: string | null;
  resolved_by?: string | null;
  metadata?: Record<string, any>;
  metadata_json?: Record<string, any>;
};

const alertMeta: Record<string, { label: string; icon: typeof Bell }> = {
  route_deviation: { label: "Route Deviation", icon: Navigation },
  missed_pickup: { label: "Missed Pickup", icon: MapPin },
  unauthorized_stop: { label: "Unauthorized Stop", icon: Clock },
  unauthorized_halt: { label: "Unauthorized Halt", icon: Clock },
  excessive_idle: { label: "Excessive Idle", icon: Clock },
  speed_anomaly: { label: "Speed Anomaly", icon: Gauge },
  speed_violation: { label: "Speed Violation", icon: Gauge },
  geofence_breach: { label: "Geofence Breach", icon: Shield },
  gps_signal_loss: { label: "GPS Signal Loss", icon: AlertTriangle },
  vehicle_offline: { label: "Vehicle Offline", icon: Truck },
};

const titleCase = (value: string) => value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
const dateOnly = (value: Date) => value.toISOString().slice(0, 10);
const defaultStartDate = () => {
  const value = new Date();
  value.setDate(value.getDate() - 7);
  return dateOnly(value);
};

const formatDateTime = (value?: string | null) => {
  if (!value) return "-";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
};

const formatMetadataValue = (value: unknown): string => {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map(formatMetadataValue).join(", ");
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    if (record.lat !== undefined && record.lng !== undefined) return `${record.lat}, ${record.lng}`;
    return JSON.stringify(value);
  }
  return String(value);
};

const alertTimestamp = (alert: AlertRow) => alert.triggered_at || "";
const alertType = (alert: AlertRow) => alert.alert_type || alert.category || "alert";
const alertVehicle = (alert: AlertRow) => alert.vehicle_id || alert.imei || "-";
const alertMetadata = (alert: AlertRow) => alert.metadata || alert.metadata_json || {};
const alertLocation = (alert: AlertRow) => {
  const meta = alertMetadata(alert);
  if (meta.location || meta.coordinates) return formatMetadataValue(meta.location || meta.coordinates);
  if (meta.lat && meta.lng) return `${meta.lat}, ${meta.lng}`;
  return "-";
};

const getSeverityColor = (severity?: string) => {
  switch (severity) {
    case "critical": return "bg-destructive/10 text-destructive border-destructive/30";
    case "high": return "bg-orange-500/10 text-orange-600 border-orange-500/30";
    case "medium": return "bg-warning/10 text-warning border-warning/30";
    default: return "bg-muted text-muted-foreground border-border";
  }
};

const getStatusColor = (status?: string) => {
  switch (status) {
    case "open": return "bg-destructive/10 text-destructive";
    case "acknowledged": return "bg-warning/10 text-warning";
    case "escalated": return "bg-orange-500/10 text-orange-600";
    case "resolved": return "bg-emerald-500/10 text-emerald-600";
    default: return "bg-muted text-muted-foreground";
  }
};

export default function Alerts() {
  const queryClient = useQueryClient();
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [selectedSeverity, setSelectedSeverity] = useState("all");
  const [selectedType, setSelectedType] = useState("all");
  const [selectedZone, setSelectedZone] = useState("all");
  const [selectedWard, setSelectedWard] = useState("all");
  const [selectedRoute, setSelectedRoute] = useState("all");
  const [activeTab, setActiveTab] = useState("live");
  const [selectedStartDate, setSelectedStartDate] = useState(defaultStartDate);
  const [selectedEndDate, setSelectedEndDate] = useState(() => dateOnly(new Date()));
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedAlert, setSelectedAlert] = useState<AlertRow | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const { data: zones = [] } = useQuery({
    queryKey: ["zones", "alert-filters"],
    queryFn: () => apiService.getZones(),
    staleTime: 5 * 60 * 1000,
  });

  const { data: wards = [] } = useQuery({
    queryKey: ["wards", "alert-filters", selectedZone],
    queryFn: () => selectedZone === "all" ? apiService.getWards() : apiService.getZoneWards(selectedZone),
    staleTime: 5 * 60 * 1000,
  });

  const { data: routes = [] } = useQuery({
    queryKey: ["routes", "alert-filters", selectedZone, selectedWard],
    queryFn: () => apiService.getRoutes({
      zone_id: selectedZone === "all" ? undefined : selectedZone,
      ward_id: selectedWard === "all" ? undefined : selectedWard,
    }),
    staleTime: 5 * 60 * 1000,
  });

  const { data: alertsPage = {}, isLoading, isFetching } = useQuery({
    queryKey: ["alerts", "page", selectedStatus, selectedSeverity, selectedType, selectedZone, selectedWard, selectedRoute, selectedStartDate, selectedEndDate, searchQuery, currentPage, pageSize],
    queryFn: () => apiService.getAlertsPage({
      status: selectedStatus === "all" ? undefined : selectedStatus,
      severity: selectedSeverity === "all" ? undefined : selectedSeverity,
      alert_type: selectedType === "all" ? undefined : selectedType,
      zone_id: selectedZone === "all" ? undefined : selectedZone,
      ward_id: selectedWard === "all" ? undefined : selectedWard,
      route_id: selectedRoute === "all" ? undefined : selectedRoute,
      search: searchQuery.trim() || undefined,
      date_from: selectedStartDate,
      date_to: selectedEndDate,
      page: currentPage,
      page_size: pageSize,
    }),
    refetchInterval: 30 * 1000,
    staleTime: 20 * 1000,
  });
  const alerts = (alertsPage.items || []) as AlertRow[];

  const { data: summary = {} } = useQuery({
    queryKey: ["alerts", "summary"],
    queryFn: () => apiService.getAlertSummary(),
    refetchInterval: 30 * 1000,
    staleTime: 20 * 1000,
  });

  const invalidateAlerts = () => {
    queryClient.invalidateQueries({ queryKey: ["alerts"] });
  };

  const acknowledgeMutation = useMutation({
    mutationFn: (alertId: string) => apiService.acknowledgeAlert(alertId, "Acknowledged from Alerts page"),
    onSuccess: invalidateAlerts,
  });
  const resolveMutation = useMutation({
    mutationFn: (alertId: string) => apiService.resolveAlert(alertId, "Resolved from Alerts page"),
    onSuccess: invalidateAlerts,
  });
  const escalateMutation = useMutation({
    mutationFn: (alertId: string) => apiService.escalateAlert(alertId, "Escalated from Alerts page"),
    onSuccess: invalidateAlerts,
  });

  const filteredAlerts = alerts;

  const alertTypes = useMemo(() => {
    const values = Array.from(new Set([...(alertsPage.types || []), ...alerts.map(alertType)].filter(Boolean)));
    return values.sort();
  }, [alerts, alertsPage.types]);

  const bySeverity = alertsPage.counts?.bySeverity || {};
  const byStatus = alertsPage.counts?.byStatus || {};
  const visibleCounts = {
    active: Number(alertsPage.total || 0) - Number(byStatus.resolved || 0),
    critical: Number(bySeverity.critical || 0),
    high: Number(bySeverity.high || 0),
    resolved: Number(byStatus.resolved || 0),
    total: Number(alertsPage.total || 0),
  };
  const activeCount = visibleCounts.active;
  const criticalCount = visibleCounts.critical;
  const highCount = visibleCounts.high;
  const resolvedCount = visibleCounts.resolved;

  const totalPages = Number(alertsPage.total_pages || 1);
  const paginatedAlerts = alerts;
  const pageStart = visibleCounts.total === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const pageEnd = Math.min(currentPage * pageSize, visibleCounts.total);
  const selectedPeriodLabel = selectedStartDate === selectedEndDate
    ? `For ${selectedEndDate}`
    : `For ${selectedStartDate} to ${selectedEndDate}`;
  const selectedPeriodShortLabel = selectedStartDate === selectedEndDate ? "1 day" : "selected date range";

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, selectedEndDate, selectedRoute, selectedSeverity, selectedStartDate, selectedStatus, selectedType, selectedWard, selectedZone]);

  useEffect(() => {
    setSelectedWard("all");
    setSelectedRoute("all");
  }, [selectedZone]);

  useEffect(() => {
    setSelectedRoute("all");
  }, [selectedWard]);

  useEffect(() => {
    if (currentPage > totalPages) setCurrentPage(totalPages);
  }, [currentPage, totalPages]);

  const distribution = useMemo(() => {
    const counts: Record<string, number> = {};
    filteredAlerts.forEach((alert) => {
      const type = alertType(alert);
      counts[type] = (counts[type] || 0) + 1;
    });
    const colors = ["hsl(var(--chart-1))", "hsl(var(--chart-2))", "hsl(var(--chart-3))", "hsl(var(--chart-4))", "hsl(var(--destructive))"];
    return Object.entries(counts).map(([name, value], index) => ({
      name: alertMeta[name]?.label || titleCase(name),
      value,
      color: colors[index % colors.length],
    }));
  }, [filteredAlerts]);

  const severityBreakdown = useMemo(() => {
    const rows = [
      { key: "critical", label: "Critical", value: Number(bySeverity.critical || 0), color: "hsl(var(--destructive))" },
      { key: "high", label: "High", value: Number(bySeverity.high || 0), color: "#f97316" },
      { key: "medium", label: "Medium", value: Number(bySeverity.medium || 0), color: "hsl(var(--warning))" },
      { key: "low", label: "Low", value: Number(bySeverity.low || 0), color: "hsl(var(--muted-foreground))" },
    ];
    const total = rows.reduce((sum, row) => sum + row.value, 0);
    return rows.map((row) => ({ ...row, percent: total ? Math.round((row.value / total) * 100) : 0 }));
  }, [bySeverity.critical, bySeverity.high, bySeverity.low, bySeverity.medium]);

  const statusBreakdown = useMemo(() => {
    const rows = [
      { key: "open", label: "Open", value: Number(byStatus.open || 0), color: "hsl(var(--destructive))" },
      { key: "acknowledged", label: "Acknowledged", value: Number(byStatus.acknowledged || 0), color: "hsl(var(--warning))" },
      { key: "escalated", label: "Escalated", value: Number(byStatus.escalated || 0), color: "#f97316" },
      { key: "resolved", label: "Resolved", value: Number(byStatus.resolved || 0), color: "#10b981" },
    ];
    const total = rows.reduce((sum, row) => sum + row.value, 0);
    return rows.map((row) => ({ ...row, percent: total ? Math.round((row.value / total) * 100) : 0 }));
  }, [byStatus.acknowledged, byStatus.escalated, byStatus.open, byStatus.resolved]);

  const trend = useMemo(() => {
    const buckets = Array.from({ length: 24 }, (_, hour) => ({ hour: `${hour}:00`, critical: 0, high: 0, medium: 0, low: 0 }));
    const targetDate = selectedEndDate;
    filteredAlerts.forEach((alert) => {
      const ts = alertTimestamp(alert);
      if (!ts.startsWith(targetDate)) return;
      const parsed = new Date(ts);
      if (Number.isNaN(parsed.getTime())) return;
      const severity = (alert.severity || "low") as "critical" | "high" | "medium" | "low";
      buckets[parsed.getHours()][severity] += 1;
    });
    return buckets;
  }, [filteredAlerts, selectedEndDate]);

  const zoneRows = useMemo(() => {
    const rows: Record<string, any> = {};
    filteredAlerts.forEach((alert) => {
      const meta = alertMetadata(alert);
      const zone = meta.zone || meta.zone_name || alert.ward_id || "Unmapped";
      rows[zone] ||= { zone, critical: 0, high: 0, medium: 0, low: 0 };
      const severity = alert.severity || "low";
      if (severity in rows[zone]) rows[zone][severity] += 1;
    });
    return Object.values(rows);
  }, [filteredAlerts]);

  const topFocusRows = useMemo(() => {
    return [...zoneRows]
      .map((row: any) => ({
        ...row,
        total: Number(row.critical || 0) + Number(row.high || 0) + Number(row.medium || 0) + Number(row.low || 0),
        risk: Number(row.critical || 0) * 4 + Number(row.high || 0) * 3 + Number(row.medium || 0) * 2 + Number(row.low || 0),
      }))
      .sort((a: any, b: any) => b.risk - a.risk)
      .slice(0, 6);
  }, [zoneRows]);

  const handleExportAlerts = () => {
    const csvContent = [
      ["ID", "Type", "Title", "Vehicle", "Severity", "Status", "Triggered At", "Message"].join(","),
      ...filteredAlerts.map((alert) => [
        alert.id,
        alertType(alert),
        `"${alert.title || ""}"`,
        alertVehicle(alert),
        alert.severity || "",
        alert.status || "",
        alert.triggered_at || "",
        `"${alert.message || ""}"`,
      ].join(",")),
    ].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `alerts_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const drillToLive = (updates: { severity?: string; status?: string; type?: string; search?: string }) => {
    if (updates.severity) setSelectedSeverity(updates.severity);
    if (updates.status) setSelectedStatus(updates.status);
    if (updates.type) setSelectedType(updates.type);
    if (updates.search !== undefined) setSearchQuery(updates.search);
    setCurrentPage(1);
    setActiveTab("live");
  };

  const renderActions = (alert: AlertRow) => {
    const busy = acknowledgeMutation.isPending || resolveMutation.isPending || escalateMutation.isPending;
    return (
      <div className="flex flex-nowrap items-center justify-end gap-2">
        {alert.status === "open" && (
          <Button size="sm" variant="outline" className="h-8 whitespace-nowrap px-3 text-xs" disabled={busy} onClick={() => acknowledgeMutation.mutate(alert.id)}>
            Ack
          </Button>
        )}
        {alert.status !== "resolved" && (
          <Button size="sm" variant="outline" className="h-8 whitespace-nowrap px-3 text-xs" disabled={busy} onClick={() => escalateMutation.mutate(alert.id)}>
            Esc
          </Button>
        )}
        {alert.status !== "resolved" && (
          <Button size="sm" className="h-8 whitespace-nowrap px-3 text-xs" disabled={busy} onClick={() => resolveMutation.mutate(alert.id)}>
            Resolve
          </Button>
        )}
      </div>
    );
  };

  return (
    <div className="w-full h-full overflow-auto">
      <div className="container mx-auto px-4 py-6 space-y-6">
        <PageHeader
          category="Monitoring"
          title="Alerts Command Center"
          description="Real alerts from operations, analytics, GPS, SLA and fleet monitoring"
          icon={AlertTriangle}
          badge={{ label: `${activeCount} Active`, className: activeCount > 0 ? "bg-destructive/10 text-destructive animate-pulse" : "bg-emerald-500/10 text-emerald-600" }}
          actions={
            <>
              <Button variant="outline" size="sm" onClick={handleExportAlerts}>
                <Download className="h-4 w-4 mr-2" /> Export
              </Button>
              <Button variant="outline" size="sm" onClick={invalidateAlerts} disabled={isFetching}>
                <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? "animate-spin" : ""}`} /> Refresh
              </Button>
            </>
          }
        />

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="relative overflow-hidden border-l-4 border-l-destructive bg-gradient-to-br from-destructive/8 via-background to-background p-5 shadow-sm">
            <div className="absolute -right-8 -top-8 h-24 w-24 rounded-full bg-destructive/10" />
            <div className="relative flex items-center justify-between gap-4">
              <div><p className="text-sm font-medium text-muted-foreground">Critical Alerts</p><p className="text-3xl font-bold text-destructive">{criticalCount}</p><p className="mt-1 text-[11px] uppercase tracking-wide text-muted-foreground">current filters</p></div>
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-destructive/10"><AlertTriangle className="h-7 w-7 text-destructive" /></div>
            </div>
          </Card>
          <Card className="relative overflow-hidden border-l-4 border-l-orange-500 bg-gradient-to-br from-orange-500/10 via-background to-background p-5 shadow-sm">
            <div className="absolute -right-8 -top-8 h-24 w-24 rounded-full bg-orange-500/10" />
            <div className="relative flex items-center justify-between gap-4">
              <div><p className="text-sm font-medium text-muted-foreground">High Priority</p><p className="text-3xl font-bold text-orange-500">{highCount}</p><p className="mt-1 text-[11px] uppercase tracking-wide text-muted-foreground">current filters</p></div>
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-orange-500/10"><Bell className="h-7 w-7 text-orange-500" /></div>
            </div>
          </Card>
          <Card className="relative overflow-hidden border-l-4 border-l-emerald-500 bg-gradient-to-br from-emerald-500/10 via-background to-background p-5 shadow-sm">
            <div className="absolute -right-8 -top-8 h-24 w-24 rounded-full bg-emerald-500/10" />
            <div className="relative flex items-center justify-between gap-4">
              <div><p className="text-sm font-medium text-muted-foreground">Resolved</p><p className="text-3xl font-bold text-emerald-500">{resolvedCount}</p><p className="mt-1 text-[11px] uppercase tracking-wide text-muted-foreground">current filters</p></div>
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/10"><CheckCircle className="h-7 w-7 text-emerald-500" /></div>
            </div>
          </Card>
          <Card className="relative overflow-hidden border-l-4 border-l-blue-500 bg-gradient-to-br from-blue-500/10 via-background to-background p-5 shadow-sm">
            <div className="absolute -right-8 -top-8 h-24 w-24 rounded-full bg-blue-500/10" />
            <div className="relative flex items-center justify-between gap-4">
              <div><p className="text-sm font-medium text-muted-foreground">Visible Alerts</p><p className="text-3xl font-bold text-blue-500">{visibleCounts.total}</p><p className="mt-1 text-[11px] uppercase tracking-wide text-muted-foreground">current filters</p></div>
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-500/10"><Zap className="h-7 w-7 text-blue-500" /></div>
            </div>
          </Card>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList className="bg-muted/50 p-1">
            <TabsTrigger value="live"><Zap className="h-4 w-4 mr-2" /> Live Alerts</TabsTrigger>
            <TabsTrigger value="analytics"><Filter className="h-4 w-4 mr-2" /> Analytics</TabsTrigger>
          </TabsList>

          <TabsContent value="live" className="space-y-4">
            <Card className="overflow-hidden border-border/70 bg-gradient-to-r from-background via-muted/20 to-background shadow-sm">
              <div className="flex flex-col gap-4 p-4">
                <div className="flex flex-col gap-3 xl:flex-row xl:items-end">
                  <div className="min-w-0 flex-1 space-y-1.5">
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                      <Filter className="h-3.5 w-3.5" /> Alert Filters
                    </div>
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        placeholder="Search vehicle, IMEI, title, category or message..."
                        className="h-11 rounded-xl border-border/80 bg-background/90 pl-10"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-nowrap">
                    <div className="space-y-1.5">
                      <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">From</span>
                      <Input type="date" className="h-11 rounded-xl sm:w-[150px]" value={selectedStartDate} onChange={(e) => setSelectedStartDate(e.target.value)} max={selectedEndDate} />
                    </div>
                    <div className="space-y-1.5">
                      <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">To</span>
                      <Input type="date" className="h-11 rounded-xl sm:w-[150px]" value={selectedEndDate} onChange={(e) => setSelectedEndDate(e.target.value)} min={selectedStartDate} />
                    </div>
                  </div>
                </div>

                <div className="grid gap-3 lg:grid-cols-[1.2fr_1fr]">
                  <div className="rounded-2xl border bg-background/70 p-3">
                    <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                      <MapPin className="h-3.5 w-3.5" /> Location Hierarchy
                    </div>
                    <div className="grid gap-2 md:grid-cols-3">
                      <Select value={selectedZone} onValueChange={setSelectedZone}>
                        <SelectTrigger className="h-10 rounded-xl"><SelectValue placeholder="All Zones" /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Zones</SelectItem>
                          {zones.filter((zone: any) => zone.id).map((zone: any) => (
                            <SelectItem key={zone.id} value={zone.id}>{zone.name || zone.code || zone.id}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Select value={selectedWard} onValueChange={setSelectedWard}>
                        <SelectTrigger className="h-10 rounded-xl"><SelectValue placeholder="All Wards" /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Wards</SelectItem>
                          {wards.filter((ward: any) => ward.id).map((ward: any) => (
                            <SelectItem key={ward.id} value={ward.id}>{ward.name || ward.code || ward.id}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Select value={selectedRoute} onValueChange={setSelectedRoute}>
                        <SelectTrigger className="h-10 rounded-xl"><SelectValue placeholder="All Routes" /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Routes</SelectItem>
                          {routes.filter((route: any) => route.id).map((route: any) => (
                            <SelectItem key={route.id} value={route.id}>{route.route_name || route.name || route.code || route.id}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="rounded-2xl border bg-background/70 p-3">
                    <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                      <Shield className="h-3.5 w-3.5" /> Alert State
                    </div>
                    <div className="grid gap-2 md:grid-cols-3">
                      <Select value={selectedStatus} onValueChange={setSelectedStatus}>
                        <SelectTrigger className="h-10 rounded-xl"><SelectValue /></SelectTrigger>
                        <SelectContent><SelectItem value="all">All Status</SelectItem><SelectItem value="open">Open</SelectItem><SelectItem value="acknowledged">Acknowledged</SelectItem><SelectItem value="escalated">Escalated</SelectItem><SelectItem value="resolved">Resolved</SelectItem></SelectContent>
                      </Select>
                      <Select value={selectedSeverity} onValueChange={setSelectedSeverity}>
                        <SelectTrigger className="h-10 rounded-xl"><SelectValue /></SelectTrigger>
                        <SelectContent><SelectItem value="all">All Severity</SelectItem><SelectItem value="critical">Critical</SelectItem><SelectItem value="high">High</SelectItem><SelectItem value="medium">Medium</SelectItem><SelectItem value="low">Low</SelectItem></SelectContent>
                      </Select>
                      <Select value={selectedType} onValueChange={setSelectedType}>
                        <SelectTrigger className="h-10 rounded-xl"><SelectValue /></SelectTrigger>
                        <SelectContent><SelectItem value="all">All Types</SelectItem>{alertTypes.map((type) => <SelectItem key={type} value={type}>{alertMeta[type]?.label || titleCase(type)}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
              </div>
            </Card>

            <Card className="overflow-hidden">
              <ScrollArea className="h-[560px]">
                <div className="space-y-2 p-3">
                  {isLoading ? (
                    <div className="flex items-center justify-center py-16 text-muted-foreground"><Loader2 className="h-6 w-6 mr-2 animate-spin" /> Loading alerts...</div>
                  ) : visibleCounts.total === 0 ? (
                    <div className="flex flex-col items-center justify-center py-16 text-center text-muted-foreground">
                      <Bell className="h-12 w-12 mb-4 opacity-40" />
                      <p className="text-lg font-medium">No alerts found</p>
                      <p className="text-sm">
                        {Number(summary.total || 0) > 0
                          ? `${summary.total} alerts exist, but none match the selected filters.`
                          : "Try adjusting filters or wait for new operational alerts."}
                      </p>
                    </div>
                  ) : (
                    paginatedAlerts.map((alert) => {
                      const type = alertType(alert);
                      const Icon = alertMeta[type]?.icon || Bell;
                      const meta = alertMetadata(alert);
                      return (
                        <Card key={alert.id} className={`overflow-hidden border-l-4 bg-card/95 px-3 py-2.5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-lg ${alert.severity === "critical" ? "border-l-destructive" : alert.severity === "high" ? "border-l-orange-500" : alert.severity === "medium" ? "border-l-warning" : "border-l-border"}`}>
                          <div className="grid gap-3 xl:grid-cols-[auto_minmax(0,1fr)_410px] xl:items-center">
                            <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-muted ring-1 ring-border">
                              <Icon className="h-4 w-4" />
                            </div>
                            <div className="min-w-0 flex-1">
                              <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
                                <p className="truncate font-semibold leading-tight text-foreground">{alert.title || alertMeta[type]?.label || titleCase(type)}</p>
                                <span className="whitespace-nowrap text-xs text-muted-foreground">{formatDateTime(alert.triggered_at)}</span>
                              </div>
                              <p className="mt-1 truncate text-sm text-foreground/85">{alert.message || "No message supplied."}</p>
                              <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                                <span className="flex items-center gap-1"><Truck className="h-3 w-3" /> {alertVehicle(alert)}</span>
                                <span className="flex items-center gap-1"><MapPin className="h-3 w-3" /> {alertLocation(alert)}</span>
                                <span>Category: {alert.category || "-"}</span>
                                {meta.route && <span>Route: {formatMetadataValue(meta.route)}</span>}
                                {meta.driver && <span>Driver: {formatMetadataValue(meta.driver)}</span>}
                              </div>
                            </div>
                            <div className="flex flex-wrap items-center justify-end gap-2 rounded-xl bg-muted/35 p-2">
                              <div className="flex flex-nowrap justify-end gap-1.5">
                                <Badge variant="outline" className={getSeverityColor(alert.severity)}>{alert.severity || "medium"}</Badge>
                                <Badge className={getStatusColor(alert.status)}>{alert.status || "open"}</Badge>
                              </div>
                              <div className="flex flex-nowrap justify-end gap-1.5">
                                {renderActions(alert)}
                                <ActionDropdown truckId={alertVehicle(alert)} alertType={titleCase(type)} alertMessage={alert.message || alert.title || ""} size="icon" />
                                <Button variant="ghost" size="sm" className="h-8 w-8 p-0" title="View details" onClick={() => setSelectedAlert(alert)}><Eye className="h-4 w-4" /></Button>
                              </div>
                            </div>
                          </div>
                        </Card>
                      );
                    })
                  )}
                </div>
              </ScrollArea>
              <div className="flex flex-col gap-3 border-t bg-muted/20 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="text-sm text-muted-foreground">
                  Showing <span className="font-medium text-foreground">{pageStart}</span>-<span className="font-medium text-foreground">{pageEnd}</span> of <span className="font-medium text-foreground">{visibleCounts.total}</span> filtered alerts
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Select value={String(pageSize)} onValueChange={(value) => { setPageSize(Number(value)); setCurrentPage(1); }}>
                    <SelectTrigger className="h-9 w-[120px]"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="10">10 / page</SelectItem>
                      <SelectItem value="20">20 / page</SelectItem>
                      <SelectItem value="50">50 / page</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button variant="outline" size="sm" disabled={currentPage <= 1} onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}>
                    Previous
                  </Button>
                  <span className="min-w-[90px] text-center text-sm text-muted-foreground">
                    Page {currentPage} / {totalPages}
                  </span>
                  <Button variant="outline" size="sm" disabled={currentPage >= totalPages} onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}>
                    Next
                  </Button>
                </div>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="analytics" className="space-y-4">
            <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
              <Card className="overflow-hidden border-border/70 bg-gradient-to-br from-slate-950 via-slate-900 to-teal-950 text-white shadow-xl">
                <div className="relative p-5">
                  <div className="absolute -right-12 -top-12 h-40 w-40 rounded-full bg-cyan-400/15 blur-2xl" />
                  <div className="absolute bottom-0 left-1/3 h-24 w-56 rounded-full bg-emerald-400/10 blur-2xl" />
                  <div className="relative flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.28em] text-cyan-200/80">Monitoring Intelligence</p>
                      <h3 className="mt-2 text-2xl font-semibold">Alerts Command Center</h3>
                      <p className="mt-1 max-w-2xl text-sm text-slate-300">Live operational pressure, severity mix, and response workload from the selected filters.</p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <Badge className="border-cyan-300/30 bg-cyan-300/10 text-cyan-100 hover:bg-cyan-300/10">{selectedPeriodLabel}</Badge>
                        <Badge className="border-white/20 bg-white/10 text-slate-100 hover:bg-white/10">Aggregated over {selectedPeriodShortLabel}</Badge>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="rounded-2xl border border-white/10 bg-white/10 px-4 py-3 backdrop-blur">
                        <p className="text-2xl font-bold">{visibleCounts.total}</p>
                        <p className="text-[10px] uppercase tracking-wide text-slate-300">Filtered</p>
                      </div>
                      <div className="rounded-2xl border border-red-300/20 bg-red-500/15 px-4 py-3 backdrop-blur">
                        <p className="text-2xl font-bold text-red-200">{criticalCount + highCount}</p>
                        <p className="text-[10px] uppercase tracking-wide text-red-100/80">Urgent</p>
                      </div>
                      <div className="rounded-2xl border border-emerald-300/20 bg-emerald-500/15 px-4 py-3 backdrop-blur">
                        <p className="text-2xl font-bold text-emerald-200">{resolvedCount}</p>
                        <p className="text-[10px] uppercase tracking-wide text-emerald-100/80">Closed</p>
                      </div>
                    </div>
                  </div>
                  <div className="relative mt-5 grid gap-3 md:grid-cols-4">
                    {severityBreakdown.map((item) => (
                      <button
                        key={item.key}
                        type="button"
                        className="rounded-2xl border border-white/10 bg-white/[0.07] p-3 text-left transition hover:-translate-y-0.5 hover:border-cyan-300/40 hover:bg-white/[0.11]"
                        onClick={() => drillToLive({ severity: item.key })}
                        title={`Drill down to ${item.label} alerts`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-slate-200">{item.label}</span>
                          <span className="text-lg font-bold" style={{ color: item.color }}>{item.value}</span>
                        </div>
                        <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10">
                          <div className="h-full rounded-full" style={{ width: `${item.percent}%`, backgroundColor: item.color }} />
                        </div>
                        <p className="mt-1 text-right text-[10px] text-slate-400">{item.percent}%</p>
                      </button>
                    ))}
                  </div>
                </div>
              </Card>

              <Card className="p-4">
                <div className="mb-3 flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold">Response Workload</h3>
                    <p className="text-sm text-muted-foreground">{selectedPeriodLabel}</p>
                  </div>
                  <Badge variant="outline">{activeCount} active</Badge>
                </div>
                <div className="space-y-4">
                  {statusBreakdown.map((item) => (
                    <button
                      key={item.key}
                      type="button"
                      className="block w-full rounded-xl p-1 text-left transition hover:bg-muted/60"
                      onClick={() => drillToLive({ status: item.key })}
                      title={`Drill down to ${item.label} alerts`}
                    >
                      <div className="mb-1 flex items-center justify-between text-sm">
                        <span className="font-medium">{item.label}</span>
                        <span className="text-muted-foreground">{item.value} alerts</span>
                      </div>
                      <div className="h-3 overflow-hidden rounded-full bg-muted">
                        <div className="h-full rounded-full" style={{ width: `${item.percent}%`, backgroundColor: item.color }} />
                      </div>
                    </button>
                  ))}
                </div>
              </Card>
            </div>

            <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
              <Card className="p-4 xl:col-span-2">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold">Hourly Alert Intensity</h3>
                    <p className="text-sm text-muted-foreground">One-day timeline for selected end date</p>
                  </div>
                  <Badge variant="outline">Day view: {selectedEndDate}</Badge>
                </div>
                <div className="h-[320px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={trend}>
                      <defs>
                        <linearGradient id="criticalAlertGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="hsl(var(--destructive))" stopOpacity={0.75} />
                          <stop offset="95%" stopColor="hsl(var(--destructive))" stopOpacity={0.12} />
                        </linearGradient>
                        <linearGradient id="highAlertGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#f97316" stopOpacity={0.7} />
                          <stop offset="95%" stopColor="#f97316" stopOpacity={0.1} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                      <XAxis dataKey="hour" className="text-xs" interval={2} />
                      <YAxis className="text-xs" />
                      <Tooltip />
                      <Area type="monotone" dataKey="critical" stackId="1" stroke="hsl(var(--destructive))" fill="url(#criticalAlertGradient)" />
                      <Area type="monotone" dataKey="high" stackId="1" stroke="#f97316" fill="url(#highAlertGradient)" />
                      <Area type="monotone" dataKey="medium" stackId="1" stroke="hsl(var(--warning))" fill="hsl(var(--warning))" fillOpacity={0.35} />
                      <Area type="monotone" dataKey="low" stackId="1" stroke="hsl(var(--muted-foreground))" fill="hsl(var(--muted-foreground))" fillOpacity={0.2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </Card>

              <Card className="p-4">
                <div className="mb-4">
                  <h3 className="text-lg font-semibold">Alert Type Mix</h3>
                  <p className="text-sm text-muted-foreground">Current page sample from {selectedPeriodLabel.toLowerCase()}</p>
                </div>
                <div className="h-[230px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={distribution} cx="50%" cy="50%" innerRadius={55} outerRadius={92} paddingAngle={3} dataKey="value">
                        {distribution.map((entry) => <Cell key={entry.name} fill={entry.color} />)}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-2 space-y-2">
                  {distribution.slice(0, 5).map((item) => (
                    <button
                      key={item.name}
                      type="button"
                      className="flex w-full items-center justify-between rounded-lg bg-muted/40 px-3 py-2 text-left text-sm transition hover:bg-muted"
                      onClick={() => {
                        const matchingType = alertTypes.find((type) => (alertMeta[type]?.label || titleCase(type)) === item.name);
                        drillToLive({ type: matchingType || item.name.toLowerCase().replace(/\s+/g, "_") });
                      }}
                      title={`Drill down to ${item.name}`}
                    >
                      <span className="flex min-w-0 items-center gap-2 truncate"><span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} /> {item.name}</span>
                      <span className="font-semibold">{item.value}</span>
                    </button>
                  ))}
                </div>
              </Card>
            </div>

            <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.15fr_0.85fr]">
              <Card className="p-4">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold">Zone / Ward Severity Matrix</h3>
                    <p className="text-sm text-muted-foreground">Visible alert concentration for {selectedPeriodLabel.toLowerCase()}</p>
                  </div>
                </div>
                <div className="h-[320px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={zoneRows}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                      <XAxis dataKey="zone" className="text-xs" />
                      <YAxis className="text-xs" />
                      <Tooltip />
                      <Bar dataKey="critical" stackId="a" fill="hsl(var(--destructive))" radius={[0, 0, 4, 4]} />
                      <Bar dataKey="high" stackId="a" fill="#f97316" />
                      <Bar dataKey="medium" stackId="a" fill="hsl(var(--warning))" />
                      <Bar dataKey="low" stackId="a" fill="hsl(var(--muted-foreground))" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>

              <Card className="p-4">
                <div className="mb-4">
                  <h3 className="text-lg font-semibold">Priority Focus Areas</h3>
                  <p className="text-sm text-muted-foreground">Ranked by weighted alert severity. Click an area to drill down.</p>
                </div>
                <div className="overflow-hidden rounded-xl border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Area</TableHead>
                        <TableHead className="text-right">Alerts</TableHead>
                        <TableHead className="text-right">Risk</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {topFocusRows.length === 0 ? (
                        <TableRow><TableCell colSpan={3} className="py-8 text-center text-muted-foreground">No focus areas for current filters.</TableCell></TableRow>
                      ) : topFocusRows.map((row: any) => (
                        <TableRow key={row.zone} className="cursor-pointer" onClick={() => drillToLive({ search: row.zone === "Unmapped" ? "" : row.zone })}>
                          <TableCell className="font-medium">{row.zone}</TableCell>
                          <TableCell className="text-right">{row.total}</TableCell>
                          <TableCell className="text-right">
                            <Badge className={row.risk >= 10 ? "bg-destructive/10 text-destructive" : row.risk >= 5 ? "bg-orange-500/10 text-orange-600" : "bg-muted text-muted-foreground"}>
                              {row.risk}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </Card>
            </div>
          </TabsContent>
        </Tabs>

        <Dialog open={Boolean(selectedAlert)} onOpenChange={(open) => !open && setSelectedAlert(null)}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>{selectedAlert?.title || (selectedAlert ? titleCase(alertType(selectedAlert)) : "Alert Details")}</DialogTitle>
              <DialogDescription>Real alert record from the backend alerts table.</DialogDescription>
            </DialogHeader>
            {selectedAlert && (
              <div className="grid gap-3 text-sm">
                <div className="grid grid-cols-2 gap-3">
                  <div><span className="text-muted-foreground">Severity:</span><div><Badge className={getSeverityColor(selectedAlert.severity)}>{selectedAlert.severity}</Badge></div></div>
                  <div><span className="text-muted-foreground">Status:</span><div><Badge className={getStatusColor(selectedAlert.status)}>{selectedAlert.status}</Badge></div></div>
                  <div><span className="text-muted-foreground">Vehicle:</span><p>{alertVehicle(selectedAlert)}</p></div>
                  <div><span className="text-muted-foreground">Triggered:</span><p>{formatDateTime(selectedAlert.triggered_at)}</p></div>
                </div>
                <div><span className="text-muted-foreground">Message:</span><p>{selectedAlert.message || "-"}</p></div>
                <div><span className="text-muted-foreground">Location:</span><p>{alertLocation(selectedAlert)}</p></div>
                <div><span className="text-muted-foreground">Metadata:</span><pre className="mt-1 max-h-48 overflow-auto rounded bg-muted p-3 text-xs">{JSON.stringify(alertMetadata(selectedAlert), null, 2)}</pre></div>
              </div>
            )}
            <DialogFooter>{selectedAlert && renderActions(selectedAlert)}</DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
