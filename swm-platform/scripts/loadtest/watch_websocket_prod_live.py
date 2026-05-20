#!/usr/bin/env python3
"""Watch production websocket updates and print compact live rows."""

from __future__ import annotations

import argparse
import asyncio
import json
import ssl
from datetime import UTC, datetime
from typing import Any

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed


def utc_now() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S")


def log(message: str) -> None:
    print(f"[{utc_now()}] {message}")


def build_ssl_context() -> tuple[ssl.SSLContext, str]:
    try:
        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT), "truststore"
    except ImportError:
        return ssl.create_default_context(), "default"


def as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def print_payload(record: dict[str, Any]) -> None:
    imei = as_text(record.get("imei"))
    vehicle_id = as_text(record.get("vehicle_id"))
    lat = as_text(record.get("lat"))
    lng = as_text(record.get("lng"))
    speed = as_text(record.get("speed"))
    status = as_text(record.get("status"))
    event_ts = as_text(record.get("event_ts"))

    log(
        "WS "
        f"imei={imei} vehicle={vehicle_id} lat={lat} lng={lng} "
        f"speed={speed} status={status} ts={event_ts}"
    )


async def run(args: argparse.Namespace) -> None:
    ssl_context, mode = build_ssl_context()
    log(f"connecting websocket={args.websocket_url} tls_context={mode}")

    async with connect(args.websocket_url, ssl=ssl_context, open_timeout=15.0, ping_interval=None) as websocket:
        log("connected")

        while True:
            try:
                raw_message = await asyncio.wait_for(websocket.recv(), timeout=args.timeout_seconds)
            except asyncio.TimeoutError:
                log(f"no message in {args.timeout_seconds:.1f}s")
                continue
            except ConnectionClosed as exc:
                log(f"closed code={exc.code} reason={exc.reason}")
                break

            if isinstance(raw_message, bytes):
                try:
                    raw_message = raw_message.decode("utf-8")
                except UnicodeDecodeError:
                    log(f"binary={raw_message!r}")
                    continue

            try:
                obj = json.loads(raw_message)
            except json.JSONDecodeError:
                log(f"raw={raw_message}")
                continue

            if isinstance(obj, dict) and isinstance(obj.get("payload"), dict):
                print(obj)
                print_payload(obj["payload"])
            elif isinstance(obj, dict):
                print_payload(obj)
            else:
                log(f"raw={obj}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch production websocket live stream")
    parser.add_argument("--websocket-url", default="wss://websocket-swm.zentrixel.com/ws/realtime")
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        log("stopped")


if __name__ == "__main__":
    main()
