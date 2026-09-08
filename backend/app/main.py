from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes.analytics import router as analytics_router
from app.api.routes.analytics_engine import router as analytics_engine_router
from app.api.routes.ingestion import router as ingestion_router
from app.database import get_db

app = FastAPI(
    title="InsightX API",
    description="Social Media Analytics Data Ingestion, Storage & Multi-Layer Analytics Engine",
    version="0.4.7",
)

# Register API Routers
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
