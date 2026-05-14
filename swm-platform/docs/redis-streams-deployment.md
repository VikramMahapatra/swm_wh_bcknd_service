# Redis Streams Deployment Guide

## Summary

The Redis Streams topology has been fully designed and implemented for the Fleet GPS platform. It provides a production-ready event streaming and job processing system.

## Deliverables

### 1. Architecture Documentation
- **File**: [redis-streams-architecture.md](./redis-streams-architecture.md)
- **Contents**:
  - 7 stream definitions with schemas
  - Consumer group strategy per stream
  - Retry strategy with exponential backoff
  - Dead-letter handling and recovery
  - Monitoring metrics and alerting rules
  - TTL and retention policies

### 2. Python Implementation
- **File**: [libs/redis/src/swm_redis/streams.py](../libs/redis/src/swm_redis/streams.py)
- **Exports**: `StreamTopology`, `StreamConfig`, `ConsumerGroupConfig`, `StreamMessage`, `StreamConsumer`
- **Lines**: ~600 LOC
- **Coverage**:
  - Stream initialization with consumer groups
  - Publishing API for telemetry, jobs, and alerts
  - Consumer reading with batch support
  - Automatic retry with exponential backoff
  - Dead-letter queue management
  - Stream and consumer group monitoring

### 3. Comprehensive Tests
- **File**: [libs/redis/src/swm_redis/test_streams.py](../libs/redis/src/swm_redis/test_streams.py)
- **Test Count**: 15 unit tests
- **Coverage**:
  - Stream initialization
  - Publishing (telemetry, jobs, alerts)
  - Retry logic and backoff calculation
  - DLQ handling
  - Consumer group stats
  - Message acknowledgment

### 4. Usage Examples
- **File**: [redis-streams-examples.py](./redis-streams-examples.py)
- **Examples**:
  1. Publishing GPS telemetry from 100 devices
  2. Consuming with automatic retry and DLQ handling
  3. Dedicated retry worker with backoff
  4. Job publishing and consuming (analytics, reports)
  5. Alert publishing and monitoring
  6. Stream and consumer group statistics

### 5. Quick Start Guide
- **File**: [redis-streams-quickstart.md](./redis-streams-quickstart.md)
- **Contents**:
  - 5-minute startup
  - Stream reference
  - Retry strategy explanation
  - Consumer group patterns
  - Monitoring and alerting
  - Troubleshooting guide
  - Performance tuning
  - Production checklist

## Stream Topology

### Primary Streams

```
gps.telemetry.raw (100k maxlen)
  ├─ ingestion-api:telemetry-processor
  ├─ analytics-worker:telemetry-consumer
  └─ replay-worker:telemetry-archiver

gps.telemetry.retry (50k maxlen)
  └─ retry-worker:telemetry-retry-processor

gps.telemetry.failed (10k maxlen) [DLQ]
  └─ dlq-monitor:telemetry-failure-handler

analytics.jobs (50k maxlen)
  └─ analytics-worker:job-processor

report.jobs (30k maxlen)
  └─ report-worker:job-processor

alert.events.stream (100k maxlen)
  ├─ alert-worker:event-processor
  └─ notification-service:event-dispatcher

replay.jobs (20k maxlen)
  └─ replay-worker:job-processor
```

### Message Flow Diagram

```
┌─────────────────┐
│  GPS Device     │
└────────┬────────┘
         │
         ▼
   ┌───────────────────────────────────┐
   │  gps.telemetry.raw                │
   │  (100k maxlen, 1h retention)      │
   └───┬───────────┬───────────┬───────┘
       │           │           │
       ▼           ▼           ▼
   ┌────────┐  ┌────────┐  ┌────────┐
   │Ingest  │  │Analyt. │  │Replay  │
   │Proc.   │  │Worker  │  │Worker  │
   └────┬───┘  └───┬────┘  └───┬────┘
        │          │           │
        ├─ fail ─┬─┤           │
        │        ▼ ▼           │
        │   ┌─────────────┐    │
        │   │  RETRY LOOP │    │
        │   │  (1s,4s,16s)│    │
        │   └──────┬──────┘    │
        │          │           │
        │ max fail ║ success   │
        └──────┬───║───────────┘
               ▼   ▼
          ┌────────────────┐
          │ gps.telemetry  │
          │    .failed     │  [Alert & Handle]
          │  (DLQ, 10k)    │
          └────────────────┘

┌──────────────────────┐
│  Business Logic      │
│  (Rules, Jobs)       │
└──────┬───────┬───────┘
       ▼       ▼
  ┌─────────────────┐  ┌─────────────────┐
  │analytics.jobs   │  │report.jobs      │
  │(50k, 24h)       │  │(30k, 24h)       │
  └────────┬────────┘  └────────┬────────┘
           │                    │
           ▼                    ▼
    ┌────────────┐       ┌────────────┐
    │Analytics   │       │Report      │
    │Worker      │       │Worker      │
    └────────────┘       └────────────┘

┌──────────────────────────────────────┐
│  Rules Engine                        │
└──────────────┬───────────────────────┘
               │
               ▼
       ┌────────────────────┐
       │alert.events.stream │
       │(100k, 7d)          │
       └──┬──────────────┬──┘
          ▼              ▼
    ┌──────────┐  ┌──────────────┐
    │Alert     │  │Notification  │
    │Worker    │  │Service       │
    └──────────┘  └──────────────┘
```

