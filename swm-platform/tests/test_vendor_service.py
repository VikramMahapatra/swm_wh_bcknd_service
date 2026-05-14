from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from swm_db.models import VendorORM
from swm_db.vendor_service import VendorCreateInput, VendorService, VendorUpdateInput


def _vendor() -> VendorORM:
    return VendorORM(
        id=uuid.uuid4(),
        vendor_code="VEN_201",
        vendor_name="Vendor 201",
        allowed_ips=["127.0.0.1"],
        auth_type="header",
        callback_format={},
        metadata_json={},
    )


class TestVendorService:
    @pytest.mark.asyncio
    async def test_create_vendor_maps_payload(self) -> None:
        repo = AsyncMock()
        created = _vendor()
        repo.create.return_value = created

        service = VendorService(repo)
        result = await service.create_vendor(
            VendorCreateInput(
                vendor_code="ven_201",
                vendor_name="Vendor 201",
                metadata={"tier": "gold"},
            )
        )

        assert result is created
        repo.create.assert_awaited_once()
        _, kwargs = repo.create.await_args
        assert kwargs["vendor_code"] == "ven_201"
        assert kwargs["metadata_json"] == {"tier": "gold"}

    @pytest.mark.asyncio
    async def test_update_vendor_builds_partial_update_map(self) -> None:
        repo = AsyncMock()
        updated = _vendor()
        repo.update.return_value = updated

        service = VendorService(repo)
        vendor_id = uuid.uuid4()
        result = await service.update_vendor(
            vendor_id,
            VendorUpdateInput(email="ops@vendor.com", active=False, metadata={"tier": "silver"}),
        )

        assert result is updated
        repo.update.assert_awaited_once()
        args, kwargs = repo.update.await_args
        assert args[0] == vendor_id
        assert kwargs["email"] == "ops@vendor.com"
        assert kwargs["active"] is False
        assert kwargs["metadata_json"] == {"tier": "silver"}

    @pytest.mark.asyncio
    async def test_activate_and_deactivate_vendor(self) -> None:
        repo = AsyncMock()
        repo.update.return_value = _vendor()

        service = VendorService(repo)
        vendor_id = uuid.uuid4()

        await service.activate_vendor(vendor_id)
        await service.deactivate_vendor(vendor_id)

        assert repo.update.await_count == 2
