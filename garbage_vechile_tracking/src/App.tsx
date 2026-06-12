import { Suspense, lazy } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/hooks/useAuth";
import { LoadScript } from "@react-google-maps/api";
import { GOOGLE_MAPS_API_KEY } from "@/data/fleetData";
import Layout from "@/components/Layout";

const Index = lazy(() => import("./pages/Index"));
const Auth = lazy(() => import("./pages/Auth"));
const Fleet = lazy(() => import("./pages/Fleet"));
const RoutesPage = lazy(() => import("./pages/Routes"));
const PickupPoints = lazy(() => import("./pages/PickupPoints"));
const Alerts = lazy(() => import("./pages/Alerts"));
const Reports = lazy(() => import("./pages/Reports"));
const Analytics = lazy(() => import("./pages/Analytics"));
const Users = lazy(() => import("./pages/Users"));
const Settings = lazy(() => import("./pages/Settings"));
const TwitterMentions = lazy(() => import("./pages/TwitterMentions"));
const Tickets = lazy(() => import("./pages/Tickets"));
const MasterDrivers = lazy(() => import("./pages/MasterDrivers"));
const MasterVendors = lazy(() => import("./pages/MasterVendors"));
const MasterVehicles = lazy(() => import("./pages/MasterVehicles"));
const MasterDevices = lazy(() => import("./pages/MasterDevices"));
const MasterDeviceAssignments = lazy(() => import("./pages/MasterDeviceAssignments"));
const MasterZonesWards = lazy(() => import("./pages/MasterZonesWards"));
const MasterRoutesPickups = lazy(() => import("./pages/MasterRoutesPickups"));
const MasterGtsDumpYards = lazy(() => import("./pages/MasterGtsDumpYards"));
const MasterDumpYardWeighmentEntry = lazy(() => import("./pages/MasterDumpYardWeighmentEntry"));
const SpareVehicles = lazy(() => import("./pages/SpareVehicles"));
const ActiveTrucks = lazy(() => import("./pages/ActiveTrucks"));
const TripsCompleted = lazy(() => import("./pages/TripsCompleted"));
const ActiveAlertsDetail = lazy(() => import("./pages/ActiveAlertsDetail"));
const CollectionRate = lazy(() => import("./pages/CollectionRate"));
const NotFound = lazy(() => import("./pages/NotFound"));
const GtcCheckpoint = lazy(() => import("./pages/GtcCheckpoint"));
const CollectionTonToday = lazy(() => import("./pages/CollectionTonToday"));

const queryClient = new QueryClient();

const routeFallback = (
  <div className="flex items-center justify-center min-h-screen text-sm text-muted-foreground">Loading page...</div>
);

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  
  if (isLoading) {
    return <div className="flex items-center justify-center min-h-screen">Loading...</div>;
  }
  
  if (!user) {
    return <Navigate to="/auth" replace />;
  }
  
  return <Layout>{children}</Layout>;
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <LoadScript googleMapsApiKey={GOOGLE_MAPS_API_KEY}>
        <BrowserRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
          <AuthProvider>
            <Suspense fallback={routeFallback}>
              <Routes>
                <Route path="/auth" element={<Auth />} />
                <Route path="/" element={<ProtectedRoute><Index /></ProtectedRoute>} />
                <Route path="/fleet" element={<ProtectedRoute><Fleet /></ProtectedRoute>} />
                <Route path="/spare-vehicles" element={<ProtectedRoute><SpareVehicles /></ProtectedRoute>} />
                <Route path="/routes" element={<ProtectedRoute><RoutesPage /></ProtectedRoute>} />
                <Route path="/pickup-points" element={<ProtectedRoute><PickupPoints /></ProtectedRoute>} />
                <Route path="/alerts" element={<ProtectedRoute><Alerts /></ProtectedRoute>} />
                <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
                <Route path="/analytics" element={<ProtectedRoute><Analytics /></ProtectedRoute>} />
                <Route path="/users" element={<ProtectedRoute><Users /></ProtectedRoute>} />
                <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
                <Route path="/twitter" element={<ProtectedRoute><TwitterMentions /></ProtectedRoute>} />
                <Route path="/tickets" element={<ProtectedRoute><Tickets /></ProtectedRoute>} />
                <Route path="/master/drivers" element={<ProtectedRoute><MasterDrivers /></ProtectedRoute>} />
                <Route path="/master/vendors" element={<ProtectedRoute><MasterVendors /></ProtectedRoute>} />
                <Route path="/master/vehicles" element={<ProtectedRoute><MasterVehicles /></ProtectedRoute>} />
                <Route path="/master/devices" element={<ProtectedRoute><MasterDevices /></ProtectedRoute>} />
                <Route path="/master/device-assignments" element={<ProtectedRoute><MasterDeviceAssignments /></ProtectedRoute>} />
                <Route path="/master/zones-wards" element={<ProtectedRoute><MasterZonesWards /></ProtectedRoute>} />
                <Route path="/master/routes-pickups" element={<ProtectedRoute><MasterRoutesPickups /></ProtectedRoute>} />
                <Route path="/master/gts-dump-yards" element={<ProtectedRoute><MasterGtsDumpYards /></ProtectedRoute>} />
                <Route path="/master/dump-yard-weighment-entry" element={<ProtectedRoute><MasterDumpYardWeighmentEntry /></ProtectedRoute>} />
                <Route path="/active-trucks" element={<ProtectedRoute><ActiveTrucks /></ProtectedRoute>} />
                <Route path="/trips-completed" element={<ProtectedRoute><TripsCompleted /></ProtectedRoute>} />
                <Route path="/active-alerts" element={<ProtectedRoute><ActiveAlertsDetail /></ProtectedRoute>} />
                <Route path="/collection-rate" element={<ProtectedRoute><CollectionRate /></ProtectedRoute>} />
                <Route path="/gtc-checkpoint" element={<ProtectedRoute><GtcCheckpoint /></ProtectedRoute>} />
                <Route path="/collection-ton-today" element={<ProtectedRoute><CollectionTonToday /></ProtectedRoute>} />
                {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
                <Route path="*" element={<NotFound />} />
              </Routes>
            </Suspense>
          </AuthProvider>
        </BrowserRouter>
      </LoadScript>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
