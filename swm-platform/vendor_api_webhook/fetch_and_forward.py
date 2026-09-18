"""Fetch live vehicle GPS data from the Zone-F vendor API and forward it to
the SWM ingestion webhook (see docs/external-gps-webhook-spec.md).

Configuration is read from environment variables so credentials are not
hardcoded in source control. Defaults match the values previously supplied
for local/manual runs.

Environment variables:
    VENDOR_API_BASE_URL   Vendor webservice base URL
    VENDOR_USERNAME       Vendor API username
    VENDOR_PASSWORD       Vendor API password
    VENDOR_PROJECT_ID     Vendor "ProjectId" parameter
    VENDOR_COMPANY_NAME   Vendor "company_names" parameter
    VENDOR_IMEI_NOS       Comma-separated IMEI list to request
    WEBHOOK_URL           SWM ingestion webhook URL
    WEBHOOK_VENDOR_ID     X-Vendor-Id header value sent to the webhook
    WEBHOOK_VERIFY_SSL    "true"/"false" - verify TLS on the webhook call
    VENDOR_VERIFY_SSL     "true"/"false" - verify TLS on the vendor API call
    INGESTION_WEBHOOK_SECRET         Shared secret required by the ingestion API
    INGESTION_WEBHOOK_SECRET_HEADER  Header name for the shared secret (default: X-Webhook-Secret)
    POLL_INTERVAL_SECONDS  Seconds to wait between fetch/push cycles when run continuously (default: 90)
    WEBHOOK_TARGET        Which webhook(s) to push to: "local", "prod", or "both" (default: both)
    LOCAL_WEBHOOK_URL     Local ingestion-api webhook URL (default: http://127.0.0.1:9001/webhook/gps)
    LOCAL_WEBHOOK_VERIFY_SSL  "true"/"false" - verify TLS on the local webhook call (default: false)
"""
import os
import time
import uuid
from datetime import datetime

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

VENDOR_BASE_URL = os.environ.get("VENDOR_API_BASE_URL", "http://43.204.188.112/webservice")
VENDOR_CREDENTIALS = {
    "username": os.environ.get("VENDOR_USERNAME", "zonef"),
    "password": os.environ.get("VENDOR_PASSWORD", "f@123"),
}
VENDOR_PROJECT_ID = os.environ.get("VENDOR_PROJECT_ID", "16")
VENDOR_COMPANY_NAME = os.environ.get("VENDOR_COMPANY_NAME", "Zone-F")
VENDOR_IMEI_NOS = os.environ.get(
    "VENDOR_IMEI_NOS",
    "357803373445671,867111062621948,357803370693901,"
    "867111063111626,867111063124991,357803370392157,"
    "356218601961525,356218601645482,866330053247072,"
    "220718645,357803370355055,356218600956146,"
    "356218600456170,868926034573599,868926034511946,"
    "866710035968897,866710035988523",
)
VENDOR_VERIFY_SSL = os.environ.get("VENDOR_VERIFY_SSL", "false").lower() == "true"

WEBHOOK_VENDOR_ID = os.environ.get("WEBHOOK_VENDOR_ID", "zonef")

# Which webhook(s) to push to: "local", "prod", or "both"
WEBHOOK_TARGET = os.environ.get("WEBHOOK_TARGET", "both").strip().lower()

# Production target (SWM ingestion webhook)
PRODUCTION_WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://ingestion-swmdev.zentrixel.com/webhook/gps")
PRODUCTION_WEBHOOK_VERIFY_SSL = os.environ.get("WEBHOOK_VERIFY_SSL", "true").lower() == "true"

# Local dev target (docker-compose ingestion-api)
LOCAL_WEBHOOK_URL = os.environ.get("LOCAL_WEBHOOK_URL", "http://127.0.0.1:9001/webhook/gps")
LOCAL_WEBHOOK_VERIFY_SSL = os.environ.get("LOCAL_WEBHOOK_VERIFY_SSL", "false").lower() == "true"

# Shared secret required by the ingestion API's webhook auth (see INGESTION_WEBHOOK_SECRET in .env)
WEBHOOK_SECRET = os.environ.get("INGESTION_WEBHOOK_SECRET", "")
WEBHOOK_SECRET_HEADER = os.environ.get("INGESTION_WEBHOOK_SECRET_HEADER", "X-Webhook-Secret")


