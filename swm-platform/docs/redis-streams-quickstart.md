# Redis Streams Quick Start Guide

## Overview

The Redis Streams topology provides a reliable, scalable event streaming and job processing system for the Fleet GPS platform. It includes:

- **7 main streams**: Telemetry, jobs, alerts, and replay events
- **Consumer groups**: Automatic load balancing and at-least-once delivery
- **Retry strategy**: Exponential backoff with configurable max retries
- **Dead-letter queues (DLQ)**: Permanent failure handling and monitoring
- **Built-in monitoring**: Stream length, consumer lag, and processing metrics

## Architecture Files

| File | Purpose |
|------|---------|
| [redis-streams-architecture.md](./redis-streams-architecture.md) | Detailed topology, schemas, and design rationale |
| [libs/redis/src/swm_redis/streams.py](../libs/redis/src/swm_redis/streams.py) | Python wrapper implementation |
| [redis-streams-examples.py](./redis-streams-examples.py) | Complete usage examples |

## 5-Minute Startup

### 1. Initialize Topology

```python
from swm_redis import StreamTopology, ConsumerGroupConfig

# Create and initialize topology
topology = StreamTopology(redis_url="redis://localhost:6379/0")
await topology.initialize()
```

This creates all 7 streams and consumer groups with optimal defaults.

### 2. Publish Telemetry

```python
from datetime import UTC, datetime
from uuid import uuid4

message_id = await topology.publish_telemetry(
    device_id=uuid4(),
    imei="351234567890123",
    timestamp=datetime.now(UTC),
    latitude=40.7128,
    longitude=-74.0060,
    speed_kph=45.5,
    heading=270,
    accuracy=5.0,
    battery_percent=85.0,
)
print(f"Published: {message_id}")
```

### 3. Consume with Automatic Retry

```python
config = ConsumerGroupConfig(
    stream_name="gps.telemetry.raw",
    group_name="ingestion-api:telemetry-processor",
    consumer_name="pod-1",
)
consumer = topology.create_consumer(config)

async for message in consumer.read_stream(batch_size=100):
    try:
        # Your processing logic
        result = await process_telemetry(message.data)
        await consumer.ack(message)
    except TemporaryError:
        # Automatic retry with backoff
        await topology.enqueue_retry(message, error=str(e))
    except PermanentError:
        # Move to dead-letter queue
        await topology.enqueue_dlq(message, failure_reason="validation_error")
```

### 4. Monitor Health

```python
# Stream statistics
stats = await topology.get_stream_stats("gps.telemetry.raw")
print(f"Stream length: {stats['length']}")

# Consumer group lag
lag = await topology.get_consumer_group_stats(
    "gps.telemetry.raw",
    "ingestion-api:telemetry-processor",
)
print(f"Pending messages: {lag['pending']}")
```

## Stream Reference

### gps.telemetry.raw
**Entry stream for GPS telemetry from devices.**

- **Maxlen**: 100,000 messages
- **Retention**: ~1 hour
- **Consumers**: ingestion-api, analytics-worker, replay-worker

```json
{
  "device_id": "uuid",
  "imei": "15-17 digit ID",
  "timestamp": "ISO8601",
  "latitude": "float (-90 to 90)",
  "longitude": "float (-180 to 180)",
  "speed_kph": "float >= 0",
  "heading": "int (0-359)",
  "accuracy": "float (meters)",
  "battery_percent": "float (0-100)"
}
```

### gps.telemetry.retry
**Temporary holding for messages awaiting retry.**

- **Maxlen**: 50,000 messages
- **Retention**: ~30 minutes
- **Consumers**: retry-worker

Messages automatically moved here on temporary failures, with exponential backoff (1s, 4s, 16s).

### gps.telemetry.failed
**Dead-letter queue for permanent failures.**

- **Maxlen**: 10,000 messages
- **Retention**: 72 hours
- **Consumers**: dlq-monitor

Messages moved here after max retries (3) or permanent errors. Trigger alerts.

### analytics.jobs, report.jobs, replay.jobs
**Job queues for asynchronous processing.**

- **Maxlen**: 50,000 (analytics), 30,000 (report), 20,000 (replay)
- **Retention**: 24 hours (analytics/report), 30 days (replay)

