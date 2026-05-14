from __future__ import annotations

import argparse
import asyncio
import json
import sys
import math
import random
import statistics
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

DEFAULT_VENDOR_IDS = ("vendor_a", "vendor_b", "vendor_c")
WINDOWS_SELECTOR_CONNECTION_CAP = 256
REQUESTS_PER_SECOND_MULTIPLIER = 2
WINDOWS_REQUESTS_PER_SECOND_CAP = 128


@dataclass(slots=True)
class Truck:
    imei: str
    vendor_id: str


@dataclass(slots=True)
class VendorStats:
    requests: int = 0
    http_2xx: int = 0
    http_4xx: int = 0
    http_5xx: int = 0
    latency_ms: list[float] = field(default_factory=list)
    app_accepted: int = 0
    app_published: int = 0
    app_rejected: int = 0
    app_validation_failed: int = 0
    app_publish_failed: int = 0


@dataclass(slots=True)
class ScenarioStats:
    name: str
    duration_seconds: int
    expected_events: int
    total_requests: int = 0
    http_2xx: int = 0
    http_4xx: int = 0
    http_5xx: int = 0
    transport_failures: int = 0
    latency_ms: list[float] = field(default_factory=list)
    app_accepted: int = 0
    app_published: int = 0
    app_rejected: int = 0
    app_validation_failed: int = 0
    app_publish_failed: int = 0
    vendors: dict[str, VendorStats] = field(default_factory=dict)

    def vendor(self, vendor_id: str) -> VendorStats:
        if vendor_id not in self.vendors:
            self.vendors[vendor_id] = VendorStats()
        return self.vendors[vendor_id]


@dataclass(slots=True)
class LoadTestConfig:
    base_url: str
    endpoint: str
    trucks: int
    target_eps: int
    duration_seconds: int
    concurrency: int
    timeout_seconds: float
    report_dir: Path
    seed: int


@dataclass(slots=True)
class RequestSpec:
    vendor_id: str
    payload: Any


def _make_trucks(total: int) -> list[Truck]:
    trucks: list[Truck] = []
    for i in range(total):
        imei = f"990000000000{i:03d}"[-15:]
        vendor_id = DEFAULT_VENDOR_IDS[i % len(DEFAULT_VENDOR_IDS)]
        trucks.append(Truck(imei=imei, vendor_id=vendor_id))
    return trucks


def _group_trucks_by_vendor(trucks: list[Truck]) -> dict[str, list[Truck]]:
    grouped: dict[str, list[Truck]] = {}
    for truck in trucks:
        grouped.setdefault(truck.vendor_id, []).append(truck)
    return grouped


def _build_valid_event(truck: Truck, idx: int, rng: random.Random) -> dict[str, Any]:
    base_lat = 28.6139 + (idx % 30) * 0.0001
    base_lng = 77.2090 + (idx % 30) * 0.0001
    return {
        "imei": truck.imei,
        "latitude": round(base_lat + rng.uniform(-0.0005, 0.0005), 6),
        "longitude": round(base_lng + rng.uniform(-0.0005, 0.0005), 6),
        "speed": round(rng.uniform(0, 62), 2),
        "heading": int(rng.uniform(0, 359)),
        "ignition": bool(rng.randint(0, 1)),
        "odometer": round(10_000 + idx * 0.07, 3),
        "fuel_level": round(rng.uniform(5, 90), 2),
        "timestamp": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
    }


def _build_invalid_payload(valid: dict[str, Any], rng: random.Random) -> Any:
    mode = rng.choice(("bad_imei", "missing_ts", "not_array", "bad_lat"))
    if mode == "not_array":
        return {"invalid": True, "event": valid}
    invalid = dict(valid)
    if mode == "bad_imei":
        invalid["imei"] = "BAD_IMEI"
    elif mode == "missing_ts":
        invalid.pop("timestamp", None)
    elif mode == "bad_lat":
        invalid["latitude"] = 999.0
    return [invalid]


def _rate_burst(second: int, target_eps: int) -> int:
    # 20-second cycle: 12s baseline + 8s burst.
    phase = second % 20
    if phase < 12:
        return max(1, int(target_eps * 0.55))
    return max(1, int(target_eps * 1.8))


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    idx = (len(sorted_values) - 1) * pct
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return sorted_values[int(idx)]
    lower = sorted_values[lo]
    upper = sorted_values[hi]
    return lower + (upper - lower) * (idx - lo)


