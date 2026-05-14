from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from swm_db.models import VendorORM
from swm_db.vendor_repository import VendorRepository


@dataclass(slots=True)
class VendorCreateInput:
    vendor_code: str
    vendor_name: str
    contact_person: str | None = None
    email: str | None = None
    phone: str | None = None
    webhook_secret: str | None = None
    signature_key: str | None = None
    allowed_ips: list[str] | None = None
    auth_type: str = "header"
    callback_format: dict[str, Any] | None = None
    active: bool = True
    metadata: dict[str, Any] | None = None


@dataclass(slots=True)
class VendorUpdateInput:
    vendor_name: str | None = None
    contact_person: str | None = None
    email: str | None = None
    phone: str | None = None
    webhook_secret: str | None = None
    signature_key: str | None = None
    allowed_ips: list[str] | None = None
    auth_type: str | None = None
    callback_format: dict[str, Any] | None = None
    active: bool | None = None
    metadata: dict[str, Any] | None = None


class VendorService:
    """CRUD service layer for Vendor master."""

    def __init__(self, repository: VendorRepository) -> None:
        self._repository = repository

    async def create_vendor(self, payload: VendorCreateInput) -> VendorORM:
        return await self._repository.create(
            vendor_code=payload.vendor_code,
            vendor_name=payload.vendor_name,
            contact_person=payload.contact_person,
            email=payload.email,
            phone=payload.phone,
            webhook_secret=payload.webhook_secret,
            signature_key=payload.signature_key,
            allowed_ips=payload.allowed_ips or [],
            auth_type=payload.auth_type,
            callback_format=payload.callback_format or {},
            active=payload.active,
            metadata_json=payload.metadata or {},
        )

    async def get_vendor(self, vendor_id: uuid.UUID) -> VendorORM | None:
        return await self._repository.get_by_id(vendor_id)

    async def get_vendor_by_code(self, vendor_code: str) -> VendorORM | None:
        return await self._repository.get_by_code(vendor_code)

    async def list_vendors(self, *, active_only: bool | None = None) -> list[VendorORM]:
        return await self._repository.list(active_only=active_only)

    async def update_vendor(self, vendor_id: uuid.UUID, payload: VendorUpdateInput) -> VendorORM:
        updates: dict[str, Any] = {}
        if payload.vendor_name is not None:
            updates["vendor_name"] = payload.vendor_name
        if payload.contact_person is not None:
            updates["contact_person"] = payload.contact_person
        if payload.email is not None:
            updates["email"] = payload.email
        if payload.phone is not None:
            updates["phone"] = payload.phone
        if payload.webhook_secret is not None:
            updates["webhook_secret"] = payload.webhook_secret
        if payload.signature_key is not None:
            updates["signature_key"] = payload.signature_key
        if payload.allowed_ips is not None:
            updates["allowed_ips"] = payload.allowed_ips
        if payload.auth_type is not None:
            updates["auth_type"] = payload.auth_type
        if payload.callback_format is not None:
            updates["callback_format"] = payload.callback_format
        if payload.active is not None:
            updates["active"] = payload.active
        if payload.metadata is not None:
            updates["metadata_json"] = payload.metadata

        return await self._repository.update(vendor_id, **updates)

    async def delete_vendor(self, vendor_id: uuid.UUID) -> None:
        await self._repository.delete(vendor_id)

    async def activate_vendor(self, vendor_id: uuid.UUID) -> VendorORM:
        return await self._repository.update(vendor_id, active=True)

    async def deactivate_vendor(self, vendor_id: uuid.UUID) -> VendorORM:
        return await self._repository.update(vendor_id, active=False)
