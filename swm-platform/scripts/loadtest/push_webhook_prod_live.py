#!/usr/bin/env python3
"""Push synthetic GPS events to production webhook in a steady loop."""

from __future__ import annotations

import argparse
import asyncio
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

VENDORS = ("vendor_a", "vendor_b", "vendor_c")


@dataclass(slots=True)
class Truck:
    imei: str
    vendor_id: str
    lat: float
    lng: float
    heading: int
    odometer_km: float


def build_trucks(total: int, rng: random.Random, base_lat: float, base_lng: float) -> list[Truck]:
    trucks: list[Truck] = []
    for idx in range(total):
        trucks.append(
            Truck(
                imei=f"990000000000{idx:03d}"[-15:],
                vendor_id=VENDORS[idx % len(VENDORS)],
                lat=base_lat + (idx % 10) * 0.00015,
                lng=base_lng + (idx % 10) * 0.00015,
                heading=rng.randint(0, 359),
                odometer_km=10000 + idx * 0.25,
            )
        )
    return trucks


def next_event(truck: Truck, rng: random.Random) -> dict[str, Any]:
    speed = round(rng.uniform(5.0, 48.0), 2)
    truck.heading = (truck.heading + rng.randint(-18, 18)) % 360
    step = speed / 3600.0
    lat_step = (step / 111.0) * rng.uniform(0.7, 1.2)
    lng_step = (step / 111.0) * rng.uniform(0.7, 1.2)

    truck.lat = round(truck.lat + lat_step * (1 if rng.random() > 0.5 else -1), 6)
    truck.lng = round(truck.lng + lng_step * (1 if rng.random() > 0.5 else -1), 6)
    truck.odometer_km = round(truck.odometer_km + step, 3)

    return {
        "imei": truck.imei,
        "latitude": truck.lat,
        "longitude": truck.lng,
        "speed": speed,
        "heading": truck.heading,
        "ignition": True,
        "odometer": truck.odometer_km,
        "fuel_level": round(rng.uniform(8, 88), 2),
        "timestamp": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
    }


async def run(args: argparse.Namespace) -> None:
    rng = random.Random(args.seed)
    trucks = build_trucks(args.trucks, rng, args.base_lat, args.base_lng)
    by_vendor: dict[str, list[Truck]] = {vendor: [] for vendor in VENDORS}
    for truck in trucks:
        by_vendor[truck.vendor_id].append(truck)

    url = f"{args.base_url.rstrip('/')}{args.endpoint}"
    timeout = httpx.Timeout(args.timeout_seconds)
    limits = httpx.Limits(max_connections=40, max_keepalive_connections=20)

    print(f"[push-prod] target={url}")
    print(f"[push-prod] trucks={args.trucks} batch_size={args.batch_size} interval={args.interval_seconds}s")

    request_count = 0
    published_total = 0
    rejected_total = 0

    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        while True:
            for vendor_id, vendor_trucks in by_vendor.items():
                for i in range(0, len(vendor_trucks), args.batch_size):
                    batch_trucks = vendor_trucks[i : i + args.batch_size]
                    payload = [next_event(truck, rng) for truck in batch_trucks]
                    headers = {
                        "X-Vendor-Id": vendor_id,
                        "X-Request-Id": f"prod-live-{request_count + 1}",
                    }

                    try:
                        response = await client.post(url, json=payload, headers=headers)
                        request_count += 1
                        if response.headers.get("content-type", "").startswith("application/json"):
                            body = response.json()
                        else:
                            body = {}

                        published = int(body.get("published", 0)) if isinstance(body, dict) else 0
                        rejected = int(body.get("rejected", 0)) if isinstance(body, dict) else 0
                        published_total += published
                        rejected_total += rejected

                        print(
                            "[push-prod] "
                            f"status={response.status_code} vendor={vendor_id} size={len(payload)} "
                            f"published={published} rejected={rejected} "
                            f"tot_published={published_total} tot_rejected={rejected_total}"
                        )
                    except Exception as exc:
                        request_count += 1
                        print(f"[push-prod] FAIL vendor={vendor_id} size={len(payload)} error={exc}")

            await asyncio.sleep(args.interval_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Push synthetic GPS events to production webhook")
    parser.add_argument("--base-url", default="https://ingestion-swm.zentrixel.com")
    parser.add_argument("--endpoint", default="/webhook/gps")
    parser.add_argument("--trucks", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=6)
    parser.add_argument("--interval-seconds", type=float, default=1.0)
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--base-lat", type=float, default=28.6139)
    parser.add_argument("--base-lng", type=float, default=77.2090)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("[push-prod] stopped")


if __name__ == "__main__":
    main()
