import argparse
import asyncio
import json
import math
import random
from datetime import UTC, datetime, timedelta
from typing import Any, List, Tuple

import httpx

ROUTE_COORDS: List[Tuple[float, float]] = [
  (73.77146106998136, 18.65590324664102), (73.77153575645825, 18.65645416108611), (73.77159955721109, 18.65713920037117), (73.77162186777511, 18.65758657046405), (73.77160510591423, 18.65792506858464), (73.77156262181313, 18.65840899834526), (73.77151310810318, 18.65886460124904), (73.77139885499075, 18.6593496697149), (73.77225299469606, 18.65927694333488), (73.77226433700231, 18.65872198462487), (73.77220344905489, 18.65747230784769), (73.77217129631809, 18.65697977984953), (73.77269793187584, 18.65695283731598), (73.77308596110458, 18.65695279514572), (73.77307190702825, 18.6569747257674), (73.77268124216285, 18.65696406058874), (73.77271750510725, 18.65747371430444), (73.77273118734925, 18.65800028967268), (73.77275722995662, 18.65868293345706), (73.77333457869716, 18.65865630403874), (73.77332697192888, 18.65867786371363), (73.77227958479261, 18.65873746156021), (73.77226845218199, 18.65928090405186), (73.7731589048901, 18.65924712319138), (73.773802301387, 18.65918697730056), (73.77376586289685, 18.65862727052929), (73.7737405801543, 18.65809594243039), (73.77376507066883, 18.65771686425186), (73.77381380415426, 18.65742840214441), (73.77400832754742, 18.65704799089504), (73.7733433574773, 18.65649640167991), (73.77323081984359, 18.65644545485485), (73.77307989163887, 18.65643872894527), (73.77283045357468, 18.6564436767463), (73.77212864977731, 18.65648026253997), (73.77216946342709, 18.65693943550169), (73.77225294014298, 18.65877731394175), (73.77225542826001, 18.65930345377331), (73.77316634820666, 18.65926838297078), (73.77313635368566, 18.65980019860179), (73.77307084339483, 18.66086128313934), (73.77308054206873, 18.661093777711), (73.77349400639434, 18.66106555245612), (73.77384075861312, 18.66104499678103), (73.77391794080056, 18.66105657763077), (73.77413733692697, 18.66122136318888), (73.7744081671241, 18.66157284955925), (73.77425072466114, 18.66161632383806), (73.77382385054472, 18.66205468870171), (73.7736856325033, 18.66215797429268), (73.77361091234636, 18.66218884583567), (73.77348595956681, 18.66220606209703), (73.77313197420727, 18.66223001469054), (73.77284916514698, 18.66212790155745), (73.77273518200916, 18.66203042678747), (73.77254105332263, 18.6618156330084), (73.77238845996948, 18.66156784674652), (73.77228638295759, 18.6612882380265), (73.77223644500366, 18.66111582940568), (73.77220887676815, 18.66082898851018), (73.77221576668201, 18.6603800859481), (73.77221473944932, 18.65984891039755), (73.77311895847788, 18.65982485665181), (73.77308536570072, 18.66114050679472), (73.77305980881809, 18.66157833611896), (73.77302088914767, 18.6618228342088), (73.77292371484508, 18.66201160734053), (73.77275818416341, 18.66218175418146), (73.772155412722, 18.66247702955707), (73.7720078761777, 18.66255231845255), (73.77137282554231, 18.66269650339625), (73.77131033765896, 18.6626053083471), (73.77115880342197, 18.66233890536685), (73.77105300400682, 18.66208578947181), (73.7710133991897, 18.66162059429064), (73.77107060389277, 18.66111738532206), (73.77115036902349, 18.66073148040449), (73.77131156871816, 18.65999690974357), (73.77140572150314, 18.65938294561175), (73.77401998775159, 18.65918300600291), (73.77464129846332, 18.65917452059299), (73.77463916461113, 18.65950304770787), (73.77461787571771, 18.66022327509764), (73.77465018456815, 18.66027908952177), (73.77471006247018, 18.66035647287808), (73.7750242608799, 18.66062689653272), (73.77530253423373, 18.66027144944046), (73.77531664275726, 18.66029086778855), (73.77504407627593, 18.66064151069748), (73.77552116246555, 18.66102372013914), (73.77568533177484, 18.66089594605834), (73.77573154237565, 18.66013427966685), (73.77580362909214, 18.65933244209058), (73.77701805724064, 18.65937203989435), (73.77643785363328, 18.65997064290794), (73.77541645313838, 18.66111340872655), (73.77491966229563, 18.66162987821377), (73.77412540048151, 18.66243717772338), (73.7737854831016, 18.66277431509786),(73.723068, 18.684626)
]