def _latency_summary(values: list[float]) -> dict[str, float]:
    if not values:
        return {
            "avg_ms": 0.0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
            "max_ms": 0.0,
        }
    return {
        "avg_ms": round(statistics.fmean(values), 3),
        "p50_ms": round(_percentile(values, 0.50), 3),
        "p95_ms": round(_percentile(values, 0.95), 3),
        "p99_ms": round(_percentile(values, 0.99), 3),
        "max_ms": round(max(values), 3),
    }


def _scenario_report(stats: ScenarioStats) -> dict[str, Any]:
    achieved_rps = stats.total_requests / stats.duration_seconds if stats.duration_seconds > 0 else 0.0
    published_eps = stats.app_published / stats.duration_seconds if stats.duration_seconds > 0 else 0.0
    return {
        "scenario": stats.name,
        "duration_seconds": stats.duration_seconds,
        "expected_events": stats.expected_events,
        "generated_requests": stats.total_requests,
        "http": {
            "2xx": stats.http_2xx,
            "4xx": stats.http_4xx,
            "5xx": stats.http_5xx,
            "transport_failures": stats.transport_failures,
        },
        "application": {
            "accepted": stats.app_accepted,
            "published": stats.app_published,
            "rejected": stats.app_rejected,
            "validation_failures": stats.app_validation_failed,
            "publish_failures": stats.app_publish_failed,
        },
        "throughput": {
            "requests_per_sec": round(achieved_rps, 2),
            "payload_per_sec": round(published_eps, 2),
        },
        "latency": _latency_summary(stats.latency_ms),
        "vendor_breakdown": {
            vendor: {
                "requests": v.requests,
                "http_2xx": v.http_2xx,
                "http_4xx": v.http_4xx,
                "http_5xx": v.http_5xx,
                "accepted": v.app_accepted,
                "published": v.app_published,
                "rejected": v.app_rejected,
                "validation_failures": v.app_validation_failed,
                "publish_failures": v.app_publish_failed,
                "latency": _latency_summary(v.latency_ms),
            }
            for vendor, v in sorted(stats.vendors.items())
        },
    }


async def _send_one(
    *,
    client: httpx.AsyncClient,
    url: str,
    spec: RequestSpec,
    stats: ScenarioStats,
    semaphore: asyncio.Semaphore,
) -> None:
    await semaphore.acquire()
    started = time.perf_counter()
    try:
        headers = {
            "X-Vendor-Id": spec.vendor_id,
            "X-Request-Id": f"lt-{time.time_ns()}",
        }
        response = await client.post(url, json=spec.payload, headers=headers)
        latency_ms = (time.perf_counter() - started) * 1000.0
        stats.total_requests += 1
        stats.latency_ms.append(latency_ms)

        vendor_stats = stats.vendor(spec.vendor_id)
        vendor_stats.requests += 1
        vendor_stats.latency_ms.append(latency_ms)

        if 200 <= response.status_code < 300:
            stats.http_2xx += 1
            vendor_stats.http_2xx += 1
        elif 400 <= response.status_code < 500:
            stats.http_4xx += 1
            vendor_stats.http_4xx += 1
        else:
            stats.http_5xx += 1
            vendor_stats.http_5xx += 1

        data: dict[str, Any] = {}
        if response.headers.get("content-type", "").startswith("application/json"):
            try:
                data = response.json()
            except Exception:
                data = {}

        accepted = int(data.get("accepted", 0))
        published = int(data.get("published", accepted))
        rejected = int(data.get("rejected", 0))
        stats.app_accepted += accepted
        stats.app_published += published
        stats.app_rejected += rejected
        vendor_stats.app_accepted += accepted
        vendor_stats.app_published += published
        vendor_stats.app_rejected += rejected

        error_summary = data.get("error_summary")
        if isinstance(error_summary, dict):
            validation = error_summary.get("validation", {})
            normalization = error_summary.get("normalization", {})
            publish = error_summary.get("publish", {})
            validation_failed = int(validation.get("failed", 0)) + int(normalization.get("failed", 0))
            publish_failed = int(publish.get("failed", 0))
            stats.app_validation_failed += validation_failed
            stats.app_publish_failed += publish_failed
            vendor_stats.app_validation_failed += validation_failed
            vendor_stats.app_publish_failed += publish_failed
    except Exception:
        stats.transport_failures += 1
        stats.total_requests += 1
        vendor_stats = stats.vendor(spec.vendor_id)
        vendor_stats.requests += 1
    finally:
        try:
            semaphore.release()
        except RuntimeError:
            pass  # loop already closed during teardown; safe to ignore


