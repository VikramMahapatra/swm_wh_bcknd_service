from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _run_command(cmd: list[str]) -> None:
    rendered = " ".join(cmd)
    print(f"[drill] running: {rendered}", flush=True)
    subprocess.run(cmd, check=True)  # noqa: S603


def _latest_report(report_dir: Path) -> Path:
    candidates = sorted(report_dir.glob("gps-loadtest-*.json"))
    if not candidates:
        raise FileNotFoundError(f"No loadtest report found in {report_dir}")
    return candidates[-1]


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def _validate_scenario(
    scenario: dict[str, Any],
    *,
    max_http5xx_ratio: float,
    max_transport_failure_ratio: float,
    max_p95_ms: float,
    min_publish_ratio: float,
) -> list[str]:
    name = str(scenario.get("scenario", "unknown"))
    generated_requests = int(scenario.get("generated_requests", 0))
    expected_events = int(scenario.get("expected_events", 0))

    http = scenario.get("http", {})
    latency = scenario.get("latency", {})
    application = scenario.get("application", {})

    http_5xx = int(http.get("5xx", 0))
    transport_failures = int(http.get("transport_failures", 0))
    p95_ms = float(latency.get("p95_ms", 0.0))
    published = int(application.get("published", 0))

    http_5xx_ratio = _safe_ratio(http_5xx, generated_requests)
    transport_ratio = _safe_ratio(transport_failures, generated_requests)
    publish_ratio = _safe_ratio(published, expected_events)

    failures: list[str] = []
    if http_5xx_ratio > max_http5xx_ratio:
        failures.append(
            f"{name}: http_5xx_ratio={http_5xx_ratio:.4f} exceeds {max_http5xx_ratio:.4f}"
        )
    if transport_ratio > max_transport_failure_ratio:
        failures.append(
            f"{name}: transport_failure_ratio={transport_ratio:.4f} "
            f"exceeds {max_transport_failure_ratio:.4f}"
        )
    if p95_ms > max_p95_ms:
        failures.append(f"{name}: p95_ms={p95_ms:.2f} exceeds {max_p95_ms:.2f}")
    if publish_ratio < min_publish_ratio:
        failures.append(f"{name}: publish_ratio={publish_ratio:.4f} below {min_publish_ratio:.4f}")

    print(
        (
            f"[drill] scenario={name} p95_ms={p95_ms:.2f} "
            f"http_5xx_ratio={http_5xx_ratio:.4f} "
            f"transport_ratio={transport_ratio:.4f} "
            f"publish_ratio={publish_ratio:.4f}"
        ),
        flush=True,
    )
    return failures


def _validate_report(report_path: Path, args: argparse.Namespace) -> list[str]:
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    scenarios = payload.get("scenarios", [])
    if not isinstance(scenarios, list) or not scenarios:
        return ["loadtest report contains no scenarios"]

    failures: list[str] = []
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            failures.append("encountered malformed scenario in report")
            continue

        name = str(scenario.get("scenario", ""))
        if name == "failure_benchmark":
            failures.extend(
                _validate_scenario(
                    scenario,
                    max_http5xx_ratio=args.max_http5xx_ratio_failure,
                    max_transport_failure_ratio=args.max_transport_failure_ratio,
                    max_p95_ms=args.max_p95_ms,
                    min_publish_ratio=args.min_publish_ratio_failure,
                )
            )
        else:
            failures.extend(
                _validate_scenario(
                    scenario,
                    max_http5xx_ratio=args.max_http5xx_ratio,
                    max_transport_failure_ratio=args.max_transport_failure_ratio,
                    max_p95_ms=args.max_p95_ms,
                    min_publish_ratio=args.min_publish_ratio,
                )
            )
    return failures


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run resilience drill suite and enforce readiness thresholds."
    )
    parser.add_argument("--report-dir", default="scripts/loadtest/reports")

    parser.add_argument("--base-url", default="http://127.0.0.1:9001")
    parser.add_argument("--endpoint", default="/webhook/gps")
    parser.add_argument("--trucks", type=int, default=60)
    parser.add_argument("--target-eps", type=int, default=120)
    parser.add_argument("--duration-seconds", type=int, default=12)
    parser.add_argument("--concurrency", type=int, default=80)
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument("--seed", type=int, default=42)

    parser.add_argument("--max-http5xx-ratio", type=float, default=0.02)
    parser.add_argument("--max-http5xx-ratio-failure", type=float, default=0.05)
    parser.add_argument("--max-transport-failure-ratio", type=float, default=0.01)
    parser.add_argument("--max-p95-ms", type=float, default=300.0)
    parser.add_argument("--min-publish-ratio", type=float, default=0.90)
    parser.add_argument("--min-publish-ratio-failure", type=float, default=0.75)

    parser.add_argument("--admin-base-url", default="http://127.0.0.1:9003")
    parser.add_argument("--websocket-base-url", default="http://127.0.0.1:9002")
    parser.add_argument("--redis-url", default="redis://127.0.0.1:6379/0")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    _run_command(
        [
            sys.executable,
            "scripts/loadtest/gps_ingestion_load_test.py",
            "--base-url",
            args.base_url,
            "--endpoint",
            args.endpoint,
            "--trucks",
            str(args.trucks),
            "--target-eps",
            str(args.target_eps),
            "--duration-seconds",
            str(args.duration_seconds),
            "--concurrency",
            str(args.concurrency),
            "--timeout-seconds",
            str(args.timeout_seconds),
            "--seed",
            str(args.seed),
            "--report-dir",
            str(report_dir),
        ]
    )

    report_path = _latest_report(report_dir)
    print(f"[drill] validating report: {report_path}", flush=True)
    failures = _validate_report(report_path, args)

    _run_command(
        [
            sys.executable,
            "scripts/recovery/sla_validation_check.py",
            "--ingestion-base-url",
            args.base_url,
            "--admin-base-url",
            args.admin_base_url,
            "--websocket-base-url",
            args.websocket_base_url,
            "--redis-url",
            args.redis_url,
        ]
    )

    if failures:
        print("[drill] readiness gate failed", flush=True)
        for failure in failures:
            print(f"[drill] {failure}", flush=True)
        return 1

    print("[drill] readiness gate passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
