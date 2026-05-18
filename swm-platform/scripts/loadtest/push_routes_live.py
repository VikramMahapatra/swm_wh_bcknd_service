"""Push 3 trucks along predefined road routes in Kharadi, Pune.

Each truck follows a different route and loops back when it reaches the end.
Sends one GPS event per second to the ingestion API.

Usage:
    uv run python scripts/loadtest/push_routes_live.py \
        --base-url http://127.0.0.1:8001 \
        --duration-minutes 30
"""

from __future__ import annotations

import argparse
import asyncio
import math
import time
from datetime import UTC, datetime

import httpx

# ---------------------------------------------------------------------------
# Route definitions — GPS waypoints along real roads in Kharadi, Pune
# Each route is ~1.5–2 km long and loops back when the truck reaches the end
# ---------------------------------------------------------------------------

ROUTES: list[dict] = [
    {
        "name": "Route-A (Kharadi Main Road N-S)",
        "vendor_id": "vendor_a",
        "imei": "990000000000001",
        "waypoints": [
            (18.5435, 73.9483),
            (18.5452, 73.9481),
            (18.5468, 73.9480),
            (18.5484, 73.9479),
            (18.5500, 73.9480),
            (18.5516, 73.9483),
            (18.5530, 73.9486),
            (18.5545, 73.9489),
            (18.5560, 73.9490),
            (18.5575, 73.9488),
            (18.5590, 73.9485),
            (18.5605, 73.9482),
        ],
    },
    {
        "name": "Route-B (Nagar Road E-W)",
        "vendor_id": "vendor_b",
        "imei": "990000000000002",
        "waypoints": [
            (18.5519, 73.9390),
            (18.5519, 73.9410),
            (18.5518, 73.9430),
            (18.5517, 73.9450),
            (18.5516, 73.9470),
            (18.5516, 73.9490),
            (18.5515, 73.9510),
            (18.5514, 73.9530),
            (18.5513, 73.9550),
            (18.5512, 73.9570),
            (18.5511, 73.9590),
        ],
    },
    {
        "name": "Route-C (EON IT Park Loop)",
        "vendor_id": "vendor_a",
        "imei": "990000000000003",
        "waypoints": [
            (18.5516, 73.9483),
            (18.5525, 73.9497),
            (18.5538, 73.9510),
            (18.5552, 73.9518),
            (18.5563, 73.9508),
            (18.5568, 73.9493),
            (18.5560, 73.9477),
            (18.5547, 73.9466),
            (18.5532, 73.9462),
            (18.5518, 73.9468),
            (18.5510, 73.9478),
            (18.5516, 73.9483),
        ],
    },
]

SPEED_KPH = 28.0  # realistic city driving speed


def _bearing(p1: tuple[float, float], p2: tuple[float, float]) -> int:
    """Calculate compass bearing from p1 to p2."""
    lat1, lng1 = math.radians(p1[0]), math.radians(p1[1])
    lat2, lng2 = math.radians(p2[0]), math.radians(p2[1])
    dlng = lng2 - lng1
    x = math.sin(dlng) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlng)
    return int((math.degrees(math.atan2(x, y)) + 360) % 360)


def _distance_m(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    """Haversine distance in metres between two lat/lng points."""
    R = 6_371_000
    lat1, lat2 = math.radians(p1[0]), math.radians(p2[0])
    dlat = lat2 - lat1
    dlng = math.radians(p2[1] - p1[1])
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _interpolate(
    p1: tuple[float, float],
    p2: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    """Linear interpolation between two points, t in [0, 1]."""
    return (
        p1[0] + (p2[0] - p1[0]) * t,
        p1[1] + (p2[1] - p1[1]) * t,
    )


class TruckRunner:
    """Walks a truck along its waypoints, looping back and forth."""

    def __init__(self, route: dict) -> None:
        self.route = route
        self.waypoints = route["waypoints"]
        self.seg_idx = 0        # current segment index
        self.seg_t = 0.0        # progress within segment [0, 1]
        self.direction = 1      # 1 = forward, -1 = reverse
        self._meters_per_second = SPEED_KPH * 1000 / 3600

    def step(self) -> tuple[float, float, int]:
        """Advance the truck by one second and return (lat, lng, heading)."""
        wp = self.waypoints
        seg_start = wp[self.seg_idx]
        seg_end = wp[self.seg_idx + 1] if self.direction == 1 else wp[self.seg_idx - 1]

        seg_len = _distance_m(seg_start, seg_end)
        advance = self._meters_per_second / max(seg_len, 0.1)

        self.seg_t += advance

        while self.seg_t >= 1.0:
            self.seg_t -= 1.0
            self.seg_idx += self.direction

            # Reached the end — reverse direction
            if self.seg_idx >= len(wp) - 1:
                self.seg_idx = len(wp) - 2
                self.direction = -1
            elif self.seg_idx < 0:
                self.seg_idx = 0
                self.direction = 1

            seg_start = wp[self.seg_idx]
            seg_end = wp[self.seg_idx + 1] if self.direction == 1 else wp[self.seg_idx - 1]
            seg_len = _distance_m(seg_start, seg_end)
            advance = self._meters_per_second / max(seg_len, 0.1)

        lat, lng = _interpolate(seg_start, seg_end, self.seg_t)
        heading = _bearing(seg_start, seg_end)
        return round(lat, 6), round(lng, 6), heading


async def send_event(
    client: httpx.AsyncClient,
    url: str,
    vendor_id: str,
    imei: str,
    lat: float,
    lng: float,
    heading: int,
    speed: float,
) -> None:
    payload = [
        {
            "imei": imei,
            "latitude": lat,
            "longitude": lng,
            "speed": speed,
            "heading": heading,
            "ignition": True,
            "timestamp": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        }
    ]
    try:
        await client.post(
            f"{url}/webhook/gps",
            json=payload,
            headers={"X-Vendor-Id": vendor_id, "X-Request-Id": f"route-{time.time_ns()}"},
            timeout=3.0,
        )
    except Exception:
        pass  # non-fatal; next tick will retry


async def run(base_url: str, duration_minutes: int) -> None:
    runners = [TruckRunner(r) for r in ROUTES]
    total_seconds = duration_minutes * 60
    start = time.time()

    print(f"Starting {len(ROUTES)} trucks on Kharadi routes for {duration_minutes} minutes")
    for r in ROUTES:
        print(f"  • {r['imei']} — {r['name']}")
    print()

    async with httpx.AsyncClient() as client:
        second = 0
        while time.time() - start < total_seconds:
            tick_start = time.time()
            second += 1

            tasks = []
            for runner in runners:
                lat, lng, heading = runner.step()
                tasks.append(
                    send_event(
                        client,
                        base_url,
                        runner.route["vendor_id"],
                        runner.route["imei"],
                        lat,
                        lng,
                        heading,
                        SPEED_KPH,
                    )
                )

            await asyncio.gather(*tasks)

            if second % 10 == 0:
                elapsed = int(time.time() - start)
                print(f"second={second} elapsed={elapsed}s trucks={len(ROUTES)} running…")

            # Sleep the remainder of the 1-second tick
            elapsed_tick = time.time() - tick_start
            await asyncio.sleep(max(0, 1.0 - elapsed_tick))

    print("\nDone.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Push 3 trucks along Kharadi road routes")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--duration-minutes", type=int, default=30)
    args = parser.parse_args()
    asyncio.run(run(args.base_url, args.duration_minutes))


if __name__ == "__main__":
    main()
