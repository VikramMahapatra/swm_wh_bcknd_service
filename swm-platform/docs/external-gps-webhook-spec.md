# GPS Webhook Spec for External Senders

This document defines the payload and endpoint an external party should use to push GPS telemetry into the SWM platform.

## Webhook URL

Use the public ingestion endpoint exposed by your deployment:

- Preferred through Nginx: `POST /ingestion/webhook/gps`
- Direct ingestion API path: `POST /webhook/gps`

For local development in this repository:

- `http://localhost/ingestion/webhook/gps`
- `http://localhost:8001/webhook/gps`

If you have a public host name, replace `localhost` with that host.

## Method

- `POST`

## Headers

Required:

- `X-Vendor-Id`: vendor identifier string, for example `vendor_a`

Recommended:

- `X-Request-Id`: request tracing identifier
- `X-Trace-Id`: optional trace identifier; if omitted, the service will derive one

## Body Format

The request body must be a JSON array.

Each array item is one GPS event object.

### Required event fields

- `imei`: numeric string, 14 to 17 digits
- `latitude`: number between `-90` and `90`
- `longitude`: number between `-180` and `180`
- `timestamp`: ISO-8601 UTC string, or epoch seconds / milliseconds

### Optional event fields

- `speed`: `0` to `320`
- `heading`: `0` to `359`
- `ignition`: boolean
- `odometer`: non-negative number
- `fuel_level`: `0` to `100`

### Accepted aliases

The API also accepts some common aliases, but external senders should prefer the canonical names above.

- `lat` -> `latitude`
- `lng` / `lon` -> `longitude`
- `ts` / `event_time` / `time` -> `timestamp`
- `acc` / `acc_status` -> `ignition`

## Example Request

```json
[
  {
    "imei": "990000000000001",
    "latitude": 28.6139,
    "longitude": 77.209,
    "speed": 25.5,
    "heading": 90,
    "ignition": true,
    "odometer": 12345.6,
    "fuel_level": 61.2,
    "timestamp": "2026-05-09T10:00:00Z"
  },
  {
    "imei": "990000000000002",
    "latitude": 28.6141,
    "longitude": 77.2092,
    "speed": 32.7,
    "heading": 120,
    "ignition": true,
    "odometer": 22345.6,
    "fuel_level": 54.1,
    "timestamp": "2026-05-09T10:00:01Z"
  }
]
```

## Example cURL

```bash
curl -X POST "https://YOUR_PUBLIC_HOST/ingestion/webhook/gps" \
  -H "Content-Type: application/json" \
  -H "X-Vendor-Id: vendor_a" \
  -H "X-Request-Id: ext-test-0001" \
  --data @payload.json
```

## Response

The API returns `202 Accepted` with a JSON response containing:

- `accepted`
- `published`
- `rejected`
- `stream`
- `request_id`
- `latency_ms`
- `error_summary`

## Validation Notes

- The body must be a JSON array, not a single object.
- Invalid records are counted in `rejected`.
- `error_summary.validation.failed = 0` means the payload shape is valid.
- `error_summary.publish.failed > 0` means Redis publish pressure or transient backend failure, not bad payload format.

## Operational Notes

- Unknown extra fields are ignored.
- The handler is asynchronous and returns after validation and publish.
- No authentication header is currently enforced in the handler code.
