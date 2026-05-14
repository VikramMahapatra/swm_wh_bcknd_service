from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from swm_db.device_repository import DeviceRepository
from swm_db.models import DeviceORM


@dataclass(slots=True)
class DeviceCreateInput:
    vendor_id: uuid.UUID
    imei: str
    serial_no: str | None = None
    model: str | None = None
    manufacturer: str | None = None
    firmware_version: str | None = None
    sim_number: str | None = None
    installed_on: datetime | None = None
    activated_on: datetime | None = None
    last_seen: datetime | None = None
    battery_percent: float | None = None
    signal_strength: float | None = None
    health_status: str = "healthy"
    active: bool = True
    metadata: dict[str, Any] | None = None


@dataclass(slots=True)
class DeviceUpdateInput:
    serial_no: str | None = None
    model: str | None = None
    manufacturer: str | None = None
    firmware_version: str | None = None
    sim_number: str | None = None
    installed_on: datetime | None = None
    activated_on: datetime | None = None
    last_seen: datetime | None = None
    battery_percent: float | None = None
    signal_strength: float | None = None
    health_status: str | None = None
    active: bool | None = None
    metadata: dict[str, Any] | None = None


class DeviceService:
    """CRUD service layer for Device master."""

    def __init__(self, repository: DeviceRepository) -> None:
        self._repository = repository

    async def create_device(self, payload: DeviceCreateInput) -> DeviceORM:
        return await self._repository.create(
            vendor_id=payload.vendor_id,
            imei=payload.imei,
            serial_no=payload.serial_no,
            model=payload.model,
            manufacturer=payload.manufacturer,
            firmware_version=payload.firmware_version,
            sim_number=payload.sim_number,
            installed_on=payload.installed_on,
            activated_on=payload.activated_on,
            last_seen=payload.last_seen,
            battery_percent=payload.battery_percent,
            signal_strength=payload.signal_strength,
            health_status=payload.health_status,
            active=payload.active,
            metadata_json=payload.metadata or {},
        )

    async def get_device(self, device_id: uuid.UUID) -> DeviceORM | None:
        return await self._repository.get_by_id(device_id)

    async def get_device_by_imei(self, imei: str) -> DeviceORM | None:
        return await self._repository.get_by_imei(imei)

    async def list_vendor_devices(
        self,
        vendor_id: uuid.UUID,
        *,
        active_only: bool | None = None,
    ) -> list[DeviceORM]:
        return await self._repository.list_by_vendor(vendor_id, active_only=active_only)

    async def update_device(self, device_id: uuid.UUID, payload: DeviceUpdateInput) -> DeviceORM:
        updates: dict[str, Any] = {}
        if payload.serial_no is not None:
            updates["serial_no"] = payload.serial_no
        if payload.model is not None:
            updates["model"] = payload.model
        if payload.manufacturer is not None:
            updates["manufacturer"] = payload.manufacturer
        if payload.firmware_version is not None:
            updates["firmware_version"] = payload.firmware_version
        if payload.sim_number is not None:
            updates["sim_number"] = payload.sim_number
        if payload.installed_on is not None:
            updates["installed_on"] = payload.installed_on
        if payload.activated_on is not None:
            updates["activated_on"] = payload.activated_on
        if payload.last_seen is not None:
            updates["last_seen"] = payload.last_seen
        if payload.battery_percent is not None:
            updates["battery_percent"] = payload.battery_percent
        if payload.signal_strength is not None:
            updates["signal_strength"] = payload.signal_strength
        if payload.health_status is not None:
            updates["health_status"] = payload.health_status
        if payload.active is not None:
            updates["active"] = payload.active
        if payload.metadata is not None:
            updates["metadata_json"] = payload.metadata

        return await self._repository.update(device_id, **updates)

    async def delete_device(self, device_id: uuid.UUID) -> None:
        await self._repository.delete(device_id)

    async def activate_device(self, device_id: uuid.UUID) -> DeviceORM:
        return await self._repository.update(device_id, active=True)

    async def deactivate_device(self, device_id: uuid.UUID) -> DeviceORM:
        return await self._repository.update(device_id, active=False)
