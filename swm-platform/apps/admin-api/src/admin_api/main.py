from collections.abc import Awaitable, Callable
import os

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
from swm_common import (
    REQUEST_COUNTER,
    configure_logging,
    get_settings,
)

from admin_api.routers import system as system_router
from admin_api.routers import auth as auth_router

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title="SWM Admin API", version="0.1.0")

_cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8080,http://127.0.0.1:8080",
    ).split(",")
    if origin.strip()
]

# CORS origins should represent browser UI origins, not API service ports.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    response = await call_next(request)
    REQUEST_COUNTER.labels(
        app="admin-api",
        method=request.method,
        path=request.url.path,
        status=str(response.status_code),
    ).inc()
    return response


app.include_router(system_router.router)
app.include_router(auth_router.router)

# Imported here to avoid circular imports for routers that reference symbols from this module.
from admin_api.routers import realtime as realtime_router  # noqa: PLC0415

app.include_router(realtime_router.router)

# Imported here to avoid circular imports for routers that reference symbols from this module.
from admin_api.routers import operations as operations_router  # noqa: PLC0415

app.include_router(operations_router.router)

# Imported here to avoid circular imports for routers that reference symbols from this module.
from admin_api.routers import master_data as master_data_router  # noqa: PLC0415

app.include_router(master_data_router.router)


# Imported here to avoid circular imports for routers that reference symbols from this module.
from admin_api.routers import analytics as analytics_router  # noqa: PLC0415

app.include_router(analytics_router.router)


# Imported here to avoid circular imports for routers that reference symbols from this module.
from admin_api.routers import dashboard as dashboard_router  # noqa: PLC0415

app.include_router(dashboard_router.router)


def run() -> None:
    uvicorn.run(
        "admin_api.main:app",
        host=settings.admin_api_host,
        port=settings.admin_api_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
