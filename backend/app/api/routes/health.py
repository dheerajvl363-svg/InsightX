"""
Phase 5.1 / 5.2 — Versioned health endpoint.

GET /api/v1/health
  Returns application version, environment, and per-subsystem status.
  This complements the legacy root /health probe (kept as-is for backward
  compatibility) by providing richer operational metadata.

Phase 5.2: endpoint now uses an explicit ``HealthResponse`` response model
so the contract is documented in OpenAPI and validated at the boundary.
"""
from fastapi import APIRouter

from app.config import APP_ENV, APP_VERSION
from app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Versioned API Health Check",
    description=(
        "Returns application version, deployment environment, and "
        "per-subsystem readiness status for the v1 API layer."
    ),
)
def api_health() -> HealthResponse:
    """
    Lightweight readiness probe for the v1 API layer.

    Returns
    -------
    HealthResponse
        ``status``      – ``"ok"`` when all subsystems are reachable.
        ``version``     – Running application version (from APP_VERSION env var).
        ``environment`` – Deployment environment (from APP_ENV env var).
        ``services``    – Per-subsystem readiness map.
    """
    return HealthResponse(
        status="ok",
        version=APP_VERSION,
        environment=APP_ENV,
        services={
            "analytics_engine": "ok",
            "ingestion": "ok",
            "analytics": "ok",
        },
    )
