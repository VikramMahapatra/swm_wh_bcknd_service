from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import NoResultFound

from admin_api.main import app, get_db_session


class _DummySession:
    async def execute(self, *_args, **_kwargs):
        class _Result:
            def scalar_one(self):
                return 0

            def scalars(self):
                class _S:
                    def all(self):
                        return []

                return _S()

        return _Result()


async def _override_db_session():
    yield _DummySession()


class _Obj:
    def __init__(self, data):
        self.id = data.get("id", uuid4())
        self.created_at = data.get("created_at", datetime.now(UTC))
        for k, v in data.items():
            setattr(self, k, v)

    @property
    def __table__(self):
        cols = [type("_C", (), {"name": k}) for k in self.__dict__.keys()]
        return type("_T", (), {"columns": cols})


class _BaseRepo:
    _existing_id = UUID("00000000-0000-0000-0000-000000000001")

    def __init__(self, _session):
        pass

    async def create(self, **kwargs):
        return _Obj(kwargs)

    async def bulk_create(self, rows):
        return [_Obj(row) for row in rows]

    async def get_by_id(self, entity_id):
        if entity_id != self._existing_id:
            return None
        return _Obj({"id": entity_id, "name": "existing"})

    async def update(self, entity_id, **kwargs):
        if entity_id != self._existing_id:
            raise NoResultFound()
        return _Obj({"id": entity_id, **kwargs})

    async def delete(self, entity_id):
        if entity_id != self._existing_id:
            raise NoResultFound()


class _VendorRepo(_BaseRepo):
    pass


class _DeviceRepo(_BaseRepo):
    pass


class _VehicleRepo(_BaseRepo):
    pass


class _RouteRepo(_BaseRepo):
    pass


class _GeofenceRepo(_BaseRepo):
    pass


class _ContractorRepo(_BaseRepo):
    pass


class _WardRepo(_BaseRepo):
    pass


class _DeviceAssignmentRepo:
    _existing_id = UUID("00000000-0000-0000-0000-000000000001")

    def __init__(self, _session):
        pass

    async def get_active_by_device(self, device_id):
        if device_id != self._existing_id:
            return None
        return _Obj(
            {
                "device_id": device_id,
                "vehicle_id": UUID("00000000-0000-0000-0000-000000000002"),
                "active": True,
                "remarks": "active",
            }
        )


class _DeviceAssignmentService:
    def __init__(self, _repo):
        pass

    async def assign(self, payload):
        return _Obj(
            {
                "device_id": payload.device_id,
                "vehicle_id": payload.vehicle_id,
                "assigned_from": payload.assigned_from or datetime.now(UTC),
                "assigned_to": None,
                "active": True,
                "remarks": payload.remarks,
            }
        )

    async def unassign_device(self, device_id, *, assigned_to=None, remarks=None):
        if device_id != UUID("00000000-0000-0000-0000-000000000001"):
            return None
        return _Obj(
            {
                "device_id": device_id,
                "vehicle_id": UUID("00000000-0000-0000-0000-000000000002"),
                "assigned_to": assigned_to or datetime.now(UTC),
                "active": False,
                "remarks": remarks,
            }
        )


def _client(monkeypatch):
    from admin_api import main as m

    app.dependency_overrides[get_db_session] = _override_db_session
    monkeypatch.setattr(m, "VendorRepository", _VendorRepo)
    monkeypatch.setattr(m, "DeviceRepository", _DeviceRepo)
    monkeypatch.setattr(m, "VehicleRepository", _VehicleRepo)
    monkeypatch.setattr(m, "RouteRepository", _RouteRepo)
    monkeypatch.setattr(m, "GeofenceRepository", _GeofenceRepo)
    monkeypatch.setattr(m, "ContractorRepository", _ContractorRepo)
    monkeypatch.setattr(m, "WardRepository", _WardRepo)
    monkeypatch.setattr(m, "DeviceVehicleAssignmentRepository", _DeviceAssignmentRepo)
    monkeypatch.setattr(m, "DeviceVehicleAssignmentService", _DeviceAssignmentService)
    return TestClient(app)


def test_healthz(monkeypatch):
    client = _client(monkeypatch)
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["service"] == "admin-api"


@pytest.mark.parametrize(
    "path",
    [
        "/vendors",
        "/devices",
        "/vehicles",
        "/routes",
        "/geofences",
        "/contractors",
        "/wards",
        "/device-assignments",
    ],
)
def test_list_endpoints(monkeypatch, path):
    client = _client(monkeypatch)
    r = client.get(path, headers={"x-role": "viewer"})
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body


