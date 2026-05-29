from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from swm_db import DriverORM, GtcCheckpointORM, PickupPointORM, get_db_session

from admin_api.api_support import RoleContext, get_role_context
from admin_api.main import app


class _FakeResult:
    def __init__(self, *, rows=None):
        self._rows = rows or []

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)

    def first(self):
        if self._rows:
            return self._rows[0]
        return None


class _MasterDataSession:
    def __init__(self):
        self.drivers: list[DriverORM] = []
        self.gtc_checkpoints: list[GtcCheckpointORM] = []
        self.pickup_points: list[PickupPointORM] = []
        self._next_gtc_id = 1

    def add(self, obj):
        now = datetime.now(UTC)
        if isinstance(obj, DriverORM):
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()
            if getattr(obj, "created_at", None) is None:
                obj.created_at = now
            obj.updated_at = now
            self.drivers.append(obj)
            return

        if isinstance(obj, PickupPointORM):
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()
            if getattr(obj, "created_at", None) is None:
                obj.created_at = now
            obj.updated_at = now
            self.pickup_points.append(obj)
            return

        if isinstance(obj, GtcCheckpointORM):
            if getattr(obj, "id", None) is None:
                obj.id = self._next_gtc_id
                self._next_gtc_id += 1
            if getattr(obj, "created_at", None) is None:
                obj.created_at = now
            self.gtc_checkpoints.append(obj)

    async def commit(self):
        return None

    async def refresh(self, _obj):
        return None

    async def rollback(self):
        return None

    async def delete(self, obj):
        if isinstance(obj, DriverORM):
            self.drivers = [row for row in self.drivers if row.id != obj.id]
            return None
        if isinstance(obj, PickupPointORM):
            self.pickup_points = [row for row in self.pickup_points if row.id != obj.id]
        return None

    async def execute(self, statement):
        stmt_text = str(statement)
        criteria = list(getattr(statement, "_where_criteria", []))

        if "FROM drivers" in stmt_text:
            rows = list(self.drivers)
            for criterion in criteria:
                left = getattr(criterion, "left", None)
                right = getattr(criterion, "right", None)
                if getattr(left, "key", None) == "id":
                    rows = [row for row in rows if row.id == getattr(right, "value", None)]
            rows.sort(key=lambda row: str(getattr(row, "name", "")))
            return _FakeResult(rows=rows)

        if "FROM pickup_points" in stmt_text:
            rows = list(self.pickup_points)
            for criterion in criteria:
                left = getattr(criterion, "left", None)
                right = getattr(criterion, "right", None)
                key = getattr(left, "key", None)
                if key == "id":
                    rows = [row for row in rows if row.id == getattr(right, "value", None)]
                if key == "ward_id":
                    rows = [row for row in rows if row.ward_id == getattr(right, "value", None)]
                if key == "route_id":
                    rows = [row for row in rows if row.route_id == getattr(right, "value", None)]
            rows.sort(key=lambda row: str(getattr(row, "pickup_name", "")))
            return _FakeResult(rows=rows)

        if "FROM gtc_checkpoints" in stmt_text:
            rows = list(self.gtc_checkpoints)
            for criterion in criteria:
                left = getattr(criterion, "left", None)
                right = getattr(criterion, "right", None)
                operator = getattr(criterion, "operator", None)
                key = getattr(left, "key", None)
                value = getattr(right, "value", None)

                if key == "truck_id" and value is not None:
                    rows = [row for row in rows if row.truck_id == value]
                    continue

                if key == "arrived_at" and value is not None:
                    operator_name = getattr(operator, "__name__", "")
                    if operator_name == "ge":
                        rows = [row for row in rows if row.arrived_at >= value]
                    elif operator_name == "le":
                        rows = [row for row in rows if row.arrived_at <= value]
                    elif operator_name == "lt":
                        rows = [row for row in rows if row.arrived_at < value]

            rows.sort(key=lambda row: (row.arrived_at, row.id), reverse=True)
            return _FakeResult(rows=rows)

        return _FakeResult(rows=[])


def _build_client(fake_session: _MasterDataSession) -> TestClient:
    async def _override_db_session():
        yield fake_session

    async def _override_role_context() -> RoleContext:
        return RoleContext(
            subject="test-user",
            role="admin",
            roles=["admin"],
            permissions=["*"],
            auth_type="test",
        )

    app.dependency_overrides[get_db_session] = _override_db_session
    app.dependency_overrides[get_role_context] = _override_role_context
    return TestClient(app)


def test_driver_write_rejects_malformed_related_uuids():
    fake_session = _MasterDataSession()
    driver = DriverORM(name="Seed Driver", active=True, metadata_json={})
    fake_session.add(driver)

    with _build_client(fake_session) as client:
        create_resp = client.post(
            "/drivers",
            json={
                "name": "Bad Driver",
                "vendorId": "not-a-uuid",
                "assignedTruckId": "also-not-a-uuid",
            },
        )
        assert create_resp.status_code == 422

        update_resp = client.put(
            f"/drivers/{driver.id}",
            json={"vendorId": "not-a-uuid", "assignedTruckId": "also-not-a-uuid"},
        )
        assert update_resp.status_code == 422

    app.dependency_overrides.clear()


