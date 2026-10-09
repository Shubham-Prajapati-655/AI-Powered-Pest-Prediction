import os
import secrets
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
DATA_DIR = BASE_DIR / "data"
DATABASE_DIR = BASE_DIR / "database"
LOGS_DIR = BASE_DIR / "logs"
BACKUPS_DIR = BASE_DIR / "backups"
UPLOADS_DIR = BASE_DIR / "uploads"
AVATARS_DIR = UPLOADS_DIR / "avatars"

# Ensure essential runtime directories exist
for directory in [LOGS_DIR, BACKUPS_DIR, UPLOADS_DIR, AVATARS_DIR, DATABASE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Load environment variables from .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)
except ImportError:
    pass

# Application Settings
APP_NAME = os.getenv("APP_NAME", "AgriAI Advisor")
APP_VERSION = os.getenv("APP_VERSION", "v2.1.0")
APP_ENV = os.getenv("APP_ENV", "production").lower()  # development, staging, production
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# Security & Sessions
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "1440"))  # Default: 24 Hours
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOGIN_LOCKOUT_MINUTES = int(os.getenv("LOGIN_LOCKOUT_MINUTES", "5"))
PASSWORD_RESET_TOKEN_EXPIRY_HOURS = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRY_HOURS", "2"))

# Database Configuration
# Supported schemes: sqlite:///, postgresql://user:pass@host:port/dbname, mysql://user:pass@host:port/dbname
DEFAULT_SQLITE_PATH = DATABASE_DIR / "predictions.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_TIMEOUT_SECONDS = int(os.getenv("DB_TIMEOUT_SECONDS", "10"))

# Default Admin Credentials (Used for seeding if no admin exists)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@agriai.org")
ADMIN_DEFAULT_PASSWORD = os.getenv("ADMIN_DEFAULT_PASSWORD", "Admin@12345")

# Weather API Configuration
WEATHER_API_URL = os.getenv("WEATHER_API_URL", "https://api.open-meteo.com/v1/forecast")
WEATHER_GEOCODING_URL = os.getenv("WEATHER_GEOCODING_URL", "https://geocoding-api.open-meteo.com/v1/search")
WEATHER_API_TIMEOUT = int(os.getenv("WEATHER_API_TIMEOUT", "3"))
WEATHER_API_RETRIES = int(os.getenv("WEATHER_API_RETRIES", "1"))
WEATHER_CACHE_TTL_SECONDS = int(os.getenv("WEATHER_CACHE_TTL_SECONDS", "1800"))  # 30 minutes

# Logging Configuration
LOG_FILE = LOGS_DIR / "agriai.log"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(5 * 1024 * 1024)))  # 5 MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

# Storage & Upload Limits
MAX_AVATAR_SIZE_BYTES = int(os.getenv("MAX_AVATAR_SIZE_MB", "2")) * 1024 * 1024
ALLOWED_AVATAR_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

# SMTP Settings (Optional notification service)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.example.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "True").lower() in ("true", "1", "yes")
