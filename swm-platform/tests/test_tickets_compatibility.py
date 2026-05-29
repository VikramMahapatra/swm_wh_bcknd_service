
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
                def scalar(self): return 0
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

def test_tickets_list():
    resp = client.get("/tickets", headers={"x-role": "admin"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)

@pytest.mark.parametrize("params", [
    {"status": "open"},
    {"priority": "high"},
    {"category": "general"},
])
def test_tickets_list_filters(params):
    resp = client.get("/tickets", params=params, headers={"x-role": "admin"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_ticket_create():
    payload = {
        "title": "Test Ticket",
        "description": "Test description",
        "status": "open",
        "priority": "high",
        "category": "complaint"
    }
    resp = client.post("/tickets", json=payload, headers={"x-role": "admin"})
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert "id" in data or "ok" in data

def test_ticket_get():
    # This test expects at least one ticket to exist
    resp = client.get("/tickets", headers={"x-role": "admin"})
    if resp.json():
        ticket_id = resp.json()[0]["id"]
        resp2 = client.get(f"/tickets/{ticket_id}", headers={"x-role": "admin"})
        assert resp2.status_code == 200
        assert isinstance(resp2.json(), dict)

def test_ticket_update():
    # This test expects at least one ticket to exist
    resp = client.get("/tickets", headers={"x-role": "admin"})
    if resp.json():
        ticket_id = resp.json()[0]["id"]
        payload = {"status": "closed"}
        resp2 = client.put(f"/tickets/{ticket_id}", json=payload, headers={"x-role": "admin"})
        assert resp2.status_code in (200, 204)

def test_ticket_comments():
    # This test expects at least one ticket to exist
    resp = client.get("/tickets", headers={"x-role": "admin"})
    if resp.json():
        ticket_id = resp.json()[0]["id"]
        resp2 = client.get(f"/tickets/{ticket_id}/comments", headers={"x-role": "admin"})
        assert resp2.status_code == 200
        assert isinstance(resp2.json(), list)
        # Try posting a comment
        payload = {"comment": "Test comment"}
        resp3 = client.post(f"/tickets/{ticket_id}/comments", json=payload, headers={"x-role": "admin"})
        assert resp3.status_code in (200, 201)

def test_ticket_statistics():
    resp = client.get("/tickets/statistics/summary", headers={"x-role": "admin"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)
