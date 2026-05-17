import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { ActionDropdown } from "@/components/ActionDropdown";
import {
  Brain,
  TrendingUp,
  AlertTriangle,
  Target,
  Zap,
  Route,
  Users,
  Gauge,
  Eye,
  Sparkles,
  ArrowUp,
  ArrowDown,
  Clock,
  MapPin,
  Fuel,
  Weight,
  Camera,
  Shield,
  RefreshCw,
} from "lucide-react";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { PageHeader } from "@/components/PageHeader";

// AI Predictions Data
const pickupDemandPredictions = [
  { pointId: "PP-K001", location: "Kharadi IT Park", currentLoad: 78, predictedPeak: "2 hrs", priority: "high", confidence: 94 },
  { pointId: "PP-K015", location: "EON Free Zone", currentLoad: 65, predictedPeak: "4 hrs", priority: "medium", confidence: 87 },
  { pointId: "PP-K023", location: "World Trade Center", currentLoad: 82, predictedPeak: "1.5 hrs", priority: "critical", confidence: 96 },
  { pointId: "PP-K007", location: "Zensar Campus", currentLoad: 45, predictedPeak: "8 hrs", priority: "low", confidence: 91 },
];

const anomalyAlerts = [
  { id: 1, type: "idle_time", truck: "MH-12-AB-1234", driverName: "Ramesh Kumar", driverPhone: "+919876543210", vendorName: "FleetCo Transport", vendorPhone: "+919876543220", description: "Unusual 45-min halt outside designated zone", severity: "high", time: "10:23 AM", aiSuggestion: "Verify driver activity - potential unauthorized break" },
  { id: 2, type: "weight_drop", truck: "MH-12-CD-5678", driverName: "Suresh Patil", driverPhone: "+919876543211", vendorName: "Metro Logistics", vendorPhone: "+919876543221", description: "Unexpected 200kg weight reduction mid-route", severity: "critical", time: "09:45 AM", aiSuggestion: "Possible unauthorized dumping - review camera footage" },
  { id: 3, type: "route_deviation", truck: "MH-12-EF-9012", driverName: "Amit Singh", driverPhone: "+919876543212", vendorName: "City Fleet Services", vendorPhone: "+919876543222", description: "15km deviation from assigned route", severity: "medium", time: "11:30 AM", aiSuggestion: "Traffic avoidance detected - route seems optimal" },
  { id: 4, type: "fuel_anomaly", truck: "MH-12-GH-3456", driverName: "Mahesh Jadhav", driverPhone: "+919876543213", vendorName: "FleetCo Transport", vendorPhone: "+919876543220", description: "Fuel consumption 40% higher than expected", severity: "high", time: "08:15 AM", aiSuggestion: "Check for fuel theft or vehicle maintenance issue" },
];

const driverScores = [
  { name: "Rajesh Kumar", id: "DRV-001", score: 94, routeAdherence: 98, missedPickups: 0, idleTime: 12, fuelEfficiency: 92, safetyScore: 96, trend: "up" },
  { name: "Amit Singh", id: "DRV-002", score: 87, routeAdherence: 85, missedPickups: 2, idleTime: 28, fuelEfficiency: 88, safetyScore: 91, trend: "down" },
  { name: "Priya Sharma", id: "DRV-003", score: 91, routeAdherence: 94, missedPickups: 1, idleTime: 15, fuelEfficiency: 95, safetyScore: 88, trend: "up" },
  { name: "Suresh Patil", id: "DRV-004", score: 78, routeAdherence: 72, missedPickups: 4, idleTime: 45, fuelEfficiency: 76, safetyScore: 82, trend: "down" },
  { name: "Meena Desai", id: "DRV-005", score: 96, routeAdherence: 99, missedPickups: 0, idleTime: 8, fuelEfficiency: 94, safetyScore: 98, trend: "up" },
];

const routeOptimizations = [
  { routeId: "RT-001", currentTime: "4.2 hrs", optimizedTime: "3.1 hrs", savings: "26%", fuelSaved: "12L", suggestion: "Reorder pickups 5,6,7 based on traffic patterns" },
  { routeId: "RT-003", currentTime: "5.8 hrs", optimizedTime: "4.5 hrs", savings: "22%", fuelSaved: "18L", suggestion: "Optimize route sequence during peak hours" },
  { routeId: "RT-007", currentTime: "3.5 hrs", optimizedTime: "2.8 hrs", savings: "20%", fuelSaved: "8L", suggestion: "Combine with RT-008 for efficiency" },
];

