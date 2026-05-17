import { TruckStatus, TruckType } from "@/data/fleetData";

interface TruckIconProps {
  status: TruckStatus;
  type: TruckType;
  size?: number;
  className?: string;
}

const statusColors: Record<TruckStatus, string> = {
  moving: "#22c55e",
  idle: "#f59e0b",
  dumping: "#3b82f6",
  offline: "#6b7280",
  breakdown: "#ef4444",
};

export const TruckIcon = ({ status, type, size = 32, className = "" }: TruckIconProps) => {
  const color = statusColors[status];
  const isPrimary = type === "primary";
  
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Truck body */}
      <rect x="2" y="12" width="20" height="12" rx="2" fill={color} />
      {/* Cabin */}
      <rect x="18" y="8" width="10" height="16" rx="2" fill={color} />
      {/* Window */}
      <rect x="20" y="10" width="6" height="5" rx="1" fill="white" fillOpacity="0.8" />
      {/* Wheels */}
      <circle cx="8" cy="26" r="3" fill="#374151" stroke="white" strokeWidth="1" />
      <circle cx="24" cy="26" r="3" fill="#374151" stroke="white" strokeWidth="1" />
      {/* Type indicator */}
      {isPrimary ? (
        <text x="11" y="20" fontSize="8" fill="white" fontWeight="bold" textAnchor="middle">P</text>
      ) : (
        <text x="11" y="20" fontSize="8" fill="white" fontWeight="bold" textAnchor="middle">S</text>
      )}
      {/* Status indicator dot */}
      <circle cx="28" cy="6" r="4" fill={color} stroke="white" strokeWidth="2">
        {status === "moving" && (
          <animate attributeName="opacity" values="1;0.5;1" dur="1s" repeatCount="indefinite" />
        )}
      </circle>
    </svg>
  );
};

