# SWM Platform API Endpoints Reference

## Overview
This document is a practical API catalog for all current platform endpoints across:
- ingestion-api
- admin-api
- websocket-api

It includes purpose, auth requirements, parameters, and usage examples.

## Base URLs
- Local ingestion API: `http://127.0.0.1:9001`
- Local websocket API: `ws://127.0.0.1:9002`
- Local admin API: `http://127.0.0.1:9003`

## Authentication and Headers

### Admin API authentication
Supported auth mechanisms:
- `Authorization: Bearer <jwt>`
- `X-API-Key: <key>`
- Legacy fallback (when enabled): `X-Role: admin|ops|viewer|...`

Optional actor headers used for audit trails:
- `X-User`
- `X-Actor`

### Ingestion webhook authentication (optional, feature-flagged)
Depending on configuration:
- `X-Webhook-Secret`
- `X-Webhook-Signature`
- `X-Webhook-Nonce`
- `X-Vendor-Id`

### WebSocket authentication (optional, feature-flagged)
When `WEBSOCKET_AUTH_REQUIRED=true`, provide either:
- `token` query parameter, or
- `Authorization: Bearer <jwt>`

## Common Parameter Patterns

### Pagination
Most list endpoints use:
- `page` (>=1)
- `page_size` (bounded per endpoint)

### Sorting
Most master-data list endpoints support:
- `sort_by`
- `sort_order=asc|desc`

### Time filters
Analytics/operations endpoints commonly use:
- `from_ts`, `to_ts` (datetime)
- `date_from`, `date_to` (date)

### Export formats
Some endpoints support file export via `export`:
- `json`
- `csv`
- `xlsx`
- `pdf`

## Ingestion API Endpoints

### GET /healthz
Purpose: Service health check.
Parameters: None.
Usage:
```bash
curl http://127.0.0.1:9001/healthz
```

### GET /metrics
Purpose: Prometheus metrics endpoint.
Parameters: None.
Usage:
```bash
curl http://127.0.0.1:9001/metrics
```

### POST /v1/events
Purpose: Publish generic event batches to Redis pub/sub channel `telemetry.events`.
Body:
- `events`: array of device events (1..1000)
Usage:
```bash
curl -X POST http://127.0.0.1:9001/v1/events \
  -H "Content-Type: application/json" \
  -d '{"events":[{"device_id":"dev-1","imei":"123456789012345","event_ts":"2026-05-22T10:00:00Z","lat":18.52,"lng":73.85}]}'
```

### POST /webhook/gps
Purpose: Ingest vendor GPS fixes array, validate, normalize, and push to `gps.telemetry.raw` stream.
Headers:
- `X-Vendor-Id` (optional, default `unknown`)
- `X-Request-Id` (optional)
- `X-Trace-Id` (optional)
Body:
- JSON array of GPS fix objects
- Typical fields: `imei`, `latitude`, `longitude`, `timestamp`, `speed`, `heading`, `ignition`, `odometer`, `fuel_level`
Usage:
```bash
curl -X POST http://127.0.0.1:9001/webhook/gps \
  -H "Content-Type: application/json" \
  -H "X-Vendor-Id: vendor_a" \
  -d '[{"imei":"123456789012345","latitude":18.52,"longitude":73.85,"timestamp":"2026-05-22T10:00:00Z"}]'
```

## WebSocket API Endpoints

### GET /healthz
Purpose: Service health check.
Usage:
```bash
curl http://127.0.0.1:9002/healthz
```

### GET /metrics
Purpose: Prometheus metrics endpoint.
Usage:
```bash
curl http://127.0.0.1:9002/metrics
```

### WS /ws/realtime
Purpose: Stream realtime updates from Redis pub/sub channel `live_updates`.
Auth: Optional JWT depending on `WEBSOCKET_AUTH_REQUIRED`.
Usage:
```text
ws://127.0.0.1:9002/ws/realtime
```
With token:
```text
ws://127.0.0.1:9002/ws/realtime?token=<jwt>
```

## Admin API Endpoints

### Authentication

#### POST /v1/auth/login
Purpose: Authenticate a database-backed user and issue JWT access + refresh tokens.
Auth: Public endpoint (no prior token required).
Body:
- `username` (required)
- `password` (required)

Response:
- `access_token`
- `refresh_token`
- `token_type` (`bearer`)
- `expires_in` (seconds)
- `refresh_expires_in` (seconds)
- `subject`
- `roles`
- `permissions`

