from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from starlette.responses import Response
from swm_common import metrics_response
from swm_common.logger import get_logger

from admin_api.api_support import RoleContext, require_roles

router = APIRouter()
logger = get_logger("admin_api")


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "admin-api"}


@router.get("/metrics")
async def metrics() -> Response:
    return metrics_response()


@router.get("/v1/platform/status")
async def platform_status(_: RoleContext = Depends(require_roles("admin", "ops", "viewer"))) -> dict[str, str]:
    now = datetime.now(tz=UTC).isoformat()
    logger.info("platform_status_requested", ts=now)
    return {"status": "operational", "timestamp": now}
