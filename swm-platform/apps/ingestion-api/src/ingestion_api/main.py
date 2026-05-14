from collections.abc import Awaitable, Callable

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.responses import Response
from swm_common import (
    REQUEST_COUNTER,
    configure_logging,
    get_logger,
    get_settings,
    metrics_response,
)
from swm_redis import RedisClient
from swm_schemas import EventBatch

from ingestion_api.webhook_gps import make_gps_webhook_router

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("ingestion_api")

app = FastAPI(title="SWM Ingestion API", version="0.1.0")
redis_client = RedisClient.from_url(
    settings.redis_url,
    max_connections=settings.redis_max_connections,
    socket_timeout=settings.redis_socket_timeout,
    socket_connect_timeout=settings.redis_socket_connect_timeout,
    retry_attempts=settings.redis_retry_attempts,
    retry_base_delay=settings.redis_retry_base_delay,
)

# Register webhook routers
app.include_router(make_gps_webhook_router(redis_client=redis_client))


@app.middleware("http")
async def metrics_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    response = await call_next(request)
    REQUEST_COUNTER.labels(
        app="ingestion-api",
        method=request.method,
        path=request.url.path,
        status=str(response.status_code),
    ).inc()
    return response


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "ingestion-api"}


@app.get("/metrics")
async def metrics() -> Response:
    return metrics_response()


@app.post("/v1/events", status_code=status.HTTP_202_ACCEPTED)
async def ingest_events(batch: EventBatch) -> JSONResponse:
    total = len(batch.events)
    for event in batch.events:
        await redis_client.publish(channel="telemetry.events", payload=event.model_dump_json())
    logger.info("events_ingested", count=total)
    return JSONResponse(content={"accepted": total}, status_code=status.HTTP_202_ACCEPTED)


def run() -> None:
    uvicorn.run(
        "ingestion_api.main:app",
        host=settings.ingestion_api_host,
        port=settings.ingestion_api_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
