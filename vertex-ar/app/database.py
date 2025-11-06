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
        self.path = path
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._initialise_schema()
    
    def _initialise_schema(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    hashed_password TEXT NOT NULL,
                    is_admin INTEGER NOT NULL DEFAULT 0
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
            # Create index for phone search
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_clients_phone ON clients(phone)")
            except sqlite3.OperationalError:
                pass
    
    def _execute(self, query: str, parameters: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        with self._lock:
            cursor = self._connection.execute(query, parameters)
            self._connection.commit()
            return cursor
    
    # User methods
    def create_user(self, username: str, hashed_password: str, is_admin: bool = False) -> None:
        try:
            self._execute(
                "INSERT INTO users (username, hashed_password, is_admin) VALUES (?, ?, ?)",
                (username, hashed_password, int(is_admin)),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("user_already_exists") from exc
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        cursor = self._execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    
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
    
    # Video methods
    def create_video(
        self,
        video_id: str,
        portrait_id: str,
        video_path: str,
        is_active: bool = False,
        video_preview_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new video."""
        self._execute(
            """
            INSERT INTO videos (
                id, portrait_id, video_path, video_preview_path, is_active
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (video_id, portrait_id, video_path, video_preview_path, int(is_active)),
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
    
    def delete_video(self, video_id: str) -> bool:
        """Delete video."""
        cursor = self._execute("DELETE FROM videos WHERE id = ?", (video_id,))
        return cursor.rowcount > 0