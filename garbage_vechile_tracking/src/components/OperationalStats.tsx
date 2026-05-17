import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useZones, useZoneWards, useVendors, useTrucks, useRoutes, useDrivers } from "@/hooks/useDataQueries";
import { 
  MapPin, 
  Building2, 
  Truck, 
  Users, 
  Route, 
  UserCheck,
  TrendingUp,
  AlertCircle,
  ChevronRight,
  Loader2
} from "lucide-react";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis } from "recharts";
import { useNavigate } from "react-router-dom";

const OperationalStats = () => {
  const navigate = useNavigate();
  const { data: zonesData = [] } = useZones();
  const { data: wardsData = [] } = useZoneWards();
  const { data: vendorsData = [] } = useVendors();
  const { data: trucksData = [] } = useTrucks();
  const { data: routesData = [] } = useRoutes();
  const { data: driversData = [] } = useDrivers();

  // Use data directly instead of duplicating in state
  const zones = zonesData as any[];
  const wards = wardsData as any[];
  const vendors = vendorsData as any[];
  const trucks = trucksData as any[];
  const routes = routesData as any[];
  const drivers = driversData as any[];

  // Calculate stats
  const activeZones = zones.filter(z => z.status === 'active').length;
  const activeWards = wards.filter(w => w.status === 'active').length;
  const activeVendors = vendors.filter(v => v.status === 'active').length;
  const activeTrucks = trucks.filter(t => t.status === 'active').length;
  const maintenanceTrucks = trucks.filter(t => t.status === 'maintenance').length;
  const activeDrivers = drivers.filter(d => d.status === 'active').length;
  const activeRoutes = routes.filter(r => r.status === 'active').length;

  // Truck type distribution
  const truckTypeData = [
    { name: 'Compactor', value: trucks.filter(t => t.type === 'compactor').length, fill: 'hsl(var(--chart-1))' },
    { name: 'Mini-truck', value: trucks.filter(t => t.type === 'mini-truck').length, fill: 'hsl(var(--chart-2))' },
    { name: 'Dumper', value: trucks.filter(t => t.type === 'dumper').length, fill: 'hsl(var(--chart-3))' },
    { name: 'Open-truck', value: trucks.filter(t => t.type === 'open-truck').length, fill: 'hsl(var(--chart-4))' },
  ];

  // Vendor truck distribution
  const vendorData = vendors.map(v => ({
    name: v.companyName?.split(' ')[0] || v.name?.split(' ')[0] || 'Unknown',
    trucks: trucks.filter(t => t.vendorId === v.id).length,
    spare: trucks.filter(t => t.vendorId === v.id && t.isSpare).length,
  }));

  // Zone ward distribution
  const zoneData = zones.map(z => ({
    name: z.code,
    wards: z.totalWards,
  }));

  const chartConfig = {
    compactor: { label: "Compactor", color: "hsl(var(--chart-1))" },
    miniTruck: { label: "Mini-truck", color: "hsl(var(--chart-2))" },
    dumper: { label: "Dumper", color: "hsl(var(--chart-3))" },
    openTruck: { label: "Open-truck", color: "hsl(var(--chart-4))" },
    trucks: { label: "Trucks", color: "hsl(var(--primary))" },
    spare: { label: "Spare", color: "hsl(var(--chart-2))" },
    wards: { label: "Wards", color: "hsl(var(--chart-1))" },
  };

  const stats = [
    { label: "Zones", value: activeZones, total: zones.length, icon: MapPin, color: "text-chart-1", bgColor: "bg-chart-1/10", route: "/master/zones-wards" },
    { label: "Wards", value: activeWards, total: wards.length, icon: Building2, color: "text-chart-2", bgColor: "bg-chart-2/10", route: "/master/zones-wards" },
    { label: "Vendors", value: activeVendors, total: vendors.length, icon: Users, color: "text-chart-3", bgColor: "bg-chart-3/10", route: "/master/vendors" },
    { label: "Trucks", value: activeTrucks, total: trucks.length, icon: Truck, color: "text-chart-4", bgColor: "bg-chart-4/10", route: "/master/trucks" },
    { label: "Drivers", value: activeDrivers, total: drivers.length, icon: UserCheck, color: "text-primary", bgColor: "bg-primary/10", route: "/master/drivers" },
    { label: "Routes", value: activeRoutes, total: routes.length, icon: Route, color: "text-chart-5", bgColor: "bg-chart-5/10", route: "/master/routes-pickups" },
  ];

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-primary" />
          Operational Overview
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Quick Stats Grid */}
        <div className="grid grid-cols-3 gap-2">
          {stats.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <div 
                key={index} 
                className={`${stat.bgColor} rounded-lg p-2.5 flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity group`}
                onClick={() => navigate(stat.route)}
              >
                <Icon className={`h-4 w-4 ${stat.color}`} />
                <div className="flex-1">
                  <p className="text-xs text-muted-foreground">{stat.label}</p>
                  <p className="text-sm font-semibold">
                    {stat.value}<span className="text-xs text-muted-foreground">/{stat.total}</span>
                  </p>
                </div>
                <ChevronRight className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            );
          })}
        </div>

        {/* Maintenance Alert */}
        {maintenanceTrucks > 0 && (
          <div className="flex items-center gap-2 p-2 rounded-lg bg-warning/10 border border-warning/20">
            <AlertCircle className="h-4 w-4 text-warning" />
            <span className="text-sm text-warning">
              {maintenanceTrucks} truck{maintenanceTrucks > 1 ? 's' : ''} in maintenance
            </span>
          </div>
        )}

        {/* Charts Row */}
        <div className="grid grid-cols-2 gap-3">
          {/* Truck Type Distribution */}
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Fleet by Type</p>
            <ChartContainer config={chartConfig} className="h-[120px]">
              <PieChart>
                <Pie
                  data={truckTypeData}
                  cx="50%"
                  cy="50%"
                  innerRadius={25}
                  outerRadius={45}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {truckTypeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <ChartTooltip content={<ChartTooltipContent />} />
              </PieChart>
            </ChartContainer>
            <div className="flex flex-wrap gap-2 justify-center">
              {truckTypeData.map((item, index) => (
                <div key={index} className="flex items-center gap-1 text-xs">
                  <div 
                    className="w-2 h-2 rounded-full" 
                    style={{ backgroundColor: item.fill }}
                  />
                  <span className="text-muted-foreground">{item.name}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Vendor Distribution */}
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Trucks by Vendor</p>
            <ChartContainer config={chartConfig} className="h-[120px]">
              <BarChart data={vendorData} layout="vertical">
                <XAxis type="number" hide />
                <YAxis 
                  dataKey="name" 
                  type="category" 
                  width={50} 
                  tick={{ fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="trucks" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ChartContainer>
          </div>
        </div>

        {/* Zone Summary */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">Zone Coverage</p>
          <div className="flex gap-2">
            {zones.slice(0, 5).map((zone) => (
              <div 
                key={zone.id} 
                className="flex-1 text-center p-2.5 rounded-lg bg-muted/50"
              >
                <p className="text-xs font-semibold">{zone.code}</p>
                <p className="text-lg font-bold text-primary">{zone.totalWards}</p>
                <p className="text-[10px] text-muted-foreground">wards</p>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default OperationalStats;
