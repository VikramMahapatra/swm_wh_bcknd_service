from __future__ import annotations

import argparse
import asyncio
import json
import os
from uuid import uuid4

from swm_redis import (
    RedisClient,
    RedisReplayPipeline,
    ReplayJobKind,
    ReplayJobRequest,
    StreamTopology,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Replay telemetry from DLQ/retry streams "
            "into target stream for recovery operations."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["queue", "process", "status"],
        default="queue",
        help=(
            "queue: enqueue replay job in replay.jobs, "
            "process: execute immediately, status: query progress"
        ),
    )
    parser.add_argument("--redis-url", default=os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    parser.add_argument(
        "--job-id",
        default="",
        help="Replay job ID. Auto-generated when omitted in queue/process mode",
    )
    parser.add_argument("--source-stream", default="gps.telemetry.failed")
    parser.add_argument("--target-stream", default="gps.telemetry.raw")
    parser.add_argument("--start-id", default="-")
    parser.add_argument("--end-id", default="+")
    parser.add_argument("--max-messages", type=int, default=1000)
    parser.add_argument("--priority", type=int, default=8)
    parser.add_argument(
        "--kind",
        choices=[ReplayJobKind.DEAD_LETTER.value, ReplayJobKind.BACKFILL.value],
        default=ReplayJobKind.DEAD_LETTER.value,
    )
    return parser


def _print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


async def _run(args: argparse.Namespace) -> int:
    redis_client = RedisClient.from_url(args.redis_url)
    topology = StreamTopology(redis_client=redis_client)
    pipeline = RedisReplayPipeline(topology)

    job_id = args.job_id or str(uuid4())

    if args.mode == "status":
        if not args.job_id:
            print("--job-id is required in status mode")
            return 2
        progress = await pipeline.get_progress(args.job_id)
        if progress is None:
            _print_json({"job_id": args.job_id, "status": "not_found"})
            return 1
        _print_json(progress.to_dict())
        return 0

    kind = ReplayJobKind(args.kind)
    target_stream = args.target_stream or None
    max_messages = args.max_messages if args.max_messages and args.max_messages > 0 else None

    if args.mode == "queue":
        if kind is ReplayJobKind.DEAD_LETTER:
            replay_message_id = await pipeline.enqueue_dead_letter_reprocess(
                job_id=job_id,
                poison_stream=args.source_stream,
                target_stream=target_stream,
                start_id=args.start_id,
                end_id=args.end_id,
                max_messages=max_messages,
                priority=args.priority,
            )
        else:
            if target_stream is None:
                print("--target-stream is required for backfill jobs")
                return 2
            replay_message_id = await pipeline.enqueue_backfill(
                job_id=job_id,
                source_stream=args.source_stream,
                target_stream=target_stream,
                start_id=args.start_id,
                end_id=args.end_id,
                max_messages=max_messages,
                priority=args.priority,
            )
        _print_json(
            {
                "action": "queued",
                "job_id": job_id,
                "replay_message_id": replay_message_id,
                "kind": kind.value,
                "source_stream": args.source_stream,
                "target_stream": target_stream,
                "max_messages": max_messages,
            }
        )
        return 0

    job = ReplayJobRequest(
        job_id=job_id,
        kind=kind,
        source_stream=args.source_stream,
        target_stream=target_stream,
        start_id=args.start_id,
        end_id=args.end_id,
        max_messages=max_messages,
        priority=args.priority,
    )
    progress = await pipeline.process_job(job)
    _print_json(progress.to_dict())
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
