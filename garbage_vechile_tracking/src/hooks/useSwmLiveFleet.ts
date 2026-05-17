import { useEffect, useMemo, useRef, useState } from "react";

import { SWM_ADMIN_API_URL, SWM_WS_URL } from "@/config/api";
import { TruckData } from "@/data/fleetData";

type SnapshotTruck = {
  imei: string;
  device_id?: string | null;
  vehicle_id?: string | null;
  lat: number;
  lng: number;
  speed_kph?: number | null;
  heading?: number | null;
  ignition?: boolean | null;
  event_ts?: string | null;
  status?: string | null;
  vendor_id?: string | null;
};

type SnapshotResponse = {
  items: SnapshotTruck[];
  total: number;
};

type LiveWsMessage = {
  imei?: string;
  vehicle_id?: string;
  lat?: number;
  lng?: number;
  speed?: number;
  status?: string;
  event_ts?: string;
};

const RECONNECT_DELAY_MS = 1500;

function toTruckStatus(rawStatus: string | null | undefined, speed: number): TruckData["status"] {
  const status = (rawStatus || "").toLowerCase();
  if (status === "moving") return "moving";
  if (status === "idle") return "idle";
  if (status === "offline") return "offline";
  if (status === "parked") return "idle";
  if (status === "dumping") return "dumping";
  if (status === "breakdown") return "breakdown";
  if (speed >= 5) return "moving";
  return "idle";
}

function toTruckType(vehicleId: string | null | undefined): TruckData["truckType"] {
  if (!vehicleId) return "primary";
  return vehicleId.toLowerCase().includes("s") ? "secondary" : "primary";
}

function buildTruckFromSnapshot(item: SnapshotTruck): TruckData | null {
  const imei = (item.imei || "").trim();
  if (!imei) return null;

  const lat = Number(item.lat);
  const lng = Number(item.lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;

  const speed = Number(item.speed_kph ?? 0);
  const truckNumber = (item.vehicle_id || imei).trim();
  const eventTs = item.event_ts || new Date().toISOString();

  return {
    id: imei,
    truckNumber,
    truckType: toTruckType(item.vehicle_id),
    vehicleType: "compactor",
    position: { lat, lng },
    status: toTruckStatus(item.status, speed),
    driver: "Unassigned",
    driverId: "-",
    route: "Live Feed",
    routeId: "",
    speed,
    assignedGTP: undefined,
    assignedDumpingSite: undefined,
    tripsCompleted: 0,
    tripsAllowed: 0,
    gpsDevice: {
      imei,
      status: toTruckStatus(item.status, speed) === "offline" ? "offline" : "online",
      lastPing: eventTs,
      signalStrength: 100,
      batteryLevel: 100,
    },
    vehicleCapacity: "-",
    lastUpdate: eventTs,
    vendorId: item.vendor_id || "",
    zoneId: "",
    wardId: "",
    isSpare: false,
    bearing: Number(item.heading ?? 0),
  };
}

function mergeWsUpdate(existing: TruckData, msg: LiveWsMessage): TruckData {
  const lat = Number(msg.lat ?? existing.position.lat);
  const lng = Number(msg.lng ?? existing.position.lng);
  const speed = Number(msg.speed ?? existing.speed ?? 0);
  const nextStatus = toTruckStatus(msg.status, speed);
  const eventTs = msg.event_ts || existing.lastUpdate || new Date().toISOString();

  return {
    ...existing,
    truckNumber: msg.vehicle_id || existing.truckNumber,
    position: {
      lat: Number.isFinite(lat) ? lat : existing.position.lat,
      lng: Number.isFinite(lng) ? lng : existing.position.lng,
    },
    speed,
    status: nextStatus,
    lastUpdate: eventTs,
    gpsDevice: {
      ...existing.gpsDevice,
      lastPing: eventTs,
      status: nextStatus === "offline" ? "offline" : "online",
    },
  };
}

export function useSwmLiveFleet(limit = 20000): { trucks: TruckData[]; isConnected: boolean } {
  const [trucksById, setTrucksById] = useState<Record<string, TruckData>>({});
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);

  useEffect(() => {
    let disposed = false;

    const loadSnapshot = async () => {
      try {
        const response = await fetch(`${SWM_ADMIN_API_URL}/v1/realtime/trucks?limit=${limit}`, {
          headers: {
            "Content-Type": "application/json",
            "x-role": "viewer",
          },
        });
        if (!response.ok) return;
        const payload = (await response.json()) as SnapshotResponse;
        if (disposed || !Array.isArray(payload.items)) return;

        const nextMap: Record<string, TruckData> = {};
        for (const item of payload.items) {
          const truck = buildTruckFromSnapshot(item);
          if (truck) {
            nextMap[truck.id] = truck;
          }
        }

        setTrucksById((prev) => ({ ...prev, ...nextMap }));
      } catch {
        // Snapshot is best-effort; websocket may still provide updates.
      }
    };

    const connectWs = () => {
      if (disposed) return;
      const ws = new WebSocket(SWM_WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as LiveWsMessage;
          const imei = (data.imei || "").trim();
          if (!imei) return;

          setTrucksById((prev) => {
            const existing = prev[imei] || {
              id: imei,
              truckNumber: data.vehicle_id || imei,
              truckType: toTruckType(data.vehicle_id),
              vehicleType: "compactor",
              position: {
                lat: Number(data.lat ?? 0),
                lng: Number(data.lng ?? 0),
              },
              status: toTruckStatus(data.status, Number(data.speed ?? 0)),
              driver: "Unassigned",
              driverId: "-",
              route: "Live Feed",
              routeId: "",
              speed: Number(data.speed ?? 0),
              assignedGTP: undefined,
              assignedDumpingSite: undefined,
              tripsCompleted: 0,
              tripsAllowed: 0,
              gpsDevice: {
                imei,
                status: "online",
                lastPing: data.event_ts || new Date().toISOString(),
                signalStrength: 100,
                batteryLevel: 100,
              },
              vehicleCapacity: "-",
              lastUpdate: data.event_ts || new Date().toISOString(),
              vendorId: "",
              zoneId: "",
              wardId: "",
              isSpare: false,
              bearing: 0,
            } as TruckData;

            return {
              ...prev,
              [imei]: mergeWsUpdate(existing, data),
            };
          });
        } catch {
          // Ignore malformed payloads from websocket.
        }
      };

      ws.onerror = () => {
        setIsConnected(false);
      };

      ws.onclose = () => {
        setIsConnected(false);
        if (!disposed) {
          reconnectTimerRef.current = window.setTimeout(() => {
            loadSnapshot();
            connectWs();
          }, RECONNECT_DELAY_MS);
        }
      };
    };

    loadSnapshot();
    connectWs();

    return () => {
      disposed = true;
      setIsConnected(false);
      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [limit]);

  const trucks = useMemo(() => {
    return Object.values(trucksById).sort((a, b) => a.truckNumber.localeCompare(b.truckNumber));
  }, [trucksById]);

  return { trucks, isConnected };
}
