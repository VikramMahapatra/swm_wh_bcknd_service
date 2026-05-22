from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from swm_db import get_db_session

from admin_api.main import app


class _DummySession:
    def add(self, *_args, **_kwargs):
        return None

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def refresh(self, _obj):
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


def _path_with_params(path: str) -> str:
    return (
        path.replace("{vendor_id}", "00000000-0000-0000-0000-000000000001")
        .replace("{device_id}", "00000000-0000-0000-0000-000000000001")
        .replace("{vehicle_id}", "00000000-0000-0000-0000-000000000001")
        .replace("{route_id}", "00000000-0000-0000-0000-000000000001")
        .replace("{geofence_id}", "00000000-0000-0000-0000-000000000001")
        .replace("{contractor_id}", "00000000-0000-0000-0000-000000000001")
        .replace("{ward_id}", "00000000-0000-0000-0000-000000000001")
        .replace("{config_id}", "00000000-0000-0000-0000-000000000001")
        .replace("{category_id}", "00000000-0000-0000-0000-000000000001")
        .replace("{alert_id}", "00000000-0000-0000-0000-000000000001")
    )


def _payload_for(path: str) -> dict:
    shared_uuid = "00000000-0000-0000-0000-000000000001"
    if path == "/vendors":
        return {
            "vendor_code": "VEN-T",
            "vendor_name": "Vendor Test",
            "allowed_ips": [],
            "auth_type": "header",
            "callback_format": {},
            "active": True,
            "metadata": {},
        }
    if path == "/devices":
        return {
            "vendor_id": shared_uuid,
            "imei": "123456789012345",
            "health_status": "healthy",
            "active": True,
            "metadata": {},
        }
    if path == "/vehicles":
        return {
            "vehicle_number": "MH12AB1234",
            "registration_number": "MH12AB1234",
            "contractor_id": shared_uuid,
            "ward_id": shared_uuid,
            "fuel_type": "diesel",
            "operational_status": "operational",
            "active": True,
            "metadata": {},
        }
    if path == "/routes":
        return {
            "route_code": "R-1",
            "route_name": "Route One",
            "expected_distance_km": 5.0,
            "expected_duration_min": 30,
            "start_point": "A",
            "end_point": "B",
            "active": True,
        }
    if path == "/geofences":
        return {
            "geofence_code": "G-1",
            "geofence_name": "Geo One",
            "type": "zone",
            "geometry_type": "circle",
            "center_lat": 18.5,
            "center_lng": 73.8,
            "radius_meter": 100.0,
            "active": True,
        }
    if path == "/contractors":
        return {
            "contractor_code": "C-1",
            "contractor_name": "Contractor One",
            "sla_details": {},
            "active": True,
        }
    if path == "/wards":
        return {
            "ward_code": "W-1",
            "ward_name": "Ward One",
            "zone_name": "Zone A",
            "active": True,
        }
    if path == "/device-assignments":
        return {
            "device_id": shared_uuid,
            "vehicle_id": str(uuid4()),
            "assigned_from": datetime.now(UTC).isoformat(),
            "active": True,
            "remarks": "test",
        }
    if path == "/v1/alerts":
        return {
            "alert_type": "overspeed",
            "category": "safety",
            "title": "Overspeed",
            "severity": "medium",
            "vehicle_id": "MH12AB1234",
            "metadata": {},
        }
    if path == "/v1/configurations":
        return {
            "config_key": "retention.days",
            "config_type": "vendor_config",
            "value": {"days": 30},
            "active": True,
        }
    if path == "/v1/operational-categories":
        return {
            "category_code": "OPS-1",
            "category_name": "Operations",
            "active": True,
        }
    return {}


def _call(client: TestClient, method: str, path: str):
    headers = {"x-role": "admin"}
    payload = _payload_for(path)
    if method == "GET":
        return client.get(path, headers=headers)
    if method == "POST":
        return client.post(path, json=payload, headers=headers)
    if method == "PUT":
        return client.put(path, json=payload, headers=headers)
    if method == "DELETE":
        return client.delete(path, headers=headers)
    raise AssertionError(f"unsupported method {method}")


def test_all_admin_api_http_routes_smoke(monkeypatch):
    from admin_api.routers import realtime as rt

    class _RedisStub:
        async def scan(self, *, cursor, match, count):
            return (0, [])

        async def mget_json(self, *keys):
            return []

        async def xrange(self, stream, count):
            return []

    app.dependency_overrides[get_db_session] = _override_db_session
    monkeypatch.setattr(rt, "redis_client", _RedisStub())

    allowed = {200, 201, 202, 204, 400, 401, 403, 404, 405, 409, 422}
    failures: list[str] = []

    with TestClient(app) as client:
        routes = [r for r in app.routes if isinstance(r, APIRoute)]
        for route in routes:
            path = _path_with_params(route.path)
            for method in sorted(route.methods):
                if method not in {"GET", "POST", "PUT", "DELETE"}:
                    continue
                response = _call(client, method, path)
                if response.status_code not in allowed:
                    failures.append(f"{method} {path} -> {response.status_code} {response.text[:180]}")

    app.dependency_overrides.clear()

    assert not failures, "Unexpected status codes:\n" + "\n".join(failures)
