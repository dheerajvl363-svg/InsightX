import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL
from app.models.base import Base
# Import all models so that Base.metadata knows about them
import app.models  # noqa: F401

logger = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initializes the database schema non-destructively:
    1. Creates all tables registered in Base.metadata if they do not exist.
    2. Applies safe non-destructive ALTERs for Phase 2 fields.
    3. Creates performance and analytical indexes.
    4. Seeds initial platforms if missing.
    """
    # Create any missing tables
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        # Non-destructive migrations for posts table
        conn.execute(text("ALTER TABLE posts ALTER COLUMN user_id DROP NOT NULL;"))
        conn.execute(text("ALTER TABLE posts ADD COLUMN IF NOT EXISTS url VARCHAR(512);"))
        conn.execute(text("ALTER TABLE posts ADD COLUMN IF NOT EXISTS language VARCHAR(10);"))
        conn.execute(text("ALTER TABLE posts ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;"))
        conn.execute(text("ALTER TABLE posts ADD COLUMN IF NOT EXISTS raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb;"))

        # Safe index creation
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_posts_posted_at ON posts (posted_at DESC);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_posts_collected_at ON posts (collected_at DESC);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_posts_platform_id ON posts (platform_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_posts_language ON posts (language);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_post_metrics_post_id ON post_metrics (post_id);"))

        # Seed initial standard platforms if missing
        standard_platforms = ["X", "Telegram", "Reddit", "YouTube"]
        for p_name in standard_platforms:
            conn.execute(
                text("INSERT INTO platforms (name) VALUES (:name) ON CONFLICT (name) DO NOTHING;"),
                {"name": p_name}
            )

    logger.info("Database initialized and Phase 2 schema verified successfully.")
