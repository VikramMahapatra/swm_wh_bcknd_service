"""
Example: Using Redis Streams Topology in the GPS Fleet Platform

This module demonstrates usage patterns for the StreamTopology API:
- Publishing telemetry from ingestion API
- Consuming and processing telemetry in workers
- Retry and DLQ handling
- Monitoring
"""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from swm_redis import ConsumerGroupConfig, StreamTopology


# ===== EXAMPLE 1: Publishing GPS Telemetry =====


async def example_publish_telemetry(redis_url: str) -> None:
    """Simulate the ingestion API publishing GPS telemetry."""
    topology = StreamTopology(redis_url=redis_url)
    await topology.initialize()

    print("[PUBLISHER] Simulating GPS ingest from 100 devices...")
    for device_index in range(100):
        device_id = uuid4()
        message_id = await topology.publish_telemetry(
            device_id=device_id,
            imei=f"35123456789012{device_index:02d}",
            timestamp=datetime.now(UTC),
            latitude=40.7128 + (device_index * 0.001),  # Variable lat
            longitude=-74.0060 + (device_index * 0.001),  # Variable lon
            speed_kph=45.5 + (device_index % 10),
            heading=(device_index * 36) % 360,
            accuracy=5.0,
            battery_percent=85.0 - (device_index % 20),
        )
        print(f"  ✓ Published telemetry for device {device_index}: {message_id}")

    await topology.close()


# ===== EXAMPLE 2: Consuming Telemetry with Error Handling =====


async def example_consume_telemetry(redis_url: str) -> None:
    """
    Simulate a worker consuming and processing telemetry.
    
    Demonstrates:
    - Reading messages in batches
    - Processing with potential failures
    - Retry and DLQ handling
    - Acknowledging successful messages
    """
    topology = StreamTopology(redis_url=redis_url)
    await topology.initialize()

    config = ConsumerGroupConfig(
        stream_name="gps.telemetry.raw",
        group_name="ingestion-api:telemetry-processor",
        consumer_name="pod-1-instance-0",
        batch_size=50,
        block_ms=2000,
    )
    consumer = topology.create_consumer(config)

    processed = 0
    failed = 0
    retried = 0

    print("[CONSUMER] Starting to read telemetry messages...")

    async for message in consumer.read_stream(batch_size=10):
        try:
            # Simulate processing
            device_id = message.data.get("device_id")
            latitude = float(message.data.get("latitude", 0))
            longitude = float(message.data.get("longitude", 0))

            # Simulate occasional validation failures (5% chance)
            import random

            if random.random() < 0.05:
                raise ValueError(f"Invalid coordinates: {latitude}, {longitude}")

            print(f"  ✓ Processed telemetry: device={device_id}, lat={latitude:.4f}, lon={longitude:.4f}")
            await consumer.ack(message)
            processed += 1

        except ValueError as e:
            # Permanent error: move to DLQ
            print(f"  ✗ Permanent error for msg {message.message_id}: {e}")
            await topology.enqueue_dlq(
                message,
                final_error=str(e),
                failure_reason="validation_error",
                last_consumer=config.consumer_name,
            )
            failed += 1

        except Exception as e:
            # Temporary error: retry
            print(f"  ⚠ Temporary error for msg {message.message_id}: {e}, will retry...")
            await topology.enqueue_retry(
                message,
                error=str(e),
                consumer_name=config.consumer_name,
            )
            retried += 1

        # Demo: stop after 20 messages
        if processed + failed + retried >= 20:
            break

    print(f"\n[SUMMARY] Processed={processed}, Failed={failed}, Retried={retried}")
    await topology.close()


# ===== EXAMPLE 3: Retry Worker Processing Backoff =====


