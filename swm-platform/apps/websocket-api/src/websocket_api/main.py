import asyncio

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from jwt import InvalidTokenError
from redis.asyncio import Redis
from swm_auth import decode_access_token
from starlette.responses import Response
from swm_common import (
    REQUEST_COUNTER,
    WEBSOCKET_CONNECTIONS,
    configure_logging,
    get_logger,
    get_settings,
    metrics_response,
)

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("websocket_api")

app = FastAPI(title="SWM WebSocket API", version="0.1.0")
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
LIVE_UPDATES_CHANNEL = "live_updates"
ALERT_EVENTS_CHANNEL = "alert_events"


def _extract_websocket_token(websocket: WebSocket) -> str | None:
    from_query = websocket.query_params.get("token")
    if from_query:
        return from_query.strip()

    authorization = websocket.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token.strip():
        return token.strip()
    return None


def _is_websocket_authenticated(websocket: WebSocket) -> bool:
    token = _extract_websocket_token(websocket)
    if not token:
        return False

    try:
        decode_access_token(token, settings.jwt_secret, settings.jwt_algorithm)
    except InvalidTokenError:
        return False
    return True


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "websocket-api"}


@app.get("/metrics")
async def metrics() -> Response:
    return metrics_response()


@app.websocket("/ws/realtime")
async def realtime_socket(websocket: WebSocket) -> None:
    if not _is_websocket_authenticated(websocket):
        await websocket.close(code=1008)
        return

    await websocket.accept()
    WEBSOCKET_CONNECTIONS.inc()
    pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
    await pubsub.subscribe(LIVE_UPDATES_CHANNEL, ALERT_EVENTS_CHANNEL)
    logger.info("websocket_connected")

    try:
        while True:
            message = await pubsub.get_message(timeout=1.0)
            if message and isinstance(message.get("data"), str):
                await websocket.send_text(message["data"])
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        logger.info("websocket_disconnected")
    finally:
        REQUEST_COUNTER.labels(
            app="websocket-api",
            method="WS",
            path="/ws/realtime",
            status="closed",
        ).inc()
        WEBSOCKET_CONNECTIONS.dec()
        await pubsub.unsubscribe(LIVE_UPDATES_CHANNEL, ALERT_EVENTS_CHANNEL)
        await pubsub.close()


def run() -> None:
    uvicorn.run(
        "websocket_api.main:app",
        host=settings.websocket_api_host,
        port=settings.websocket_api_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
