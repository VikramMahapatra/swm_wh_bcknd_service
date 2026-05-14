"""Typed Redis GEO service for fleet location use cases.

Capabilities:
- GEOADD
- GEOSEARCH
- Radius search
- Nearest vehicle
- Depot proximity
- Zone lookup
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from swm_common import get_logger
from swm_redis.client import RedisClient

logger = get_logger("swm_redis.geo")


class GeoUnit(StrEnum):
    M = "m"
    KM = "km"
    MI = "mi"
    FT = "ft"


class GeoSort(StrEnum):
    ASC = "ASC"
    DESC = "DESC"


@dataclass(slots=True)
class GeoConfig:
    vehicles_key: str = "geo:vehicles"
    depots_key: str = "geo:depots"
    zones_key: str = "geo:zones"
    default_unit: GeoUnit = GeoUnit.KM


@dataclass(slots=True)
class GeoPoint:
    member: str
    longitude: float
    latitude: float


@dataclass(slots=True)
class GeoSearchResult:
    member: str
    distance: float
    unit: GeoUnit


class RedisGeoService:
    """Typed API for Redis GEO operations and fleet-centric lookup helpers."""

    def __init__(self, redis_client: RedisClient, *, config: GeoConfig | None = None) -> None:
        self.redis = redis_client
        self.config = config or GeoConfig()

    async def geoadd(self, key: str, points: list[GeoPoint]) -> int:
        """Add one or more geo points with GEOADD semantics."""
        members = [(point.longitude, point.latitude, point.member) for point in points]
        return await self.redis.geoadd(key, members)

    async def geosearch(
        self,
        key: str,
        *,
        longitude: float,
        latitude: float,
        radius: float,
        unit: GeoUnit | None = None,
        limit: int | None = None,
        sort: GeoSort = GeoSort.ASC,
    ) -> list[GeoSearchResult]:
        """Search nearby members around coordinate center."""
        used_unit = unit or self.config.default_unit
        raw = await self.redis.run_operation(
            lambda: self.redis.client.geosearch(
                key,
                longitude=longitude,
                latitude=latitude,
                radius=radius,
                unit=used_unit.value,
                sort=sort.value,
                count=limit,
                withdist=True,
            ),
            operation="geosearch",
        )
        return self._parse_geosearch(raw, used_unit)

    async def radius_search(
        self,
        *,
        longitude: float,
        latitude: float,
        radius_km: float,
        limit: int | None = None,
    ) -> list[GeoSearchResult]:
        """Radius search for vehicles around a point."""
        return await self.geosearch(
            self.config.vehicles_key,
            longitude=longitude,
            latitude=latitude,
            radius=radius_km,
            unit=GeoUnit.KM,
            limit=limit,
            sort=GeoSort.ASC,
        )

    async def nearest_vehicle(
        self,
        *,
        longitude: float,
        latitude: float,
        max_radius_km: float = 50,
    ) -> GeoSearchResult | None:
        """Find nearest vehicle within radius; returns None when no result."""
        found = await self.radius_search(
            longitude=longitude,
            latitude=latitude,
            radius_km=max_radius_km,
            limit=1,
        )
        return found[0] if found else None

    async def depot_proximity(
        self,
        *,
        longitude: float,
        latitude: float,
        radius_km: float,
        limit: int | None = None,
    ) -> list[GeoSearchResult]:
        """Find depots within radius from a coordinate."""
        return await self.geosearch(
            self.config.depots_key,
            longitude=longitude,
            latitude=latitude,
            radius=radius_km,
            unit=GeoUnit.KM,
            limit=limit,
            sort=GeoSort.ASC,
        )

    async def zone_lookup(
        self,
        *,
        longitude: float,
        latitude: float,
        radius_km: float = 5,
        limit: int | None = 1,
    ) -> list[GeoSearchResult]:
        """Lookup nearest zone(s) using zone centroids in Redis GEO."""
        return await self.geosearch(
            self.config.zones_key,
            longitude=longitude,
            latitude=latitude,
            radius=radius_km,
            unit=GeoUnit.KM,
            limit=limit,
            sort=GeoSort.ASC,
        )

    async def add_vehicle_position(self, *, vehicle_id: str, longitude: float, latitude: float) -> int:
        """Upsert vehicle position into geo vehicles key."""
        return await self.geoadd(
            self.config.vehicles_key,
            [GeoPoint(member=vehicle_id, longitude=longitude, latitude=latitude)],
        )

    async def add_depot(self, *, depot_id: str, longitude: float, latitude: float) -> int:
        """Add depot location."""
        return await self.geoadd(
            self.config.depots_key,
            [GeoPoint(member=depot_id, longitude=longitude, latitude=latitude)],
        )

    async def add_zone(self, *, zone_id: str, longitude: float, latitude: float) -> int:
        """Add zone centroid location."""
        return await self.geoadd(
            self.config.zones_key,
            [GeoPoint(member=zone_id, longitude=longitude, latitude=latitude)],
        )

    async def vehicle_distance_km(self, vehicle_a: str, vehicle_b: str) -> float | None:
        """Distance between two vehicles in km."""
        distance = await self.redis.geodist(
            self.config.vehicles_key,
            vehicle_a,
            vehicle_b,
            unit=GeoUnit.KM.value,
        )
        if distance is None:
            return None
        return float(distance)

    async def vehicle_position(self, vehicle_id: str) -> tuple[float, float] | None:
        """Current position from GEO index for one vehicle."""
        result = await self.redis.geopos(self.config.vehicles_key, vehicle_id)
        if not result or result[0] is None:
            return None
        longitude, latitude = result[0]
        return float(longitude), float(latitude)

    def _parse_geosearch(self, raw: Any, unit: GeoUnit) -> list[GeoSearchResult]:
        if raw is None:
            return []

        parsed: list[GeoSearchResult] = []
        for item in raw:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                member = item[0].decode("utf-8") if isinstance(item[0], bytes) else str(item[0])
                distance = float(item[1])
            else:
                member = item.decode("utf-8") if isinstance(item, bytes) else str(item)
                distance = 0.0

            parsed.append(GeoSearchResult(member=member, distance=distance, unit=unit))

        return parsed
