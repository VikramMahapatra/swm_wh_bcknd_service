# Admin Operations Epic Traceability

## Scope
This document maps the admin operations epic stories to concrete API endpoints and persistence entities implemented in the platform.

## Story-to-API Mapping

### 1) Dashboard KPIs and utilization metrics
- GET /v1/dashboard/kpis
- Source entities: analytics_daily_kpis, analytics_vehicle_state, vehicles, routes, wards
- Output includes:
  - total_fleet_count
  - active_vehicles
  - inactive_vehicles
  - idle_vehicles
  - moving_vehicles
  - route_completion_pct
  - avg_utilization_pct
- Export formats: json, csv, xlsx, pdf

### 2) Detailed vehicle views (live state and histories)
- GET /v1/vehicles/{vehicle_id}/detail
- Source entities: vehicles, device_vehicle_assignments, devices, analytics_vehicle_state, analytics_trip_records, analytics_idle_records, analytics_geofence_events, alerts, device_events
- Output sections:
  - vehicle
  - device_assignment
  - device
  - current_state
  - trip_history
  - idle_history
  - route_history
  - alerts
  - telemetry_snapshots

### 3) Vehicle search and filters
- GET /v1/vehicles/search
- Filters supported:
  - vehicle_number
  - imei
  - contractor_id
  - route_id
  - zone_name
  - ward_id
  - operational_status
  - date_from/date_to
  - alert_category

### 4) Master CRUD APIs
- Vendors:
  - GET/POST /vendors
  - GET/PUT/DELETE /vendors/{vendor_id}
  - POST /vendors/import
- Devices:
  - GET/POST /devices
  - GET/PUT/DELETE /devices/{device_id}
  - POST /devices/import
- Vehicles:
  - GET/POST /vehicles
  - GET/PUT/DELETE /vehicles/{vehicle_id}
  - POST /vehicles/import
- Contractors:
  - GET/POST /contractors
  - GET/PUT/DELETE /contractors/{contractor_id}
  - POST /contractors/import
- Routes:
  - GET/POST /routes
  - GET/PUT/DELETE /routes/{route_id}
  - POST /routes/import
- Geofences:
  - GET/POST /geofences
  - GET/PUT/DELETE /geofences/{geofence_id}
  - POST /geofences/import
- Wards:
  - GET/POST /wards
  - GET/PUT/DELETE /wards/{ward_id}
  - POST /wards/import
- Device mapping:
  - POST /device-assignments
  - GET /device-assignments
  - GET /device-assignments/{device_id}
  - PUT /device-assignments/{device_id}
  - DELETE /device-assignments/{device_id}
  - POST /device-assignments/import
- Operational categories:
  - GET/POST /v1/operational-categories
  - PUT/DELETE /v1/operational-categories/{category_id}

### 5) Alert management and lifecycle
- GET /v1/alerts
- POST /v1/alerts
- POST /v1/alerts/{alert_id}/acknowledge
- POST /v1/alerts/{alert_id}/resolve
- POST /v1/alerts/{alert_id}/escalate
- GET /v1/alerts/{alert_id}/audit
- Source entities:
  - alerts
  - alert_actions
  - audit_logs

### 6) Configurations and rules
- GET /v1/configurations
- POST /v1/configurations
- PUT /v1/configurations/{config_id}
- DELETE /v1/configurations/{config_id}
- Source entity: system_configurations
- Supported configuration types:
  - speed_threshold
  - geofence
  - idle_threshold
  - alert_rule
  - webhook_secret
  - vendor_config
  - retention_policy

### 7) Operational reporting exports
- GET /v1/reports/operations/export
- Source entities:
  - analytics_daily_kpis
  - alerts
- Export formats: csv, xlsx, pdf, json

### 8) Audit logging and compliance
- GET /v1/audit-logs
- Automatic audit writes on:
  - alert lifecycle actions
  - configuration create/update/delete
- Source entity: audit_logs

## Persistence Added for this Epic
- operational_categories
- alerts
- alert_actions
- system_configurations
- audit_logs

## Migration
- Alembic revision: 0009_admin_operations_epic
- Upgrade path: 0008_analytics_engine -> 0009_admin_operations_epic

## Validation
- Focused suite executed: tests/test_admin_api.py
- Result: pass