## Retry Strategy

Messages failing temporarily are retried with exponential backoff:

```
Original Stream: gps.telemetry.raw
         │
         ▼ (processing fails)
    Retry Stream: gps.telemetry.retry
         │
         ├─ Check backoff_until timestamp
         │
         ├─ If waiting → stay in retry
         │
         └─ If ready → back to gps.telemetry.raw
                │
                ├─ Success → ACK (remove from pending)
                │
                └─ Fail again (retry_count+1)
                    │
                    ├─ If retry_count < MAX_RETRIES (3)
                    │  └─ Re-enqueue to retry stream with longer backoff
                    │
                    └─ If retry_count >= MAX_RETRIES
                       └─ Move to DLQ (gps.telemetry.failed)
```

Backoff delays:
- Attempt 1: ~1s (1 ± 0.1 jitter)
- Attempt 2: ~4s (2² ± jitter)
- Attempt 3: ~16s (2⁴ ± jitter)
- Attempt 4+: DLQ

## Integration Points

### Ingestion API
```python
from swm_redis import StreamTopology

topology = StreamTopology(redis_url=settings.redis_url)
await topology.initialize()

# In telemetry endpoint handler
await topology.publish_telemetry(
    device_id=request.device_id,
    imei=request.imei,
    timestamp=request.timestamp,
    latitude=request.latitude,
    longitude=request.longitude,
    speed_kph=request.speed_kph,
    heading=request.heading,
)
```

### Analytics Worker
```python
config = ConsumerGroupConfig(
    stream_name="analytics.jobs",
    group_name="analytics-worker:job-processor",
    consumer_name=f"pod-{pod_id}",
    batch_size=50,
)
consumer = topology.create_consumer(config)

async for job in consumer.read_stream():
    try:
        await process_analytics_job(job.data)
        await consumer.ack(job)
    except TemporaryError as e:
        await topology.enqueue_retry(job, error=str(e))
    except PermanentError as e:
        await topology.enqueue_dlq(job, failure_reason="analysis_error")
```

### Alert Worker
```python
config = ConsumerGroupConfig(
    stream_name="alert.events.stream",
    group_name="alert-worker:event-processor",
    consumer_name=f"pod-{pod_id}",
    batch_size=100,
    block_ms=100,  # Low latency
)
consumer = topology.create_consumer(config)

async for alert in consumer.read_stream():
    try:
        await send_alert_notifications(alert.data)
        await consumer.ack(alert)
    except Exception as e:
        # Alerts should rarely fail, but handle gracefully
        logger.error(f"Alert delivery failed: {e}")
```

## Monitoring Integration

### Prometheus Metrics

Add to your metrics collection:

```python
from prometheus_client import Gauge, Counter, Histogram

# Stream sizes
stream_length = Gauge(
    "redis_stream_length",
    "Current stream length",
    ["stream"],
)

# Consumer group stats
consumer_lag = Gauge(
    "redis_consumer_group_lag",
    "Messages waiting in consumer group",
    ["stream", "group"],
)

# Processing rates
messages_added = Counter(
    "redis_stream_messages_added",
    "Total messages added to stream",
    ["stream"],
)

# Retry metrics
retry_count = Counter(
    "redis_stream_retry_attempts",
    "Retry attempts",
    ["stream", "attempt"],
)

# Usage in monitoring loop
async def monitor_redis_health():
    topology = ...
    while True:
        for stream in ["gps.telemetry.raw", "gps.telemetry.retry", "gps.telemetry.failed"]:
            stats = await topology.get_stream_stats(stream)
            stream_length.labels(stream=stream).set(stats["length"])
        
        await asyncio.sleep(30)
```

### Grafana Dashboard

Recommended panels:
1. **Stream Length Over Time** - Line chart per stream
2. **Consumer Lag** - Gauge per consumer group
3. **Retry Rate** - Rate(messages added to retry stream)
4. **DLQ Growth** - Rate(messages to DLQ)
5. **Processing Duration** - Histogram of consumer batch times
6. **Message Volume** - Stacked bar (success/retry/failed)

### Alerting

