import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  Shield, 
  IdCard, 
  AlertTriangle, 
  Clock, 
  ChevronRight,
  Truck,
  User,
  FileWarning
} from "lucide-react";
import { useTrucks, useDrivers } from "@/hooks/useDataQueries";
import { differenceInDays, parseISO, format } from "date-fns";

interface ExpiryItem {
  id: string;
  name: string;
  type: 'insurance' | 'license' | 'fitness';
  expiryDate: string;
  daysLeft: number;
  status: 'expired' | 'critical' | 'warning' | 'ok';
  entity: 'truck' | 'driver';
  entityId: string;
}

const getExpiryStatus = (daysLeft: number): 'expired' | 'critical' | 'warning' | 'ok' => {
  if (daysLeft < 0) return 'expired';
  if (daysLeft <= 7) return 'critical';
  if (daysLeft <= 30) return 'warning';
  return 'ok';
};

const getExpiryItems = (trucks: any[], drivers: any[]): ExpiryItem[] => {
  const items: ExpiryItem[] = [];
  const today = new Date();

  trucks.forEach(truck => {
    // Only process if insuranceExpiry exists
    if (truck.insuranceExpiry) {
      const daysLeft = differenceInDays(parseISO(truck.insuranceExpiry), today);
      items.push({
        id: `insurance-${truck.id}`,
        name: truck.registrationNumber,
        type: 'insurance',
        expiryDate: truck.insuranceExpiry,
        daysLeft,
        status: getExpiryStatus(daysLeft),
        entity: 'truck',
        entityId: truck.id
      });
    }
  });

  trucks.forEach(truck => {
    // Only process if fitnessExpiry exists
    if (truck.fitnessExpiry) {
      const daysLeft = differenceInDays(parseISO(truck.fitnessExpiry), today);
      items.push({
        id: `fitness-${truck.id}`,
        name: truck.registrationNumber,
        type: 'fitness',
        expiryDate: truck.fitnessExpiry,
        daysLeft,
        status: getExpiryStatus(daysLeft),
        entity: 'truck',
        entityId: truck.id
      });
    }
  });

  drivers.forEach(driver => {
    // Only process if licenseExpiry exists
    if (driver.licenseExpiry) {
      const daysLeft = differenceInDays(parseISO(driver.licenseExpiry), today);
      items.push({
        id: `license-${driver.id}`,
        name: driver.name,
        type: 'license',
        expiryDate: driver.licenseExpiry,
        daysLeft,
        status: getExpiryStatus(daysLeft),
        entity: 'driver',
        entityId: driver.id
      });
    }
  });

  return items.sort((a, b) => a.daysLeft - b.daysLeft);
};