```python
message_id = await topology.publish_job(
    stream_name="analytics.jobs",
    job_id=uuid4(),
    job_type="route_optimization",
    parameters={"vehicle_ids": [...]},
    priority=8,
)
```

### alert.events.stream
**Real-time alert events from rule engine.**

- **Maxlen**: 100,000 messages
- **Retention**: 7 days
- **Consumers**: alert-worker, notification-service

```python
message_id = await topology.publish_alert(
    alert_id=uuid4(),
    alert_type="geofence_breach",
    severity="critical",
    device_id=uuid4(),
    vehicle_id=uuid4(),
    context={"rule_id": "...", "geofence": "Depot A"},
    recipients=["user@company.com"],
)
```

## Retry Strategy

Messages that fail are automatically retried with exponential backoff:

| Attempt | Delay | Reason to Fail |
|---------|-------|----------------|
| Initial | 0s | Move to retry stream |
| 1st Retry | ~1s | Temporary service error, network timeout |
| 2nd Retry | ~4s | Database locked, rate limit |
| 3rd Retry | ~16s | Still failing... |
| Final | → DLQ | Max retries exceeded |

All timings include random jitter (±10%) to avoid thundering herd.

## Consumer Group Patterns

### Pattern 1: Single Consumer (High Throughput)

```python
config = ConsumerGroupConfig(
    stream_name="gps.telemetry.raw",
    group_name="analytics-worker:telemetry-consumer",
    consumer_name=f"pod-{pod_id}",
    batch_size=500,
    block_ms=1000,
)
```

### Pattern 2: Competing Consumers (Load Balanced)

```python
# Multiple instances with same group, different consumer names
config = ConsumerGroupConfig(
    stream_name="analytics.jobs",
    group_name="analytics-worker:job-processor",
    consumer_name=f"pod-{pod_id}-replica-{replica_id}",
    batch_size=50,
)
```

Redis automatically distributes work across competing consumers. If a consumer crashes, its pending messages are claimed by others after a timeout (default 5 minutes).

### Pattern 3: Fan-Out (Multiple Independent Consumers)

```python
# Each service has its own group on the same stream
streams = [
    ("gps.telemetry.raw", "ingestion-api:processor"),
    ("gps.telemetry.raw", "analytics-worker:consumer"),
    ("gps.telemetry.raw", "replay-worker:archiver"),
]
# Each group processes all messages independently
```

## Monitoring

### Key Metrics to Track

```python
# Stream length (should not grow unbounded)
await topology.get_stream_stats("gps.telemetry.raw")
→ {"length": 5234, "first_entry": [...], "last_entry": [...]}

# Consumer group lag (gap between last message and consumer)
await topology.get_consumer_group_stats("gps.telemetry.raw", "group-1")
→ {"consumers": 2, "pending": 345, "last_delivered_id": "1234-0"}

# DLQ growth (should be < 1% of throughput)
await topology.get_stream_stats("gps.telemetry.failed")
→ {"length": 42}  # Alert if > 100/hour
```

### Alerting Rules (Prometheus)

```yaml
groups:
  - name: redis-streams
    rules:
      # Stream growing unbounded
      - alert: StreamLength
        expr: redis_stream_length{stream="gps.telemetry.raw"} > 50000
        for: 5m
        action: Scale consumers or check processing errors

      # Consumer lag (messages piling up)
      - alert: ConsumerLag
        expr: redis_consumer_group_pending{stream="gps.telemetry.raw"} > 1000
        for: 5m
        action: Check consumer resource usage, add replicas

      # High DLQ rate
      - alert: DLQGrowth
        expr: rate(redis_stream_entries_added{stream="gps.telemetry.failed"}[5m]) > 1
        for: 5m
        action: Investigate failure root cause, check error logs

      # Consumer offline
      - alert: ConsumerOffline
        expr: time() - redis_consumer_last_activity{...} > 300
        for: 1m
        action: Consumer pod may be crashed, check Kubernetes logs
```

## Troubleshooting

### Issue: Stream Growing Unbounded

