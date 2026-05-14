"""Unit tests for Redis Streams topology and consumer groups."""

from __future__ import annotations

import asyncio
import base64
from datetime import UTC, datetime, timedelta
import zlib
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import orjson
import pytest

from swm_redis.streams import (
    AbstractStreamConsumer,
    ConsumerGroupConfig,
    PoisonMessageError,
    ProducerConfig,
    RedisReplayJobProcessor,
    RedisReplayPipeline,
    RedisTelemetryProducer,
    ReplayJobKind,
    ReplayJobRequest,
    ReplayJobStatus,
    StreamConfig,
    StreamConsumerFrameworkConfig,
    StreamMessage,
    StreamTopology,
    TelemetryEvent,
)


class TestStreamTopology:
    """Tests for StreamTopology initialization and configuration."""

    @pytest.mark.asyncio
    async def test_initialize_creates_streams_and_groups(self) -> None:
        """Test that initialize() creates streams and consumer groups."""
        mock_redis = AsyncMock()
        mock_client = MagicMock()
        mock_client.client = mock_redis
        mock_client.close = AsyncMock()

        topology = StreamTopology(redis_client=mock_client)

        # Mock XGROUP CREATE responses
        async def xgroup_side_effect(*args, **kwargs):
            if args[0] == "XGROUP":
                # First call already exists (root group)
                if "$group$" in args:
                    raise Exception("BUSYGROUP Root #...")
                return None
            return None

        mock_redis.execute_command = AsyncMock(side_effect=xgroup_side_effect)

        # Initialize with a small test set
        test_streams = [
            StreamConfig(
                name="test.stream.1",
                maxlen=1000,
                consumer_groups=["group-a", "group-b"],
            ),
        ]

        await topology.initialize(streams=test_streams)

        # Should have called execute_command for stream creation
        assert mock_redis.execute_command.called

    @pytest.mark.asyncio
    async def test_publish_telemetry(self) -> None:
        """Test publishing telemetry to gps.telemetry.raw."""
        mock_client = MagicMock()
        mock_client.xadd = AsyncMock(return_value="1234567890-0")

        topology = StreamTopology(redis_client=mock_client)

        message_id = await topology.publish_telemetry(
            device_id=uuid4(),
            imei="123456789012345",
            timestamp=datetime.now(UTC),
            latitude=40.7128,
            longitude=-74.0060,
            speed_kph=45.5,
            heading=270,
            accuracy=5.0,
            battery_percent=85.0,
        )

        assert message_id == "1234567890-0"
        mock_client.xadd.assert_called_once()

        # Verify call structure
        call_args = mock_client.xadd.call_args
        assert call_args[0][0] == "gps.telemetry.raw"
        assert isinstance(call_args[0][1], dict)
        assert call_args[1]["timeout"] == 5.0
        assert "payload" in call_args[0][1]


