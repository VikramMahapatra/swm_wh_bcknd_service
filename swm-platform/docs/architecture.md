# SWM Fleet Telemetry Platform Architecture

## Throughput Targets
- 600 active GPS devices
- 600+ telemetry events per second
- Near-realtime fanout via Redis pub/sub and WebSocket API
- Durable storage for operational and analytical workloads

## Data Flow
1. Device payloads hit ingestion-api.
2. Ingestion publishes canonical events to Redis channel `telemetry.events`.
3. WebSocket API and workers subscribe asynchronously.
4. storage-worker persists to PostgreSQL and ClickHouse.
5. analytics-worker computes rollups.
6. alert-worker evaluates threshold and geofence rules.

## Operational Stack
- FastAPI async services for APIs
- Redis for low-latency fanout and ephemeral state
- PostgreSQL for transactional and admin data
- ClickHouse for high-volume historical analytics
- Prometheus + Grafana for observability