```python
# Investigate
length = (await topology.get_stream_stats("gps.telemetry.raw"))["length"]
if length > 100000:
    print("Stream is growing faster than consumers can process")
    
# Check consumer lag
lag = await topology.get_consumer_group_stats(
    "gps.telemetry.raw",
    "ingestion-api:telemetry-processor"
)
print(f"Pending: {lag['pending']}")

# Solutions:
# 1. Add more consumer replicas
# 2. Increase batch_size to process faster
# 3. Check if consumers are crashing (logs, memory usage)
# 4. Reduce message rate at source if needed
```

### Issue: High Failure Rate (DLQ Growing)

```python
# Check DLQ
dlq_stats = await topology.get_stream_stats("gps.telemetry.failed")
print(f"Failed messages: {dlq_stats['length']}")

# Look at actual failures
redis = topology.redis_client.client
failed = await redis.xrange("gps.telemetry.failed", count=10)
for msg_id, data in failed:
    print(f"Failed: {data.get(b'failure_reason', b'?').decode()}")
    print(f"  Error: {data.get(b'final_error', b'?').decode()}")

# Solutions:
# 1. Fix validation logic if validation_error
# 2. Return 5xx errors from upstream deps if service_error
# 3. Increase backoff times if temp errors
# 4. Contact on-call if permanent infrastructure issue
```

### Issue: Consumer Lag Growing After Crash

```python
# Pending messages will be reclaimed after claim_timeout_ms (default 5 min)
# To recover immediately:

redis = topology.redis_client.client
# Force reclaim of all pending for a group
await redis.xpending("gps.telemetry.raw", "group-name")
# Shows pending entries, then:
await redis.xclaim(
    "gps.telemetry.raw",
    "group-name",
    "new-consumer",
    0,  # min-idle-time = 0 (claim immediately)
    ["message-id-1", "message-id-2", ...],
)
```

## Performance Tuning

### For High Throughput (100k+ events/sec)

```python
config = ConsumerGroupConfig(
    stream_name="gps.telemetry.raw",
    group_name="ingestion-api:telemetry-processor",
    consumer_name="pod-1",
    batch_size=1000,      # Large batch
    block_ms=100,         # Short blocking (batch fills quickly)
    claim_timeout_ms=120_000,  # Longer timeout (quick consumers)
)
```

### For Low Latency Alerts

```python
config = ConsumerGroupConfig(
    stream_name="alert.events.stream",
    group_name="alert-worker:event-processor",
    consumer_name="pod-1",
    batch_size=10,        # Small batch
    block_ms=100,         # No blocking, poll fast
    claim_timeout_ms=60_000,   # Fast failover
)
```

### For Batch Processing (Reports)

```python
config = ConsumerGroupConfig(
    stream_name="report.jobs",
    group_name="report-worker:job-processor",
    consumer_name="batch-worker-1",
    batch_size=100,
    block_ms=5000,        # Can wait longer
)
```

## Testing

Run the complete example suite:

```bash
cd swm-platform
python docs/redis-streams-examples.py
```

This demonstrates:
- Publishing telemetry from 100 simulated devices
- Consuming with failures and retry logic
- Processing jobs and alerts
- Monitoring stream health

All with a local Redis instance (localhost:6379).

## Production Checklist

- [ ] Redis 5.0+ deployed and backed up
- [ ] Persistence enabled (AOF recommended)
- [ ] Memory policy set to `allkeys-lru`
- [ ] Monitoring dashboard created (stream length, lag, DLQ)
- [ ] Alert rules configured (see Alerting section)
- [ ] Consumer group ownership documented (which service owns which group)
- [ ] Runbook written for DLQ processing
- [ ] Load tested at expected throughput (test peak rates)
- [ ] Failover tested (consumer crash, Redis restart)
- [ ] Retention policy validated (trim frequency, maxlen)

## References

- Full Architecture: [redis-streams-architecture.md](./redis-streams-architecture.md)
- Python Implementation: [libs/redis/src/swm_redis/streams.py](../libs/redis/src/swm_redis/streams.py)
- Examples: [redis-streams-examples.py](./redis-streams-examples.py)
- Redis Docs: https://redis.io/docs/data-types/streams/
- Consumer Groups: https://redis.io/docs/data-types/streams-tutorial/#consumer-groups-tutorial