Usage:
```bash
curl -X POST http://127.0.0.1:9003/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

#### GET /v1/auth/me
Purpose: Return the current authenticated principal and claims from the access token.
Auth: Requires a valid JWT in `Authorization: Bearer <jwt>` or the legacy admin auth header path.
Response:
- `active`
- `subject`
- `role`
- `roles`
- `permissions`

Usage:
```bash
curl http://127.0.0.1:9003/v1/auth/me \
  -H "Authorization: Bearer <jwt>"
```

#### POST /v1/auth/refresh
Purpose: Rotate a refresh token and issue a new JWT + refresh pair.
Body:
- `refresh_token`

#### POST /v1/auth/logout
Purpose: Revoke a refresh token.
Body:
- `refresh_token`

### User / Role Management

These endpoints require an admin JWT.

- `GET /v1/auth/users`
- `POST /v1/auth/users`
- `GET /v1/auth/users/{username}`
- `PATCH /v1/auth/users/{username}`
- `DELETE /v1/auth/users/{username}`
- `POST /v1/auth/users/{username}/roles/{role_key}`
- `DELETE /v1/auth/users/{username}/roles/{role_key}`
- `GET /v1/auth/roles`
- `POST /v1/auth/roles`
- `PATCH /v1/auth/roles/{role_key}`
- `DELETE /v1/auth/roles/{role_key}`
- `POST /v1/auth/roles/{role_key}/permissions/{permission_key}`
- `DELETE /v1/auth/roles/{role_key}/permissions/{permission_key}`
- `GET /v1/auth/permissions`
- `POST /v1/auth/permissions`

### System

#### GET /healthz
Purpose: Service health check.

#### GET /metrics
Purpose: Prometheus metrics endpoint.

#### GET /v1/platform/status
Purpose: Platform operational status and timestamp.

Usage:
```bash
curl http://127.0.0.1:9003/v1/platform/status -H "X-Role: admin"
```

### Realtime and Ingestion Observability

#### GET /v1/realtime/trucks
Purpose: Live map truck snapshot from realtime cache.
Role access: `admin|ops|viewer`
Query params:
- `limit` (1..50000)

#### GET /v1/ingestion/failures
Purpose: List quarantine and DLQ records from Redis streams.
Role access: `admin|ops|viewer`
Query params:
- `source=all|quarantine|dlq`
- `limit` (1..500)
- `vendor_id` (optional)
- `retryable` (optional)

Usage:
```bash
curl "http://127.0.0.1:9003/v1/ingestion/failures?source=dlq&limit=100" -H "X-Role: ops"
```

### Dashboard

#### GET /v1/dashboard/kpis
Purpose: Fleet KPI summary with optional filters and export.
Role access: `admin|ops|viewer`
Query params:
- `date_from`, `date_to`
- `contractor_id`, `route_id`, `ward_id`
- `zone_name`
- `export=json|csv|xlsx|pdf`

#### GET /v1/vehicles/{vehicle_id}/detail
Purpose: Full vehicle detail including assignment, state, history, alerts, telemetry snapshots.
Role access: `admin|ops|viewer`
Query params:
- `from_ts`, `to_ts`
- `history_limit` (1..1000)

#### GET /v1/vehicles/search
Purpose: Filtered vehicle search.
Role access: `admin|ops|viewer`
Query params:
- `page`, `page_size`
- `vehicle_number`, `imei`
- `contractor_id`, `route_id`, `zone_name`, `ward_id`
- `operational_status`
- `date_from`, `date_to`
- `alert_category`

Usage:
```bash
curl "http://127.0.0.1:9003/v1/vehicles/search?page=1&page_size=20&imei=123456" -H "X-Role: viewer"
```

### Analytics Event Feeds
Role access for all analytics endpoints: `admin|ops|viewer`

#### GET /analytics/trips
Query params: `started_from`, `started_to`, `vehicle_id`, `vendor_id`, `limit`

#### GET /analytics/idle-segments
Query params: `started_from`, `started_to`, `vehicle_id`, `vendor_id`, `limit`

#### GET /analytics/overspeed-events
Query params: `from_ts`, `to_ts`, `vehicle_id`, `vendor_id`, `limit`

#### GET /analytics/geofence-events
Query params: `from_ts`, `to_ts`, `vehicle_id`, `event_type`, `limit`

Usage:
```bash
curl "http://127.0.0.1:9003/analytics/trips?limit=100" -H "X-Role: viewer"
```

### Analytics Reports
Role access for all: `admin|ops|viewer`
Export support: `json|csv`

#### GET /analytics/reports/daily
#### GET /analytics/reports/monthly
#### GET /analytics/reports/quarterly
#### GET /analytics/reports/half-yearly
#### GET /analytics/reports/annual
Common query params:
- `date_from`, `date_to`
- `vehicle_id`, `vendor_id`
- `export`

Usage:
```bash
curl "http://127.0.0.1:9003/analytics/reports/daily?date_from=2026-05-01&date_to=2026-05-22&export=csv" -H "X-Role: viewer"
```

### Analytics Summaries
Role access: `admin|ops|viewer`

#### GET /analytics/vehicle-state
Query params: `limit`, `vehicle_id`

#### GET /analytics/vehicle-state/{vehicle_id}

#### GET /analytics/geofence-summary
Query params: `from_ts`, `to_ts`, `vehicle_id`, `geofence_code`, `limit`, `export=json|csv`

#### GET /analytics/vehicle-utilization
Query params: `date_from`, `date_to`, `vehicle_id`, `vendor_id`, `limit`, `export=json|csv`

#### GET /analytics/route-deviation-summary
Query params: `from_ts`, `to_ts`, `vehicle_id`, `limit`, `export=json|csv`

#### GET /analytics/fuel-efficiency
Query params: `date_from`, `date_to`, `vehicle_id`, `vendor_id`, `limit`, `export=json|csv`

#### GET /analytics/speed-analysis
Query params: `from_ts`, `to_ts`, `vehicle_id`, `vendor_id`, `limit`, `export=json|csv`

#### GET /analytics/idle-summary
Query params: `date_from`, `date_to`, `vehicle_id`, `vendor_id`, `limit`, `export=json|csv`

### Operations: Alerts, Config, Categories, Reports, Audit

#### GET /v1/alerts
Purpose: Alert listing with filters and export.
Role access: `admin|ops|viewer`
Query params:
- `page`, `page_size`
- `status`, `severity`, `category`, `vehicle_id`
- `from_ts`, `to_ts`
- `export=json|csv|xlsx|pdf`

#### POST /v1/alerts
Purpose: Create alert.
Role access: `admin|ops`
Body fields:
- `alert_type`, `category`, `title`
- Optional: `message`, `severity`, `vehicle_id`, `imei`, `contractor_id`, `route_id`, `ward_id`, `triggered_at`, `metadata`

#### POST /v1/alerts/{alert_id}/acknowledge
Role access: `admin|ops`
Body: `actor`, `notes`, `escalation_status` (optional)

#### POST /v1/alerts/{alert_id}/resolve
Role access: `admin|ops`
Body: `actor`, `notes`, `escalation_status` (optional)

#### POST /v1/alerts/{alert_id}/escalate
Role access: `admin|ops`
Body: `actor`, `notes`, `escalation_status` (optional)

#### GET /v1/alerts/{alert_id}/audit
Role access: `admin|ops|viewer`

#### GET /v1/configurations
Role access: `admin|ops|viewer`
Query params: `page`, `page_size`, `config_type`, `active`, `q`

#### POST /v1/configurations
Role access: `admin|ops`
Body: `config_key`, `config_type`, `description`, `value`, `active`

#### PUT /v1/configurations/{config_id}
Role access: `admin|ops`
Body: same as create.

#### DELETE /v1/configurations/{config_id}
Role access: `admin`

#### GET /v1/operational-categories
Role access: `admin|ops|viewer`
Query params: `page`, `page_size`, `q`, `active`

#### POST /v1/operational-categories
Role access: `admin|ops`
Body: `category_code`, `category_name`, `description`, `active`

#### PUT /v1/operational-categories/{category_id}
Role access: `admin|ops`
Body: same as create.

#### DELETE /v1/operational-categories/{category_id}
Role access: `admin`

#### GET /v1/reports/operations/export
Role access: `admin|ops|viewer`
Query params: `date_from`, `date_to`, `export=csv|xlsx|pdf|json`

#### GET /v1/audit-logs
Role access: `admin|ops|viewer`
Query params:
- `page`, `page_size`
- `entity_type`, `entity_id`, `actor`
- `from_ts`, `to_ts`

Usage:
```bash
curl "http://127.0.0.1:9003/v1/audit-logs?page=1&page_size=50" -H "X-Role: admin"
```

### Master Data APIs

All master-data list endpoints use pagination and filters.
All `import` endpoints expect `multipart/form-data` with `file` CSV upload.

#### Vendors
- `GET /vendors`
- `POST /vendors`
- `GET /vendors/{vendor_id}`
- `PUT /vendors/{vendor_id}`
- `DELETE /vendors/{vendor_id}`
- `POST /vendors/import`

Vendor body (`POST`/`PUT`):
- `vendor_code`, `vendor_name`
- Optional: `contact_person`, `email`, `phone`, `webhook_secret`, `signature_key`, `allowed_ips`, `auth_type`, `callback_format`, `active`, `metadata`

#### Devices
- `GET /devices`
- `POST /devices`
- `GET /devices/{device_id}`
- `PUT /devices/{device_id}`
- `DELETE /devices/{device_id}`
- `POST /devices/import`

Device body (`POST`/`PUT`):
- `vendor_id`, `imei`
- Optional: `serial_no`, `model`, `manufacturer`, `firmware_version`, `sim_number`, `installed_on`, `activated_on`, `last_seen`, `battery_percent`, `signal_strength`, `health_status`, `active`, `metadata`

#### Vehicles
- `GET /vehicles`
- `POST /vehicles`
- `GET /vehicles/{vehicle_id}`
- `PUT /vehicles/{vehicle_id}`
- `DELETE /vehicles/{vehicle_id}`
- `POST /vehicles/import`

Vehicle body (`POST`/`PUT`):
- `vehicle_number`, `registration_number`, `contractor_id`, `ward_id`
- Optional: `route_id`, `truck_type`, `capacity_kg`, `capacity_cubic_meter`, `fuel_type`, `operational_status`, `chassis_number`, `engine_number`, `manufacture_year`, `active`, `metadata`

#### Routes
- `GET /routes`
- `POST /routes`
- `GET /routes/{route_id}`
- `PUT /routes/{route_id}`
- `DELETE /routes/{route_id}`
- `POST /routes/import`

Route body (`POST`/`PUT`):
- `route_code`, `route_name`, `start_point`, `end_point`
- Optional: `expected_distance_km`, `expected_duration_min`, `active`

#### Geofences
- `GET /geofences`
- `POST /geofences`
- `GET /geofences/{geofence_id}`
- `PUT /geofences/{geofence_id}`
- `DELETE /geofences/{geofence_id}`
- `POST /geofences/import`

Geofence body (`POST`/`PUT`):
- `geofence_code`, `geofence_name`, `type`, `geometry_type`
- Optional: `center_lat`, `center_lng`, `radius_meter`, `polygon`, `ward_id`, `active`

#### Contractors
- `GET /contractors`
- `POST /contractors`
- `GET /contractors/{contractor_id}`
- `PUT /contractors/{contractor_id}`
- `DELETE /contractors/{contractor_id}`
- `POST /contractors/import`

Contractor body (`POST`/`PUT`):
- `contractor_code`, `contractor_name`
- Optional: `contact`, `sla_details`, `active`

#### Wards
- `GET /wards`
- `POST /wards`
- `GET /wards/{ward_id}`
- `PUT /wards/{ward_id}`
- `DELETE /wards/{ward_id}`
- `POST /wards/import`

Ward body (`POST`/`PUT`):
- `ward_code`, `ward_name`, `zone_name`
- Optional: `active`

#### Device Assignments
- `POST /device-assignments`
- `GET /device-assignments`
- `GET /device-assignments/{device_id}`
- `PUT /device-assignments/{device_id}`
- `DELETE /device-assignments/{device_id}`
- `POST /device-assignments/import`

Create assignment body (`POST /device-assignments`):
- `device_id`, `vehicle_id`
- Optional: `assigned_from`, `assigned_to`, `active`, `remarks`

Reassign query params (`PUT /device-assignments/{device_id}`):
- `vehicle_id` (required)
- `remarks` (optional)

Unassign query params (`DELETE /device-assignments/{device_id}`):
- `remarks` (optional)

Usage:
```bash
curl -X POST http://127.0.0.1:9003/vendors \
  -H "Content-Type: application/json" \
  -H "X-Role: admin" \
  -d '{"vendor_code":"VEN-001","vendor_name":"Acme GPS","allowed_ips":[],"auth_type":"header","callback_format":{},"active":true,"metadata":{}}'