def heading_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    dlon = math.radians(lon2 - lon1)
    lat1r = math.radians(lat1)
    lat2r = math.radians(lat2)
    x = math.sin(dlon) * math.cos(lat2r)
    y = math.cos(lat1r) * math.sin(lat2r) - math.sin(lat1r) * math.cos(lat2r) * math.cos(dlon)
    brng = (math.degrees(math.atan2(x, y)) + 360.0) % 360.0
    return int(round(brng))


def next_speed_kph(
    rng: random.Random,
    previous_speed: float,
    args: argparse.Namespace,
) -> float:
    if rng.random() < args.overspeed_chance:
        return round(rng.uniform(args.overspeed_min_kph, args.overspeed_max_kph), 2)

    target = rng.uniform(args.speed_kph - args.speed_fluctuation_kph, args.speed_kph + args.speed_fluctuation_kph)
    smoothed = (previous_speed * 0.65) + (target * 0.35)
    return round(max(args.min_speed_kph, min(args.max_normal_speed_kph, smoothed)), 2)


ALERT_SCENARIOS = [
    "overspeeding",
    "excessive_idle",
    "route_deviation",
    "missed_pickup",
    "unauthorized_stop",
    "unauthorized_halt",
    "speed_anomaly",
    "speed_violation",
    "geofence_breach",
    "gps_signal_loss",
    "vehicle_offline",
]

WEIGHMENT_WEIGHT_RANGES_KG = {
    "wet_waste": (400, 1200),
    "dry_waste": (200, 700),
    "plastic_waste": (100, 300),
    "construction_waste": (600, 1800),
    "mixed_waste": (350, 1000),
    "biomedical_waste": (40, 160),
}


def _parse_scenarios(raw: str) -> list[str]:
    if not raw.strip():
        return []
    values = [item.strip().lower() for item in raw.split(",") if item.strip()]
    unknown = sorted(set(values) - set(ALERT_SCENARIOS))
    if unknown:
        raise ValueError(f"unknown alert scenario(s): {', '.join(unknown)}")
    return values


def _parse_csv_values(raw: str) -> list[str]:
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


async def _admin_login(client: httpx.AsyncClient, args: argparse.Namespace) -> dict[str, str] | None:
    login_url = args.admin_api_url.rstrip("/") + "/v1/auth/login"
    try:
        resp = await client.post(
            login_url,
            json={"username": args.admin_username, "password": args.admin_password},
        )
        if resp.status_code >= 300:
            print(f"Weighment generation disabled: admin login failed HTTP {resp.status_code} -> {resp.text[:160]}")
            return None
        token = resp.json().get("access_token")
        if not token:
            print("Weighment generation disabled: admin login did not return access_token")
            return None
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    except Exception as exc:
        print(f"Weighment generation disabled: admin API unavailable ({exc})")
        return None


