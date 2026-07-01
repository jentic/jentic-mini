"""Admin health check endpoint."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends

from jentic_one.admin.services.health_service import HealthService
from jentic_one.admin.web.deps import get_health_service
from jentic_one.admin.web.schemas.health import HealthResponse

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/health")
async def health(svc: HealthService = Depends(get_health_service)) -> HealthResponse:
    """Return admin service health status."""
    try:
        view = await svc.get_health()
    except Exception:
        logger.debug("health_check_db_unreachable", exc_info=True)
        return HealthResponse(status="ok", surface="admin", setup_required=False)
    return HealthResponse(
        status=view.status,
        surface=view.surface,
        setup_required=view.setup_required,
        next_step=view.next_step,
    )
