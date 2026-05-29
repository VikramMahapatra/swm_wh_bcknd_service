
# Patch require_roles BEFORE importing app so endpoints use test-friendly dependency
import sys
import types
from fastapi import Depends
from admin_api.api_support import get_role_context, RoleContext

def _require_roles_patch(*_roles):
    def _dep():
        return RoleContext(
            subject="test-user",
            role="admin",
            roles=["admin"],
            permissions=["*"],
            auth_type="test",
        )
    return _dep

import admin_api.api_support as api_support_mod
api_support_mod.require_roles = _require_roles_patch

from fastapi.testclient import TestClient
from admin_api.main import app
from swm_db import get_db_session
import pytest

async def _override_db_session():
    class DummySession:
        async def execute(self, *_args, **_kwargs):
            class _Result:
                def scalar_one(self): return 0
                def scalar_one_or_none(self): return None
                def mappings(self):
                    class _M:
                        def all(self): return []
                        def first(self): return {}
                    return _M()
                def first(self): return None
                def scalars(self):
                    class _S:
                        def all(self): return []
                        def first(self): return None
                    return _S()
                def fetchall(self): return []
                def all(self): return []
            return _Result()
        async def commit(self): return None
        async def flush(self): return None
        async def refresh(self, _): return None
        def add(self, *_args, **_kwargs): return None
        def delete(self, *_args, **_kwargs): return None
    yield DummySession()

async def _override_role_context(request):
    requested_role = (request.headers.get("x-role") or "admin").strip().lower()
    return RoleContext(
        subject="test-user",
        role=requested_role,
        roles=[requested_role],
        permissions=["*"],
        auth_type="test",
    )

app.dependency_overrides[get_db_session] = _override_db_session
app.dependency_overrides[get_role_context] = _override_role_context

client = TestClient(app)

@pytest.mark.parametrize("endpoint,params,expected_type,expected_keys", [
    ("/drivers", {}, list, ["id", "name", "phone", "license_number", "license_expiry", "vendor_id", "assigned_truck_id", "status", "active"]),
    ("/drivers/00000000-0000-0000-0000-000000000000", {}, dict, ["id", "name", "phone", "license_number", "license_expiry", "vendor_id", "assigned_truck_id", "status", "active"]),
])
def test_drivers_endpoints(endpoint, params, expected_type, expected_keys):
    resp = client.get(endpoint, params=params, headers={"x-role": "admin"})
    assert resp.status_code in (200, 404)
    data = resp.json()
    if resp.status_code == 200:
        assert isinstance(data, expected_type)
        if isinstance(data, list) and data:
            for key in expected_keys:
                assert key in data[0]
        elif isinstance(data, dict):
            for key in expected_keys:
                assert key in data
    else:
        assert data["detail"] == "driver not found"