class TestRedisTelemetryProducer:
    @pytest.mark.asyncio
    async def test_publish_telemetry_uses_async_xadd(self) -> None:
        mock_client = MagicMock()
        mock_client.xadd = AsyncMock(return_value="1-0")
        producer = RedisTelemetryProducer(mock_client)

        message_id = await producer.publish_telemetry(
            TelemetryEvent(
                device_id=uuid4(),
                imei="123456789012345",
                timestamp=datetime.now(UTC),
                latitude=12.34,
                longitude=56.78,
                speed_kph=40.0,
                heading=90,
            )
        )

        assert message_id == "1-0"
        mock_client.xadd.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_publish_batch_returns_message_ids(self) -> None:
        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[b"1-0", b"1-1"])
        mock_pipe.reset = AsyncMock()

        mock_redis = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe

        mock_client = MagicMock()
        mock_client.client = mock_redis
        mock_client.run_operation = AsyncMock(return_value=[b"1-0", b"1-1"])

        producer = RedisTelemetryProducer(mock_client)
        results = await producer.publish_batch(
            [
                {
                    "device_id": str(uuid4()),
                    "imei": "123456789012345",
                    "timestamp": datetime.now(UTC),
                    "latitude": 10.0,
                    "longitude": 20.0,
                    "speed_kph": 30.0,
                    "heading": 45,
                },
                {
                    "device_id": str(uuid4()),
                    "imei": "123456789012346",
                    "timestamp": datetime.now(UTC),
                    "latitude": 11.0,
                    "longitude": 21.0,
                    "speed_kph": 31.0,
                    "heading": 46,
                },
            ]
        )

        assert results == ["1-0", "1-1"]
        assert mock_pipe.xadd.call_count == 2
        mock_client.run_operation.assert_awaited_once()
        mock_pipe.reset.assert_awaited_once()

    def test_prepare_fields_serializes_and_compresses_payload(self) -> None:
        mock_client = MagicMock()
        producer = RedisTelemetryProducer(
            mock_client,
            config=ProducerConfig(compression_threshold_bytes=1),
        )

        fields = producer._prepare_fields(
            {
                "device_id": str(uuid4()),
                "imei": "123456789012345",
                "timestamp": datetime.now(UTC),
                "latitude": 12.34,
                "longitude": 56.78,
                "speed_kph": 40.0,
                "heading": 90,
                "attributes": {"source": "test"},
            }
        )

        assert fields["content_encoding"] == "zlib+base64"
        decoded = zlib.decompress(base64.b64decode(fields["payload"]))
        payload = orjson.loads(decoded)
        assert payload["imei"] == "123456789012345"
        assert payload["attributes"]["source"] == "test"

    @patch("structlog.contextvars.get_contextvars", return_value={"trace_id": "trace-123", "correlation_id": "corr-456"})
    def test_prepare_fields_propagates_trace_context(self, _mock_context) -> None:
        mock_client = MagicMock()
        producer = RedisTelemetryProducer(mock_client)

        fields = producer._prepare_fields(
            {
                "device_id": str(uuid4()),
                "imei": "123456789012345",
                "timestamp": datetime.now(UTC),
                "latitude": 1.0,
                "longitude": 2.0,
                "speed_kph": 3.0,
                "heading": 4,
            }
        )

        assert fields["trace_id"] == "trace-123"
        assert fields["correlation_id"] == "corr-456"

    @pytest.mark.asyncio
    async def test_publish_telemetry_passes_timeout(self) -> None:
        mock_client = MagicMock()
        mock_client.xadd = AsyncMock(return_value="1-0")
        producer = RedisTelemetryProducer(
            mock_client,
            config=ProducerConfig(timeout=2.5),
        )

        await producer.publish_telemetry(
            {
                "device_id": str(uuid4()),
                "imei": "123456789012345",
                "timestamp": datetime.now(UTC),
                "latitude": 10.0,
                "longitude": 20.0,
                "speed_kph": 30.0,
                "heading": 45,
            }
        )

        assert mock_client.xadd.await_args.kwargs["timeout"] == 2.5

    @pytest.mark.asyncio
    async def test_publish_job(self) -> None:
        """Test publishing a job to analytics.jobs."""
        mock_redis = AsyncMock()
        mock_redis.xadd = AsyncMock(return_value=b"job-123")
        mock_client = MagicMock()
        mock_client.client = mock_redis

        topology = StreamTopology(redis_client=mock_client)

        message_id = await topology.publish_job(
            stream_name="analytics.jobs",
            job_id=uuid4(),
            job_type="route_optimization",
            parameters={"vehicle_id": str(uuid4())},
            priority=8,
        )

        assert message_id == "job-123"
        mock_redis.xadd.assert_called_once()

        call_args = mock_redis.xadd.call_args
        assert call_args[0][0] == "analytics.jobs"
        assert call_args[0][1]["job_type"] == "route_optimization"

    @pytest.mark.asyncio
    async def test_enqueue_dead_letter_reprocess_job(self) -> None:
        mock_client = MagicMock()
        mock_client.xadd = AsyncMock(return_value="replay-job-1")
        mock_client.set_json = AsyncMock(return_value=True)

        topology = StreamTopology(redis_client=mock_client)
        replay = RedisReplayPipeline(topology)

        message_id = await replay.enqueue_dead_letter_reprocess(
            job_id="job-1",
            poison_stream="gps.telemetry.poison",
            target_stream="gps.telemetry.raw",
            max_messages=25,
            priority=9,
        )

        assert message_id == "replay-job-1"
        mock_client.xadd.assert_awaited_once()
        args = mock_client.xadd.await_args.args
        assert args[0] == "replay.jobs"
        assert args[1]["replay_kind"] == ReplayJobKind.DEAD_LETTER.value
        assert args[1]["priority"] == "9"
        mock_client.set_json.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_replay_pipeline_processes_dead_letters_and_tracks_progress(self) -> None:
        mock_client = MagicMock()
        mock_client.xrange = AsyncMock(
            return_value=[
                (
                    "1-0",
                    {
                        "device_id": "dev-1",
                        "original_stream": "gps.telemetry.raw",
                        "original_message_id": "orig-1",
                        "last_error": "bad payload",
                    },
                )
            ]
        )
        mock_client.xadd = AsyncMock(return_value="replayed-1")
        mock_client.set_json = AsyncMock(return_value=True)
        mock_client.get_json = AsyncMock(
            return_value={
                "job_id": "job-1",
                "kind": "dead_letter",
                "status": "completed",
                "source_stream": "gps.telemetry.poison",
                "target_stream": "gps.telemetry.raw",
                "priority": 8,
                "start_id": "-",
                "end_id": "+",
                "max_messages": 10,
                "total_messages": 1,
                "replayed_messages": 1,
                "failed_messages": 0,
                "last_replayed_id": "1-0",
                "last_error": None,
                "created_at": datetime.now(UTC).isoformat(),
                "started_at": datetime.now(UTC).isoformat(),
                "finished_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
                "progress_percent": 100.0,
            }
        )

        topology = StreamTopology(redis_client=mock_client)
        replay = RedisReplayPipeline(topology)

        progress = await replay.process_job(
            ReplayJobRequest(
                job_id="job-1",
                kind=ReplayJobKind.DEAD_LETTER,
                source_stream="gps.telemetry.poison",
                target_stream="gps.telemetry.raw",
                max_messages=10,
                priority=8,
            )
        )

        assert progress.status == ReplayJobStatus.COMPLETED
        assert progress.replayed_messages == 1
        xadd_calls = mock_client.xadd.await_args_list
        assert xadd_calls[0].args[0] == "gps.telemetry.raw"
        assert "original_stream" not in xadd_calls[0].args[1]
        stored = await replay.get_progress("job-1")
        assert stored is not None
        assert stored.status == ReplayJobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_replay_pipeline_processes_backfill_messages(self) -> None:
        mock_client = MagicMock()
        mock_client.xrange = AsyncMock(
            return_value=[
                ("1-0", {"device_id": "dev-1", "payload": "a"}),
                ("2-0", {"device_id": "dev-2", "payload": "b"}),
            ]
        )
        mock_client.xadd = AsyncMock(return_value="replayed")
        mock_client.set_json = AsyncMock(return_value=True)

        topology = StreamTopology(redis_client=mock_client)
        replay = RedisReplayPipeline(topology)

        progress = await replay.process_job(
            ReplayJobRequest(
                job_id="job-2",
                kind=ReplayJobKind.BACKFILL,
                source_stream="gps.telemetry.raw",
                target_stream="gps.telemetry.retry",
                start_id="0-0",
                end_id="9-0",
                priority=4,
            )
        )

        assert progress.status == ReplayJobStatus.COMPLETED
        assert progress.replayed_messages == 2
        mock_client.xadd.assert_any_await("gps.telemetry.retry", {"device_id": "dev-1", "payload": "a"})
        mock_client.xadd.assert_any_await("gps.telemetry.retry", {"device_id": "dev-2", "payload": "b"})

    def test_replay_job_processor_prioritizes_higher_priority_jobs(self) -> None:
        topology = StreamTopology(redis_client=MagicMock())
        replay = RedisReplayPipeline(topology)
        processor = RedisReplayJobProcessor(topology, replay)

        ordered = processor._prioritize_messages(
            [
                StreamMessage("replay.jobs", "1-0", {"job_id": "low", "priority": "1"}),
                StreamMessage("replay.jobs", "2-0", {"job_id": "high", "priority": "9"}),
                StreamMessage("replay.jobs", "3-0", {"job_id": "mid", "priority": "5"}),
            ]
        )

        assert [message.data["job_id"] for message in ordered] == ["high", "mid", "low"]

    @pytest.mark.asyncio
    async def test_publish_alert(self) -> None:
        """Test publishing an alert event."""
        mock_redis = AsyncMock()
        mock_redis.xadd = AsyncMock(return_value=b"alert-xyz")
        mock_client = MagicMock()
        mock_client.client = mock_redis

        topology = StreamTopology(redis_client=mock_client)

        message_id = await topology.publish_alert(
            alert_id=uuid4(),
            alert_type="geofence_breach",
            severity="critical",
            device_id=uuid4(),
            vehicle_id=uuid4(),
            context={"rule_id": str(uuid4()), "geofence_name": "Depot A"},
            recipients=["user-123", "group-456"],
        )

        assert message_id == "alert-xyz"
        mock_redis.xadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_enqueue_retry(self) -> None:
        """Test moving a message to retry stream."""
        mock_redis = AsyncMock()
        mock_redis.xadd = AsyncMock(return_value=b"retry-msg-1")
        mock_client = MagicMock()
        mock_client.client = mock_redis

        topology = StreamTopology(redis_client=mock_client)

        original_msg = StreamMessage(
            stream="gps.telemetry.raw",
            message_id="1234567890-0",
            data={"device_id": str(uuid4()), "latitude": "40.7128"},
            retry_count=0,
        )

        message_id = await topology.enqueue_retry(
            original_msg,
            error="Processing failed",
            consumer_name="pod-1",
        )

        assert message_id == "retry-msg-1"
        mock_redis.xadd.assert_called_once()

        call_args = mock_redis.xadd.call_args
        assert call_args[0][0] == "gps.telemetry.retry"
        assert call_args[0][1]["retry_count"] == "1"

    @pytest.mark.asyncio
    async def test_enqueue_retry_exceeds_max(self) -> None:
        """Test that exceeding max retries moves to DLQ."""
        mock_redis = AsyncMock()
        mock_redis.xadd = AsyncMock(return_value=b"dlq-msg-1")
        mock_client = MagicMock()
        mock_client.client = mock_redis

        topology = StreamTopology(redis_client=mock_client)

        original_msg = StreamMessage(
            stream="gps.telemetry.raw",
            message_id="1234567890-0",
            data={"device_id": str(uuid4())},
            retry_count=StreamTopology.MAX_RETRIES,
        )

        message_id = await topology.enqueue_retry(
            original_msg,
            error="Max retries exceeded",
        )

        # Should enqueue to DLQ instead
        assert message_id == "dlq-msg-1"
        mock_redis.xadd.assert_called_once()

        call_args = mock_redis.xadd.call_args
        assert call_args[0][0] == "gps.telemetry.failed"

    @pytest.mark.asyncio
    async def test_enqueue_dlq(self) -> None:
        """Test moving a message to the dead-letter queue."""
        mock_redis = AsyncMock()
        mock_redis.xadd = AsyncMock(return_value=b"dlq-final-1")
        mock_client = MagicMock()
        mock_client.client = mock_redis

        topology = StreamTopology(redis_client=mock_client)

        original_msg = StreamMessage(
            stream="gps.telemetry.raw",
            message_id="1234567890-0",
            data={"device_id": str(uuid4()), "imei": "123456789012345"},
            retry_count=3,
        )

        message_id = await topology.enqueue_dlq(
            original_msg,
            final_error="Permanent validation error",
            failure_reason="validation_error",
            last_consumer="ingestion-processor",
        )

        assert message_id == "dlq-final-1"
        mock_redis.xadd.assert_called_once()

        call_args = mock_redis.xadd.call_args
        assert call_args[0][0] == "gps.telemetry.failed"
        assert call_args[0][1]["failure_reason"] == "validation_error"

    def test_calculate_backoff(self) -> None:
        """Test exponential backoff calculation."""
        mock_client = MagicMock()
        topology = StreamTopology(redis_client=mock_client)

        # retry_count=0 → base_delay=1
        backoff_0 = topology._calculate_backoff(0)
        assert 0 < backoff_0 <= 1.1  # ~1s with jitter

        # retry_count=1 → base_delay=4
        backoff_1 = topology._calculate_backoff(1)
        assert 3.6 <= backoff_1 <= 4.4  # ~4s with jitter

        # retry_count=2 → base_delay=16
        backoff_2 = topology._calculate_backoff(2)
        assert 14.4 <= backoff_2 <= 17.6  # ~16s with jitter

        # Backoff increases exponentially
        assert backoff_1 > backoff_0
        assert backoff_2 > backoff_1

    @pytest.mark.asyncio
    async def test_get_stream_stats(self) -> None:
        """Test fetching stream statistics."""
        mock_redis = AsyncMock()
        mock_redis.xinfo_stream = AsyncMock(
            return_value={
                "length": 5000,
                "first-entry": [b"1-0", {"device_id": b"dev-1"}],
                "last-entry": [b"10-0", {"device_id": b"dev-10"}],
            }
        )
        mock_client = MagicMock()
        mock_client.client = mock_redis

        topology = StreamTopology(redis_client=mock_client)

        stats = await topology.get_stream_stats("gps.telemetry.raw")

        assert stats["length"] == 5000
        assert stats["first_entry"] is not None
        assert stats["last_entry"] is not None

    @pytest.mark.asyncio
    async def test_get_consumer_group_stats(self) -> None:
        """Test fetching consumer group statistics."""
        mock_redis = AsyncMock()
        mock_redis.xinfo_groups = AsyncMock(
            return_value=[
                {
                    "name": "group-1",
                    "consumers": 2,
                    "pending": 100,
                    "last-delivered-id": b"1234-0",
                }
            ]
        )
        mock_client = MagicMock()
        mock_client.client = mock_redis

        topology = StreamTopology(redis_client=mock_client)

        stats = await topology.get_consumer_group_stats("gps.telemetry.raw", "group-1")

        assert stats["name"] == "group-1"
        assert stats["consumers"] == 2
        assert stats["pending"] == 100

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """Test closing the topology."""
        mock_client = AsyncMock()
        mock_client.close = AsyncMock()

        topology = StreamTopology(redis_client=mock_client)
        await topology.close()

        mock_client.close.assert_called_once()