async def _prepare_weighment_context(
    client: httpx.AsyncClient,
    args: argparse.Namespace,
) -> dict[str, Any] | None:
    if not args.generate_weighments:
        return None
    headers = await _admin_login(client, args)
    if headers is None:
        return None

    admin_base = args.admin_api_url.rstrip("/")
    vehicle_query = args.weighment_vehicle_search or args.vehicle_id
    try:
        vehicle_resp = await client.get(
            f"{admin_base}/vehicles/search",
            params={"q": vehicle_query, "page_size": 10},
            headers=headers,
        )
        vehicle_resp.raise_for_status()
        vehicles = vehicle_resp.json()
        vehicle = next(
            (
                item
                for item in vehicles
                if str(item.get("vehicle_number")) == args.vehicle_id
                or str(item.get("registration_number")) == args.vehicle_id
            ),
            vehicles[0] if vehicles else None,
        )
        if not vehicle:
            print(f"Weighment generation disabled: no vehicle found for {vehicle_query}")
            return None

        detail_resp = await client.get(f"{admin_base}/vehicles/{vehicle['id']}/details", headers=headers)
        detail_resp.raise_for_status()
        vehicle_details = detail_resp.json()

        dump_yard_id = args.dump_yard_id or vehicle_details.get("dump_yard_id")
        dump_yards: list[dict[str, Any]] = []
        if not dump_yard_id:
            yards_resp = await client.get(f"{admin_base}/dump-yards", params={"active": "true"}, headers=headers)
            yards_resp.raise_for_status()
            yards_payload = yards_resp.json()
            dump_yards = yards_payload.get("items", yards_payload) if isinstance(yards_payload, dict) else yards_payload
            if dump_yards:
                dump_yard_id = dump_yards[0].get("id")
        if not dump_yard_id:
            print("Weighment generation disabled: no dump yard available")
            return None

        materials = _parse_csv_values(args.weighment_materials)
        materials = [material for material in materials if material in WEIGHMENT_WEIGHT_RANGES_KG]
        if not materials:
            materials = list(WEIGHMENT_WEIGHT_RANGES_KG)

        print(
            "Weighment generation enabled: "
            f"vehicle={vehicle_details.get('vehicle_number')}, dump_yard_id={dump_yard_id}, materials={','.join(materials)}"
        )
        return {
            "headers": headers,
            "vehicle": vehicle_details,
            "dump_yard_id": dump_yard_id,
            "materials": materials,
            "created_keys": set(),
        }
    except Exception as exc:
        print(f"Weighment generation disabled: failed to prepare admin context ({exc})")
        return None


def _simulated_weighment_time(service_day: datetime, lap: int, index: int, args: argparse.Namespace) -> datetime:
    start = service_day.replace(hour=args.weighment_start_hour, minute=5, second=0, microsecond=0)
    return start + timedelta(minutes=(lap - 1) * args.weighment_lap_spacing_min + index * args.weighment_entry_spacing_min)


async def _create_weighments_for_completed_route(
    client: httpx.AsyncClient,
    args: argparse.Namespace,
    rng: random.Random,
    context: dict[str, Any] | None,
    lap: int,
) -> None:
    if context is None:
        return
    now_local = datetime.now()
    if now_local.hour < args.weighment_start_hour:
        return

    admin_base = args.admin_api_url.rstrip("/")
    vehicle = context["vehicle"]
    service_days = [
        (now_local - timedelta(days=days_back)).replace(hour=0, minute=0, second=0, microsecond=0)
        for days_back in range(args.weighment_days_back, -1, -1)
    ]
    for day_index, service_day in enumerate(service_days):
        material = rng.choice(context["materials"])
        low, high = WEIGHMENT_WEIGHT_RANGES_KG[material]
        net_weight = round(rng.uniform(low, high), 1)
        tare_weight = round(rng.uniform(args.weighment_tare_min_kg, args.weighment_tare_max_kg), 1)
        gross_weight = round(net_weight + tare_weight, 1)
        entry_time = _simulated_weighment_time(service_day, lap, day_index, args)
        key = (vehicle.get("vehicle_id") or vehicle.get("id"), context["dump_yard_id"], material, entry_time.isoformat())
        if key in context["created_keys"]:
            continue
        context["created_keys"].add(key)
        payload = {
            "vehicle_id": vehicle.get("vehicle_id") or vehicle.get("id"),
            "gts_pickup_point_id": vehicle.get("gts_pickup_point_id"),
            "dump_yard_id": context["dump_yard_id"],
            "material_type": material,
            "service_date": service_day.date().isoformat(),
            "entry_time": entry_time.isoformat(),
            "gross_weight_kg": gross_weight,
            "tare_weight_kg": tare_weight,
            "net_weight_kg": net_weight,
            "slip_number": f"SIM-{service_day:%Y%m%d}-{args.vehicle_id}-{lap}-{day_index}",
            "operator_name": "Load Test Simulator",
            "remarks": (
                f"Simulated weighment for {args.vehicle_id}; "
                f"route={vehicle.get('route_name')}, ward={vehicle.get('ward_name')}, zone={vehicle.get('zone_name')}"
            ),
        }
        try:
            resp = await client.post(
                f"{admin_base}/dump-yard-weighment",
                headers=context["headers"],
                json=payload,
            )
            if resp.status_code == 409:
                print(f"[lap {lap}] skipped duplicate weighment {payload['slip_number']}")
            elif resp.status_code >= 300:
                print(f"[lap {lap}] weighment HTTP {resp.status_code} -> {resp.text[:200]}")
            else:
                print(
                    f"[lap {lap}] weighment {payload['service_date']} {material} "
                    f"net={net_weight}kg truck={args.vehicle_id}"
                )
        except Exception as exc:
            print(f"[lap {lap}] weighment send failed: {exc}")


