import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.errors import setup_exception_handlers
from app.api.routes.analytics import router as analytics_router
from app.api.routes.analytics_engine import router as analytics_engine_router
from app.api.routes.health import router as health_router
from app.api.routes.ingestion import router as ingestion_router
from app.api.routes.platforms import router as platforms_router
from app.api.routes.posts import router as posts_router
from app.api.routes.timeline import router as timeline_router
from app.config import APP_ENV, APP_VERSION, CORS_ORIGINS, DEBUG
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

tags_metadata = [
    {
        "name": "Health",
        "description": "System readiness, database connectivity, and subsystem status probes.",
    },
    {
        "name": "Posts",
        "description": "Social media post retrieval, full-text searching, metrics filtering, and pagination.",
    },
    {
        "name": "Platforms",
        "description": "Supported platform discovery and metadata enumeration.",
    },
    {
        "name": "Timeline",
        "description": "Chronological post volume aggregations and platform distribution timeline bucketing.",
    },
    {
        "name": "Analytics",
        "description": "High-level dashboard analytics: sentiment, topics, trends, network graphs, overview, and platform comparisons.",
    },
    {
        "name": "Ingestion",
        "description": "Raw post ingestion, batch processing, and adapter discovery.",
    },
    {
        "name": "Analytics Engine",
        "description": "Standalone low-level NLP, sentiment, trend, narrative, and demographic analysis services.",
    },
]

app = FastAPI(
    title="InsightX Social Media Analytics API",
    description=(
        "InsightX provides AI-driven multi-platform social media intelligence across X, Telegram, "
        "Reddit, and YouTube. Features data ingestion, automated normalisation, engagement analytics, "
        "sentiment detection, trend momentum tracking, narrative cluster analysis, and time-series dynamic modeling."
    ),
    version=APP_VERSION,
    debug=DEBUG,
    lifespan=lifespan,
    openapi_tags=tags_metadata,
)

# --- Phase 5.9: Configurable CORS middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Phase 5.6: Global exception handlers ---
setup_exception_handlers(app)

# --- Phase 5.1: versioned v1 API routers ---
app.include_router(health_router, prefix="/api/v1")

# --- Phase 5.4: Posts, Platforms & Timeline REST API routers ---
app.include_router(posts_router, prefix="/api/v1/posts")
app.include_router(platforms_router, prefix="/api/v1/platforms")
app.include_router(timeline_router, prefix="/api/v1/timeline")

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
