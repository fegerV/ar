"""
Authentication module for Vertex AR application.
Contains authentication classes and utilities.
"""
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

from logging_setup import get_logger

logger = get_logger(__name__)


# Import hash functions from utils to avoid circular dependencies
from app.utils import hash_password as _hash_password, verify_password as _verify_password


@dataclass
class SessionData:
    username: str
    issued_at: datetime
    last_seen: datetime


class TokenManager:
    """Manage issued access tokens with session timeouts using database storage for Uvicorn worker compatibility."""

    def __init__(self, session_timeout_minutes: int = 30) -> None:
        self._session_timeout = timedelta(minutes=session_timeout_minutes)
        self._lock = threading.Lock()

    def issue_token(self, username: str) -> str:
        """Issue a new token and store it in the database."""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + self._session_timeout

        # Get database instance
        from app.main import get_current_app
        app = get_current_app()
        database = app.state.database

        # Store session in database
        database.create_admin_session(token, username, expires_at)
        return token

    def verify_token(self, token: str) -> Optional[str]:
        """Verify a token against the database and update last seen timestamp."""
        # Get database instance
        from app.main import get_current_app
        app = get_current_app()
        database = app.state.database

        # Get session from database
        session = database.get_admin_session(token)
        if session is None:
            return None

        # Update last seen timestamp
        database.update_admin_session_last_seen(token)
        return session['username']

    def revoke_token(self, token: str) -> None:
        """Revoke a token by marking it as revoked in the database."""
        # Get database instance
        from app.main import get_current_app
        app = get_current_app()
        database = app.state.database

        # Revoke session in database
        database.revoke_admin_session(token)

    def revoke_user(self, username: str) -> None:
        """Revoke all tokens for a user by marking them as revoked in the database."""
        # Get database instance
        from app.main import get_current_app
        app = get_current_app()
        database = app.state.database

        # Revoke all sessions for user in database
        database.revoke_admin_sessions_for_user(username)

    def revoke_user_except_current(self, username: str, current_token: Optional[str] = None) -> None:
        """Revoke all tokens for a user except the current one."""
        # Get database instance
        from app.main import get_current_app
        app = get_current_app()
        database = app.state.database

        # Revoke all sessions for user except current in database
        database.revoke_admin_sessions_for_user_except_current(username, current_token)

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions from the database. Returns number of sessions removed."""
        # Get database instance
        from app.main import get_current_app
        app = get_current_app()
        database = app.state.database

        # Clean up expired sessions in database
        return database.cleanup_expired_admin_sessions()


class AuthSecurityManager:
    """Track authentication attempts and enforce temporary lockouts."""

    def __init__(self, max_attempts: int = 5, lockout_minutes: int = 15) -> None:
        self._max_attempts = max_attempts
        self._lockout_duration = timedelta(minutes=lockout_minutes)
        self._failed_attempts: Dict[str, int] = {}
        self._lockouts: Dict[str, datetime] = {}
        self._lock = threading.Lock()

    def is_locked(self, username: str) -> Optional[datetime]:
        with self._lock:
            locked_until = self._lockouts.get(username)
            if locked_until and locked_until > datetime.utcnow():
                return locked_until
            if locked_until:
                # Lock has expired, clean up state
                self._lockouts.pop(username, None)
            return None

    def register_failure(self, username: str) -> Optional[datetime]:
        with self._lock:
            now = datetime.utcnow()
            locked_until = self._lockouts.get(username)
            if locked_until and locked_until > now:
                return locked_until
            if locked_until:
                self._lockouts.pop(username, None)

            attempts = self._failed_attempts.get(username, 0) + 1
            if attempts >= self._max_attempts:
                locked_until = now + self._lockout_duration
                self._lockouts[username] = locked_until
                self._failed_attempts[username] = 0
                logger.warning(
                    "User locked due to repeated failed login attempts",
                    username=username,
                    locked_until=locked_until.isoformat(),
                )
                return locked_until

            self._failed_attempts[username] = attempts
            return None

    def reset(self, username: str) -> None:
        with self._lock:
            self._failed_attempts.pop(username, None)
            self._lockouts.pop(username, None)
