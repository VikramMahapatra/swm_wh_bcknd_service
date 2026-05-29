
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
    ("/pickup-points", {}, list, ["id", "name", "ward_id", "route_id", "lat", "lng", "type", "active"]),
    ("/pickup-points", {"ward_id": "00000000-0000-0000-0000-000000000000"}, list, ["id", "name", "ward_id", "route_id", "lat", "lng", "type", "active"]),
    ("/pickup-points", {"route_id": "00000000-0000-0000-0000-000000000000"}, list, ["id", "name", "ward_id", "route_id", "lat", "lng", "type", "active"]),
    ("/routes/00000000-0000-0000-0000-000000000000/pickup-points", {}, list, ["id", "name", "ward_id", "route_id", "lat", "lng", "type", "active"]),
])
def test_pickup_points_endpoints(endpoint, params, expected_type, expected_keys):
    resp = client.get(endpoint, params=params, headers={"x-role": "admin"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, expected_type)
    if data:
        for key in expected_keys:
            assert key in data[0]
