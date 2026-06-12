
import { useMemo, useState } from "react";
import { format, subDays } from "date-fns";
import {
  Activity,
  AlertTriangle,
  Bell,
  Building2,
  CheckCircle2,
  CircleDot,
  Clock,
  Gauge,
  LayoutDashboard,
  MapPin,
  Recycle,
  Route,
  ShieldAlert,
  Sparkles,
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
  Line,
  LineChart,
  Pie,
  PieChart,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useSwmLiveFleet } from "@/hooks/useSwmLiveFleet";
import { useActiveAlerts, useReportsData, useSpareTrucks, useVehicles } from "@/hooks/useDataQueries";

const chartColors = ["#0f766e", "#14b8a6", "#f59e0b", "#2563eb", "#ef4444", "#8b5cf6", "#06b6d4"];

const toNumber = (...values: unknown[]) => {
  for (const value of values) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return 0;
};

const asText = (...values: unknown[]) => {
  for (const value of values) {
    if (value !== null && value !== undefined && String(value).trim()) return String(value).trim();
  }
  return "Unmapped";
};

const formatTons = (kg: number) => {
  if (!Number.isFinite(kg) || kg <= 0) return "0.0 t";
  return `${(kg / 1000).toFixed(1)} t`;
};

const compactNumber = (value: number) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: 1 }).format(value || 0);

const normalizeDate = (value: unknown) => {
  if (!value) return "";
  const text = String(value);
  if (/^\d{4}-\d{2}-\d{2}/.test(text)) return text.slice(0, 10);
  const parsed = new Date(text);
  return Number.isNaN(parsed.getTime()) ? text.slice(0, 10) : format(parsed, "yyyy-MM-dd");
};

type MetricCardProps = {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ElementType;
  tone: string;
  onClick?: () => void;
  active?: boolean;
};

const MetricCard = ({ title, value, subtitle, icon: Icon, tone, onClick, active }: MetricCardProps) => (
  <Card
    role={onClick ? "button" : undefined}
    tabIndex={onClick ? 0 : undefined}
    onClick={onClick}
    onKeyDown={(event) => {
      if (onClick && (event.key === "Enter" || event.key === " ")) onClick();
    }}
    className={`overflow-hidden border-border/70 bg-card/95 shadow-sm transition ${onClick ? "cursor-pointer hover:-translate-y-0.5 hover:border-teal-400 hover:shadow-md" : ""} ${active ? "ring-2 ring-teal-500/50" : ""}`}
  >
    <CardContent className="relative p-5">
      <div className={`absolute right-0 top-0 h-24 w-24 rounded-bl-[2rem] ${tone}`} />
      <div className="relative flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <p className="mt-2 text-3xl font-bold tracking-tight text-foreground">{value}</p>
          <p className="mt-1 text-xs uppercase tracking-[0.18em] text-muted-foreground">{subtitle}</p>
        </div>
        <div className="rounded-2xl border border-white/60 bg-white/70 p-3 shadow-sm backdrop-blur">
          <Icon className="h-5 w-5 text-teal-700" />
        </div>
      </div>
    </CardContent>
  </Card>
);

const citizenSignals = [
  { label: "Missed collection", count: 24, sla: 82, tone: "#ef4444" },
  { label: "Waste spot reported", count: 18, sla: 88, tone: "#f59e0b" },
  { label: "Street sweeping", count: 11, sla: 91, tone: "#14b8a6" },
  { label: "Odour complaint", count: 7, sla: 79, tone: "#8b5cf6" },
];

const citizenHotspots = [
  { ward: "W1", zone: "Zone1", complaints: 19, resolution: "3.2 hrs", sentiment: 72 },
  { ward: "W4", zone: "Zone1", complaints: 14, resolution: "4.1 hrs", sentiment: 64 },
  { ward: "W7", zone: "Zone2", complaints: 12, resolution: "2.8 hrs", sentiment: 81 },
];