const ExpiryAlerts = () => {
  const [activeTab, setActiveTab] = useState("all");
  const navigate = useNavigate();
  
  // API Hooks
  const { data: trucksData = [] } = useTrucks();
  const { data: driversData = [] } = useDrivers();
  
  // State for API data
  const [trucks, setTrucks] = useState<any[]>([]);
  const [drivers, setDrivers] = useState<any[]>([]);
  
  // Sync API data to state
  useEffect(() => {
    setTrucks(trucksData);
  }, [trucksData]);
  
  useEffect(() => {
    setDrivers(driversData);
  }, [driversData]);
  
  const expiryItems = getExpiryItems(trucks, drivers);

  const allFilteredItems = expiryItems.filter(item => {
    if (activeTab === "all") return item.status !== 'ok';
    if (activeTab === "insurance") return item.type === 'insurance' && item.status !== 'ok';
    if (activeTab === "license") return item.type === 'license' && item.status !== 'ok';
    if (activeTab === "fitness") return item.type === 'fitness' && item.status !== 'ok';
    return false;
  });

  // Show only top 6 items on dashboard
  const filteredItems = allFilteredItems.slice(0, 6);

  const expiredCount = expiryItems.filter(i => i.status === 'expired').length;
  const criticalCount = expiryItems.filter(i => i.status === 'critical').length;
  const warningCount = expiryItems.filter(i => i.status === 'warning').length;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'expired':
        return <Badge variant="destructive" className="text-[10px]">Expired</Badge>;
      case 'critical':
        return <Badge className="bg-orange-500 text-white text-[10px]">Critical</Badge>;
      case 'warning':
        return <Badge className="bg-chart-4/80 text-white text-[10px]">Warning</Badge>;
      default:
        return <Badge variant="secondary" className="text-[10px]">OK</Badge>;
    }
  };

  const getTypeIcon = (type: string, entity: string) => {
    if (entity === 'driver') return <IdCard className="h-4 w-4" />;
    if (type === 'insurance') return <Shield className="h-4 w-4" />;
    return <Truck className="h-4 w-4" />;
  };

  const getStatusStyles = (status: string) => {
    switch (status) {
      case 'expired':
        return { bg: 'bg-destructive/10', border: 'border-destructive/30', icon: 'text-destructive' };
      case 'critical':
        return { bg: 'bg-orange-500/10', border: 'border-orange-500/30', icon: 'text-orange-500' };
      case 'warning':
        return { bg: 'bg-chart-4/10', border: 'border-chart-4/30', icon: 'text-chart-4' };
      default:
        return { bg: 'bg-muted', border: 'border-border', icon: 'text-muted-foreground' };
    }
  };

  return (
    <Card className="h-full flex flex-col overflow-hidden">
      <CardHeader className="p-4 border-b border-border bg-muted/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileWarning className="h-5 w-5 text-warning" />
            <h2 className="text-lg font-semibold text-foreground">Expiry Alerts</h2>
          </div>
          <div className="flex gap-1.5">
            {expiredCount > 0 && (
              <Badge variant="destructive" className="text-xs">{expiredCount}</Badge>
            )}
            {criticalCount > 0 && (
              <Badge className="bg-orange-500 text-white text-xs">{criticalCount}</Badge>
            )}
            {warningCount > 0 && (
              <Badge className="bg-chart-4/80 text-white text-xs">{warningCount}</Badge>
            )}
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="p-0 flex-1 flex flex-col">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
          <div className="px-4 py-2 border-b border-border">
            <TabsList className="grid w-full grid-cols-4 h-8">
              <TabsTrigger value="all" className="text-xs">All</TabsTrigger>
              <TabsTrigger value="insurance" className="text-xs">Insurance</TabsTrigger>
              <TabsTrigger value="license" className="text-xs">License</TabsTrigger>
              <TabsTrigger value="fitness" className="text-xs">Fitness</TabsTrigger>
            </TabsList>
          </div>

          <ScrollArea className="flex-1">
            <div className="p-4 space-y-3">
              {filteredItems.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No expiring items in this category</p>
                </div>
              ) : (
                filteredItems.map(item => {
                  const styles = getStatusStyles(item.status);
                  return (
                    <div 
                      key={item.id}
                      className={`p-4 rounded-lg border ${styles.border} ${styles.bg} transition-all hover:shadow-sm`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2.5 min-w-0">
                          <div className={`p-1.5 rounded-md ${styles.bg}`}>
                            <span className={styles.icon}>
                              {getTypeIcon(item.type, item.entity)}
                            </span>
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="font-medium text-sm text-foreground truncate">{item.name}</span>
                              {item.entity === 'driver' ? (
                                <User className="h-3 w-3 text-muted-foreground shrink-0" />
                              ) : (
                                <Truck className="h-3 w-3 text-muted-foreground shrink-0" />
                              )}
                            </div>
                            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                              <span className="capitalize">{item.type}</span>
                              <span>•</span>
                              <span>{format(parseISO(item.expiryDate), 'dd MMM yyyy')}</span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          {getStatusBadge(item.status)}
                          <span className={`text-xs font-semibold ${
                            item.daysLeft < 0 ? 'text-destructive' :
                            item.daysLeft <= 7 ? 'text-orange-600' :
                            'text-muted-foreground'
                          }`}>
                            {item.daysLeft < 0 
                              ? `${Math.abs(item.daysLeft)}d ago` 
                              : `${item.daysLeft}d`}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </ScrollArea>
        </Tabs>
        
        <div className="p-3 border-t border-border bg-muted/20">
          <div className="flex items-center justify-between mb-2">
            {allFilteredItems.length > 6 && (
              <span className="text-xs text-muted-foreground">
                Showing 6 of {allFilteredItems.length} alerts
              </span>
            )}
          </div>
          <Button 
            variant="ghost" 
            className="w-full justify-between text-sm h-9"
            onClick={() => navigate("/reports?tab=expiry")}
          >
            View Full Report
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default ExpiryAlerts;
