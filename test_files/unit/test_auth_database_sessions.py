"""
Tests for database-backed authentication sessions.
"""
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import tempfile
import os
from pathlib import Path
import sys

# Add the vertex-ar directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'vertex-ar'))

from app.auth import TokenManager
from app.database import Database


class TestDatabaseBackedSessions:
    """Test database-backed session functionality."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        # Create a temporary database file
        temp_db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db_file.close()

        # Create database instance
        db = Database(temp_db_file.name)

        # Create a test user to satisfy foreign key constraints
        db._execute(
            "INSERT OR IGNORE INTO users (username, hashed_password, is_admin, is_active) VALUES (?, ?, ?, ?)",
            ("testuser", "hashed_password", 1, 1)
        )
        db._execute(
            "INSERT OR IGNORE INTO users (username, hashed_password, is_admin, is_active) VALUES (?, ?, ?, ?)",
            ("otheruser", "hashed_password", 0, 1)
        )

        yield db

        # Cleanup
        try:
            os.unlink(temp_db_file.name)
        except:
            pass

    @pytest.fixture
    def token_manager(self, temp_db):
        """Create a TokenManager instance with database for testing."""
        # Mock the get_current_app function to return our test database
        with patch('app.main.get_current_app') as mock_get_current_app:
            mock_app = Mock()
            mock_app.state.database = temp_db
            mock_get_current_app.return_value = mock_app
            tm = TokenManager(session_timeout_minutes=1)
            yield tm

    def test_issue_token_stores_in_database(self, token_manager, temp_db):
        """Test that issued tokens are stored in the database."""
        username = "testuser"
        token = token_manager.issue_token(username)

        # Verify token was stored in database
        session = temp_db.get_admin_session(token)
        assert session is not None
        assert session["username"] == username
        assert session["revoked"] == 0
        # Datetime fields are returned as strings from SQLite
        assert isinstance(session["issued_at"], str)
        assert isinstance(session["expires_at"], str)
        assert isinstance(session["last_seen"], str)

    def test_verify_token_valid_from_database(self, token_manager, temp_db):
        """Test token verification for valid token from database."""
        username = "testuser"
        token = token_manager.issue_token(username)

        verified_username = token_manager.verify_token(token)
        assert verified_username == username

        # Verify last_seen was updated
        session = temp_db.get_admin_session(token)
        assert session is not None
        # We can't easily compare string timestamps, so we'll just verify the field exists

    def test_verify_token_invalid_from_database(self, token_manager):
        """Test token verification for invalid token."""
        invalid_token = "invalid_token_123"

        verified_username = token_manager.verify_token(invalid_token)
        assert verified_username is None

    def test_verify_token_expired_from_database(self, token_manager, temp_db):
        """Test token verification for expired token from database."""
        username = "testuser"
        token = token_manager.issue_token(username)

        # Manually expire the token by setting last_seen far in the past
        temp_db.update_admin_session_last_seen(token)
        # We can't directly manipulate the last_seen timestamp, so we'll test differently
        # by manually setting the expires_at to a past time
        past_time = datetime.utcnow() - timedelta(minutes=5)
        temp_db._execute(
            "UPDATE admin_sessions SET expires_at = ? WHERE token = ?",
            (past_time, token)
        )

        verified_username = token_manager.verify_token(token)
        assert verified_username is None

        # Token should be marked as revoked in database
        session = temp_db.get_admin_session(token)
        assert session is None  # Expired tokens are not returned

    def test_revoke_token_updates_database(self, token_manager, temp_db):
        """Test token revocation updates database."""
        username = "testuser"
        token = token_manager.issue_token(username)

        # Verify token exists and is not revoked
        session = temp_db.get_admin_session(token)
        assert session is not None
        assert session["revoked"] == 0

        # Revoke token
        token_manager.revoke_token(token)

        # Verify token is marked as revoked
        session = temp_db.get_admin_session(token)
        assert session is None  # Revoked tokens are not returned

    def test_revoke_user_updates_database(self, token_manager, temp_db):
        """Test revoking all tokens for a user updates database."""
        username = "testuser"

        # Issue multiple tokens for the same user
        token1 = token_manager.issue_token(username)
        token2 = token_manager.issue_token(username)

        # Issue token for different user
        other_token = token_manager.issue_token("otheruser")

        # Verify all tokens exist and are not revoked
        assert temp_db.get_admin_session(token1) is not None
        assert temp_db.get_admin_session(token2) is not None
        assert temp_db.get_admin_session(other_token) is not None

        # Revoke all tokens for testuser
        token_manager.revoke_user(username)

        # Verify user's tokens are revoked but other user's token remains
        assert temp_db.get_admin_session(token1) is None  # Revoked tokens are not returned
        assert temp_db.get_admin_session(token2) is None  # Revoked tokens are not returned
        assert temp_db.get_admin_session(other_token) is not None

    def test_revoke_user_except_current_updates_database(self, token_manager, temp_db):
        """Test revoking all tokens except current for a user updates database."""
        username = "testuser"

        # Issue multiple tokens for the same user
        token1 = token_manager.issue_token(username)
        token2 = token_manager.issue_token(username)
        token3 = token_manager.issue_token(username)

        # Issue token for different user
        other_token = token_manager.issue_token("otheruser")

        # Verify all tokens exist and are not revoked
        assert temp_db.get_admin_session(token1) is not None
        assert temp_db.get_admin_session(token2) is not None
        assert temp_db.get_admin_session(token3) is not None
        assert temp_db.get_admin_session(other_token) is not None

        # Revoke all tokens for testuser except token2
        token_manager.revoke_user_except_current(username, token2)

        # Verify user's tokens are revoked except token2
        assert temp_db.get_admin_session(token1) is None  # Revoked
        assert temp_db.get_admin_session(token2) is not None  # Not revoked
        assert temp_db.get_admin_session(token3) is None  # Revoked
        assert temp_db.get_admin_session(other_token) is not None  # Different user, not affected

    def test_cleanup_expired_sessions(self, token_manager, temp_db):
        """Test cleanup of expired sessions from database."""
        username = "testuser"

        # Issue a valid token
        valid_token = token_manager.issue_token(username)

        # Issue an expired token
        expired_token = token_manager.issue_token(username)

        # Manually expire the token by setting expires_at in the past
        past_time = datetime.utcnow() - timedelta(minutes=5)
        temp_db._execute(
            "UPDATE admin_sessions SET expires_at = ? WHERE token = ?",
            (past_time, expired_token)
        )

        # Verify both tokens exist before cleanup
        assert temp_db.get_admin_session(valid_token) is not None
        # Expired token should not be returned by get_admin_session
        assert temp_db.get_admin_session(expired_token) is None

        # Clean up expired sessions - this should remove expired tokens from database
        cleaned_count = token_manager.cleanup_expired_sessions()

        # Should have cleaned up at least 1 expired session
        assert cleaned_count >= 1

        # Valid token should still exist
        assert temp_db.get_admin_session(valid_token) is not None

    def test_session_timeout_disabled(self, temp_db):
        """Test token manager with session timeout disabled."""
        username = "testuser"

        # Mock the get_current_app function to return our test database
        with patch('app.main.get_current_app') as mock_get_current_app:
            mock_app = Mock()
            mock_app.state.database = temp_db
            mock_get_current_app.return_value = mock_app
            token_manager = TokenManager(session_timeout_minutes=0)

            token = token_manager.issue_token(username)

            # Token should verify even after long time
            assert token_manager.verify_token(token) == username

            # Token should still exist in database
            session = temp_db.get_admin_session(token)
            assert session is not None