def _build_webhook_targets():
    """Build the list of webhook destinations to push to, based on WEBHOOK_TARGET."""
    if WEBHOOK_TARGET not in ("local", "prod", "both"):
        raise ValueError(f'WEBHOOK_TARGET must be "local", "prod", or "both", got: {WEBHOOK_TARGET!r}')

    targets = []
    if WEBHOOK_TARGET in ("prod", "both"):
        targets.append({
            "name": "production",
            "url": PRODUCTION_WEBHOOK_URL,
            "verify_ssl": PRODUCTION_WEBHOOK_VERIFY_SSL,
        })
    if WEBHOOK_TARGET in ("local", "both"):
        targets.append({
            "name": "local",
            "url": LOCAL_WEBHOOK_URL,
            "verify_ssl": LOCAL_WEBHOOK_VERIFY_SSL,
        })
    return targets


WEBHOOK_TARGETS = _build_webhook_targets()

# The vendor account is limited to ~1 API call per minute; keep cycles well above that.
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "90"))

# Candidate field names used by the vendor API for each webhook attribute.
# Confirmed against a live response: Imeino, Latitude, Longitude, GPSActualTime,
# Speed, Angle, IGN, Odometer.
FIELD_ALIASES = {
    "imei": ("Imeino", "IMEI", "Imei", "Imei_No", "IMEI_No", "imei", "imei_no"),
    "latitude": ("Latitude", "latitude", "Lat"),
    "longitude": ("Longitude", "longitude", "Long", "Lng"),
    "timestamp": ("GPSActualTime", "Datetime", "GPS_Time", "Location_Time", "timestamp"),
    "speed": ("Speed", "speed"),
    "heading": ("Angle", "course", "Heading", "Direction", "heading"),
    "ignition": ("IGN", "Ignition_Status", "Ignition", "Acc_Status", "ignition"),
    "odometer": ("Odometer", "Odometer_Reading", "odometer"),
}

# Vendor GPSActualTime/Datetime values are "DD-MM-YYYY HH:MM:SS" in IST (UTC+5:30).
VENDOR_TIMESTAMP_FORMAT = "%d-%m-%Y %H:%M:%S"
VENDOR_TZ_OFFSET = "+05:30"


def parse_vendor_timestamp(raw):
    """Convert a vendor DD-MM-YYYY HH:MM:SS timestamp to ISO-8601 with IST offset."""
    try:
        parsed = datetime.strptime(str(raw).strip(), VENDOR_TIMESTAMP_FORMAT)
        return parsed.strftime("%Y-%m-%dT%H:%M:%S") + VENDOR_TZ_OFFSET
    except ValueError:
        return raw


def _first_present(vehicle, keys):
    """Return the first non-empty value found in vehicle for any of the keys.

    The vendor API uses "--" as a placeholder for unavailable fields.
    """
    for key in keys:
        value = vehicle.get(key)
        if value not in (None, "", "--"):
            return value
    return None


def generate_token():
    """Fetch a fresh access token from the vendor API."""
    response = requests.post(
        VENDOR_BASE_URL,
        params={"token": "generateAccessToken"},
        json=VENDOR_CREDENTIALS,
        verify=VENDOR_VERIFY_SSL,
    )
    response.raise_for_status()
    data = response.json()

    # Vendor API nests the token under "data"; fall back to top-level keys too
    nested = data.get("data") if isinstance(data.get("data"), dict) else {}
    token = (
        nested.get("token")
        or data.get("token")
        or data.get("access_token")
        or data.get("auth-code")
    )
    if not token:
        raise ValueError(f"Could not extract token from response: {data}")

    print("Token generated successfully.")
    return token


def get_vehicle_gps_data(auth_token):
    """Fetch live vehicle GPS data using the provided token."""
    headers = {"auth-code": auth_token}
    params = {
        "token": "getTokenBaseLiveData",
        "ProjectId": VENDOR_PROJECT_ID,
    }
    body = {
        "company_names": VENDOR_COMPANY_NAME,
        "vehicle_nos": "",
        "imei_nos": VENDOR_IMEI_NOS,
        "format": "json",
    }

    response = requests.get(
        VENDOR_BASE_URL,
        params=params,
        headers=headers,
        json=body,
        verify=VENDOR_VERIFY_SSL,
    )
    response.raise_for_status()
    data = response.json()
    vendor_error = data.get("root", {}).get("error") if isinstance(data.get("root"), dict) else None
    if vendor_error:
        raise RuntimeError(f"Vendor GPS API error: {vendor_error}")
    return data


def is_token_expired(data):
    """Detect if the response indicates an expired or invalid token."""
    if isinstance(data, dict):
        status = str(data.get("status", "")).lower()
        message = str(data.get("message", "")).lower()
        error = str(data.get("error", "")).lower()
        if any(kw in status + message + error for kw in ["expired", "invalid", "unauthorized", "token"]):
            return True
    return False


