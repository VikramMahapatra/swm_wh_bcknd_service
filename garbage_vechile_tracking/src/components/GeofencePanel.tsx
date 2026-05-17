import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  MapPin, 
  Pencil, 
  Trash2, 
  Eye, 
  EyeOff,
  Route,
  Truck
} from "lucide-react";

export interface TruckData {
  id: string;
  position: { lat: number; lng: number };
  status: string;
  driver: string;
  route: string;
  routeType: "primary" | "secondary";
  speed: number;
}

export interface GeofencePath {
  truckId: string;
  path: { lat: number; lng: number }[];
  enabled: boolean;
  color: string;
}

interface GeofencePanelProps {
  trucks: TruckData[];
  geofences: Record<string, GeofencePath>;
  selectedTruck: string | null;
  isDrawing: boolean;
  currentPathLength: number;
  onSelectTruck: (truckId: string | null) => void;
  onStartDrawing: (truckId: string) => void;
  onSaveGeofence: () => void;
  onCancelDrawing: () => void;
  onToggleGeofence: (truckId: string) => void;
  onDeleteGeofence: (truckId: string) => void;
}

const GeofencePanel = ({
  trucks,
  geofences,
  selectedTruck,
  isDrawing,
  currentPathLength,
  onSelectTruck,
  onStartDrawing,
  onSaveGeofence,
  onCancelDrawing,
  onToggleGeofence,
  onDeleteGeofence,
}: GeofencePanelProps) => {
  const [routeFilter, setRouteFilter] = useState<"all" | "primary" | "secondary">("all");

  const filteredTrucks = trucks.filter(truck => 
    routeFilter === "all" || truck.routeType === routeFilter
  );

  const getStatusColor = (status: string) => {
    switch (status) {
      case "moving": return "bg-success text-success-foreground";
      case "idle": return "bg-warning text-warning-foreground";
      case "dumping": return "bg-chart-1 text-white";
      default: return "bg-muted text-muted-foreground";
    }
  };

  return (
    <Card className="h-full flex flex-col">
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2 mb-3">
          <Route className="h-5 w-5 text-primary" />
          <h3 className="font-semibold text-foreground">Route Geofencing</h3>
        </div>
        
        <Tabs value={routeFilter} onValueChange={(v) => setRouteFilter(v as typeof routeFilter)}>
          <TabsList className="w-full">
            <TabsTrigger value="all" className="flex-1">All</TabsTrigger>
            <TabsTrigger value="primary" className="flex-1">Primary</TabsTrigger>
            <TabsTrigger value="secondary" className="flex-1">Secondary</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {isDrawing && selectedTruck && (
        <div className="p-3 bg-primary/10 border-b border-primary/20">
          <p className="text-sm font-medium text-primary mb-2">
            Drawing geofence for {selectedTruck}
          </p>
          <p className="text-xs text-muted-foreground mb-2">
            Click on the map to add waypoints ({currentPathLength} points added)
          </p>
          <div className="flex gap-2">
            <Button 
              variant="default" 
              size="sm" 
              onClick={onSaveGeofence}
              disabled={currentPathLength < 2}
              className="flex-1"
            >
              Save Geofence
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={onCancelDrawing}
              className="flex-1"
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      <ScrollArea className="flex-1">
        <div className="p-3 space-y-2">
          {filteredTrucks.map((truck) => {
            const hasGeofence = geofences[truck.id]?.path?.length > 0;
            const isSelected = selectedTruck === truck.id;
            
            return (
              <div
                key={truck.id}
                className={`p-3 rounded-lg border transition-all cursor-pointer ${
                  isSelected 
                    ? "border-primary bg-primary/5" 
                    : "border-border hover:border-primary/50 hover:bg-muted/50"
                }`}
                onClick={() => onSelectTruck(isSelected ? null : truck.id)}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Truck className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium text-sm">{truck.id}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Badge variant="outline" className="text-xs">
                      {truck.routeType}
                    </Badge>
                    <Badge className={`text-xs ${getStatusColor(truck.status)}`}>
                      {truck.status}
                    </Badge>
                  </div>
                </div>
                
                <p className="text-xs text-muted-foreground mb-2">
                  {truck.driver} • {truck.route}
                </p>

                {isSelected && (
                  <div className="flex gap-2 mt-3 pt-3 border-t border-border">
                    {hasGeofence ? (
                      <>
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1"
                          onClick={(e) => {
                            e.stopPropagation();
                            onToggleGeofence(truck.id);
                          }}
                        >
                          {geofences[truck.id]?.enabled ? (
                            <><EyeOff className="h-3 w-3 mr-1" /> Hide</>
                          ) : (
                            <><Eye className="h-3 w-3 mr-1" /> Show</>
                          )}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            onStartDrawing(truck.id);
                          }}
                        >
                          <Pencil className="h-3 w-3" />
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteGeofence(truck.id);
                          }}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </>
                    ) : (
                      <Button
                        variant="default"
                        size="sm"
                        className="w-full"
                        onClick={(e) => {
                          e.stopPropagation();
                          onStartDrawing(truck.id);
                        }}
                        disabled={isDrawing}
                      >
                        <MapPin className="h-3 w-3 mr-1" />
                        Draw Route Geofence
                      </Button>
                    )}
                  </div>
                )}

                {hasGeofence && !isSelected && (
                  <div className="flex items-center gap-1 mt-2">
                    <div 
                      className="h-2 w-2 rounded-full" 
                      style={{ backgroundColor: geofences[truck.id]?.color }}
                    />
                    <span className="text-xs text-muted-foreground">
                      Geofence: {geofences[truck.id]?.enabled ? "Active" : "Hidden"}
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </ScrollArea>

      <div className="p-3 border-t border-border bg-muted/30">
        <p className="text-xs text-muted-foreground text-center">
          Select a truck and draw the route path on the map
        </p>
      </div>
    </Card>
  );
};

export default GeofencePanel;
