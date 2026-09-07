import sys
from pathlib import Path

# Add backend directory to sys.path so app can be imported
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.database import init_db

if __name__ == "__main__":
    print("Initializing InsightX database and Phase 2 schema...")
    init_db()
    print("Database initialization complete.")