async def example_retry_worker(redis_url: str) -> None:
    """
    Simulate a dedicated retry worker that processes backlogged messages.
    
    Demonstrates:
    - Reading from retry stream
    - Checking backoff timers
    - Re-submitting or moving to DLQ
    """
    topology = StreamTopology(redis_url=redis_url)

    config = ConsumerGroupConfig(
        stream_name="gps.telemetry.retry",
        group_name="retry-worker:telemetry-retry-processor",
        consumer_name="retry-pod-1",
        batch_size=25,
        block_ms=5000,
    )
    consumer = topology.create_consumer(config)

    print("[RETRY_WORKER] Starting retry processing...")

    async for message in consumer.read_stream(batch_size=5):
        try:
            retry_count = int(message.data.get("retry_count", 0))
            backoff_until = message.data.get("backoff_until", "")

            # Check if backoff period has elapsed
            if backoff_until:
                backoff_time = datetime.fromisoformat(backoff_until)
                if datetime.now(UTC) < backoff_time:
                    print(f"  ⏳ Msg {message.message_id} still in backoff, skip for now")
                    continue  # Don't acknowledge, will be retried later

            # Attempt reprocessing
            print(f"  ↻ Retrying message {message.message_id} (attempt {retry_count + 1})")

            # Simulate reprocessing (may fail again)
            import random

            if random.random() < 0.1:  # 10% failure rate
                raise Exception("Reprocessing failed")

            # Success: move back to primary stream
            original_id = message.data.get("original_id")
            payload = message.data.get("payload")
            print(f"    ✓ Retry succeeded for {original_id}")
            await consumer.ack(message)

        except Exception as e:
            print(f"  ✗ Retry failed: {e}")
            # Re-enqueue to retry or DLQ based on count
            await topology.enqueue_retry(
                message,
                error=str(e),
                retry_count=retry_count,
                consumer_name=config.consumer_name,
            )

        # Demo
        if random.random() < 0.3:
            break

    print("[RETRY_WORKER] Processing complete")
    await topology.close()


# ===== EXAMPLE 4: Publishing and Consuming Jobs =====


async def example_publishing_jobs(redis_url: str) -> None:
    """Simulate publishing analytics and report jobs."""
    topology = StreamTopology(redis_url=redis_url)
    await topology.initialize()

    print("[JOB_PUBLISHER] Publishing analytics jobs...")

    for i in range(5):
        job_id = uuid4()
        msg_id = await topology.publish_job(
            stream_name="analytics.jobs",
            job_id=job_id,
            job_type="route_optimization",
            parameters={"vehicle_ids": [str(uuid4()) for _ in range(3)]},
            priority=8,
        )
        print(f"  ✓ Published analytics job {job_id}: {msg_id}")

    print("\n[JOB_PUBLISHER] Publishing report jobs...")

    for i in range(3):
        job_id = uuid4()
        msg_id = await topology.publish_job(
            stream_name="report.jobs",
            job_id=job_id,
            job_type="daily_summary",
            parameters={"date": "2025-05-04"},
            priority=5,
        )
        print(f"  ✓ Published report job {job_id}: {msg_id}")

    await topology.close()


async def example_consuming_jobs(redis_url: str) -> None:
    """Simulate a worker consuming analytics jobs."""
    topology = StreamTopology(redis_url=redis_url)
    await topology.initialize()

    config = ConsumerGroupConfig(
        stream_name="analytics.jobs",
        group_name="analytics-worker:job-processor",
        consumer_name="analytics-pod-1",
        batch_size=10,
        block_ms=2000,
    )
    consumer = topology.create_consumer(config)

    print("[JOB_CONSUMER] Starting job processing...")

    async for message in consumer.read_stream(batch_size=3):
        try:
            job_id = message.data.get("job_id")
            job_type = message.data.get("job_type")
            print(f"  ⚙ Processing job {job_id} (type={job_type})")

            # Simulate work
            await asyncio.sleep(0.5)

            print(f"    ✓ Job {job_id} completed")
            await consumer.ack(message)

        except Exception as e:
            print(f"  ✗ Job processing failed: {e}")
            await topology.enqueue_dlq(
                message,
                final_error=str(e),
                failure_reason="processing_error",
                last_consumer=config.consumer_name,
            )

        # Demo
        import random

        if random.random() < 0.4:
            break

    print("[JOB_CONSUMER] Job processing complete")
    await topology.close()