def fetch_fleet_data():
    """Get token, fetch vehicle data, auto-retry once if the token expired."""
    auth_token = generate_token()
    data = get_vehicle_gps_data(auth_token)

    if is_token_expired(data):
        print("Token expired or invalid. Regenerating token and retrying...")
        auth_token = generate_token()
        data = get_vehicle_gps_data(auth_token)

    vehicles = data.get("root", {}).get("VehicleData", [])
    if not isinstance(vehicles, list):
        raise ValueError("Vendor GPS API returned an invalid VehicleData payload.")
    print(f"Total vehicles received from vendor API: {len(vehicles)}")
    return vehicles


def transform_vehicle_to_gps_event(vehicle):
    """Map one vendor VehicleData record to the webhook's GPS event schema.

    Returns None if the vehicle is missing a required field (imei/lat/lon).
    """
    imei = _first_present(vehicle, FIELD_ALIASES["imei"])
    latitude = _first_present(vehicle, FIELD_ALIASES["latitude"])
    longitude = _first_present(vehicle, FIELD_ALIASES["longitude"])
    timestamp = _first_present(vehicle, FIELD_ALIASES["timestamp"])

    if not (imei and latitude is not None and longitude is not None and timestamp):
        return None

    # Webhook contract requires imei to be 14-17 digits; some vendor records are malformed.
    if not (14 <= len(str(imei)) <= 17):
        return None

    event = {
        "imei": str(imei),
        "latitude": float(latitude),
        "longitude": float(longitude),
        "timestamp": parse_vendor_timestamp(timestamp),
    }

    speed = _first_present(vehicle, FIELD_ALIASES["speed"])
    if speed not in (None, ""):
        event["speed"] = float(speed)

    heading = _first_present(vehicle, FIELD_ALIASES["heading"])
    if heading not in (None, ""):
        event["heading"] = float(heading)

    ignition = _first_present(vehicle, FIELD_ALIASES["ignition"])
    if ignition is not None:
        event["ignition"] = str(ignition).strip().lower() in ("1", "true", "on", "yes")

    odometer = _first_present(vehicle, FIELD_ALIASES["odometer"])
    if odometer not in (None, ""):
        event["odometer"] = float(odometer)

    return event


def build_gps_events(vehicles):
    """Convert vendor vehicles into webhook GPS events, skipping incomplete records."""
    events = []
    skipped = 0
    for vehicle in vehicles:
        event = transform_vehicle_to_gps_event(vehicle)
        if event is None:
            skipped += 1
            continue
        events.append(event)

    if skipped:
        print(f"Skipped {skipped} vehicle(s) missing required GPS fields.")
    return events


def push_to_webhook(events, url, verify_ssl):
    """POST the GPS events batch to a single SWM ingestion webhook target."""
    headers = {
        "Content-Type": "application/json",
        "X-Vendor-Id": WEBHOOK_VENDOR_ID,
        "X-Request-Id": str(uuid.uuid4()),
    }
    if WEBHOOK_SECRET:
        headers[WEBHOOK_SECRET_HEADER] = WEBHOOK_SECRET
    response = requests.post(
        url,
        json=events,
        headers=headers,
        verify=verify_ssl,
    )
    response.raise_for_status()
    return response


def push_to_all_webhooks(events):
    """Push the GPS events batch to every configured webhook target independently.

    A failure on one target (e.g. production) does not prevent delivery to the others.
    """
    if not events:
        print("No GPS events to send; skipping webhook calls.")
        return

    if not WEBHOOK_TARGETS:
        print("No webhook targets configured (WEBHOOK_TARGET must be 'local', 'prod', or 'both').")
        return

    for target in WEBHOOK_TARGETS:
        try:
            response = push_to_webhook(events, target["url"], target["verify_ssl"])
            print(f"[{target['name']}] Sent {len(events)} GPS event(s). Status: {response.status_code}")
        except requests.exceptions.RequestException as exc:
            print(f"[{target['name']}] Webhook push failed: {exc}")


def run():
    """Full import cycle: fetch vendor GPS data and forward it to SWM."""
    vehicles = fetch_fleet_data()
    events = build_gps_events(vehicles)
    push_to_all_webhooks(events)


def run_forever(interval_seconds=POLL_INTERVAL_SECONDS):
    """Repeatedly run the fetch/transform/push cycle until interrupted (Ctrl+C)."""
    print(f"Starting continuous GPS import loop (interval: {interval_seconds}s). Press Ctrl+C to stop.")
    while True:
        try:
            run()
        except Exception as exc:  # noqa: BLE001 - keep the loop alive across any cycle failure
            print(f"Cycle failed: {exc}")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    try:
        run_forever()
    except KeyboardInterrupt:
        print("Stopped by user.")