const Index = () => {
  const [activeDrilldown, setActiveDrilldown] = useState<"collection" | "average" | "coverage" | "fleet" | null>(null);
  const [fleetAvailabilityDrilldown, setFleetAvailabilityDrilldown] = useState<"active" | "inactive" | "idle" | "spare" | null>(null);
  const dateTo = format(new Date(), "yyyy-MM-dd");
  const dateFrom = format(subDays(new Date(), 6), "yyyy-MM-dd");

  const { trucks: liveTrucks, isConnected } = useSwmLiveFleet();
  const { data: reportsData = {}, isLoading: reportsLoading } = useReportsData({
    report_type: "material_wise_collection,daily_pickup_coverage,spare_usage",
    date_from: dateFrom,
    date_to: dateTo,
  });
  const { data: activeAlerts = [] } = useActiveAlerts();
  const { data: vehicles = [] } = useVehicles();
  const { data: spareTrucks = [] } = useSpareTrucks();

  const materialRows: any[] = (reportsData as any).material_wise_collection || (reportsData as any).dump_yard || [];
  const dailyCoverageRows: any[] = (reportsData as any).daily_pickup_coverage || [];
  const routePerformanceRows: any[] = (reportsData as any).route_performance || [];
  const spareUsageRows: any[] = (reportsData as any).spare_usage || [];
  const collection = useMemo(() => {
    const days = Array.from({ length: 7 }, (_, index) => {
      const date = format(subDays(new Date(dateTo), 6 - index), "yyyy-MM-dd");
      return { date, label: format(new Date(`${date}T00:00:00`), "dd MMM"), kg: 0, entries: 0, trips: 0 };
    });
    const byDate = new Map(days.map((day) => [day.date, day]));
    const materialMix = new Map<string, number>();
    const zoneTotals = new Map<string, { name: string; kg: number; entries: number }>();
    const wardTotals = new Map<string, { name: string; zone: string; kg: number; entries: number }>();
    let totalKg = 0;
    let entries = 0;

    for (const row of materialRows) {
      const kg = toNumber(row.netWeightKg, row.net_weight_kg, row.weightKg, row.weight_kg, row.net_weight, row.weight, row.totalWeightKg);
      const date = normalizeDate(row.date || row.entryDate || row.entry_date || row.timestamp || row.created_at || row.entry_time);
      const material = asText(row.materialType, row.material_type, row.material, row.wasteType, row.waste_type);
      const zone = asText(row.zone, row.zoneName, row.zone_name, row.zone_id);
      const ward = asText(row.ward, row.wardName, row.ward_name, row.ward_id);

      totalKg += kg;
      entries += 1;
      materialMix.set(material, (materialMix.get(material) || 0) + kg);

      if (byDate.has(date)) {
        const item = byDate.get(date)!;
        item.kg += kg;
        item.entries += 1;
        item.trips += 1;
      }

      const zoneItem = zoneTotals.get(zone) || { name: zone, kg: 0, entries: 0 };
      zoneItem.kg += kg;
      zoneItem.entries += 1;
      zoneTotals.set(zone, zoneItem);

      const wardKey = `${zone}-${ward}`;
      const wardItem = wardTotals.get(wardKey) || { name: ward, zone, kg: 0, entries: 0 };
      wardItem.kg += kg;
      wardItem.entries += 1;
      wardTotals.set(wardKey, wardItem);
    }

    const coverageTotal = dailyCoverageRows.reduce((sum, row) => sum + toNumber(row.totalPoints, row.total_points, row.totalPickupPoints), 0);
    const coverageDone = dailyCoverageRows.reduce((sum, row) => sum + toNumber(row.covered, row.coveredPoints, row.covered_points, row.visitedPoints, row.visited_points), 0);
    const pickupCoverage = coverageTotal > 0 ? Math.round((coverageDone / coverageTotal) * 100) : 0;
    const coverageMissed = Math.max(coverageTotal - coverageDone, 0);
    const coverageDetails = dailyCoverageRows
      .map((row) => {
        const totalPoints = toNumber(row.totalPoints, row.total_points, row.totalPickupPoints);
        const covered = toNumber(row.covered, row.coveredPoints, row.covered_points, row.visitedPoints, row.visited_points);
        const missed = toNumber(row.missed, row.missedPoints, row.missed_points, Math.max(totalPoints - covered, 0));
        const percent = totalPoints > 0 ? Math.round((covered / totalPoints) * 100) : 0;
        return {
          date: asText(row.date, row.reportDate, row.report_date),
          zone: asText(row.zone, row.zoneName, row.zone_name),
          ward: asText(row.ward, row.wardName, row.ward_name),
          route: asText(row.route, row.routeName, row.route_name),
          truck: asText(row.truck, row.vehicle, row.vehicleNumber, row.vehicle_number),
          driver: asText(row.driver, row.driverName, row.driver_name),
          totalPoints,
          covered,
          missed,
          percent,
          status: asText(row.status, percent >= 90 ? "complete" : percent >= 70 ? "partial" : "attention"),
        };
      })
      .sort((a, b) => a.percent - b.percent)
      .slice(0, 12);

    const mix = Array.from(materialMix, ([name, kg]) => ({ name, kg, tons: Number((kg / 1000).toFixed(2)) }))
      .sort((a, b) => b.kg - a.kg)
      .slice(0, 7);
    const zones = Array.from(zoneTotals.values())
      .map((item) => ({ ...item, tons: Number((item.kg / 1000).toFixed(2)) }))
      .sort((a, b) => b.kg - a.kg)
      .slice(0, 8);
    const wards = Array.from(wardTotals.values())
      .map((item) => ({ ...item, tons: Number((item.kg / 1000).toFixed(2)) }))
      .sort((a, b) => b.kg - a.kg)
      .slice(0, 5);
    const weighmentDetails = materialRows
      .map((row) => {
        const kg = toNumber(row.netWeightKg, row.net_weight_kg, row.weightKg, row.weight_kg, row.net_weight, row.weight, row.totalWeightKg);
        return {
          date: asText(normalizeDate(row.date || row.entryDate || row.entry_date || row.timestamp || row.created_at || row.entry_time)),
          truck: asText(row.truck, row.truckNumber, row.vehicle, row.vehicleNumber, row.vehicle_number),
          zone: asText(row.zone, row.zoneName, row.zone_name, row.zone_id),
          ward: asText(row.ward, row.wardName, row.ward_name, row.ward_id),
          route: asText(row.route, row.routeName, row.route_name, row.route_id),
          material: asText(row.materialType, row.material_type, row.material, row.wasteType, row.waste_type),
          kg,
        };
      })
      .sort((a, b) => b.kg - a.kg)
      .slice(0, 12);
    const averageDetails = days.map((day) => {
      const delta = day.kg - totalKg / 7;
      return {
        ...day,
        tons: Number((day.kg / 1000).toFixed(2)),
        avgTons: Number((totalKg / 7 / 1000).toFixed(2)),
        deltaTons: Number((delta / 1000).toFixed(2)),
      };
    });

    return {
      days: days.map((day) => ({ ...day, tons: Number((day.kg / 1000).toFixed(2)) })),
      averageDetails,
      weighmentDetails,
      totalKg,
      entries,
      avgPerDayKg: totalKg / 7,
      pickupCoverage,
      coverageTotal,
      coverageDone,
      coverageMissed,
      coverageDetails,
      materialMix: mix,
      topMaterial: mix[0]?.name || "No material data",
      zones,
      wards,
    };
  }, [dailyCoverageRows, dateTo, materialRows]);

  const fleet = useMemo(() => {
    const statusCounts: Record<string, number> = { moving: 0, idle: 0, dumping: 0, offline: 0, breakdown: 0, active: 0, spare: 0 };
    const zoneCounts = new Map<string, { zone: string; active: number; idle: number; offline: number; spare: number; total: number }>();
    const source = liveTrucks.length ? liveTrucks : vehicles;

    for (const truck of source as any[]) {
      const status = String(truck.status || truck.current_status || truck.operational_status || "active").toLowerCase();
      const zone = asText(truck.zoneId, truck.zone_id, truck.zone, truck.zoneName);
      const isSpare = Boolean(truck.isSpare || truck.is_spare || truck.route_type === "spare");
      const normalized = status.includes("offline") ? "offline" : status.includes("idle") ? "idle" : status.includes("dump") ? "dumping" : status.includes("break") ? "breakdown" : "moving";
      statusCounts[normalized] = (statusCounts[normalized] || 0) + 1;
      if (normalized !== "offline" && normalized !== "breakdown") statusCounts.active += 1;
      if (isSpare) statusCounts.spare += 1;

      const zoneItem = zoneCounts.get(zone) || { zone, active: 0, idle: 0, offline: 0, spare: 0, total: 0 };
      zoneItem.total += 1;
      if (normalized === "idle") zoneItem.idle += 1;
      if (normalized === "offline" || normalized === "breakdown") zoneItem.offline += 1;
      if (normalized !== "offline" && normalized !== "breakdown") zoneItem.active += 1;
      if (isSpare) zoneItem.spare += 1;
      zoneCounts.set(zone, zoneItem);
    }

    const spareUsage = spareUsageRows.reduce((sum, row) => sum + toNumber(row.usageCount, row.usage_count, row.trips, row.totalUsage), 0);
    const spareTotal = Math.max(statusCounts.spare, spareTrucks.length, spareUsage);
    const total = Math.max(source.length, vehicles.length, liveTrucks.length);
    const allVehicleDetails = (source as any[])
      .map((truck) => {
        const status = String(truck.status || truck.current_status || truck.operational_status || "active").toLowerCase();
        const normalized = status.includes("offline") ? "offline" : status.includes("idle") ? "idle" : status.includes("dump") ? "dumping" : status.includes("break") ? "breakdown" : "moving";
        return {
          truck: asText(truck.truckNumber, truck.registration_number, truck.vehicleNumber, truck.vehicle_id, truck.id),
          zone: asText(truck.zoneId, truck.zone_id, truck.zone, truck.zoneName),
          ward: asText(truck.wardId, truck.ward_id, truck.ward, truck.wardName),
          route: asText(truck.routeName, truck.route_name, truck.routeId, truck.route_id),
          status: normalized,
          speed: toNumber(truck.speed, truck.speed_kph),
          spare: Boolean(truck.isSpare || truck.is_spare || truck.route_type === "spare"),
          updated: asText(truck.lastUpdate, truck.last_update, truck.event_ts, truck.timestamp),
        };
      })
    const buildAvailabilityBreakdown = (mode: "active" | "inactive" | "idle" | "spare") => {
      const grouped = new Map<string, { zone: string; ward: string; count: number; moving: number; idle: number; inactive: number; spare: number }>();
      for (const vehicle of allVehicleDetails) {
        const isInactive = vehicle.status === "offline" || vehicle.status === "breakdown";
        const isActive = !isInactive;
        const include =
          mode === "active" ? isActive :
          mode === "inactive" ? isInactive :
          mode === "idle" ? vehicle.status === "idle" :
          vehicle.spare;
        if (!include) continue;

        const key = `${vehicle.zone}-${vehicle.ward}`;
        const item = grouped.get(key) || { zone: vehicle.zone, ward: vehicle.ward, count: 0, moving: 0, idle: 0, inactive: 0, spare: 0 };
        item.count += 1;
        if (vehicle.status === "idle") item.idle += 1;
        if (vehicle.status === "moving" || vehicle.status === "dumping") item.moving += 1;
        if (isInactive) item.inactive += 1;
        if (vehicle.spare) item.spare += 1;
        grouped.set(key, item);
      }
      return Array.from(grouped.values()).sort((a, b) => b.count - a.count).slice(0, 10);
    };

    return {
      total,
      active: statusCounts.active,
      inactive: (statusCounts.offline || 0) + (statusCounts.breakdown || 0),
      idle: statusCounts.idle || 0,
      moving: statusCounts.moving || 0,
      dumping: statusCounts.dumping || 0,
      spare: spareTotal,
      utilization: total > 0 ? Math.round((statusCounts.active / total) * 100) : 0,
      statusChart: [
        { name: "Active", value: statusCounts.active, fill: "#14b8a6" },
        { name: "Idle", value: statusCounts.idle || 0, fill: "#f59e0b" },
        { name: "Inactive", value: (statusCounts.offline || 0) + (statusCounts.breakdown || 0), fill: "#ef4444" },
        { name: "Spare", value: spareTotal, fill: "#2563eb" },
      ],
      zones: Array.from(zoneCounts.values()).sort((a, b) => b.total - a.total).slice(0, 6),
      vehicleDetails: allVehicleDetails.slice(0, 14),
      availabilityBreakdowns: {
        active: buildAvailabilityBreakdown("active"),
        inactive: buildAvailabilityBreakdown("inactive"),
        idle: buildAvailabilityBreakdown("idle"),
        spare: buildAvailabilityBreakdown("spare"),
      },
    };
  }, [liveTrucks, spareTrucks.length, spareUsageRows, vehicles]);
  const alerts = useMemo(() => {
    const bySeverity: Record<string, number> = {};
    const byType: Record<string, number> = {};
    const byCategory: Record<string, number> = {};

    for (const alert of activeAlerts as any[]) {
      const severity = String(alert.severity || "medium").toLowerCase();
      const type = asText(alert.alert_type, alert.type, alert.title).replace(/_/g, " ");
      const category = asText(alert.category, alert.alert_category, alert.source, "Operations");
      bySeverity[severity] = (bySeverity[severity] || 0) + 1;
      byType[type] = (byType[type] || 0) + 1;
      byCategory[category] = (byCategory[category] || 0) + 1;
    }

    const typeRows = Object.entries(byType)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 6);
    const categoryRows = Object.entries(byCategory)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 5);
    const severityRows = ["critical", "high", "medium", "low"].map((name) => ({ name, value: bySeverity[name] || 0 }));

    return {
      total: activeAlerts.length,
      critical: bySeverity.critical || 0,
      high: bySeverity.high || 0,
      topType: typeRows[0]?.name || "No active alerts",
      typeRows,
      categoryRows,
      severityRows,
      operationsRisk: Math.min(100, Math.round((((bySeverity.critical || 0) * 9 + (bySeverity.high || 0) * 5 + (bySeverity.medium || 0) * 2 + activeAlerts.length) / Math.max(1, fleet.total)) * 10)),
    };
  }, [activeAlerts, fleet.total]);

  const routeAnomalies = routePerformanceRows.reduce((sum, row) => sum + toNumber(row.anomalyCount, row.anomaly_count, row.anomyCount, row.deviations, row.overspeeding), 0);
  const citizenSlaAverage = Math.round(citizenSignals.reduce((sum, item) => sum + item.sla, 0) / citizenSignals.length);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Fleet Dashboard"
        description="Seven-day garbage collection intelligence, fleet availability, citizen signal and alert command view"
        icon={LayoutDashboard}
        gradient="from-teal-600 via-cyan-600 to-emerald-600"
      />

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="7-Day Collection"
          value={formatTons(collection.totalKg)}
          subtitle={`${dateFrom} to ${dateTo}`}
          icon={Recycle}
          tone="bg-teal-500/10"
          active={activeDrilldown === "collection"}
          onClick={() => setActiveDrilldown((value) => value === "collection" ? null : "collection")}
        />
        <MetricCard
          title="Average Per Day"
          value={formatTons(collection.avgPerDayKg)}
          subtitle={`${collection.entries} weighment entries`}
          icon={Activity}
          tone="bg-cyan-500/10"
          active={activeDrilldown === "average"}
          onClick={() => setActiveDrilldown((value) => value === "average" ? null : "average")}
        />
        <MetricCard
          title="Pickup Coverage"
          value={`${collection.pickupCoverage}%`}
          subtitle={`${collection.coverageDone}/${collection.coverageTotal} points covered`}
          icon={CheckCircle2}
          tone="bg-emerald-500/10"
          active={activeDrilldown === "coverage"}
          onClick={() => setActiveDrilldown((value) => value === "coverage" ? null : "coverage")}
        />
        <MetricCard
          title="Fleet Utilization"
          value={`${fleet.utilization}%`}
          subtitle={`${fleet.active}/${fleet.total || 0} active vehicles`}
          icon={Truck}
          tone="bg-blue-500/10"
          active={activeDrilldown === "fleet"}
          onClick={() => setActiveDrilldown((value) => value === "fleet" ? null : "fleet")}
        />
      </section>

      {activeDrilldown === "collection" && (
        <Card className="overflow-hidden border-teal-200 bg-gradient-to-br from-white via-teal-50/50 to-emerald-50/40 shadow-sm">
          <CardHeader className="pb-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle className="flex items-center gap-2"><Recycle className="h-5 w-5 text-teal-700" /> 7-Day Collection Drill Down</CardTitle>
                <p className="text-sm text-muted-foreground">Daily tons, material contribution, and largest weighment records in the selected 7-day report window.</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge className="bg-teal-100 text-teal-800 hover:bg-teal-100">{formatTons(collection.totalKg)} collected</Badge>
                <Badge variant="outline">{collection.entries} weighments</Badge>
                <Badge variant="outline">Top material: {collection.topMaterial}</Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent className="grid gap-5 xl:grid-cols-[1fr_1.2fr]">
            <div className="rounded-3xl border bg-white p-4">
              <p className="mb-3 text-sm font-semibold">Daily collection</p>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={collection.days}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="label" tickLine={false} axisLine={false} />
                    <YAxis tickLine={false} axisLine={false} />
                    <Tooltip formatter={(value: number) => `${value} t`} />
                    <Bar dataKey="tons" name="Tons" radius={[10, 10, 0, 0]} fill="#0f766e" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div className="overflow-hidden rounded-3xl border bg-white">
              <div className="grid grid-cols-[1fr_1fr_0.8fr_0.8fr_1fr_0.8fr] bg-slate-50 px-4 py-3 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                <span>Date</span><span>Truck</span><span>Zone</span><span>Ward</span><span>Material</span><span>Weight</span>
              </div>
              <div className="divide-y">
                {collection.weighmentDetails.map((row, index) => (
                  <div key={`${row.date}-${row.truck}-${index}`} className="grid grid-cols-[1fr_1fr_0.8fr_0.8fr_1fr_0.8fr] items-center gap-2 px-4 py-3 text-sm">
                    <span className="font-medium">{row.date}</span>
                    <span className="font-mono text-xs">{row.truck}</span>
                    <span>{row.zone}</span>
                    <span>{row.ward}</span>
                    <span>{row.material}</span>
                    <span className="font-semibold text-teal-800">{formatTons(row.kg)}</span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {activeDrilldown === "average" && (
        <Card className="overflow-hidden border-cyan-200 bg-gradient-to-br from-white via-cyan-50/50 to-sky-50/40 shadow-sm">
          <CardHeader className="pb-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle className="flex items-center gap-2"><Activity className="h-5 w-5 text-cyan-700" /> Average Per Day Drill Down</CardTitle>
                <p className="text-sm text-muted-foreground">Shows each day against the 7-day average so low/high collection days are visible immediately.</p>
              </div>
              <Badge className="bg-cyan-100 text-cyan-800 hover:bg-cyan-100">Average {formatTons(collection.avgPerDayKg)}</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-7">
              {collection.averageDetails.map((day) => (
                <div key={day.date} className="rounded-3xl border bg-white p-4">
                  <p className="text-sm font-semibold">{day.label}</p>
                  <p className="mt-2 text-2xl font-bold text-cyan-800">{day.tons} t</p>
                  <p className={`mt-1 text-xs font-medium ${day.deltaTons >= 0 ? "text-teal-700" : "text-rose-700"}`}>
                    {day.deltaTons >= 0 ? "+" : ""}{day.deltaTons} t vs avg
                  </p>
                  <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
                    <span className="block h-full rounded-full bg-cyan-500" style={{ width: `${Math.min(100, collection.avgPerDayKg ? (day.kg / collection.avgPerDayKg) * 50 : 0)}%` }} />
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">{day.entries} weighments</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {activeDrilldown === "coverage" && (
        <Card className="overflow-hidden border-teal-200 bg-gradient-to-br from-white via-teal-50/50 to-cyan-50/40 shadow-sm">
          <CardHeader className="pb-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-teal-700" />
                  Pickup Coverage Drill Down
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  Last 7 days from {dateFrom} to {dateTo}. Sorted by lowest coverage first so supervisors can act quickly.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge className="bg-teal-100 text-teal-800 hover:bg-teal-100">{collection.coverageDone} covered</Badge>
                <Badge className="bg-rose-100 text-rose-800 hover:bg-rose-100">{collection.coverageMissed} missed</Badge>
                <Badge variant="outline">{collection.coverageTotal} total points</Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {collection.coverageDetails.length ? (
              <div className="overflow-hidden rounded-3xl border bg-white">
                <div className="grid grid-cols-[1fr_0.8fr_0.8fr_0.8fr_1fr_0.8fr_1fr] bg-slate-50 px-4 py-3 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                  <span>Date</span>
                  <span>Zone</span>
                  <span>Ward</span>
                  <span>Route</span>
                  <span>Truck</span>
                  <span>Points</span>
                  <span>Coverage</span>
                </div>
                <div className="divide-y">
                  {collection.coverageDetails.map((row, index) => (
                    <div key={`${row.date}-${row.route}-${row.truck}-${index}`} className="grid grid-cols-[1fr_0.8fr_0.8fr_0.8fr_1fr_0.8fr_1fr] items-center gap-2 px-4 py-3 text-sm">
                      <span className="font-medium">{row.date}</span>
                      <span>{row.zone}</span>
                      <span>{row.ward}</span>
                      <span>{row.route}</span>
                      <span className="font-mono text-xs">{row.truck}</span>
                      <span>{row.covered}/{row.totalPoints}</span>
                      <span>
                        <span className="mb-1 flex items-center justify-between gap-2">
                          <strong className={row.percent < 70 ? "text-rose-700" : row.percent < 90 ? "text-amber-700" : "text-teal-700"}>{row.percent}%</strong>
                          <Badge variant={row.percent >= 90 ? "default" : "secondary"}>{row.status}</Badge>
                        </span>
                        <span className="block h-2 overflow-hidden rounded-full bg-muted">
                          <span
                            className={`block h-full rounded-full ${row.percent < 70 ? "bg-rose-500" : row.percent < 90 ? "bg-amber-400" : "bg-teal-500"}`}
                            style={{ width: `${Math.min(100, row.percent)}%` }}
                          />
                        </span>
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="rounded-3xl border border-dashed bg-white/70 p-8 text-center">
                <p className="font-semibold text-foreground">No pickup coverage rows found for this 7-day window.</p>
                <p className="mt-1 text-sm text-muted-foreground">If collection exists for older dates, the dashboard window may need a date selector next.</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {activeDrilldown === "fleet" && (
        <Card className="overflow-hidden border-blue-200 bg-gradient-to-br from-white via-blue-50/50 to-cyan-50/40 shadow-sm">
          <CardHeader className="pb-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle className="flex items-center gap-2"><Truck className="h-5 w-5 text-blue-700" /> Fleet Utilization Drill Down</CardTitle>
                <p className="text-sm text-muted-foreground">Live fleet availability by status and zone. Utilization counts active, idle, moving and dumping vehicles as available.</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">{fleet.utilization}% utilized</Badge>
                <Badge className="bg-teal-100 text-teal-800 hover:bg-teal-100">{fleet.active} active</Badge>
                <Badge className="bg-rose-100 text-rose-800 hover:bg-rose-100">{fleet.inactive} inactive</Badge>
                <Badge variant="outline">{fleet.spare} spare</Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent className="grid gap-5 xl:grid-cols-[0.8fr_1.2fr]">
            <div className="grid gap-4">
              <div className="rounded-3xl border bg-white p-4">
                <p className="mb-3 text-sm font-semibold">Status mix</p>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadialBarChart innerRadius="24%" outerRadius="95%" data={fleet.statusChart} startAngle={90} endAngle={-270}>
                      <RadialBar dataKey="value" cornerRadius={12} background />
                      <Tooltip formatter={(value: number) => compactNumber(Number(value))} />
                    </RadialBarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="space-y-2">
                {fleet.zones.map((zone) => (
                  <div key={zone.zone} className="rounded-2xl border bg-white p-3">
                    <div className="flex items-center justify-between text-sm font-medium">
                      <span>{zone.zone}</span>
                      <span>{zone.active}/{zone.total} active</span>
                    </div>
                    <div className="mt-2 flex h-2 overflow-hidden rounded-full bg-muted">
                      <span className="bg-teal-500" style={{ width: `${zone.total ? (zone.active / zone.total) * 100 : 0}%` }} />
                      <span className="bg-amber-400" style={{ width: `${zone.total ? (zone.idle / zone.total) * 100 : 0}%` }} />
                      <span className="bg-rose-500" style={{ width: `${zone.total ? (zone.offline / zone.total) * 100 : 0}%` }} />
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">Idle {zone.idle}, inactive {zone.offline}, spare {zone.spare}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="overflow-hidden rounded-3xl border bg-white">
              <div className="grid grid-cols-[1fr_0.8fr_0.8fr_0.9fr_0.8fr_0.6fr_0.7fr] bg-slate-50 px-4 py-3 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                <span>Truck</span><span>Zone</span><span>Ward</span><span>Route</span><span>Status</span><span>Speed</span><span>Spare</span>
              </div>
              <div className="divide-y">
                {fleet.vehicleDetails.length ? fleet.vehicleDetails.map((row, index) => (
                  <div key={`${row.truck}-${index}`} className="grid grid-cols-[1fr_0.8fr_0.8fr_0.9fr_0.8fr_0.6fr_0.7fr] items-center gap-2 px-4 py-3 text-sm">
                    <span className="font-mono text-xs">{row.truck}</span>
                    <span>{row.zone}</span>
                    <span>{row.ward}</span>
                    <span>{row.route}</span>
                    <Badge variant={row.status === "offline" || row.status === "breakdown" ? "destructive" : row.status === "idle" ? "secondary" : "default"}>{row.status}</Badge>
                    <span>{row.speed} km/h</span>
                    <span>{row.spare ? "Yes" : "No"}</span>
                  </div>
                )) : (
                  <div className="p-8 text-center text-sm text-muted-foreground">No live vehicle rows available right now.</div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <section className="grid gap-6 xl:grid-cols-[1.55fr_1fr]">
        <Card className="overflow-hidden border-teal-900/20 bg-gradient-to-br from-slate-950 via-teal-950 to-slate-900 text-white shadow-xl">
          <CardHeader className="pb-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.3em] text-cyan-200">
                  <Sparkles className="h-4 w-4" /> Garbage Collection
                </div>
                <CardTitle className="mt-2 text-3xl">Municipal Collection Pulse</CardTitle>
                <p className="mt-2 max-w-2xl text-sm text-cyan-50/75">
                  Real 7-day dump yard and material-wise collection records, merged with pickup coverage and area distribution.
                </p>
              </div>
              <Badge className="border-cyan-300/30 bg-cyan-300/15 text-cyan-50 hover:bg-cyan-300/15">
                {reportsLoading ? "Syncing reports" : "Live report window"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="grid gap-5 lg:grid-cols-[1.35fr_0.8fr]">
            <div className="rounded-3xl border border-white/10 bg-white/[0.06] p-4 backdrop-blur">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-white">Daily collection trend</p>
                  <p className="text-xs text-cyan-100/65">Tons collected by weighment date</p>
                </div>
                <Badge variant="outline" className="border-white/20 text-cyan-50">Top: {collection.topMaterial}</Badge>
              </div>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={collection.days} margin={{ left: 0, right: 10, top: 10, bottom: 0 }}>
                    <defs>
                      <linearGradient id="collectionFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#5eead4" stopOpacity={0.75} />
                        <stop offset="95%" stopColor="#5eead4" stopOpacity={0.05} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="rgba(255,255,255,0.1)" vertical={false} />
                    <XAxis dataKey="label" stroke="rgba(255,255,255,0.65)" tickLine={false} axisLine={false} />
                    <YAxis stroke="rgba(255,255,255,0.65)" tickLine={false} axisLine={false} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,0.15)", borderRadius: 14, color: "#fff" }} />
                    <Area type="monotone" dataKey="tons" name="Tons" stroke="#5eead4" strokeWidth={3} fill="url(#collectionFill)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div className="grid gap-4">
              <div className="rounded-3xl border border-white/10 bg-white/[0.06] p-4">
                <p className="text-sm font-semibold">Material mix</p>
                <div className="mt-3 h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={collection.materialMix.length ? collection.materialMix : [{ name: "No data", kg: 1 }]} dataKey="kg" nameKey="name" innerRadius={52} outerRadius={78} paddingAngle={3}>
                        {(collection.materialMix.length ? collection.materialMix : [{ name: "No data" }]).map((_, index) => (
                          <Cell key={index} fill={chartColors[index % chartColors.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,0.15)", borderRadius: 14, color: "#fff" }} formatter={(value: number) => formatTons(Number(value))} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="grid gap-2">
                  {collection.materialMix.slice(0, 4).map((item, index) => (
                    <div key={item.name} className="flex items-center justify-between rounded-xl bg-white/[0.06] px-3 py-2 text-sm">
                      <span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full" style={{ background: chartColors[index % chartColors.length] }} />{item.name}</span>
                      <span className="font-semibold">{formatTons(item.kg)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader>
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle className="flex items-center gap-2"><Truck className="h-5 w-5 text-teal-700" /> Fleet Availability</CardTitle>
                <p className="text-sm text-muted-foreground">Active, inactive, spare and live feed status</p>
              </div>
              <Badge variant={isConnected ? "default" : "secondary"}>{isConnected ? "Realtime connected" : "Feed offline"}</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setFleetAvailabilityDrilldown((value) => value === "active" ? null : "active")}
                className={`rounded-2xl bg-teal-50 p-4 text-left text-teal-950 transition hover:-translate-y-0.5 hover:shadow-md ${fleetAvailabilityDrilldown === "active" ? "ring-2 ring-teal-500/50" : ""}`}
              >
                <p className="text-xs uppercase tracking-[0.2em]">Active</p>
                <p className="mt-1 text-3xl font-bold">{fleet.active}</p>
                <p className="mt-1 text-xs opacity-70">Zone and ward drill-down</p>
              </button>
              <button
                type="button"
                onClick={() => setFleetAvailabilityDrilldown((value) => value === "inactive" ? null : "inactive")}
                className={`rounded-2xl bg-rose-50 p-4 text-left text-rose-950 transition hover:-translate-y-0.5 hover:shadow-md ${fleetAvailabilityDrilldown === "inactive" ? "ring-2 ring-rose-500/50" : ""}`}
              >
                <p className="text-xs uppercase tracking-[0.2em]">Inactive</p>
                <p className="mt-1 text-3xl font-bold">{fleet.inactive}</p>
                <p className="mt-1 text-xs opacity-70">Offline and breakdown</p>
              </button>
              <button
                type="button"
                onClick={() => setFleetAvailabilityDrilldown((value) => value === "idle" ? null : "idle")}
                className={`rounded-2xl bg-amber-50 p-4 text-left text-amber-950 transition hover:-translate-y-0.5 hover:shadow-md ${fleetAvailabilityDrilldown === "idle" ? "ring-2 ring-amber-500/50" : ""}`}
              >
                <p className="text-xs uppercase tracking-[0.2em]">Idle</p>
                <p className="mt-1 text-3xl font-bold">{fleet.idle}</p>
                <p className="mt-1 text-xs opacity-70">Stationary vehicles</p>
              </button>
              <button
                type="button"
                onClick={() => setFleetAvailabilityDrilldown((value) => value === "spare" ? null : "spare")}
                className={`rounded-2xl bg-blue-50 p-4 text-left text-blue-950 transition hover:-translate-y-0.5 hover:shadow-md ${fleetAvailabilityDrilldown === "spare" ? "ring-2 ring-blue-500/50" : ""}`}
              >
                <p className="text-xs uppercase tracking-[0.2em]">Spare</p>
                <p className="mt-1 text-3xl font-bold">{fleet.spare}</p>
                <p className="mt-1 text-xs opacity-70">Backup fleet spread</p>
              </button>
            </div>
            {fleetAvailabilityDrilldown && (
              <div className="overflow-hidden rounded-3xl border bg-white">
                <div className="flex items-center justify-between bg-slate-50 px-4 py-3">
                  <div>
                    <p className="text-sm font-semibold capitalize">{fleetAvailabilityDrilldown} vehicles by zone and ward</p>
                    <p className="text-xs text-muted-foreground">Grouped from current live/vehicle status data</p>
                  </div>
                  <Badge variant="outline">
                    {fleet.availabilityBreakdowns[fleetAvailabilityDrilldown].reduce((sum, row) => sum + row.count, 0)} vehicles
                  </Badge>
                </div>
                {fleet.availabilityBreakdowns[fleetAvailabilityDrilldown].length ? (
                  <div className="divide-y">
                    <div className="grid grid-cols-[1fr_1fr_0.7fr_0.7fr_0.7fr_0.7fr] px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                      <span>Zone</span>
                      <span>Ward</span>
                      <span>Total</span>
                      <span>Moving</span>
                      <span>Idle</span>
                      <span>Spare</span>
                    </div>
                    {fleet.availabilityBreakdowns[fleetAvailabilityDrilldown].map((row) => (
                      <div key={`${fleetAvailabilityDrilldown}-${row.zone}-${row.ward}`} className="grid grid-cols-[1fr_1fr_0.7fr_0.7fr_0.7fr_0.7fr] items-center px-4 py-3 text-sm">
                        <span className="font-medium">{row.zone}</span>
                        <span>{row.ward}</span>
                        <span className="font-semibold">{row.count}</span>
                        <span className="text-teal-700">{row.moving}</span>
                        <span className="text-amber-700">{row.idle}</span>
                        <span className="text-blue-700">{row.spare}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-6 text-center text-sm text-muted-foreground">
                    No {fleetAvailabilityDrilldown} vehicles found in the current live snapshot.
                  </div>
                )}
              </div>
            )}
            <div className="h-44 rounded-3xl border bg-muted/20 p-3">
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart innerRadius="28%" outerRadius="95%" data={fleet.statusChart} startAngle={90} endAngle={-270}>
                  <RadialBar dataKey="value" cornerRadius={12} background />
                  <Tooltip formatter={(value: number) => compactNumber(Number(value))} />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-2">
              {fleet.zones.slice(0, 4).map((zone) => (
                <div key={zone.zone} className="rounded-2xl border bg-card p-3">
                  <div className="flex items-center justify-between text-sm font-medium">
                    <span>{zone.zone}</span>
                    <span>{zone.total} vehicles</span>
                  </div>
                  <div className="mt-2 flex h-2 overflow-hidden rounded-full bg-muted">
                    <span className="bg-teal-500" style={{ width: `${zone.total ? (zone.active / zone.total) * 100 : 0}%` }} />
                    <span className="bg-amber-400" style={{ width: `${zone.total ? (zone.idle / zone.total) * 100 : 0}%` }} />
                    <span className="bg-rose-500" style={{ width: `${zone.total ? (zone.offline / zone.total) * 100 : 0}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </section>
      <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <Card className="border-border/70 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><MapPin className="h-5 w-5 text-teal-700" /> Zone and Ward Collection</CardTitle>
            <p className="text-sm text-muted-foreground">Where garbage volume is concentrated across the last 7 days</p>
          </CardHeader>
          <CardContent className="grid gap-5 lg:grid-cols-[1.15fr_0.85fr]">
            <div className="h-72 rounded-3xl border bg-muted/20 p-3">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={collection.zones} layout="vertical" margin={{ left: 20, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="name" width={90} tickLine={false} axisLine={false} />
                  <Tooltip formatter={(value: number) => `${value} t`} />
                  <Bar dataKey="tons" name="Tons" radius={[0, 10, 10, 0]} fill="#0f766e" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-3">
              {collection.wards.map((ward, index) => (
                <div key={`${ward.zone}-${ward.name}`} className="rounded-2xl border bg-gradient-to-r from-card to-teal-50/50 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-semibold">{ward.name}</p>
                      <p className="text-xs text-muted-foreground">{ward.zone}</p>
                    </div>
                    <Badge variant="secondary">#{index + 1}</Badge>
                  </div>
                  <p className="mt-2 text-2xl font-bold text-teal-800">{formatTons(ward.kg)}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="overflow-hidden border-border/70 shadow-sm">
          <CardHeader className="bg-gradient-to-r from-cyan-50 via-white to-emerald-50">
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle className="flex items-center gap-2"><Users className="h-5 w-5 text-cyan-700" /> Citizen Service Signal</CardTitle>
                <p className="text-sm text-muted-foreground">Pilot citizen panel using mock complaint signals until citizen complaint API is wired</p>
              </div>
              <Badge className="bg-cyan-100 text-cyan-800 hover:bg-cyan-100">Pilot data</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-5 p-5">
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-2xl bg-slate-950 p-4 text-white">
                <p className="text-xs uppercase tracking-[0.18em] text-cyan-200">Complaints</p>
                <p className="mt-1 text-3xl font-bold">60</p>
              </div>
              <div className="rounded-2xl bg-emerald-50 p-4 text-emerald-950">
                <p className="text-xs uppercase tracking-[0.18em]">SLA Met</p>
                <p className="mt-1 text-3xl font-bold">{citizenSlaAverage}%</p>
              </div>
              <div className="rounded-2xl bg-amber-50 p-4 text-amber-950">
                <p className="text-xs uppercase tracking-[0.18em]">Repeat Zones</p>
                <p className="mt-1 text-3xl font-bold">3</p>
              </div>
            </div>
            <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
              <div className="h-52 rounded-3xl border bg-muted/20 p-3">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={citizenSignals} dataKey="count" nameKey="label" outerRadius={78} innerRadius={45} paddingAngle={4}>
                      {citizenSignals.map((item) => <Cell key={item.label} fill={item.tone} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-2">
                {citizenSignals.map((item) => (
                  <div key={item.label} className="rounded-2xl border p-3">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">{item.label}</span>
                      <span className="font-bold">{item.count}</span>
                    </div>
                    <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">
                      <span className="block h-full rounded-full" style={{ width: `${item.sla}%`, background: item.tone }} />
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">Resolution SLA {item.sla}%</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="grid gap-2">
              {citizenHotspots.map((item) => (
                <div key={`${item.zone}-${item.ward}`} className="flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-muted/30 px-4 py-3 text-sm">
                  <span><strong>{item.zone}</strong> / {item.ward}</span>
                  <span>{item.complaints} complaints</span>
                  <span className="text-muted-foreground">Avg resolve {item.resolution}</span>
                  <Badge variant={item.sentiment > 75 ? "default" : "secondary"}>Sentiment {item.sentiment}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="overflow-hidden border-rose-200/80 bg-gradient-to-br from-white via-rose-50/40 to-orange-50/60 shadow-sm">
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle className="flex items-center gap-2"><ShieldAlert className="h-5 w-5 text-rose-700" /> Alert Intelligence</CardTitle>
                <p className="text-sm text-muted-foreground">Consolidated active alerts by severity, type and operational category</p>
              </div>
              <Badge className="bg-rose-100 text-rose-800 hover:bg-rose-100">Risk score {alerts.operationsRisk}</Badge>
            </div>
          </CardHeader>
          <CardContent className="grid gap-5 lg:grid-cols-[0.85fr_1.15fr]">
            <div className="space-y-3">
              <div className="rounded-3xl bg-slate-950 p-5 text-white">
                <div className="flex items-center justify-between">
                  <p className="text-xs uppercase tracking-[0.28em] text-rose-200">Active Alerts</p>
                  <Bell className="h-5 w-5 text-rose-200" />
                </div>
                <p className="mt-3 text-5xl font-bold">{alerts.total}</p>
                <p className="mt-2 text-sm text-slate-300">Top signal: {alerts.topType}</p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-2xl border bg-white p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Critical</p>
                  <p className="mt-1 text-3xl font-bold text-rose-700">{alerts.critical}</p>
                </div>
                <div className="rounded-2xl border bg-white p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">High</p>
                  <p className="mt-1 text-3xl font-bold text-orange-600">{alerts.high}</p>
                </div>
              </div>
              <div className="rounded-2xl border bg-white p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Route anomalies</span>
                  <Route className="h-4 w-4 text-teal-700" />
                </div>
                <p className="mt-1 text-2xl font-bold">{compactNumber(routeAnomalies)}</p>
                <p className="text-xs text-muted-foreground">From route performance report window</p>
              </div>
            </div>
            <div className="grid gap-4">
              <div className="h-56 rounded-3xl border bg-white p-3">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={alerts.typeRows} margin={{ left: 0, right: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="name" tickLine={false} axisLine={false} tick={{ fontSize: 11 }} interval={0} angle={-18} textAnchor="end" height={60} />
                    <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
                    <Tooltip />
                    <Bar dataKey="value" name="Alerts" radius={[10, 10, 0, 0]} fill="#e11d48" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="grid gap-2 md:grid-cols-2">
                {alerts.categoryRows.map((item, index) => (
                  <div key={item.name} className="rounded-2xl border bg-white p-3">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">{item.name}</span>
                      <Badge variant="secondary">{item.value}</Badge>
                    </div>
                    <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">
                      <span className="block h-full rounded-full" style={{ width: `${alerts.total ? Math.min(100, (item.value / alerts.total) * 100) : 0}%`, background: chartColors[index % chartColors.length] }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/70 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Gauge className="h-5 w-5 text-teal-700" /> Command Priorities</CardTitle>
            <p className="text-sm text-muted-foreground">What supervisors should look at first</p>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              { icon: AlertTriangle, title: "Stabilize alert backlog", body: `${alerts.critical + alerts.high} critical/high alerts need supervisor acknowledgement.`, tone: "bg-rose-50 text-rose-900" },
              { icon: Building2, title: "Balance collection load", body: `${collection.zones[0]?.name || "Top zone"} is carrying the highest 7-day tonnage.`, tone: "bg-teal-50 text-teal-950" },
              { icon: Clock, title: "Watch route timing", body: `${compactNumber(routeAnomalies)} route anomalies found in the selected report window.`, tone: "bg-amber-50 text-amber-950" },
              { icon: Zap, title: "Spare fleet readiness", body: `${fleet.spare} spare vehicles available or used for continuity.`, tone: "bg-blue-50 text-blue-950" },
            ].map((item) => (
              <div key={item.title} className={`rounded-3xl p-4 ${item.tone}`}>
                <div className="flex items-start gap-3">
                  <div className="rounded-2xl bg-white/70 p-2"><item.icon className="h-5 w-5" /></div>
                  <div>
                    <p className="font-semibold">{item.title}</p>
                    <p className="mt-1 text-sm opacity-80">{item.body}</p>
                  </div>
                </div>
              </div>
            ))}
            <div className="rounded-3xl border bg-muted/20 p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold"><CircleDot className="h-4 w-4 text-teal-700" /> Severity spread</div>
              <div className="h-36">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={alerts.severityRows}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="name" tickLine={false} axisLine={false} />
                    <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
                    <Tooltip />
                    <Line type="monotone" dataKey="value" stroke="#0f766e" strokeWidth={3} dot={{ r: 5 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
};

export default Index;
