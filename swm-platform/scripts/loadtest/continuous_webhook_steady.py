from __future__ import annotations

import argparse
import asyncio
import os
import random
import time
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
    phase: str
    phase_seconds_left: int


def _rand_duration(rng: random.Random, minimum: int, maximum: int) -> int:
    if maximum <= minimum:
        return minimum
    return rng.randint(minimum, maximum)


def build_trucks(total: int, *, rng: random.Random, base_lat: float, base_lng: float) -> list[Truck]:
    trucks: list[Truck] = []
    for i in range(total):
        imei = f"990000000000{i:03d}"[-15:]
        vendor_id = VENDORS[i % len(VENDORS)]
        trucks.append(
            Truck(
                imei=imei,
                vendor_id=vendor_id,
                lat=base_lat + (i % 10) * 0.00015,
                lng=base_lng + (i % 10) * 0.00015,
                heading=rng.randint(0, 359),
                odometer_km=10_000 + i * 0.5,
                phase="moving",
                phase_seconds_left=_rand_duration(rng, 45, 120),
            )
        )
    return trucks


def _switch_phase(truck: Truck, rng: random.Random) -> None:
    if truck.phase == "moving":
        truck.phase = "idle"
        truck.phase_seconds_left = _rand_duration(rng, 120, 180)
        return
    truck.phase = "moving"
    truck.phase_seconds_left = _rand_duration(rng, 30, 70)


def build_event(
    truck: Truck,
    rng: random.Random,
    *,
    overspeed_chance: float,
    overspeed_min_kph: float,
    overspeed_max_kph: float,
) -> dict[str, Any]:
    if truck.phase_seconds_left <= 0:
        _switch_phase(truck, rng)

    if truck.phase == "idle":
        speed = round(rng.uniform(0.0, 0.8), 2)
        ignition = True
        truck.lat = round(truck.lat + rng.uniform(-0.000002, 0.000002), 6)
        truck.lng = round(truck.lng + rng.uniform(-0.000002, 0.000002), 6)
    else:
        is_overspeed = rng.random() < overspeed_chance
        if is_overspeed:
            speed = round(rng.uniform(overspeed_min_kph, overspeed_max_kph), 2)
        else:
            speed = round(rng.uniform(14.0, 52.0), 2)
        ignition = True
        truck.heading = (truck.heading + rng.randint(-20, 20)) % 360
        step = speed / 3600.0
        lat_step = (step / 111.0) * rng.uniform(0.5, 1.2)
        lng_step = (step / 111.0) * rng.uniform(0.5, 1.2)
        truck.lat = round(truck.lat + lat_step * (1 if rng.random() > 0.5 else -1), 6)
        truck.lng = round(truck.lng + lng_step * (1 if rng.random() > 0.5 else -1), 6)
        truck.odometer_km = round(truck.odometer_km + step, 3)

    truck.phase_seconds_left -= 1

    return {
        "imei": truck.imei,
        "latitude": truck.lat,
        "longitude": truck.lng,
        "speed": speed,
        "heading": truck.heading,
        "ignition": ignition,
        "odometer": truck.odometer_km,
        "fuel_level": round(rng.uniform(5, 90), 2),
        "timestamp": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
    }


async def send_batch(
    client: httpx.AsyncClient,
    url: str,
    vendor_id: str,
    payload: list[dict[str, Any]],
    webhook_secret: str,
    webhook_secret_header: str,
    counters: dict[str, int],
    semaphore: asyncio.Semaphore,
) -> None:
    await semaphore.acquire()
    try:
        headers = {
            "X-Vendor-Id": vendor_id,
            "X-Request-Id": f"steady-{time.time_ns()}",
        }
        if webhook_secret:
            headers[webhook_secret_header] = webhook_secret
        try:
            resp = await client.post(url, json=payload, headers=headers)
            counters["requests"] += 1
            if 200 <= resp.status_code < 300:
                counters["http_2xx"] += 1
            elif 400 <= resp.status_code < 500:
                counters["http_4xx"] += 1
            else:
                counters["http_5xx"] += 1

            data: dict[str, Any] = {}
            if resp.headers.get("content-type", "").startswith("application/json"):
                try:
                    data = resp.json()
                except Exception:
                    data = {}
            counters["accepted"] += int(data.get("accepted", 0))
            counters["published"] += int(data.get("published", 0))
            counters["rejected"] += int(data.get("rejected", 0))

            error_summary = data.get("error_summary", {})
            if isinstance(error_summary, dict):
                validation = error_summary.get("validation", {})
                normalization = error_summary.get("normalization", {})
                publish = error_summary.get("publish", {})

                if isinstance(validation, dict):
                    counters["rejected_validation"] += int(validation.get("failed", 0) or 0)
                if isinstance(normalization, dict):
                    counters["rejected_normalization"] += int(normalization.get("failed", 0) or 0)
                if isinstance(publish, dict):
                    counters["rejected_publish"] += int(publish.get("failed", 0) or 0)
        except Exception:
            counters["transport_failures"] += 1
            counters["requests"] += 1
    finally:
        semaphore.release()


