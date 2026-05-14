from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from swm_db.models import VendorORM
from swm_db.vendor_repository import VendorRepository


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


def _vendor(**kwargs: Any) -> VendorORM:
    obj = VendorORM(
        vendor_code=kwargs.pop("vendor_code", "VEN_001"),
        vendor_name=kwargs.pop("vendor_name", "Vendor One"),
        allowed_ips=kwargs.pop("allowed_ips", ["127.0.0.1"]),
        auth_type=kwargs.pop("auth_type", "header"),
        callback_format=kwargs.pop("callback_format", {}),
        metadata_json=kwargs.pop("metadata_json", {}),
        **kwargs,
    )
    if obj.id is None:  # type: ignore[attr-defined]
        obj.id = uuid.uuid4()
    return obj


class TestVendorRepository:
    @pytest.mark.asyncio
    async def test_create_adds_flushes_and_refreshes(self) -> None:
        ses = _mock_session()
        repo = VendorRepository(ses)

        created = await repo.create(
            vendor_code="VEN_101",
            vendor_name="Vendor 101",
            allowed_ips=["10.0.0.1"],
            auth_type="header",
            callback_format={},
            metadata_json={},
        )

        ses.add.assert_called_once()
        ses.flush.assert_awaited_once()
        ses.refresh.assert_awaited_once_with(created)

    @pytest.mark.asyncio
    async def test_get_by_id_returns_row(self) -> None:
        ses = _mock_session()
        vendor = _vendor()
        ses.execute.return_value = _scalar_result(vendor)

        found = await VendorRepository(ses).get_by_id(vendor.id)
        assert found is vendor

    @pytest.mark.asyncio
    async def test_get_by_code_normalizes_input(self) -> None:
        ses = _mock_session()
        vendor = _vendor(vendor_code="VEN_ABC")
        ses.execute.return_value = _scalar_result(vendor)

        found = await VendorRepository(ses).get_by_code(" ven_abc ")
        assert found is vendor

    @pytest.mark.asyncio
    async def test_list_returns_items(self) -> None:
        ses = _mock_session()
        vendors = [_vendor(vendor_code="VEN_A"), _vendor(vendor_code="VEN_B")]
        ses.execute.return_value = _scalar_result(vendors)

        items = await VendorRepository(ses).list()
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_update_raises_for_missing_vendor(self) -> None:
        ses = _mock_session()
        ses.execute.return_value = _scalar_result(None)

        with pytest.raises(NoResultFound):
            await VendorRepository(ses).update(uuid.uuid4(), vendor_name="Updated")

    @pytest.mark.asyncio
    async def test_delete_calls_session_delete(self) -> None:
        ses = _mock_session()
        vendor = _vendor()
        ses.execute.return_value = _scalar_result(vendor)

        await VendorRepository(ses).delete(vendor.id)
        ses.delete.assert_awaited_once_with(vendor)
        ses.flush.assert_awaited_once()
