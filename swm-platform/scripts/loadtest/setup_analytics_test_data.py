from __future__ import annotations

import argparse
import time
from typing import Any

import httpx


def _find_by_code(items: list[dict[str, Any]], key: str, value: str) -> dict[str, Any] | None:
    for item in items:
        if str(item.get(key, "")).strip().lower() == value.strip().lower():
            return item
    return None


def _list_entities(client: httpx.Client, base_url: str, path: str, *, q: str | None = None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"page": 1, "page_size": 200}
    if q:
        params["q"] = q
    resp = client.get(f"{base_url}{path}", params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return data.get("items", [])


def _ensure_vendor(client: httpx.Client, base_url: str, code: str) -> str:
    rows = _list_entities(client, base_url, "/vendors", q=code)
    found = _find_by_code(rows, "vendor_code", code)
    if found:
        return str(found["id"])

    payload = {
        "vendor_code": code,
        "vendor_name": f"{code.upper()} Test Vendor",
        "auth_type": "header",
        "active": True,
        "allowed_ips": [],
        "callback_format": {},
        "metadata": {"purpose": "analytics-loadtest"},
    }
    resp = client.post(f"{base_url}/vendors", json=payload, timeout=20)
    resp.raise_for_status()
    return str(resp.json()["id"])


def _ensure_contractor(client: httpx.Client, base_url: str) -> str:
    code = "CNT_LOADTEST"
    rows = _list_entities(client, base_url, "/contractors", q=code)
    found = _find_by_code(rows, "contractor_code", code)
    if found:
        return str(found["id"])

    payload = {
        "contractor_code": code,
        "contractor_name": "Loadtest Contractor",
        "contact": "loadtest",
        "sla_details": {},
        "active": True,
    }
    resp = client.post(f"{base_url}/contractors", json=payload, timeout=20)
    resp.raise_for_status()
    return str(resp.json()["id"])


def _ensure_ward(client: httpx.Client, base_url: str) -> str:
    code = "WARD_LOADTEST"
    rows = _list_entities(client, base_url, "/wards", q=code)
    found = _find_by_code(rows, "ward_code", code)
    if found:
        return str(found["id"])

    payload = {
        "ward_code": code,
        "ward_name": "Loadtest Ward",
        "zone_name": "Loadtest Zone",
        "active": True,
    }
    resp = client.post(f"{base_url}/wards", json=payload, timeout=20)
    resp.raise_for_status()
    return str(resp.json()["id"])


def _ensure_route(client: httpx.Client, base_url: str) -> str:
    code = "ROUTE_LOADTEST"
    rows = _list_entities(client, base_url, "/routes", q=code)
    found = _find_by_code(rows, "route_code", code)
    if found:
        return str(found["id"])

    payload = {
        "route_code": code,
        "route_name": "Loadtest Route",
        "expected_distance_km": 12.0,
        "expected_duration_min": 90,
        "start_point": "Loadtest Start",
        "end_point": "Loadtest End",
        "active": True,
    }
    resp = client.post(f"{base_url}/routes", json=payload, timeout=20)
    resp.raise_for_status()
    return str(resp.json()["id"])


def _ensure_geofence(client: httpx.Client, base_url: str, ward_id: str, base_lat: float, base_lng: float) -> None:
    code = "GF_LOADTEST_CORE"
    rows = _list_entities(client, base_url, "/geofences", q=code)
    found = _find_by_code(rows, "geofence_code", code)
    if found:
        return

    payload = {
        "geofence_code": code,
        "geofence_name": "Loadtest Core Geofence",
        "type": "zone",
        "geometry_type": "circle",
        "center_lat": base_lat,
        "center_lng": base_lng,
        "radius_meter": 1200.0,
        "ward_id": ward_id,
        "active": True,
    }
    resp = client.post(f"{base_url}/geofences", json=payload, timeout=20)
    resp.raise_for_status()


def _ensure_vehicle(client: httpx.Client, base_url: str, idx: int, contractor_id: str, ward_id: str, route_id: str) -> str:
    vehicle_number = f"LT-TRK-{idx:03d}"
    rows = _list_entities(client, base_url, "/vehicles", q=vehicle_number)
    found = _find_by_code(rows, "vehicle_number", vehicle_number)
    if found:
        return str(found["id"])

    payload = {
        "vehicle_number": vehicle_number,
        "registration_number": vehicle_number,
        "contractor_id": contractor_id,
        "ward_id": ward_id,
        "route_id": route_id,
        "truck_type": "compactor",
        "capacity_kg": 12000,
        "capacity_cubic_meter": 12,
        "fuel_type": "diesel",
        "operational_status": "operational",
        "chassis_number": None,
        "engine_number": None,
        "manufacture_year": None,
        "active": True,
        "metadata": {"source": "loadtest"},
    }
    resp = client.post(f"{base_url}/vehicles", json=payload, timeout=20)
    resp.raise_for_status()
    return str(resp.json()["id"])


def _ensure_device(client: httpx.Client, base_url: str, imei: str, vendor_id: str) -> str:
    rows = _list_entities(client, base_url, "/devices", q=imei)
    found = _find_by_code(rows, "imei", imei)
    if found:
        return str(found["id"])

    payload = {
        "vendor_id": vendor_id,
        "imei": imei,
        "serial_no": imei,
        "model": "loadtest-gps",
        "manufacturer": "loadtest",
        "firmware_version": "1.0",
        "sim_number": None,
        "installed_on": None,
        "activated_on": None,
        "last_seen": None,
        "battery_percent": None,
        "signal_strength": None,
        "health_status": "healthy",
        "active": True,
        "metadata": {"source": "loadtest"},
    }
    resp = client.post(f"{base_url}/devices", json=payload, timeout=20)
    resp.raise_for_status()
    return str(resp.json()["id"])


def _ensure_assignment(client: httpx.Client, base_url: str, device_id: str, vehicle_id: str) -> None:
    payload = {
        "device_id": device_id,
        "vehicle_id": vehicle_id,
        "assigned_from": None,
        "assigned_to": None,
        "active": True,
        "remarks": "loadtest setup",
    }
    last_error: Exception | None = None
    for _ in range(3):
        resp = client.post(f"{base_url}/device-assignments", json=payload, timeout=20)
        if resp.status_code in {200, 201}:
            return
        if resp.status_code >= 500:
            # Retry transient commit/visibility races between create and assign requests.
            time.sleep(0.4)
            last_error = httpx.HTTPStatusError(
                "server error while assigning device",
                request=resp.request,
                response=resp,
            )
            continue
        resp.raise_for_status()

    if last_error is not None:
        raise last_error


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare ward/geofence/vehicle/device mappings for analytics loadtest")
    parser.add_argument("--admin-base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--trucks", type=int, default=10)
    parser.add_argument("--base-lat", type=float, default=28.6139)
    parser.add_argument("--base-lng", type=float, default=77.2090)
    args = parser.parse_args()

    vendor_codes = ["vendor_a", "vendor_b", "vendor_c"]

    with httpx.Client(headers={"x-role": "admin"}) as client:
        vendor_ids = {code: _ensure_vendor(client, args.admin_base_url, code) for code in vendor_codes}
        contractor_id = _ensure_contractor(client, args.admin_base_url)
        ward_id = _ensure_ward(client, args.admin_base_url)
        route_id = _ensure_route(client, args.admin_base_url)
        _ensure_geofence(client, args.admin_base_url, ward_id, args.base_lat, args.base_lng)

        for i in range(args.trucks):
            imei = f"990000000000{i:03d}"[-15:]
            vendor_code = vendor_codes[i % len(vendor_codes)]
            vehicle_id = _ensure_vehicle(client, args.admin_base_url, i + 1, contractor_id, ward_id, route_id)
            device_id = _ensure_device(client, args.admin_base_url, imei, vendor_ids[vendor_code])
            _ensure_assignment(client, args.admin_base_url, device_id, vehicle_id)

    print("[setup] loadtest master data and mappings ready")


if __name__ == "__main__":
    main()
