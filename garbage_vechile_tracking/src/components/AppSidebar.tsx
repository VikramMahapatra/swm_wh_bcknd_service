import { 
  LayoutDashboard, 
  Truck, 
  Map, 
  FileText, 
  AlertTriangle,
  Settings,
  MapPin,
  Users,
  BarChart3,
  Twitter,
  Database,
  Ticket,
  User,
  Building2,
  Route,
  Wrench,
  LogOut,
  ClipboardCheck
} from 'lucide-react';
import { NavLink } from '@/components/NavLink';
import { useAuth } from '@/hooks/useAuth';
import { useNavigate } from 'react-router-dom';

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
  useSidebar,
} from '@/components/ui/sidebar';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

const menuItems = [
  { title: 'Dashboard', url: '/', icon: LayoutDashboard },
  { title: 'Fleet', url: '/fleet', icon: Truck },
  { title: 'Spare Vehicles', url: '/spare-vehicles', icon: Wrench },
  { title: 'Routes', url: '/routes', icon: Map },
  { title: 'Pickup Points', url: '/pickup-points', icon: MapPin },
  { title: 'Alerts', url: '/alerts', icon: AlertTriangle },
  { title: 'Reports', url: '/reports', icon: FileText },
  { title: 'Analytics', url: '/analytics', icon: BarChart3 },
  { title: 'GTC Checkpoint', url: '/gtc-checkpoint', icon: ClipboardCheck },
  { title: 'Twitter Mentions', url: '/twitter', icon: Twitter },
  { title: 'Tickets', url: '/tickets', icon: Ticket },
  { title: 'Users', url: '/users', icon: Users },
  { title: 'Settings', url: '/settings', icon: Settings },
];

const masterItems = [
  { title: 'Drivers', url: '/master/drivers', icon: User },
  { title: 'Vendors', url: '/master/vendors', icon: Building2 },
  { title: 'Trucks', url: '/master/trucks', icon: Truck },
  { title: 'Zones & Wards', url: '/master/zones-wards', icon: MapPin },
  { title: 'Routes & Pickups', url: '/master/routes-pickups', icon: Route },
];

export function AppSidebar() {
  const { open } = useSidebar();
  const { isAdmin, user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/auth');
  };

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b border-emerald-200/60 bg-gradient-to-r from-emerald-50/80 via-background to-amber-50/60 p-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary/15 to-secondary/20 ring-1 ring-primary/20 flex items-center justify-center">
            <Truck className="w-5 h-5 text-primary" />
          </div>
          {open && (
            <div className="flex flex-col">
              <span className="font-semibold text-sm text-emerald-700">Swachh Seva</span>
              <span className="text-xs text-emerald-600/80">Swachh Bharat Mission</span>
            </div>
          )}
        </div>
      </SidebarHeader>
      
      <SidebarContent className="bg-gradient-to-b from-emerald-50/40 via-background to-amber-50/30">
        <SidebarGroup>
          <SidebarGroupLabel className="text-[10px] uppercase tracking-[0.2em] text-emerald-700/70">Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {menuItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <NavLink 
                      to={item.url} 
                      end={item.url === '/'}
                      className="group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted-foreground transition-all hover:bg-primary/10 hover:text-primary"
                      activeClassName="bg-gradient-to-r from-primary/15 via-secondary/15 to-transparent text-foreground shadow-sm ring-1 ring-primary/15 [&>span:first-child]:bg-primary/15 [&>span:first-child]:text-primary"
                    >
                      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted/50 text-muted-foreground transition-all group-hover:bg-primary/15 group-hover:text-primary">
                        <item.icon className="h-4 w-4" />
                      </span>
                      <span>{item.title}</span>
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        
        {isAdmin && (
          <SidebarGroup>
            <SidebarGroupLabel className="flex items-center gap-2 text-[10px] uppercase tracking-[0.2em] text-emerald-700/70">
              <Database className="h-3 w-3" /> Master Entries
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {masterItems.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton asChild>
                      <NavLink 
                        to={item.url}
                        className="group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted-foreground transition-all hover:bg-primary/10 hover:text-primary"
                        activeClassName="bg-gradient-to-r from-primary/15 via-secondary/15 to-transparent text-foreground shadow-sm ring-1 ring-primary/15 [&>span:first-child]:bg-primary/15 [&>span:first-child]:text-primary"
                      >
                        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted/50 text-muted-foreground transition-all group-hover:bg-primary/15 group-hover:text-primary">
                          <item.icon className="h-4 w-4" />
                        </span>
                        <span>{item.title}</span>
                      </NavLink>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>

      <SidebarFooter className="border-t border-emerald-200/60 bg-gradient-to-r from-emerald-50/70 via-background to-amber-50/50 p-3">
        {open ? (
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 px-2">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary/15 to-secondary/20 ring-1 ring-primary/20 flex items-center justify-center">
                <User className="w-4 h-4 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{user?.name}</p>
                <Badge variant={isAdmin ? "default" : "secondary"} className="text-[10px] h-4">
                  {isAdmin ? 'Admin' : 'User'}
                </Badge>
              </div>
            </div>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleLogout}
              className="w-full justify-start gap-2 bg-white/70 hover:bg-white"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </Button>
          </div>
        ) : (
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={handleLogout}
            className="w-full"
            title="Logout"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