```yaml
groups:
  - name: redis_streams
    rules:
      - alert: StreamLengthHigh
        expr: redis_stream_length{stream="gps.telemetry.raw"} > 50000
        for: 5m
        annotations:
          summary: "Stream {{ $labels.stream }} is growing"
          action: "Scale consumers or check for processing errors"

      - alert: DLQGrowth
        expr: rate(redis_stream_messages_added{stream="gps.telemetry.failed"}[5m]) > 5
        for: 5m
        annotations:
          summary: "High failure rate detected"
          action: "Review error logs and root cause"

      - alert: ConsumerLagHigh
        expr: redis_consumer_group_lag{group=~".*"} > 10000
        for: 10m
        annotations:
          summary: "Consumer group {{ $labels.group }} is lagging"
          action: "Add consumer replicas or optimize processing"
```

## Deployment Steps

### 1. Prepare Infrastructure
```bash
# Ensure Redis 5.0+ is deployed
redis-cli --version
# Redis version >= 5.0.0

# Check maxmemory and policy
redis-cli CONFIG GET maxmemory-policy
# Should be: allkeys-lru
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Enable AOF persistence
redis-cli CONFIG SET appendonly yes
redis-cli CONFIG SET appendfsync everysec
```

### 2. Deploy Python Wrapper
```bash
# Already in libs/redis:
pip install -e libs/redis

# Or in requirements.txt:
# -e libs/redis
```

### 3. Initialize Topology
```python
# In application startup:
from swm_redis import StreamTopology

@app.on_event("startup")
async def init_streams():
    topology = StreamTopology(redis_url=settings.redis_url)
    await topology.initialize()
    app.state.topology = topology

@app.on_event("shutdown")
async def cleanup_streams():
    await app.state.topology.close()
```

### 4. Deploy Consumers
Deploy consumer services:
- ingestion-api (telemetry processor)
- analytics-worker (job processor)
- alert-worker (event processor)
- retry-worker (retry handler)

Each with appropriate `ConsumerGroupConfig`.

### 5. Enable Monitoring
```bash
# Add Prometheus scrape config
scrape_configs:
  - job_name: 'redis-streams'
    static_configs:
      - targets: ['localhost:9090']  # Redis exporter

# Or custom metrics via app instrumentation
```

### 6. Test End-to-End
```bash
# Run examples
python docs/redis-streams-examples.py

# Verify streams created
redis-cli XINFO STREAM gps.telemetry.raw
redis-cli XINFO GROUPS gps.telemetry.raw
```

## Performance Benchmarks

Expected performance (single Redis instance, local network):

| Metric | Value |
|--------|-------|
| Publish throughput | 50k+ msg/sec |
| Latency (p50) | < 5ms |
| Latency (p99) | < 50ms |
| Consumer throughput | 100k+ msg/sec (1000 msg/batch) |
| Memory per stream (100k msgs) | ~500MB |
| Memory per consumer group | ~50MB |

Tuning recommendations:
- Increase `batch_size` for throughput
- Decrease `block_ms` for latency
- Use multiple consumer replicas to scale
- Monitor memory and trim old messages

## Troubleshooting

### Debug Consumer Health
```bash
# Check pending entries (messages not yet ACK'd)
redis-cli XINFO GROUPS gps.telemetry.raw

# Check consumer status
redis-cli XINFO CONSUMERS gps.telemetry.raw "group-name"

# Read a few messages manually
redis-cli XREAD COUNT 5 STREAMS gps.telemetry.raw 0
```

### Debug Retry Logic
```bash
# Check retry stream size
redis-cli XLEN gps.telemetry.retry

# Read a failed message to see retry metadata
redis-cli XRANGE gps.telemetry.retry - + COUNT 1
```

### Debug DLQ
```bash
# List oldest DLQ entries (failures to investigate)
redis-cli XRANGE gps.telemetry.failed - + COUNT 10 | less

# Archive old failures to database
# (see runbook section below)
```

## Runbooks

### DLQ Processing Runbook

For manual DLQ batch processing:

```bash
# List all failures in last 24h
redis-cli XREVRANGE gps.telemetry.failed + - COUNT 1000 | \
  jq '.[] | select(.timestamp > (now - 86400))'

# Categorize failures
# - validation_error: Log issue, may be unfixable
# - service_error: Check upstream service, may need re-publishing
# - permanent_error: Log, requires investigation

# Archive DLQ to database for auditing
# (run daily or weekly)
python scripts/archive_dlq.py --days 7 --destination=s3://...
```

### Consumer Replica Recovery

If consumer pods crash and pending messages accumulate:

```bash
# Check pending count
redis-cli XPENDING gps.telemetry.raw group-name

# Manually claim and reassign to healthy replica
redis-cli XCLAIM gps.telemetry.raw group-name \
  new-consumer-name 0 <msg-id-1> <msg-id-2> ...

# Or auto-recover via claim timeout (default 5 min)
# No action needed, just wait
```

## References

- [Architecture Deep Dive](./redis-streams-architecture.md)
- [Quick Start](./redis-streams-quickstart.md)
- [Python Examples](./redis-streams-examples.py)
- [Source Code](../libs/redis/src/swm_redis/streams.py)
- [Tests](../libs/redis/src/swm_redis/test_streams.py)
- [Redis Streams Docs](https://redis.io/docs/data-types/streams/)
