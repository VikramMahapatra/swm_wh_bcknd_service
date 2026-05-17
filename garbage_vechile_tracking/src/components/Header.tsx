import {
  AlertTriangle,
  BarChart3,
  Bell,
  ClipboardCheck,
  Database,
  FileText,
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
import { useAuth } from "@/hooks/useAuth";
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

export default function Header() {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

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
              <Badge className="absolute -top-0.5 -right-0.5 h-4 w-4 flex items-center justify-center p-0 text-[10px]">
                3
              </Badge>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <DropdownMenuLabel>Notifications</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <div className="flex flex-col gap-1">
                <p className="text-sm font-medium">Route Deviation - MH-12-1234</p>
                <p className="text-xs text-muted-foreground">2 minutes ago</p>
              </div>
            </DropdownMenuItem>
            <DropdownMenuItem>
              <div className="flex flex-col gap-1">
                <p className="text-sm font-medium">Missed Pickup - Zone A</p>
                <p className="text-xs text-muted-foreground">15 minutes ago</p>
              </div>
            </DropdownMenuItem>
            <DropdownMenuItem>
              <div className="flex flex-col gap-1">
                <p className="text-sm font-medium">Device Offline - MH-12-5678</p>
                <p className="text-xs text-muted-foreground">1 hour ago</p>
              </div>
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