async def _run_rate_scenario(
    *,
    scenario_name: str,
    duration_seconds: int,
    rate_by_second: list[int],
    config: LoadTestConfig,
    trucks: list[Truck],
    failure_mode: bool,
    invalid_ratio: float,
) -> ScenarioStats:
    expected_events = sum(rate_by_second)
    stats = ScenarioStats(
        name=scenario_name,
        duration_seconds=duration_seconds,
        expected_events=expected_events,
    )
    print(
        f"[loadtest] {scenario_name}: start duration={duration_seconds}s expected_events={expected_events}",
        flush=True,
    )
    semaphore = asyncio.Semaphore(config.concurrency)
    rng = random.Random(config.seed + hash(scenario_name))
    truck_idx = 0
    vendor_trucks = _group_trucks_by_vendor(trucks)
    vendor_indices = {vendor_id: 0 for vendor_id in vendor_trucks}
    vendor_cycle = [truck.vendor_id for truck in trucks[: len(DEFAULT_VENDOR_IDS)]]
    tasks: set[asyncio.Task[None]] = set()

    endpoint = f"{config.base_url.rstrip('/')}{config.endpoint}"
    timeout = httpx.Timeout(config.timeout_seconds)
    max_connections = config.concurrency
    if sys.platform == "win32":
        max_connections = min(max_connections, WINDOWS_SELECTOR_CONNECTION_CAP)
    limits = httpx.Limits(max_connections=max_connections, max_keepalive_connections=max_connections)
    request_rate_cap = max_connections * REQUESTS_PER_SECOND_MULTIPLIER
    if sys.platform == "win32":
        request_rate_cap = min(request_rate_cap, WINDOWS_REQUESTS_PER_SECOND_CAP)
    max_inflight_tasks = max(max_connections, request_rate_cap)

    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        started = time.perf_counter()
        try:
            if max_connections != config.concurrency:
                print(
                    (
                        f"[loadtest] {scenario_name}: capping http connections to {max_connections} "
                        f"on Windows selector loop (requested concurrency={config.concurrency})"
                    ),
                    flush=True,
                )
            for second in range(duration_seconds):
                if second % 5 == 0:
                    print(
                        f"[loadtest] {scenario_name}: second={second}/{duration_seconds}",
                        flush=True,
                    )
                    tasks = {t for t in tasks if not t.done()}
                second_rate = max(0, rate_by_second[second])
                if second_rate == 0:
                    await asyncio.sleep(1)
                    continue
                request_rate = min(second_rate, request_rate_cap)
                batch_size = max(1, math.ceil(second_rate / request_rate))
                if second == 0 and batch_size > 1:
                    print(
                        (
                            f"[loadtest] {scenario_name}: batching {batch_size} payloads/request "
                            f"to sustain target_eps={second_rate} with request_rate={request_rate}"
                        ),
                        flush=True,
                    )
                sec_start = started + second
                interval = 1.0 / float(request_rate)
                generated_events = 0
                for i in range(request_rate):
                    planned_at = sec_start + i * interval
                    now = time.perf_counter()
                    if planned_at > now:
                        await asyncio.sleep(planned_at - now)
                    while len(tasks) >= max_inflight_tasks:
                        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                        del done
                        tasks = pending
                    remaining_events = second_rate - generated_events
                    current_batch_size = min(batch_size, remaining_events)
                    payload: list[dict[str, Any]] = []
                    vendor_id = vendor_cycle[truck_idx % len(vendor_cycle)]
                    vendor_pool = vendor_trucks[vendor_id]
                    for _ in range(current_batch_size):
                        truck = vendor_pool[vendor_indices[vendor_id] % len(vendor_pool)]
                        vendor_indices[vendor_id] += 1
                        truck_idx += 1
                        valid = _build_valid_event(truck, truck_idx, rng)
                        if failure_mode and rng.random() < invalid_ratio:
                            payload.extend(_build_invalid_payload(valid, rng))
                        else:
                            payload.append(valid)
                        generated_events += 1
                    spec = RequestSpec(vendor_id=vendor_id, payload=payload)
                    tasks.add(
                        asyncio.create_task(
                            _send_one(
                                client=client,
                                url=endpoint,
                                spec=spec,
                                stats=stats,
                                semaphore=semaphore,
                            )
                        )
                    )

            pending = [t for t in tasks if not t.done()]
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
        except asyncio.CancelledError:
            # Cancel all in-flight tasks immediately so they don't get GC'd
            # as pending coroutines during Python shutdown.
            for t in tasks:
                if not t.done():
                    t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
    print(
        (
            f"[loadtest] {scenario_name}: done requests={stats.total_requests} "
            f"published={stats.app_published} rejected={stats.app_rejected}"
        ),
        flush=True,
    )
    return stats


