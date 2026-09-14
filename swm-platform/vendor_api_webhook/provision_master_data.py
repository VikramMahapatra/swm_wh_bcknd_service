"""One-off provisioning script: rebuild SWM master data from a live vendor GPS snapshot.

Deletes ALL existing rows in Zones, Wards, Vehicles, Devices, Device-Vehicle
Assignments, and Drivers on the target admin-api, then recreates them from a
fresh fetch of the Zone-F vendor fleet API (see fetch_and_forward.py).

This talks to a REAL database (admin-api's configured Postgres) via the
admin-api REST endpoints, so all writes go through normal validation.

Environment variables:
    ADMIN_API_BASE_URL   admin-api base URL (default: http://127.0.0.1:9003)
    ADMIN_USERNAME       admin-api login username (default: admin)
    ADMIN_PASSWORD       admin-api login password (default: admin123)
"""
import os
import sys

import requests

from fetch_and_forward import FIELD_ALIASES, _first_present, fetch_fleet_data

ADMIN_API_BASE_URL = os.environ.get("ADMIN_API_BASE_URL", "http://127.0.0.1:9003").rstrip("/")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

ZONE_CODE = "ZONEF"
ZONE_NAME = "Zone-F"
WARD_CODE = "F11"
WARD_NAME = "F11"
VENDOR_CODE = "ZONEF"
VENDOR_NAME = "Zone-F"


