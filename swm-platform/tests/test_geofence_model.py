from __future__ import annotations

import uuid

import pytest

from swm_db.models import GeofenceORM, WardORM


def _ward() -> WardORM:
    return WardORM(ward_code="WARD-01", ward_name="Ward 01", zone_name="North")


class TestGeofenceModel:
    def test_circle_geofence_validates(self) -> None:
        ward = _ward()
        geofence = GeofenceORM(
            geofence_code="GF-001",
            geofence_name="Depot Circle",
            type="depot",
            geometry_type="circle",
            center_lat=12.9716,
            center_lng=77.5946,
            radius_meter=250,
            ward_id=ward.id,
            active=True,
        )
        assert geofence.geofence_code == "GF-001"

    def test_polygon_geojson_validates(self) -> None:
        geofence = GeofenceORM(
            geofence_code="GF-002",
            geofence_name="Zone Polygon",
            type="zone",
            geometry_type="polygon",
            polygon={
                "type": "Polygon",
                "coordinates": [
                    [
                        [77.59, 12.97],
                        [77.60, 12.97],
                        [77.60, 12.98],
                        [77.59, 12.98],
                        [77.59, 12.97],
                    ]
                ],
            },
            active=True,
        )
        assert geofence.polygon is not None

    def test_invalid_geometry_type_raises(self) -> None:
        with pytest.raises(ValueError, match="geometry_type"):
            GeofenceORM(
                geofence_code="GF-003",
                geofence_name="Bad Geofence",
                type="zone",
                geometry_type="line",
                active=True,
            )

    def test_invalid_latitude_raises(self) -> None:
        with pytest.raises(ValueError, match="center_lat"):
            GeofenceORM(
                geofence_code="GF-004",
                geofence_name="Bad Lat",
                type="parking",
                geometry_type="circle",
                center_lat=100.0,
                center_lng=77.0,
                radius_meter=100,
                active=True,
            )

    def test_invalid_polygon_type_raises(self) -> None:
        with pytest.raises(ValueError, match="GeoJSON"):
            GeofenceORM(
                geofence_code="GF-005",
                geofence_name="Bad Polygon",
                type="zone",
                geometry_type="polygon",
                polygon={"type": "Point", "coordinates": [77.59, 12.97]},
                active=True,
            )

    def test_ward_relationship_exists(self) -> None:
        assert "ward" in GeofenceORM.__mapper__.relationships
        assert "geofences" in WardORM.__mapper__.relationships
