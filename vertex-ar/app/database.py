"""
Database module for Vertex AR application.
Contains all database operations and models.
"""
import sqlite3
import threading
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
            # Create new tables for clients, portraits and videos
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS clients (
                    id TEXT PRIMARY KEY,
                    phone TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
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
            # Create index for phone search
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_clients_phone ON clients(phone)")
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
    
    def _execute(self, query: str, parameters: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        with self._lock:
            cursor = self._connection.execute(query, parameters)
            self._connection.commit()
            return cursor
    
    # User methods
    def create_user(self, username: str, hashed_password: str, is_admin: bool = False, 
                    email: Optional[str] = None, full_name: Optional[str] = None) -> None:
        try:
            self._execute(
                """
                INSERT INTO users (username, hashed_password, is_admin, email, full_name) 
                VALUES (?, ?, ?, ?, ?)
                """,
                (username, hashed_password, int(is_admin), email, full_name),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("user_already_exists") from exc
    
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
    
    def delete_user(self, username: str) -> bool:
        """Delete a user (soft delete by deactivating)."""
        cursor = self._execute(
            "UPDATE users SET is_active = 0 WHERE username = ?",
            (username,)
        )
        return cursor.rowcount > 0
    
    def list_users(self, is_admin: Optional[bool] = None, is_active: Optional[bool] = None,
                   limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List users with optional filters."""
        query = "SELECT * FROM users WHERE 1=1"
        params = []
        
        if is_admin is not None:
            query += " AND is_admin = ?"
            params.append(int(is_admin))
        
        if is_active is not None:
            query += " AND is_active = ?"
            params.append(int(is_active))
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = self._execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    
    def search_users(self, query_str: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Search users by username, email, or full name."""
        cursor = self._execute(
            """
            SELECT * FROM users 
            WHERE (username LIKE ? OR email LIKE ? OR full_name LIKE ?) AND is_active = 1
            ORDER BY username ASC LIMIT ? OFFSET ?
            """,
            (f"%{query_str}%", f"%{query_str}%", f"%{query_str}%", limit, offset)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def update_last_login(self, username: str) -> None:
        """Update the last login timestamp for a user."""
        self._execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?",
            (username,)
        )
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics."""
        cursor = self._execute("SELECT COUNT(*) as total FROM users")
        total_users = cursor.fetchone()['total']
        
        cursor = self._execute("SELECT COUNT(*) as active FROM users WHERE is_active = 1")
        active_users = cursor.fetchone()['active']
        
        cursor = self._execute("SELECT COUNT(*) as admins FROM users WHERE is_admin = 1 AND is_active = 1")
        admin_users = cursor.fetchone()['admins']
        
        cursor = self._execute(
            "SELECT COUNT(*) as recent FROM users WHERE last_login >= datetime('now', '-7 days')"
        )
        recent_logins = cursor.fetchone()['recent']
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'admin_users': admin_users,
            'recent_logins': recent_logins
        }
    
    def change_password(self, username: str, new_hashed_password: str) -> bool:
        """Change user password."""
        cursor = self._execute(
            "UPDATE users SET hashed_password = ? WHERE username = ?",
            (new_hashed_password, username)
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
    def create_client(self, client_id: str, phone: str, name: str) -> Dict[str, Any]:
        """Create a new client."""
        self._execute(
            "INSERT INTO clients (id, phone, name) VALUES (?, ?, ?)",
            (client_id, phone, name),
        )
        return self.get_client(client_id)
    
    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client by ID."""
        cursor = self._execute("SELECT * FROM clients WHERE id = ?", (client_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    
    def get_client_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get client by phone number."""
        cursor = self._execute("SELECT * FROM clients WHERE phone = ?", (phone,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    
    def search_clients(self, phone: str) -> List[Dict[str, Any]]:
        """Search clients by phone (partial match)."""
        cursor = self._execute(
            "SELECT * FROM clients WHERE phone LIKE ? ORDER BY created_at DESC",
            (f"%{phone}%",),
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def list_clients(self) -> List[Dict[str, Any]]:
        """Get list of all clients."""
        cursor = self._execute("SELECT * FROM clients ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]
    
    def update_client(self, client_id: str, phone: Optional[str] = None, name: Optional[str] = None) -> bool:
        """Update client data."""
        updates = []
        params = []
        if phone is not None:
            updates.append("phone = ?")
            params.append(phone)
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
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
    ) -> Dict[str, Any]:
        """Create a new portrait."""
        self._execute(
            """
            INSERT INTO portraits (
                id, client_id, image_path, image_preview_path,
                marker_fset, marker_fset3, marker_iset,
                permanent_link, qr_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (portrait_id, client_id, image_path, image_preview_path,
             marker_fset, marker_fset3, marker_iset, permanent_link, qr_code),
        )
        return self.get_portrait(portrait_id)
    
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
    
    def list_portraits(self, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of portraits."""
        if client_id:
            cursor = self._execute(
                "SELECT * FROM portraits WHERE client_id = ? ORDER BY created_at DESC",
                (client_id,),
            )
        else:
            cursor = self._execute("SELECT * FROM portraits ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]
    
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
    
    def update_portrait_preview(self, portrait_id: str, preview_path: str) -> bool:
        """Update portrait preview path."""
        cursor = self._execute(
            "UPDATE portraits SET image_preview_path = ? WHERE id = ?",
            (preview_path, portrait_id),
        )
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
    ) -> Dict[str, Any]:
        """Create a new video."""
        self._execute(
            """
            INSERT INTO videos (
                id, portrait_id, video_path, video_preview_path, description, is_active
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (video_id, portrait_id, video_path, video_preview_path, description, int(is_active)),
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
    
    def delete_video(self, video_id: str) -> bool:
        """Delete video."""
        cursor = self._execute("DELETE FROM videos WHERE id = ?", (video_id,))
        return cursor.rowcount > 0
    
    def update_video_preview(self, video_id: str, preview_path: str) -> bool:
        """Update video preview path."""
        cursor = self._execute(
            "UPDATE videos SET video_preview_path = ? WHERE id = ?",
            (preview_path, video_id),
        )
        return cursor.rowcount > 0


def ensure_default_admin_user(database: "Database") -> None:
    """Ensure the default admin user exists in the provided database instance."""
    from app.config import settings
    from app.auth import _hash_password

    username = getattr(settings, "DEFAULT_ADMIN_USERNAME", None)
    password = getattr(settings, "DEFAULT_ADMIN_PASSWORD", None)

    if not username or not password:
        logger.warning("Default admin credentials are not configured; skipping bootstrap")
        return

    hashed_password = _hash_password(password)
    email = getattr(settings, "DEFAULT_ADMIN_EMAIL", None)
    full_name = getattr(settings, "DEFAULT_ADMIN_FULL_NAME", None)

    database.ensure_admin_user(
        username=username,
        hashed_password=hashed_password,
        email=email,
        full_name=full_name,
    )
