from app.api.routes.analytics import router as analytics_router
from app.api.routes.ingestion import router as ingestion_router

__all__ = ["ingestion_router", "analytics_router"]
