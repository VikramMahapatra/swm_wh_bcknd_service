import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, Package, Activity, CheckCircle2 } from "lucide-react";

interface HeroKPIProps {
  todayCollection?: number;
  trend?: number;
  status?: "on-track" | "delayed" | "ahead";
  totalPickups?: number;
  completedPickups?: number;
  trucks: any[];
  onlineDevices: any[];
}

export function HeroKPI({
  todayCollection = 85.2,
  trend = 5.3,
  status = "on-track",
  totalPickups = 120,
  completedPickups = 98,
  trucks,
  onlineDevices,
}: HeroKPIProps) {
  const statusConfig = {
    "on-track": { label: "On Track", color: "text-success", bg: "bg-success/10", border: "border-success/20" },
    delayed: { label: "Delayed", color: "text-warning", bg: "bg-warning/10", border: "border-warning/20" },
    ahead: { label: "Ahead", color: "text-chart-1", bg: "bg-chart-1/10", border: "border-chart-1/20" },
  };

  const currentStatus = statusConfig[status];
  const completionRate = ((completedPickups / totalPickups) * 100).toFixed(1);

  const totalTrucks = trucks.length || 1;
  const movingTrucks = trucks.filter((t) => t.status === "moving").length;
  const idleTrucks = trucks.filter((t) => t.status === "idle").length;
  const dumpingTrucks = trucks.filter((t) => t.status === "dumping").length;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* Today's Collection - Hero Card */}
      <Card
        className={`relative overflow-hidden border ${currentStatus.border} ${currentStatus.bg} cursor-pointer transition hover:shadow-lg`}
        onClick={() => {
          if (typeof window !== "undefined") {
            window.location.href = "/collection-ton-today";
          }
        }}
      >
        <CardContent className="p-5">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Today's Collection
              </p>
              <div className="flex items-baseline gap-2">
                <h2 className="text-4xl font-bold tracking-tight">{todayCollection}</h2>
                <span className="text-lg font-semibold text-muted-foreground">tons</span>
              </div>
              <div className="flex items-center gap-2 mt-2">
                {trend >= 0 ? (
                  <div className="flex items-center gap-1 text-success">
                    <TrendingUp className="h-3.5 w-3.5" />
                    <span className="text-xs font-semibold">+{trend}%</span>
                  </div>
                ) : (
                  <div className="flex items-center gap-1 text-destructive">
                    <TrendingDown className="h-3.5 w-3.5" />
                    <span className="text-xs font-semibold">{trend}%</span>
                  </div>
                )}
                <span className="text-xs text-muted-foreground">vs yesterday</span>
              </div>
            </div>
            <Badge className={`${currentStatus.bg} ${currentStatus.color} border-0`}>
              {currentStatus.label}
            </Badge>
          </div>
          {/* Sparkline placeholder */}
          <div className="mt-4 h-8 flex items-end gap-0.5">
            {[42, 58, 51, 63, 48, 71, 65, 78, 85, 82, 88, 85].map((val, i) => (
              <div
                key={i}
                className={`flex-1 rounded-t ${currentStatus.bg} opacity-60`}
                style={{ height: `${(val / 100) * 100}%` }}
              />
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Collection Progress */}
      <Card className="relative overflow-hidden">
        <CardContent className="p-5">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Collection Progress
              </p>
              <div className="flex items-baseline gap-2">
                <h2 className="text-3xl font-bold tracking-tight">{completionRate}%</h2>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {completedPickups} of {totalPickups} pickups completed
              </p>
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20">
              <CheckCircle2 className="h-6 w-6 text-primary" />
            </div>
          </div>
          {/* Progress ring visual */}
          <div className="mt-4 flex items-center gap-3">
            <div className="relative h-16 w-16">
              <svg className="h-16 w-16 -rotate-90 transform">
                <circle
                  cx="32"
                  cy="32"
                  r="28"
                  stroke="currentColor"
                  strokeWidth="6"
                  fill="transparent"
                  className="text-muted/20"
                />
                <circle
                  cx="32"
                  cy="32"
                  r="28"
                  stroke="currentColor"
                  strokeWidth="6"
                  fill="transparent"
                  strokeDasharray={`${2 * Math.PI * 28}`}
                  strokeDashoffset={`${2 * Math.PI * 28 * (1 - parseFloat(completionRate) / 100)}`}
                  className="text-primary transition-all duration-500"
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-xs font-bold">{completionRate}%</span>
              </div>
            </div>
            <div className="flex-1 space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Completed</span>
                <span className="font-semibold">{completedPickups}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Remaining</span>
                <span className="font-semibold">{totalPickups - completedPickups}</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Active Operations */}
      <Card className="relative overflow-hidden">
        <CardContent className="p-5">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Active Operations
              </p>
              <div className="flex items-baseline gap-2">
                <h2 className="text-3xl font-bold tracking-tight">{onlineDevices.length}</h2>
                <span className="text-sm font-semibold text-muted-foreground">trucks</span>
              </div>
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-success/10 ring-1 ring-success/20">
              <Activity className="h-6 w-6 text-success animate-pulse" />
            </div>
          </div>
          {/* Stacked mini bars */}
          <div className="mt-6 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Moving</span>
              <span className="font-semibold text-success">
                {movingTrucks}
              </span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
              <div
                className="h-full bg-success transition-all duration-500"
                style={{
                  width: `${(movingTrucks / totalTrucks) * 100}%`,
                }}
              />
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Idle</span>
              <span className="font-semibold text-warning">
                {idleTrucks}
              </span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
              <div
                className="h-full bg-warning transition-all duration-500"
                style={{
                  width: `${(idleTrucks / totalTrucks) * 100}%`,
                }}
              />
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Dumping</span>
              <span className="font-semibold text-chart-1">
                {dumpingTrucks}
              </span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
              <div
                className="h-full bg-chart-1 transition-all duration-500"
                style={{
                  width: `${(dumpingTrucks / totalTrucks) * 100}%`,
                }}
              />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
