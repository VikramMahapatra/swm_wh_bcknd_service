# Redis Streams Architecture: Fleet GPS Platform

## Overview

This document describes the Redis Streams topology for the SWM Fleet GPS platform. The design supports high-throughput GPS telemetry ingestion, reliable job processing, and event-driven alert handling with retry semantics and dead-letter queuing.

## Stream Topology

### Primary Streams

#### 1. `gps.telemetry.raw`
**Purpose:** Entry point for all incoming GPS telemetry from devices.

```
Properties:
  maxlen: 100,000 (approximate, using ~ policy)
  retention: 1 hour (implicit via consumer lag)
  
Consumer Groups:
  - ingestion-api:telemetry-processor    → validates & normalizes
  - analytics-worker:telemetry-consumer   → processes events
  - replay-worker:telemetry-archiver      → archives to cold storage
```

**Message Schema:**
```json
{
  "device_id": "uuid",
  "imei": "string",
  "timestamp": "ISO8601",
  "latitude": "float",
  "longitude": "float",
  "speed_kph": "float",
  "heading": "int",
  "accuracy": "float",
  "battery_percent": "float",
  "attributes": {"key": "value"}
}
```

---

#### 2. `gps.telemetry.retry`
**Purpose:** Temporary holding stream for messages that failed processing and are awaiting retry.

```
Properties:
  maxlen: 50,000 (smaller, temporary queue)
  retention: 30 minutes
  
Consumer Groups:
  - retry-worker:telemetry-retry-processor → attempts reprocessing with backoff
```

**Message Schema** (wraps original message with retry metadata):
```json
{
  "original_id": "stream-entry-id",
  "payload": { ... gps.telemetry.raw message ... },
  "retry_count": 0,
  "last_error": "error message",
  "backoff_until": "ISO8601 timestamp",
  "attempted_consumer": "string"
}
```

---

#### 3. `gps.telemetry.failed`
**Purpose:** Dead-letter queue (DLQ) for telemetry that permanently failed all retries.

```
Properties:
  maxlen: 10,000 (permanent archive)
  retention: 72 hours
  
Consumer Groups:
  - dlq-monitor:telemetry-failure-handler → alerts & metrics
```

**Message Schema** (enriched with failure details):
```json
{
  "original_id": "stream-entry-id",
  "payload": { ... original message ... },
  "retry_count": 3,
  "final_error": "error message",
  "failed_at": "ISO8601",
  "failure_reason": "max_retries_exceeded | validation_error | permanent_error",
  "last_consumer": "string",
  "debug_info": {}
}
```

---

#### 4. `analytics.jobs`
**Purpose:** Job queue for asynchronous analytics processing tasks.

```
Properties:
  maxlen: 50,000
  retention: 24 hours
  
Consumer Groups:
  - analytics-worker:job-processor       → processes analytics jobs
  - scheduler:job-monitor                → tracks job completion
```

**Message Schema:**
```json
{
  "job_id": "uuid",
  "job_type": "route_optimization | heatmap_generation | utilization_report",
  "parameters": {...},
  "priority": 1-10,
  "scheduled_for": "ISO8601",
  "created_at": "ISO8601"
}
```

---

#### 5. `report.jobs`
**Purpose:** Job queue for report generation and export tasks.

```
Properties:
  maxlen: 30,000
  retention: 24 hours
  
Consumer Groups:
  - report-worker:job-processor          → generates reports
  - storage-worker:report-archiver       → stores results
```

**Message Schema:**
```json
{
  "report_id": "uuid",
  "report_type": "daily_summary | fleet_overview | incident_log",
  "filters": {"contractor_id": "uuid", "date_range": {}},
  "output_format": "pdf | csv | json",
  "requested_by": "user-id",
  "created_at": "ISO8601"
}
```

---

#### 6. `alert.events.stream`
**Purpose:** Stream of alert events triggered by rule evaluations and thresholds.

```
Properties:
  maxlen: 100,000
  retention: 7 days
  
Consumer Groups:
  - alert-worker:event-processor         → triggers notifications
  - notification-service:event-dispatcher → sends alerts to users
```

