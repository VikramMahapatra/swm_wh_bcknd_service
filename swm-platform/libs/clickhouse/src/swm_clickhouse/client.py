from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import clickhouse_connect
import pyarrow as pa
import pyarrow.parquet as pq
from swm_common import get_logger
from swm_models import CanonicalTelemetry

logger = get_logger("swm_clickhouse.client")


class ClickHouseRawTelemetryClient:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
        fallback_dir: str = "./data/parquet_fallback/raw_telemetry",
    ) -> None:
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.fallback_dir = Path(fallback_dir)

    def _sync_client(self) -> Any:
        return clickhouse_connect.get_client(
            host=self.host,
            port=self.port,
            database=self.database,
            username=self.username,
            password=self.password,
        )

    async def ensure_table(self) -> None:
        ddl = """
        CREATE TABLE IF NOT EXISTS raw_telemetry (
            imei String,
            vendor_id UUID,
            device_id UUID,
            vehicle_id UUID,
            event_ts DateTime64(3, 'UTC'),
            received_ts DateTime64(3, 'UTC'),
            lat Float64,
            lng Float64,
            speed Float32,
            heading UInt16,
            altitude Nullable(Float32),
            acc_status UInt8,
            odometer Nullable(Float64),
            fuel_level Nullable(Float32),
            payload_json String,
            INDEX idx_vehicle_id vehicle_id TYPE bloom_filter(0.01) GRANULARITY 64,
            INDEX idx_event_ts event_ts TYPE minmax GRANULARITY 1
        )
        ENGINE = MergeTree
        PARTITION BY toYYYYMM(event_ts)
        ORDER BY (vehicle_id, event_ts)
        TTL event_ts + INTERVAL 24 MONTH DELETE
        """

        def _ensure() -> None:
            client = self._sync_client()
            try:
                client.command(ddl)
            finally:
                client.close()

        await asyncio.to_thread(_ensure)

    async def insert_raw_telemetry_batch(self, events: list[CanonicalTelemetry]) -> int:
        if not events:
            return 0

        rows = [
            [
                e.imei,
                self._to_uuid_or_zero(e.vendor_id),
                self._to_uuid_or_zero(e.device_id),
                self._to_uuid_or_zero(e.vehicle_id),
                e.event_ts,
                e.received_ts,
                e.lat,
                e.lng,
                float(e.speed),
                e.heading,
                None,
                e.acc_status,
                e.odometer,
                float(e.fuel_level) if e.fuel_level is not None else None,
                str(e.raw_payload),
            ]
            for e in events
        ]

        def _insert() -> int:
            client = self._sync_client()
            try:
                client.insert(
                    "raw_telemetry",
                    rows,
                    column_names=[
                        "imei",
                        "vendor_id",
                        "device_id",
                        "vehicle_id",
                        "event_ts",
                        "received_ts",
                        "lat",
                        "lng",
                        "speed",
                        "heading",
                        "altitude",
                        "acc_status",
                        "odometer",
                        "fuel_level",
                        "payload_json",
                    ],
                )
                return len(rows)
            finally:
                client.close()

        try:
            return await asyncio.to_thread(_insert)
        except Exception as exc:
            logger.error("clickhouse_insert_failed", error=str(exc), batch_size=len(events))
            await self.write_parquet_fallback(events, reason=str(exc))
            raise

    async def write_parquet_fallback(self, events: list[CanonicalTelemetry], *, reason: str) -> Path:
        self.fallback_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S-%f")
        path = self.fallback_dir / f"raw_telemetry_{ts}.parquet"

        table = pa.table(
            {
                "imei": [e.imei for e in events],
                "lat": [e.lat for e in events],
                "lng": [e.lng for e in events],
                "speed": [e.speed for e in events],
                "heading": [e.heading for e in events],
                "acc_status": [e.acc_status for e in events],
                "odometer": [e.odometer for e in events],
                "fuel_level": [e.fuel_level for e in events],
                "vendor_id": [e.vendor_id for e in events],
                "device_id": [e.device_id for e in events],
                "vehicle_id": [e.vehicle_id for e in events],
                "event_ts": [e.event_ts for e in events],
                "received_ts": [e.received_ts for e in events],
                "payload_json": [str(e.raw_payload) for e in events],
                "fallback_reason": [reason for _ in events],
            }
        )

        await asyncio.to_thread(pq.write_table, table, path)
        logger.warning("clickhouse_fallback_parquet_written", path=str(path), batch_size=len(events))
        return path

    def _to_uuid_or_zero(self, value: str) -> str:
        try:
            return str(UUID(value))
        except Exception:
            return "00000000-0000-0000-0000-000000000000"
