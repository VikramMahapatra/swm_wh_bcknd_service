from __future__ import annotations

import uuid

import pytest

from swm_db.models import ContractorORM, RouteORM, VehicleORM, WardORM


def _contractor() -> ContractorORM:
    return ContractorORM(id=uuid.uuid4(), contractor_name="ABC Contractor")


def _ward() -> WardORM:
    return WardORM(id=uuid.uuid4(), ward_name="Ward 11")


def _route() -> RouteORM:
    return RouteORM(id=uuid.uuid4(), route_name="Route 7")


class TestVehicleModel:
    def test_vehicle_accepts_valid_payload(self) -> None:
        contractor = _contractor()
        ward = _ward()
        route = _route()

        vehicle = VehicleORM(
            vehicle_number="tn01-ab-1234",
            registration_number="ka02-cd-9876",
            contractor_id=contractor.id,
            ward_id=ward.id,
            route_id=route.id,
            fuel_type="diesel",
            operational_status="operational",
            capacity_kg=12000,
            capacity_cubic_meter=28,
            metadata_json={"gps": "yes"},
        )

        assert vehicle.vehicle_number == "TN01-AB-1234"
        assert vehicle.registration_number == "KA02-CD-9876"

    def test_invalid_vehicle_number_raises(self) -> None:
        contractor = _contractor()
        ward = _ward()

        with pytest.raises(ValueError, match="vehicle_number"):
            VehicleORM(
                vehicle_number="@@@",
                registration_number="KA02-CD-9876",
                contractor_id=contractor.id,
                ward_id=ward.id,
                fuel_type="diesel",
                operational_status="operational",
                capacity_kg=1,
                capacity_cubic_meter=1,
                metadata_json={},
            )

    def test_invalid_fuel_type_raises(self) -> None:
        contractor = _contractor()
        ward = _ward()

        with pytest.raises(ValueError, match="fuel_type"):
            VehicleORM(
                vehicle_number="TN01-AB-1234",
                registration_number="KA02-CD-9876",
                contractor_id=contractor.id,
                ward_id=ward.id,
                fuel_type="hydrogen",
                operational_status="operational",
                capacity_kg=1,
                capacity_cubic_meter=1,
                metadata_json={},
            )

    def test_invalid_operational_status_raises(self) -> None:
        contractor = _contractor()
        ward = _ward()

        with pytest.raises(ValueError, match="operational_status"):
            VehicleORM(
                vehicle_number="TN01-AB-1234",
                registration_number="KA02-CD-9876",
                contractor_id=contractor.id,
                ward_id=ward.id,
                fuel_type="diesel",
                operational_status="unknown",
                capacity_kg=1,
                capacity_cubic_meter=1,
                metadata_json={},
            )

    def test_relationship_properties_exist(self) -> None:
        assert "vehicles" in ContractorORM.__mapper__.relationships
        assert "vehicles" in WardORM.__mapper__.relationships
        assert "vehicles" in RouteORM.__mapper__.relationships
        assert "contractor" in VehicleORM.__mapper__.relationships
        assert "ward" in VehicleORM.__mapper__.relationships
        assert "route" in VehicleORM.__mapper__.relationships
