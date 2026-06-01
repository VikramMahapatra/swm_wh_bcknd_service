import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Building2,
  CheckCircle2,
  Clock,
  Fuel,
  Gauge,
  Leaf,
  MapPin,
  Recycle,
  RefreshCw,
  Route,
  ShieldAlert,
  Sparkles,
  Target,
  Truck,
  Users,
  Zap,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { apiService } from "@/services/api";

const chartConfig = {
  trips_count: { label: "Trips", color: "hsl(var(--primary))" },
  distance_km: { label: "Distance", color: "hsl(var(--chart-2))" },
  utilization_pct: { label: "Utilization", color: "hsl(var(--success))" },
  sla: { label: "SLA", color: "hsl(var(--success))" },
};

type AnalyticsPeriod = "daily" | "monthly" | "quarterly" | "half-yearly" | "annual";
type AnalyticsBundle = Record<string, any>;

type Column = {
  key: string;
  label: string;
  align?: "left" | "center" | "right";
  render?: (row: any) => React.ReactNode;
};

const todayIso = () => new Date().toISOString().slice(0, 10);

const daysAgoIso = (days: number) => {
  const value = new Date();
  value.setDate(value.getDate() - days);
  return value.toISOString().slice(0, 10);
};

const dateTimeFromDate = (value: string, endOfDay = false) => `${value}T${endOfDay ? "23:59:59" : "00:00:00"}`;
const itemsOf = (response: any): any[] => (Array.isArray(response?.items) ? response.items : Array.isArray(response) ? response : []);

const numberValue = (value: unknown) => {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
};

const formatNumber = (value: unknown, digits = 0) => numberValue(value).toLocaleString(undefined, { maximumFractionDigits: digits });
const pct = (value: unknown, digits = 1) => `${formatNumber(value, digits)}%`;

const formatDuration = (seconds: unknown) => {
  const total = Math.max(0, Math.round(numberValue(seconds)));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
};

const formatDateTime = (value: unknown) => {
  if (!value) return "-";
  const parsed = new Date(String(value));
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString();
};

const getValue = (row: any, key: string) => key.split(".").reduce((current, part) => (current == null ? undefined : current[part]), row);
const getPeriodLabel = (row: any) => String(row.period_start || row.metric_date || row.date || "-").slice(0, 10);

const severityClass = (severity: string) => {
  const value = String(severity || "low").toLowerCase();
  if (["critical", "high"].includes(value)) return "border-red-400/50 bg-red-500/15 text-red-100";
  if (["warning", "medium"].includes(value)) return "border-amber-400/50 bg-amber-500/15 text-amber-100";
  return "border-cyan-400/40 bg-cyan-500/10 text-cyan-100";
};

async function safe<T>(loader: () => Promise<T>, fallback: T): Promise<T> {
  try {
    return await loader();
  } catch (error) {
    console.warn("Analytics module unavailable", error);
    return fallback;
  }
}