def test_pickup_point_write_rejects_malformed_related_uuids():
    fake_session = _MasterDataSession()
    pickup = PickupPointORM(
        pickup_code="P-001",
        pickup_name="Seed Pickup",
        active=True,
        metadata_json={},
    )
    fake_session.add(pickup)

    with _build_client(fake_session) as client:
        create_resp = client.post(
            "/pickup-points",
            json={
                "pickupCode": "P-002",
                "pickupName": "Bad Pickup",
                "wardId": "not-a-uuid",
                "routeId": "also-not-a-uuid",
            },
        )
        assert create_resp.status_code == 422

        update_resp = client.put(
            f"/pickup-points/{pickup.id}",
            json={"wardId": "not-a-uuid", "routeId": "also-not-a-uuid"},
        )
        assert update_resp.status_code == 422

    app.dependency_overrides.clear()


def test_driver_crud_flow():
    fake_session = _MasterDataSession()

    with _build_client(fake_session) as client:
        create_resp = client.post(
            "/drivers",
            json={
                "name": "Driver One",
                "phone": "9999999999",
                "licenseNumber": "LIC-001",
                "licenseExpiry": "2030-01-01",
                "status": "active",
                "email": "driver@example.com",
            },
        )
        assert create_resp.status_code == 200
        created = create_resp.json()
        driver_id = created["id"]
        assert created["name"] == "Driver One"
        assert created["licenseNumber"] == "LIC-001"

        list_resp = client.get("/drivers")
        assert list_resp.status_code == 200
        listed = list_resp.json()
        assert len(listed) == 1
        assert listed[0]["id"] == driver_id

        get_resp = client.get(f"/drivers/{driver_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["email"] == "driver@example.com"

        update_resp = client.put(
            f"/drivers/{driver_id}",
            json={
                "name": "Driver Updated",
                "phone": "8888888888",
                "licenseExpiry": "",
                "status": "inactive",
                "address": "Test Address",
            },
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["name"] == "Driver Updated"
        assert updated["phone"] == "8888888888"
        assert updated["licenseExpiry"] is None
        assert updated["status"] == "inactive"
        assert updated["address"] == "Test Address"

        delete_resp = client.delete(f"/drivers/{driver_id}")
        assert delete_resp.status_code == 200
        assert delete_resp.json()["ok"] is True

        missing_resp = client.get(f"/drivers/{driver_id}")
        assert missing_resp.status_code == 404

    app.dependency_overrides.clear()


def test_pickup_point_crud_and_filters():
    fake_session = _MasterDataSession()
    ward_id = uuid4()
    route_id = uuid4()
    other_ward_id = uuid4()

    with _build_client(fake_session) as client:
        create_resp = client.post(
            "/pickup-points",
            json={
                "pickupCode": "P-100",
                "pickupName": "Alpha Pickup",
                "wardId": str(ward_id),
                "routeId": str(route_id),
                "lat": 18.52,
                "lng": 73.85,
                "category": "mixed",
                "status": "active",
                "expectedPickupTime": "08:00",
                "address": "Street 1",
            },
        )
        assert create_resp.status_code == 200
        created = create_resp.json()
        pickup_id = created["id"]
        assert created["pickupCode"] == "P-100"
        assert created["wardId"] == str(ward_id)
        assert created["routeId"] == str(route_id)

        second_resp = client.post(
            "/pickup-points",
            json={
                "pickupCode": "P-101",
                "pickupName": "Beta Pickup",
                "wardId": str(other_ward_id),
                "status": "inactive",
            },
        )
        assert second_resp.status_code == 200

        list_resp = client.get("/pickup-points")
        assert list_resp.status_code == 200
        assert [item["pickupCode"] for item in list_resp.json()] == ["P-100", "P-101"]

        ward_filtered = client.get("/pickup-points", params={"ward_id": str(ward_id)})
        assert ward_filtered.status_code == 200
        ward_items = ward_filtered.json()
        assert len(ward_items) == 1
        assert ward_items[0]["id"] == pickup_id

        route_filtered = client.get("/pickup-points", params={"route_id": str(route_id)})
        assert route_filtered.status_code == 200
        route_items = route_filtered.json()
        assert len(route_items) == 1
        assert route_items[0]["pickupCode"] == "P-100"

        update_resp = client.put(
            f"/pickup-points/{pickup_id}",
            json={
                "pickupName": "Alpha Updated",
                "status": "inactive",
                "expectedPickupTime": "09:00",
                "address": "Street 2",
            },
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["pickupName"] == "Alpha Updated"
        assert updated["status"] == "inactive"
        assert updated["expectedPickupTime"] == "09:00"
        assert updated["address"] == "Street 2"

        delete_resp = client.delete(f"/pickup-points/{pickup_id}")
        assert delete_resp.status_code == 200
        assert delete_resp.json()["ok"] is True

        filtered_after_delete = client.get("/pickup-points", params={"route_id": str(route_id)})
        assert filtered_after_delete.status_code == 200
        assert filtered_after_delete.json() == []

    app.dependency_overrides.clear()


def test_gtc_checkpoint_create_and_filters():
    fake_session = _MasterDataSession()

    fake_session.add(
        GtcCheckpointORM(
            truck_id="TRK-1",
            arrived_at=datetime.fromisoformat("2026-05-20T06:30:00+00:00"),
            is_dry=True,
            is_wet=False,
            is_metal=False,
            is_plastic=False,
            is_sanitary=False,
            truck_cleanliness_score=4.0,
            gtc_cleanliness_score=4.5,
            remarks="older",
        )
    )
    fake_session.add(
        GtcCheckpointORM(
            truck_id="TRK-2",
            arrived_at=datetime.fromisoformat("2026-05-21T08:00:00+00:00"),
            is_dry=False,
            is_wet=True,
            is_metal=False,
            is_plastic=True,
            is_sanitary=False,
            truck_cleanliness_score=3.0,
            gtc_cleanliness_score=3.5,
            remarks="same-day other truck",
        )
    )

def test_driver_list_fallback_from_vehicle_metadata():
    """
    When the drivers table is empty, /drivers should return drivers derived from vehicle metadata.
    """
    from swm_db import VehicleORM, ContractorORM, WardORM
    fake_session = _MasterDataSession()

    # Add a contractor and ward for foreign keys
    contractor_id = uuid4()
    ward_id = uuid4()
    vehicle1_id = uuid4()
    vehicle2_id = uuid4()

    # Patch the fake session to support vehicles
    fake_session.vehicles = []
    async def fake_execute(statement):
        stmt_text = str(statement)
        if "FROM vehicles" in stmt_text:
            class _FakeVehicleResult:
                def __init__(self, rows):
                    self._rows = rows
                def scalars(self):
                    return self
                def all(self):
                    return list(self._rows)
            return _FakeVehicleResult(fake_session.vehicles)
        # Fallback to original (sync) for other tables
        result = fake_session.__class__.execute(fake_session, statement)
        if hasattr(result, "__await__"):
            # If it's a coroutine, await it and return the result
            return await result
        # Wrap sync result in awaitable
        class _Awaitable:
            def __init__(self, value):
                self._value = value
            def __await__(self):
                async def _coro():
                    return self._value
                return _coro().__await__()
        return _Awaitable(result)
    fake_session.execute = fake_execute

    # Add vehicles with driver metadata
    fake_session.vehicles.append(
        VehicleORM(
            id=vehicle1_id,
            vehicle_number="MH12AB1234",
            registration_number="MH12AB1234",
            truck_type="compactor",
            capacity_kg=5000,
            capacity_cubic_meter=10,
            contractor_id=contractor_id,
            ward_id=ward_id,
            fuel_type="diesel",
            operational_status="operational",
            active=True,
            metadata_json={
                "driver_name": "Fallback Driver",
                "driver_id": "drv-fallback-1",
                "driver_phone": "9876543210",
                "license_number": "LIC-FALLBACK",
                "license_expiry": "2035-12-31",
            },
        )
    )
    fake_session.vehicles.append(
        VehicleORM(
            id=vehicle2_id,
            vehicle_number="MH12AB5678",
            registration_number="MH12AB5678",
            truck_type="tipper",
            capacity_kg=4000,
            capacity_cubic_meter=8,
            contractor_id=contractor_id,
            ward_id=ward_id,
            fuel_type="diesel",
            operational_status="operational",
            active=True,
            metadata_json={
                "driver_name": "Second Fallback",
                # No driver_id, should auto-generate
                "driver_phone": "9123456789",
            },
        )
    )

    with _build_client(fake_session) as client:
        resp = client.get("/drivers")
        assert resp.status_code == 200
        drivers = resp.json()
        # Should list both drivers
        names = {d["name"] for d in drivers}
        assert "Fallback Driver" in names
        assert "Second Fallback" in names
        # Check fields for first driver
        fallback = next(d for d in drivers if d["name"] == "Fallback Driver")
        assert fallback["id"] == "drv-fallback-1"
        assert fallback["phone"] == "9876543210"
        assert fallback["license_number"] == "LIC-FALLBACK"
        assert fallback["license_expiry"] == "2035-12-31"
        assert fallback["assigned_truck_id"] == str(vehicle1_id)
        # Second driver should have auto-generated id
        second = next(d for d in drivers if d["name"] == "Second Fallback")
        assert second["id"].startswith("drv-")
        assert second["assigned_truck_id"] == str(vehicle2_id)


    app.dependency_overrides.clear()