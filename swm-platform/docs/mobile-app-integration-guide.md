# Mobile App Integration Guide

This guide is for the mobile team building fleet views on top of the SWM backend.

## Base URLs

- Admin API: `http://127.0.0.1:9003`
- WebSocket API: `ws://127.0.0.1:9002`
- Ingestion API: `http://127.0.0.1:9001`

For production, replace `127.0.0.1` with the deployed host name.

## Authentication

Most mobile reads use the admin API and require a JWT:

```http
Authorization: Bearer <access_token>
```

Allowed roles for the fleet read endpoints are typically `admin`, `ops`, and `viewer`.

## What To Call

### 1. Vehicle list with pagination

Use this when you need the fleet list screen.

`GET /v1/vehicles/search`

Query params:

- `page` - page number, starts at `1`
- `page_size` - items per page, up to `200`
- `vehicle_number`
- `imei`
- `vendor_id`
- `route_id`
- `zone_name`
- `ward_id`
- `operational_status`
- `date_from`
- `date_to`
- `alert_category`

Example:

```bash
curl "http://127.0.0.1:9003/v1/vehicles/search?page=1&page_size=20&zone_name=Zone%201" \
  -H "Authorization: Bearer <jwt>"
```

Response shape:

- `items` - array of vehicles
- `total` - total matching records
- `page`
- `page_size`

Important fields in each vehicle item:

- `id`
- `vehicle_number`
- `registration_number`
- `vehicle_category`
- `route_id`
- `route_name`
- `ward_id`
- `ward_name`
- `zone_id`
- `zone_name`
- `active`

### 2. Active / inactive vehicles

Use the same search endpoint and filter on `active`.

Examples:

```http
GET /v1/vehicles/search?page=1&page_size=20&active=true
GET /v1/vehicles/search?page=1&page_size=20&active=false
```

If the app needs a simple count summary, use:

`GET /v1/dashboard/kpis`

That returns:

- `active_vehicles`
- `inactive_vehicles`
- `idle_vehicles`
- `moving_vehicles`

### 3. Idle vehicles

There is no separate "idle list" endpoint, so use one of these:

- `GET /v1/dashboard/kpis` for the idle count
- `GET /analytics/vehicle-state` for per-vehicle current state
- `GET /v1/vehicles/{vehicle_id}/detail` for one vehicle with history

Idle is derived from analytics state, not from the master vehicle table alone.

### 4. Vehicle detail screen

Use this for the vehicle profile page.

`GET /v1/vehicles/{vehicle_id}/detail`

Query params:

- `from_ts`
- `to_ts`
- `history_limit` - default `100`, max `1000`

This response includes:

- `vehicle`
- `device_assignment`
- `device`
- `current_state`
- `trip_history`
- `idle_history`
- `route_history`
- `alerts`
- `telemetry_snapshots`

### 5. Zone list

`GET /zones`

This returns all zones as a plain array.

Zone fields:

- `id`
- `zone_code`
- `zone_name`
- `active`

### 6. Ward list

`GET /wards`

Query params:

- `page`
- `page_size`
- `q`
- `active`
- `zone_name`

Ward fields:

- `id`
- `ward_code`
- `ward_name`
- `zone_id`
- `active`

### 7. Route list and route coordinates

`GET /routes`

Query params:

- `page`
- `page_size`
- `q`
- `active`
- `ward_id`
- `zone_id`
- `ui_compat`

For mobile, `ui_compat=true` is useful because it returns route-friendly objects with coordinates:

- `id`
- `route_name`
- `zone_id`
- `ward_id`
- `polyline_coordinates`
- `estimated_distance`
- `estimated_time`

Example:

```bash
curl "http://127.0.0.1:9003/routes?page=1&page_size=20&ui_compat=true" \
  -H "Authorization: Bearer <jwt>"
```

Each route has `polyline_coordinates` as `[lng, lat]` pairs.

### 8. Live movement / live map

Use the live snapshot endpoint for the map screen:

`GET /v1/realtime/trucks`

Query params:

- `limit` - up to `50000`

This returns the latest live position per tracked truck, including:

- `imei`
- `device_id`
- `vehicle_id`
- `registration_number`
- `vehicle_number`
- `lat`
- `lng`
- `speed_kph`
- `heading`
- `ignition`
- `event_ts`
- `status`
- `zone_name`
- `ward_name`
- `route_name`
- `vehicle_category`
- `operational_status`

This is the best endpoint for the moving dots on the map.

### 9. Realtime push updates

If the mobile app wants push updates instead of polling, connect to:

`ws://127.0.0.1:9002/ws/realtime`

Auth:

- either `?token=<jwt>`
- or `Authorization: Bearer <jwt>`

The websocket streams JSON messages from Redis pub/sub channels.
The message envelope is:

```json
{
  "channel": "live_updates",
  "ts": "2026-06-24T10:00:00Z",
  "trace_id": "",
  "correlation_id": "",
  "source": "",
  "payload": {}
}
```

For live movement, listen for messages on `live_updates`.

## Recommended Mobile Flow

1. Load zones, wards, and routes first so dropdowns and filters are ready.
2. Call `GET /v1/vehicles/search` for the fleet list.
3. Call `GET /v1/dashboard/kpis` for active, inactive, idle, and moving counts.
4. Call `GET /v1/realtime/trucks` for the live map snapshot.
5. Open the websocket if the app needs near-real-time movement updates.
6. Use `GET /v1/vehicles/{vehicle_id}/detail` for drill-down on one vehicle.

## Example Mobile Headers

```http
Authorization: Bearer <jwt>
Content-Type: application/json
```

If the app is not using JWT for a public read surface, confirm that with backend before shipping; the current backend expects authenticated access on the admin API.
