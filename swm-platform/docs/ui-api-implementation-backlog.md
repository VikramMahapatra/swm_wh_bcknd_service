# UI API Implementation Backlog (garbage_vechile_tracking -> swm-platform)

Date: 2026-05-22

## Objective
Provide a build-ready endpoint backlog to align garbage_vechile_tracking UI with swm-platform APIs.

## Principles
- Prefer compatibility adapters first to make UI work fast.
- Reuse existing entities where possible (vehicles, wards, routes, alerts, auth).
- Add missing domain modules only where no equivalent exists.
- Keep contracts stable once exposed to UI.

## Phase 1: Compatibility Layer (highest impact, fastest delivery)

### 1. Auth compatibility
1. POST /auth/login-json
- Purpose: UI login endpoint alias.
- Backend mapping: delegate to POST /v1/auth/login.
- Request:
  - email: string
  - password: string
- Response:
  - access_token: string
  - refresh_token: string
  - token_type: string
  - expires_in: number
  - subject: string
  - roles: string[]
- Notes:
  - Accept email and map to username if needed.

2. GET /auth/me
- Purpose: UI profile endpoint alias.
- Backend mapping: delegate to GET /v1/auth/me.

3. GET /auth/users
- Purpose: UI users page listing alias.
- Backend mapping: delegate to GET /v1/auth/users.

4. POST /auth/register
- Purpose: UI create user alias.
- Backend mapping: delegate to POST /v1/auth/users.
- Request:
  - email: string
  - password: string
  - name: string
  - role: string

### 2. Alerts path compatibility
1. GET /alerts
- Purpose: UI alerts listing currently calls this path.
- Backend mapping: delegate to GET /v1/alerts.
- Query support:
  - status
  - severity
  - truck_id

2. GET /alerts/active
- Purpose: dashboard active alert panel.
- Backend mapping: GET /v1/alerts?status=active.

3. GET /alerts/expiry
- Purpose: dashboard expiry widget.
- Backend mapping: temporary computed response until expiry model exists.
- Response shape expected by UI:
  - items: any[]
  - total: number

### 3. Trucks compatibility
1. GET /trucks
- Purpose: UI central listing for master/reports/filters.
- Backend mapping:
  - Merge /v1/realtime/trucks + /vehicles metadata by normalized vehicle key.
- Query support:
  - zone_id
  - vendor_id
  - status

2. PUT /trucks/{truckId}/assign-route
- Purpose: UI master-trucks route assignment.
- Backend mapping:
  - Update vehicle.route_id in existing vehicles domain.
- Request:
  - assigned_route_id: string

3. GET /trucks/spare
- Purpose: spare vehicle management.
- Backend mapping:
  - Filter vehicles where is_spare=true or operational_status=spare.

### 4. Zone/Ward compatibility
1. GET /zones
- Purpose: populate zone filters.
- Backend mapping:
  - Aggregate distinct zone_name from /wards.
- Response suggested:
  - id: string
  - name: string
  - code: string
  - total_wards: number

2. GET /zones/{zoneId}/wards
- Purpose: zone-specific ward dropdowns.
- Backend mapping:
  - Filter /wards by zone_name.

### 5. Routes compatibility
1. GET /routes
- Purpose: UI route lists and filters.
- Backend mapping: existing /routes plus ward and zone enrichment.
- Query support:
  - zone_id
  - ward_id

## Phase 2: Core Missing Modules

### 6. Pickup points module
1. GET /pickup-points
- Query:
  - ward_id
  - route_id
- Response:
  - id, name, ward_id, route_id, lat, lng, type, active

2. GET /routes/{routeId}/pickup-points
- Response:
  - pickup points for selected route

Data model proposal:
- pickup_points
  - id UUID PK
  - pickup_code varchar unique
  - pickup_name varchar
  - ward_id UUID FK
  - route_id UUID FK nullable
  - lat numeric
  - lng numeric
  - category varchar
  - active boolean
  - created_at, updated_at

