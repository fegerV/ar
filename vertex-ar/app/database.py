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
    def create_client(self, client_id: str, phone: str, name: str, company_id: str = "vertex-ar-default") -> Dict[str, Any]:
        """Create a new client."""
        self._execute(
            "INSERT INTO clients (id, company_id, phone, name) VALUES (?, ?, ?, ?)",
            (client_id, company_id, phone, name),
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
            query += " AND (phone LIKE ? OR name LIKE ?)"
            params.extend([like, like])

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
            query += " AND (phone LIKE ? OR name LIKE ?)"
            params.extend([like, like])

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
    
    def get_admin_records(
        self,
        company_id: Optional[str] = None,
        limit: Optional[int] = None,
        search: Optional[str] = None,
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
    def create_company(self, company_id: str, name: str) -> None:
        """Create a new company."""
        try:
            self._execute(
                "INSERT INTO companies (id, name) VALUES (?, ?)",
                (company_id, name),
            )
            logger.info(f"Created company: {name}")
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
            SELECT c.id, c.name, c.created_at, COUNT(cl.id) as client_count
            FROM companies c
            LEFT JOIN clients cl ON c.id = cl.company_id
            GROUP BY c.id
            ORDER BY c.name ASC
        """)
        return [dict(row) for row in cursor.fetchall()]


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