def _offset_from_route(lat: float, lng: float, meters: float) -> tuple[float, float]:
    # Approximate meter-to-degree conversion is sufficient for load-test anomaly injection.
    return lat + (meters / 111_320.0), lng + (meters / (111_320.0 * max(math.cos(math.radians(lat)), 0.01)))


def maybe_alert_scenario(rng: random.Random, args: argparse.Namespace) -> str | None:
    if not args.inject_alerts or not args.alert_scenarios:
        return None
    if rng.random() >= args.alert_chance:
        return None
    return rng.choice(args.alert_scenarios)


def apply_alert_scenario(
    scenario: str | None,
    *,
    rng: random.Random,
    lat: float,
    lng: float,
    speed: float,
    timestamp: datetime,
    args: argparse.Namespace,
) -> tuple[float, float, float, datetime, dict[str, Any]]:
    if not scenario:
        return lat, lng, speed, timestamp, {}

    attributes: dict[str, Any] = {
        "simulated_alert": True,
        "alert_type": scenario,
        "alert_severity": "high",
        "alert_category": "fleet",
        "alert_reason": f"loadtest injected {scenario}",
    }

    if scenario in {"overspeeding", "speed_violation", "speed_anomaly"}:
        speed = round(rng.uniform(args.overspeed_min_kph, args.overspeed_max_kph), 2)
        attributes.update(
            {
                "alert_category": "fleet",
                "speed_violation": True,
                "speed_anomaly": scenario == "speed_anomaly",
                "overspeeding": scenario == "overspeeding",
                "threshold_kph": args.alert_speed_threshold_kph,
            }
        )
    elif scenario == "excessive_idle":
        speed = 0.0
        attributes.update(
            {
                "alert_category": "fleet",
                "idle_seconds": args.alert_idle_seconds,
                "excessive_idle": True,
            }
        )
    elif scenario in {"unauthorized_stop", "unauthorized_halt"}:
        speed = 0.0
        attributes.update(
            {
                "alert_category": "operations",
                "halt_seconds": args.alert_halt_seconds,
                "unauthorized_stop": scenario == "unauthorized_stop",
                "unauthorized_halt": scenario == "unauthorized_halt",
            }
        )
    elif scenario == "route_deviation":
        lat, lng = _offset_from_route(lat, lng, args.route_deviation_offset_m)
        attributes.update({"alert_category": "route", "route_deviation": True, "offset_m": args.route_deviation_offset_m})
    elif scenario == "missed_pickup":
        attributes.update({"alert_category": "operations", "missed_pickup": True})
    elif scenario == "geofence_breach":
        lat, lng = _offset_from_route(lat, lng, args.route_deviation_offset_m)
        attributes.update({"alert_category": "route", "geofence_breach": True, "geofence_event": "breach"})
    elif scenario == "gps_signal_loss":
        timestamp = timestamp - timedelta(seconds=args.gps_signal_loss_age_seconds)
        attributes.update({"alert_category": "device", "gps_signal_loss": True, "alert_severity": "medium"})
    elif scenario == "vehicle_offline":
        timestamp = timestamp - timedelta(seconds=args.vehicle_offline_age_seconds)
        speed = 0.0
        attributes.update({"alert_category": "device", "vehicle_offline": True, "alert_severity": "critical"})

    return lat, lng, speed, timestamp, attributes


