#!/usr/bin/env python3
"""Smoke-test remote SWM service endpoints.

The script checks the ingestion webhook, admin-api, Grafana, and Prometheus
HTTP endpoints and performs a real websocket handshake against the realtime
endpoint.
"""

from __future__ import annotations

import argparse
import asyncio
import ssl
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

import httpx
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed


@dataclass(slots=True)
class CheckResult:
    name: str
    ok: bool
    details: str


HTTP_ERROR_STATUS = 400
WEBSOCKET_PREVIEW_LIMIT = 200


def ensure_scheme(url: str, default_scheme: str) -> str:
    text = url.strip()
    if "//" not in text:
        return f"{default_scheme}://{text}"
    return text


def ensure_http_url(url: str, default_path: str) -> str:
    normalized = ensure_scheme(url, "https")
    parsed = urlparse(normalized)
    path = parsed.path or ""
    if path in {"", "/"}:
        parsed = parsed._replace(path=default_path)
    return urlunparse(parsed)


def ensure_websocket_url(url: str, default_path: str) -> str:
    normalized = ensure_scheme(url, "wss")
    parsed = urlparse(normalized)
    path = parsed.path or ""
    if path in {"", "/"}:
        parsed = parsed._replace(path=default_path)
    return urlunparse(parsed)


def build_websocket_ssl_context() -> tuple[ssl.SSLContext, str]:
    try:
        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT), "truststore"
    except ImportError:
        # Fall back to Python's default CA resolution when truststore isn't installed.
        return ssl.create_default_context(), "default"


async def check_http(name: str, url: str, timeout_seconds: float, allow_405: bool = False) -> CheckResult:
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
            response = await client.get(url)
        details = f"status={response.status_code} final_url={response.url}"
        if response.status_code >= HTTP_ERROR_STATUS:
            # 405 Method Not Allowed means endpoint exists but doesn't accept GET
            if allow_405 and response.status_code == 405:
                return CheckResult(name=name, ok=True, details=f"{details} (endpoint exists, POST-only)")
            body = response.text.strip()
            if body:
                details = f"{details} body={body[:500]!r}"
            return CheckResult(name=name, ok=False, details=details)
        return CheckResult(name=name, ok=True, details=details)
    except Exception as exc:
        return CheckResult(name=name, ok=False, details=str(exc))


async def check_websocket(
    url: str,
    timeout_seconds: float,
    listen_seconds: float,
    ssl_context: ssl.SSLContext,
    ssl_context_mode: str,
) -> CheckResult:
    try:
        async with connect(url, ssl=ssl_context, open_timeout=timeout_seconds, ping_interval=None) as websocket:
            details = ["connected", f"tls_context={ssl_context_mode}"]
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=listen_seconds)
            except TimeoutError:
                details.append(f"no message received within {listen_seconds:.1f}s")
            except ConnectionClosed as exc:
                return CheckResult(
                    name="websocket",
                    ok=False,
                    details=f"connected_then_closed code={exc.code} reason={exc.reason}",
                )
            else:
                if isinstance(message, bytes):
                    preview = message[:120]
                    details.append(f"binary_message={preview!r}")
                else:
                    preview = message.strip()
                    if len(preview) > WEBSOCKET_PREVIEW_LIMIT:
                        preview = preview[:WEBSOCKET_PREVIEW_LIMIT] + "..."
                    details.append(f"text_message={preview!r}")

            return CheckResult(name="websocket", ok=True, details="; ".join(details))
    except ssl.SSLCertVerificationError as exc:
        details = str(exc)
        if ssl_context_mode == "default":
            details = (
                f"{details} (tip: install truststore and rerun: python -m pip install truststore)"
            )
        return CheckResult(name="websocket", ok=False, details=details)
    except Exception as exc:
        return CheckResult(name="websocket", ok=False, details=str(exc))


async def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test SWM remote endpoints")
    parser.add_argument("--ingestion-url", default="ingestion-swm.zentrixel.com")
    parser.add_argument("--grafana-url", default="grafana-swm.zentrixel.com")
    parser.add_argument("--prometheus-url", default="grafana-swm.zentrixel.com/prometheus")
    parser.add_argument("--admin-api-url", default="api-swm.zentrixel.com")
    parser.add_argument("--webhook-url", default="ingestion-swm.zentrixel.com/webhook/gps")
    parser.add_argument("--websocket-url", default="websocket-swm.zentrixel.com")
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--listen-seconds", type=float, default=5.0)
    args = parser.parse_args()

    ingestion_url = ensure_http_url(args.ingestion_url, "/healthz")
    grafana_url = ensure_http_url(args.grafana_url, "/api/health")
    prometheus_url = ensure_http_url(args.prometheus_url, "/prometheus/-/healthy")
    admin_api_url = ensure_http_url(args.admin_api_url, "/healthz")
    webhook_url = ensure_http_url(args.webhook_url, "/webhook/gps")
    websocket_url = ensure_websocket_url(args.websocket_url, "/ws/realtime")
    websocket_ssl_context, websocket_ssl_context_mode = build_websocket_ssl_context()

    checks = [
        await check_http("ingestion", ingestion_url, args.timeout_seconds),
        await check_http("grafana", grafana_url, args.timeout_seconds),
        await check_http("prometheus", prometheus_url, args.timeout_seconds),
        await check_http("admin-api", admin_api_url, args.timeout_seconds),
        await check_http("webhook", webhook_url, args.timeout_seconds, allow_405=True),
        await check_websocket(
            websocket_url,
            args.timeout_seconds,
            args.listen_seconds,
            websocket_ssl_context,
            websocket_ssl_context_mode,
        ),
    ]

    print("Remote endpoint smoke test")
    print(f"- ingestion: {ingestion_url}")
    print(f"- grafana:   {grafana_url}")
    print(f"- prometheus:{prometheus_url}")
    print(f"- admin-api: {admin_api_url}")
    print(f"- webhook:   {webhook_url}")
    print(f"- websocket: {websocket_url}")

    failed = False
    for result in checks:
        status = "OK" if result.ok else "FAIL"
        print(f"[{status}] {result.name}: {result.details}")
        failed = failed or not result.ok

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