def _format_markdown_report(config: LoadTestConfig, reports: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    now = datetime.now(tz=UTC).isoformat()
    lines.append("# GPS Ingestion Load Test Report")
    lines.append("")
    lines.append(f"Generated at: {now}")
    lines.append("")
    lines.append("## Test Configuration")
    lines.append("")
    lines.append(f"- Base URL: {config.base_url}")
    lines.append(f"- Endpoint: {config.endpoint}")
    lines.append(f"- Simulated trucks: {config.trucks}")
    lines.append(f"- Target events/sec: {config.target_eps}")
    lines.append(f"- Concurrency: {config.concurrency}")
    lines.append("")

    for report in reports:
        scenario = report["scenario"]
        latency = report["latency"]
        http = report["http"]
        app = report["application"]
        throughput = report["throughput"]

        lines.append(f"## Scenario: {scenario}")
        lines.append("")
        lines.append("### Throughput")
        lines.append("")
        lines.append(f"- Requests/sec: {throughput['requests_per_sec']}")
        lines.append(f"- Payload/sec (published): {throughput['payload_per_sec']}")
        lines.append("")
        lines.append("### Latency")
        lines.append("")
        lines.append(f"- avg: {latency['avg_ms']} ms")
        lines.append(f"- p50: {latency['p50_ms']} ms")
        lines.append(f"- p95: {latency['p95_ms']} ms")
        lines.append(f"- p99: {latency['p99_ms']} ms")
        lines.append(f"- max: {latency['max_ms']} ms")
        lines.append("")
        lines.append("### Failures")
        lines.append("")
        lines.append(f"- HTTP 4xx: {http['4xx']}")
        lines.append(f"- HTTP 5xx: {http['5xx']}")
        lines.append(f"- Transport failures: {http['transport_failures']}")
        lines.append(f"- Validation failures: {app['validation_failures']}")
        lines.append(f"- Publish failures: {app['publish_failures']}")
        lines.append("")
        lines.append("### Vendor Breakdown")
        lines.append("")
        lines.append("| Vendor | Requests | Published | Validation Failures | Publish Failures | p95 (ms) |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for vendor, details in report["vendor_breakdown"].items():
            p95 = details["latency"]["p95_ms"]
            lines.append(
                f"| {vendor} | {details['requests']} | {details['published']} | "
                f"{details['validation_failures']} | {details['publish_failures']} | {p95} |"
            )
        lines.append("")

    return "\n".join(lines)


async def _run_suite(config: LoadTestConfig) -> dict[str, Any]:
    print("[loadtest] suite started", flush=True)
    trucks = _make_trucks(config.trucks)

    steady_rates = [config.target_eps for _ in range(config.duration_seconds)]
    burst_rates = [_rate_burst(s, config.target_eps) for s in range(config.duration_seconds)]
    latency_rates = [max(1, int(config.target_eps * 0.4)) for _ in range(max(10, config.duration_seconds // 2))]
    failure_rates = [config.target_eps for _ in range(config.duration_seconds)]

    steady = await _run_rate_scenario(
        scenario_name="steady_traffic",
        duration_seconds=config.duration_seconds,
        rate_by_second=steady_rates,
        config=config,
        trucks=trucks,
        failure_mode=False,
        invalid_ratio=0.0,
    )
    burst = await _run_rate_scenario(
        scenario_name="burst_traffic",
        duration_seconds=config.duration_seconds,
        rate_by_second=burst_rates,
        config=config,
        trucks=trucks,
        failure_mode=False,
        invalid_ratio=0.0,
    )
    latency = await _run_rate_scenario(
        scenario_name="latency_benchmark",
        duration_seconds=len(latency_rates),
        rate_by_second=latency_rates,
        config=config,
        trucks=trucks,
        failure_mode=False,
        invalid_ratio=0.0,
    )
    failure = await _run_rate_scenario(
        scenario_name="failure_benchmark",
        duration_seconds=config.duration_seconds,
        rate_by_second=failure_rates,
        config=config,
        trucks=trucks,
        failure_mode=True,
        invalid_ratio=0.20,
    )

    reports = [
        _scenario_report(steady),
        _scenario_report(burst),
        _scenario_report(latency),
        _scenario_report(failure),
    ]
    print("[loadtest] suite finished", flush=True)
    return {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "config": {
            "base_url": config.base_url,
            "endpoint": config.endpoint,
            "trucks": config.trucks,
            "target_eps": config.target_eps,
            "duration_seconds": config.duration_seconds,
            "concurrency": config.concurrency,
            "timeout_seconds": config.timeout_seconds,
            "seed": config.seed,
        },
        "scenarios": reports,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GPS webhook load test suite")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--endpoint", default="/webhook/gps")
    parser.add_argument("--trucks", type=int, default=600)
    parser.add_argument("--target-eps", type=int, default=3000)
    parser.add_argument("--duration-seconds", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=1200)
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--report-dir", default="scripts/loadtest/reports")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    config = LoadTestConfig(
        base_url=args.base_url,
        endpoint=args.endpoint,
        trucks=args.trucks,
        target_eps=args.target_eps,
        duration_seconds=args.duration_seconds,
        concurrency=args.concurrency,
        timeout_seconds=args.timeout_seconds,
        report_dir=Path(args.report_dir),
        seed=args.seed,
    )

    # Suppress noisy GC errors that fire when pending coroutines are closed
    # after the event loop has been shut down (Python 3.14 stricter finalizers).
    import sys as _sys
    _orig_unraisable = _sys.unraisablehook
    def _silent_unraisable(exc_info: _sys.UnraisableHookArgs) -> None:
        if isinstance(exc_info.exc_value, RuntimeError) and "closed" in str(exc_info.exc_value):
            return
        _orig_unraisable(exc_info)
    _sys.unraisablehook = _silent_unraisable

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # Suppress "Task was destroyed but it is pending!" messages that asyncio
    # emits via the loop exception handler (not catchable via warnings module).
    loop.set_exception_handler(lambda _loop, ctx: None)
    suite_report: dict[str, Any] | None = None
    try:
        suite_report = loop.run_until_complete(_run_suite(config))
    except KeyboardInterrupt:
        print("\n[loadtest] interrupted by user (Ctrl+C). Exiting cleanly.", flush=True)
        raise SystemExit(130)
    except Exception as exc:
        print(f"\n[loadtest] suite error: {exc}", flush=True)
        raise SystemExit(1)
    finally:
        # Each scenario awaits all its tasks before returning, so there are no
        # dangling tasks here. Just close the loop; skip shutdown_asyncgens
        # which can hang waiting for httpx/anyio internal generators.
        try:
            loop.close()
        except Exception:
            pass

    assert suite_report is not None
    config.report_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
    json_path = config.report_dir / f"gps-loadtest-{ts}.json"
    md_path = config.report_dir / f"gps-loadtest-{ts}.md"

    json_path.write_text(json.dumps(suite_report, indent=2), encoding="utf-8")
    md_path.write_text(
        _format_markdown_report(config, suite_report["scenarios"]),
        encoding="utf-8",
    )

    print(f"Load test completed. JSON report: {json_path}")
    print(f"Load test completed. Markdown report: {md_path}")


if __name__ == "__main__":
    # On Windows, ProactorEventLoop exhausts socket buffers at high concurrency.
    # SelectorEventLoop avoids the socketpair self-pipe and handles large fan-outs.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()