**Message Schema:**
```json
{
  "alert_id": "uuid",
  "alert_type": "geofence_breach | speed_violation | battery_low | offline",
  "severity": "critical | warning | info",
  "device_id": "uuid",
  "vehicle_id": "uuid",
  "triggered_at": "ISO8601",
  "context": {"rule_id": "uuid", "threshold": "value"},
  "recipients": ["user-id", "group-id"]
}
```

---

#### 7. `replay.jobs`
**Purpose:** Job queue for replay/recovery of historical data or failed batches.

```
Properties:
  maxlen: 20,000
  retention: 30 days (longer, for audit trail)
  
Consumer Groups:
  - replay-worker:job-processor          → executes replay logic
  - audit-logger:job-tracker             → logs completion
```

**Message Schema:**
```json
{
  "replay_id": "uuid",
  "replay_type": "device_events | telemetry_backfill | analytics_recalculation",
  "start_time": "ISO8601",
  "end_time": "ISO8601",
  "filter": {"device_ids": [], "contractor_ids": []},
  "target_stream": "string",
  "initiated_by": "user-id",
  "created_at": "ISO8601"
}
```

---

## Consumer Group Strategy

### Group Creation & Management

```
For each stream + consumer group pair:
  XGROUP CREATE <stream> <group> $ MKSTREAM
  
Example:
  XGROUP CREATE gps.telemetry.raw ingestion-api:telemetry-processor $ MKSTREAM
```

### Processing Semantics

**At-Least-Once Delivery:**
- Consumer reads message: `XREADGROUP GROUP <group> <consumer> STREAMS <stream> >`
- Consumer processes message
- Consumer acknowledges: `XACK <stream> <group> <message-id>`

**If processing fails:**
1. Message stays in pending entry list (PEL)
2. After configurable timeout (e.g., 5 minutes), claimed by retry handler
3. Moved to retry stream with backoff
4. After max retries, moved to DLQ

### Consumer Configuration

```python
# Example consumer lifecycle:
consumer_config = {
    "group_name": "ingestion-api:telemetry-processor",
    "consumer_name": f"pod-{pod_id}-{instance_id}",
    "batch_size": 100,
    "block_ms": 1000,
    "claim_timeout_ms": 300_000,  # 5 minutes
    "idle_callback_interval_ms": 10_000,
}
```

---

## Retry Strategy

### Exponential Backoff with Jitter

```python
def calculate_backoff(retry_count: int, max_retries: int = 3) -> int:
    """
    Exponential backoff: 1s, 4s, 16s (with jitter)
    
    retry_count=0 → 1s + jitter
    retry_count=1 → 4s + jitter
    retry_count=2 → 16s + jitter
    retry_count=3 → move to DLQ
    """
    if retry_count >= max_retries:
        return None  # Move to DLQ
    
    base_delay = 2 ** (2 * retry_count)  # 1, 4, 16
    jitter = random.uniform(0, base_delay * 0.1)
    return int(base_delay + jitter)
```

### Retry Flow

```
1. Message enters primary stream (gps.telemetry.raw)
2. Consumer processes; if fails:
   → XADD gps.telemetry.retry <retry_message_with_metadata>
   → No ACK on primary stream
   
3. After claim_timeout_ms:
   → Retry handler claims pending entry
   → Checks backoff_until timestamp
   → If backoff passed, re-adds to primary stream
   → Otherwise, keeps in retry stream for next cycle
   
4. After max_retries:
   → XADD gps.telemetry.failed <failure_metadata>
   → Alert monitoring on DLQ threshold
```

---

## Dead-Letter Handling

### DLQ Monitoring

```python
# Threshold alerts
max_dlq_length = 1000
dlq_age_threshold_hours = 24

# Trigger alert if:
#   - gps.telemetry.failed length > 1000
#   - Any message in DLQ older than 24h
```

### DLQ Processing

```
Daily batch:
  1. XREAD COUNT 100 STREAMS gps.telemetry.failed 0
  2. For each failed message:
     - Log to error tracking system
     - Extract root cause
     - Tag for manual review or automatic remediation
  3. Archive older than 7 days to cold storage (database/S3)
```

---

## Monitoring & Metrics

