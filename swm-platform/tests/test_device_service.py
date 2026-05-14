from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from swm_db.device_service import DeviceCreateInput, DeviceService, DeviceUpdateInput
from swm_db.models import DeviceORM


def _device(vendor_id: uuid.UUID) -> DeviceORM:
    return DeviceORM(
        id=uuid.uuid4(),
        vendor_id=vendor_id,
        imei="123456789012345",
        health_status="healthy",
        metadata_json={},
    )


class TestDeviceService:
    @pytest.mark.asyncio
    async def test_create_device_maps_payload(self) -> None:
        vendor_id = uuid.uuid4()
        repo = AsyncMock()
        created = _device(vendor_id)
        repo.create.return_value = created

        service = DeviceService(repo)
        result = await service.create_device(
            DeviceCreateInput(
                vendor_id=vendor_id,
                imei="123456789012345",
                metadata={"hw": "v1"},
            )
        )

        assert result is created
        repo.create.assert_awaited_once()
        _, kwargs = repo.create.await_args
        assert kwargs["vendor_id"] == vendor_id
        assert kwargs["metadata_json"] == {"hw": "v1"}

    @pytest.mark.asyncio
    async def test_update_device_builds_partial_map(self) -> None:
        vendor_id = uuid.uuid4()
        repo = AsyncMock()
        repo.update.return_value = _device(vendor_id)

        service = DeviceService(repo)
        device_id = uuid.uuid4()
        await service.update_device(
            device_id,
            DeviceUpdateInput(model="X100", active=False, metadata={"fw": "2.0"}),
        )

        repo.update.assert_awaited_once()
        args, kwargs = repo.update.await_args
        assert args[0] == device_id
        assert kwargs["model"] == "X100"
        assert kwargs["active"] is False
        assert kwargs["metadata_json"] == {"fw": "2.0"}

    @pytest.mark.asyncio
    async def test_activate_and_deactivate_device(self) -> None:
        vendor_id = uuid.uuid4()
        repo = AsyncMock()
        repo.update.return_value = _device(vendor_id)

        service = DeviceService(repo)
        device_id = uuid.uuid4()

        await service.activate_device(device_id)
        await service.deactivate_device(device_id)

        assert repo.update.await_count == 2
