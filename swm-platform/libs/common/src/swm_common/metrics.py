from typing import Any

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest

REQUEST_COUNTER = Counter(
    "http_requests_total",
    "Count of HTTP requests",
    ["app", "method", "path", "status"],
)

WEBSOCKET_CONNECTIONS = Gauge(
    "websocket_connections",
    "Currently connected websocket clients",
)


def metrics_response() -> Any:
    from starlette.responses import Response

    payload = generate_latest()
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)
