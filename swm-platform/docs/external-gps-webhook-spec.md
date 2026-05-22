# GPS Telemetry Provider Integration Guide

This document is for external telemetry providers who will push live GPS data
into SWM.

## Production Webhook

- Method: `POST`
- Live URL: `https://ingestion-swm.zentrixel.com/webhook/gps`
- Content-Type: `application/json`

## Required Headers

- `X-Vendor-Id`: provider identifier (example: `vendor_a`)

## Recommended Headers

- `X-Request-Id`: unique ID per HTTP request for tracing and support
- `X-Trace-Id`: optional end-to-end trace ID

## Request Body Contract

The request body must be a JSON array. Each array item is one GPS event.

### Required Fields Per Event

- `imei`: string of 14 to 17 numeric digits
- `latitude`: float in range `-90` to `90`
- `longitude`: float in range `-180` to `180`
- `timestamp`: one of:
  - ISO-8601 UTC string (recommended), example: `2026-05-20T12:45:30Z`
  - epoch seconds
  - epoch milliseconds

### Optional Fields Per Event

- `speed`: `0` to `320` (km/h)
- `heading`: `0` to `359`
- `ignition`: boolean
- `odometer`: non-negative number
- `fuel_level`: `0` to `100`

### Accepted Aliases

Preferred keys are the canonical names above, but these aliases are accepted:

- `lat` -> `latitude`
- `lng` or `lon` -> `longitude`
- `ts`, `event_time`, `eventTime`, `gpsTime`, `time`, `datetime` -> `timestamp`
- `acc` or `acc_status` -> `ignition`

## Sample Payload

```json
[
  {
    "imei": "990000000000001",
    "latitude": 28.6139,
    "longitude": 77.2090,
    "speed": 34.5,
    "heading": 102,
    "ignition": true,
    "odometer": 12345.67,
    "fuel_level": 62.3,
    "timestamp": "2026-05-20T12:45:30Z"
  },
  {
    "imei": "990000000000002",
    "latitude": 28.6141,
    "longitude": 77.2092,
    "speed": 0.5,
    "heading": 250,
    "ignition": true,
    "timestamp": 1779271531000
  }
]
```

## cURL Example (Ready To Use)

The command below is for bash/zsh terminals (Linux/macOS/Git Bash):

```bash
curl -X POST "https://ingestion-swm.zentrixel.com/webhook/gps" \
  -H "Content-Type: application/json" \
  -H "X-Vendor-Id: vendor_a" \
  -H "X-Request-Id: provider-batch-20260520-0001" \
  --data '[
    {
      "imei":"990000000000001",
      "latitude":28.6139,
      "longitude":77.2090,
      "speed":34.5,
      "heading":102,
      "ignition":true,
      "timestamp":"2026-05-20T12:45:30Z"
    }
  ]'
```

## Windows PowerShell Examples (Tested)

Use `curl.exe` (not `curl`) in PowerShell.

### Option A: Inline JSON in PowerShell

```powershell
curl.exe -sS -i -X POST "https://ingestion-swm.zentrixel.com/webhook/gps" `
  -H "Content-Type: application/json" `
  -H "X-Vendor-Id: vendor_a" `
  -H "X-Request-Id: provider-batch-20260520-0001" `
  --data-raw "[{\"imei\":\"990000000000001\",\"latitude\":28.6139,\"longitude\":77.2090,\"speed\":34.5,\"heading\":102,\"ignition\":true,\"timestamp\":\"2026-05-20T12:45:30Z\"}]"
```

### Option B: JSON File (Recommended on Windows)

Create payload file without BOM:

```powershell
$payload = '[{"imei":"990000000000001","latitude":28.6139,"longitude":77.2090,"speed":34.5,"heading":102,"ignition":true,"timestamp":"2026-05-20T12:45:30Z"}]'
[System.IO.File]::WriteAllText("payload.json", $payload)
```

Send request:

```powershell
curl.exe -sS -i -X POST "https://ingestion-swm.zentrixel.com/webhook/gps" `
  -H "Content-Type: application/json" `
  -H "X-Vendor-Id: vendor_a" `
  -H "X-Request-Id: provider-batch-20260520-0001" `
  --data-binary "@payload.json"
```

Expected success status: `HTTP/1.1 202 Accepted`

## Success Response

On accepted requests, API returns `202 Accepted`.

Example:

```json
{
  "accepted": 100,
  "published": 100,
  "rejected": 0,
  "stream": "gps.telemetry.raw",
  "request_id": "provider-batch-20260520-0001",
  "latency_ms": 18.42,
  "error_summary": {
    "validation": {"failed": 0, "error_counts": {}, "samples": []},
    "normalization": {"failed": 0, "samples": []},
    "publish": {"failed": 0, "samples": []}
  }
}
```

## Error Response

If body is not a JSON array, API returns `422 Unprocessable Entity`:

```json
{
  "error": "Request body must be a JSON array"
}
```

## Provider-side Best Practices

- Send events in batches (recommended 20 to 500 events/request).
- Include `X-Request-Id` and keep it unique for each request.
- Use UTC timestamps.
- Retry on network errors and `5xx` responses with exponential backoff.
- For `202` with non-zero `rejected`, check payload quality for rejected items.

## Go-live Checklist

- Confirm your `X-Vendor-Id` value with SWM team.
- Share your source IPs if allow-listing is enabled.
- Send a pilot batch and confirm `published > 0`.
- Validate latency and success rate during peak traffic.
