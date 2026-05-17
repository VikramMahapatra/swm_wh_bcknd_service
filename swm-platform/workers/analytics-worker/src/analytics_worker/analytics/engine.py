from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from analytics_worker.analytics.geo import haversine_km, point_in_polygon
from swm_db import (
    AnalyticsDailyKPIORM,
    AnalyticsGeofenceEventORM,
    AnalyticsIdleRecordORM,
    AnalyticsOverspeedEventORM,
    AnalyticsTripRecordORM,
    AnalyticsVehicleStateORM,
    DatabaseSessionManager,
    EngineConfig,
    GeofenceORM,
    VehicleORM,
)
from swm_models import CanonicalTelemetry
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class AnalyticsConfig:
    moving_speed_kph: float = 5.0
    idle_speed_kph: float = 1.0
    overspeed_kph: float = 80.0
    idle_min_seconds: int = 180
    idle_stationary_radius_m: float = 25.0
    trip_end_stationary_seconds: int = 420
    trip_start_odometer_delta_km: float = 0.05
    route_deviation_cooldown_seconds: int = 300
    operational_hours_per_day: float = 8.0
    fuel_efficiency_kmpl: float = 4.5
    max_gap_seconds: int = 3600
    max_segment_km: float = 5.0

    @classmethod
    def from_env(cls) -> "AnalyticsConfig":
        return cls(
            moving_speed_kph=float(os.getenv("ANALYTICS_MOVING_SPEED_KPH", "5")),
            idle_speed_kph=float(os.getenv("ANALYTICS_IDLE_SPEED_KPH", "1")),
            overspeed_kph=float(os.getenv("ANALYTICS_OVERSPEED_KPH", "80")),
            idle_min_seconds=int(os.getenv("ANALYTICS_IDLE_MIN_SECONDS", "180")),
            idle_stationary_radius_m=float(os.getenv("ANALYTICS_IDLE_STATIONARY_RADIUS_M", "25")),
            trip_end_stationary_seconds=int(os.getenv("ANALYTICS_TRIP_END_STATIONARY_SECONDS", "420")),
            trip_start_odometer_delta_km=float(os.getenv("ANALYTICS_TRIP_START_ODO_DELTA_KM", "0.05")),
            route_deviation_cooldown_seconds=int(os.getenv("ANALYTICS_ROUTE_DEV_COOLDOWN_SECONDS", "300")),
            operational_hours_per_day=float(os.getenv("ANALYTICS_OPERATIONAL_HOURS_PER_DAY", "8")),
            fuel_efficiency_kmpl=float(os.getenv("ANALYTICS_FUEL_EFFICIENCY_KMPL", "4.5")),
            max_gap_seconds=int(os.getenv("ANALYTICS_MAX_GAP_SECONDS", "3600")),
            max_segment_km=float(os.getenv("ANALYTICS_MAX_SEGMENT_KM", "5")),
        )


