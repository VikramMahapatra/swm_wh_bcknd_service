import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Truck, MapPin, Clock, ChevronRight, Gauge } from "lucide-react";
import type { TruckData } from "@/data/fleetData";

interface TruckListProps {
  onSelectTruck: (truck: TruckData) => void;
  selectedTruck: TruckData | null;
  trucks: TruckData[];
}

const TruckList = ({ onSelectTruck, selectedTruck, trucks }: TruckListProps) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "moving":
        return "bg-success/10 text-success border-success/30";
      case "idle":
        return "bg-warning/10 text-warning border-warning/30";
      case "dumping":
        return "bg-chart-1/10 text-chart-1 border-chart-1/30";
      default:
        return "bg-muted text-muted-foreground border-border";
    }
  };

  const getStatusDot = (status: string) => {
    switch (status) {
      case "moving":
        return "bg-success";
      case "idle":
        return "bg-warning";
      case "dumping":
        return "bg-chart-1";
      default:
        return "bg-muted";
    }
  };

  const movingCount = trucks.filter(t => t.status === "moving").length;
  const idleCount = trucks.filter(t => t.status === "idle").length;

  return (
    <Card className="flex flex-col h-[500px] overflow-hidden">
      <div className="p-4 border-b border-border bg-muted/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Truck className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold text-foreground">Fleet Overview</h2>
          </div>
          <Badge variant="secondary" className="bg-primary/10 text-primary">
            {trucks.length} Trucks
          </Badge>
        </div>
        <div className="flex items-center gap-4 mt-3">
          <div className="flex items-center gap-1.5">
            <div className="h-2 w-2 rounded-full bg-success animate-pulse" />
            <span className="text-xs text-muted-foreground">{movingCount} Moving</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="h-2 w-2 rounded-full bg-warning" />
            <span className="text-xs text-muted-foreground">{idleCount} Idle</span>
          </div>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-3 space-y-2">
          {trucks.map((truck) => (
            <div
              key={truck.id}
              className={`p-3 rounded-lg border cursor-pointer transition-all duration-200 hover:shadow-md ${
                selectedTruck?.id === truck.id
                  ? "ring-2 ring-primary border-primary bg-primary/5"
                  : "border-border hover:border-primary/50 bg-card"
              }`}
              onClick={() => onSelectTruck(truck)}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className={`h-2 w-2 rounded-full ${getStatusDot(truck.status)} ${truck.status === 'moving' ? 'animate-pulse' : ''}`} />
                  <div>
                    <h3 className="font-semibold text-sm text-foreground">{truck.truckNumber || truck.id}</h3>
                    <p className="text-xs text-muted-foreground">{truck.id}</p>
                  </div>
                </div>
                <Badge className={`${getStatusColor(truck.status)} text-xs capitalize`} variant="outline">
                  {truck.status}
                </Badge>
              </div>

              <div className="space-y-1.5 text-xs">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <MapPin className="h-3 w-3" />
                  <span className="truncate">{truck.route || "Unassigned"}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground truncate">
                    {truck.driver || "Unassigned"}
                  </span>
                  {truck.status === "moving" && (
                    <div className="flex items-center gap-1 text-success">
                      <Gauge className="h-3 w-3" />
                      <span>{truck.speed} km/h</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between mt-2 pt-2 border-t border-border">
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  {truck.lastUpdate || "Just now"}
                </div>
                <div className="flex items-center gap-1 text-xs font-medium text-foreground">
                  {(truck.tripsCompleted ?? 0)} trips
                  <ChevronRight className="h-3 w-3 text-muted-foreground" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
    </Card>
  );
};

export default TruckList;
