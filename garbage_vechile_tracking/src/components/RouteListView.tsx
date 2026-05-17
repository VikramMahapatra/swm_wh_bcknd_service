import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  Route, MapPin, Truck, Clock, ArrowRight, 
  Plus, Edit, Trash2, Eye, Search 
} from "lucide-react";
import { RouteData, trucks } from "@/data/fleetData";

interface RouteListViewProps {
  routes: RouteData[];
  selectedRoute: RouteData | null;
  filterType: "all" | "primary" | "secondary";
  onFilterChange: (type: "all" | "primary" | "secondary") => void;
  onSelectRoute: (route: RouteData) => void;
  onEditRoute: (route: RouteData) => void;
  onDeleteRoute: (routeId: string) => void;
  onCreateRoute: (type: "primary" | "secondary") => void;
}

export default function RouteListView({
  routes,
  selectedRoute,
  filterType,
  onFilterChange,
  onSelectRoute,
  onEditRoute,
  onDeleteRoute,
  onCreateRoute,
}: RouteListViewProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const normalizedQuery = searchQuery.trim().toLowerCase();

  const filteredRoutes = routes.filter((route) => {
    if (filterType !== "all" && route.type !== filterType) return false;
    if (!normalizedQuery) return true;
    const assignedTruck = getAssignedTruckInfo(route.assignedTruck);
    return (
      route.name.toLowerCase().includes(normalizedQuery) ||
      route.code.toLowerCase().includes(normalizedQuery) ||
      route.assignedTruck?.toLowerCase().includes(normalizedQuery) ||
      assignedTruck?.truckNumber.toLowerCase().includes(normalizedQuery) ||
      assignedTruck?.driver.toLowerCase().includes(normalizedQuery)
    );
  });

  const getAssignedTruckInfo = (truckId?: string) => {
    if (!truckId) return null;
    return trucks.find(t => t.id === truckId);
  };

  const getPointTypeIcon = (type: string) => {
    switch (type) {
      case "pickup": return <div className="w-2 h-2 rounded-full bg-green-500" />;
      case "gtp": return <div className="w-2 h-2 rounded-full bg-amber-500" />;
      case "dumping": return <div className="w-2 h-2 rounded-full bg-red-500" />;
      default: return <div className="w-2 h-2 rounded-full bg-gray-500" />;
    }
  };

  return (
    <div className="grid lg:grid-cols-3 gap-4">
      {/* Route List */}
      <Card className="lg:col-span-1">
        <CardHeader className="pb-3">
          <div className="relative mb-3">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Search routes, trucks, drivers..."
              className="pl-9 h-9"
            />
          </div>
          <div className="flex gap-1 mb-3">
            {(["all", "primary", "secondary"] as const).map((type) => (
              <Button
                key={type}
                variant={filterType === type ? "default" : "outline"}
                size="sm"
                className="flex-1 text-xs capitalize"
                onClick={() => onFilterChange(type)}
              >
                {type}
              </Button>
            ))}
          </div>
          <div className="flex gap-2">
            <Button 
              size="sm" 
              className="flex-1 text-xs"
              variant="outline"
              onClick={() => onCreateRoute("primary")}
            >
              <Plus className="h-3 w-3 mr-1" />
              Primary
            </Button>
            <Button 
              size="sm" 
              className="flex-1 text-xs"
              variant="outline"
              onClick={() => onCreateRoute("secondary")}
            >
              <Plus className="h-3 w-3 mr-1" />
              Secondary
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <ScrollArea className="h-[500px]">
            {filteredRoutes.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">
                <Route className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No routes found</p>
              </div>
            ) : (
              filteredRoutes.map((route) => {
                const truck = getAssignedTruckInfo(route.assignedTruck);
                return (
                  <div
                    key={route.id}
                    onClick={() => onSelectRoute(route)}
                    className={`p-4 border-b border-border cursor-pointer hover:bg-muted/50 transition-colors ${
                      selectedRoute?.id === route.id ? "bg-primary/10 border-l-2 border-l-primary" : ""
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold text-sm">{route.name}</h3>
                      <Badge variant={route.status === "active" ? "default" : "secondary"} className="text-xs">
                        {route.status}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2 mb-2">
                      <Badge 
                        variant="outline" 
                        className={`text-xs capitalize ${
                          route.type === "primary" ? "border-primary text-primary" : "border-secondary text-secondary"
                        }`}
                      >
                        {route.type}
                      </Badge>
                      <span className="text-xs text-muted-foreground">{route.totalPickupPoints || route.total_pickup_points || 0} points</span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Route className="h-3 w-3" /> {route.distance || `${route.estimated_distance || route.estimatedDistance || 0} km`}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" /> {route.estimated_time || route.estimatedTime || 0} min
                      </span>
                    </div>
                    {truck && (
                      <div className="mt-2 pt-2 border-t border-border">
                        <div className="flex items-center gap-2 text-xs">
                          <Truck className="h-3 w-3 text-primary" />
                          <span>{truck.truckNumber}</span>
                          <span className="text-muted-foreground">• {truck.driver}</span>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Route Details */}
      <Card className="lg:col-span-2">
        {selectedRoute ? (
          <>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Route className="h-5 w-5" />
                    {selectedRoute.name}
                  </CardTitle>
                  <div className="flex items-center gap-2 mt-2">
                    <Badge variant="outline" className="capitalize">{selectedRoute.type}</Badge>
                    <Badge variant={selectedRoute.status === "active" ? "default" : "secondary"}>
                      {selectedRoute.status}
                    </Badge>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => onEditRoute(selectedRoute)}>
                    <Edit className="h-4 w-4 mr-1" /> Edit Route
                  </Button>
                  <Button 
                    variant="destructive" 
                    size="sm"
                    onClick={() => onDeleteRoute(selectedRoute.id)}
                  >
                    <Trash2 className="h-4 w-4 mr-1" /> Delete
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-3 gap-4 mb-6">
                <div className="text-center p-4 bg-muted/50 rounded-lg">
                  <p className="text-2xl font-bold text-primary">{selectedRoute.distance || `${selectedRoute.estimated_distance || selectedRoute.estimatedDistance || 0} km`}</p>
                  <p className="text-sm text-muted-foreground">Total Distance</p>
                </div>
                <div className="text-center p-4 bg-muted/50 rounded-lg">
                  <p className="text-2xl font-bold text-primary">{selectedRoute.estimated_time || selectedRoute.estimatedTime || 0} min</p>
                  <p className="text-sm text-muted-foreground">Estimated Time</p>
                </div>
                <div className="text-center p-4 bg-muted/50 rounded-lg">
                  <p className="text-2xl font-bold text-primary">{selectedRoute.totalPickupPoints || selectedRoute.total_pickup_points || 0}</p>
                  <p className="text-sm text-muted-foreground">Total Points</p>
                </div>
              </div>

              {/* Route Flow Visualization - Only show if points exist */}
              {selectedRoute.points && selectedRoute.points.length > 0 && (
                <div className="mb-6 p-4 bg-muted/30 rounded-lg">
                  <h4 className="font-semibold mb-3 text-sm">Route Flow</h4>
                  <div className="flex items-center gap-2 overflow-x-auto pb-2">
                    {selectedRoute.points.map((point, index) => (
                    <div key={point.id} className="flex items-center gap-2">
                      <div className="flex flex-col items-center min-w-fit">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white ${
                          point.type === "pickup" ? "bg-green-500" :
                          point.type === "gtp" ? "bg-amber-500" :
                          "bg-red-500"
                        }`}>
                          {point.order}
                        </div>
                        <p className="text-xs mt-1 max-w-[80px] truncate text-center">{point.name}</p>
                        {point.scheduledTime && (
                          <p className="text-[10px] text-primary font-medium">⏰ {point.scheduledTime}</p>
                        )}
                        <p className="text-[10px] text-muted-foreground capitalize">{point.type}</p>
                      </div>
                      {index < selectedRoute.points.length - 1 && (
                        <ArrowRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                      )}
                    </div>
                  ))}
                </div>
              </div>
              )}

              {/* Detailed Points List - Only show if points exist */}
              {selectedRoute.points && selectedRoute.points.length > 0 && (
                <>
                  <h4 className="font-semibold mb-3">Route Points Detail</h4>
                  <div className="space-y-2 max-h-[200px] overflow-y-auto">
                    {selectedRoute.points.map((point, index) => (
                  <div key={point.id} className="flex items-center gap-3 p-3 bg-muted/30 rounded-lg">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                      point.type === "pickup" ? "bg-green-500 text-white" :
                      point.type === "gtp" ? "bg-amber-500 text-white" :
                      "bg-red-500 text-white"
                    }`}>
                      {point.order}
                    </div>
                    <div className="flex-1">
                      <p className="font-medium">{point.name}</p>
                      <div className="flex items-center gap-2">
                        <p className="text-xs text-muted-foreground capitalize">{point.type}</p>
                        {point.scheduledTime && (
                          <>
                            <span className="text-xs text-muted-foreground">•</span>
                            <p className="text-xs text-primary font-medium flex items-center gap-1">
                              <Clock className="h-3 w-3" /> {point.scheduledTime}
                            </p>
                          </>
                        )}
                      </div>
                    </div>
                    <div className="text-xs text-muted-foreground text-right">
                      <p>{point.position.lat.toFixed(4)}</p>
                      <p>{point.position.lng.toFixed(4)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </>
            )}

              {selectedRoute.assignedTruck && (
                <div className="mt-6 p-4 bg-primary/10 rounded-lg">
                  <h4 className="font-semibold mb-2">Assigned Truck</h4>
                  {(() => {
                    const truck = getAssignedTruckInfo(selectedRoute.assignedTruck);
                    return truck ? (
                      <div className="flex items-center gap-4">
                        <Truck className="h-8 w-8 text-primary" />
                        <div>
                          <p className="font-medium">{truck.truckNumber}</p>
                          <p className="text-sm text-muted-foreground">Driver: {truck.driver}</p>
                        </div>
                        <Badge className="ml-auto capitalize">{truck.status}</Badge>
                      </div>
                    ) : null;
                  })()}
                </div>
              )}
            </CardContent>
          </>
        ) : (
          <CardContent className="h-[500px] flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <Route className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>Select a route to view details</p>
              <p className="text-sm mt-2">Or create a new route to get started</p>
            </div>
          </CardContent>
        )}
      </Card>
    </div>
  );
}