class TestStreamConsumer:
    """Tests for StreamConsumer reading and acknowledgment."""

    @pytest.mark.asyncio
    async def test_consumer_creation(self) -> None:
        """Test creating a stream consumer."""
        mock_client = MagicMock()
        topology = StreamTopology(redis_client=mock_client)

        config = ConsumerGroupConfig(
            stream_name="gps.telemetry.raw",
            group_name="ingestion-api:telemetry-processor",
            consumer_name="pod-1",
        )

        consumer = topology.create_consumer(config)

        assert consumer.config.stream_name == "gps.telemetry.raw"
        assert consumer.config.group_name == "ingestion-api:telemetry-processor"

    @pytest.mark.asyncio
    async def test_read_stream(self) -> None:
        """Test reading messages from stream."""
        mock_redis = AsyncMock()
        mock_redis.xreadgroup = AsyncMock(
            return_value=[
                (
                    b"gps.telemetry.raw",
                    [
                        (b"1-0", {b"device_id": b"dev-1", b"latitude": b"40.7128"}),
                        (b"1-1", {b"device_id": b"dev-2", b"latitude": b"34.0522"}),
                    ],
                )
            ]
        )
        mock_client = MagicMock()
        mock_client.client = mock_redis

        topology = StreamTopology(redis_client=mock_client)
        config = ConsumerGroupConfig(
            stream_name="gps.telemetry.raw",
            group_name="test-group",
            consumer_name="test-consumer",
        )
        consumer = topology.create_consumer(config)

        messages = []
        async_gen = consumer.read_stream()
        async for msg in async_gen:
            messages.append(msg)
            if len(messages) >= 2:
                break

        assert len(messages) == 2
        assert messages[0].message_id == "1-0"
        assert messages[0].data["device_id"] == "dev-1"
        assert messages[1].message_id == "1-1"

    @pytest.mark.asyncio
    async def test_ack(self) -> None:
        """Test acknowledging a message."""
        mock_redis = AsyncMock()
        mock_redis.xack = AsyncMock(return_value=1)
        mock_client = MagicMock()
        mock_client.client = mock_redis

        topology = StreamTopology(redis_client=mock_client)
        config = ConsumerGroupConfig(
            stream_name="gps.telemetry.raw",
            group_name="test-group",
            consumer_name="test-consumer",
        )
        consumer = topology.create_consumer(config)

        msg = StreamMessage(
            stream="gps.telemetry.raw",
            message_id="1-0",
            data={"device_id": "dev-1"},
        )

        await consumer.ack(msg)

        mock_redis.xack.assert_called_once_with("gps.telemetry.raw", "test-group", "1-0")

    @pytest.mark.asyncio
    async def test_claim_pending(self) -> None:
        """Test claiming pending entries from other consumers."""
        mock_redis = AsyncMock()
        mock_redis.xautoclaim = AsyncMock(
            return_value=[
                b"0",
                [
                    (b"1-0", {b"device_id": b"dev-1"}),
                    (b"1-1", {b"device_id": b"dev-2"}),
                ],
            ]
        )
        mock_client = MagicMock()
        mock_client.client = mock_redis

        topology = StreamTopology(redis_client=mock_client)
        config = ConsumerGroupConfig(
            stream_name="gps.telemetry.raw",
            group_name="test-group",
            consumer_name="test-consumer",
        )
        consumer = topology.create_consumer(config)

        claimed = await consumer.claim_pending()

        assert len(claimed) == 2
        assert claimed[0].message_id == "1-0"
        assert claimed[1].message_id == "1-1"

    @pytest.mark.asyncio
    async def test_claim_pending_empty(self) -> None:
        """Test claiming when no pending entries exist."""
        mock_redis = AsyncMock()
        mock_redis.xautoclaim = AsyncMock(return_value=[b"0", []])
        mock_client = MagicMock()
        mock_client.client = mock_redis

        topology = StreamTopology(redis_client=mock_client)
        config = ConsumerGroupConfig(
            stream_name="gps.telemetry.raw",
            group_name="test-group",
            consumer_name="test-consumer",
        )
        consumer = topology.create_consumer(config)

        claimed = await consumer.claim_pending()

        assert len(claimed) == 0


