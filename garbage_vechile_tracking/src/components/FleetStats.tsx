import { Truck, TrendingUp, AlertTriangle, CheckCircle2, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import { useNavigate } from "react-router-dom";
import { useTrucks, useAlerts } from "@/hooks/useDataQueries";
import { useMemo } from "react";

const FleetStats = () => {
  const navigate = useNavigate();
  const { data: trucksData = [] } = useTrucks();
  const { data: alertsData = [] } = useAlerts();

  // Calculate real-time statistics
  const stats = useMemo(() => {
    const totalTrucks = trucksData.length;
    const activeTrucks = trucksData.filter((t: any) => 
      t.status === "active" && t.current_status !== "offline" && t.current_status !== "breakdown"
    ).length;
    
    // Calculate total trips completed today from all trucks
    const totalTripsCompleted = trucksData.reduce((sum: number, t: any) => 
      sum + (t.trips_completed || 0), 0
    );
    
    // Calculate target based on active trucks (each truck has trips_allowed, default 5)
    const totalTripsAllowed = trucksData.reduce((sum: number, t: any) => 
      sum + (t.trips_allowed || 5), 0
    );
    
    // Active alerts (status = active or pending)
    const activeAlerts = alertsData.filter((a: any) => 
      a.status === "active" || a.status === "pending"
    ).length;
    
    // Collection rate calculation (trips completed vs allowed)
    const collectionRate = totalTripsAllowed > 0 
      ? Math.round((totalTripsCompleted / totalTripsAllowed) * 100)
      : 0;

    return [
      {
        label: "Active Trucks",
        value: activeTrucks.toString(),
        total: totalTrucks.toString(),
        icon: Truck,
        color: "text-success",
        bgColor: "bg-success/10",
        borderColor: "border-l-success",
        trend: activeTrucks > 0 ? `${Math.round((activeTrucks / totalTrucks) * 100)}%` : "0%",
        trendUp: activeTrucks > totalTrucks * 0.7,
        trendLabel: "active now",
        route: "/active-trucks",
      },
      {
        label: "Trips Completed",
        value: totalTripsCompleted.toString(),
        target: totalTripsAllowed.toString(),
        icon: CheckCircle2,
        color: "text-chart-2",
        bgColor: "bg-chart-2/10",
        borderColor: "border-l-chart-2",
        trend: `${collectionRate}%`,
        trendUp: collectionRate >= 70,
        trendLabel: "of daily target",
        route: "/trips-completed",
      },
      {
        label: "Active Alerts",
        value: activeAlerts.toString(),
        icon: AlertTriangle,
        color: "text-warning",
        bgColor: "bg-warning/10",
        borderColor: "border-l-warning",
        trend: activeAlerts === 0 ? "None" : `${activeAlerts}`,
        trendUp: activeAlerts <= 5,
        trendLabel: "requires attention",
        route: "/active-alerts",
      },
      {
        label: "Collection Rate",
        value: `${collectionRate}%`,
        icon: TrendingUp,
        color: "text-primary",
        bgColor: "bg-primary/10",
        borderColor: "border-l-primary",
        trend: collectionRate >= 70 ? "Good" : "Low",
        trendUp: collectionRate >= 70,
        trendLabel: "overall efficiency",
        route: "/collection-rate",
      },
    ];
  }, [trucksData, alertsData]);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat, index) => {
        const Icon = stat.icon;
        return (
          <Card
            key={index}
            className={`p-4 hover:shadow-lg transition-shadow border-l-4 ${stat.borderColor} cursor-pointer`}
            onClick={() => navigate(stat.route)}
          >
            <div className="flex items-start justify-between">
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  {stat.label}
                </p>
                <div className="flex items-baseline gap-2">
                  <h3 className="text-2xl font-bold text-foreground">
                    {stat.value}
                  </h3>
                  {(stat.total || stat.target) && (
                    <span className="text-sm text-muted-foreground font-medium">
                      / {stat.total || stat.target}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1.5">
                  {stat.trendUp ? (
                    <ArrowUpRight className="h-3.5 w-3.5 text-success" />
                  ) : (
                    <ArrowDownRight className="h-3.5 w-3.5 text-destructive" />
                  )}
                  <span className={`text-xs font-semibold ${stat.trendUp ? 'text-success' : 'text-destructive'}`}>
                    {stat.trend}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {stat.trendLabel}
                  </span>
                </div>
              </div>
              <div className={`${stat.bgColor} h-12 w-12 rounded-xl shadow-sm flex items-center justify-center`}>
                <Icon className={`h-6 w-6 ${stat.color}`} />
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
};

export default FleetStats;