### 7. Drivers module
1. GET /drivers
2. GET /drivers/{driverId}
3. POST /drivers (optional if UI creates)
4. PUT /drivers/{driverId} (optional if UI edits)

Minimum response shape:
- id
- name
- phone
- license_number
- license_expiry
- vendor_id
- active

### 8. GTC checkpoints module
1. GET /gtc-checkpoints
- Query:
  - truck_id
  - date
  - date_from
  - date_to

2. POST /gtc-checkpoints
- Request:
  - truck_id
  - arrived_at
  - is_dry
  - is_wet
  - is_metal
  - is_plastic
  - is_sanitary
  - truck_cleanliness_score
  - gtc_cleanliness_score
  - remarks

Data model proposal:
- gtc_checkpoints
  - id bigserial PK
  - truck_id varchar
  - arrived_at timestamptz
  - is_dry boolean
  - is_wet boolean
  - is_metal boolean
  - is_plastic boolean
  - is_sanitary boolean
  - truck_cleanliness_score numeric
  - gtc_cleanliness_score numeric
  - remarks text
  - created_at timestamptz default now()

## Phase 3: Ticketing

### 9. Tickets API
1. GET /tickets
- Query:
  - status
  - priority
  - category

2. GET /tickets/{ticketId}
3. POST /tickets
4. PUT /tickets/{ticketId}
5. GET /tickets/{ticketId}/comments
6. POST /tickets/{ticketId}/comments
7. GET /tickets/statistics/summary

Minimum entities:
- tickets
- ticket_comments

## Phase 4: Reports and Analytics Contract Alignment

### 10. Reports endpoints expected by UI
1. GET /reports/data
2. GET /reports/statistics
3. GET /reports/zone-performance
4. GET /reports/vendor-performance
5. GET /reports/collection-efficiency

Implementation option A (recommended):
- Add adapter endpoints that compose from existing analytics and dashboard sources.

Implementation option B:
- Update UI to call existing analytics routes directly.

### 11. Analytics endpoints expected by UI
1. GET /analytics/performance/overview
2. GET /analytics/performance/zone-wise
3. GET /analytics/performance/vendor-wise
4. GET /analytics/predictions/maintenance
5. GET /analytics/trends/collection-rate

Recommendation:
- Build these as compatibility aliases backed by current analytics tables/services.

## Phase 5: Social and Optional Dashboards

### 12. Twitter/social endpoints
1. GET /social-media/twitter-mentions
2. GET /social-media/twitter-mentions/statistics/summary
3. PUT /social-media/twitter-mentions/{mentionId}/respond

### 13. Collection ton today endpoint (optional but useful)
1. GET /collection-ton-today
- Response:
  - zone
  - vehicle
  - weight

## Suggested Delivery Sprints

### Sprint 1 (1 week)
- Auth compatibility endpoints
- Alerts compatibility endpoints
- Trucks compatibility endpoints
- Zones and wards compatibility endpoints
- Routes compatibility endpoint normalization

### Sprint 2 (1 week)
- Pickup points module
- Drivers module
- GTC checkpoints module

### Sprint 3 (1 week)
- Tickets module
- Reports adapter endpoints

### Sprint 4 (1 week)
- Analytics adapter endpoints
- Social endpoints
- Collection-ton endpoint

## Acceptance Checklist
- All UI pages load without empty-stub fallback.
- No frontend path mismatch (auth, alerts, trucks, zones).
- Reports and analytics tabs show non-mock backend data.
- Ticket and GTC workflows complete create and read cycles.
- Basic API tests added for each new endpoint group.

## Testing Priority
1. Contract tests for compatibility aliases.
2. Integration tests for /trucks merge logic.
3. Filter correctness tests for zones, wards, routes, pickup points.
4. CRUD tests for tickets and GTC checkpoints.
5. Role access tests for auth and operations.
