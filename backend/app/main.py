import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes.analytics import router as analytics_router
from app.api.routes.analytics_engine import router as analytics_engine_router
from app.api.routes.health import router as health_router
from app.api.routes.ingestion import router as ingestion_router
from app.config import APP_ENV, APP_VERSION, DEBUG
from app.database import get_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):  # noqa: RUF029
    """Application lifespan: runs startup logic, yields, then runs shutdown logic."""
    logger.info(
        "InsightX API starting up — version=%s env=%s debug=%s",
        APP_VERSION,
        APP_ENV,
        DEBUG,
    )
    yield
    logger.info("InsightX API shutting down.")

app = FastAPI(
    title="InsightX API",
    description=(
        "Social Media Analytics — Data Ingestion, Storage & Multi-Layer Analytics Engine. "
        "Phases 0–5: ingestion adapters, normalisation, engagement analytics, sentiment, "
        "trend momentum, narrative intelligence, and time-series dynamics."
    ),
    version=APP_VERSION,
    debug=DEBUG,
    lifespan=lifespan,
)

# --- Phase 5.1: versioned v1 API routers ---
app.include_router(health_router, prefix="/api/v1")

# --- Phase 1–4: existing routers (unchanged) ---
app.include_router(ingestion_router, prefix="/api/v1/ingestion")
app.include_router(analytics_router, prefix="/api/v1/analytics")
app.include_router(analytics_engine_router, prefix="/api/v1/analytics/engine")



@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


@app.get("/db-health", tags=["Health"])
def database_health(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT current_database();"))
    return {"database": result.scalar()}
