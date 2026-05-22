from collections.abc import Awaitable, Callable
import secrets

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from starlette.responses import Response
from swm_auth import decode_access_token
from swm_common import (
    REQUEST_COUNTER,
    configure_logging,
    get_logger,
    get_settings,
    metrics_response,
)
from swm_redis import RedisClient
from swm_redis import RateLimitRule, RedisRateLimitMiddleware, RedisRateLimiterConfig
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

_bearer_scheme = HTTPBearer(auto_error=False)
_webhook_secret_scheme = APIKeyHeader(name=settings.ingestion_webhook_secret_header, auto_error=False)


def _split_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _canonical_role(role: str | None) -> str:
    if role is None:
        return "read_only"
    aliases = {
        "ops": "operator",
        "operator": "operator",
        "viewer": "read_only",
        "read_only": "read_only",
        "read-only": "read_only",
        "readonly": "read_only",
        "admin": "admin",
        "supervisor": "supervisor",
        "fleet_manager": "fleet_manager",
        "fleet manager": "fleet_manager",
        "analyst": "analyst",
    }
    return aliases.get(role.strip().lower(), role.strip().lower())


def _normalize_roles(values: object, *, fallback: str) -> set[str]:
    roles: set[str] = set()
    if isinstance(values, list):
        roles = {_canonical_role(str(item)) for item in values if str(item).strip()}
    elif isinstance(values, str) and values.strip():
        roles = {_canonical_role(part) for part in values.split(",") if part.strip()}
    if not roles:
        roles = {_canonical_role(fallback)}
    return roles


async def require_ingestion_roles(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
) -> dict[str, object]:
    token = credentials.credentials if credentials else _extract_bearer_token(request.headers.get("authorization"))
    if not token:
        raise HTTPException(status_code=401, detail="authentication required")

    try:
        claims = decode_access_token(token, settings.jwt_secret, settings.jwt_algorithm)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="invalid access token") from exc

    raw_role = claims.get("role")
    if isinstance(raw_role, list):
        raw_role = raw_role[0] if raw_role else None
    role = _canonical_role(str(raw_role)) if raw_role is not None else "read_only"
    roles = _normalize_roles(claims.get("roles", []), fallback=role)
    if role not in roles:
        roles.add(role)

    allowed = {"admin", "supervisor", "operator"}
    if roles.isdisjoint(allowed):
        raise HTTPException(status_code=403, detail="forbidden")

    return {"subject": str(claims.get("sub", "jwt-user")), "roles": sorted(roles)}


async def require_webhook_provider_auth(
    secret_value: str | None = Security(_webhook_secret_scheme),
) -> dict[str, object]:
    if not settings.ingestion_webhook_auth_enabled:
        return {"auth": "disabled"}

    expected_secret = settings.ingestion_webhook_secret.strip()
    if not expected_secret:
        raise HTTPException(status_code=500, detail="webhook auth misconfigured")

    if not secret_value:
        raise HTTPException(status_code=401, detail="webhook secret header missing")

    if not secrets.compare_digest(secret_value, expected_secret):
        raise HTTPException(status_code=401, detail="webhook secret invalid")

    return {"auth": "webhook-secret"}


if settings.ingestion_rate_limit_enabled:
    app.add_middleware(
        RedisRateLimitMiddleware,
        redis_client=redis_client,
        config=RedisRateLimiterConfig(
            key_prefix=settings.ingestion_rate_limit_prefix,
            global_rule=RateLimitRule(
                limit=settings.ingestion_rate_limit_global_limit,
                window_seconds=settings.ingestion_rate_limit_global_window_seconds,
            ),
            vendor_rule=RateLimitRule(
                limit=settings.ingestion_rate_limit_vendor_limit,
                window_seconds=settings.ingestion_rate_limit_vendor_window_seconds,
            ),
            ip_rule=RateLimitRule(
                limit=settings.ingestion_rate_limit_ip_limit,
                window_seconds=settings.ingestion_rate_limit_ip_window_seconds,
            ),
            imei_rule=RateLimitRule(
                limit=settings.ingestion_rate_limit_imei_limit,
                window_seconds=settings.ingestion_rate_limit_imei_window_seconds,
            ),
        ),
    )

# Register webhook routers
app.include_router(
    make_gps_webhook_router(
        redis_client=redis_client,
        auth_dependency=require_webhook_provider_auth,
    )
)


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
async def ingest_events(batch: EventBatch, _: dict[str, object] = Security(require_ingestion_roles)) -> JSONResponse:
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
