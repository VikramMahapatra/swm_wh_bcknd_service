from __future__ import annotations

import uuid

import pytest

from swm_db.models import VendorORM


class TestVendorModelValidation:
    def test_vendor_code_is_upper_normalized(self) -> None:
        vendor = VendorORM(
            vendor_code="abc_01",
            vendor_name="ABC Vendor",
            allowed_ips=["127.0.0.1"],
            auth_type="header",
            callback_format={},
            metadata_json={},
        )
        assert vendor.vendor_code == "ABC_01"

    def test_invalid_vendor_code_raises(self) -> None:
        with pytest.raises(ValueError, match="vendor_code"):
            VendorORM(
                vendor_code="ab",
                vendor_name="Bad Vendor",
                allowed_ips=["127.0.0.1"],
                auth_type="header",
                callback_format={},
                metadata_json={},
            )

    def test_invalid_email_raises(self) -> None:
        with pytest.raises(ValueError, match="email"):
            VendorORM(
                vendor_code="VEN_100",
                vendor_name="Bad Email",
                email="not-an-email",
                allowed_ips=["127.0.0.1"],
                auth_type="header",
                callback_format={},
                metadata_json={},
            )

    def test_invalid_auth_type_raises(self) -> None:
        with pytest.raises(ValueError, match="auth_type"):
            VendorORM(
                vendor_code="VEN_101",
                vendor_name="Bad Auth",
                allowed_ips=["127.0.0.1"],
                auth_type="oauth",
                callback_format={},
                metadata_json={},
            )

    def test_invalid_allowed_ip_raises(self) -> None:
        with pytest.raises(ValueError):
            VendorORM(
                vendor_code="VEN_102",
                vendor_name="Bad IP",
                allowed_ips=["999.1.1.1"],
                auth_type="ip",
                callback_format={},
                metadata_json={},
            )

    def test_metadata_json_maps_to_metadata_column(self) -> None:
        vendor = VendorORM(
            id=uuid.uuid4(),
            vendor_code="VEN_103",
            vendor_name="Meta Vendor",
            allowed_ips=["10.0.0.1"],
            auth_type="signature",
            callback_format={"v": 1},
            metadata_json={"source": "seed"},
        )
        cols = set(VendorORM.__table__.columns.keys())
        assert "metadata" in cols
        assert vendor.metadata_json["source"] == "seed"