def login():
    """Authenticate against admin-api and return a bearer token."""
    resp = requests.post(
        f"{ADMIN_API_BASE_URL}/v1/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _get_all(session, path):
    """List all rows of a paginated master_data endpoint."""
    items = []
    page = 1
    while True:
        resp = session.get(f"{ADMIN_API_BASE_URL}{path}", params={"page": page, "page_size": 200})
        resp.raise_for_status()
        body = resp.json()
        rows = body.get("items", body) if isinstance(body, dict) else body
        if not rows:
            break
        items.extend(rows)
        if len(rows) < 200:
            break
        page += 1
    return items


def wipe_existing_master_data(session):
    """Delete all existing rows: assignments -> devices -> drivers -> vehicles -> wards -> zones."""
    for device in _get_all(session, "/devices"):
        session.delete(f"{ADMIN_API_BASE_URL}/device-assignments/{device['id']}")

    for device in _get_all(session, "/devices"):
        session.delete(f"{ADMIN_API_BASE_URL}/devices/{device['id']}")
    print("Deleted existing devices (and their assignments).")

    for driver in session.get(f"{ADMIN_API_BASE_URL}/drivers").json():
        session.delete(f"{ADMIN_API_BASE_URL}/drivers/{driver['id']}")
    print("Deleted existing drivers.")

    for vehicle in _get_all(session, "/vehicles"):
        session.delete(f"{ADMIN_API_BASE_URL}/vehicles/{vehicle['id']}")
    print("Deleted existing vehicles.")

    for ward in _get_all(session, "/wards"):
        session.delete(f"{ADMIN_API_BASE_URL}/wards/{ward['id']}")
    print("Deleted existing wards.")

    for zone in session.get(f"{ADMIN_API_BASE_URL}/zones").json():
        session.delete(f"{ADMIN_API_BASE_URL}/zones/{zone['id']}")
    print("Deleted existing zones.")


def ensure_zone_and_ward(session):
    zone = session.post(
        f"{ADMIN_API_BASE_URL}/zones",
        json={"zone_code": ZONE_CODE, "zone_name": ZONE_NAME},
    )
    zone.raise_for_status()
    zone_id = zone.json()["id"]

    ward = session.post(
        f"{ADMIN_API_BASE_URL}/wards",
        json={"ward_code": WARD_CODE, "ward_name": WARD_NAME, "zone_name": ZONE_NAME},
    )
    ward.raise_for_status()
    ward_id = ward.json()["id"]

    print(f"Created zone {ZONE_NAME} ({zone_id}) and ward {WARD_NAME} ({ward_id}).")
    return zone_id, ward_id


def ensure_vendor(session):
    """Create the Zone-F vendor used as the FK owner for devices/vehicles."""
    resp = session.post(
        f"{ADMIN_API_BASE_URL}/vendors",
        json={
            "vendor_code": VENDOR_CODE,
            "vendor_name": VENDOR_NAME,
            "phone": "0000000000",
            "auth_type": "header",
        },
    )
    resp.raise_for_status()
    vendor_id = resp.json()["id"]
    print(f"Created vendor {VENDOR_NAME} ({vendor_id}).")
    return vendor_id


def _clean_vehicle_number(raw):
    return "".join(ch for ch in str(raw).upper() if ch.isalnum() or ch == "-")


def build_records(vehicles):
    """Extract (vehicle_number, imei, truck_type, driver_name) tuples, skipping invalid IMEIs."""
    records = []
    for vehicle in vehicles:
        imei = _first_present(vehicle, FIELD_ALIASES["imei"])
        vehicle_no = _first_present(vehicle, ("Vehicle_No",))
        if not imei or not vehicle_no or not (14 <= len(str(imei)) <= 17):
            continue

        vehicle_number = _clean_vehicle_number(vehicle_no)
        truck_type = _first_present(vehicle, ("Vehicletype",)) or "Truck"

        first_name = str(vehicle.get("Driver_First_Name") or "").strip()
        last_name = str(vehicle.get("Driver_Last_Name") or "").strip()
        driver_name = None
        if first_name and first_name != "--":
            driver_name = f"{first_name} {last_name}".strip()

        records.append(
            {
                "imei": str(imei),
                "vehicle_number": vehicle_number,
                "truck_type": truck_type,
                "driver_name": driver_name,
            }
        )
    return records


def create_devices_and_vehicles(session, vendor_id, ward_id, records):
    device_ids = {}
    vehicle_ids = {}

    for record in records:
        device_resp = session.post(
            f"{ADMIN_API_BASE_URL}/devices",
            json={"vendor_id": vendor_id, "imei": record["imei"], "health_status": "healthy"},
        )
        if device_resp.status_code >= 400:
            print(f"  [device] {record['imei']} failed: {device_resp.status_code} {device_resp.text}")
            continue
        device_ids[record["imei"]] = device_resp.json()["id"]

        vehicle_resp = session.post(
            f"{ADMIN_API_BASE_URL}/vehicles",
            json={
                "vehicle_number": record["vehicle_number"],
                "registration_number": record["vehicle_number"],
                "vendor_id": vendor_id,
                "ward_id": ward_id,
                "truck_type": record["truck_type"],
                "fuel_type": "diesel",
                "operational_status": "operational",
            },
        )
        if vehicle_resp.status_code >= 400:
            print(f"  [vehicle] {record['vehicle_number']} failed: {vehicle_resp.status_code} {vehicle_resp.text}")
            continue
        vehicle_ids[record["imei"]] = vehicle_resp.json()["id"]

    print(f"Created {len(device_ids)} devices and {len(vehicle_ids)} vehicles.")
    return device_ids, vehicle_ids


def create_assignments(session, device_ids, vehicle_ids):
    count = 0
    for imei, device_id in device_ids.items():
        vehicle_id = vehicle_ids.get(imei)
        if not vehicle_id:
            continue
        resp = session.post(
            f"{ADMIN_API_BASE_URL}/device-assignments",
            json={"device_id": device_id, "vehicle_id": vehicle_id},
        )
        if resp.status_code >= 400:
            print(f"  [assignment] {imei} failed: {resp.status_code} {resp.text}")
            continue
        count += 1
    print(f"Created {count} device-vehicle assignments.")


def create_drivers(session, vendor_id, vehicle_ids, records):
    count = 0
    for record in records:
        if not record["driver_name"]:
            continue
        vehicle_id = vehicle_ids.get(record["imei"])
        if not vehicle_id:
            continue
        resp = session.post(
            f"{ADMIN_API_BASE_URL}/drivers",
            json={
                "name": record["driver_name"],
                "person_type": "driver",
                "vendor_id": vendor_id,
                "assigned_truck_id": vehicle_id,
                "status": "active",
            },
        )
        if resp.status_code >= 400:
            print(f"  [driver] {record['driver_name']} failed: {resp.status_code} {resp.text}")
            continue
        count += 1
    print(f"Created {count} driver records with truck assignments.")


class _AuthSession(requests.Session):
    def __init__(self, token):
        super().__init__()
        self.headers.update(_headers(token))


def main():
    token = login()
    session = _AuthSession(token)

    print("Fetching live vendor fleet data...")
    vehicles = fetch_fleet_data()
    records = build_records(vehicles)
    if not records:
        print("No valid vehicle records extracted from vendor response; aborting before any deletes.")
        sys.exit(1)
    print(f"Extracted {len(records)} valid vehicle/device records (of {len(vehicles)} vendor rows).")

    wipe_existing_master_data(session)

    zone_id, ward_id = ensure_zone_and_ward(session)
    vendor_id = ensure_vendor(session)
    device_ids, vehicle_ids = create_devices_and_vehicles(session, vendor_id, ward_id, records)
    create_assignments(session, device_ids, vehicle_ids)
    create_drivers(session, vendor_id, vehicle_ids, records)


if __name__ == "__main__":
    main()
