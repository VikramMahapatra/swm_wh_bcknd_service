from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from swm_db.device_repository import DeviceRepository
from swm_db.models import DeviceORM


def _mock_session() -> MagicMock:
    ses = MagicMock(spec=AsyncSession)
    ses.execute = AsyncMock()
    ses.flush = AsyncMock()
    ses.refresh = AsyncMock()
    ses.delete = AsyncMock()
    ses.add = MagicMock()
    ses.add_all = MagicMock()
    return ses


def _scalar_result(value: Any) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalars.return_value.all.return_value = value if isinstance(value, list) else [value]
    return result


def _device(**kwargs: Any) -> DeviceORM:
    vendor_id = kwargs.pop("vendor_id", uuid.uuid4())
    obj = DeviceORM(
        vendor_id=vendor_id,
        imei=kwargs.pop("imei", "123456789012345"),
        health_status=kwargs.pop("health_status", "healthy"),
        metadata_json=kwargs.pop("metadata_json", {}),
        **kwargs,
    )
    if obj.id is None:  # type: ignore[attr-defined]
        obj.id = uuid.uuid4()
    return obj


class TestDeviceRepository:
    @pytest.mark.asyncio
    async def test_create_adds_flushes_refreshes(self) -> None:
        ses = _mock_session()
        repo = DeviceRepository(ses)

        device = await repo.create(
            vendor_id=uuid.uuid4(),
            imei="123456789012345",
            health_status="healthy",
            metadata_json={},
        )

        ses.add.assert_called_once()
        ses.flush.assert_awaited_once()
        ses.refresh.assert_awaited_once_with(device)

    @pytest.mark.asyncio
    async def test_get_by_id_returns_row(self) -> None:
        ses = _mock_session()
        device = _device()
        ses.execute.return_value = _scalar_result(device)

        found = await DeviceRepository(ses).get_by_id(device.id)
        assert found is device

    @pytest.mark.asyncio
    async def test_get_by_imei_returns_row(self) -> None:
        ses = _mock_session()
        device = _device(imei="123456789012346")
        ses.execute.return_value = _scalar_result(device)

        found = await DeviceRepository(ses).get_by_imei("123456789012346")
        assert found is device

    @pytest.mark.asyncio
    async def test_update_raises_when_missing(self) -> None:
        ses = _mock_session()
        ses.execute.return_value = _scalar_result(None)

        with pytest.raises(NoResultFound):
            await DeviceRepository(ses).update(uuid.uuid4(), model="X")

    @pytest.mark.asyncio
    async def test_delete_calls_session_delete(self) -> None:
        ses = _mock_session()
        device = _device()
        ses.execute.return_value = _scalar_result(device)

        await DeviceRepository(ses).delete(device.id)
        ses.delete.assert_awaited_once_with(device)
        ses.flush.assert_awaited_once()
