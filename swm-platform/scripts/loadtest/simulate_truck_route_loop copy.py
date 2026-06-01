import argparse
import asyncio
import json
import math
import random
from datetime import UTC, datetime
from typing import List, Tuple

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

    print(f"Sending GPS loop to {url} for IMEI={args.imei}, vehicle={args.vehicle_id}")
    print(f"Total points per lap: {len(ROUTE_COORDS)}")
    print(
        "Speed profile: "
        f"baseline={args.speed_kph} km/h, fluctuation=+/-{args.speed_fluctuation_kph} km/h, "
        f"overspeed_chance={args.overspeed_chance:.2f}, overspeed={args.overspeed_min_kph}-{args.overspeed_max_kph} km/h"
    )

    timeout = httpx.Timeout(args.timeout_sec)
    async with httpx.AsyncClient(timeout=timeout) as client:
        lap = 0
        while True:
            lap += 1
            print(f"Starting lap {lap}...")
            for i, (lng, lat) in enumerate(ROUTE_COORDS):
                nxt = ROUTE_COORDS[(i + 1) % len(ROUTE_COORDS)]
                hdg = heading_deg(lat, lng, nxt[1], nxt[0])
                current_speed = next_speed_kph(rng, current_speed, args)
                payload = [{
                    "imei": args.imei,
                    "latitude": lat,
                    "longitude": lng,
                    "speed": current_speed,
                    "heading": hdg,
                    "ignition": True,
                    "timestamp": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
                    # keep in payload for downstream systems that inspect raw fields
                    "vehicle_id": args.vehicle_id,
                    "device_id": args.device_id,
                    "attributes": {
                        "vehicle_id": args.vehicle_id,
                        "device_id": args.device_id,
                    },
                }]
                try:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code >= 300:
                        print(f"[{lap}:{i}] HTTP {resp.status_code} -> {resp.text[:200]}")
                except Exception as exc:
                    print(f"[{lap}:{i}] send failed: {exc}")

                await asyncio.sleep(args.point_interval_sec)


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
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed for repeatable speed profile")
    parser.add_argument("--point-interval-sec", type=float, default=2.0)
    parser.add_argument("--timeout-sec", type=float, default=10.0)
    parser.add_argument("--webhook-secret", default="", help="Webhook secret value if ingestion webhook auth is enabled")
    parser.add_argument("--webhook-secret-header", default="X-Webhook-Secret", help="Webhook secret header name")

    args = parser.parse_args()
    asyncio.run(run(args))
