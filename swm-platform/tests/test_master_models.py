from __future__ import annotations

import uuid

import pytest

from swm_db.models import ContractorORM, RouteORM, VehicleORM, WardORM


class TestContractorWardRouteModelValidation:
    def test_contractor_code_normalized(self) -> None:
        contractor = ContractorORM(
            contractor_code="ctr-01",
            contractor_name="ABC Services",
            sla_details={"uptime": "99.9%"},
        )
        assert contractor.contractor_code == "CTR-01"

    def test_ward_code_normalized(self) -> None:
        ward = WardORM(ward_code="w-11", ward_name="Ward 11", zone_name="East")
        assert ward.ward_code == "W-11"

    def test_route_code_normalized(self) -> None:
        route = RouteORM(
            route_code="r-20",
            route_name="Route 20",
            expected_distance_km=12.5,
            expected_duration_min=45,
            start_point="Depot A",
            end_point="Depot B",
        )
        assert route.route_code == "R-20"

    def test_invalid_route_duration_raises(self) -> None:
        with pytest.raises(ValueError, match="expected_duration_min"):
            RouteORM(
                route_code="R-21",
                route_name="Route 21",
                expected_distance_km=10,
                expected_duration_min=-1,
                start_point="A",
                end_point="B",
            )

    def test_relationships_exist(self) -> None:
        assert "vehicles" in ContractorORM.__mapper__.relationships
        assert "vehicles" in WardORM.__mapper__.relationships
        assert "vehicles" in RouteORM.__mapper__.relationships
        assert "contractor" in VehicleORM.__mapper__.relationships
        assert "ward" in VehicleORM.__mapper__.relationships
        assert "route" in VehicleORM.__mapper__.relationships

    def test_vehicle_can_reference_all_fk_fields(self) -> None:
        vehicle = VehicleORM(
            id=uuid.uuid4(),
            vehicle_number="TN01-AB-1234",
            registration_number="KA02-CD-9876",
            contractor_id=uuid.uuid4(),
            ward_id=uuid.uuid4(),
            route_id=uuid.uuid4(),
            fuel_type="diesel",
            operational_status="operational",
            capacity_kg=1000,
            capacity_cubic_meter=12,
            metadata_json={},
        )
        assert vehicle.route_id is not None
