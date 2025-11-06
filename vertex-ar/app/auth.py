"""
Authentication module for Vertex AR application.
Contains authentication classes and utilities.
"""
import hashlib
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

from logging_setup import get_logger

logger = get_logger(__name__)


def _hash_password(password: str) -> str:
    """Simple password hashing (use proper hashing in production)."""
    return hashlib.sha256(password.encode()).hexdigest()


def _verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return _hash_password(password) == hashed


@dataclass
class SessionData:
    username: str
    issued_at: datetime
    last_seen: datetime


class TokenManager:
    """Manage issued access tokens with session timeouts."""

    def __init__(self, session_timeout_minutes: int = 30) -> None:
        self._tokens: Dict[str, SessionData] = {}
        self._lock = threading.Lock()
        self._session_timeout = timedelta(minutes=session_timeout_minutes)

    def issue_token(self, username: str) -> str:
        token = secrets.token_urlsafe(32)
        session = SessionData(
            username=username,
            issued_at=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )
        with self._lock:
            self._tokens[token] = session
        return token

    def verify_token(self, token: str) -> Optional[str]:
        with self._lock:
            session = self._tokens.get(token)
            if session is None:
                return None

            if self._session_timeout.total_seconds() > 0:
                now = datetime.utcnow()
                if now - session.last_seen > self._session_timeout:
                    self._tokens.pop(token, None)
                    logger.info("Session expired", username=session.username)
                    return None
                session.last_seen = now

            return session.username

    def revoke_token(self, token: str) -> None:
        with self._lock:
            self._tokens.pop(token, None)

    def revoke_user(self, username: str) -> None:
        with self._lock:
            tokens_to_remove = [token for token, session in self._tokens.items() if session.username == username]
            for token in tokens_to_remove:
                self._tokens.pop(token, None)


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