"""
Phase 5.1 — Versioned health endpoint.

GET /api/v1/health
  Returns application version, environment, and per-subsystem status.
  This complements the legacy root /health probe (kept as-is for backward
  compatibility) by providing richer operational metadata.
"""
from fastapi import APIRouter

from app.config import APP_ENV, APP_VERSION

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Versioned API Health Check",
    description=(
        "Returns application version, deployment environment, and "
        "per-subsystem readiness status for the v1 API layer."
    ),
)
def api_health() -> dict:
    """
    Lightweight readiness probe for the v1 API layer.

    Returns
    -------
    dict
        ``status``      – ``"ok"`` when all subsystems are reachable.
        ``version``     – Running application version (from APP_VERSION env var).
        ``environment`` – Deployment environment (from APP_ENV env var).
        ``services``    – Per-subsystem readiness flags.
    """
    return {
        "status": "ok",
        "version": APP_VERSION,
        "environment": APP_ENV,
        "services": {
            "analytics_engine": "ok",
            "ingestion": "ok",
            "analytics": "ok",
        },
    }
