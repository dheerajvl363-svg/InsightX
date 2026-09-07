from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes.ingestion import router as ingestion_router
from app.database import get_db

app = FastAPI(
    title="InsightX API",
    description="Social Media Analytics Data Ingestion & Processing Pipeline",
    version="0.2.0",
)

# Register Ingestion API Router
app.include_router(ingestion_router, prefix="/api/v1/ingestion")


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


@app.get("/db-health", tags=["Health"])
def database_health(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT current_database();"))
    return {"database": result.scalar()}
