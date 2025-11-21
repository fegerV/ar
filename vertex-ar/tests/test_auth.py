"""
Tests for the authentication module.
"""
import pytest
import time
from datetime import datetime, timedelta
from app.utils import hash_password as _hash_password, verify_password as _verify_password
from app.auth import TokenManager, AuthSecurityManager


class TestAuthUtils:
    """Test authentication utility functions."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "test_password"
        hashed = _hash_password(password)

        assert hashed != password
        assert len(hashed) == 64  # SHA256 hex length

        # Same password should produce same hash
        hashed2 = _hash_password(password)
        assert hashed == hashed2

    def test_verify_password(self):
        """Test password verification."""
        password = "test_password"
        hashed = _hash_password(password)

        assert _verify_password(password, hashed) is True
        assert _verify_password("wrong_password", hashed) is False


class TestTokenManager:
    """Test TokenManager class."""

    @pytest.fixture
    def token_manager(self):
        """Create a TokenManager instance for testing."""
        return TokenManager(session_timeout_minutes=1)

    def test_issue_token(self, token_manager):
        """Test token issuance."""
        username = "testuser"
        token = token_manager.issue_token(username)

        assert isinstance(token, str)
        assert len(token) > 30  # URL-safe token length

        # Verify token was stored
        session = token_manager._tokens.get(token)
        assert session is not None
        assert session.username == username
        assert isinstance(session.issued_at, datetime)
        assert isinstance(session.last_seen, datetime)

    def test_verify_token_valid(self, token_manager):
        """Test token verification for valid token."""
        username = "testuser"
        token = token_manager.issue_token(username)

        verified_username = token_manager.verify_token(token)
        assert verified_username == username

    def test_verify_token_invalid(self, token_manager):
        """Test token verification for invalid token."""
        invalid_token = "invalid_token_123"

        verified_username = token_manager.verify_token(invalid_token)
        assert verified_username is None

    def test_verify_token_expired(self, token_manager):
        """Test token verification for expired token."""
        username = "testuser"
        token = token_manager.issue_token(username)

        # Manually expire the token by setting last_seen far in the past
        session = token_manager._tokens[token]
        session.last_seen = datetime.utcnow() - timedelta(minutes=2)

        verified_username = token_manager.verify_token(token)
        assert verified_username is None

        # Token should be removed from storage
        assert token not in token_manager._tokens

    def test_revoke_token(self, token_manager):
        """Test token revocation."""
        username = "testuser"
        token = token_manager.issue_token(username)

        # Verify token exists
        assert token in token_manager._tokens

        # Revoke token
        token_manager.revoke_token(token)

        # Verify token is removed
        assert token not in token_manager._tokens
        assert token_manager.verify_token(token) is None

    def test_revoke_user(self, token_manager):
        """Test revoking all tokens for a user."""
        username = "testuser"

        # Issue multiple tokens for the same user
        token1 = token_manager.issue_token(username)
        token2 = token_manager.issue_token(username)

        # Issue token for different user
        other_token = token_manager.issue_token("otheruser")

        # Verify all tokens exist
        assert token1 in token_manager._tokens
        assert token2 in token_manager._tokens
        assert other_token in token_manager._tokens

        # Revoke all tokens for testuser
        token_manager.revoke_user(username)

        # Verify user's tokens are removed but other user's token remains
        assert token1 not in token_manager._tokens
        assert token2 not in token_manager._tokens
        assert other_token in token_manager._tokens

    def test_session_timeout_disabled(self):
        """Test token manager with session timeout disabled."""
        token_manager = TokenManager(session_timeout_minutes=0)
        username = "testuser"
        token = token_manager.issue_token(username)

        # Token should verify even after long time
        assert token_manager.verify_token(token) == username

        # Should not be removed
        assert token in token_manager._tokens


class TestAuthSecurityManager:
    """Test AuthSecurityManager class."""

    @pytest.fixture
    def auth_security(self):
        """Create an AuthSecurityManager instance for testing."""
        return AuthSecurityManager(max_attempts=3, lockout_minutes=1)

    def test_initial_state(self, auth_security):
        """Test initial state of security manager."""
        assert len(auth_security._failed_attempts) == 0
        assert len(auth_security._lockouts) == 0

    def test_not_locked_initially(self, auth_security):
        """Test that user is not locked initially."""
        assert auth_security.is_locked("testuser") is None

    def test_register_failure_below_threshold(self, auth_security):
        """Test registering failures below max attempts."""
        username = "testuser"

        # Register 2 failures (below threshold of 3)
        for i in range(2):
            locked_until = auth_security.register_failure(username)
            assert locked_until is None
            assert auth_security._failed_attempts[username] == i + 1

    def test_register_failure_at_threshold(self, auth_security):
        """Test registering failures at max attempts threshold."""
        username = "testuser"

        # Register 3 failures (at threshold)
        for i in range(2):
            auth_security.register_failure(username)

        # Third failure should trigger lockout
        locked_until = auth_security.register_failure(username)
        assert locked_until is not None
        assert isinstance(locked_until, datetime)
        assert locked_until > datetime.utcnow()

        # User should now be locked
        assert auth_security.is_locked(username) is not None
        assert auth_security._failed_attempts[username] == 0  # Reset after lockout

    def test_is_locked_while_locked(self, auth_security):
        """Test checking lock status while user is locked."""
        username = "testuser"

        # Lock the user
        auth_security.register_failure(username)
        auth_security.register_failure(username)
        locked_until = auth_security.register_failure(username)

        # Should return lock end time
        assert auth_security.is_locked(username) == locked_until

    def test_is_locked_after_expiry(self, auth_security):
        """Test checking lock status after lock expires."""
        username = "testuser"

        # Lock the user
        for i in range(3):
            auth_security.register_failure(username)

        # Manually expire the lock
        auth_security._lockouts[username] = datetime.utcnow() - timedelta(minutes=1)

        # Should return None (not locked) and clean up
        assert auth_security.is_locked(username) is None
        assert username not in auth_security._lockouts

    def test_register_failure_while_locked(self, auth_security):
        """Test registering failure while user is already locked."""
        username = "testuser"

        # Lock the user
        for i in range(3):
            auth_security.register_failure(username)

        original_locked_until = auth_security.is_locked(username)

        # Try to register another failure while locked
        locked_until = auth_security.register_failure(username)

        # Should return the same lock end time
        assert locked_until == original_locked_until

    def test_reset(self, auth_security):
        """Test resetting user's security state."""
        username = "testuser"

        # Register some failures
        auth_security.register_failure(username)
        auth_security.register_failure(username)

        assert username in auth_security._failed_attempts
        assert auth_security._failed_attempts[username] == 2

        # Reset user
        auth_security.reset(username)

        # Should clean up user state
        assert username not in auth_security._failed_attempts
        assert username not in auth_security._lockouts

    def test_multiple_users(self, auth_security):
        """Test security manager with multiple users."""
        user1 = "user1"
        user2 = "user2"

        # User1 fails once
        auth_security.register_failure(user1)
        assert auth_security._failed_attempts[user1] == 1
        assert user1 not in auth_security._lockouts

        # User2 fails enough to get locked
        for i in range(3):
            auth_security.register_failure(user2)

        assert user2 in auth_security._lockouts
        assert user2 not in auth_security._failed_attempts  # Reset after lockout

        # User1 should still have 1 failure
        assert auth_security._failed_attempts[user1] == 1
        assert user1 not in auth_security._lockouts