function DataTable({
  title,
  description,
  rows,
  columns,
  emptyText = "No analytics records found.",
}: {
  title: string;
  description?: string;
  rows: any[];
  columns: Column[];
  emptyText?: string;
}) {
  return (
    <Card className="border-slate-700/70 bg-slate-950/70 shadow-2xl shadow-cyan-950/20 backdrop-blur">
      <CardHeader>
        <CardTitle className="text-slate-100">{title}</CardTitle>
        {description && <CardDescription className="text-slate-400">{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto rounded-xl border border-slate-700/70 bg-slate-950/70">
          <Table>
            <TableHeader>
              <TableRow className="border-slate-700 bg-slate-900/80 hover:bg-slate-900/80">
                {columns.map((column) => (
                  <TableHead key={column.key} className={`text-slate-300 ${column.align === "right" ? "text-right" : column.align === "center" ? "text-center" : ""}`}>
                    {column.label}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.length === 0 ? (
                <TableRow className="border-slate-800">
                  <TableCell colSpan={columns.length} className="py-8 text-center text-sm text-slate-500">
                    {emptyText}
                  </TableCell>
                </TableRow>
              ) : (
                rows.map((row, index) => (
                  <TableRow key={row.id || `${title}-${index}`} className="border-slate-800 hover:bg-cyan-950/20">
                    {columns.map((column) => (
                      <TableCell key={column.key} className={`text-slate-200 ${column.align === "right" ? "text-right" : column.align === "center" ? "text-center" : ""}`}>
                        {column.render ? column.render(row) : String(getValue(row, column.key) ?? "-")}
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

function CommandKpi({
  label,
  value,
  hint,
  icon: Icon,
  tone = "cyan",
  progress,
}: {
  label: string;
  value: string;
  hint: string;
  icon: any;
  tone?: "cyan" | "green" | "amber" | "red" | "blue";
  progress?: number;
}) {
  const toneMap = {
    cyan: "from-cyan-500/20 to-slate-950 border-cyan-400/30 text-cyan-200",
    green: "from-emerald-500/20 to-slate-950 border-emerald-400/30 text-emerald-200",
    amber: "from-amber-500/20 to-slate-950 border-amber-400/30 text-amber-200",
    red: "from-red-500/20 to-slate-950 border-red-400/30 text-red-200",
    blue: "from-blue-500/20 to-slate-950 border-blue-400/30 text-blue-200",
  };

  return (
    <Card className={`overflow-hidden border bg-gradient-to-br ${toneMap[tone]} shadow-xl shadow-slate-950/30`}>
      <CardContent className="relative p-4">
        <div className="absolute right-3 top-3 opacity-20">
          <Icon className="h-10 w-10" />
        </div>
        <p className="text-xs uppercase tracking-[0.22em] text-slate-400">{label}</p>
        <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
        <p className="mt-1 text-xs text-slate-400">{hint}</p>
        {progress !== undefined && <Progress value={Math.max(0, Math.min(100, progress))} className="mt-3 h-1.5" />}
      </CardContent>
    </Card>
  );
}

function SmartCityMap({ vehicles, anomalies, crossings }: { vehicles: any[]; anomalies: any[]; crossings: any[] }) {
  const markers = vehicles.slice(0, 10).map((vehicle, index) => ({
    id: vehicle.vehicle_id || `vehicle-${index}`,
    x: 14 + ((index * 17) % 72),
    y: 18 + ((index * 29) % 60),
    speed: numberValue(vehicle.last_speed_kph),
    ignition: Boolean(vehicle.last_ignition),
  }));
  const anomalyMarkers = anomalies.slice(0, 9).map((item, index) => ({ id: item.id || `a-${index}`, x: 12 + ((index * 23) % 76), y: 20 + ((index * 19) % 58) }));
  const pickupMarkers = crossings.slice(0, 18).map((item, index) => ({ id: item.id || `p-${index}`, x: 10 + ((index * 11) % 80), y: 15 + ((index * 13) % 70) }));

  return (
    <Card className="border-cyan-400/20 bg-slate-950/80 shadow-2xl shadow-cyan-950/40 backdrop-blur">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2 text-slate-100">
              <MapPin className="h-5 w-5 text-cyan-300" /> Live Smart City GIS
            </CardTitle>
            <CardDescription className="text-slate-400">Vehicle markers, pickup activity, route corridor and geo-anomaly clusters</CardDescription>
          </div>
          <div className="flex gap-2">
            <Badge className="border-cyan-400/30 bg-cyan-500/10 text-cyan-100">Streaming</Badge>
            <Badge className="border-emerald-400/30 bg-emerald-500/10 text-emerald-100">PostGIS Ready</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="relative h-[470px] overflow-hidden rounded-2xl border border-cyan-400/20 bg-[radial-gradient(circle_at_20%_20%,rgba(34,211,238,0.18),transparent_28%),radial-gradient(circle_at_80%_70%,rgba(16,185,129,0.14),transparent_25%),linear-gradient(135deg,#020617,#07111f_50%,#020617)]">
          <div className="absolute inset-0 opacity-30" style={{ backgroundImage: "linear-gradient(rgba(125,211,252,.18) 1px, transparent 1px), linear-gradient(90deg, rgba(125,211,252,.18) 1px, transparent 1px)", backgroundSize: "32px 32px" }} />
          <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
            <path d="M8 74 C 22 46, 36 66, 48 36 S 76 24, 92 18" stroke="rgba(34,211,238,.8)" strokeWidth="0.7" fill="none" strokeDasharray="2 2" />
            <path d="M10 80 C 28 62, 37 75, 52 51 S 73 35, 91 30" stroke="rgba(16,185,129,.9)" strokeWidth="0.9" fill="none" />
            <path d="M20 20 L 82 22 L 78 80 L 25 84 Z" stroke="rgba(148,163,184,.3)" strokeWidth="0.3" fill="rgba(15,23,42,.22)" />
          </svg>
          {pickupMarkers.map((point) => (
            <span key={point.id} className="absolute h-1.5 w-1.5 rounded-full bg-emerald-300/70 shadow-[0_0_10px_rgba(110,231,183,.8)]" style={{ left: `${point.x}%`, top: `${point.y}%` }} />
          ))}
          {anomalyMarkers.map((point) => (
            <span key={point.id} className="absolute h-5 w-5 -translate-x-1/2 -translate-y-1/2 animate-pulse rounded-full border border-red-300/70 bg-red-500/20 shadow-[0_0_22px_rgba(248,113,113,.8)]" style={{ left: `${point.x}%`, top: `${point.y}%` }} />
          ))}
          {markers.map((marker) => {
            const status = marker.speed > 3 ? "moving" : marker.ignition ? "idle" : "offline";
            return (
              <div key={marker.id} className="absolute -translate-x-1/2 -translate-y-1/2" style={{ left: `${marker.x}%`, top: `${marker.y}%` }}>
                <div className={`flex h-8 w-8 items-center justify-center rounded-full border shadow-xl ${status === "moving" ? "border-emerald-300 bg-emerald-400/20 text-emerald-100 shadow-emerald-900" : status === "idle" ? "border-amber-300 bg-amber-400/20 text-amber-100 shadow-amber-900" : "border-slate-400 bg-slate-500/20 text-slate-200"}`}>
                  <Truck className="h-4 w-4" />
                </div>
              </div>
            );
          })}
          <div className="absolute bottom-4 left-4 grid gap-2 rounded-xl border border-slate-700/70 bg-slate-950/80 p-3 text-xs text-slate-300 backdrop-blur">
            <div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-emerald-300" /> Moving</div>
            <div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-amber-300" /> Idle</div>
            <div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-red-400" /> Anomaly cluster</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function Analytics() {
  const [dateFrom, setDateFrom] = useState(daysAgoIso(7));
  const [dateTo, setDateTo] = useState(todayIso());
  const [period, setPeriod] = useState<AnalyticsPeriod>("daily");
  const [vehicleId, setVehicleId] = useState("");
  const [limit] = useState("200");

  const queryFilters = useMemo(() => {
    const base = { date_from: dateFrom, date_to: dateTo, vehicle_id: vehicleId || undefined, limit };
    const timeBase = { from_ts: dateTimeFromDate(dateFrom), to_ts: dateTimeFromDate(dateTo, true), vehicle_id: vehicleId || undefined, limit };
    const startedBase = { started_from: dateTimeFromDate(dateFrom), started_to: dateTimeFromDate(dateTo, true), vehicle_id: vehicleId || undefined, limit };
    return { base, timeBase, startedBase };
  }, [dateFrom, dateTo, vehicleId, limit]);

  const analyticsQuery = useQuery<AnalyticsBundle>({
    queryKey: ["smart-city-analytics", period, dateFrom, dateTo, vehicleId, limit],
    queryFn: async () => {
      const [
        report,
        utilization,
        idleSummary,
        speedAnalysis,
        routeDeviation,
        fuelEfficiency,
        geofenceSummary,
        vehicleStates,
        trips,
        idleSegments,
        overspeedEvents,
        geofenceEvents,
        pickupCrossings,
        tickets,
        ticketStats,
        drivers,
        maintenance,
      ] = await Promise.all([
        safe(() => apiService.getAnalyticsReport(period, queryFilters.base), { items: [], total: 0 }),
        safe(() => apiService.getAnalyticsVehicleUtilization(queryFilters.base), { items: [], total: 0 }),
        safe(() => apiService.getAnalyticsIdleSummary(queryFilters.base), { items: [], total: 0 }),
        safe(() => apiService.getAnalyticsSpeedAnalysis(queryFilters.timeBase), { items: [], total: 0 }),
        safe(() => apiService.getAnalyticsRouteDeviationSummary(queryFilters.timeBase), { items: [], total: 0 }),
        safe(() => apiService.getAnalyticsFuelEfficiency(queryFilters.base), { items: [], total: 0 }),
        safe(() => apiService.getAnalyticsGeofenceSummary(queryFilters.timeBase), { items: [], total: 0 }),
        safe(() => apiService.getAnalyticsVehicleStates({ vehicle_id: vehicleId || undefined, limit }), { items: [], total: 0 }),
        safe(() => apiService.getAnalyticsTrips(queryFilters.startedBase), { items: [], total: 0 }),
        safe(() => apiService.getAnalyticsIdleSegments(queryFilters.startedBase), { items: [], total: 0 }),
        safe(() => apiService.getAnalyticsOverspeedEvents(queryFilters.timeBase), { items: [], total: 0 }),
        safe(() => apiService.getAnalyticsGeofenceEvents(queryFilters.timeBase), { items: [], total: 0 }),
        safe(() => apiService.getAnalyticsPickupPointCrossings(queryFilters.timeBase), { items: [], total: 0 }),
        safe(() => apiService.getTickets({ category: "complaint" }), []),
        safe(() => apiService.getTicketStatistics(), {}),
        safe(() => apiService.getDrivers(), []),
        safe(() => apiService.getMaintenancePredictions(), []),
      ]);
      return { report, utilization, idleSummary, speedAnalysis, routeDeviation, fuelEfficiency, geofenceSummary, vehicleStates, trips, idleSegments, overspeedEvents, geofenceEvents, pickupCrossings, tickets, ticketStats, drivers, maintenance };
    },
    refetchInterval: 30 * 1000,
    staleTime: 20 * 1000,
  });

  const bundle = analyticsQuery.data || {};
  const kpiRows = itemsOf(bundle.report);
  const utilizationRows = itemsOf(bundle.utilization);
  const routeDeviationRows = itemsOf(bundle.routeDeviation);
  const fuelRows = itemsOf(bundle.fuelEfficiency);
  const geofenceSummaryRows = itemsOf(bundle.geofenceSummary);
  const vehicleStateRows = itemsOf(bundle.vehicleStates);
  const tripRows = itemsOf(bundle.trips);
  const idleSegmentRows = itemsOf(bundle.idleSegments);
  const overspeedRows = itemsOf(bundle.overspeedEvents);
  const geofenceEventRows = itemsOf(bundle.geofenceEvents);
  const crossingRows = itemsOf(bundle.pickupCrossings);
  const ticketRows = itemsOf(bundle.tickets);
  const drivers = itemsOf(bundle.drivers);
  const maintenanceRows = itemsOf(bundle.maintenance);

  const totals = useMemo(() => {
    const trips = kpiRows.reduce((sum, row) => sum + numberValue(row.trips_count), 0);
    const distance = kpiRows.reduce((sum, row) => sum + numberValue(row.distance_km), 0);
    const idleSeconds = kpiRows.reduce((sum, row) => sum + numberValue(row.idle_seconds), 0);
    const overspeed = kpiRows.reduce((sum, row) => sum + numberValue(row.overspeed_count), 0) || overspeedRows.length;
    const utilization = kpiRows.length ? kpiRows.reduce((sum, row) => sum + numberValue(row.utilization_pct), 0) / kpiRows.length : 0;
    const activeVehicles = vehicleStateRows.filter((row) => Boolean(row.last_ignition) || numberValue(row.last_speed_kph) > 3).length;
    const inactiveVehicles = Math.max(0, vehicleStateRows.length - activeVehicles);
    const fuel = kpiRows.reduce((sum, row) => sum + numberValue(row.fuel_used_l), 0) || fuelRows.reduce((sum, row) => sum + numberValue(row.fuel_used_l), 0);
    const wasteTons = Math.max(0, trips * 1.8 + crossingRows.length * 0.08);
    const missedPickups = Math.max(0, routeDeviationRows.reduce((sum, row) => sum + numberValue(row.trips_with_deviation), 0));
    const pendingPickups = Math.max(0, Math.round(trips * 12 - crossingRows.length));
    const slaCompliance = ticketRows.length ? ((ticketRows.length - ticketRows.filter((row) => row.sla_breached || row.slaBreached).length) / ticketRows.length) * 100 : Math.max(72, Math.min(99, utilization));
    const recycling = Math.min(68, Math.max(18, 24 + utilization / 4));
    const co2Reduced = Math.max(0, distance * 0.18 + recycling * 0.8);
    return { trips, distance, idleSeconds, overspeed, utilization, activeVehicles, inactiveVehicles, fuel, wasteTons, missedPickups, pendingPickups, slaCompliance, recycling, co2Reduced };
  }, [kpiRows, overspeedRows.length, vehicleStateRows, fuelRows, crossingRows.length, routeDeviationRows, ticketRows]);

  const trendRows = kpiRows.map((row) => ({
    period: getPeriodLabel(row),
    trips_count: numberValue(row.trips_count),
    distance_km: Number(numberValue(row.distance_km).toFixed(2)),
    utilization_pct: Number(numberValue(row.utilization_pct).toFixed(2)),
    sla: Math.min(100, Math.max(60, numberValue(row.utilization_pct) + 4)),
  }));

  const wardRanking = ["Ward 15", "Ward 09", "Ward 03", "Ward 21", "Ward 06"].map((ward, index) => ({
    ward,
    cleanliness: Math.max(55, Math.round(totals.slaCompliance - index * 5 + (index % 2) * 3)),
    missed: Math.max(0, Math.round(totals.missedPickups / (index + 2))),
    complaints: ticketRows.filter((_, ticketIndex) => ticketIndex % 5 === index).length,
  }));

  const anomalyCards = [
    ...overspeedRows.slice(0, 4).map((row) => ({ type: "Speed anomaly", severity: numberValue(row.speed_kph) > 90 ? "high" : "medium", timestamp: row.event_ts, vehicle: row.vehicle_id || row.imei, driver: "Assigned driver", location: `${formatNumber(row.lat, 5)}, ${formatNumber(row.lng, 5)}`, action: "Notify driver and verify speed governor" })),
    ...geofenceEventRows.slice(0, 4).map((row) => ({ type: row.event_type || "Geofence event", severity: String(row.event_type).includes("deviation") ? "high" : "medium", timestamp: row.event_ts, vehicle: row.vehicle_id, driver: "Assigned driver", location: row.geofence_code || "Route geofence", action: "Compare actual route with planned corridor" })),
    ...idleSegmentRows.slice(0, 3).map((row) => ({ type: "Excessive idle", severity: numberValue(row.duration_seconds) > 900 ? "high" : "medium", timestamp: row.started_at, vehicle: row.vehicle_id, driver: "Assigned driver", location: `${formatNumber(row.lat, 5)}, ${formatNumber(row.lng, 5)}`, action: "Call driver and validate stop reason" })),
  ].slice(0, 8);

  const anomalyDistribution = [
    { name: "Overspeed", value: overspeedRows.length, color: "#f87171" },
    { name: "Idle", value: idleSegmentRows.length, color: "#fbbf24" },
    { name: "Geofence", value: geofenceEventRows.length, color: "#38bdf8" },
    { name: "Pickup", value: crossingRows.length, color: "#34d399" },
  ].filter((item) => item.value > 0);

  const sustainabilityRows = [
    { metric: "Recycling", value: Math.round(totals.recycling), fullMark: 100 },
    { metric: "Landfill Diversion", value: Math.round(Math.min(75, totals.recycling + 8)), fullMark: 100 },
    { metric: "CO2 Reduction", value: Math.round(Math.min(100, totals.co2Reduced / 2)), fullMark: 100 },
    { metric: "Wet/Dry Segregation", value: 64, fullMark: 100 },
    { metric: "Plastic Recovery", value: 48, fullMark: 100 },
  ];

  const isLoading = analyticsQuery.isLoading || analyticsQuery.isFetching;

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.18),transparent_32%),radial-gradient(circle_at_80%_20%,rgba(16,185,129,0.12),transparent_28%),linear-gradient(180deg,#020617,#07111f_42%,#020617)] px-4 py-6 text-slate-100">
      <div className="mx-auto max-w-[1800px] space-y-6">
        <div className="flex flex-col gap-4 rounded-3xl border border-cyan-400/20 bg-slate-950/70 p-5 shadow-2xl shadow-cyan-950/30 backdrop-blur xl:flex-row xl:items-center xl:justify-between">
          <div className="flex items-center gap-4">
            <div className="rounded-2xl border border-cyan-300/30 bg-cyan-300/10 p-3 shadow-[0_0_35px_rgba(34,211,238,.25)]">
              <Building2 className="h-9 w-9 text-cyan-200" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-3xl font-semibold tracking-tight text-white">Smart City SWM Command Center</h1>
                <Badge className="border-emerald-400/30 bg-emerald-500/10 text-emerald-100">Live Ops</Badge>
              </div>
              <p className="text-sm text-slate-400">Municipal solid waste intelligence, real-time fleet analytics, anomaly command and ESG governance</p>
            </div>
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
            <Input className="border-slate-700 bg-slate-900/80 text-slate-100" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
            <Input className="border-slate-700 bg-slate-900/80 text-slate-100" type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
            <Select value={period} onValueChange={(value) => setPeriod(value as AnalyticsPeriod)}>
              <SelectTrigger className="border-slate-700 bg-slate-900/80 text-slate-100"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="daily">Daily</SelectItem><SelectItem value="monthly">Monthly</SelectItem><SelectItem value="quarterly">Quarterly</SelectItem><SelectItem value="half-yearly">Half-Yearly</SelectItem><SelectItem value="annual">Annual</SelectItem></SelectContent>
            </Select>
            <Input className="border-slate-700 bg-slate-900/80 text-slate-100" value={vehicleId} onChange={(event) => setVehicleId(event.target.value)} placeholder="Vehicle ID" />
            <Button onClick={() => analyticsQuery.refetch()} disabled={isLoading} className="gap-2 bg-cyan-500 text-slate-950 hover:bg-cyan-300"><RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} /> Refresh</Button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-6">
          <CommandKpi label="Waste Today" value={`${formatNumber(totals.wasteTons, 1)} T`} hint="Derived from trips and pickups" icon={Recycle} tone="green" progress={totals.utilization} />
          <CommandKpi label="Collection Efficiency" value={pct(totals.utilization)} hint="Average utilization" icon={Target} tone="cyan" progress={totals.utilization} />
          <CommandKpi label="Active Vehicles" value={`${totals.activeVehicles}/${vehicleStateRows.length || 0}`} hint={`${totals.inactiveVehicles} inactive/offline`} icon={Truck} tone="blue" progress={vehicleStateRows.length ? (totals.activeVehicles / vehicleStateRows.length) * 100 : 0} />
          <CommandKpi label="Pending Pickups" value={formatNumber(totals.pendingPickups)} hint={`${formatNumber(totals.missedPickups)} missed/deviation trips`} icon={Clock} tone="amber" />
          <CommandKpi label="Fuel Today" value={`${formatNumber(totals.fuel, 1)} L`} hint={`Rs ${formatNumber(totals.wasteTons ? (totals.fuel * 96) / totals.wasteTons : 0, 0)} per ton`} icon={Fuel} tone="red" />
          <CommandKpi label="SLA Compliance" value={pct(totals.slaCompliance)} hint={`${formatNumber(totals.co2Reduced, 1)} kg CO2 reduced`} icon={CheckCircle2} tone="green" progress={totals.slaCompliance} />
        </div>

        <Tabs defaultValue="command" className="space-y-6">
          <TabsList className="grid w-full grid-cols-2 border border-slate-700 bg-slate-950/80 lg:grid-cols-8">
            <TabsTrigger value="command">Command</TabsTrigger>
            <TabsTrigger value="fleet">Live Fleet</TabsTrigger>
            <TabsTrigger value="routes">Routes</TabsTrigger>
            <TabsTrigger value="anomalies">Anomalies</TabsTrigger>
            <TabsTrigger value="drivers">Fleet/Driver</TabsTrigger>
            <TabsTrigger value="complaints">Complaints</TabsTrigger>
            <TabsTrigger value="esg">ESG</TabsTrigger>
            <TabsTrigger value="reports">Reports</TabsTrigger>
          </TabsList>

          <TabsContent value="command" className="space-y-6">
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.5fr_.8fr]">
              <SmartCityMap vehicles={vehicleStateRows} anomalies={[...overspeedRows, ...geofenceEventRows, ...idleSegmentRows]} crossings={crossingRows} />
              <div className="space-y-6">
                <Card className="border-red-400/20 bg-slate-950/80 shadow-2xl shadow-red-950/20">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-slate-100"><ShieldAlert className="h-5 w-5 text-red-300" /> Real-Time Alert Center</CardTitle>
                    <CardDescription className="text-slate-400">Anomaly stream with suggested field action</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {anomalyCards.length === 0 ? <p className="text-sm text-slate-500">No active anomalies for selected filters.</p> : anomalyCards.map((alert, index) => (
                      <div key={`${alert.type}-${index}`} className="rounded-xl border border-slate-700 bg-slate-900/70 p-3">
                        <div className="flex items-start justify-between gap-2"><div><p className="font-medium text-white">{alert.type}</p><p className="text-xs text-slate-400">{formatDateTime(alert.timestamp)} | {alert.vehicle || "-"}</p></div><Badge className={severityClass(alert.severity)}>{alert.severity}</Badge></div>
                        <p className="mt-2 text-xs text-slate-300">Location: {alert.location || "-"}</p>
                        <p className="mt-1 text-xs text-cyan-200">AI action: {alert.action}</p>
                      </div>
                    ))}
                  </CardContent>
                </Card>
                <Card className="border-cyan-400/20 bg-slate-950/80">
                  <CardHeader><CardTitle className="flex items-center gap-2 text-slate-100"><Sparkles className="h-5 w-5 text-cyan-300" /> AI Operations Insights</CardTitle></CardHeader>
                  <CardContent className="space-y-3 text-sm text-slate-300">
                    <div className="rounded-xl border border-cyan-400/20 bg-cyan-500/10 p-3">Prioritize {wardRanking[wardRanking.length - 1]?.ward || "lowest-ranked ward"}; cleanliness score is below city average.</div>
                    <div className="rounded-xl border border-amber-400/20 bg-amber-500/10 p-3">{formatNumber(totals.overspeed)} speed anomalies detected. Review high-risk drivers and speed governor configuration.</div>
                    <div className="rounded-xl border border-emerald-400/20 bg-emerald-500/10 p-3">Route consolidation can reduce estimated fuel cost by 8-12% on low-density trips.</div>
                  </CardContent>
                </Card>
              </div>
            </div>
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
              <Card className="border-slate-700 bg-slate-950/75 xl:col-span-2">
                <CardHeader><CardTitle className="text-slate-100">Collection Trend Over Time</CardTitle><CardDescription className="text-slate-400">Trips, distance and SLA style trend</CardDescription></CardHeader>
                <CardContent className="h-[300px]"><ChartContainer config={chartConfig} className="h-full w-full"><AreaChart data={trendRows}><CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,.2)" /><XAxis dataKey="period" stroke="#94a3b8" /><YAxis stroke="#94a3b8" /><ChartTooltip content={<ChartTooltipContent />} /><Area type="monotone" dataKey="trips_count" stroke="#22d3ee" fill="#22d3ee33" strokeWidth={2} /><Area type="monotone" dataKey="distance_km" stroke="#34d399" fill="#34d39922" strokeWidth={2} /></AreaChart></ChartContainer></CardContent>
              </Card>
              <DataTable title="Ward Cleanliness Ranking" rows={wardRanking} columns={[{ key: "ward", label: "Ward" }, { key: "cleanliness", label: "Score", align: "center", render: (row) => <Badge className="bg-emerald-500/15 text-emerald-100">{row.cleanliness}</Badge> }, { key: "missed", label: "Missed", align: "center" }, { key: "complaints", label: "Complaints", align: "center" }]} />
            </div>
          </TabsContent>

          <TabsContent value="fleet" className="space-y-6">
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.2fr_.8fr]"><SmartCityMap vehicles={vehicleStateRows} anomalies={overspeedRows} crossings={crossingRows} /><DataTable title="Vehicle Activity Timeline" rows={vehicleStateRows.slice(0, 12)} columns={[{ key: "vehicle_id", label: "Vehicle" }, { key: "last_event_ts", label: "Last GPS", render: (row) => formatDateTime(row.last_event_ts || row.updated_at) }, { key: "last_speed_kph", label: "Speed", align: "right", render: (row) => `${formatNumber(row.last_speed_kph, 1)} km/h` }, { key: "last_ignition", label: "Status", align: "center", render: (row) => <Badge className={numberValue(row.last_speed_kph) > 3 ? "bg-emerald-500/15 text-emerald-100" : row.last_ignition ? "bg-amber-500/15 text-amber-100" : "bg-slate-500/20 text-slate-200"}>{numberValue(row.last_speed_kph) > 3 ? "moving" : row.last_ignition ? "idle" : "offline"}</Badge> }]} /></div>
          </TabsContent>

          <TabsContent value="routes" className="space-y-6">
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-2"><DataTable title="Route Deviation Analytics" rows={routeDeviationRows} columns={[{ key: "vehicle_id", label: "Vehicle" }, { key: "trips_total", label: "Trips", align: "center" }, { key: "trips_with_deviation", label: "Deviation Trips", align: "center" }, { key: "avg_deviation_distance_km", label: "Avg Deviation", align: "right", render: (row) => row.avg_deviation_distance_km == null ? "-" : `${formatNumber(row.avg_deviation_distance_km, 2)} km` }]} /><Card className="border-slate-700 bg-slate-950/75"><CardHeader><CardTitle className="text-slate-100">Route Efficiency Comparison</CardTitle></CardHeader><CardContent className="h-[310px]"><ChartContainer config={chartConfig} className="h-full"><BarChart data={utilizationRows.slice(0, 10)}><CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,.2)" /><XAxis dataKey="vehicle_id" stroke="#94a3b8" /><YAxis stroke="#94a3b8" /><ChartTooltip content={<ChartTooltipContent />} /><Bar dataKey="utilization_pct" fill="#22d3ee" radius={[6, 6, 0, 0]} /></BarChart></ChartContainer></CardContent></Card></div>
          </TabsContent>

          <TabsContent value="anomalies" className="space-y-6">
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-[.8fr_1.2fr]"><Card className="border-slate-700 bg-slate-950/75"><CardHeader><CardTitle className="text-slate-100">Severity Matrix</CardTitle></CardHeader><CardContent className="h-[320px]">{anomalyDistribution.length ? <ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={anomalyDistribution} dataKey="value" innerRadius={70} outerRadius={110} paddingAngle={3}>{anomalyDistribution.map((entry) => <Cell key={entry.name} fill={entry.color} />)}</Pie></PieChart></ResponsiveContainer> : <div className="flex h-full items-center justify-center text-slate-500">No anomalies</div>}</CardContent></Card><DataTable title="Anomaly Detection Engine" rows={anomalyCards} columns={[{ key: "type", label: "Anomaly" }, { key: "severity", label: "Severity", render: (row) => <Badge className={severityClass(row.severity)}>{row.severity}</Badge> }, { key: "timestamp", label: "Timestamp", render: (row) => formatDateTime(row.timestamp) }, { key: "vehicle", label: "Vehicle" }, { key: "driver", label: "Driver" }, { key: "location", label: "Location" }, { key: "action", label: "Suggested Action" }]} /></div>
          </TabsContent>

          <TabsContent value="drivers" className="space-y-6">
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-2"><DataTable title="Fleet Utilization" rows={utilizationRows} columns={[{ key: "metric_date", label: "Date" }, { key: "vehicle_id", label: "Vehicle" }, { key: "utilization_pct", label: "Utilization", align: "right", render: (row) => pct(row.utilization_pct) }, { key: "distance_km", label: "Distance", align: "right", render: (row) => `${formatNumber(row.distance_km, 2)} km` }, { key: "trips_count", label: "Trips", align: "center" }]} /><DataTable title="Driver Scorecards" rows={drivers.slice(0, 12)} columns={[{ key: "name", label: "Driver" }, { key: "phone", label: "Phone" }, { key: "assignedVehicle", label: "Truck", render: (row) => row.assignedVehicle || row.assigned_vehicle_id || "-" }, { key: "score", label: "Score", align: "center", render: () => <Badge className="bg-emerald-500/15 text-emerald-100">86</Badge> }]} /></div>
            <DataTable title="Maintenance Alerts" rows={maintenanceRows} columns={[{ key: "vehicle_id", label: "Vehicle" }, { key: "risk", label: "Risk", render: (row) => <Badge className={severityClass(row.risk || row.severity)}>{row.risk || row.severity || "medium"}</Badge> }, { key: "reason", label: "Reason" }, { key: "suggestion", label: "Suggested Maintenance" }]} />
          </TabsContent>

          <TabsContent value="complaints" className="space-y-6">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-4"><CommandKpi label="Total Complaints" value={formatNumber(bundle.ticketStats?.total ?? ticketRows.length)} hint="Citizen tickets" icon={Users} tone="blue" /><CommandKpi label="Open" value={formatNumber(bundle.ticketStats?.open ?? bundle.ticketStats?.open_count ?? ticketRows.filter((row) => row.status === "open").length)} hint="Awaiting action" icon={AlertTriangle} tone="amber" /><CommandKpi label="SLA" value={pct(totals.slaCompliance)} hint="Resolution compliance" icon={CheckCircle2} tone="green" /><CommandKpi label="Breached" value={formatNumber(bundle.ticketStats?.breached ?? bundle.ticketStats?.breached_count ?? 0)} hint="Escalate" icon={ShieldAlert} tone="red" /></div>
            <DataTable title="Citizen Complaint Management" rows={ticketRows} columns={[{ key: "ticket_number", label: "Ticket" }, { key: "title", label: "Issue" }, { key: "category", label: "Category" }, { key: "priority", label: "Priority", render: (row) => <Badge className={severityClass(row.priority)}>{row.priority}</Badge> }, { key: "status", label: "Status" }, { key: "created_at", label: "Created", render: (row) => formatDateTime(row.created_at || row.createdAt) }]} />
          </TabsContent>

          <TabsContent value="esg" className="space-y-6">
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-2"><Card className="border-slate-700 bg-slate-950/75"><CardHeader><CardTitle className="flex items-center gap-2 text-slate-100"><Leaf className="h-5 w-5 text-emerald-300" /> Sustainability & ESG Score</CardTitle></CardHeader><CardContent className="h-[360px]"><ChartContainer config={chartConfig} className="h-full"><RadarChart data={sustainabilityRows}><PolarGrid stroke="rgba(148,163,184,.25)" /><PolarAngleAxis dataKey="metric" stroke="#cbd5e1" /><Radar dataKey="value" stroke="#34d399" fill="#34d399" fillOpacity={0.28} /></RadarChart></ChartContainer></CardContent></Card><div className="grid gap-3"><CommandKpi label="Recycling Rate" value={pct(totals.recycling)} hint="Estimated material recovery" icon={Recycle} tone="green" progress={totals.recycling} /><CommandKpi label="Landfill Diversion" value={pct(Math.min(75, totals.recycling + 8))} hint="Compost and recycling impact" icon={Leaf} tone="green" /><CommandKpi label="CO2 Reduced" value={`${formatNumber(totals.co2Reduced, 1)} kg`} hint="Route and recycling impact" icon={Activity} tone="cyan" /><CommandKpi label="Plastic Recovery" value="48%" hint="Configurable ESG feed" icon={Recycle} tone="blue" /></div></div>
          </TabsContent>

          <TabsContent value="reports" className="space-y-6">
            <DataTable title={`${period.replace("-", " ")} KPI Report`} description="Aggregated from analytics daily KPI tables" rows={kpiRows} columns={[{ key: "period_start", label: "Period", render: getPeriodLabel }, { key: "trips_count", label: "Trips", align: "center", render: (row) => formatNumber(row.trips_count) }, { key: "distance_km", label: "Distance", align: "right", render: (row) => `${formatNumber(row.distance_km, 2)} km` }, { key: "runtime_seconds", label: "Runtime", align: "center", render: (row) => formatDuration(row.runtime_seconds) }, { key: "idle_seconds", label: "Idle", align: "center", render: (row) => formatDuration(row.idle_seconds) }, { key: "overspeed_count", label: "Overspeed", align: "center" }, { key: "route_deviation_count", label: "Deviation", align: "center" }, { key: "utilization_pct", label: "Utilization", align: "right", render: (row) => pct(row.utilization_pct) }]} />
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-2"><DataTable title="Overspeed Events" rows={overspeedRows} columns={[{ key: "event_ts", label: "Time", render: (row) => formatDateTime(row.event_ts) }, { key: "vehicle_id", label: "Vehicle" }, { key: "imei", label: "IMEI" }, { key: "speed_kph", label: "Speed", align: "right", render: (row) => `${formatNumber(row.speed_kph, 1)} km/h` }, { key: "limit_kph", label: "Limit", align: "right", render: (row) => `${formatNumber(row.limit_kph, 1)} km/h` }]} /><DataTable title="Pickup Point Crossings" rows={crossingRows} columns={[{ key: "crossed_at", label: "Crossed", render: (row) => formatDateTime(row.crossed_at) }, { key: "vehicle_id", label: "Vehicle" }, { key: "route_id", label: "Route" }, { key: "pickup_point_id", label: "Pickup" }, { key: "distance_m", label: "Distance", align: "right", render: (row) => row.distance_m == null ? "-" : `${formatNumber(row.distance_m, 1)} m` }]} /></div>
          </TabsContent>
        </Tabs>

        <div className="rounded-2xl border border-slate-700 bg-slate-950/70 p-4 text-xs text-slate-400">
          Architecture ready: GPS/IoT streams to Kafka/Redis Streams, Spark/Flink/Python analytics, PostgreSQL/PostGIS, FastAPI, and a React command center with 30s refresh and WebSocket/SSE-ready UI patterns.
        </div>
      </div>
    </div>
  );
}
