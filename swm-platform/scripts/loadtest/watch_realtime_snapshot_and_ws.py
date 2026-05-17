#!/usr/bin/env python3
"""Watch the realtime truck snapshot and websocket stream.

The script fetches the initial snapshot from the admin API and then listens to
the live websocket feed, printing each record to stdout and appending the same
lines to a text log file.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from websockets.exceptions import ConnectionClosed
from websockets.asyncio.client import connect


def timestamp() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S")


def write_log_line(output_path: Path, message: str) -> None:
    line = f"[{timestamp()}] {message}"
    print(line)
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def get_value(record: Any, names: tuple[str, ...]) -> str:
    if not isinstance(record, dict):
        return ""

    for name in names:
        value = record.get(name)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text

    return ""


def format_record(prefix: str, record: dict[str, Any]) -> str:
    imei = get_value(record, ("imei", "IMEI"))
    vehicle = get_value(record, ("vehicle_id", "vehicleId", "vehicle"))
    lat = get_value(record, ("lat", "latitude"))
    lng = get_value(record, ("lng", "lon", "longitude"))
    speed = get_value(record, ("speed", "speed_kph", "speedKph"))
    status = get_value(record, ("status", "state"))
    event_ts = get_value(record, ("event_ts", "ts", "timestamp", "time"))
    return (
        f"{prefix} imei={imei} vehicle={vehicle} lat={lat} lng={lng} "
        f"speed={speed} status={status} ts={event_ts}"
    )


def is_truck_payload(record: dict[str, Any]) -> bool:
    return any(key in record for key in ("imei", "vehicle_id", "lat", "lng", "speed", "status", "event_ts"))


def normalize_payload(payload: Any) -> list[Any]:
    if payload is None:
        return []

    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            return []
        try:
            return normalize_payload(json.loads(text))
        except json.JSONDecodeError:
            return [payload]

    if isinstance(payload, dict):
        if "payload" in payload:
            return normalize_payload(payload["payload"])
        if "data" in payload:
            return normalize_payload(payload["data"])
        return [payload]

    if isinstance(payload, Iterable):
        items: list[Any] = []
        for item in payload:
            items.extend(normalize_payload(item))
        return items

    return [payload]


async def fetch_snapshot(admin_api_url: str, output_path: Path) -> None:
    url = f"{admin_api_url.rstrip('/')}/v1/realtime/trucks"
    write_log_line(output_path, f"Fetching snapshot from {url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers={"x-role": "viewer"})
        response.raise_for_status()
        payload = response.json()

    items = payload.get("items", []) if isinstance(payload, dict) else []
    total = payload.get("total", len(items)) if isinstance(payload, dict) else len(items)
    write_log_line(output_path, f"Snapshot total={total} items={len(items)}")

    for item in items:
        if isinstance(item, dict):
            write_log_line(output_path, format_record("SNAPSHOT", item))
        else:
            write_log_line(output_path, f"SNAPSHOT raw={item}")


async def watch_websocket(websocket_url: str, output_path: Path, duration_minutes: int) -> None:
    deadline = None
    if duration_minutes > 0:
        deadline = asyncio.get_running_loop().time() + (duration_minutes * 60)

    write_log_line(output_path, f"Connecting websocket to {websocket_url}")

    async with connect(websocket_url) as websocket:
        write_log_line(output_path, "WebSocket connected")

        while True:
            if deadline is not None and asyncio.get_running_loop().time() >= deadline:
                write_log_line(output_path, "Duration reached; closing websocket")
                break

            try:
                raw_message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except ConnectionClosed:
                write_log_line(output_path, "WebSocket closed")
                break

            payload: Any
            if isinstance(raw_message, bytes):
                try:
                    raw_message = raw_message.decode("utf-8")
                except UnicodeDecodeError:
                    write_log_line(output_path, f"WS raw_bytes={raw_message!r}")
                    continue

            try:
                payload = json.loads(raw_message)
            except json.JSONDecodeError:
                write_log_line(output_path, f"WS raw={raw_message}")
                continue

            records = normalize_payload(payload)
            if not records:
                write_log_line(output_path, f"WS raw={raw_message}")
                continue

            for record in records:
                if isinstance(record, dict):
                    if "payload" in record and isinstance(record["payload"], dict):
                        write_log_line(output_path, format_record("WS", record["payload"]))
                        continue

                    if is_truck_payload(record):
                        write_log_line(output_path, format_record("WS", record))
                        continue

                    write_log_line(output_path, f"WS raw={record}")
                else:
                    write_log_line(output_path, f"WS raw={record}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Watch realtime snapshot and websocket updates")
    parser.add_argument("--admin-api-url", default="http://127.0.0.1:8003")
    parser.add_argument("--websocket-url", default="ws://127.0.0.1:8002/ws/realtime")
    parser.add_argument("--output-path", default="./realtime-watch.log")
    parser.add_argument("--duration-minutes", type=int, default=0)
    args = parser.parse_args()

    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    write_log_line(output_path, "Starting realtime watcher")
    await fetch_snapshot(args.admin_api_url, output_path)
    await watch_websocket(args.websocket_url, output_path, args.duration_minutes)
    write_log_line(output_path, "Watcher finished")


if __name__ == "__main__":
    asyncio.run(main())