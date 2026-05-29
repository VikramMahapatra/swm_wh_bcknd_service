from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy.exc import NoResultFound
from swm_db import get_db_session

from admin_api.api_support import RoleContext, get_role_context
from admin_api.main import app


class _DummySession:
    def add(self, *_args, **_kwargs):
        return None

    async def flush(self):
        return None

    async def commit(self):
        return None

    def delete(self, *_args, **_kwargs):
        return None

    async def execute(self, *_args, **_kwargs):
        class _Result:
            def scalar_one(self):
                return 0

            def scalar_one_or_none(self):
                return None

            def mappings(self):
                class _M:
                    def all(self):
                        return []

                    def first(self):
                        return {}

                return _M()

            def first(self):
                return None

            def scalars(self):
                class _S:
                    def all(self):
                        return []

                    def first(self):
                        return None

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
    from admin_api.routers import master_data as md
    from admin_api.routers import realtime as rt

    async def _override_role_context(request: Request) -> RoleContext:
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
    monkeypatch.setattr(md, "VendorRepository", _VendorRepo)
    monkeypatch.setattr(md, "DeviceRepository", _DeviceRepo)
    monkeypatch.setattr(md, "VehicleRepository", _VehicleRepo)
    monkeypatch.setattr(md, "RouteRepository", _RouteRepo)
    monkeypatch.setattr(md, "GeofenceRepository", _GeofenceRepo)
    monkeypatch.setattr(md, "ContractorRepository", _ContractorRepo)
    monkeypatch.setattr(md, "WardRepository", _WardRepo)
    monkeypatch.setattr(md, "DeviceVehicleAssignmentRepository", _DeviceAssignmentRepo)
    monkeypatch.setattr(md, "DeviceVehicleAssignmentService", _DeviceAssignmentService)

    class _RedisStub:
        async def scan(self, *, cursor, match, count):
            return (0, [])

        async def mget_json(self, *keys):
            return []

        async def xrange(self, stream, count):
            return []

    monkeypatch.setattr(rt, "redis_client", _RedisStub())
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


def test_route_write_rejects_invalid_payload(monkeypatch):
    client = _client(monkeypatch)

    create_resp = client.post(
        "/routes",
        json={
            "route_code": "bad code",
            "route_name": "Route X",
            "expected_distance_km": -1,
            "expected_duration_min": -5,
            "start_point": "A",
            "end_point": "B",
            "active": True,
        },
        headers={"x-role": "admin"},
    )
    assert create_resp.status_code == 422

    update_resp = client.put(
        f"/routes/{_BaseRepo._existing_id}",
        json={
            "route_code": "R1",
            "route_name": "",
            "expected_distance_km": 1,
            "expected_duration_min": 10,
            "start_point": "A",
            "end_point": "B",
            "active": True,
        },
        headers={"x-role": "admin"},
    )
    assert update_resp.status_code == 422


def test_vehicle_write_rejects_invalid_payload(monkeypatch):
    client = _client(monkeypatch)

    create_resp = client.post(
        "/vehicles",
        json={
            "vehicle_number": "bad vehicle",
            "registration_number": "bad reg",
            "contractor_id": str(_BaseRepo._existing_id),
            "ward_id": str(_BaseRepo._existing_id),
            "capacity_kg": -1,
            "capacity_cubic_meter": -2,
            "fuel_type": "steam",
            "operational_status": "flying",
            "manufacture_year": 1900,
            "active": True,
            "metadata": {},
        },
        headers={"x-role": "admin"},
    )
    assert create_resp.status_code == 422

    update_resp = client.put(
        f"/vehicles/{_BaseRepo._existing_id}",
        json={
            "vehicle_number": "MH12AB1234",
            "registration_number": "MH12AB1234",
            "contractor_id": str(_BaseRepo._existing_id),
            "ward_id": str(_BaseRepo._existing_id),
            "capacity_kg": 1,
            "capacity_cubic_meter": 1,
            "fuel_type": "diesel",
            "operational_status": "operational",
            "manufacture_year": 2200,
            "active": True,
            "metadata": {},
        },
        headers={"x-role": "admin"},
    )
    assert update_resp.status_code == 422


def test_geofence_write_rejects_invalid_payload(monkeypatch):
    client = _client(monkeypatch)

    create_resp = client.post(
        "/geofences",
        json={
            "geofence_code": "bad code",
            "geofence_name": "Bad Geofence",
            "type": "airport",
            "geometry_type": "line",
            "center_lat": 91,
            "center_lng": 181,
            "radius_meter": 0,
            "active": True,
        },
        headers={"x-role": "admin"},
    )
    assert create_resp.status_code == 422

    update_resp = client.put(
        f"/geofences/{_BaseRepo._existing_id}",
        json={
            "geofence_code": "GF_1",
            "geofence_name": "Geo",
            "type": "zone",
            "geometry_type": "polygon",
            "polygon": {"type": "Point", "coordinates": []},
            "active": True,
        },
        headers={"x-role": "admin"},
    )
    assert update_resp.status_code == 422


