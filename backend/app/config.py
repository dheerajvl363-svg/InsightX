import os
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL = os.getenv("DATABASE_URL")

# Application metadata
APP_ENV = os.getenv("APP_ENV", "development")
APP_VERSION = os.getenv("APP_VERSION", "5.1.0")
DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")

# CORS Configuration
def get_cors_origins(env: str = APP_ENV, raw_origins: str | None = None) -> list[str]:
    """Parse CORS origins from environment variable or return safe environment-specific defaults."""
    if raw_origins is None:
        raw_origins = os.getenv("CORS_ORIGINS", "")

    raw_origins = raw_origins.strip()
    if raw_origins:
        return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

    if env == "production":
        return []

    # Default allowed origins for local frontend development (Next.js, Vite, CRA)
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]


CORS_ORIGINS = get_cors_origins()
