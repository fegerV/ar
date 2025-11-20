"""
Configuration management for Vertex AR application.
"""
import os
from pathlib import Path
from typing import List


class Settings:
    """Application settings."""
    
    def __init__(self) -> None:
        self.load_environment()
        
    def load_environment(self) -> None:
        """Load configuration from environment variables."""
        # Base paths
        self.BASE_DIR = Path(__file__).resolve().parent.parent
        # Use /app/data for database if it exists (Docker), otherwise use BASE_DIR
        db_dir = Path("/app/data") if Path("/app/data").exists() else self.BASE_DIR
        self.DB_DIR = db_dir
        self.DB_DIR.mkdir(parents=True, exist_ok=True)
        self.DB_PATH = self.DB_DIR / "app_data.db"
        self.STORAGE_ROOT = self.BASE_DIR / "storage"
        self.STATIC_ROOT = self.BASE_DIR / "static"
        
        # Version
        VERSION_FILE = self.BASE_DIR / "VERSION"
        try:
            self.VERSION = VERSION_FILE.read_text().strip()
        except FileNotFoundError:
            self.VERSION = "1.3.0"
            
        # URLs
        self.BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
        
        # Authentication settings
        self.SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
        self.AUTH_MAX_ATTEMPTS = int(os.getenv("AUTH_MAX_ATTEMPTS", "5"))
        self.AUTH_LOCKOUT_MINUTES = int(os.getenv("AUTH_LOCKOUT_MINUTES", "15"))
        
        # Rate limiting settings
        self.RUNNING_TESTS = os.getenv("RUNNING_TESTS") == "1" or "PYTEST_CURRENT_TEST" in os.environ
        self.RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true" and not self.RUNNING_TESTS
        self.GLOBAL_RATE_LIMIT = os.getenv("GLOBAL_RATE_LIMIT", "100/minute")
        self.AUTH_RATE_LIMIT = os.getenv("AUTH_RATE_LIMIT", "5/minute")
        self.UPLOAD_RATE_LIMIT = os.getenv("UPLOAD_RATE_LIMIT", "10/minute")
        
        # CORS settings
        cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
        self.CORS_ORIGINS = [origin.strip() for origin in cors_origins.split(",")]
        
        # Sentry settings
        self.SENTRY_DSN = os.getenv("SENTRY_DSN")
        self.SENTRY_TRACES_SAMPLE_RATE = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
        self.SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))
        
        # Storage settings
        self.STORAGE_TYPE = os.getenv("STORAGE_TYPE", "local")  # local or minio
        self.MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.MINIO_BUCKET = os.getenv("MINIO_BUCKET", "vertex-ar")
        
        # Telegram notifications
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        self.TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
        
        # Email notifications
        self.SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USERNAME = os.getenv("SMTP_USERNAME")
        self.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
        self.EMAIL_FROM = os.getenv("EMAIL_FROM", self.SMTP_USERNAME)
        self.ADMIN_EMAILS = [email.strip() for email in os.getenv("ADMIN_EMAILS", "").split(",") if email.strip()]
        
        # Monitoring and alerting
        self.ALERTING_ENABLED = os.getenv("ALERTING_ENABLED", "true").lower() == "true"
        self.CPU_THRESHOLD = float(os.getenv("CPU_THRESHOLD", "80.0"))  # %
        self.MEMORY_THRESHOLD = float(os.getenv("MEMORY_THRESHOLD", "85.0"))  # %
        self.DISK_THRESHOLD = float(os.getenv("DISK_THRESHOLD", "90.0"))  # %
        self.HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "60"))  # seconds
        self.WEEKLY_REPORT_DAY = os.getenv("WEEKLY_REPORT_DAY", "monday")  # monday, tuesday, etc.
        self.WEEKLY_REPORT_TIME = os.getenv("WEEKLY_REPORT_TIME", "09:00")  # HH:MM format
        
        # File upload settings
        self.MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "50")) * 1024 * 1024  # 50MB default
        self.ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]
        self.ALLOWED_VIDEO_TYPES = ["video/mp4", "video/webm", "video/quicktime"]
        
        # Default admin credentials
        self.DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "superar")
        self.DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "ffE48f0ns@HQ")
        self.DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "superar@vertex-ar.local")
        self.DEFAULT_ADMIN_FULL_NAME = os.getenv("DEFAULT_ADMIN_FULL_NAME", "Super Administrator")
        
        # Ensure directories exist
        self.STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
        self.STATIC_ROOT.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()