const weeklyTrend = [
  { day: "Mon", collected: 145, predicted: 150, efficiency: 87 },
  { day: "Tue", collected: 162, predicted: 158, efficiency: 91 },
  { day: "Wed", collected: 138, predicted: 145, efficiency: 84 },
  { day: "Thu", collected: 171, predicted: 168, efficiency: 93 },
  { day: "Fri", collected: 156, predicted: 160, efficiency: 89 },
  { day: "Sat", collected: 189, predicted: 185, efficiency: 95 },
  { day: "Sun", collected: 98, predicted: 100, efficiency: 82 },
];

const zonePerformance = [
  { zone: "Zone A", efficiency: 92, coverage: 98, complaints: 2 },
  { zone: "Zone B", efficiency: 85, coverage: 94, complaints: 5 },
  { zone: "Zone C", efficiency: 78, coverage: 89, complaints: 8 },
  { zone: "Zone D", efficiency: 88, coverage: 96, complaints: 3 },
  { zone: "Zone E", efficiency: 94, coverage: 99, complaints: 1 },
];

const radarData = [
  { metric: "Route Adherence", value: 92, fullMark: 100 },
  { metric: "Fuel Efficiency", value: 85, fullMark: 100 },
  { metric: "Pickup Rate", value: 94, fullMark: 100 },
  { metric: "Time Efficiency", value: 88, fullMark: 100 },
  { metric: "Safety Score", value: 91, fullMark: 100 },
  { metric: "Driver Rating", value: 89, fullMark: 100 },
];

const wasteDistribution = [
  { name: "Organic", value: 45, color: "hsl(var(--success))" },
  { name: "Recyclable", value: 28, color: "hsl(var(--chart-2))" },
  { name: "Hazardous", value: 8, color: "hsl(var(--destructive))" },
  { name: "General", value: 19, color: "hsl(var(--muted-foreground))" },
];

const chartConfig = {
  collected: { label: "Collected (tons)", color: "hsl(var(--primary))" },
  predicted: { label: "AI Predicted", color: "hsl(var(--chart-2))" },
  efficiency: { label: "Efficiency %", color: "hsl(var(--success))" },
};

