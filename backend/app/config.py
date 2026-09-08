import os
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL = os.getenv("DATABASE_URL")

# Application metadata
APP_ENV = os.getenv("APP_ENV", "development")
APP_VERSION = os.getenv("APP_VERSION", "5.1.0")
DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")