def test_list_vendors_pagination_search_sort_filter(monkeypatch):
    client = _client(monkeypatch)
    r = client.get(
        "/vendors",
        params={
            "page": 1,
            "page_size": 10,
            "q": "abc",
            "active": True,
            "auth_type": "header",
            "sort_by": "vendor_name",
            "sort_order": "asc",
        },
        headers={"x-role": "viewer"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 1
    assert body["page_size"] == 10


def test_create_vendor_and_rbac(monkeypatch):
    client = _client(monkeypatch)
    payload = {
        "vendor_code": "VEN-1",
        "vendor_name": "Vendor One",
        "allowed_ips": [],
        "auth_type": "header",
        "callback_format": {},
        "active": True,
        "metadata": {},
    }

    denied = client.post("/vendors", json=payload, headers={"x-role": "viewer"})
    assert denied.status_code == 403

    ok = client.post("/vendors", json=payload, headers={"x-role": "admin"})
    assert ok.status_code == 200
    assert UUID(ok.json()["id"])


def test_vendor_read_update_delete(monkeypatch):
    client = _client(monkeypatch)
    existing = "00000000-0000-0000-0000-000000000001"
    missing = "00000000-0000-0000-0000-000000000099"

    get_ok = client.get(f"/vendors/{existing}", headers={"x-role": "viewer"})
    assert get_ok.status_code == 200

    get_404 = client.get(f"/vendors/{missing}", headers={"x-role": "viewer"})
    assert get_404.status_code == 404

    update_payload = {
        "vendor_code": "VEN-1",
        "vendor_name": "Vendor Updated",
        "allowed_ips": [],
        "auth_type": "header",
        "callback_format": {},
        "active": True,
        "metadata": {},
    }
    put_ok = client.put(f"/vendors/{existing}", json=update_payload, headers={"x-role": "ops"})
    assert put_ok.status_code == 200

    delete_ok = client.delete(f"/vendors/{existing}", headers={"x-role": "admin"})
    assert delete_ok.status_code == 200
    assert delete_ok.json()["message"] == "deleted"


def test_bulk_import_vendors(monkeypatch):
    client = _client(monkeypatch)
    csv_content = "vendor_code,vendor_name\nVEN-1,Vendor One\nVEN-2,Vendor Two\n"
    r = client.post(
        "/vendors/import",
        files={"file": ("vendors.csv", csv_content, "text/csv")},
        headers={"x-role": "ops"},
    )
    assert r.status_code == 200
    assert r.json()["created"] == 2


def test_bulk_import_validation(monkeypatch):
    client = _client(monkeypatch)
    bad_csv = "foo,bar\n1,2\n"
    r = client.post(
        "/vendors/import",
        files={"file": ("vendors.csv", bad_csv, "text/csv")},
        headers={"x-role": "ops"},
    )
    assert r.status_code == 400


@pytest.mark.parametrize(
    "path,csv_content",
    [
        ("/routes/import", "route_code,route_name,start_point,end_point\nR1,Route 1,S,E\n"),
        (
            "/geofences/import",
            "geofence_code,geofence_name,type,geometry_type\nG1,Geo 1,ward,circle\n",
        ),
        ("/contractors/import", "contractor_code,contractor_name\nC1,Contractor 1\n"),
        ("/wards/import", "ward_code,ward_name,zone_name\nW1,Ward 1,Zone A\n"),
    ],
)
def test_other_bulk_import_endpoints(monkeypatch, path, csv_content):
    client = _client(monkeypatch)
    r = client.post(
        path,
        files={"file": ("bulk.csv", csv_content, "text/csv")},
        headers={"x-role": "ops"},
    )
    assert r.status_code == 200
    assert r.json()["created"] == 1


def test_device_assignment_endpoint(monkeypatch):
    client = _client(monkeypatch)
    payload = {
        "device_id": "00000000-0000-0000-0000-000000000001",
        "vehicle_id": str(uuid4()),
        "remarks": "initial map",
    }
    r = client.post("/device-assignments", json=payload, headers={"x-role": "ops"})
    assert r.status_code == 200
    body = r.json()
    assert body["active"] is True
    assert body["remarks"] == "initial map"

    get_active = client.get(
        "/device-assignments/00000000-0000-0000-0000-000000000001",
        headers={"x-role": "viewer"},
    )
    assert get_active.status_code == 200

    reassign = client.put(
        "/device-assignments/00000000-0000-0000-0000-000000000001",
        params={"vehicle_id": str(uuid4()), "remarks": "moved"},
        headers={"x-role": "ops"},
    )
    assert reassign.status_code == 200

    unassign = client.delete(
        "/device-assignments/00000000-0000-0000-0000-000000000001",
        headers={"x-role": "ops"},
    )
    assert unassign.status_code == 200

    missing = client.delete(
        "/device-assignments/00000000-0000-0000-0000-000000000099",
        headers={"x-role": "ops"},
    )
    assert missing.status_code == 404