def test_vendor_write_rejects_invalid_payload(monkeypatch):
    client = _client(monkeypatch)

    create_resp = client.post(
        "/vendors",
        json={
            "vendor_code": "bad code",
            "vendor_name": "Vendor One",
            "email": "not-an-email",
            "allowed_ips": ["999.999.999.999"],
            "auth_type": "oauth",
            "callback_format": {},
            "active": True,
            "metadata": {},
        },
        headers={"x-role": "admin"},
    )
    assert create_resp.status_code == 422

    update_resp = client.put(
        f"/vendors/{_BaseRepo._existing_id}",
        json={
            "vendor_code": "VEN_1",
            "vendor_name": "Vendor One",
            "email": "vendor@example.com",
            "allowed_ips": ["127.0.0.1"],
            "auth_type": "header",
            "callback_format": {},
            "active": True,
            "metadata": "not-an-object",
        },
        headers={"x-role": "admin"},
    )
    assert update_resp.status_code == 422


def test_device_write_rejects_invalid_payload(monkeypatch):
    client = _client(monkeypatch)

    create_resp = client.post(
        "/devices",
        json={
            "vendor_id": str(_BaseRepo._existing_id),
            "imei": "abc",
            "battery_percent": 101,
            "health_status": "unknown",
            "active": True,
            "metadata": {},
        },
        headers={"x-role": "admin"},
    )
    assert create_resp.status_code == 422

    update_resp = client.put(
        f"/devices/{_BaseRepo._existing_id}",
        json={
            "vendor_id": str(_BaseRepo._existing_id),
            "imei": "12345678901234",
            "battery_percent": -1,
            "health_status": "healthy",
            "active": True,
            "metadata": {},
        },
        headers={"x-role": "admin"},
    )
    assert update_resp.status_code == 422


def test_contractor_write_rejects_invalid_payload(monkeypatch):
    client = _client(monkeypatch)

    create_resp = client.post(
        "/contractors",
        json={
            "contractor_code": "bad code",
            "contractor_name": "Contractor One",
            "sla_details": {},
            "active": True,
        },
        headers={"x-role": "admin"},
    )
    assert create_resp.status_code == 422

    update_resp = client.put(
        f"/contractors/{_BaseRepo._existing_id}",
        json={
            "contractor_code": "CTR_1",
            "contractor_name": "",
            "sla_details": [],
            "active": True,
        },
        headers={"x-role": "admin"},
    )
    assert update_resp.status_code == 422


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


@pytest.mark.parametrize(
    "path,csv_content",
    [
        ("/devices/import", "vendor_id,imei\nnot-a-uuid,12345678901234\n"),
        (
            "/vehicles/import",
            "vehicle_number,registration_number,contractor_id,ward_id,capacity_kg\nTRK001,REG001,00000000-0000-0000-0000-000000000001,not-a-uuid,abc\n",
        ),
        ("/routes/import", "route_code,route_name,start_point,end_point,expected_duration_min\nR1,Route 1,S,E,abc\n"),
        (
            "/geofences/import",
            "geofence_code,geofence_name,type,geometry_type,center_lat\nG1,Geo 1,zone,circle,abc\n",
        ),
        (
            "/device-assignments/import",
            "device_id,vehicle_id,assigned_from\nnot-a-uuid,00000000-0000-0000-0000-000000000001,not-a-datetime\n",
        ),
    ],
)
def test_import_endpoints_reject_malformed_row_values(monkeypatch, path, csv_content):
    client = _client(monkeypatch)
    response = client.post(
        path,
        files={"file": ("bulk.csv", csv_content, "text/csv")},
        headers={"x-role": "ops"},
    )
    assert response.status_code == 400


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


@pytest.mark.parametrize(
    "path",
    [
        "/v1/dashboard/kpis",
        "/v1/vehicles/search",
        "/v1/realtime/trucks",
        "/v1/ingestion/failures",
        "/v1/alerts",
        "/v1/configurations",
        "/v1/operational-categories",
        "/v1/reports/operations/export?export=json",
        "/v1/audit-logs",
    ],
)
def test_epic_endpoints_smoke(monkeypatch, path):
    client = _client(monkeypatch)
    response = client.get(path, headers={"x-role": "viewer"})
    assert response.status_code == 200