// SVG data URL for Google Maps marker - Modern truck icon with better distinction
export const createTruckMarkerIcon = (status: TruckStatus, type: TruckType, bearing: number = 0, speed: number = 0): string => {
  const color = statusColors[status];
  const typeLabel = type === "primary" ? "P" : "S";
  const isPrimary = type === "primary";
  
  // Primary: Blue background, Secondary: Purple background
  const typeBgColor = isPrimary ? "#0066cc" : "#9333ea";
  const typeTextColor = "#ffffff";
  
  // Convert geographic bearing (0=North) to SVG rotation
  const svgRotation = (90 - bearing + 180 + 360) % 360;
  
  const svg = `
    <svg width="56" height="48" viewBox="-4 -4 56 48" xmlns="http://www.w3.org/2000/svg">
      <g transform="translate(24, 16) rotate(${svgRotation}) translate(-24, -16)">
        <!-- Shadow for depth -->
        <ellipse cx="24" cy="29" rx="20" ry="2.5" fill="rgba(0,0,0,0.2)"/>
        
        <!-- Main truck body/compactor with gradient effect -->
        <defs>
          <linearGradient id="bodyGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" style="stop-color:${color};stop-opacity:1" />
            <stop offset="100%" style="stop-color:${color};stop-opacity:0.8" />
          </linearGradient>
        </defs>
        
        <!-- Compactor body -->
        <rect x="0" y="8" width="24" height="16" rx="2.5" fill="url(#bodyGrad)" stroke="white" stroke-width="2"/>
        
        <!-- Compactor tank detail -->
        <rect x="2" y="10" width="20" height="12" rx="1.5" fill="white" opacity="0.25"/>
        
        <!-- Hydraulic compression effect -->
        <rect x="4" y="11" width="2.5" height="10" rx="1" fill="white" opacity="0.4"/>
        <rect x="9" y="11" width="2.5" height="10" rx="1" fill="white" opacity="0.4"/>
        <rect x="14" y="11" width="2.5" height="10" rx="1" fill="white" opacity="0.4"/>
        <rect x="19" y="11" width="2.5" height="10" rx="1" fill="white" opacity="0.4"/>
        
        <!-- Cabin -->
        <rect x="22" y="5" width="16" height="19" rx="3" fill="url(#bodyGrad)" stroke="white" stroke-width="2"/>
        
        <!-- Windshield (larger and more prominent) -->
        <rect x="24" y="7" width="12" height="7.5" rx="2" fill="rgba(255,255,255,0.9)" stroke="white" stroke-width="1"/>
        
        <!-- Windshield shine -->
        <rect x="25" y="7.5" width="10" height="2" rx="1" fill="white" opacity="0.5"/>
        
        <!-- Door window -->
        <rect x="26" y="16" width="10" height="6" rx="1.5" fill="rgba(255,255,255,0.7)"/>
        
        <!-- Side mirror (more visible) -->
        <rect x="21" y="10" width="2" height="3.5" rx="0.5" fill="white" opacity="0.8" stroke="white" stroke-width="0.5"/>
        <circle cx="22" cy="9.5" r="1.2" fill="white" opacity="0.7"/>
        
        <!-- Headlights -->
        <circle cx="37" cy="13" r="1.8" fill="#fbbf24" opacity="1" stroke="white" stroke-width="0.5"/>
        <circle cx="37" cy="19" r="1.8" fill="#fbbf24" opacity="0.8" stroke="white" stroke-width="0.5"/>
        
        <!-- Grille detail -->
        <rect x="38" y="10" width="1.5" height="12" rx="0.5" fill="white" opacity="0.15"/>
        
        <!-- Wheels (more detailed) -->
        <g>
          <!-- Front wheel -->
          <circle cx="8" cy="25" r="4" fill="#0f172a" stroke="#e2e8f0" stroke-width="1.5"/>
          <circle cx="8" cy="25" r="2.5" fill="#334155"/>
          <circle cx="8" cy="25" r="1.2" fill="#1e293b"/>
          
          <!-- Rear wheel -->
          <circle cx="32" cy="25" r="4" fill="#0f172a" stroke="#e2e8f0" stroke-width="1.5"/>
          <circle cx="32" cy="25" r="2.5" fill="#334155"/>
          <circle cx="32" cy="25" r="1.2" fill="#1e293b"/>
        </g>
        
        <!-- Type badge - Larger and more prominent -->
        <g>
          ${isPrimary ? 
            `<!-- Primary truck badge -->
            <defs>
              <radialGradient id="primaryGrad" cx="40%" cy="40%">
                <stop offset="0%" style="stop-color:#0088ff;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#0066cc;stop-opacity:1" />
              </radialGradient>
            </defs>
            <circle cx="42" cy="6" r="7.5" fill="url(#primaryGrad)" stroke="white" stroke-width="2"/>
            <rect x="40.5" y="4.5" width="3" height="3" rx="0.5" fill="white" opacity="0.3"/>` 
            : 
            `<!-- Secondary truck badge -->
            <defs>
              <radialGradient id="secondaryGrad" cx="40%" cy="40%">
                <stop offset="0%" style="stop-color:#b366ff;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#9333ea;stop-opacity:1" />
              </radialGradient>
            </defs>
            <circle cx="42" cy="6" r="7.5" fill="url(#secondaryGrad)" stroke="white" stroke-width="2"/>
            <polygon points="42,3.5 44,8 40,8" fill="white" opacity="0.4"/>`
          }
          <text x="42" y="9.5" font-size="8.5" fill="white" font-weight="900" text-anchor="middle" font-family="sans-serif" letter-spacing="1">${typeLabel}</text>
        </g>
        
        <!-- Status pulse for moving trucks -->
        ${status === "moving" ? `<circle cx="42" cy="6" r="7.5" fill="none" stroke="${color}" stroke-width="1.8" opacity="0.7"><animate attributeName="r" values="7.5;14;7.5" dur="1.8s" repeatCount="indefinite"/><animate attributeName="opacity" values="0.7;0;0.7" dur="1.8s" repeatCount="indefinite"/></circle>` : ''}
        
        <!-- Speed badge - shown only when moving -->
        ${status === "moving" ? `
          <rect x="6" y="31" width="36" height="8" rx="2" fill="#1f2937" stroke="#22c55e" stroke-width="1.5" opacity="0.95"/>
          <text x="24" y="37" font-size="6.5" font-weight="bold" text-anchor="middle" fill="#22c55e" font-family="monospace">${Math.round(speed)} km/h</text>
        ` : ''}
      </g>
    </svg>
  `;
  
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
};

export default TruckIcon;