# ===== EXAMPLE 5: Publishing and Monitoring Alerts =====


async def example_publishing_alerts(redis_url: str) -> None:
    """Simulate rule engine publishing alert events."""
    topology = StreamTopology(redis_url=redis_url)
    await topology.initialize()

    print("[ALERT_PUBLISHER] Publishing alert events...")

    alert_scenarios = [
        ("geofence_breach", "critical", "breach detected at Depot A"),
        ("speed_violation", "warning", "device exceeding 80 km/h"),
        ("battery_low", "warning", "battery below 20%"),
        ("offline", "critical", "device offline for 30+ minutes"),
    ]

    for alert_type, severity, description in alert_scenarios:
        alert_id = uuid4()
        device_id = uuid4()
        vehicle_id = uuid4()

        msg_id = await topology.publish_alert(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            device_id=device_id,
            vehicle_id=vehicle_id,
            context={"rule_id": str(uuid4()), "description": description},
            recipients=["operator@company.com", "group:fleet-supervisors"],
        )
        print(f"  ✓ Published {severity.upper()} alert ({alert_type}): {msg_id}")

    await topology.close()


# ===== EXAMPLE 6: Monitoring Stream Health =====


async def example_monitoring(redis_url: str) -> None:
    """Demonstrate monitoring stream and consumer group stats."""
    topology = StreamTopology(redis_url=redis_url)
    await topology.initialize()

    print("[MONITORING] Fetching stream statistics...")

    streams_to_monitor = [
        "gps.telemetry.raw",
        "gps.telemetry.retry",
        "gps.telemetry.failed",
        "analytics.jobs",
        "alert.events.stream",
    ]

    for stream_name in streams_to_monitor:
        stats = await topology.get_stream_stats(stream_name)
        print(f"\n  {stream_name}:")
        print(f"    - Length: {stats.get('length', 0)}")

    print("\n[MONITORING] Fetching consumer group statistics...")

    groups_to_monitor = [
        ("gps.telemetry.raw", "ingestion-api:telemetry-processor"),
        ("analytics.jobs", "analytics-worker:job-processor"),
        ("alert.events.stream", "alert-worker:event-processor"),
    ]

    for stream_name, group_name in groups_to_monitor:
        stats = await topology.get_consumer_group_stats(stream_name, group_name)
        if stats:
            print(f"\n  {stream_name} / {group_name}:")
            print(f"    - Consumers: {stats.get('consumers', 0)}")
            print(f"    - Pending: {stats.get('pending', 0)}")

    await topology.close()


# ===== Main Demo =====


async def main() -> None:
    """Run all examples (requires running Redis instance)."""
    REDIS_URL = "redis://localhost:6379/0"

    print("=" * 70)
    print("Redis Streams Topology - Complete Usage Examples")
    print("=" * 70)

    try:
        # Example 1: Publish telemetry
        print("\n1. PUBLISHING TELEMETRY")
        print("-" * 70)
        await example_publish_telemetry(REDIS_URL)

        # Example 2: Consume with error handling
        print("\n2. CONSUMING WITH ERROR HANDLING & RETRY")
        print("-" * 70)
        await example_consume_telemetry(REDIS_URL)

        # Example 3: Retry worker
        print("\n3. RETRY WORKER PROCESSING")
        print("-" * 70)
        await example_retry_worker(REDIS_URL)

        # Example 4: Jobs
        print("\n4. JOB PUBLISHING AND CONSUMING")
        print("-" * 70)
        await example_publishing_jobs(REDIS_URL)
        await example_consuming_jobs(REDIS_URL)

        # Example 5: Alerts
        print("\n5. ALERT PUBLISHING")
        print("-" * 70)
        await example_publishing_alerts(REDIS_URL)

        # Example 6: Monitoring
        print("\n6. MONITORING METRICS")
        print("-" * 70)
        await example_monitoring(REDIS_URL)

        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