async def run(args: argparse.Namespace) -> None:
    url = args.base_url.rstrip("/") + "/webhook/gps"
    headers = {
        "X-Vendor-Id": args.vendor_id,
        "Content-Type": "application/json",
    }
    if args.webhook_secret:
        headers[args.webhook_secret_header] = args.webhook_secret

    rng = random.Random(args.seed)
    current_speed = args.speed_kph
    args.alert_scenarios = _parse_scenarios(args.alert_scenarios)

    print(f"Sending GPS loop to {url} for IMEI={args.imei}, vehicle={args.vehicle_id}")
    print(f"Total points per lap: {len(ROUTE_COORDS)}")
    print(
        "Speed profile: "
        f"baseline={args.speed_kph} km/h, fluctuation=+/-{args.speed_fluctuation_kph} km/h, "
        f"overspeed_chance={args.overspeed_chance:.2f}, overspeed={args.overspeed_min_kph}-{args.overspeed_max_kph} km/h"
    )
    if args.inject_alerts:
        print(
            "Alert injection: "
            f"chance={args.alert_chance:.2f}, scenarios={','.join(args.alert_scenarios) or 'none'}"
        )

    timeout = httpx.Timeout(args.timeout_sec)
    async with httpx.AsyncClient(timeout=timeout) as client:
        weighment_context = await _prepare_weighment_context(client, args)
        lap = 0
        while True:
            lap += 1
            print(f"Starting lap {lap}...")
            for i, (lng, lat) in enumerate(ROUTE_COORDS):
                nxt = ROUTE_COORDS[(i + 1) % len(ROUTE_COORDS)]
                hdg = heading_deg(lat, lng, nxt[1], nxt[0])
                current_speed = next_speed_kph(rng, current_speed, args)
                event_ts = datetime.now(tz=UTC)
                scenario = maybe_alert_scenario(rng, args)
                send_lat, send_lng, send_speed, event_ts, alert_attributes = apply_alert_scenario(
                    scenario,
                    rng=rng,
                    lat=lat,
                    lng=lng,
                    speed=current_speed,
                    timestamp=event_ts,
                    args=args,
                )
                payload = [{
                    "imei": args.imei,
                    "latitude": send_lat,
                    "longitude": send_lng,
                    "speed": send_speed,
                    "heading": hdg,
                    "ignition": True,
                    "timestamp": event_ts.isoformat().replace("+00:00", "Z"),
                    # keep in payload for downstream systems that inspect raw fields
                    "vehicle_id": args.vehicle_id,
                    "device_id": args.device_id,
                    "attributes": {
                        "vehicle_id": args.vehicle_id,
                        "device_id": args.device_id,
                        **alert_attributes,
                    },
                }]
                if scenario:
                    print(f"[{lap}:{i}] injected alert={scenario} speed={send_speed} lat={send_lat:.6f} lng={send_lng:.6f}")
                try:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code >= 300:
                        print(f"[{lap}:{i}] HTTP {resp.status_code} -> {resp.text[:200]}")
                except Exception as exc:
                    print(f"[{lap}:{i}] send failed: {exc}")

                await asyncio.sleep(args.point_interval_sec)
            await _create_weighments_for_completed_route(client, args, rng, weighment_context, lap)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Loop truck movement over a fixed route via webhook")
    parser.add_argument("--base-url", default="http://127.0.0.1:9001", help="Ingestion API base URL")
    parser.add_argument("--vendor-id", default="vendor_a", help="X-Vendor-Id header value")
    parser.add_argument("--imei", default="990000000000000")
    parser.add_argument("--vehicle-id", default="LT-TRK-001")
    parser.add_argument("--device-id", default="9cc9c071-5349-4eca-a63e-a5d4563a588c")
    parser.add_argument("--speed-kph", type=float, default=28.0, help="Normal cruising baseline speed")
    parser.add_argument("--speed-fluctuation-kph", type=float, default=18.0, help="Normal speed varies around baseline by this amount")
    parser.add_argument("--min-speed-kph", type=float, default=4.0, help="Minimum generated normal speed")
    parser.add_argument("--max-normal-speed-kph", type=float, default=62.0, help="Maximum generated non-overspeed speed")
    parser.add_argument("--overspeed-chance", type=float, default=0.12, help="Chance per point to emit an overspeed value")
    parser.add_argument("--overspeed-min-kph", type=float, default=82.0, help="Minimum generated overspeed")
    parser.add_argument("--overspeed-max-kph", type=float, default=96.0, help="Maximum generated overspeed")
    parser.add_argument("--inject-alerts", action="store_true", help="Enable random simulated alert/anomaly markers")
    parser.add_argument(
        "--alert-scenarios",
        default="overspeeding,excessive_idle,route_deviation,missed_pickup,unauthorized_stop,unauthorized_halt,speed_anomaly,speed_violation,geofence_breach,gps_signal_loss,vehicle_offline",
        help="Comma-separated alert scenarios to randomly inject",
    )
    parser.add_argument("--alert-chance", type=float, default=0.08, help="Chance per point to inject one alert scenario when --inject-alerts is enabled")
    parser.add_argument("--alert-speed-threshold-kph", type=float, default=80.0, help="Threshold metadata for speed alert scenarios")
    parser.add_argument("--alert-idle-seconds", type=int, default=240, help="Idle duration metadata for excessive_idle")
    parser.add_argument("--alert-halt-seconds", type=int, default=240, help="Halt duration metadata for stop/halt alerts")
    parser.add_argument("--route-deviation-offset-m", type=float, default=120.0, help="Coordinate offset for deviation/geofence scenarios")
    parser.add_argument("--gps-signal-loss-age-seconds", type=int, default=360, help="Backdate GPS signal loss events by this many seconds")
    parser.add_argument("--vehicle-offline-age-seconds", type=int, default=720, help="Backdate vehicle offline events by this many seconds")
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed for repeatable speed profile")
    parser.add_argument("--point-interval-sec", type=float, default=2.0)
    parser.add_argument("--timeout-sec", type=float, default=10.0)
    parser.add_argument("--webhook-secret", default="", help="Webhook secret value if ingestion webhook auth is enabled")
    parser.add_argument("--webhook-secret-header", default="X-Webhook-Secret", help="Webhook secret header name")
    parser.add_argument("--generate-weighments", action="store_true", help="Create dump yard weighments after each completed lap when local time is after --weighment-start-hour")
    parser.add_argument("--admin-api-url", default="http://127.0.0.1:9003", help="Admin API base URL for weighment creation")
    parser.add_argument("--admin-username", default="admin", help="Admin API username for weighment creation")
    parser.add_argument("--admin-password", default="admin123", help="Admin API password for weighment creation")
    parser.add_argument("--weighment-vehicle-search", default="", help="Optional search text for matching the vehicle in Admin API")
    parser.add_argument("--dump-yard-id", default="", help="Optional dump yard UUID override")
    parser.add_argument("--weighment-start-hour", type=int, default=14, help="Local hour after which simulated weighments are generated")
    parser.add_argument("--weighment-days-back", type=int, default=1, help="Generate records from this many days back through today")
    parser.add_argument(
        "--weighment-materials",
        default="wet_waste,dry_waste,plastic_waste,construction_waste,mixed_waste,biomedical_waste",
        help="Comma-separated material types for simulated weighments",
    )
    parser.add_argument("--weighment-tare-min-kg", type=float, default=2200.0, help="Minimum simulated tare weight")
    parser.add_argument("--weighment-tare-max-kg", type=float, default=5200.0, help="Maximum simulated tare weight")
    parser.add_argument("--weighment-lap-spacing-min", type=int, default=17, help="Minutes between weighments for consecutive completed laps")
    parser.add_argument("--weighment-entry-spacing-min", type=int, default=19, help="Minutes between generated historical service-day entries")

    args = parser.parse_args()
    asyncio.run(run(args))
