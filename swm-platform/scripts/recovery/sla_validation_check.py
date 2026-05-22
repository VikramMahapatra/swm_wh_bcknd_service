from __future__ import annotations

import argparse
import asyncio
import time
from dataclasses import dataclass

import httpx
from swm_redis import RedisClient

HTTP_OK = 200


@dataclass(slots=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


async def _check_http(url: str, timeout_seconds: float, max_latency_ms: float) -> CheckResult:
    started = time.perf_counter()
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.get(url)
    latency_ms = (time.perf_counter() - started) * 1000.0
    ok = response.status_code == HTTP_OK and latency_ms <= max_latency_ms
    detail = f"status={response.status_code} latency_ms={latency_ms:.2f}"
    return CheckResult(name=url, ok=ok, detail=detail)


async def _check_stream(redis: RedisClient, stream: str, max_len: int) -> CheckResult:
    current = int(await redis.xlen(stream))
    ok = current <= max_len
    return CheckResult(
        name=f"stream:{stream}",
        ok=ok,
        detail=f"len={current} max_allowed={max_len}",
    )


async def _run(args: argparse.Namespace) -> int:
    checks: list[CheckResult] = []

    checks.append(
        await _check_http(
            f"{args.ingestion_base_url.rstrip('/')}/healthz",
            args.timeout_seconds,
            args.max_health_latency_ms,
        )
    )
    checks.append(
        await _check_http(
            f"{args.admin_base_url.rstrip('/')}/healthz",
            args.timeout_seconds,
            args.max_health_latency_ms,
        )
    )
    checks.append(
        await _check_http(
            f"{args.websocket_base_url.rstrip('/')}/healthz",
            args.timeout_seconds,
            args.max_health_latency_ms,
        )
    )

    redis = RedisClient.from_url(args.redis_url)
    checks.append(await _check_stream(redis, args.raw_stream, args.max_raw_stream_len))
    checks.append(await _check_stream(redis, args.retry_stream, args.max_retry_stream_len))
    checks.append(await _check_stream(redis, args.dlq_stream, args.max_dlq_stream_len))

    failures = [item for item in checks if not item.ok]
    for item in checks:
        state = "PASS" if item.ok else "FAIL"
        print(f"[{state}] {item.name} {item.detail}")

    return 0 if not failures else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run SLA/SLO readiness checks for platform recovery drills."
    )
    parser.add_argument("--ingestion-base-url", default="http://127.0.0.1:9001")
    parser.add_argument("--admin-base-url", default="http://127.0.0.1:9003")
    parser.add_argument("--websocket-base-url", default="http://127.0.0.1:9002")
    parser.add_argument("--redis-url", default="redis://127.0.0.1:6379/0")
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument("--max-health-latency-ms", type=float, default=250.0)

    parser.add_argument("--raw-stream", default="gps.telemetry.raw")
    parser.add_argument("--retry-stream", default="gps.telemetry.retry")
    parser.add_argument("--dlq-stream", default="gps.telemetry.failed")

    parser.add_argument("--max-raw-stream-len", type=int, default=1_000_000)
    parser.add_argument("--max-retry-stream-len", type=int, default=50_000)
    parser.add_argument("--max-dlq-stream-len", type=int, default=10_000)
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