export default function Analytics() {
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 2000);
  };

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-gradient-to-br from-primary/20 to-chart-2/20 rounded-xl">
            <Brain className="h-8 w-8 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-primary to-chart-2 bg-clip-text text-transparent">
              AI Analytics Hub
            </h1>
            <p className="text-muted-foreground">Predictive insights powered by machine learning</p>
          </div>
        </div>
        <Button onClick={handleRefresh} variant="outline" className="gap-2">
          <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
          Refresh Insights
        </Button>
      </div>

      {/* AI Insight Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-primary/10 to-primary/5 border-primary/20">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">AI Accuracy</p>
                <p className="text-3xl font-bold text-primary">94.2%</p>
                <div className="flex items-center gap-1 text-success text-sm mt-1">
                  <ArrowUp className="h-3 w-3" />
                  <span>+2.3% this week</span>
                </div>
              </div>
              <div className="p-3 bg-primary/20 rounded-full">
                <Target className="h-6 w-6 text-primary" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-warning/10 to-warning/5 border-warning/20">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Anomalies Detected</p>
                <p className="text-3xl font-bold text-warning">12</p>
                <div className="flex items-center gap-1 text-destructive text-sm mt-1">
                  <ArrowUp className="h-3 w-3" />
                  <span>4 critical alerts</span>
                </div>
              </div>
              <div className="p-3 bg-warning/20 rounded-full">
                <AlertTriangle className="h-6 w-6 text-warning" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-success/10 to-success/5 border-success/20">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Route Optimization</p>
                <p className="text-3xl font-bold text-success">23%</p>
                <div className="flex items-center gap-1 text-muted-foreground text-sm mt-1">
                  <Fuel className="h-3 w-3" />
                  <span>38L fuel saved today</span>
                </div>
              </div>
              <div className="p-3 bg-success/20 rounded-full">
                <Route className="h-6 w-6 text-success" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-chart-2/10 to-chart-2/5 border-chart-2/20">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Predictions Made</p>
                <p className="text-3xl font-bold text-chart-2">1,247</p>
                <div className="flex items-center gap-1 text-success text-sm mt-1">
                  <Sparkles className="h-3 w-3" />
                  <span>Real-time analysis</span>
                </div>
              </div>
              <div className="p-3 bg-chart-2/20 rounded-full">
                <Zap className="h-6 w-6 text-chart-2" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Tabs */}
      <Tabs defaultValue="predictions" className="space-y-6">
        <TabsList className="grid w-full grid-cols-5 lg:w-auto lg:inline-grid">
          <TabsTrigger value="predictions" className="gap-2">
            <Eye className="h-4 w-4" />
            <span className="hidden sm:inline">Predictions</span>
          </TabsTrigger>
          <TabsTrigger value="anomalies" className="gap-2">
            <AlertTriangle className="h-4 w-4" />
            <span className="hidden sm:inline">Anomalies</span>
          </TabsTrigger>
          <TabsTrigger value="drivers" className="gap-2">
            <Users className="h-4 w-4" />
            <span className="hidden sm:inline">Driver AI</span>
          </TabsTrigger>
          <TabsTrigger value="routes" className="gap-2">
            <Route className="h-4 w-4" />
            <span className="hidden sm:inline">Route AI</span>
          </TabsTrigger>
          <TabsTrigger value="overview" className="gap-2">
            <Gauge className="h-4 w-4" />
            <span className="hidden sm:inline">Overview</span>
          </TabsTrigger>
        </TabsList>

        {/* Predictions Tab */}
        <TabsContent value="predictions" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Pickup Demand Predictions */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <div className="p-2 bg-warning/20 rounded-lg">
                    <Eye className="h-5 w-5 text-warning" />
                  </div>
                  <div>
                    <CardTitle>Pickup Demand Predictions</CardTitle>
                    <CardDescription>AI predicts pickup point demand patterns</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {pickupDemandPredictions.map((point) => (
                  <div key={point.pointId} className="p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <MapPin className="h-4 w-4 text-muted-foreground" />
                        <span className="font-medium">{point.pointId}</span>
                      </div>
                      <Badge variant={
                        point.priority === "critical" ? "destructive" :
                        point.priority === "high" ? "destructive" :
                        point.priority === "medium" ? "secondary" : "outline"
                      }>
                        {point.priority.toUpperCase()}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground mb-2">{point.location}</p>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>Current Load</span>
                        <span className="font-medium">{point.currentLoad}%</span>
                      </div>
                      <Progress value={point.currentLoad} className="h-2" />
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          Peak in: {point.predictedPeak}
                        </span>
                        <span className="flex items-center gap-1">
                          <Brain className="h-3 w-3" />
                          {point.confidence}% confidence
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Collection Trend Chart */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <div className="p-2 bg-primary/20 rounded-lg">
                    <TrendingUp className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <CardTitle>AI Collection Forecast</CardTitle>
                    <CardDescription>Actual vs AI predicted collection trends</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <ChartContainer config={chartConfig} className="h-[300px] w-full">
                  <AreaChart data={weeklyTrend}>
                    <defs>
                      <linearGradient id="colorCollected" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="colorPredicted" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--chart-2))" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="hsl(var(--chart-2))" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="day" className="text-xs" />
                    <YAxis className="text-xs" />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Area type="monotone" dataKey="collected" stroke="hsl(var(--primary))" fillOpacity={1} fill="url(#colorCollected)" strokeWidth={2} />
                    <Area type="monotone" dataKey="predicted" stroke="hsl(var(--chart-2))" fillOpacity={1} fill="url(#colorPredicted)" strokeWidth={2} strokeDasharray="5 5" />
                  </AreaChart>
                </ChartContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Anomalies Tab */}
        <TabsContent value="anomalies" className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <div className="p-2 bg-destructive/20 rounded-lg">
                  <Shield className="h-5 w-5 text-destructive" />
                </div>
                <div>
                  <CardTitle>AI Anomaly Detection</CardTitle>
                  <CardDescription>Real-time detection of unusual patterns and behaviors</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {anomalyAlerts.map((alert) => (
                <div key={alert.id} className={`p-4 rounded-lg border-l-4 ${
                  alert.severity === "critical" ? "border-l-destructive bg-destructive/5" :
                  alert.severity === "high" ? "border-l-warning bg-warning/5" :
                  "border-l-muted bg-muted/20"
                }`}>
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-3">
                      {alert.type === "idle_time" && <Clock className="h-5 w-5 text-warning" />}
                      {alert.type === "weight_drop" && <Weight className="h-5 w-5 text-destructive" />}
                      {alert.type === "route_deviation" && <Route className="h-5 w-5 text-chart-2" />}
                      {alert.type === "fuel_anomaly" && <Fuel className="h-5 w-5 text-warning" />}
                      <div>
                        <p className="font-medium">{alert.truck}</p>
                        <p className="text-sm text-muted-foreground">{alert.time}</p>
                      </div>
                    </div>
                    <Badge variant={alert.severity === "critical" ? "destructive" : alert.severity === "high" ? "secondary" : "outline"}>
                      {alert.severity.toUpperCase()}
                    </Badge>
                  </div>
                  <p className="text-sm mb-3">{alert.description}</p>
                  <div className="flex items-start gap-2 p-3 bg-primary/5 rounded-lg">
                    <Brain className="h-4 w-4 text-primary mt-0.5" />
                    <div>
                      <p className="text-xs font-medium text-primary">AI Suggestion</p>
                      <p className="text-sm text-muted-foreground">{alert.aiSuggestion}</p>
                    </div>
                  </div>
                  <div className="flex gap-2 mt-3">
                    <Button size="sm" variant="outline" className="gap-1">
                      <Camera className="h-3 w-3" />
                      View Camera
                    </Button>
                    <Button size="sm" variant="outline" className="gap-1">
                      <MapPin className="h-3 w-3" />
                      Track Live
                    </Button>
                    <ActionDropdown
                      truckId={alert.truck}
                      driverName={alert.driverName}
                      driverPhone={alert.driverPhone}
                      vendorName={alert.vendorName}
                      vendorPhone={alert.vendorPhone}
                      alertType={alert.type.replace(/_/g, " ").toUpperCase()}
                      alertMessage={alert.description}
                      size="sm"
                    />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Driver AI Tab */}
        <TabsContent value="drivers" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-2">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <div className="p-2 bg-chart-2/20 rounded-lg">
                    <Users className="h-5 w-5 text-chart-2" />
                  </div>
                  <div>
                    <CardTitle>Driver Performance AI Scoring</CardTitle>
                    <CardDescription>Comprehensive AI-driven driver evaluation</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {driverScores.map((driver, index) => (
                    <div key={driver.id} className="p-4 rounded-lg border hover:bg-accent/50 transition-colors">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-white ${
                            driver.score >= 90 ? "bg-success" :
                            driver.score >= 80 ? "bg-chart-2" :
                            "bg-warning"
                          }`}>
                            {index + 1}
                          </div>
                          <div>
                            <p className="font-medium">{driver.name}</p>
                            <p className="text-sm text-muted-foreground">{driver.id}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-2xl font-bold">{driver.score}</span>
                          {driver.trend === "up" ? (
                            <ArrowUp className="h-5 w-5 text-success" />
                          ) : (
                            <ArrowDown className="h-5 w-5 text-destructive" />
                          )}
                        </div>
                      </div>
                      <div className="grid grid-cols-5 gap-2 text-xs">
                        <div className="text-center p-2 bg-muted/50 rounded">
                          <p className="text-muted-foreground">Route</p>
                          <p className="font-medium">{driver.routeAdherence}%</p>
                        </div>
                        <div className="text-center p-2 bg-muted/50 rounded">
                          <p className="text-muted-foreground">Missed</p>
                          <p className="font-medium">{driver.missedPickups}</p>
                        </div>
                        <div className="text-center p-2 bg-muted/50 rounded">
                          <p className="text-muted-foreground">Idle</p>
                          <p className="font-medium">{driver.idleTime}m</p>
                        </div>
                        <div className="text-center p-2 bg-muted/50 rounded">
                          <p className="text-muted-foreground">Fuel</p>
                          <p className="font-medium">{driver.fuelEfficiency}%</p>
                        </div>
                        <div className="text-center p-2 bg-muted/50 rounded">
                          <p className="text-muted-foreground">Safety</p>
                          <p className="font-medium">{driver.safetyScore}%</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Fleet Performance Radar</CardTitle>
                <CardDescription>Overall fleet health metrics</CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer config={chartConfig} className="h-[350px] w-full">
                  <RadarChart data={radarData}>
                    <PolarGrid className="stroke-border" />
                    <PolarAngleAxis dataKey="metric" className="text-xs" />
                    <Radar name="Fleet Score" dataKey="value" stroke="hsl(var(--primary))" fill="hsl(var(--primary))" fillOpacity={0.3} strokeWidth={2} />
                  </RadarChart>
                </ChartContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Route AI Tab */}
        <TabsContent value="routes" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <div className="p-2 bg-success/20 rounded-lg">
                    <Route className="h-5 w-5 text-success" />
                  </div>
                  <div>
                    <CardTitle>AI Route Optimization</CardTitle>
                    <CardDescription>Smart suggestions to improve route efficiency</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {routeOptimizations.map((route) => (
                  <div key={route.routeId} className="p-4 rounded-lg border bg-gradient-to-r from-success/5 to-transparent">
                    <div className="flex items-center justify-between mb-3">
                      <span className="font-medium">{route.routeId}</span>
                      <Badge variant="outline" className="text-success border-success">
                        {route.savings} faster
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-4 mb-3">
                      <div className="text-center p-2 bg-muted/50 rounded">
                        <p className="text-xs text-muted-foreground">Current Time</p>
                        <p className="font-medium">{route.currentTime}</p>
                      </div>
                      <div className="text-center p-2 bg-success/10 rounded">
                        <p className="text-xs text-muted-foreground">Optimized</p>
                        <p className="font-medium text-success">{route.optimizedTime}</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-2 p-3 bg-primary/5 rounded-lg">
                      <Sparkles className="h-4 w-4 text-primary mt-0.5" />
                      <div>
                        <p className="text-xs font-medium text-primary">AI Recommendation</p>
                        <p className="text-sm text-muted-foreground">{route.suggestion}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 mt-3 text-sm text-muted-foreground">
                      <Fuel className="h-4 w-4" />
                      <span>Potential fuel savings: {route.fuelSaved}</span>
                    </div>
                    <Button size="sm" className="w-full mt-3 gap-2">
                      <Zap className="h-4 w-4" />
                      Apply Optimization
                    </Button>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Zone Performance Analysis</CardTitle>
                <CardDescription>AI-analyzed zone efficiency scores</CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer config={chartConfig} className="h-[300px] w-full">
                  <BarChart data={zonePerformance} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis type="number" domain={[0, 100]} className="text-xs" />
                    <YAxis dataKey="zone" type="category" className="text-xs" width={60} />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Bar dataKey="efficiency" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ChartContainer>
                <div className="mt-4 space-y-2">
                  {zonePerformance.map((zone) => (
                    <div key={zone.zone} className="flex items-center justify-between text-sm">
                      <span>{zone.zone}</span>
                      <div className="flex items-center gap-4">
                        <span className="text-muted-foreground">Coverage: {zone.coverage}%</span>
                        <Badge variant={zone.complaints <= 2 ? "outline" : zone.complaints <= 5 ? "secondary" : "destructive"}>
                          {zone.complaints} complaints
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Waste Distribution</CardTitle>
                <CardDescription>AI-classified waste types</CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer config={chartConfig} className="h-[250px] w-full">
                  <PieChart>
                    <Pie
                      data={wasteDistribution}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={90}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {wasteDistribution.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <ChartTooltip content={<ChartTooltipContent />} />
                  </PieChart>
                </ChartContainer>
                <div className="grid grid-cols-2 gap-2 mt-4">
                  {wasteDistribution.map((item) => (
                    <div key={item.name} className="flex items-center gap-2 text-sm">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                      <span>{item.name}: {item.value}%</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Weekly Efficiency Trend</CardTitle>
                <CardDescription>Collection efficiency over time</CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer config={chartConfig} className="h-[250px] w-full">
                  <LineChart data={weeklyTrend}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="day" className="text-xs" />
                    <YAxis className="text-xs" />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Line type="monotone" dataKey="efficiency" stroke="hsl(var(--success))" strokeWidth={3} dot={{ fill: "hsl(var(--success))", strokeWidth: 2 }} />
                  </LineChart>
                </ChartContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
