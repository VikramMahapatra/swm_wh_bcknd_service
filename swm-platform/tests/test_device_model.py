from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from swm_db.models import DeviceORM, VendorORM


def _vendor() -> VendorORM:
    return VendorORM(
        id=uuid.uuid4(),
        vendor_code="VEN_DEV",
        vendor_name="Vendor Devices",
        allowed_ips=["127.0.0.1"],
        auth_type="header",
        callback_format={},
        metadata_json={},
    )


class TestDeviceModelValidation:
    def test_device_accepts_valid_payload(self) -> None:
        vendor = _vendor()
        device = DeviceORM(
            vendor_id=vendor.id,
            imei="123456789012345",
            health_status="healthy",
            metadata_json={"source": "seed"},
            battery_percent=75.5,
        )
        assert device.imei == "123456789012345"
        assert device.health_status == "healthy"

    def test_invalid_imei_raises(self) -> None:
        vendor = _vendor()
        with pytest.raises(ValueError, match="imei"):
            DeviceORM(
                vendor_id=vendor.id,
                imei="abc",
                health_status="healthy",
                metadata_json={},
            )

    def test_invalid_health_status_raises(self) -> None:
        vendor = _vendor()
        with pytest.raises(ValueError, match="health_status"):
            DeviceORM(
                vendor_id=vendor.id,
                imei="123456789012345",
                health_status="unknown",
                metadata_json={},
            )

    def test_invalid_battery_percent_raises(self) -> None:
        vendor = _vendor()
        with pytest.raises(ValueError, match="battery_percent"):
            DeviceORM(
                vendor_id=vendor.id,
                imei="123456789012345",
                health_status="healthy",
                metadata_json={},
                battery_percent=101,
            )

    def test_metadata_json_mapped_to_metadata_column(self) -> None:
        vendor = _vendor()
        device = DeviceORM(
            vendor_id=vendor.id,
            imei="123456789012345",
            health_status="healthy",
            metadata_json={"build": "1.0"},
            last_seen=datetime.now(UTC),
        )
        cols = set(DeviceORM.__table__.columns.keys())
        assert "metadata" in cols
        assert device.metadata_json["build"] == "1.0"

    def test_vendor_relationship_property_exists(self) -> None:
        assert "vendor" in DeviceORM.__mapper__.relationships
        assert "devices" in VendorORM.__mapper__.relationships