class _SuccessfulFrameworkConsumer(AbstractStreamConsumer):
    def __init__(self, topology, config):
        super().__init__(topology, config)
        self.handled: list[str] = []

    async def handle_message(self, message: StreamMessage) -> None:
        self.handled.append(message.message_id)


class _RetryFrameworkConsumer(AbstractStreamConsumer):
    async def handle_message(self, message: StreamMessage) -> None:
        raise RuntimeError("temporary failure")


class _PoisonFrameworkConsumer(AbstractStreamConsumer):
    async def handle_message(self, message: StreamMessage) -> None:
        raise PoisonMessageError("bad payload")


class TestAbstractStreamConsumer:
    def test_message_lag_seconds_parses_redis_stream_id(self) -> None:
        topology = StreamTopology(redis_client=MagicMock())
        consumer = _SuccessfulFrameworkConsumer(
            topology,
            StreamConsumerFrameworkConfig(
                stream_name="gps.telemetry.raw",
                group_name="group-a",
                consumer_name="worker-a",
            ),
        )

        now_ms = int(datetime.now(UTC).timestamp() * 1000)
        lag = consumer._message_lag_seconds(f"{now_ms}-0")

        assert lag is not None
        assert lag >= 0

    @pytest.mark.asyncio
    async def test_process_message_success_acks_and_checkpoints(self) -> None:
        mock_client = MagicMock()
        mock_client.xack = AsyncMock(return_value=1)
        mock_client.set_json = AsyncMock(return_value=True)

        topology = StreamTopology(redis_client=mock_client)
        consumer = _SuccessfulFrameworkConsumer(
            topology,
            StreamConsumerFrameworkConfig(
                stream_name="gps.telemetry.raw",
                group_name="group-a",
                consumer_name="worker-a",
            ),
        )
        message = StreamMessage("gps.telemetry.raw", "1-0", {"device_id": "dev-1"})

        await consumer._process_message(message, "worker-a")

        assert consumer.handled == ["1-0"]
        mock_client.xack.assert_awaited_once_with("gps.telemetry.raw", "group-a", "1-0")
        mock_client.set_json.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_process_message_retries_and_acks(self) -> None:
        mock_client = MagicMock()
        mock_client.xack = AsyncMock(return_value=1)
        mock_client.set_json = AsyncMock(return_value=True)
        mock_client.xadd = AsyncMock(return_value="2-0")

        topology = StreamTopology(redis_client=mock_client)
        consumer = _RetryFrameworkConsumer(
            topology,
            StreamConsumerFrameworkConfig(
                stream_name="gps.telemetry.raw",
                group_name="group-a",
                consumer_name="worker-a",
                retry_stream_name="gps.telemetry.retry",
                max_retries=2,
            ),
        )
        message = StreamMessage("gps.telemetry.raw", "1-0", {"device_id": "dev-1"})

        await consumer._process_message(message, "worker-a")

        mock_client.xadd.assert_awaited_once()
        args = mock_client.xadd.await_args.args
        assert args[0] == "gps.telemetry.retry"
        assert args[1]["retry_count"] == "1"
        assert "backoff_until" in args[1]
        mock_client.xack.assert_awaited_once_with("gps.telemetry.raw", "group-a", "1-0")

    @pytest.mark.asyncio
    async def test_process_message_moves_to_poison_queue(self) -> None:
        mock_client = MagicMock()
        mock_client.xack = AsyncMock(return_value=1)
        mock_client.set_json = AsyncMock(return_value=True)
        mock_client.xadd = AsyncMock(return_value="3-0")

        topology = StreamTopology(redis_client=mock_client)
        consumer = _PoisonFrameworkConsumer(
            topology,
            StreamConsumerFrameworkConfig(
                stream_name="gps.telemetry.raw",
                group_name="group-a",
                consumer_name="worker-a",
                poison_stream_name="gps.telemetry.poison",
            ),
        )
        message = StreamMessage("gps.telemetry.raw", "1-0", {"device_id": "dev-1"})

        await consumer._process_message(message, "worker-a")

        mock_client.xadd.assert_awaited_once()
        args = mock_client.xadd.await_args.args
        assert args[0] == "gps.telemetry.poison"
        assert args[1]["last_error"] == "bad payload"
        mock_client.xack.assert_awaited_once_with("gps.telemetry.raw", "group-a", "1-0")

    @pytest.mark.asyncio
    async def test_start_and_shutdown_manage_parallel_workers(self) -> None:
        mock_client = MagicMock()
        topology = StreamTopology(redis_client=mock_client)
        consumer = _SuccessfulFrameworkConsumer(
            topology,
            StreamConsumerFrameworkConfig(
                stream_name="gps.telemetry.raw",
                group_name="group-a",
                consumer_name="worker-a",
                worker_count=3,
            ),
        )

        started: list[int] = []

        async def fake_worker_loop(index: int) -> None:
            started.append(index)
            await consumer._stop_event.wait()

        consumer._worker_loop = fake_worker_loop  # type: ignore[method-assign]

        await consumer.start()
        assert len(consumer._tasks) == 3
        await asyncio.sleep(0)
        assert started == [0, 1, 2]

        await consumer.shutdown()
        assert consumer._tasks == []

    @pytest.mark.asyncio
    async def test_claim_pending_uses_checkpoint_config(self) -> None:
        mock_client = MagicMock()
        mock_client.xautoclaim = AsyncMock(
            return_value=[b"0", [(b"1-0", {b"device_id": b"dev-1"})]]
        )
        topology = StreamTopology(redis_client=mock_client)
        consumer = _SuccessfulFrameworkConsumer(
            topology,
            StreamConsumerFrameworkConfig(
                stream_name="gps.telemetry.raw",
                group_name="group-a",
                consumer_name="worker-a",
                claim_timeout_ms=1234,
                claim_batch_size=5,
            ),
        )

        claimed = await consumer._claim_pending("worker-a")

        assert [message.message_id for message in claimed] == ["1-0"]
        mock_client.xautoclaim.assert_awaited_once_with(
            "gps.telemetry.raw",
            "group-a",
            "worker-a",
            1234,
            "0",
            count=5,
        )
