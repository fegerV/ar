"""
Database module for Vertex AR application.
Contains all database operations and models.
"""
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from logging_setup import get_logger

logger = get_logger(__name__)


class Database:
    """Simplified database with just users and AR content."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        # Ensure directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(str(self.path), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        # Enable foreign key constraints for cascade delete
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._initialise_schema()

    def _initialise_schema(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    hashed_password TEXT NOT NULL,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    email TEXT,
                    full_name TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ar_content (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    image_path TEXT NOT NULL,
                    video_path TEXT NOT NULL,
                    image_preview_path TEXT,
                    video_preview_path TEXT,
                    marker_fset TEXT NOT NULL,
                    marker_fset3 TEXT NOT NULL,
                    marker_iset TEXT NOT NULL,
                    ar_url TEXT NOT NULL,
                    qr_code TEXT,
                    view_count INTEGER NOT NULL DEFAULT 0,
                    click_count INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(username) REFERENCES users(username)
                )
                """
            )
            # Create companies table
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS companies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Create projects table
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE,
                    UNIQUE(company_id, name)
                )
                """
            )

            # Create folders table
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS folders (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    UNIQUE(project_id, name)
                )
                """
            )

            # Create new tables for clients, portraits and videos
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS clients (
                    id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE,
                    UNIQUE(company_id, phone)
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS portraits (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    image_path TEXT NOT NULL,
                    image_preview_path TEXT,
                    marker_fset TEXT NOT NULL,
                    marker_fset3 TEXT NOT NULL,
                    marker_iset TEXT NOT NULL,
                    permanent_link TEXT NOT NULL UNIQUE,
                    qr_code TEXT,
                    view_count INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS videos (
                    id TEXT PRIMARY KEY,
                    portrait_id TEXT NOT NULL,
                    video_path TEXT NOT NULL,
                    video_preview_path TEXT,
                    description TEXT,
                    is_active INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(portrait_id) REFERENCES portraits(id) ON DELETE CASCADE
                )
                """
            )
            # Ensure default company exists
            try:
                cursor = self._connection.execute("SELECT id FROM companies WHERE name = 'Vertex AR' LIMIT 1")
                if not cursor.fetchone():
                    # Try with new columns first, fall back to basic columns if they don't exist yet
                    try:
                        self._connection.execute(
                            "INSERT INTO companies (id, name, storage_type, content_types) VALUES (?, ?, ?, ?)",
                            ("vertex-ar-default", "Vertex AR", "local", "portraits:Portraits")
                        )
                    except sqlite3.OperationalError:
                        # Fall back to basic columns (for initial schema creation)
                        self._connection.execute(
                            "INSERT INTO companies (id, name) VALUES (?, ?)",
                            ("vertex-ar-default", "Vertex AR")
                        )
                    self._connection.commit()
                    logger.info("Created default company 'Vertex AR'")
            except sqlite3.OperationalError as e:
                logger.warning(f"Error ensuring default company: {e}")

            # Migrate existing clients to default company if needed
            try:
                cursor = self._connection.execute("SELECT COUNT(*) FROM clients WHERE company_id IS NULL")
                if cursor.fetchone()[0] > 0:
                    # Add company_id column if it doesn't exist
                    self._connection.execute(
                        "UPDATE clients SET company_id = 'vertex-ar-default' WHERE company_id IS NULL"
                    )
                    self._connection.commit()
                    logger.info("Migrated existing clients to default company")
            except sqlite3.OperationalError:
                pass

            # Add columns to existing tables if they don't exist
            try:
                self._connection.execute("ALTER TABLE ar_content ADD COLUMN image_preview_path TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE ar_content ADD COLUMN video_preview_path TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE ar_content ADD COLUMN view_count INTEGER NOT NULL DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE ar_content ADD COLUMN click_count INTEGER NOT NULL DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE videos ADD COLUMN description TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE videos ADD COLUMN file_size_mb INTEGER")
            except sqlite3.OperationalError:
                pass
            
            # Add video animation scheduling fields
            try:
                self._connection.execute("ALTER TABLE videos ADD COLUMN start_datetime TIMESTAMP")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE videos ADD COLUMN end_datetime TIMESTAMP")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE videos ADD COLUMN rotation_type TEXT DEFAULT 'none' CHECK (rotation_type IN ('none', 'sequential', 'cyclic'))")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE videos ADD COLUMN status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'archived'))")
            except sqlite3.OperationalError:
                pass
            
            # Create table for video schedule history
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS video_schedule_history (
                    id TEXT PRIMARY KEY,
                    video_id TEXT NOT NULL,
                    old_status TEXT,
                    new_status TEXT NOT NULL,
                    change_reason TEXT NOT NULL,
                    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    changed_by TEXT,  -- username or 'system'
                    FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE CASCADE
                )
                """
            )
            
            # Create indexes for scheduling
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_videos_start_end ON videos(start_datetime, end_datetime)")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status)")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_videos_portrait_active ON videos(portrait_id, is_active)")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_video_schedule_history_video ON video_schedule_history(video_id)")
            except sqlite3.OperationalError:
                pass
            # Create index for phone search
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_clients_phone ON clients(phone)")
            except sqlite3.OperationalError:
                pass

            # Add folder_id column to portraits table
            try:
                self._connection.execute("ALTER TABLE portraits ADD COLUMN folder_id TEXT")
            except sqlite3.OperationalError:
                pass
            
            # Add lifecycle management columns to portraits table
            try:
                self._connection.execute("ALTER TABLE portraits ADD COLUMN subscription_end TIMESTAMP")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE portraits ADD COLUMN lifecycle_status TEXT DEFAULT 'active' CHECK (lifecycle_status IN ('active', 'expiring', 'archived'))")
            except sqlite3.OperationalError:
                pass
            
            # Add notification tracking columns for lifecycle management
            try:
                self._connection.execute("ALTER TABLE portraits ADD COLUMN notification_7days_sent TIMESTAMP")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE portraits ADD COLUMN notification_24hours_sent TIMESTAMP")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE portraits ADD COLUMN notification_expired_sent TIMESTAMP")
            except sqlite3.OperationalError:
                pass
            
            # Add email column to clients table
            try:
                self._connection.execute("ALTER TABLE clients ADD COLUMN email TEXT")
            except sqlite3.OperationalError:
                pass
            
            # Create index for email lookups in clients table
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_clients_email ON clients(company_id, email)")
            except sqlite3.OperationalError:
                pass
            
            # Add lifecycle management columns to projects table
            try:
                self._connection.execute("ALTER TABLE projects ADD COLUMN status TEXT DEFAULT 'active' CHECK (status IN ('active', 'expiring', 'archived'))")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE projects ADD COLUMN subscription_end TIMESTAMP")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE projects ADD COLUMN last_status_change TIMESTAMP")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE projects ADD COLUMN notified_7d TIMESTAMP")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE projects ADD COLUMN notified_24h TIMESTAMP")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE projects ADD COLUMN notified_expired TIMESTAMP")
            except sqlite3.OperationalError:
                pass
            
            # Add last_status_change to portraits table
            try:
                self._connection.execute("ALTER TABLE portraits ADD COLUMN last_status_change TIMESTAMP")
            except sqlite3.OperationalError:
                pass

            # Create indexes for projects and folders
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_projects_company ON projects(company_id)")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_folders_project ON folders(project_id)")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_portraits_folder ON portraits(folder_id)")
            except sqlite3.OperationalError:
                pass

            # Migrate existing users table to new schema
            try:
                self._connection.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE users ADD COLUMN email TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")
            except sqlite3.OperationalError:
                pass

            # Create indexes for user management
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)")
            except sqlite3.OperationalError:
                pass

            # Create storage_connections table for managing multiple storage connections
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS storage_connections (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    type TEXT NOT NULL CHECK (type IN ('local', 'minio', 'yandex_disk')),
                    config TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    is_tested INTEGER NOT NULL DEFAULT 0,
                    test_result TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Create admin_settings table for Yandex Disk OAuth and SMTP settings
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    yandex_client_id TEXT,
                    yandex_client_secret_encrypted TEXT,
                    yandex_redirect_uri TEXT,
                    yandex_smtp_email TEXT,
                    yandex_smtp_password_encrypted TEXT,
                    yandex_connection_status TEXT DEFAULT 'disconnected' CHECK (yandex_connection_status IN ('connected', 'disconnected', 'reconnect_needed')),
                    yandex_smtp_status TEXT DEFAULT 'disconnected' CHECK (yandex_smtp_status IN ('connected', 'disconnected', 'reconnect_needed')),
                    last_tested_at TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Add storage columns to companies table
            try:
                self._connection.execute("ALTER TABLE companies ADD COLUMN storage_connection_id TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE companies ADD COLUMN storage_type TEXT NOT NULL DEFAULT 'local'")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE companies ADD COLUMN yandex_disk_folder_id TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE companies ADD COLUMN content_types TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE companies ADD COLUMN storage_folder_path TEXT")
            except sqlite3.OperationalError:
                pass
            
            # Backfill default content_types for existing companies with NULL values
            try:
                cursor = self._connection.execute("SELECT COUNT(*) FROM companies WHERE content_types IS NULL")
                if cursor.fetchone()[0] > 0:
                    self._connection.execute(
                        "UPDATE companies SET content_types = 'portraits:Portraits' WHERE content_types IS NULL"
                    )
                    self._connection.commit()
                    logger.info("Backfilled default content_types for existing companies")
            except sqlite3.OperationalError:
                pass
            
            # Backfill default storage_folder_path for existing companies with NULL values
            try:
                cursor = self._connection.execute("SELECT COUNT(*) FROM companies WHERE storage_folder_path IS NULL")
                if cursor.fetchone()[0] > 0:
                    self._connection.execute(
                        "UPDATE companies SET storage_folder_path = 'vertex_ar_content' WHERE storage_folder_path IS NULL"
                    )
                    self._connection.commit()
                    logger.info("Backfilled default storage_folder_path for existing companies")
            except sqlite3.OperationalError:
                pass

            # Add foreign key constraint for storage_connection_id
            try:
                self._connection.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS fk_companies_storage_connection
                    BEFORE INSERT ON companies
                    BEGIN
                        SELECT CASE
                            WHEN NEW.storage_connection_id IS NOT NULL AND 
                                 (SELECT COUNT(*) FROM storage_connections WHERE id = NEW.storage_connection_id) = 0
                            THEN RAISE(ABORT, 'Foreign key violation: storage_connection_id')
                        END;
                    END
                    """
                )
            except sqlite3.OperationalError:
                pass

            # Create index for storage connections
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_storage_connections_type ON storage_connections(type)")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_storage_connections_active ON storage_connections(is_active)")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_companies_storage ON companies(storage_connection_id)")
            except sqlite3.OperationalError:
                pass

            # Create notification_settings table for centralized email and Telegram settings
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS notification_settings (
                    id TEXT PRIMARY KEY,
                    smtp_host TEXT,
                    smtp_port INTEGER,
                    smtp_username TEXT,
                    smtp_password_encrypted TEXT,
                    smtp_from_email TEXT,
                    smtp_use_tls INTEGER DEFAULT 1,
                    smtp_use_ssl INTEGER DEFAULT 0,
                    telegram_bot_token_encrypted TEXT,
                    telegram_chat_ids TEXT,
                    event_log_errors INTEGER DEFAULT 1,
                    event_db_issues INTEGER DEFAULT 1,
                    event_disk_space INTEGER DEFAULT 1,
                    event_resource_monitoring INTEGER DEFAULT 1,
                    event_backup_success INTEGER DEFAULT 1,
                    event_info_notifications INTEGER DEFAULT 1,
                    disk_threshold_percent INTEGER DEFAULT 90,
                    cpu_threshold_percent INTEGER DEFAULT 80,
                    memory_threshold_percent INTEGER DEFAULT 85,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Create notification_history table for tracking sent notifications
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS notification_history (
                    id TEXT PRIMARY KEY,
                    notification_type TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    subject TEXT,
                    message TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('sent', 'failed')),
                    error_message TEXT,
                    sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Create indexes for notification tables
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_notification_history_type ON notification_history(notification_type)")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_notification_history_status ON notification_history(status)")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_notification_history_sent_at ON notification_history(sent_at)")
            except sqlite3.OperationalError:
                pass

            # Create email_templates table for managing HTML email templates
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS email_templates (
                    id TEXT PRIMARY KEY,
                    template_type TEXT NOT NULL CHECK (template_type IN ('subscription_end', 'system_error', 'admin_report')),
                    subject TEXT NOT NULL,
                    html_content TEXT NOT NULL,
                    variables_used TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Create indexes for email_templates table
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_email_templates_type ON email_templates(template_type)")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_email_templates_active ON email_templates(is_active)")
            except sqlite3.OperationalError:
                pass
            
            # Create email_queue table for persistent email queue
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS email_queue (
                    id TEXT PRIMARY KEY,
                    recipient_to TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    html TEXT,
                    template_id TEXT,
                    variables TEXT,
                    status TEXT NOT NULL CHECK (status IN ('pending', 'sending', 'sent', 'failed')) DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            
            # Create indexes for email_queue table
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_email_queue_status ON email_queue(status)")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_email_queue_created_at ON email_queue(created_at)")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_email_queue_status_created ON email_queue(status, created_at)")
            except sqlite3.OperationalError:
                pass
            
            # Create monitoring_settings table for persisted monitoring configuration
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS monitoring_settings (
                    id TEXT PRIMARY KEY,
                    cpu_threshold REAL NOT NULL DEFAULT 80.0,
                    memory_threshold REAL NOT NULL DEFAULT 85.0,
                    disk_threshold REAL NOT NULL DEFAULT 90.0,
                    health_check_interval INTEGER NOT NULL DEFAULT 60,
                    consecutive_failures INTEGER NOT NULL DEFAULT 3,
                    dedup_window_seconds INTEGER NOT NULL DEFAULT 300,
                    max_runtime_seconds INTEGER DEFAULT NULL,
                    health_check_cooldown_seconds INTEGER NOT NULL DEFAULT 30,
                    alert_recovery_minutes INTEGER NOT NULL DEFAULT 60,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            
            # Seed default monitoring settings if none exist
            self._seed_default_monitoring_settings()
            
            # Seed default email templates
            self._seed_default_email_templates()

    def _execute(self, query: str, parameters: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        with self._lock:
            cursor = self._connection.execute(query, parameters)
            self._connection.commit()
            return cursor

    # User methods (for admin authentication and profile management only)
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        cursor = self._execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def update_user(self, username: str, **kwargs) -> bool:
        """Update user fields."""
        if not kwargs:
            return False

        # Filter valid fields
        valid_fields = {'email', 'full_name', 'is_admin', 'is_active'}
        update_fields = {k: v for k, v in kwargs.items() if k in valid_fields and v is not None}

        if not update_fields:
            return False

        set_clause = ", ".join(f"{field} = ?" for field in update_fields.keys())
        values = list(update_fields.values()) + [username]

        cursor = self._execute(
            f"UPDATE users SET {set_clause} WHERE username = ?",
            values
        )
        return cursor.rowcount > 0

    def update_last_login(self, username: str) -> None:
        """Update the last login timestamp for a user."""
        self._execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?",
            (username,)
        )

    def change_password(self, username: str, new_hashed_password: str) -> bool:
        """Change user password."""
        cursor = self._execute(
            "UPDATE users SET hashed_password = ? WHERE username = ?",
            (new_hashed_password, username)
        )
        return cursor.rowcount > 0

    def create_user(
        self,
        username: str,
        hashed_password: str,
        *,
        is_admin: bool = False,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> bool:
        """Create a new user."""
        cursor = self._execute(
            "INSERT INTO users (username, hashed_password, is_admin, email, full_name) VALUES (?, ?, ?, ?, ?)",
            (username, hashed_password, int(is_admin), email, full_name)
        )
        return cursor.rowcount > 0

    def ensure_admin_user(
        self,
        username: str,
        hashed_password: str,
        *,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> None:
        """Ensure that a given user exists with admin privileges and active status."""
        try:
            user = self.get_user(username)
            if user is None:
                self.create_user(
                    username=username,
                    hashed_password=hashed_password,
                    is_admin=True,
                    email=email,
                    full_name=full_name,
                )
                logger.info("Default admin user created", username=username)
                return
            updates: Dict[str, Any] = {}
            if not bool(user.get("is_admin", 0)):
                updates["is_admin"] = True
            if not bool(user.get("is_active", 1)):
                updates["is_active"] = True
            if email is not None and user.get("email") != email:
                updates["email"] = email
            if full_name is not None and user.get("full_name") != full_name:
                updates["full_name"] = full_name
            if updates:
                self.update_user(username, **updates)
                logger.info("Default admin user updated", username=username, updates=list(updates.keys()))
            if user.get("hashed_password") != hashed_password:
                self.change_password(username, hashed_password)
                logger.info("Default admin password refreshed", username=username)
        except Exception as exc:
            logger.error("Failed to ensure default admin user", username=username, exc_info=exc)
            raise

    # AR Content methods
    def create_ar_content(
        self,
        content_id: str,
        username: str,
        image_path: str,
        video_path: str,
        marker_fset: str,
        marker_fset3: str,
        marker_iset: str,
        ar_url: str,
        qr_code: Optional[str],
        image_preview_path: Optional[str] = None,
        video_preview_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._execute(
            """
            INSERT INTO ar_content (
                id, username, image_path, video_path,
                image_preview_path, video_preview_path,
                marker_fset, marker_fset3, marker_iset,
                ar_url, qr_code
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (content_id, username, image_path, video_path,
             image_preview_path, video_preview_path,
             marker_fset, marker_fset3, marker_iset, ar_url, qr_code),
        )
        return self.get_ar_content(content_id)

    def get_ar_content(self, content_id: str) -> Optional[Dict[str, Any]]:
        cursor = self._execute("SELECT * FROM ar_content WHERE id = ?", (content_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def list_ar_content(self, username: Optional[str] = None) -> List[Dict[str, Any]]:
        if username:
            cursor = self._execute(
                "SELECT * FROM ar_content WHERE username = ? ORDER BY created_at DESC",
                (username,),
            )
        else:
            cursor = self._execute("SELECT * FROM ar_content ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def increment_view_count(self, content_id: str) -> None:
        """Increase view count for AR content."""
        self._execute(
            "UPDATE ar_content SET view_count = view_count + 1 WHERE id = ?",
            (content_id,),
        )

    def increment_click_count(self, content_id: str) -> None:
        """Increase click count for AR content."""
        self._execute(
            "UPDATE ar_content SET click_count = click_count + 1 WHERE id = ?",
            (content_id,),
        )

    def delete_ar_content(self, content_id: str) -> bool:
        """Delete AR content from database."""
        cursor = self._execute("DELETE FROM ar_content WHERE id = ?", (content_id,))
        return cursor.rowcount > 0

    # Client methods
    def create_client(self, client_id: str, phone: str, name: str, company_id: str = "vertex-ar-default", email: Optional[str] = None) -> Dict[str, Any]:
        """Create a new client."""
        self._execute(
            "INSERT INTO clients (id, company_id, phone, name, email) VALUES (?, ?, ?, ?, ?)",
            (client_id, company_id, phone, name, email),
        )
        return self.get_client(client_id)

    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client by ID."""
        cursor = self._execute("SELECT * FROM clients WHERE id = ?", (client_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def get_client_by_phone(self, phone: str, company_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get client by phone number, optionally filtered by company."""
        if company_id:
            cursor = self._execute("SELECT * FROM clients WHERE phone = ? AND company_id = ?", (phone, company_id))
        else:
            cursor = self._execute("SELECT * FROM clients WHERE phone = ?", (phone,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def get_client_by_email(self, email: str, company_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get client by email address, optionally filtered by company."""
        if company_id:
            cursor = self._execute("SELECT * FROM clients WHERE email = ? AND company_id = ?", (email, company_id))
        else:
            cursor = self._execute("SELECT * FROM clients WHERE email = ?", (email,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def search_clients(self, query: str, limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        """Search clients by name or phone (partial match)."""
        return self.list_clients(search=query, limit=limit, offset=offset)

    def list_clients(
        self,
        search: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        company_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of clients with optional search, pagination, and company filter."""
        query = "SELECT * FROM clients WHERE 1=1"
        params: List[Any] = []

        if company_id:
            query += " AND company_id = ?"
            params.append(company_id)

        if search:
            like = f"%{search}%"
            query += " AND (phone LIKE ? OR name LIKE ? OR email LIKE ?)"
            params.extend([like, like, like])

        query += " ORDER BY created_at DESC"

        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        cursor = self._execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    def count_clients(self, search: Optional[str] = None, company_id: Optional[str] = None) -> int:
        """Count clients with optional search and company filter."""
        query = "SELECT COUNT(*) as count FROM clients WHERE 1=1"
        params: List[Any] = []

        if company_id:
            query += " AND company_id = ?"
            params.append(company_id)

        if search:
            like = f"%{search}%"
            query += " AND (phone LIKE ? OR name LIKE ? OR email LIKE ?)"
            params.extend([like, like, like])

        cursor = self._execute(query, tuple(params))
        row = cursor.fetchone()
        return row['count'] if row else 0

    def get_clients_by_ids(self, client_ids: List[str]) -> List[Dict[str, Any]]:
        """Get multiple clients by their IDs."""
        if not client_ids:
            return []
        placeholders = ",".join("?" for _ in client_ids)
        cursor = self._execute(
            f"SELECT * FROM clients WHERE id IN ({placeholders})",
            tuple(client_ids),
        )
        rows = [dict(row) for row in cursor.fetchall()]
        by_id = {row["id"]: row for row in rows}
        return [by_id[cid] for cid in client_ids if cid in by_id]

    def get_portrait_counts(self, client_ids: List[str]) -> Dict[str, int]:
        """Get number of portraits for the provided client IDs."""
        if not client_ids:
            return {}
        placeholders = ",".join("?" for _ in client_ids)
        cursor = self._execute(
            f"SELECT client_id, COUNT(*) as count FROM portraits WHERE client_id IN ({placeholders}) GROUP BY client_id",
            tuple(client_ids),
        )
        return {row["client_id"]: row["count"] for row in cursor.fetchall()}

    def delete_clients_bulk(self, client_ids: List[str]) -> int:
        """Delete multiple clients by their IDs."""
        if not client_ids:
            return 0
        placeholders = ",".join("?" for _ in client_ids)
        cursor = self._execute(
            f"DELETE FROM clients WHERE id IN ({placeholders})",
            tuple(client_ids),
        )
        return cursor.rowcount

    def update_client(self, client_id: str, phone: Optional[str] = None, name: Optional[str] = None, email: Optional[str] = None) -> bool:
        """Update client data."""
        updates = []
        params = []
        if phone is not None:
            updates.append("phone = ?")
            params.append(phone)
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if email is not None:
            updates.append("email = ?")
            params.append(email)

        if not updates:
            return False

        params.append(client_id)
        query = f"UPDATE clients SET {', '.join(updates)} WHERE id = ?"
        cursor = self._execute(query, tuple(params))
        return cursor.rowcount > 0

    def delete_client(self, client_id: str) -> bool:
        """Delete client."""
        cursor = self._execute("DELETE FROM clients WHERE id = ?", (client_id,))
        return cursor.rowcount > 0

    # Portrait methods
    def create_portrait(
        self,
        portrait_id: str,
        client_id: str,
        image_path: str,
        marker_fset: str,
        marker_fset3: str,
        marker_iset: str,
        permanent_link: str,
        qr_code: Optional[str] = None,
        image_preview_path: Optional[str] = None,
        folder_id: Optional[str] = None,
        subscription_end: Optional[str] = None,
        lifecycle_status: str = "active",
    ) -> Dict[str, Any]:
        """Create a new portrait."""
        self._execute(
            """
            INSERT INTO portraits (
                id, client_id, image_path, image_preview_path,
                marker_fset, marker_fset3, marker_iset,
                permanent_link, qr_code, folder_id, subscription_end, lifecycle_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (portrait_id, client_id, image_path, image_preview_path,
             marker_fset, marker_fset3, marker_iset, permanent_link, qr_code, folder_id, 
             subscription_end, lifecycle_status),
        )
        return self.get_portrait(portrait_id)

    def update_portrait_marker_paths(
        self,
        portrait_id: str,
        marker_fset: Optional[str] = None,
        marker_fset3: Optional[str] = None,
        marker_iset: Optional[str] = None,
    ) -> bool:
        """Update portrait marker file paths."""
        updates = []
        params: List[Any] = []
        if marker_fset is not None:
            updates.append("marker_fset = ?")
            params.append(marker_fset)
        if marker_fset3 is not None:
            updates.append("marker_fset3 = ?")
            params.append(marker_fset3)
        if marker_iset is not None:
            updates.append("marker_iset = ?")
            params.append(marker_iset)

        if not updates:
            return False

        params.append(portrait_id)
        query = f"UPDATE portraits SET {', '.join(updates)} WHERE id = ?"
        cursor = self._execute(query, tuple(params))
        return cursor.rowcount > 0

    def get_portrait(self, portrait_id: str) -> Optional[Dict[str, Any]]:
        """Get portrait by ID."""
        cursor = self._execute("SELECT * FROM portraits WHERE id = ?", (portrait_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def get_portrait_by_link(self, permanent_link: str) -> Optional[Dict[str, Any]]:
        """Get portrait by permanent link."""
        cursor = self._execute("SELECT * FROM portraits WHERE permanent_link = ?", (permanent_link,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def list_portraits(self, client_id: Optional[str] = None, folder_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of portraits with optional filters."""
        query = "SELECT * FROM portraits WHERE 1=1"
        params: List[Any] = []
        
        if client_id:
            query += " AND client_id = ?"
            params.append(client_id)
        
        if folder_id:
            query += " AND folder_id = ?"
            params.append(folder_id)
        
        query += " ORDER BY created_at DESC"
        
        cursor = self._execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    
    def list_portraits_paginated(
        self,
        page: int = 1,
        page_size: int = 50,
        client_id: Optional[str] = None,
        folder_id: Optional[str] = None,
        company_id: Optional[str] = None,
        lifecycle_status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get paginated list of portraits with optional filters.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            client_id: Filter by client ID
            folder_id: Filter by folder ID
            company_id: Filter by company ID (via client relationship)
            lifecycle_status: Filter by lifecycle status (active, expiring, archived)
        
        Returns:
            List of portrait dictionaries
        """
        # Build base query
        if company_id:
            # Join with clients to filter by company
            query = """
                SELECT p.* FROM portraits p
                JOIN clients c ON p.client_id = c.id
                WHERE c.company_id = ?
            """
            params: List[Any] = [company_id]
        else:
            query = "SELECT * FROM portraits WHERE 1=1"
            params = []
        
        # Apply filters
        if client_id:
            query += " AND client_id = ?" if not company_id else " AND p.client_id = ?"
            params.append(client_id)
        
        if folder_id:
            query += " AND folder_id = ?" if not company_id else " AND p.folder_id = ?"
            params.append(folder_id)
        
        if lifecycle_status:
            query += " AND lifecycle_status = ?" if not company_id else " AND p.lifecycle_status = ?"
            params.append(lifecycle_status)
        
        # Add ordering and pagination
        query += " ORDER BY created_at DESC" if not company_id else " ORDER BY p.created_at DESC"
        query += " LIMIT ? OFFSET ?"
        
        offset = (page - 1) * page_size
        params.extend([page_size, offset])
        
        cursor = self._execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    
    def count_portraits(
        self,
        client_id: Optional[str] = None,
        folder_id: Optional[str] = None,
        company_id: Optional[str] = None,
        lifecycle_status: Optional[str] = None,
    ) -> int:
        """
        Count portraits with optional filters.
        
        Args:
            client_id: Filter by client ID
            folder_id: Filter by folder ID
            company_id: Filter by company ID (via client relationship)
            lifecycle_status: Filter by lifecycle status
        
        Returns:
            Total count of portraits matching filters
        """
        # Build base query
        if company_id:
            # Join with clients to filter by company
            query = """
                SELECT COUNT(*) FROM portraits p
                JOIN clients c ON p.client_id = c.id
                WHERE c.company_id = ?
            """
            params: List[Any] = [company_id]
        else:
            query = "SELECT COUNT(*) FROM portraits WHERE 1=1"
            params = []
        
        # Apply filters
        if client_id:
            query += " AND client_id = ?" if not company_id else " AND p.client_id = ?"
            params.append(client_id)
        
        if folder_id:
            query += " AND folder_id = ?" if not company_id else " AND p.folder_id = ?"
            params.append(folder_id)
        
        if lifecycle_status:
            query += " AND lifecycle_status = ?" if not company_id else " AND p.lifecycle_status = ?"
            params.append(lifecycle_status)
        
        cursor = self._execute(query, tuple(params))
        result = cursor.fetchone()
        return result[0] if result else 0

    def increment_portrait_views(self, portrait_id: str) -> None:
        """Increase portrait view count."""
        self._execute(
            "UPDATE portraits SET view_count = view_count + 1 WHERE id = ?",
            (portrait_id,),
        )

    def delete_portrait(self, portrait_id: str) -> bool:
        """Delete portrait."""
        cursor = self._execute("DELETE FROM portraits WHERE id = ?", (portrait_id,))
        return cursor.rowcount > 0

    # Video methods
    def create_video(
        self,
        video_id: str,
        portrait_id: str,
        video_path: str,
        is_active: bool = False,
        video_preview_path: Optional[str] = None,
        description: Optional[str] = None,
        file_size_mb: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a new video."""
        self._execute(
            """
            INSERT INTO videos (
                id, portrait_id, video_path, video_preview_path, description, is_active, file_size_mb
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (video_id, portrait_id, video_path, video_preview_path, description, int(is_active), file_size_mb),
        )
        return self.get_video(video_id)

    def get_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get video by ID."""
        cursor = self._execute("SELECT * FROM videos WHERE id = ?", (video_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def get_active_video(self, portrait_id: str) -> Optional[Dict[str, Any]]:
        """Get active video for portrait."""
        cursor = self._execute(
            "SELECT * FROM videos WHERE portrait_id = ? AND is_active = 1 LIMIT 1",
            (portrait_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def list_videos(self, portrait_id: str) -> List[Dict[str, Any]]:
        """Get list of videos for portrait."""
        cursor = self._execute(
            "SELECT * FROM videos WHERE portrait_id = ? ORDER BY created_at DESC",
            (portrait_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def set_active_video(self, video_id: str, portrait_id: str) -> bool:
        """Set active video for portrait."""
        with self._lock:
            # Deactivate all videos for this portrait
            self._connection.execute(
                "UPDATE videos SET is_active = 0 WHERE portrait_id = ?",
                (portrait_id,),
            )
            # Activate selected video
            cursor = self._connection.execute(
                "UPDATE videos SET is_active = 1 WHERE id = ?",
                (video_id,),
            )
            self._connection.commit()
            return cursor.rowcount > 0

    def get_videos_by_portrait(self, portrait_id: str) -> List[Dict[str, Any]]:
        """Get all videos for a portrait."""
        cursor = self._execute(
            "SELECT * FROM videos WHERE portrait_id = ? ORDER BY created_at DESC",
            (portrait_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    # Video scheduling methods
    def update_video_schedule(
        self,
        video_id: str,
        start_datetime: Optional[str] = None,
        end_datetime: Optional[str] = None,
        rotation_type: Optional[str] = None,
        status: Optional[str] = None,
        changed_by: Optional[str] = None,
    ) -> bool:
        """Update video scheduling settings."""
        updates = []
        params = []
        
        if start_datetime is not None:
            updates.append("start_datetime = ?")
            params.append(start_datetime)
        if end_datetime is not None:
            updates.append("end_datetime = ?")
            params.append(end_datetime)
        if rotation_type is not None:
            updates.append("rotation_type = ?")
            params.append(rotation_type)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        
        if not updates:
            return False
        
        params.append(video_id)
        
        with self._lock:
            # Get current status for history
            cursor = self._execute("SELECT status FROM videos WHERE id = ?", (video_id,))
            current = cursor.fetchone()
            if not current:
                return False
            
            old_status = current["status"]
            
            # Update video
            query = f"UPDATE videos SET {', '.join(updates)} WHERE id = ?"
            cursor = self._execute(query, tuple(params))
            
            # Record status change in history if status changed
            if status is not None and old_status != status:
                self._execute(
                    """
                    INSERT INTO video_schedule_history (
                        id, video_id, old_status, new_status, change_reason, changed_by
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        video_id,
                        old_status,
                        status,
                        "schedule_update",
                        changed_by or "system"
                    )
                )
            
            self._connection.commit()
            return cursor.rowcount > 0

    def get_videos_due_for_activation(self) -> List[Dict[str, Any]]:
        """Get videos that should be activated based on schedule."""
        now = datetime.utcnow().isoformat()
        cursor = self._execute(
            """
            SELECT * FROM videos 
            WHERE status = 'active' 
            AND start_datetime IS NOT NULL 
            AND start_datetime <= ? 
            AND (end_datetime IS NULL OR end_datetime > ?)
            AND is_active = 0
            ORDER BY start_datetime ASC
            """,
            (now, now),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_videos_due_for_deactivation(self) -> List[Dict[str, Any]]:
        """Get videos that should be deactivated based on schedule."""
        now = datetime.utcnow().isoformat()
        cursor = self._execute(
            """
            SELECT * FROM videos 
            WHERE status = 'active' 
            AND end_datetime IS NOT NULL 
            AND end_datetime <= ? 
            AND is_active = 1
            ORDER BY end_datetime ASC
            """,
            (now,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_videos_for_rotation(self, portrait_id: str, rotation_type: str) -> List[Dict[str, Any]]:
        """Get videos for rotation based on type."""
        now = datetime.utcnow().isoformat()
        
        if rotation_type == "sequential":
            # Get videos that should be activated in sequence
            cursor = self._execute(
                """
                SELECT * FROM videos 
                WHERE portrait_id = ? 
                AND status = 'active'
                AND start_datetime IS NOT NULL 
                AND start_datetime <= ? 
                AND (end_datetime IS NULL OR end_datetime > ?)
                ORDER BY start_datetime ASC
                """,
                (portrait_id, now, now),
            )
        elif rotation_type == "cyclic":
            # Get videos for cyclic rotation
            cursor = self._execute(
                """
                SELECT * FROM videos 
                WHERE portrait_id = ? 
                AND status = 'active'
                AND start_datetime IS NOT NULL 
                AND start_datetime <= ? 
                AND (end_datetime IS NULL OR end_datetime > ?)
                ORDER BY created_at ASC
                """,
                (portrait_id, now, now),
            )
        else:
            return []
        
        return [dict(row) for row in cursor.fetchall()]

    def activate_video_with_history(self, video_id: str, reason: str = "schedule_activation", changed_by: str = "system") -> bool:
        """Activate video and record in history."""
        with self._lock:
            # Get current status
            cursor = self._execute("SELECT status, portrait_id FROM videos WHERE id = ?", (video_id,))
            current = cursor.fetchone()
            if not current:
                return False
            
            # Deactivate all videos for this portrait first
            self._connection.execute(
                "UPDATE videos SET is_active = 0 WHERE portrait_id = ?",
                (current["portrait_id"],),
            )
            
            # Activate selected video
            cursor = self._connection.execute(
                "UPDATE videos SET is_active = 1 WHERE id = ?",
                (video_id,),
            )
            
            # Record in history
            self._execute(
                """
                INSERT INTO video_schedule_history (
                    id, video_id, old_status, new_status, change_reason, changed_by
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    video_id,
                    current["status"],
                    "active",
                    reason,
                    changed_by
                )
            )
            
            self._connection.commit()
            return cursor.rowcount > 0

    def deactivate_video_with_history(self, video_id: str, reason: str = "schedule_deactivation", changed_by: str = "system") -> bool:
        """Deactivate video and record in history."""
        with self._lock:
            # Get current status
            cursor = self._execute("SELECT status FROM videos WHERE id = ?", (video_id,))
            current = cursor.fetchone()
            if not current:
                return False
            
            # Deactivate video
            cursor = self._connection.execute(
                "UPDATE videos SET is_active = 0 WHERE id = ?",
                (video_id,),
            )
            
            # Record in history
            self._execute(
                """
                INSERT INTO video_schedule_history (
                    id, video_id, old_status, new_status, change_reason, changed_by
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    video_id,
                    current["status"],
                    "inactive",
                    reason,
                    changed_by
                )
            )
            
            self._connection.commit()
            return cursor.rowcount > 0

    def archive_expired_videos(self) -> int:
        """Archive videos whose end_datetime has passed."""
        now = datetime.utcnow().isoformat()
        with self._lock:
            cursor = self._execute(
                """
                UPDATE videos 
                SET status = 'archived', is_active = 0 
                WHERE status = 'active' 
                AND end_datetime IS NOT NULL 
                AND end_datetime < ?
                """,
                (now,),
            )
            self._connection.commit()
            return cursor.rowcount

    def get_video_schedule_history(self, video_id: str) -> List[Dict[str, Any]]:
        """Get schedule change history for a video."""
        cursor = self._execute(
            """
            SELECT * FROM video_schedule_history 
            WHERE video_id = ? 
            ORDER BY changed_at DESC
            """,
            (video_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_scheduled_videos_summary(self) -> Dict[str, Any]:
        """Get summary of scheduled videos."""
        now = datetime.utcnow().isoformat()
        
        # Count by status
        cursor = self._execute("SELECT status, COUNT(*) as count FROM videos GROUP BY status")
        status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}
        
        # Count due for activation
        cursor = self._execute(
            """
            SELECT COUNT(*) as count FROM videos 
            WHERE status = 'active' 
            AND start_datetime IS NOT NULL 
            AND start_datetime > ? 
            AND is_active = 0
            """,
            (now,),
        )
        pending_activation = cursor.fetchone()["count"]
        
        # Count due for deactivation
        cursor = self._execute(
            """
            SELECT COUNT(*) as count FROM videos 
            WHERE status = 'active' 
            AND end_datetime IS NOT NULL 
            AND end_datetime > ? 
            AND is_active = 1
            """,
            (now,),
        )
        pending_deactivation = cursor.fetchone()["count"]
        
        return {
            "status_counts": status_counts,
            "pending_activation": pending_activation,
            "pending_deactivation": pending_deactivation,
        }

    def delete_video(self, video_id: str) -> bool:
        """Delete video."""
        cursor = self._execute("DELETE FROM videos WHERE id = ?", (video_id,))
        return cursor.rowcount > 0

    # Dashboard/statistics helpers
    def count_portraits(self, company_id: Optional[str] = None) -> int:
        """Count portraits with optional company filter."""
        query = "SELECT COUNT(*) as count FROM portraits"
        params: List[Any] = []
        if company_id:
            query += " WHERE client_id IN (SELECT id FROM clients WHERE company_id = ?)"
            params.append(company_id)
        cursor = self._execute(query, tuple(params))
        row = cursor.fetchone()
        return row["count"] if row else 0

    def count_videos(self, company_id: Optional[str] = None) -> int:
        """Count videos with optional company filter."""
        query = "SELECT COUNT(*) as count FROM videos"
        params: List[Any] = []
        if company_id:
            query += (
                " WHERE portrait_id IN ("
                "SELECT id FROM portraits WHERE client_id IN ("
                "SELECT id FROM clients WHERE company_id = ?"
                ")"
                ")"
            )
            params.append(company_id)
        cursor = self._execute(query, tuple(params))
        row = cursor.fetchone()
        return row["count"] if row else 0

    def list_videos_for_schedule(
        self,
        company_id: Optional[str] = None,
        status: Optional[str] = None,
        rotation_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get list of all videos with scheduling information.
        
        Args:
            company_id: Optional filter by company (via portrait -> client -> company)
            status: Optional filter by video status (active, inactive, archived)
            rotation_type: Optional filter by rotation type (none, sequential, cyclic)
            
        Returns:
            List of video records with all fields including scheduling metadata
        """
        query = """
            SELECT v.*
            FROM videos v
            JOIN portraits p ON v.portrait_id = p.id
            JOIN clients c ON p.client_id = c.id
            WHERE 1=1
        """
        params: List[Any] = []
        
        if company_id:
            query += " AND c.company_id = ?"
            params.append(company_id)
        
        if status:
            query += " AND v.status = ?"
            params.append(status)
        
        if rotation_type:
            query += " AND v.rotation_type = ?"
            params.append(rotation_type)
        
        query += " ORDER BY v.created_at DESC"
        
        cursor = self._execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    def count_active_portraits(self, company_id: Optional[str] = None) -> int:
        """Count portraits that have an active video."""
        query = (
            "SELECT COUNT(DISTINCT portraits.id) as count "
            "FROM portraits "
            "JOIN videos ON videos.portrait_id = portraits.id AND videos.is_active = 1 "
            "JOIN clients ON clients.id = portraits.client_id"
        )
        params: List[Any] = []
        if company_id:
            query += " WHERE clients.company_id = ?"
            params.append(company_id)
        cursor = self._execute(query, tuple(params))
        row = cursor.fetchone()
        return row["count"] if row else 0

    def sum_portrait_views(self, company_id: Optional[str] = None) -> int:
        """Sum view counts for portraits with optional company filter."""
        query = "SELECT COALESCE(SUM(view_count), 0) as total FROM portraits"
        params: List[Any] = []
        if company_id:
            query += " WHERE client_id IN (SELECT id FROM clients WHERE company_id = ?)"
            params.append(company_id)
        cursor = self._execute(query, tuple(params))
        row = cursor.fetchone()
        return row["total"] if row else 0
    
    def count_portraits_by_status(self, company_id: Optional[str] = None) -> Dict[str, int]:
        """Count portraits grouped by lifecycle status."""
        query = """
            SELECT 
                COALESCE(portraits.lifecycle_status, 'active') as status,
                COUNT(*) as count
            FROM portraits
            JOIN clients ON clients.id = portraits.client_id
        """
        params: List[Any] = []
        if company_id:
            query += " WHERE clients.company_id = ?"
            params.append(company_id)
        query += " GROUP BY portraits.lifecycle_status"
        cursor = self._execute(query, tuple(params))
        results = {
            'active': 0,
            'expiring': 0,
            'archived': 0
        }
        for row in cursor.fetchall():
            status = row["status"] or 'active'
            results[status] = row["count"]
        return results

    def get_admin_records(
        self,
        company_id: Optional[str] = None,
        limit: Optional[int] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return portrait records with client info and active video details."""
        base_query = [
            "SELECT",
            "    portraits.id AS portrait_id,",
            "    portraits.client_id AS client_id,",
            "    portraits.image_path AS image_path,",
            "    portraits.image_preview_path AS image_preview_path,",
            "    portraits.permanent_link AS permanent_link,",
            "    portraits.qr_code AS qr_code,",
            "    portraits.view_count AS view_count,",
            "    portraits.created_at AS created_at,",
            "    portraits.subscription_end AS subscription_end,",
            "    portraits.lifecycle_status AS lifecycle_status,",
            "    clients.name AS client_name,",
            "    clients.phone AS client_phone,",
            "    clients.company_id AS company_id,",
            "    videos.id AS video_id,",
            "    videos.video_path AS video_path,",
            "    videos.video_preview_path AS video_preview_path,",
            "    videos.description AS video_description",
            "FROM portraits",
            "JOIN clients ON clients.id = portraits.client_id",
            "LEFT JOIN videos ON videos.portrait_id = portraits.id AND videos.is_active = 1",
        ]
        params: List[Any] = []
        filters: List[str] = []
        if company_id:
            filters.append("clients.company_id = ?")
            params.append(company_id)
        if search:
            search_like = f"%{search.lower()}%"
            filters.append(
                "(LOWER(clients.name) LIKE ? OR clients.phone LIKE ? OR LOWER(portraits.permanent_link) LIKE ? OR LOWER(portraits.id) LIKE ?)"
            )
            params.extend([search_like, f"%{search}%", search_like, search_like])
        if status:
            filters.append("portraits.lifecycle_status = ?")
            params.append(status)
        query = " ".join(base_query)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY portraits.created_at DESC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        cursor = self._execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    # Company methods
    def create_company(
        self, 
        company_id: str, 
        name: str, 
        storage_type: str = "local", 
        storage_connection_id: Optional[str] = None,
        yandex_disk_folder_id: Optional[str] = None,
        content_types: Optional[str] = None,
        storage_folder_path: Optional[str] = None
    ) -> None:
        """Create a new company."""
        try:
            self._execute(
                "INSERT INTO companies (id, name, storage_type, storage_connection_id, yandex_disk_folder_id, content_types, storage_folder_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (company_id, name, storage_type, storage_connection_id, yandex_disk_folder_id, content_types, storage_folder_path),
            )
            logger.info(f"Created company: {name} with storage: {storage_type}")
        except sqlite3.IntegrityError as exc:
            logger.error(f"Failed to create company: {exc}")
            raise ValueError("company_already_exists") from exc

    def get_company(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Get company by ID."""
        cursor = self._execute("SELECT * FROM companies WHERE id = ?", (company_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def get_company_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get company by name."""
        cursor = self._execute("SELECT * FROM companies WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def list_companies(self) -> List[Dict[str, Any]]:
        """Get all companies."""
        cursor = self._execute("SELECT * FROM companies ORDER BY name ASC")
        return [dict(row) for row in cursor.fetchall()]

    def update_company(
        self, 
        company_id: str, 
        name: Optional[str] = None,
        storage_type: Optional[str] = None,
        storage_connection_id: Optional[str] = None,
        yandex_disk_folder_id: Optional[str] = None,
        content_types: Optional[str] = None,
        storage_folder_path: Optional[str] = None
    ) -> bool:
        """
        Update company fields.
        
        Args:
            company_id: Company ID
            name: Company name (optional)
            storage_type: Storage type (optional)
            storage_connection_id: Storage connection ID (optional)
            yandex_disk_folder_id: Yandex Disk folder ID (optional)
            content_types: Content types CSV string (optional)
            storage_folder_path: Storage folder path (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            updates = []
            params: List[Any] = []
            
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            
            if storage_type is not None:
                updates.append("storage_type = ?")
                params.append(storage_type)
            
            if storage_connection_id is not None:
                updates.append("storage_connection_id = ?")
                params.append(storage_connection_id)
            
            if yandex_disk_folder_id is not None:
                updates.append("yandex_disk_folder_id = ?")
                params.append(yandex_disk_folder_id)
            
            if content_types is not None:
                updates.append("content_types = ?")
                params.append(content_types)
            
            if storage_folder_path is not None:
                updates.append("storage_folder_path = ?")
                params.append(storage_folder_path)
            
            if not updates:
                return False
            
            params.append(company_id)
            query = f"UPDATE companies SET {', '.join(updates)} WHERE id = ?"
            
            self._execute(query, tuple(params))
            logger.info(f"Updated company {company_id}")
            return True
        except Exception as exc:
            logger.error(f"Failed to update company: {exc}")
            return False

    def delete_company(self, company_id: str) -> bool:
        """Delete company and all related data (clients, portraits, videos)."""
        try:
            # This will cascade delete clients, portraits, and videos due to ON DELETE CASCADE
            cursor = self._execute("DELETE FROM companies WHERE id = ?", (company_id,))
            if cursor.rowcount > 0:
                logger.info(f"Deleted company: {company_id}")
                return True
            return False
        except Exception as exc:
            logger.error(f"Failed to delete company: {exc}")
            return False

    def get_companies_with_client_count(self) -> List[Dict[str, Any]]:
        """Get all companies with count of clients in each."""
        cursor = self._execute("""
            SELECT c.id, c.name, c.created_at, c.storage_type, c.storage_connection_id, 
                   c.yandex_disk_folder_id, c.content_types, c.storage_folder_path, COUNT(cl.id) as client_count
            FROM companies c
            LEFT JOIN clients cl ON c.id = cl.company_id
            GROUP BY c.id
            ORDER BY c.name ASC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def update_company_storage(
        self, 
        company_id: str, 
        storage_type: str, 
        storage_connection_id: Optional[str] = None,
        yandex_disk_folder_id: Optional[str] = None,
        content_types: Optional[str] = None
    ) -> bool:
        """Update company storage configuration."""
        try:
            # Build dynamic update query
            updates = ["storage_type = ?", "storage_connection_id = ?"]
            params: List[Any] = [storage_type, storage_connection_id]
            
            if yandex_disk_folder_id is not None:
                updates.append("yandex_disk_folder_id = ?")
                params.append(yandex_disk_folder_id)
            
            if content_types is not None:
                updates.append("content_types = ?")
                params.append(content_types)
            
            params.append(company_id)
            query = f"UPDATE companies SET {', '.join(updates)} WHERE id = ?"
            
            self._execute(query, tuple(params))
            logger.info(f"Updated company {company_id} storage to {storage_type}")
            return True
        except Exception as exc:
            logger.error(f"Failed to update company storage: {exc}")
            return False
    
    def set_company_yandex_folder(self, company_id: str, folder_path: str) -> bool:
        """
        Set Yandex Disk folder path for a company.
        
        Args:
            company_id: Company ID
            folder_path: Yandex Disk folder path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._execute(
                "UPDATE companies SET yandex_disk_folder_id = ? WHERE id = ?",
                (folder_path, company_id)
            )
            logger.info(f"Set Yandex Disk folder for company {company_id}: {folder_path}")
            return True
        except Exception as exc:
            logger.error(f"Failed to set Yandex Disk folder: {exc}")
            return False
    
    def update_company_content_types(self, company_id: str, content_types: str) -> bool:
        """
        Update content types for a company.
        
        Args:
            company_id: Company ID
            content_types: Comma-separated content types string
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._execute(
                "UPDATE companies SET content_types = ? WHERE id = ?",
                (content_types, company_id)
            )
            logger.info(f"Updated content types for company {company_id}: {content_types}")
            return True
        except Exception as exc:
            logger.error(f"Failed to update content types: {exc}")
            return False
    
    @staticmethod
    def serialize_content_types(content_types: List[Dict[str, str]]) -> str:
        """
        Serialize content types list to CSV format for database storage.
        
        Args:
            content_types: List of dicts with 'slug' and 'label' keys
            
        Returns:
            CSV string in format "slug1:label1,slug2:label2"
            
        Example:
            >>> Database.serialize_content_types([{"slug": "portraits", "label": "Portraits"}])
            'portraits:Portraits'
        """
        if not content_types:
            return "portraits:Portraits"
        
        parts = []
        for ct in content_types:
            slug = ct.get('slug', '').strip()
            label = ct.get('label', '').strip()
            if slug and label:
                parts.append(f"{slug}:{label}")
        
        return ",".join(parts) if parts else "portraits:Portraits"
    
    @staticmethod
    def deserialize_content_types(content_types_str: Optional[str]) -> List[Dict[str, str]]:
        """
        Deserialize content types CSV string from database to list of dicts.
        
        Args:
            content_types_str: CSV string in format "slug1:label1,slug2:label2"
            
        Returns:
            List of dicts with 'slug' and 'label' keys
            
        Example:
            >>> Database.deserialize_content_types('portraits:Portraits,diplomas:Diplomas')
            [{'slug': 'portraits', 'label': 'Portraits'}, {'slug': 'diplomas', 'label': 'Diplomas'}]
        """
        if not content_types_str or not content_types_str.strip():
            return [{"slug": "portraits", "label": "Portraits"}]
        
        result = []
        for item in content_types_str.split(','):
            item = item.strip()
            if ':' in item:
                slug, label = item.split(':', 1)
                slug = slug.strip()
                label = label.strip()
                if slug and label:
                    result.append({"slug": slug, "label": label})
        
        return result if result else [{"slug": "portraits", "label": "Portraits"}]

    # Storage connection methods
    def create_storage_connection(self, connection_id: str, name: str, storage_type: str, config: Dict[str, Any]) -> bool:
        """Create a new storage connection."""
        try:
            import json
            config_json = json.dumps(config)
            self._execute(
                "INSERT INTO storage_connections (id, name, type, config) VALUES (?, ?, ?, ?)",
                (connection_id, name, storage_type, config_json),
            )
            logger.info(f"Created storage connection: {name} ({storage_type})")
            return True
        except sqlite3.IntegrityError as exc:
            logger.error(f"Failed to create storage connection: {exc}")
            return False
        except Exception as exc:
            logger.error(f"Failed to create storage connection: {exc}")
            return False

    def get_storage_connection(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get storage connection by ID."""
        cursor = self._execute("SELECT * FROM storage_connections WHERE id = ?", (connection_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        
        result = dict(row)
        # Parse config JSON
        import json
        try:
            result['config'] = json.loads(result['config'])
        except (json.JSONDecodeError, TypeError):
            result['config'] = {}
        
        return result

    def get_storage_connections(self, active_only: bool = True, tested_only: bool = False) -> List[Dict[str, Any]]:
        """Get all storage connections."""
        query = "SELECT * FROM storage_connections"
        conditions = []
        params = []
        
        if active_only:
            conditions.append("is_active = 1")
        if tested_only:
            conditions.append("is_tested = 1")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY name ASC"
        
        cursor = self._execute(query, tuple(params))
        rows = cursor.fetchall()
        
        # Parse config JSON for each row
        import json
        results = []
        for row in rows:
            result = dict(row)
            try:
                result['config'] = json.loads(result['config'])
            except (json.JSONDecodeError, TypeError):
                result['config'] = {}
            results.append(result)
        
        return results

    def update_storage_connection(self, connection_id: str, name: Optional[str] = None, 
                                config: Optional[Dict[str, Any]] = None, is_active: Optional[bool] = None) -> bool:
        """Update storage connection."""
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if config is not None:
            import json
            updates.append("config = ?")
            params.append(json.dumps(config))
        
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(is_active)
        
        if not updates:
            return False
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(connection_id)
        
        try:
            query = f"UPDATE storage_connections SET {', '.join(updates)} WHERE id = ?"
            self._execute(query, tuple(params))
            logger.info(f"Updated storage connection: {connection_id}")
            return True
        except Exception as exc:
            logger.error(f"Failed to update storage connection: {exc}")
            return False

    def update_storage_connection_test_result(self, connection_id: str, is_tested: bool, test_result: Optional[str] = None) -> bool:
        """Update storage connection test result."""
        try:
            self._execute(
                "UPDATE storage_connections SET is_tested = ?, test_result = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (is_tested, test_result, connection_id),
            )
            logger.info(f"Updated test result for storage connection: {connection_id}")
            return True
        except Exception as exc:
            logger.error(f"Failed to update storage connection test result: {exc}")
            return False

    def delete_storage_connection(self, connection_id: str) -> bool:
        """Delete storage connection."""
        try:
            # Check if any company is using this connection
            cursor = self._execute("SELECT COUNT(*) as count FROM companies WHERE storage_connection_id = ?", (connection_id,))
            row = cursor.fetchone()
            if row and row['count'] > 0:
                logger.warning(f"Cannot delete storage connection {connection_id}: used by companies")
                return False
            
            cursor = self._execute("DELETE FROM storage_connections WHERE id = ?", (connection_id,))
            if cursor.rowcount > 0:
                logger.info(f"Deleted storage connection: {connection_id}")
                return True
            return False
        except Exception as exc:
            logger.error(f"Failed to delete storage connection: {exc}")
            return False

    def get_available_storage_options(self) -> List[Dict[str, Any]]:
        """Get available storage options for company selection."""
        options = []
        
        # Always include local storage
        options.append({
            "id": "local",
            "name": "Локальный диск",
            "type": "local",
            "connection_id": None,
            "is_available": True
        })
        
        # Add tested remote storage connections
        connections = self.get_storage_connections(active_only=True, tested_only=True)
        for conn in connections:
            options.append({
                "id": conn['id'],
                "name": conn['name'],
                "type": conn['type'],
                "connection_id": conn['id'],
                "is_available": True
            })
        
        return options

    # Project methods
    def create_project(
        self, 
        project_id: str, 
        company_id: str, 
        name: str, 
        description: Optional[str] = None,
        status: str = "active",
        subscription_end: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new project."""
        try:
            self._execute(
                "INSERT INTO projects (id, company_id, name, description, status, subscription_end) VALUES (?, ?, ?, ?, ?, ?)",
                (project_id, company_id, name, description, status, subscription_end),
            )
            logger.info(f"Created project: {name} in company {company_id}")
            return self.get_project(project_id)
        except sqlite3.IntegrityError as exc:
            logger.error(f"Failed to create project: {exc}")
            raise ValueError("project_already_exists") from exc

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project by ID."""
        cursor = self._execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def get_project_by_name(self, company_id: str, name: str) -> Optional[Dict[str, Any]]:
        """Get project by name within a company."""
        cursor = self._execute("SELECT * FROM projects WHERE company_id = ? AND name = ?", (company_id, name))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def list_projects(self, company_id: Optional[str] = None, limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        """Get list of projects with optional company filter and pagination."""
        query = "SELECT * FROM projects WHERE 1=1"
        params: List[Any] = []

        if company_id:
            query += " AND company_id = ?"
            params.append(company_id)

        query += " ORDER BY created_at DESC"

        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        cursor = self._execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    def count_projects(self, company_id: Optional[str] = None) -> int:
        """Count projects with optional company filter."""
        query = "SELECT COUNT(*) as count FROM projects WHERE 1=1"
        params: List[Any] = []

        if company_id:
            query += " AND company_id = ?"
            params.append(company_id)

        cursor = self._execute(query, tuple(params))
        row = cursor.fetchone()
        return row['count'] if row else 0

    def update_project(
        self, 
        project_id: str, 
        name: Optional[str] = None, 
        description: Optional[str] = None,
        status: Optional[str] = None,
        subscription_end: Optional[str] = None,
        last_status_change: Optional[str] = None,
        notified_7d: Optional[str] = None,
        notified_24h: Optional[str] = None,
        notified_expired: Optional[str] = None
    ) -> bool:
        """Update project data."""
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if subscription_end is not None:
            updates.append("subscription_end = ?")
            params.append(subscription_end)
        if last_status_change is not None:
            updates.append("last_status_change = ?")
            params.append(last_status_change)
        if notified_7d is not None:
            updates.append("notified_7d = ?")
            params.append(notified_7d)
        if notified_24h is not None:
            updates.append("notified_24h = ?")
            params.append(notified_24h)
        if notified_expired is not None:
            updates.append("notified_expired = ?")
            params.append(notified_expired)

        if not updates:
            return False

        params.append(project_id)
        query = f"UPDATE projects SET {', '.join(updates)} WHERE id = ?"
        cursor = self._execute(query, tuple(params))
        return cursor.rowcount > 0

    def delete_project(self, project_id: str) -> bool:
        """Delete project and all related folders (cascade)."""
        try:
            cursor = self._execute("DELETE FROM projects WHERE id = ?", (project_id,))
            if cursor.rowcount > 0:
                logger.info(f"Deleted project: {project_id}")
                return True
            return False
        except Exception as exc:
            logger.error(f"Failed to delete project: {exc}")
            return False

    def get_project_folder_count(self, project_id: str) -> int:
        """Get count of folders in a project."""
        cursor = self._execute(
            "SELECT COUNT(*) as count FROM folders WHERE project_id = ?",
            (project_id,)
        )
        row = cursor.fetchone()
        return row['count'] if row else 0

    def get_project_portrait_count(self, project_id: str) -> int:
        """Get count of portraits in a project (across all folders)."""
        cursor = self._execute(
            """
            SELECT COUNT(*) as count FROM portraits 
            WHERE folder_id IN (SELECT id FROM folders WHERE project_id = ?)
            """,
            (project_id,)
        )
        row = cursor.fetchone()
        return row['count'] if row else 0
    
    def set_project_status(self, project_id: str, status: str) -> bool:
        """Set project status and record status change timestamp."""
        now = datetime.utcnow().isoformat()
        return self.update_project(project_id, status=status, last_status_change=now)
    
    def list_projects_for_lifecycle_check(self) -> List[Dict[str, Any]]:
        """Get all projects with subscription_end dates for lifecycle checking."""
        cursor = self._execute(
            "SELECT * FROM projects WHERE subscription_end IS NOT NULL ORDER BY subscription_end ASC"
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def count_projects_by_status(self, company_id: Optional[str] = None) -> Dict[str, int]:
        """Count projects grouped by lifecycle status."""
        query = """
            SELECT 
                COALESCE(status, 'active') as status,
                COUNT(*) as count
            FROM projects
            WHERE 1=1
        """
        params: List[Any] = []
        
        if company_id:
            query += " AND company_id = ?"
            params.append(company_id)
        
        query += " GROUP BY status"
        
        cursor = self._execute(query, tuple(params))
        results = {row["status"]: row["count"] for row in cursor.fetchall()}
        
        # Ensure all statuses are present
        for status in ["active", "expiring", "archived"]:
            if status not in results:
                results[status] = 0
        
        return results

    # Folder methods
    def create_folder(self, folder_id: str, project_id: str, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new folder."""
        try:
            self._execute(
                "INSERT INTO folders (id, project_id, name, description) VALUES (?, ?, ?, ?)",
                (folder_id, project_id, name, description),
            )
            logger.info(f"Created folder: {name} in project {project_id}")
            return self.get_folder(folder_id)
        except sqlite3.IntegrityError as exc:
            logger.error(f"Failed to create folder: {exc}")
            raise ValueError("folder_already_exists") from exc

    def get_folder(self, folder_id: str) -> Optional[Dict[str, Any]]:
        """Get folder by ID."""
        cursor = self._execute("SELECT * FROM folders WHERE id = ?", (folder_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def get_folder_by_name(self, project_id: str, name: str) -> Optional[Dict[str, Any]]:
        """Get folder by name within a project."""
        cursor = self._execute("SELECT * FROM folders WHERE project_id = ? AND name = ?", (project_id, name))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def list_folders(self, project_id: Optional[str] = None, limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        """Get list of folders with optional project filter and pagination."""
        query = "SELECT * FROM folders WHERE 1=1"
        params: List[Any] = []

        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)

        query += " ORDER BY created_at DESC"

        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        cursor = self._execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    def count_folders(self, project_id: Optional[str] = None) -> int:
        """Count folders with optional project filter."""
        query = "SELECT COUNT(*) as count FROM folders WHERE 1=1"
        params: List[Any] = []

        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)

        cursor = self._execute(query, tuple(params))
        row = cursor.fetchone()
        return row['count'] if row else 0

    def update_folder(self, folder_id: str, name: Optional[str] = None, description: Optional[str] = None) -> bool:
        """Update folder data."""
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)

        if not updates:
            return False

        params.append(folder_id)
        query = f"UPDATE folders SET {', '.join(updates)} WHERE id = ?"
        cursor = self._execute(query, tuple(params))
        return cursor.rowcount > 0

    def delete_folder(self, folder_id: str) -> bool:
        """Delete folder."""
        try:
            cursor = self._execute("DELETE FROM folders WHERE id = ?", (folder_id,))
            if cursor.rowcount > 0:
                logger.info(f"Deleted folder: {folder_id}")
                return True
            return False
        except Exception as exc:
            logger.error(f"Failed to delete folder: {exc}")
            return False

    def get_folder_portrait_count(self, folder_id: str) -> int:
        """Get count of portraits in a folder."""
        cursor = self._execute(
            "SELECT COUNT(*) as count FROM portraits WHERE folder_id = ?",
            (folder_id,)
        )
        row = cursor.fetchone()
        return row['count'] if row else 0

    # Notification settings methods
    def get_notification_settings(self) -> Optional[Dict[str, Any]]:
        """Get notification settings (returns first row, as we only have one config)."""
        cursor = self._execute("SELECT * FROM notification_settings ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def create_notification_settings(self, settings_id: str, **kwargs) -> Dict[str, Any]:
        """Create notification settings."""
        fields = [
            'smtp_host', 'smtp_port', 'smtp_username', 'smtp_password_encrypted',
            'smtp_from_email', 'smtp_use_tls', 'smtp_use_ssl',
            'telegram_bot_token_encrypted', 'telegram_chat_ids',
            'event_log_errors', 'event_db_issues', 'event_disk_space',
            'event_resource_monitoring', 'event_backup_success', 'event_info_notifications',
            'disk_threshold_percent', 'cpu_threshold_percent', 'memory_threshold_percent',
            'is_active'
        ]
        
        # Build insert statement
        columns = ['id'] + [f for f in fields if f in kwargs]
        placeholders = ['?'] * len(columns)
        values = [settings_id] + [kwargs[f] for f in columns[1:]]
        
        query = f"INSERT INTO notification_settings ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        self._execute(query, tuple(values))
        
        logger.info("Created notification settings")
        return self.get_notification_settings()

    def update_notification_settings(self, settings_id: str, **kwargs) -> bool:
        """Update notification settings."""
        valid_fields = [
            'smtp_host', 'smtp_port', 'smtp_username', 'smtp_password_encrypted',
            'smtp_from_email', 'smtp_use_tls', 'smtp_use_ssl',
            'telegram_bot_token_encrypted', 'telegram_chat_ids',
            'event_log_errors', 'event_db_issues', 'event_disk_space',
            'event_resource_monitoring', 'event_backup_success', 'event_info_notifications',
            'disk_threshold_percent', 'cpu_threshold_percent', 'memory_threshold_percent',
            'is_active'
        ]
        
        updates = []
        params = []
        for field in valid_fields:
            if field in kwargs:
                updates.append(f"{field} = ?")
                params.append(kwargs[field])
        
        if not updates:
            return False
        
        # Always update the updated_at timestamp
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(settings_id)
        
        query = f"UPDATE notification_settings SET {', '.join(updates)} WHERE id = ?"
        cursor = self._execute(query, tuple(params))
        return cursor.rowcount > 0

    def save_notification_settings(self, settings_id: str, **kwargs) -> Dict[str, Any]:
        """Save notification settings (create or update)."""
        existing = self.get_notification_settings()
        if existing:
            self.update_notification_settings(existing['id'], **kwargs)
        else:
            return self.create_notification_settings(settings_id, **kwargs)
        return self.get_notification_settings()

    # Notification history methods
    def add_notification_history(
        self,
        history_id: str,
        notification_type: str,
        recipient: str,
        message: str,
        status: str,
        subject: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a notification to history."""
        self._execute(
            """
            INSERT INTO notification_history 
            (id, notification_type, recipient, subject, message, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (history_id, notification_type, recipient, subject, message, status, error_message)
        )
        logger.info(f"Added notification history: {notification_type} to {recipient} ({status})")
        return self.get_notification_history_item(history_id)

    def get_notification_history_item(self, history_id: str) -> Optional[Dict[str, Any]]:
        """Get a single notification history item."""
        cursor = self._execute("SELECT * FROM notification_history WHERE id = ?", (history_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def list_notification_history(
        self,
        limit: int = 50,
        offset: int = 0,
        notification_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get list of notification history with optional filters."""
        query = "SELECT * FROM notification_history WHERE 1=1"
        params: List[Any] = []
        
        if notification_type:
            query += " AND notification_type = ?"
            params.append(notification_type)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY sent_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = self._execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    def count_notification_history(
        self,
        notification_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        """Count notification history with optional filters."""
        query = "SELECT COUNT(*) as count FROM notification_history WHERE 1=1"
        params: List[Any] = []
        
        if notification_type:
            query += " AND notification_type = ?"
            params.append(notification_type)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        cursor = self._execute(query, tuple(params))
        row = cursor.fetchone()
        return row['count'] if row else 0

    def cleanup_old_notification_history(self, days: int = 30) -> int:
        """Clean up notification history older than specified days."""
        cursor = self._execute(
            "DELETE FROM notification_history WHERE sent_at < datetime('now', ?)",
            (f'-{days} days',)
        )
        deleted = cursor.rowcount
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old notification history records")
        return deleted

    # Lifecycle management methods
    def get_portraits_for_lifecycle_check(self) -> List[Dict[str, Any]]:
        """Get all portraits with subscription_end set for lifecycle checking."""
        cursor = self._execute(
            """
            SELECT * FROM portraits 
            WHERE subscription_end IS NOT NULL
            ORDER BY subscription_end ASC
            """
        )
        return [dict(row) for row in cursor.fetchall()]

    def update_portrait_lifecycle_status(self, portrait_id: str, status: str) -> bool:
        """Update the lifecycle status of a portrait."""
        if status not in ('active', 'expiring', 'archived'):
            logger.error(f"Invalid lifecycle status: {status}")
            return False
        
        cursor = self._execute(
            "UPDATE portraits SET lifecycle_status = ? WHERE id = ?",
            (status, portrait_id)
        )
        return cursor.rowcount > 0

    def record_lifecycle_notification(self, portrait_id: str, notification_type: str) -> bool:
        """Record that a lifecycle notification has been sent."""
        field_map = {
            '7days': 'notification_7days_sent',
            '24hours': 'notification_24hours_sent',
            'expired': 'notification_expired_sent'
        }
        
        field = field_map.get(notification_type)
        if not field:
            logger.error(f"Invalid notification type: {notification_type}")
            return False
        
        cursor = self._execute(
            f"UPDATE portraits SET {field} = CURRENT_TIMESTAMP WHERE id = ?",
            (portrait_id,)
        )
        return cursor.rowcount > 0

    def reset_lifecycle_notifications(self, portrait_id: str) -> bool:
        """Reset all lifecycle notification timestamps for a portrait."""
        cursor = self._execute(
            """
            UPDATE portraits 
            SET notification_7days_sent = NULL,
                notification_24hours_sent = NULL,
                notification_expired_sent = NULL
            WHERE id = ?
            """,
            (portrait_id,)
        )
        return cursor.rowcount > 0

    def get_admin_settings(self) -> Optional[Dict[str, Any]]:
        """Get admin settings (Yandex Disk OAuth and SMTP)."""
        cursor = self._execute("SELECT * FROM admin_settings WHERE id = 1")
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)

    def save_yandex_oauth_settings(
        self,
        client_id: str,
        client_secret_encrypted: str,
        redirect_uri: str
    ) -> bool:
        """Save Yandex Disk OAuth settings with encrypted client secret."""
        from datetime import datetime
        
        existing = self.get_admin_settings()
        now = datetime.now()
        
        if existing:
            cursor = self._execute(
                """
                UPDATE admin_settings 
                SET yandex_client_id = ?,
                    yandex_client_secret_encrypted = ?,
                    yandex_redirect_uri = ?,
                    updated_at = ?
                WHERE id = 1
                """,
                (client_id, client_secret_encrypted, redirect_uri, now)
            )
        else:
            cursor = self._execute(
                """
                INSERT INTO admin_settings (
                    id, yandex_client_id, yandex_client_secret_encrypted, 
                    yandex_redirect_uri, created_at, updated_at
                )
                VALUES (1, ?, ?, ?, ?, ?)
                """,
                (client_id, client_secret_encrypted, redirect_uri, now, now)
            )
        
        return cursor.rowcount > 0

    def save_yandex_smtp_settings(
        self,
        smtp_email: Optional[str],
        smtp_password_encrypted: Optional[str]
    ) -> bool:
        """Save Yandex SMTP settings with encrypted password."""
        from datetime import datetime
        
        existing = self.get_admin_settings()
        now = datetime.now()
        
        if existing:
            cursor = self._execute(
                """
                UPDATE admin_settings 
                SET yandex_smtp_email = ?,
                    yandex_smtp_password_encrypted = ?,
                    updated_at = ?
                WHERE id = 1
                """,
                (smtp_email, smtp_password_encrypted, now)
            )
        else:
            cursor = self._execute(
                """
                INSERT INTO admin_settings (
                    id, yandex_smtp_email, yandex_smtp_password_encrypted,
                    created_at, updated_at
                )
                VALUES (1, ?, ?, ?, ?)
                """,
                (smtp_email, smtp_password_encrypted, now, now)
            )
        
        return cursor.rowcount > 0

    def update_yandex_connection_status(
        self,
        oauth_status: Optional[str] = None,
        smtp_status: Optional[str] = None
    ) -> bool:
        """Update Yandex connection status."""
        from datetime import datetime
        
        existing = self.get_admin_settings()
        now = datetime.now()
        
        if not existing:
            self._execute(
                "INSERT INTO admin_settings (id, created_at, updated_at) VALUES (1, ?, ?)",
                (now, now)
            )
        
        updates = []
        params = []
        
        if oauth_status:
            updates.append("yandex_connection_status = ?")
            params.append(oauth_status)
        
        if smtp_status:
            updates.append("yandex_smtp_status = ?")
            params.append(smtp_status)
        
        if updates:
            updates.append("last_tested_at = ?")
            params.append(now)
            updates.append("updated_at = ?")
            params.append(now)
            params.append(1)  # WHERE id = 1
            
            cursor = self._execute(
                f"UPDATE admin_settings SET {', '.join(updates)} WHERE id = ?",
                tuple(params)
            )
            return cursor.rowcount > 0
        
        return False

    def _seed_default_email_templates(self) -> None:
        """Seed default email templates if they don't exist."""
        try:
            cursor = self._execute("SELECT COUNT(*) FROM email_templates")
            count = cursor.fetchone()[0]
            if count > 0:
                return
            
            import uuid
            from datetime import datetime
            
            now = datetime.now()
            
            # Default template for subscription_end
            subscription_end_template = {
                'id': str(uuid.uuid4()),
                'template_type': 'subscription_end',
                'subject': 'Уведомление об окончании подписки / Subscription Expiration Notice',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
        .info-box { background: white; padding: 20px; margin: 20px 0; border-left: 4px solid #667eea; border-radius: 5px; }
        .warning { color: #ff6b6b; font-weight: bold; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
        .button { display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚠️ Уведомление об окончании подписки</h1>
            <h2>Subscription Expiration Notice</h2>
        </div>
        <div class="content">
            <p><strong>Уважаемый(ая) {{client_name}},</strong></p>
            <p><strong>Dear {{client_name}},</strong></p>
            
            <div class="info-box">
                <p class="warning">Ваша подписка на проект истекает!</p>
                <p class="warning">Your subscription is expiring!</p>
                <ul>
                    <li><strong>Проект / Project:</strong> {{project_name}}</li>
                    <li><strong>Дата окончания / End Date:</strong> {{subscription_end_date}}</li>
                    <li><strong>Осталось дней / Days Remaining:</strong> {{days_remaining}}</li>
                </ul>
            </div>
            
            <p>Пожалуйста, свяжитесь с нами для продления подписки.</p>
            <p>Please contact us to renew your subscription.</p>
            
            <p style="margin-top: 30px;">
                <strong>С уважением,<br>Best regards,<br>Команда Vertex AR</strong>
            </p>
        </div>
        <div class="footer">
            <p>© 2024 Vertex AR. Все права защищены / All rights reserved.</p>
        </div>
    </div>
</body>
</html>''',
                'variables_used': '["client_name", "project_name", "subscription_end_date", "days_remaining"]',
                'is_active': 1,
                'created_at': now,
                'updated_at': now
            }
            
            # Default template for system_error
            system_error_template = {
                'id': str(uuid.uuid4()),
                'template_type': 'system_error',
                'subject': '⚠️ Системная ошибка - {{service_name}}',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #ff6b6b; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #fff3cd; padding: 30px; border-radius: 0 0 10px 10px; }
        .error-box { background: white; padding: 20px; margin: 20px 0; border-left: 4px solid #ff6b6b; border-radius: 5px; font-family: monospace; white-space: pre-wrap; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚠️ Системная ошибка</h1>
            <h2>System Error Alert</h2>
        </div>
        <div class="content">
            <p><strong>Администратор {{admin_name}},</strong></p>
            <p>В системе произошла ошибка, требующая вашего внимания.</p>
            
            <div class="error-box">
                <p><strong>Сервис:</strong> {{service_name}}</p>
                <p><strong>Время:</strong> {{error_timestamp}}</p>
                <p><strong>Ошибка:</strong></p>
                <p>{{error_message}}</p>
            </div>
            
            <p><strong>Пожалуйста, проверьте систему как можно скорее.</strong></p>
        </div>
        <div class="footer">
            <p>Vertex AR - Автоматическое уведомление системы мониторинга</p>
        </div>
    </div>
</body>
</html>''',
                'variables_used': '["admin_name", "service_name", "error_timestamp", "error_message"]',
                'is_active': 1,
                'created_at': now,
                'updated_at': now
            }
            
            # Default template for admin_report
            admin_report_template = {
                'id': str(uuid.uuid4()),
                'template_type': 'admin_report',
                'subject': '📊 Отчет системы - {{report_period}}',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
        .report-box { background: white; padding: 20px; margin: 20px 0; border-left: 4px solid #11998e; border-radius: 5px; }
        .stat { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Системный отчет</h1>
            <h2>System Report</h2>
        </div>
        <div class="content">
            <p><strong>Администратор {{admin_name}},</strong></p>
            <p>Предоставляем отчет за период: <strong>{{report_period}}</strong></p>
            
            <div class="report-box">
                <p><strong>Дата формирования:</strong> {{report_date}}</p>
                <p>Подробный отчет прикреплен к этому письму или доступен в панели администратора.</p>
            </div>
            
            <p style="margin-top: 30px;">
                <strong>С уважением,<br>Vertex AR Monitoring System</strong>
            </p>
        </div>
        <div class="footer">
            <p>© 2024 Vertex AR. Автоматический отчет.</p>
        </div>
    </div>
</body>
</html>''',
                'variables_used': '["admin_name", "report_period", "report_date"]',
                'is_active': 1,
                'created_at': now,
                'updated_at': now
            }
            
            # Insert templates
            for template in [subscription_end_template, system_error_template, admin_report_template]:
                self._execute(
                    """
                    INSERT INTO email_templates (id, template_type, subject, html_content, variables_used, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (template['id'], template['template_type'], template['subject'], template['html_content'],
                     template['variables_used'], template['is_active'], template['created_at'], template['updated_at'])
                )
            
            logger.info("Seeded 3 default email templates")
            
        except Exception as e:
            logger.error(f"Error seeding default email templates: {e}")

    def _seed_default_monitoring_settings(self) -> None:
        """Seed default monitoring settings if they don't exist."""
        try:
            cursor = self._execute("SELECT COUNT(*) FROM monitoring_settings")
            count = cursor.fetchone()[0]
            if count > 0:
                return
            
            import uuid
            from datetime import datetime
            from app.config import settings
            
            now = datetime.now()
            
            # Create default monitoring settings based on current config
            default_settings = {
                'id': str(uuid.uuid4()),
                'cpu_threshold': getattr(settings, 'CPU_THRESHOLD', 80.0),
                'memory_threshold': getattr(settings, 'MEMORY_THRESHOLD', 85.0),
                'disk_threshold': getattr(settings, 'DISK_THRESHOLD', 90.0),
                'health_check_interval': getattr(settings, 'HEALTH_CHECK_INTERVAL', 60),
                'consecutive_failures': getattr(settings, 'MONITORING_CONSECUTIVE_FAILURES', 3),
                'dedup_window_seconds': getattr(settings, 'MONITORING_DEDUP_WINDOW', 300),
                'max_runtime_seconds': getattr(settings, 'MONITORING_MAX_RUNTIME', None),
                'health_check_cooldown_seconds': getattr(settings, 'HEALTH_CHECK_COOLDOWN', 30),
                'alert_recovery_minutes': getattr(settings, 'ALERT_RECOVERY_MINUTES', 60),
                'is_active': 1,
                'created_at': now,
                'updated_at': now
            }
            
            self._execute(
                """
                INSERT INTO monitoring_settings 
                (id, cpu_threshold, memory_threshold, disk_threshold, health_check_interval, 
                 consecutive_failures, dedup_window_seconds, max_runtime_seconds, 
                 health_check_cooldown_seconds, alert_recovery_minutes, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    default_settings['id'],
                    default_settings['cpu_threshold'],
                    default_settings['memory_threshold'],
                    default_settings['disk_threshold'],
                    default_settings['health_check_interval'],
                    default_settings['consecutive_failures'],
                    default_settings['dedup_window_seconds'],
                    default_settings['max_runtime_seconds'],
                    default_settings['health_check_cooldown_seconds'],
                    default_settings['alert_recovery_minutes'],
                    default_settings['is_active'],
                    default_settings['created_at'],
                    default_settings['updated_at']
                )
            )
            
            logger.info("Seeded default monitoring settings")
            
        except Exception as e:
            logger.error(f"Error seeding default monitoring settings: {e}")

    # ============================================================
    # Monitoring Settings Methods
    # ============================================================

    def get_monitoring_settings(self) -> Optional[Dict[str, Any]]:
        """Get active monitoring settings."""
        cursor = self._execute(
            "SELECT * FROM monitoring_settings WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)

    def update_monitoring_settings(
        self,
        cpu_threshold: Optional[float] = None,
        memory_threshold: Optional[float] = None,
        disk_threshold: Optional[float] = None,
        health_check_interval: Optional[int] = None,
        consecutive_failures: Optional[int] = None,
        dedup_window_seconds: Optional[int] = None,
        max_runtime_seconds: Optional[int] = None,
        health_check_cooldown_seconds: Optional[int] = None,
        alert_recovery_minutes: Optional[int] = None
    ) -> bool:
        """Update monitoring settings."""
        from datetime import datetime
        
        # Get the active settings row
        current = self.get_monitoring_settings()
        if not current:
            # No settings exist, create default first
            self._seed_default_monitoring_settings()
            current = self.get_monitoring_settings()
            if not current:
                return False
        
        updates = []
        params = []
        
        if cpu_threshold is not None:
            updates.append("cpu_threshold = ?")
            params.append(cpu_threshold)
        
        if memory_threshold is not None:
            updates.append("memory_threshold = ?")
            params.append(memory_threshold)
        
        if disk_threshold is not None:
            updates.append("disk_threshold = ?")
            params.append(disk_threshold)
        
        if health_check_interval is not None:
            updates.append("health_check_interval = ?")
            params.append(health_check_interval)
        
        if consecutive_failures is not None:
            updates.append("consecutive_failures = ?")
            params.append(consecutive_failures)
        
        if dedup_window_seconds is not None:
            updates.append("dedup_window_seconds = ?")
            params.append(dedup_window_seconds)
        
        if max_runtime_seconds is not None:
            updates.append("max_runtime_seconds = ?")
            params.append(max_runtime_seconds)
        
        if health_check_cooldown_seconds is not None:
            updates.append("health_check_cooldown_seconds = ?")
            params.append(health_check_cooldown_seconds)
        
        if alert_recovery_minutes is not None:
            updates.append("alert_recovery_minutes = ?")
            params.append(alert_recovery_minutes)
        
        if not updates:
            return False
        
        updates.append("updated_at = ?")
        params.append(datetime.now())
        params.append(current['id'])
        
        cursor = self._execute(
            f"UPDATE monitoring_settings SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )
        return cursor.rowcount > 0

    # ============================================================
    # Email Templates Methods
    # ============================================================

    def get_email_templates(self, template_type: Optional[str] = None, is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Get email templates, optionally filtered by type and active status."""
        query = "SELECT * FROM email_templates WHERE 1=1"
        params = []
        
        if template_type:
            query += " AND template_type = ?"
            params.append(template_type)
        
        if is_active is not None:
            query += " AND is_active = ?"
            params.append(1 if is_active else 0)
        
        query += " ORDER BY created_at DESC"
        
        cursor = self._execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    def get_email_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a single email template by ID."""
        cursor = self._execute("SELECT * FROM email_templates WHERE id = ?", (template_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)

    def get_active_template_by_type(self, template_type: str) -> Optional[Dict[str, Any]]:
        """Get active email template by type."""
        cursor = self._execute(
            "SELECT * FROM email_templates WHERE template_type = ? AND is_active = 1 ORDER BY created_at DESC LIMIT 1",
            (template_type,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)

    def create_email_template(
        self,
        template_id: str,
        template_type: str,
        subject: str,
        html_content: str,
        variables_used: Optional[str] = None,
        is_active: bool = True
    ) -> bool:
        """Create a new email template."""
        from datetime import datetime
        now = datetime.now()
        
        cursor = self._execute(
            """
            INSERT INTO email_templates (id, template_type, subject, html_content, variables_used, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (template_id, template_type, subject, html_content, variables_used, 1 if is_active else 0, now, now)
        )
        return cursor.rowcount > 0

    def update_email_template(
        self,
        template_id: str,
        subject: Optional[str] = None,
        html_content: Optional[str] = None,
        variables_used: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> bool:
        """Update an email template."""
        from datetime import datetime
        
        updates = []
        params = []
        
        if subject is not None:
            updates.append("subject = ?")
            params.append(subject)
        
        if html_content is not None:
            updates.append("html_content = ?")
            params.append(html_content)
        
        if variables_used is not None:
            updates.append("variables_used = ?")
            params.append(variables_used)
        
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if is_active else 0)
        
        if not updates:
            return False
        
        updates.append("updated_at = ?")
        params.append(datetime.now())
        params.append(template_id)
        
        cursor = self._execute(
            f"UPDATE email_templates SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )
        return cursor.rowcount > 0

    def delete_email_template(self, template_id: str) -> bool:
        """Delete an email template."""
        cursor = self._execute("DELETE FROM email_templates WHERE id = ?", (template_id,))
        return cursor.rowcount > 0

    def toggle_email_template(self, template_id: str) -> bool:
        """Toggle email template active status."""
        cursor = self._execute(
            "UPDATE email_templates SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END, updated_at = ? WHERE id = ?",
            (datetime.now(), template_id)
        )
        return cursor.rowcount > 0

    # ============================================================
    # Email Queue Methods
    # ============================================================

    def create_email_job(self, job) -> str:
        """
        Create a new email job in the queue.
        
        Args:
            job: EmailQueueJob instance
        
        Returns:
            Job ID
        """
        job_dict = job.to_dict()
        
        cursor = self._execute(
            """
            INSERT INTO email_queue (id, recipient_to, subject, body, html, template_id, variables, status, attempts, last_error, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_dict["id"],
                job_dict["to"],
                job_dict["subject"],
                job_dict["body"],
                job_dict.get("html"),
                job_dict.get("template_id"),
                job_dict.get("variables"),
                job_dict["status"],
                job_dict["attempts"],
                job_dict.get("last_error"),
                job_dict["created_at"],
                job_dict["updated_at"],
            )
        )
        
        return job_dict["id"]

    def update_email_job(self, job) -> bool:
        """
        Update an existing email job.
        
        Args:
            job: EmailQueueJob instance with updated fields
        
        Returns:
            True if updated, False otherwise
        """
        job_dict = job.to_dict()
        
        cursor = self._execute(
            """
            UPDATE email_queue
            SET status = ?, attempts = ?, last_error = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                job_dict["status"],
                job_dict["attempts"],
                job_dict.get("last_error"),
                job_dict["updated_at"],
                job_dict["id"],
            )
        )
        
        return cursor.rowcount > 0

    def get_next_pending_email_job(self) -> Optional[Dict[str, Any]]:
        """
        Get the next pending email job from the queue.
        
        Returns:
            Job dictionary or None if no pending jobs
        """
        cursor = self._execute(
            """
            SELECT * FROM email_queue
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)

    def get_all_pending_email_jobs(self) -> List[Dict[str, Any]]:
        """
        Get all pending email jobs from the queue.
        
        Returns:
            List of job dictionaries
        """
        cursor = self._execute(
            """
            SELECT * FROM email_queue
            WHERE status = 'pending'
            ORDER BY created_at ASC
            """
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_failed_email_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get failed email jobs.
        
        Args:
            limit: Maximum number of jobs to return
        
        Returns:
            List of job dictionaries
        """
        cursor = self._execute(
            """
            SELECT * FROM email_queue
            WHERE status = 'failed'
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_email_queue_stats(self) -> Dict[str, int]:
        """
        Get email queue statistics.
        
        Returns:
            Dictionary with queue statistics
        """
        cursor = self._execute(
            """
            SELECT
                status,
                COUNT(*) as count
            FROM email_queue
            GROUP BY status
            """
        )
        
        stats = {
            "pending": 0,
            "sending": 0,
            "sent": 0,
            "failed": 0,
            "total": 0,
        }
        
        for row in cursor.fetchall():
            status = row["status"]
            count = row["count"]
            stats[status] = count
            stats["total"] += count
        
        return stats

    def delete_old_email_jobs(self, days: int = 30) -> int:
        """
        Delete old sent/failed email jobs.
        
        Args:
            days: Delete jobs older than this many days
        
        Returns:
            Number of jobs deleted
        """
        cursor = self._execute(
            """
            DELETE FROM email_queue
            WHERE status IN ('sent', 'failed')
            AND datetime(updated_at) < datetime('now', '-' || ? || ' days')
            """,
            (days,)
        )
        
        return cursor.rowcount


def ensure_default_admin_user(database: "Database") -> None:
    """Ensure the default admin user exists in the provided database instance."""
    from app.config import settings
    from app.utils import hash_password

    username = getattr(settings, "DEFAULT_ADMIN_USERNAME", None)
    password = getattr(settings, "DEFAULT_ADMIN_PASSWORD", None)

    if not username or not password:
        logger.warning("Default admin credentials are not configured; skipping bootstrap")
        return

    hashed_password = hash_password(password)
    email = getattr(settings, "DEFAULT_ADMIN_EMAIL", None)
    full_name = getattr(settings, "DEFAULT_ADMIN_FULL_NAME", None)

    database.ensure_admin_user(
        username=username,
        hashed_password=hashed_password,
        email=email,
        full_name=full_name,
    )


def ensure_default_company(database: "Database") -> None:
    """Ensure the default company exists."""
    # Check if default company exists
    existing = database.get_company("vertex-ar-default")
    if not existing:
        try:
            database.create_company("vertex-ar-default", "Vertex AR")
            logger.info("Created default company: Vertex AR")
        except Exception as exc:
            logger.error(f"Failed to create default company: {exc}")