def chunked(items: list[Truck], size: int) -> list[list[Truck]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


async def run_steady(args: argparse.Namespace) -> None:
    url = f"{args.base_url.rstrip('/')}{args.endpoint}"
    rng = random.Random(args.seed)
    trucks = build_trucks(
        args.trucks,
        rng=rng,
        base_lat=args.base_lat,
        base_lng=args.base_lng,
    )
    by_vendor: dict[str, list[Truck]] = {vendor: [] for vendor in VENDORS}
    for t in trucks:
        by_vendor[t.vendor_id].append(t)

    counters = {
        "requests": 0,
        "http_2xx": 0,
        "http_4xx": 0,
        "http_5xx": 0,
        "transport_failures": 0,
        "accepted": 0,
        "published": 0,
        "rejected": 0,
        "rejected_validation": 0,
        "rejected_normalization": 0,
        "rejected_publish": 0,
    }

    seconds_total = args.duration_minutes * 60
    timeout = httpx.Timeout(args.timeout_seconds)
    limits = httpx.Limits(max_connections=args.concurrency, max_keepalive_connections=args.concurrency)
    request_semaphore = asyncio.Semaphore(args.max_parallel_requests)

    print(
        (
            f"[steady] start minutes={args.duration_minutes} trucks={args.trucks} "
            f"events_per_second={args.trucks} endpoint={url} "
            f"secret_enabled={'yes' if args.webhook_secret else 'no'}"
        ),
        flush=True,
    )

    start = time.perf_counter()
    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        for second in range(seconds_total):
            target = start + second
            now = time.perf_counter()
            if target > now:
                await asyncio.sleep(target - now)

            tasks: list[asyncio.Task[None]] = []
            for vendor_id, vendor_trucks in by_vendor.items():
                for truck_chunk in chunked(vendor_trucks, args.batch_size):
                    payload: list[dict[str, Any]] = []
                    for truck in truck_chunk:
                        payload.append(
                            build_event(
                                truck,
                                rng,
                                overspeed_chance=args.overspeed_chance,
                                overspeed_min_kph=args.overspeed_min_kph,
                                overspeed_max_kph=args.overspeed_max_kph,
                            )
                        )
                    tasks.append(
                        asyncio.create_task(
                            send_batch(
                                client,
                                url,
                                vendor_id,
                                payload,
                                args.webhook_secret,
                                args.webhook_secret_header,
                                counters,
                                request_semaphore,
                            )
                        )
                    )

            await asyncio.gather(*tasks)

            if second % 10 == 0:
                elapsed = second + 1
                print(
                    (
                        f"[steady] second={elapsed}/{seconds_total} "
                        f"requests={counters['requests']} published={counters['published']} "
                        f"rejected={counters['rejected']} "
                        f"rejected_validation={counters['rejected_validation']} "
                        f"rejected_normalization={counters['rejected_normalization']} "
                        f"rejected_publish={counters['rejected_publish']}"
                    ),
                    flush=True,
                )

    elapsed_s = max(1.0, time.perf_counter() - start)
    print(
        (
            "[steady] done "
            f"requests={counters['requests']} "
            f"2xx={counters['http_2xx']} 4xx={counters['http_4xx']} 5xx={counters['http_5xx']} "
            f"transport_failures={counters['transport_failures']} "
            f"accepted={counters['accepted']} published={counters['published']} rejected={counters['rejected']} "
            f"rejected_validation={counters['rejected_validation']} "
            f"rejected_normalization={counters['rejected_normalization']} "
            f"rejected_publish={counters['rejected_publish']} "
            f"published_eps={counters['published'] / elapsed_s:.2f}"
        ),
        flush=True,
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Steady webhook sender: trucks events each second")
    p.add_argument("--base-url", default="http://127.0.0.1:9001")
    p.add_argument("--endpoint", default="/webhook/gps")
    p.add_argument("--trucks", type=int, default=600)
    p.add_argument("--duration-minutes", type=int, default=20)
    p.add_argument("--concurrency", type=int, default=256)
    p.add_argument("--batch-size", type=int, default=20)
    p.add_argument("--max-parallel-requests", type=int, default=6)
    p.add_argument("--timeout-seconds", type=float, default=10.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--base-lat", type=float, default=28.6139)
    p.add_argument("--base-lng", type=float, default=77.2090)
    p.add_argument("--overspeed-chance", type=float, default=0.18)
    p.add_argument("--overspeed-min-kph", type=float, default=82.0)
    p.add_argument("--overspeed-max-kph", type=float, default=96.0)
    p.add_argument(
        "--webhook-secret",
        default=os.getenv("INGESTION_WEBHOOK_SECRET", ""),
        help="Webhook shared secret value (default: INGESTION_WEBHOOK_SECRET env)",
    )
    p.add_argument(
        "--webhook-secret-header",
        default=os.getenv("INGESTION_WEBHOOK_SECRET_HEADER", "X-Webhook-Secret"),
        help="Webhook secret header name (default: INGESTION_WEBHOOK_SECRET_HEADER env or X-Webhook-Secret)",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(run_steady(args))


if __name__ == "__main__":
    main()
