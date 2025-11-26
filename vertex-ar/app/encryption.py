"""
Encryption utilities for Vertex AR application.
Handles encryption/decryption of sensitive data like passwords and tokens.
"""
import os
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
from logging_setup import get_logger

logger = get_logger(__name__)


class EncryptionManager:
    """Manages encryption and decryption of sensitive data."""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption manager with a key.
        If no key is provided, generates one based on system secret.
        """
        if encryption_key:
            self._key = encryption_key.encode()
        else:
            # Generate a key based on a secret (in production, use a proper secret management)
            # For now, we'll use an environment variable or generate a stable key
            secret = os.getenv("ENCRYPTION_SECRET", "vertex-ar-default-secret-change-in-production")
            self._key = self._derive_key(secret.encode())
        
        self._fernet = Fernet(self._key)
    
    def _derive_key(self, password: bytes) -> bytes:
        """Derive an encryption key from a password using PBKDF2."""
        # Use a static salt for consistency (in production, store this securely)
        salt = b"vertex-ar-encryption-salt-v1"
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def encrypt(self, data: str) -> str:
        """Encrypt a string and return base64-encoded encrypted data."""
        if not data:
            return ""
        try:
            encrypted = self._fernet.encrypt(data.encode())
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise ValueError("Failed to encrypt data")
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt base64-encoded encrypted data and return the original string."""
        if not encrypted_data:
            return ""
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted = self._fernet.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise ValueError("Failed to decrypt data")
    
    def is_encrypted(self, data: str) -> bool:
        """Check if data appears to be encrypted (base64 encoded)."""
        if not data:
            return False
        try:
            base64.b64decode(data.encode('utf-8'))
            # Additional check: encrypted data should be fairly long
            return len(data) > 20
        except Exception:
            return False


# Global encryption manager instance
encryption_manager = EncryptionManager()
