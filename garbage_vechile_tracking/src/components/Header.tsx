import {
  AlertTriangle,
  BarChart3,
  Bell,
  ClipboardCheck,
  Database,
  FileText,
  Gauge,
  LayoutDashboard,
  LogOut,
  Map,
  MapPin,
  Route,
  Settings,
  Shield,
  Ticket,
  Truck,
  Twitter,
  User,
  Users,
  Wrench,
} from "lucide-react";
import { useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/hooks/useAuth";
import { apiService } from "@/services/api";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const dateOnly = (value: Date) => value.toISOString().slice(0, 10);
const titleCase = (value: string) => value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());

export default function Header() {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { data: activeAlerts = [] } = useQuery({
    queryKey: ["alerts", "active", "bell"],
    queryFn: () => apiService.getActiveAlerts(),
    refetchInterval: 30 * 1000,
    staleTime: 20 * 1000,
  });
  const today = dateOnly(new Date());
  const { data: todayAlertsPage = {} } = useQuery({
    queryKey: ["alerts", "bell", "today", today],
    queryFn: () => apiService.getAlertsPage({
      date_from: today,
      date_to: today,
      page: 1,
      page_size: 1,
    }),
    refetchInterval: 30 * 1000,
    staleTime: 20 * 1000,
  });
  const visibleAlerts = activeAlerts.slice(0, 3);
  const actionableCount = activeAlerts.filter((alert: any) => ["critical", "high"].includes(String(alert.severity || "").toLowerCase())).length || activeAlerts.length;
  const todayTypes = useMemo(() => {
    const rows: Array<{ type: string; count: number; category: string }> = [];
    const hierarchy = todayAlertsPage.hierarchyBreakdown || {};
    const typeCounts: Record<string, { count: number; category: string }> = {};
    // Use a single hierarchy level here so the bell summary does not count the
    // same alert once per zone, ward, and route.
    (hierarchy.zone || []).forEach((area: any) => {
      (area.types || []).forEach((item: any) => {
        const key = String(item.name || "alert");
        typeCounts[key] ||= { count: 0, category: "" };
        typeCounts[key].count += Number(item.count || 0);
      });
      const dominantCategory = (area.categories || [])[0]?.name;
      if (dominantCategory) {
        Object.keys(typeCounts).forEach((type) => {
          if (!typeCounts[type].category) typeCounts[type].category = dominantCategory;
        });
      }
    });
    Object.entries(typeCounts).forEach(([type, value]) => rows.push({ type, count: value.count, category: value.category || "operations" }));
    if (rows.length === 0 && Array.isArray(todayAlertsPage.types)) {
      todayAlertsPage.types.forEach((type: string) => rows.push({ type, count: 0, category: "operations" }));
    }
    return rows.sort((a, b) => b.count - a.count).slice(0, 6);
  }, [todayAlertsPage.hierarchyBreakdown, todayAlertsPage.types]);
  const todayStatus = todayAlertsPage.counts?.byStatus || {};
  const todaySeverity = todayAlertsPage.counts?.bySeverity || {};
  const todayTotal = Number(todayAlertsPage.total || 0);

  const breadcrumbs = useMemo(() => {
    const segmentMeta: Record<string, { label: string; icon: typeof LayoutDashboard }> = {
      "auth": { label: "Auth", icon: Users },
      "master": { label: "Master Data", icon: Database },
      "zones-wards": { label: "Zones & Wards", icon: MapPin },
      "routes-pickups": { label: "Routes & Pickups", icon: Route },
      "pickup-points": { label: "Pickup Points", icon: MapPin },
      "spare-vehicles": { label: "Spare Vehicles", icon: Wrench },
      "gtc-checkpoint": { label: "GTC Checkpoint", icon: ClipboardCheck },
      "active-trucks": { label: "Active Trucks", icon: Truck },
      "active-alerts": { label: "Active Alerts", icon: AlertTriangle },
      "collection-rate": { label: "Collection Rate", icon: BarChart3 },
      "trips-completed": { label: "Trips Completed", icon: BarChart3 },
      "twitter": { label: "Twitter Mentions", icon: Twitter },
      "alerts": { label: "Alerts", icon: AlertTriangle },
      "reports": { label: "Reports", icon: FileText },
      "analytics": { label: "Analytics", icon: BarChart3 },
      "routes": { label: "Routes", icon: Map },
      "fleet": { label: "Fleet", icon: Truck },
      "tickets": { label: "Tickets", icon: Ticket },
      "users": { label: "Users", icon: Users },
      "settings": { label: "Settings", icon: Settings },
    };

    const toTitle = (value: string) =>
      value
        .replace(/-/g, " ")
        .replace(/\b\w/g, (char) => char.toUpperCase());

    const parts = location.pathname.split("/").filter(Boolean);
    if (parts.length === 0) {
      return [{ label: "Dashboard", path: "/", icon: LayoutDashboard }];
    }

    const items = [{ label: "Dashboard", path: "/", icon: LayoutDashboard }];
    let currentPath = "";

    parts.forEach((part) => {
      currentPath += `/${part}`;
      const meta = segmentMeta[part];
      items.push({
        label: meta?.label ?? toTitle(part),
        path: currentPath,
        icon: meta?.icon ?? LayoutDashboard,
      });
    });

    return items;
  }, [location.pathname]);

  const handleLogout = () => {
    logout();
    navigate('/auth');
  };

  return (
    <div className="flex items-center justify-between flex-1">
      <div className="flex items-center gap-3">
        <div className="hidden sm:flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary/20 via-secondary/15 to-transparent ring-1 ring-primary/20">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.6)]" />
        </div>
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold bg-gradient-to-r from-primary via-secondary to-emerald-500 bg-clip-text text-transparent">
              SwachhPath
            </h1>
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-emerald-600">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Live
            </span>
          </div>
          <p className="text-xs text-muted-foreground/80">Transparent route & collection tracking</p>
        </div>
      </div>
      
      <div className="flex items-center gap-2">
        <div className="hidden md:inline-flex items-center gap-2 rounded-full bg-emerald-500/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-widest text-emerald-600">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
          System Online
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative h-9 w-9 text-muted-foreground hover:text-foreground">
              <Bell className="h-4 w-4" />
              {actionableCount > 0 && (
                <Badge className="absolute -top-0.5 -right-0.5 h-4 min-w-4 flex items-center justify-center p-0 px-1 text-[10px]">
                  {actionableCount > 99 ? "99+" : actionableCount}
                </Badge>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-[390px] overflow-hidden border-orange-300/40 bg-[radial-gradient(circle_at_top_left,rgba(251,146,60,0.20),transparent_32%),linear-gradient(135deg,rgba(255,251,235,0.96),rgba(248,250,252,0.96)_58%,rgba(255,247,237,0.92))] shadow-2xl shadow-orange-950/10 backdrop-blur dark:border-orange-700/35 dark:bg-[radial-gradient(circle_at_top_left,rgba(251,146,60,0.20),transparent_35%),linear-gradient(135deg,rgba(67,20,7,0.40),rgba(2,6,23,0.96)_62%,rgba(15,23,42,0.92))]">
            <DropdownMenuLabel className="flex items-center justify-between border-b border-orange-200/50 bg-gradient-to-r from-orange-100/70 via-white/30 to-slate-100/50 dark:border-orange-900/40 dark:from-orange-950/35 dark:via-slate-950/20 dark:to-slate-900/40">
              <div>
                <span className="bg-gradient-to-r from-orange-700 via-slate-900 to-amber-700 bg-clip-text font-semibold text-transparent dark:from-orange-200 dark:via-slate-100 dark:to-amber-200">Today&apos;s Alert Summary</span>
                <p className="text-xs font-medium text-orange-800/75 dark:text-orange-100/75">{today} | categorized by alert type</p>
              </div>
              <Badge variant="outline" className="border-orange-400/40 bg-orange-100/70 font-bold text-orange-800 shadow-sm dark:border-orange-700/50 dark:bg-orange-950/45 dark:text-orange-100">{todayTotal} today</Badge>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            {todayTotal === 0 ? (
              <DropdownMenuItem disabled>
                <div className="flex flex-col gap-1">
                  <p className="text-sm font-medium">No alerts today</p>
                  <p className="text-xs text-muted-foreground">Current day operations are clear.</p>
                </div>
              </DropdownMenuItem>
            ) : (
              <div className="px-2 py-1">
                <div className="grid grid-cols-3 gap-2">
                  <button onClick={() => navigate("/alerts")} className="rounded-xl border border-destructive/20 bg-destructive/5 p-2 text-left transition hover:bg-destructive/10">
                    <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Open</p>
                    <p className="text-lg font-bold text-destructive">{Number(todayStatus.open || 0)}</p>
                  </button>
                  <button onClick={() => navigate("/alerts")} className="rounded-xl border border-orange-500/20 bg-orange-500/5 p-2 text-left transition hover:bg-orange-500/10">
                    <p className="text-[10px] uppercase tracking-wide text-muted-foreground">High/Critical</p>
                    <p className="text-lg font-bold text-orange-500">{Number(todaySeverity.high || 0) + Number(todaySeverity.critical || 0)}</p>
                  </button>
                  <button onClick={() => navigate("/alerts")} className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-2 text-left transition hover:bg-emerald-500/10">
                    <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Resolved</p>
                    <p className="text-lg font-bold text-emerald-500">{Number(todayStatus.resolved || 0)}</p>
                  </button>
                </div>
                <div className="mt-3 space-y-1.5">
                  {todayTypes.map((item) => (
                    <button
                      key={item.type}
                      onClick={() => navigate(`/alerts?type=${encodeURIComponent(item.type)}&date=${today}`)}
                      className="flex w-full items-center justify-between rounded-xl border border-orange-200/70 bg-white/78 px-3 py-2 text-left shadow-sm shadow-orange-950/5 transition hover:border-orange-300 hover:bg-orange-50/80 dark:border-orange-900/35 dark:bg-slate-950/55 dark:hover:border-orange-700/60 dark:hover:bg-orange-950/20"
                    >
                      <span className="flex min-w-0 items-center gap-2">
                        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-orange-100 text-orange-700 ring-1 ring-orange-200/80 dark:bg-orange-950/50 dark:text-orange-200 dark:ring-orange-800/50">
                          {item.type.includes("speed") || item.type.includes("overspeed") ? <Gauge className="h-3.5 w-3.5" /> : <AlertTriangle className="h-3.5 w-3.5" />}
                        </span>
                        <span className="min-w-0">
                          <p className="truncate text-sm font-bold tracking-tight text-slate-900 dark:text-slate-50">{titleCase(item.type)}</p>
                          <p className="text-xs font-medium text-orange-700/75 dark:text-orange-200/75">Category: {titleCase(item.category)}</p>
                        </span>
                      </span>
                      <Badge className="bg-slate-900 text-amber-100 shadow-sm dark:bg-amber-200 dark:text-slate-950">{item.count}</Badge>
                    </button>
                  ))}
                </div>
              </div>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuLabel className="text-xs text-muted-foreground">Recent active details</DropdownMenuLabel>
            {visibleAlerts.length === 0 ? (
              <DropdownMenuItem disabled>No active alert details</DropdownMenuItem>
            ) : (
              visibleAlerts.map((alert: any) => (
                <DropdownMenuItem key={alert.id} onClick={() => navigate("/alerts")} className="cursor-pointer">
                  <div className="flex w-full flex-col gap-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className="truncate text-sm font-medium">{alert.title || alert.alert_type || "Alert"}</p>
                      <Badge
                        className={
                          alert.severity === "critical"
                            ? "bg-destructive/15 text-destructive"
                            : alert.severity === "high"
                            ? "bg-orange-500/15 text-orange-600"
                            : "bg-muted text-muted-foreground"
                        }
                      >
                        {alert.severity || "medium"}
                      </Badge>
                    </div>
                    <p className="truncate text-xs text-muted-foreground">{alert.vehicle_id || alert.imei || "No vehicle"} | {alert.status}</p>
                  </div>
                </DropdownMenuItem>
              ))
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => navigate("/alerts")} className="cursor-pointer font-medium">
              Open Alerts Command Center
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative h-9 w-9 text-muted-foreground hover:text-foreground">
              <User className="h-4 w-4" />
              {isAdmin && (
                <Shield className="absolute -bottom-1 -right-1 h-3 w-3 text-primary" />
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <span>{user?.name}</span>
                  <Badge variant={isAdmin ? "default" : "secondary"} className="text-xs">
                    {isAdmin ? 'Admin' : 'User'}
                  </Badge>
                </div>
                <span className="text-xs font-normal text-muted-foreground">{user?.email}</span>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => navigate('/settings')}>Settings</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout}>
              <LogOut className="mr-2 h-4 w-4" />
              Logout
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}