### Key Metrics (exported to Prometheus)

```
# Stream sizes
redis_stream_length{stream="gps.telemetry.raw"}
redis_stream_length{stream="gps.telemetry.failed"}

# Consumer group lag
redis_consumer_group_lag{stream="gps.telemetry.raw", group="ingestion-api:telemetry-processor"}
redis_consumer_group_pending{stream="gps.telemetry.raw", group="ingestion-api:telemetry-processor"}

# Processing rates
redis_stream_rate{stream="gps.telemetry.raw", operation="added"}
redis_stream_rate{stream="gps.telemetry.retry", operation="added"}
redis_stream_rate{stream="gps.telemetry.failed", operation="added"}

# Retry metrics
redis_retry_attempts{stream="gps.telemetry.raw", retry_count=0}
redis_retry_attempts{stream="gps.telemetry.raw", retry_count=3}  # DLQ moves

# Processing duration
redis_stream_processing_duration_seconds{stream="gps.telemetry.raw", consumer_group="..."}
```

### Alerting Rules

```
# High consumer lag
alert: StreamConsumerLagHigh
  if redis_consumer_group_lag{stream="gps.telemetry.raw"} > 10000
  for 5m

# DLQ growth
alert: DLQGrowth
  if redis_stream_length{stream="gps.telemetry.failed"} > 1000
  for 10m

# Consumer offline
alert: ConsumerOffline
  if redis_consumer_group_pending{group="ingestion-api:telemetry-processor"} > 1000
    and timestamp(now()) - timestamp(last_claim) > 5m
```

---

## TTL & Retention Policy

### Stream Trimming

All streams use approximate trimming (`MAXLEN ~ <count>`) for performance:

```
# Telemetry streams: trim every 5 minutes
Redis command: XTRIM <stream> MAXLEN ~ <maxlen>

# Schedule via background task or stream processors
```

### Retention Summary

| Stream                   | MAXLEN | Retention | TTL  |
|--------------------------|--------|-----------|------|
| gps.telemetry.raw        | 100k   | 1 hour    | Auto |
| gps.telemetry.retry      | 50k    | 30 min    | Auto |
| gps.telemetry.failed     | 10k    | 72 hours  | Auto |
| analytics.jobs           | 50k    | 24 hours  | Auto |
| report.jobs              | 30k    | 24 hours  | Auto |
| alert.events.stream      | 100k   | 7 days    | Auto |
| replay.jobs              | 20k    | 30 days   | Auto |

---

## Python Client Wrapper

See: `libs/redis/src/swm_redis/streams/` for the production wrapper implementation.

### Quick Start

```python
from swm_redis.streams import StreamTopology

# Initialize
topology = StreamTopology(redis_url=settings.redis_url)
await topology.initialize()

# Publish telemetry
await topology.publish_telemetry(device_id, latitude, longitude, ...)

# Consume with automatic retries
consumer = topology.create_consumer(
    stream="gps.telemetry.raw",
    group="ingestion-api:telemetry-processor",
    consumer_name="pod-1",
)

async for message in consumer.read_stream(batch_size=100):
    try:
        await process(message)
        await consumer.ack(message)
    except TemporaryError:
        await topology.enqueue_retry(message)
    except PermanentError:
        await topology.enqueue_dlq(message)
```

---

## Deployment Checklist

- [ ] Redis version ≥ 5.0 (Stream support)
- [ ] Configure maxmemory policy: `allkeys-lru`
- [ ] Enable persistence: AOF for critical streams
- [ ] Set up Prometheus scraping for custom metrics
- [ ] Configure alerting thresholds (see Alerting section)
- [ ] Document consumer group ownership per service
- [ ] Create runbook for DLQ processing
- [ ] Test failover scenarios (consumer crashes, Redis restart)
- [ ] Load test with expected throughput (telemetry burst rates)

---

## References

- Redis Streams Documentation: https://redis.io/docs/data-types/streams/
- Consumer Groups: https://redis.io/docs/data-types/streams-tutorial/#consumer-groups-tutorial
- Recommended reading: "Building Reliable Systems with Redis Streams" (Salvatore Sanfilippo)