class AnalyticsEngine:
    def __init__(self, postgres_dsn: str) -> None:
        self._session_manager = DatabaseSessionManager(EngineConfig(dsn=postgres_dsn))
        self._config = AnalyticsConfig.from_env()
        self._geofence_cache: list[dict[str, Any]] = []
        self._geofence_cache_loaded_at: datetime | None = None
        self._expected_geofence_cache: dict[str, set[str]] = {}
        self._expected_cache_loaded_at: datetime | None = None

    async def close(self) -> None:
        await self._session_manager.close()

    async def process_batch(self, events: list[CanonicalTelemetry]) -> dict[str, int]:
        if not events:
            return {
                "events": 0,
                "trip_records": 0,
                "idle_records": 0,
                "overspeed_events": 0,
                "geofence_events": 0,
            }

        events.sort(key=lambda e: (e.vehicle_id, e.event_ts))
        vehicle_ids = list({e.vehicle_id for e in events})

        async with self._session_manager.session() as session:
            states = await self._load_states(session, vehicle_ids)
            geofences = await self._load_geofences(session)
            expected_geofences = await self._load_expected_geofences(session)

            trip_rows: list[dict[str, Any]] = []
            idle_rows: list[dict[str, Any]] = []
            overspeed_rows: list[dict[str, Any]] = []
            geofence_rows: list[dict[str, Any]] = []
            daily_deltas: dict[tuple[Any, ...], dict[str, Any]] = {}

            for event in events:
                state = states.get(event.vehicle_id)
                if state is None:
                    state = self._new_state(event)

                result = self._process_event(
                    event,
                    state,
                    geofences,
                    expected_geofences.get(event.vehicle_id, set()),
                )

                trip_rows.extend(result["trip_rows"])
                idle_rows.extend(result["idle_rows"])
                overspeed_rows.extend(result["overspeed_rows"])
                geofence_rows.extend(result["geofence_rows"])
                self._merge_daily_delta(daily_deltas, result["daily_delta"])
                states[event.vehicle_id] = state

            if trip_rows:
                await session.execute(sa.insert(AnalyticsTripRecordORM.__table__), trip_rows)
            if idle_rows:
                await session.execute(sa.insert(AnalyticsIdleRecordORM.__table__), idle_rows)
            if overspeed_rows:
                await session.execute(sa.insert(AnalyticsOverspeedEventORM.__table__), overspeed_rows)
            if geofence_rows:
                await session.execute(sa.insert(AnalyticsGeofenceEventORM.__table__), geofence_rows)

            await self._upsert_states(session, list(states.values()))
            if daily_deltas:
                await self._upsert_daily_kpis(session, list(daily_deltas.values()))

        return {
            "events": len(events),
            "trip_records": len(trip_rows),
            "idle_records": len(idle_rows),
            "overspeed_events": len(overspeed_rows),
            "geofence_events": len(geofence_rows),
        }

    async def _load_states(self, session: AsyncSession, vehicle_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not vehicle_ids:
            return {}
        rows = await session.execute(
            sa.select(AnalyticsVehicleStateORM).where(AnalyticsVehicleStateORM.vehicle_id.in_(vehicle_ids))
        )
        return {row.vehicle_id: self._state_from_orm(row) for row in rows.scalars().all()}

    async def _load_geofences(self, session: AsyncSession) -> list[dict[str, Any]]:
        now = datetime.now(tz=UTC)
        if self._geofence_cache_loaded_at and (now - self._geofence_cache_loaded_at).total_seconds() < 60:
            return self._geofence_cache

        rows = await session.execute(sa.select(GeofenceORM).where(GeofenceORM.active.is_(True)))
        geofences: list[dict[str, Any]] = []
        for gf in rows.scalars().all():
            polygon_points: list[list[float]] = []
            if gf.polygon and isinstance(gf.polygon, dict):
                coords = gf.polygon.get("coordinates") or []
                if coords and isinstance(coords[0], list):
                    ring = coords[0]
                    polygon_points = [
                        [float(point[0]), float(point[1])]
                        for point in ring
                        if isinstance(point, list) and len(point) >= 2
                    ]

            geofences.append(
                {
                    "id": gf.id,
                    "code": gf.geofence_code,
                    "type": gf.type,
                    "geometry_type": gf.geometry_type,
                    "center_lat": gf.center_lat,
                    "center_lng": gf.center_lng,
                    "radius_meter": gf.radius_meter,
                    "polygon": polygon_points,
                }
            )

        self._geofence_cache = geofences
        self._geofence_cache_loaded_at = now
        return geofences

    async def _load_expected_geofences(self, session: AsyncSession) -> dict[str, set[str]]:
        now = datetime.now(tz=UTC)
        if self._expected_cache_loaded_at and (now - self._expected_cache_loaded_at).total_seconds() < 60:
            return self._expected_geofence_cache

        rows = await session.execute(
            sa.select(sa.cast(VehicleORM.id, sa.String), GeofenceORM.geofence_code)
            .join(GeofenceORM, GeofenceORM.ward_id == VehicleORM.ward_id)
            .where(GeofenceORM.active.is_(True), VehicleORM.active.is_(True))
        )

        result: dict[str, set[str]] = defaultdict(set)
        for vehicle_id, geofence_code in rows.all():
            result[str(vehicle_id)].add(geofence_code)

        self._expected_geofence_cache = dict(result)
        self._expected_cache_loaded_at = now
        return self._expected_geofence_cache

    def _new_state(self, event: CanonicalTelemetry) -> dict[str, Any]:
        return {
            "vehicle_id": event.vehicle_id,
            "imei": event.imei,
            "device_id": event.device_id,
            "last_event_ts": event.event_ts,
            "last_lat": event.lat,
            "last_lng": event.lng,
            "last_speed_kph": float(event.speed),
            "last_odometer_km": event.odometer,
            "last_ignition": bool(event.acc_status),
            "trip_active": False,
            "trip_started_at": None,
            "trip_start_odometer_km": None,
            "trip_distance_km": 0.0,
            "trip_runtime_seconds": 0,
            "trip_moving_seconds": 0,
            "trip_idle_seconds": 0,
            "trip_stoppages": 0,
            "idle_active": False,
            "idle_started_at": None,
            "idle_anchor_lat": None,
            "idle_anchor_lng": None,
            "current_geofence_code": None,
            "current_geofence_entered_at": None,
            "last_route_deviation_at": None,
        }

    def _state_from_orm(self, row: AnalyticsVehicleStateORM) -> dict[str, Any]:
        return {
            "vehicle_id": row.vehicle_id,
            "imei": row.imei,
            "device_id": row.device_id,
            "last_event_ts": row.last_event_ts,
            "last_lat": row.last_lat,
            "last_lng": row.last_lng,
            "last_speed_kph": row.last_speed_kph,
            "last_odometer_km": row.last_odometer_km,
            "last_ignition": row.last_ignition,
            "trip_active": row.trip_active,
            "trip_started_at": row.trip_started_at,
            "trip_start_odometer_km": row.trip_start_odometer_km,
            "trip_distance_km": row.trip_distance_km,
            "trip_runtime_seconds": row.trip_runtime_seconds,
            "trip_moving_seconds": row.trip_moving_seconds,
            "trip_idle_seconds": row.trip_idle_seconds,
            "trip_stoppages": row.trip_stoppages,
            "idle_active": row.idle_active,
            "idle_started_at": row.idle_started_at,
            "idle_anchor_lat": row.idle_anchor_lat,
            "idle_anchor_lng": row.idle_anchor_lng,
            "current_geofence_code": row.current_geofence_code,
            "current_geofence_entered_at": row.current_geofence_entered_at,
            "last_route_deviation_at": row.last_route_deviation_at,
        }

    def _process_event(
        self,
        event: CanonicalTelemetry,
        state: dict[str, Any],
        geofences: list[dict[str, Any]],
        expected_geofences: set[str],
    ) -> dict[str, Any]:
        cfg = self._config
        trip_rows: list[dict[str, Any]] = []
        idle_rows: list[dict[str, Any]] = []
        overspeed_rows: list[dict[str, Any]] = []
        geofence_rows: list[dict[str, Any]] = []

        metric_date = event.event_ts.date()
        daily_delta = {
            "metric_date": metric_date,
            "vehicle_id": event.vehicle_id,
            "imei": event.imei,
            "vendor_id": event.vendor_id,
            "trips_count": 0,
            "distance_km": 0.0,
            "runtime_seconds": 0,
            "moving_seconds": 0,
            "idle_seconds": 0,
            "stoppages_count": 0,
            "overspeed_count": 0,
            "geofence_entries": 0,
            "geofence_exits": 0,
            "route_deviation_count": 0,
            "fuel_used_l": 0.0,
        }

        prev_ts = state.get("last_event_ts")
        delta_seconds = 0
        if isinstance(prev_ts, datetime):
            dt = int((event.event_ts - prev_ts).total_seconds())
            if dt > 0:
                delta_seconds = min(dt, cfg.max_gap_seconds)

        distance_km = self._distance_increment_km(state, event)
        daily_delta["distance_km"] += distance_km
        daily_delta["fuel_used_l"] += distance_km / max(cfg.fuel_efficiency_kmpl, 0.1)

        ignition_on = bool(event.acc_status)
        moving = event.speed >= cfg.moving_speed_kph
        stationary = event.speed <= cfg.idle_speed_kph

        if ignition_on:
            daily_delta["runtime_seconds"] += delta_seconds
        if moving:
            daily_delta["moving_seconds"] += delta_seconds

        # Idle detection and segment finalization.
        if ignition_on and stationary and delta_seconds > 0:
            if not state["idle_active"]:
                state["idle_active"] = True
                state["idle_started_at"] = event.event_ts
                state["idle_anchor_lat"] = event.lat
                state["idle_anchor_lng"] = event.lng
            else:
                anchor_lat = state.get("idle_anchor_lat") or event.lat
                anchor_lng = state.get("idle_anchor_lng") or event.lng
                drift_m = haversine_km(anchor_lat, anchor_lng, event.lat, event.lng) * 1000
                if drift_m > cfg.idle_stationary_radius_m:
                    state["idle_active"] = False
                    state["idle_started_at"] = None
                    state["idle_anchor_lat"] = None
                    state["idle_anchor_lng"] = None

            if state["idle_active"]:
                daily_delta["idle_seconds"] += delta_seconds
                if state["trip_active"]:
                    state["trip_idle_seconds"] += delta_seconds
        elif state["idle_active"]:
            idle_started_at = state.get("idle_started_at")
            if isinstance(idle_started_at, datetime):
                idle_duration = int((event.event_ts - idle_started_at).total_seconds())
                if idle_duration >= cfg.idle_min_seconds:
                    idle_rows.append(
                        {
                            "vehicle_id": event.vehicle_id,
                            "imei": event.imei,
                            "device_id": event.device_id,
                            "vendor_id": event.vendor_id,
                            "started_at": idle_started_at,
                            "ended_at": event.event_ts,
                            "duration_seconds": idle_duration,
                            "lat": state.get("idle_anchor_lat") or event.lat,
                            "lng": state.get("idle_anchor_lng") or event.lng,
                        }
                    )
            state["idle_active"] = False
            state["idle_started_at"] = None
            state["idle_anchor_lat"] = None
            state["idle_anchor_lng"] = None

        # Trip detection lifecycle.
        previous_moving = state.get("last_speed_kph", 0.0) >= cfg.moving_speed_kph
        if not state["trip_active"]:
            odometer_delta = self._odometer_delta(state, event)
            should_start = ignition_on and moving and (
                odometer_delta is None or odometer_delta >= cfg.trip_start_odometer_delta_km
            )
            if should_start:
                state["trip_active"] = True
                state["trip_started_at"] = event.event_ts
                state["trip_start_odometer_km"] = event.odometer
                state["trip_distance_km"] = 0.0
                state["trip_runtime_seconds"] = 0
                state["trip_moving_seconds"] = 0
                state["trip_idle_seconds"] = 0
                state["trip_stoppages"] = 0

        if state["trip_active"]:
            if ignition_on:
                state["trip_runtime_seconds"] += delta_seconds
            if moving:
                state["trip_moving_seconds"] += delta_seconds
            state["trip_distance_km"] += distance_km

            if previous_moving and stationary and ignition_on:
                state["trip_stoppages"] += 1
                daily_delta["stoppages_count"] += 1

            idle_started_at = state.get("idle_started_at")
            stationary_for = 0
            if isinstance(idle_started_at, datetime):
                stationary_for = int((event.event_ts - idle_started_at).total_seconds())

            should_end_trip = (not ignition_on and stationary) or (
                state["idle_active"] and stationary_for >= cfg.trip_end_stationary_seconds
            )
            if should_end_trip and isinstance(state.get("trip_started_at"), datetime):
                trip_rows.append(
                    {
                        "vehicle_id": event.vehicle_id,
                        "imei": event.imei,
                        "device_id": event.device_id,
                        "vendor_id": event.vendor_id,
                        "started_at": state["trip_started_at"],
                        "ended_at": event.event_ts,
                        "runtime_seconds": state["trip_runtime_seconds"],
                        "moving_seconds": state["trip_moving_seconds"],
                        "idle_seconds": state["trip_idle_seconds"],
                        "stoppages_count": state["trip_stoppages"],
                        "start_odometer_km": state.get("trip_start_odometer_km"),
                        "end_odometer_km": event.odometer,
                        "distance_km": max(state["trip_distance_km"], 0.0),
                    }
                )
                daily_delta["trips_count"] += 1
                state["trip_active"] = False
                state["trip_started_at"] = None
                state["trip_start_odometer_km"] = None
                state["trip_distance_km"] = 0.0
                state["trip_runtime_seconds"] = 0
                state["trip_moving_seconds"] = 0
                state["trip_idle_seconds"] = 0
                state["trip_stoppages"] = 0

        # Overspeed alerts.
        if event.speed > cfg.overspeed_kph:
            severity = "critical" if event.speed >= cfg.overspeed_kph * 1.5 else "warning"
            overspeed_rows.append(
                {
                    "vehicle_id": event.vehicle_id,
                    "imei": event.imei,
                    "device_id": event.device_id,
                    "vendor_id": event.vendor_id,
                    "event_ts": event.event_ts,
                    "speed_kph": event.speed,
                    "threshold_kph": cfg.overspeed_kph,
                    "severity": severity,
                    "lat": event.lat,
                    "lng": event.lng,
                }
            )
            daily_delta["overspeed_count"] += 1

        # Geofence enter/exit + route deviation.
        matched_geofence = self._match_geofence(event, geofences)
        previous_geofence_code = state.get("current_geofence_code")

        if previous_geofence_code != (matched_geofence or {}).get("code"):
            if previous_geofence_code:
                entered_at = state.get("current_geofence_entered_at")
                dwell_seconds = None
                if isinstance(entered_at, datetime):
                    dwell_seconds = max(0, int((event.event_ts - entered_at).total_seconds()))
                geofence_rows.append(
                    {
                        "vehicle_id": event.vehicle_id,
                        "imei": event.imei,
                        "device_id": event.device_id,
                        "vendor_id": event.vendor_id,
                        "geofence_id": None,
                        "geofence_code": previous_geofence_code,
                        "geofence_type": None,
                        "event_type": "exit",
                        "event_ts": event.event_ts,
                        "dwell_seconds": dwell_seconds,
                        "lat": event.lat,
                        "lng": event.lng,
                    }
                )
                daily_delta["geofence_exits"] += 1

            if matched_geofence:
                geofence_rows.append(
                    {
                        "vehicle_id": event.vehicle_id,
                        "imei": event.imei,
                        "device_id": event.device_id,
                        "vendor_id": event.vendor_id,
                        "geofence_id": matched_geofence["id"],
                        "geofence_code": matched_geofence["code"],
                        "geofence_type": matched_geofence["type"],
                        "event_type": "entry",
                        "event_ts": event.event_ts,
                        "dwell_seconds": None,
                        "lat": event.lat,
                        "lng": event.lng,
                    }
                )
                daily_delta["geofence_entries"] += 1
                state["current_geofence_entered_at"] = event.event_ts
            else:
                state["current_geofence_entered_at"] = None

            state["current_geofence_code"] = (matched_geofence or {}).get("code")

        if expected_geofences and event.speed >= cfg.moving_speed_kph:
            inside_expected = matched_geofence is not None and matched_geofence["code"] in expected_geofences
            if not inside_expected:
                last_deviation_at = state.get("last_route_deviation_at")
                should_emit = True
                if isinstance(last_deviation_at, datetime):
                    cooldown = int((event.event_ts - last_deviation_at).total_seconds())
                    should_emit = cooldown >= cfg.route_deviation_cooldown_seconds
                if should_emit:
                    geofence_rows.append(
                        {
                            "vehicle_id": event.vehicle_id,
                            "imei": event.imei,
                            "device_id": event.device_id,
                            "vendor_id": event.vendor_id,
                            "geofence_id": None,
                            "geofence_code": None,
                            "geofence_type": None,
                            "event_type": "route_deviation",
                            "event_ts": event.event_ts,
                            "dwell_seconds": None,
                            "lat": event.lat,
                            "lng": event.lng,
                        }
                    )
                    daily_delta["route_deviation_count"] += 1
                    state["last_route_deviation_at"] = event.event_ts

        state["imei"] = event.imei
        state["device_id"] = event.device_id
        state["last_event_ts"] = event.event_ts
        state["last_lat"] = event.lat
        state["last_lng"] = event.lng
        state["last_speed_kph"] = float(event.speed)
        state["last_odometer_km"] = event.odometer
        state["last_ignition"] = ignition_on

        return {
            "trip_rows": trip_rows,
            "idle_rows": idle_rows,
            "overspeed_rows": overspeed_rows,
            "geofence_rows": geofence_rows,
            "daily_delta": daily_delta,
        }

    def _distance_increment_km(self, state: dict[str, Any], event: CanonicalTelemetry) -> float:
        odometer_delta = self._odometer_delta(state, event)
        if odometer_delta is not None:
            if 0 <= odometer_delta <= self._config.max_segment_km:
                return odometer_delta
            return 0.0

        last_lat = state.get("last_lat")
        last_lng = state.get("last_lng")
        if last_lat is None or last_lng is None:
            return 0.0

        dist = haversine_km(last_lat, last_lng, event.lat, event.lng)
        if 0 <= dist <= self._config.max_segment_km:
            return dist
        return 0.0

    def _odometer_delta(self, state: dict[str, Any], event: CanonicalTelemetry) -> float | None:
        last_odometer = state.get("last_odometer_km")
        if last_odometer is None or event.odometer is None:
            return None
        delta = float(event.odometer) - float(last_odometer)
        if delta < 0:
            return None
        return delta

    def _match_geofence(
        self,
        event: CanonicalTelemetry,
        geofences: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        for geofence in geofences:
            if geofence["geometry_type"] == "circle":
                if geofence["center_lat"] is None or geofence["center_lng"] is None or geofence["radius_meter"] is None:
                    continue
                distance_meter = (
                    haversine_km(event.lat, event.lng, geofence["center_lat"], geofence["center_lng"]) * 1000
                )
                if distance_meter <= float(geofence["radius_meter"]):
                    return geofence
            elif geofence["geometry_type"] == "polygon":
                polygon = geofence.get("polygon") or []
                if polygon and point_in_polygon(event.lat, event.lng, polygon):
                    return geofence
        return None

    def _merge_daily_delta(
        self,
        deltas: dict[tuple[Any, ...], dict[str, Any]],
        delta: dict[str, Any],
    ) -> None:
        key = (delta["metric_date"], delta["vehicle_id"])
        if key not in deltas:
            deltas[key] = delta
            return

        existing = deltas[key]
        for field in (
            "trips_count",
            "distance_km",
            "runtime_seconds",
            "moving_seconds",
            "idle_seconds",
            "stoppages_count",
            "overspeed_count",
            "geofence_entries",
            "geofence_exits",
            "route_deviation_count",
            "fuel_used_l",
        ):
            existing[field] += delta[field]

        existing["imei"] = delta["imei"]
        existing["vendor_id"] = delta["vendor_id"]

    async def _upsert_states(self, session: AsyncSession, states: list[dict[str, Any]]) -> None:
        if not states:
            return
        stmt = pg_insert(AnalyticsVehicleStateORM.__table__).values(states)
        update_cols = {
            "imei": stmt.excluded.imei,
            "device_id": stmt.excluded.device_id,
            "last_event_ts": stmt.excluded.last_event_ts,
            "last_lat": stmt.excluded.last_lat,
            "last_lng": stmt.excluded.last_lng,
            "last_speed_kph": stmt.excluded.last_speed_kph,
            "last_odometer_km": stmt.excluded.last_odometer_km,
            "last_ignition": stmt.excluded.last_ignition,
            "trip_active": stmt.excluded.trip_active,
            "trip_started_at": stmt.excluded.trip_started_at,
            "trip_start_odometer_km": stmt.excluded.trip_start_odometer_km,
            "trip_distance_km": stmt.excluded.trip_distance_km,
            "trip_runtime_seconds": stmt.excluded.trip_runtime_seconds,
            "trip_moving_seconds": stmt.excluded.trip_moving_seconds,
            "trip_idle_seconds": stmt.excluded.trip_idle_seconds,
            "trip_stoppages": stmt.excluded.trip_stoppages,
            "idle_active": stmt.excluded.idle_active,
            "idle_started_at": stmt.excluded.idle_started_at,
            "idle_anchor_lat": stmt.excluded.idle_anchor_lat,
            "idle_anchor_lng": stmt.excluded.idle_anchor_lng,
            "current_geofence_code": stmt.excluded.current_geofence_code,
            "current_geofence_entered_at": stmt.excluded.current_geofence_entered_at,
            "last_route_deviation_at": stmt.excluded.last_route_deviation_at,
            "updated_at": sa.func.current_timestamp(),
        }
        await session.execute(stmt.on_conflict_do_update(index_elements=["vehicle_id"], set_=update_cols))

    async def _upsert_daily_kpis(self, session: AsyncSession, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return

        op_seconds = max(self._config.operational_hours_per_day * 3600, 1.0)
        for row in rows:
            row["utilization_pct"] = min(100.0, (row["moving_seconds"] / op_seconds) * 100.0)

        table = AnalyticsDailyKPIORM.__table__
        stmt = pg_insert(table).values(rows)
        excluded = stmt.excluded

        moving_total = table.c.moving_seconds + excluded.moving_seconds
        utilization_expr = sa.func.least(100.0, (moving_total * 100.0) / op_seconds)

        await session.execute(
            stmt.on_conflict_do_update(
                index_elements=["metric_date", "vehicle_id"],
                set_={
                    "imei": excluded.imei,
                    "vendor_id": excluded.vendor_id,
                    "trips_count": table.c.trips_count + excluded.trips_count,
                    "distance_km": table.c.distance_km + excluded.distance_km,
                    "runtime_seconds": table.c.runtime_seconds + excluded.runtime_seconds,
                    "moving_seconds": moving_total,
                    "idle_seconds": table.c.idle_seconds + excluded.idle_seconds,
                    "stoppages_count": table.c.stoppages_count + excluded.stoppages_count,
                    "overspeed_count": table.c.overspeed_count + excluded.overspeed_count,
                    "geofence_entries": table.c.geofence_entries + excluded.geofence_entries,
                    "geofence_exits": table.c.geofence_exits + excluded.geofence_exits,
                    "route_deviation_count": table.c.route_deviation_count + excluded.route_deviation_count,
                    "fuel_used_l": table.c.fuel_used_l + excluded.fuel_used_l,
                    "utilization_pct": utilization_expr,
                    "updated_at": sa.func.current_timestamp(),
                },
            )
        )