```

## Role-wise Access Matrix

### Canonical role mapping
Admin API currently accepts legacy role aliases and normalizes them as follows:

| Legacy role value | Canonical role |
|---|---|
| `admin` | `admin` |
| `ops` / `operator` | `operator` |
| `viewer` / `readonly` / `read-only` / `read_only` | `read_only` |
| `fleet manager` / `fleet_manager` | `fleet_manager` |
| `supervisor` | `supervisor` |
| `analyst` | `analyst` |

Current endpoint guards in code use `admin`, `ops`, `viewer` aliases.

### Service-level access

| Service | Endpoint pattern | Access policy |
|---|---|---|
| ingestion-api | `GET /healthz`, `GET /metrics`, `POST /v1/events`, `POST /webhook/gps` | Open by default; optional webhook auth and rate limit by feature flags |
| websocket-api | `GET /healthz`, `GET /metrics` | Open |
| websocket-api | `WS /ws/realtime` | Open by default; JWT required when `WEBSOCKET_AUTH_REQUIRED=true` |
| admin-api | `GET /healthz`, `GET /metrics`, `GET /v1/platform/status`, `POST /v1/auth/login` | Open (no role guard) |

### Admin API exact endpoint matrix

| Method | Endpoint | Allowed roles |
|---|---|---|
| POST | `/v1/auth/login` | Public (no role required) |
| GET | `/v1/realtime/trucks` | `admin`, `ops`, `viewer` |
| GET | `/v1/ingestion/failures` | `admin`, `ops`, `viewer` |
| GET | `/v1/dashboard/kpis` | `admin`, `ops`, `viewer` |
| GET | `/v1/vehicles/{vehicle_id}/detail` | `admin`, `ops`, `viewer` |
| GET | `/v1/vehicles/search` | `admin`, `ops`, `viewer` |
| GET | `/analytics/trips` | `admin`, `ops`, `viewer` |
| GET | `/analytics/idle-segments` | `admin`, `ops`, `viewer` |
| GET | `/analytics/overspeed-events` | `admin`, `ops`, `viewer` |
| GET | `/analytics/geofence-events` | `admin`, `ops`, `viewer` |
| GET | `/analytics/reports/daily` | `admin`, `ops`, `viewer` |
| GET | `/analytics/reports/monthly` | `admin`, `ops`, `viewer` |
| GET | `/analytics/reports/quarterly` | `admin`, `ops`, `viewer` |
| GET | `/analytics/reports/half-yearly` | `admin`, `ops`, `viewer` |
| GET | `/analytics/reports/annual` | `admin`, `ops`, `viewer` |
| GET | `/analytics/vehicle-state` | `admin`, `ops`, `viewer` |
| GET | `/analytics/vehicle-state/{vehicle_id}` | `admin`, `ops`, `viewer` |
| GET | `/analytics/geofence-summary` | `admin`, `ops`, `viewer` |
| GET | `/analytics/vehicle-utilization` | `admin`, `ops`, `viewer` |
| GET | `/analytics/route-deviation-summary` | `admin`, `ops`, `viewer` |
| GET | `/analytics/fuel-efficiency` | `admin`, `ops`, `viewer` |
| GET | `/analytics/speed-analysis` | `admin`, `ops`, `viewer` |
| GET | `/analytics/idle-summary` | `admin`, `ops`, `viewer` |
| GET | `/v1/alerts` | `admin`, `ops`, `viewer` |
| POST | `/v1/alerts` | `admin`, `ops` |
| POST | `/v1/alerts/{alert_id}/acknowledge` | `admin`, `ops` |
| POST | `/v1/alerts/{alert_id}/resolve` | `admin`, `ops` |
| POST | `/v1/alerts/{alert_id}/escalate` | `admin`, `ops` |
| GET | `/v1/alerts/{alert_id}/audit` | `admin`, `ops`, `viewer` |
| GET | `/v1/configurations` | `admin`, `ops`, `viewer` |
| POST | `/v1/configurations` | `admin`, `ops` |
| PUT | `/v1/configurations/{config_id}` | `admin`, `ops` |
| DELETE | `/v1/configurations/{config_id}` | `admin` |
| GET | `/v1/operational-categories` | `admin`, `ops`, `viewer` |
| POST | `/v1/operational-categories` | `admin`, `ops` |
| PUT | `/v1/operational-categories/{category_id}` | `admin`, `ops` |
| DELETE | `/v1/operational-categories/{category_id}` | `admin` |
| GET | `/v1/reports/operations/export` | `admin`, `ops`, `viewer` |
| GET | `/v1/audit-logs` | `admin`, `ops`, `viewer` |
| GET | `/vendors` | `admin`, `ops`, `viewer` |
| POST | `/vendors` | `admin`, `ops` |
| GET | `/vendors/{vendor_id}` | `admin`, `ops`, `viewer` |
| PUT | `/vendors/{vendor_id}` | `admin`, `ops` |
| DELETE | `/vendors/{vendor_id}` | `admin` |
| POST | `/vendors/import` | `admin`, `ops` |
| GET | `/devices` | `admin`, `ops`, `viewer` |
| POST | `/devices` | `admin`, `ops` |
| GET | `/devices/{device_id}` | `admin`, `ops`, `viewer` |
| PUT | `/devices/{device_id}` | `admin`, `ops` |
| DELETE | `/devices/{device_id}` | `admin` |
| POST | `/devices/import` | `admin`, `ops` |
| GET | `/vehicles` | `admin`, `ops`, `viewer` |
| POST | `/vehicles` | `admin`, `ops` |
| GET | `/vehicles/{vehicle_id}` | `admin`, `ops`, `viewer` |
| PUT | `/vehicles/{vehicle_id}` | `admin`, `ops` |
| DELETE | `/vehicles/{vehicle_id}` | `admin` |
| POST | `/vehicles/import` | `admin`, `ops` |
| GET | `/routes` | `admin`, `ops`, `viewer` |
| POST | `/routes` | `admin`, `ops` |
| GET | `/routes/{route_id}` | `admin`, `ops`, `viewer` |
| PUT | `/routes/{route_id}` | `admin`, `ops` |
| DELETE | `/routes/{route_id}` | `admin` |
| POST | `/routes/import` | `admin`, `ops` |
| GET | `/geofences` | `admin`, `ops`, `viewer` |
| POST | `/geofences` | `admin`, `ops` |
| GET | `/geofences/{geofence_id}` | `admin`, `ops`, `viewer` |
| PUT | `/geofences/{geofence_id}` | `admin`, `ops` |
| DELETE | `/geofences/{geofence_id}` | `admin` |
| POST | `/geofences/import` | `admin`, `ops` |
| GET | `/contractors` | `admin`, `ops`, `viewer` |
| POST | `/contractors` | `admin`, `ops` |
| GET | `/contractors/{contractor_id}` | `admin`, `ops`, `viewer` |
| PUT | `/contractors/{contractor_id}` | `admin`, `ops` |
| DELETE | `/contractors/{contractor_id}` | `admin` |
| POST | `/contractors/import` | `admin`, `ops` |
| GET | `/wards` | `admin`, `ops`, `viewer` |
| POST | `/wards` | `admin`, `ops` |
| GET | `/wards/{ward_id}` | `admin`, `ops`, `viewer` |
| PUT | `/wards/{ward_id}` | `admin`, `ops` |
| DELETE | `/wards/{ward_id}` | `admin` |
| POST | `/wards/import` | `admin`, `ops` |
| POST | `/device-assignments` | `admin`, `ops` |
| GET | `/device-assignments/{device_id}` | `admin`, `ops`, `viewer` |
| PUT | `/device-assignments/{device_id}` | `admin`, `ops` |
| DELETE | `/device-assignments/{device_id}` | `admin`, `ops` |
| GET | `/device-assignments` | `admin`, `ops`, `viewer` |
| POST | `/device-assignments/import` | `admin`, `ops` |

## Error Semantics
- `401 Unauthorized`: missing/invalid auth token or API key
- `403 Forbidden`: authenticated but role not allowed
- `404 Not Found`: resource does not exist
- `422 Unprocessable Entity`: payload/schema validation failure
- `429 Too Many Requests`: rate limiter blocked request (if enabled)

## Recommendation
Use OpenAPI docs for live schema details in each service:
- `http://127.0.0.1:9001/docs`
- `http://127.0.0.1:9002/docs`
- `http://127.0.0.1:9003/docs`
