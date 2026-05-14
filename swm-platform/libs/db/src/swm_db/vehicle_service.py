from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from swm_db.models import VehicleORM
from swm_db.vehicle_repository import VehicleRepository


@dataclass(slots=True)
class VehicleCreateInput:
    vehicle_number: str
    registration_number: str
    contractor_id: uuid.UUID
    ward_id: uuid.UUID
    route_id: uuid.UUID | None = None
    truck_type: str | None = None
    capacity_kg: float = 0
    capacity_cubic_meter: float = 0
    fuel_type: str = "diesel"
    operational_status: str = "operational"
    chassis_number: str | None = None
    engine_number: str | None = None
    manufacture_year: int | None = None
    active: bool = True
    metadata: dict[str, Any] | None = None


@dataclass(slots=True)
class VehicleUpdateInput:
    route_id: uuid.UUID | None = None
    truck_type: str | None = None
    capacity_kg: float | None = None
    capacity_cubic_meter: float | None = None
    fuel_type: str | None = None
    operational_status: str | None = None
    chassis_number: str | None = None
    engine_number: str | None = None
    manufacture_year: int | None = None
    active: bool | None = None
    metadata: dict[str, Any] | None = None


class VehicleService:
    """CRUD service layer for Vehicle master."""

    def __init__(self, repository: VehicleRepository) -> None:
        self._repository = repository

    async def create_vehicle(self, payload: VehicleCreateInput) -> VehicleORM:
        return await self._repository.create(
            vehicle_number=payload.vehicle_number,
            registration_number=payload.registration_number,
            contractor_id=payload.contractor_id,
            ward_id=payload.ward_id,
            route_id=payload.route_id,
            truck_type=payload.truck_type,
            capacity_kg=payload.capacity_kg,
            capacity_cubic_meter=payload.capacity_cubic_meter,
            fuel_type=payload.fuel_type,
            operational_status=payload.operational_status,
            chassis_number=payload.chassis_number,
            engine_number=payload.engine_number,
            manufacture_year=payload.manufacture_year,
            active=payload.active,
            metadata_json=payload.metadata or {},
        )

    async def get_vehicle(self, vehicle_id: uuid.UUID) -> VehicleORM | None:
        return await self._repository.get_by_id(vehicle_id)

    async def get_vehicle_by_number(self, vehicle_number: str) -> VehicleORM | None:
        return await self._repository.get_by_vehicle_number(vehicle_number)

    async def get_vehicle_by_registration(self, registration_number: str) -> VehicleORM | None:
        return await self._repository.get_by_registration_number(registration_number)

    async def list_vehicles(
        self,
        *,
        contractor_id: uuid.UUID | None = None,
        ward_id: uuid.UUID | None = None,
        route_id: uuid.UUID | None = None,
        active_only: bool | None = None,
    ) -> list[VehicleORM]:
        return await self._repository.list(
            contractor_id=contractor_id,
            ward_id=ward_id,
            route_id=route_id,
            active_only=active_only,
        )

    async def update_vehicle(self, vehicle_id: uuid.UUID, payload: VehicleUpdateInput) -> VehicleORM:
        updates: dict[str, Any] = {}
        if payload.route_id is not None:
            updates["route_id"] = payload.route_id
        if payload.truck_type is not None:
            updates["truck_type"] = payload.truck_type
        if payload.capacity_kg is not None:
            updates["capacity_kg"] = payload.capacity_kg
        if payload.capacity_cubic_meter is not None:
            updates["capacity_cubic_meter"] = payload.capacity_cubic_meter
        if payload.fuel_type is not None:
            updates["fuel_type"] = payload.fuel_type
        if payload.operational_status is not None:
            updates["operational_status"] = payload.operational_status
        if payload.chassis_number is not None:
            updates["chassis_number"] = payload.chassis_number
        if payload.engine_number is not None:
            updates["engine_number"] = payload.engine_number
        if payload.manufacture_year is not None:
            updates["manufacture_year"] = payload.manufacture_year
        if payload.active is not None:
            updates["active"] = payload.active
        if payload.metadata is not None:
            updates["metadata_json"] = payload.metadata

        return await self._repository.update(vehicle_id, **updates)

    async def delete_vehicle(self, vehicle_id: uuid.UUID) -> None:
        await self._repository.delete(vehicle_id)

    async def activate_vehicle(self, vehicle_id: uuid.UUID) -> VehicleORM:
        return await self._repository.update(vehicle_id, active=True)

    async def deactivate_vehicle(self, vehicle_id: uuid.UUID) -> VehicleORM:
        return await self._repository.update(vehicle_id, active=False)
