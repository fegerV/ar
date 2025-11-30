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
        # Internal health check URL (fallback for monitoring when BASE_URL is external)
        # If not set, will auto-build from APP_HOST and APP_PORT
        self.INTERNAL_HEALTH_URL = os.getenv("INTERNAL_HEALTH_URL", "")
        self.APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
        self.APP_PORT = int(os.getenv("APP_PORT", "8000"))
        
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
        self.EMAIL_FROM = os.getenv("EMAIL_FROM")
        self.ADMIN_EMAILS = [email.strip() for email in os.getenv("ADMIN_EMAILS", "").split(",") if email.strip()]
        
        # SECURITY: Check for deprecated env-based SMTP credentials
        # These should be stored encrypted in the database via admin UI
        _env_smtp_username = os.getenv("SMTP_USERNAME")
        _env_smtp_password = os.getenv("SMTP_PASSWORD")
        
        if _env_smtp_username or _env_smtp_password:
            import sys
            from logging_setup import get_logger
            _logger = get_logger(__name__)
            
            warning_msg = (
                "CRITICAL SECURITY WARNING: SMTP credentials detected in environment variables!\n"
                "  Environment-based SMTP_USERNAME and SMTP_PASSWORD are deprecated and insecure.\n"
                "  ACTION REQUIRED:\n"
                "    1. Access the admin notification settings UI at /admin/notification-settings\n"
                "    2. Configure SMTP credentials through the secure encrypted storage interface\n"
                "    3. Remove SMTP_USERNAME and SMTP_PASSWORD from your .env file and environment\n"
                "  See docs/EMAIL_MIGRATION.md for detailed migration instructions."
            )
            
            _logger.critical(warning_msg)
            
            # In production, refuse to start with env-based credentials
            environment = os.getenv("ENVIRONMENT", "development").lower()
            if environment == "production":
                _logger.critical("FATAL: Cannot start in production with env-based SMTP credentials")
                sys.exit(1)
        
        # Do NOT expose SMTP credentials on settings object
        # Runtime code must fetch from encrypted database via NotificationConfig
        self.SMTP_USERNAME = None
        self.SMTP_PASSWORD = None
        
        # Monitoring and alerting
        self.ALERTING_ENABLED = os.getenv("ALERTING_ENABLED", "true").lower() == "true"
        self.CPU_THRESHOLD = float(os.getenv("CPU_THRESHOLD", "80.0"))  # %
        self.MEMORY_THRESHOLD = float(os.getenv("MEMORY_THRESHOLD", "85.0"))  # %
        self.DISK_THRESHOLD = float(os.getenv("DISK_THRESHOLD", "90.0"))  # %
        self.HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "60"))  # seconds
        self.WEEKLY_REPORT_DAY = os.getenv("WEEKLY_REPORT_DAY", "monday")  # monday, tuesday, etc.
        self.WEEKLY_REPORT_TIME = os.getenv("WEEKLY_REPORT_TIME", "09:00")  # HH:MM format
        
        # Alert deduplication and stability settings
        self.MONITORING_CONSECUTIVE_FAILURES = int(os.getenv("MONITORING_CONSECUTIVE_FAILURES", "3"))  # failures before alert
        self.MONITORING_DEDUP_WINDOW = int(os.getenv("MONITORING_DEDUP_WINDOW", "300"))  # seconds (5 minutes)
        self.MONITORING_MAX_RUNTIME = int(os.getenv("MONITORING_MAX_RUNTIME", "0")) if os.getenv("MONITORING_MAX_RUNTIME") else None  # seconds, None = no limit
        self.HEALTH_CHECK_COOLDOWN = int(os.getenv("HEALTH_CHECK_COOLDOWN", "30"))  # seconds between checks
        self.ALERT_RECOVERY_MINUTES = int(os.getenv("ALERT_RECOVERY_MINUTES", "60"))  # minutes before alert can re-fire
        
        # Notification center settings
        self.NOTIFICATION_SYNC_INTERVAL = int(os.getenv("NOTIFICATION_SYNC_INTERVAL", "300"))  # 5 minutes
        self.NOTIFICATION_CLEANUP_INTERVAL = int(os.getenv("NOTIFICATION_CLEANUP_INTERVAL", "3600"))  # 1 hour
        self.NOTIFICATION_RETENTION_DAYS = int(os.getenv("NOTIFICATION_RETENTION_DAYS", "30"))
        self.NOTIFICATION_AUTO_ARCHIVE_HOURS = int(os.getenv("NOTIFICATION_AUTO_ARCHIVE_HOURS", "24"))
        self.NOTIFICATION_DEDUP_WINDOW = int(os.getenv("NOTIFICATION_DEDUP_WINDOW", "300"))  # 5 minutes
        
        # Webhook integration settings
        self.WEBHOOK_URLS = [url.strip() for url in os.getenv("WEBHOOK_URLS", "").split(",") if url.strip()]
        self.WEBHOOK_TIMEOUT = int(os.getenv("WEBHOOK_TIMEOUT", "30"))
        self.WEBHOOK_MAX_RETRIES = int(os.getenv("WEBHOOK_MAX_RETRIES", "3"))
        
        # Notification routing settings
        self.NOTIFICATION_TELEGRAM_ENABLED = os.getenv("NOTIFICATION_TELEGRAM_ENABLED", "true").lower() == "true"
        self.NOTIFICATION_EMAIL_ENABLED = os.getenv("NOTIFICATION_EMAIL_ENABLED", "true").lower() == "true"
        self.NOTIFICATION_WEBHOOK_ENABLED = os.getenv("NOTIFICATION_WEBHOOK_ENABLED", "false").lower() == "true"
        
        # Priority routing thresholds
        self.CRITICAL_NOTIFICATION_ROUTES = os.getenv("CRITICAL_NOTIFICATION_ROUTES", "telegram,email,webhook").split(",")
        self.HIGH_NOTIFICATION_ROUTES = os.getenv("HIGH_NOTIFICATION_ROUTES", "telegram,email").split(",")
        self.MEDIUM_NOTIFICATION_ROUTES = os.getenv("MEDIUM_NOTIFICATION_ROUTES", "email").split(",")
        self.LOW_NOTIFICATION_ROUTES = os.getenv("LOW_NOTIFICATION_ROUTES", "").split(",")
        
        # File upload settings
        self.MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "50")) * 1024 * 1024  # 50MB default
        self.ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]
        self.ALLOWED_VIDEO_TYPES = ["video/mp4", "video/webm", "video/quicktime"]
        
        # Default admin credentials
        self.DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "superar")
        self.DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "ffE48f0ns@HQ")
        self.DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "superar@vertex-ar.local")
        self.DEFAULT_ADMIN_FULL_NAME = os.getenv("DEFAULT_ADMIN_FULL_NAME", "Super Administrator")
        
        # Video animation scheduler settings
        self.VIDEO_SCHEDULER_ENABLED = os.getenv("VIDEO_SCHEDULER_ENABLED", "true").lower() == "true"
        self.VIDEO_SCHEDULER_CHECK_INTERVAL = int(os.getenv("VIDEO_SCHEDULER_CHECK_INTERVAL", "300"))  # 5 minutes
        self.VIDEO_SCHEDULER_ROTATION_INTERVAL = int(os.getenv("VIDEO_SCHEDULER_ROTATION_INTERVAL", "3600"))  # 1 hour
        self.VIDEO_SCHEDULER_ARCHIVE_AFTER_HOURS = int(os.getenv("VIDEO_SCHEDULER_ARCHIVE_AFTER_HOURS", "168"))  # 1 week
        self.VIDEO_SCHEDULER_NOTIFICATIONS_ENABLED = os.getenv("VIDEO_SCHEDULER_NOTIFICATIONS_ENABLED", "true").lower() == "true"
        
        # Lifecycle scheduler settings
        self.LIFECYCLE_SCHEDULER_ENABLED = os.getenv("LIFECYCLE_SCHEDULER_ENABLED", "true").lower() == "true"
        self.LIFECYCLE_CHECK_INTERVAL_SECONDS = int(os.getenv("LIFECYCLE_CHECK_INTERVAL_SECONDS", "3600"))  # 1 hour
        self.LIFECYCLE_NOTIFICATIONS_ENABLED = os.getenv("LIFECYCLE_NOTIFICATIONS_ENABLED", "true").lower() == "true"
        
        # Email service retry settings
        self.EMAIL_RETRY_MAX_ATTEMPTS = int(os.getenv("EMAIL_RETRY_MAX_ATTEMPTS", "5"))
        # Parse EMAIL_RETRY_DELAYS as comma-separated floats (e.g., "1,2,4,8,16")
        retry_delays_str = os.getenv("EMAIL_RETRY_DELAYS", "1,2,4,8,16")
        try:
            self.EMAIL_RETRY_DELAYS = [float(x.strip()) for x in retry_delays_str.split(",")]
        except ValueError:
            self.EMAIL_RETRY_DELAYS = [1, 2, 4, 8, 16]  # Default exponential backoff
        
        # Email default sender
        self.EMAIL_DEFAULT_FROM = os.getenv("EMAIL_DEFAULT_FROM", "")
        
        # Email queue worker settings
        self.EMAIL_QUEUE_WORKERS = int(os.getenv("EMAIL_QUEUE_WORKERS", "3"))
        
        # Yandex Disk storage tuning
        self.YANDEX_REQUEST_TIMEOUT = int(os.getenv("YANDEX_REQUEST_TIMEOUT", "30"))  # seconds
        self.YANDEX_CHUNK_SIZE_MB = int(os.getenv("YANDEX_CHUNK_SIZE_MB", "10"))  # megabytes
        self.YANDEX_UPLOAD_CONCURRENCY = int(os.getenv("YANDEX_UPLOAD_CONCURRENCY", "3"))  # parallel chunks
        self.YANDEX_DIRECTORY_CACHE_TTL = int(os.getenv("YANDEX_DIRECTORY_CACHE_TTL", "300"))  # seconds (5 min)
        self.YANDEX_DIRECTORY_CACHE_SIZE = int(os.getenv("YANDEX_DIRECTORY_CACHE_SIZE", "1000"))  # max entries
        self.YANDEX_SESSION_POOL_CONNECTIONS = int(os.getenv("YANDEX_SESSION_POOL_CONNECTIONS", "10"))
        self.YANDEX_SESSION_POOL_MAXSIZE = int(os.getenv("YANDEX_SESSION_POOL_MAXSIZE", "20"))
        
        # Ensure directories exist
        self.STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
        self.STATIC_ROOT.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()