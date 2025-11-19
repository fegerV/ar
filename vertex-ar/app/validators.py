"""
Custom validators for Vertex AR application.
Provides reusable validation functions and Pydantic validators.
"""
import re
from typing import Any, Optional
from pydantic import field_validator, ValidationInfo


def validate_email(email: str) -> str:
    """Validate email format."""
    if not email:
        return email
    
    # Simple email validation pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValueError("Invalid email format")
    
    if len(email) > 255:
        raise ValueError("Email is too long (max 255 characters)")
    
    return email.lower()


def validate_phone(phone: str) -> str:
    """Validate phone number format."""
    if not phone:
        raise ValueError("Phone number cannot be empty")
    
    # Remove common formatting characters
    cleaned = re.sub(r'[\s\-\(\)\.]+', '', phone)
    
    if len(cleaned) < 7:
        raise ValueError("Phone number is too short (minimum 7 digits)")
    
    if len(cleaned) > 20:
        raise ValueError("Phone number is too long (maximum 20 characters)")
    
    # Check that it contains mostly digits
    if not re.search(r'\d', cleaned):
        raise ValueError("Phone number must contain at least one digit")
    
    return phone.strip()


def validate_username(username: str) -> str:
    """Validate username format."""
    if not username:
        raise ValueError("Username cannot be empty")
    
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters long")
    
    if len(username) > 150:
        raise ValueError("Username must not exceed 150 characters")
    
    # Username should contain only alphanumeric characters, underscores, and hyphens
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
    
    return username.lower()


def validate_password_strength(password: str) -> str:
    """Validate password meets minimum security requirements."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    if len(password) > 256:
        raise ValueError("Password is too long (max 256 characters)")
    
    # Password should contain at least one letter and one number
    has_letter = re.search(r'[a-zA-Z]', password)
    has_number = re.search(r'\d', password)
    
    if not has_letter:
        raise ValueError("Password must contain at least one letter")
    
    if not has_number:
        raise ValueError("Password must contain at least one number")
    
    return password


def validate_url(url: str) -> str:
    """Validate URL format."""
    if not url:
        raise ValueError("URL cannot be empty")
    
    # Simple URL validation pattern
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    if not re.match(pattern, url, re.IGNORECASE):
        raise ValueError("Invalid URL format")
    
    if len(url) > 2048:
        raise ValueError("URL is too long (max 2048 characters)")
    
    return url


def validate_name(name: str, min_length: int = 1, max_length: int = 150) -> str:
    """Validate name field."""
    if not name:
        raise ValueError("Name cannot be empty")
    
    name = name.strip()
    
    if len(name) < min_length:
        raise ValueError(f"Name must be at least {min_length} character(s) long")
    
    if len(name) > max_length:
        raise ValueError(f"Name must not exceed {max_length} characters")
    
    # Name should not contain only special characters
    # Check for any Unicode letter or number using \w with Unicode flag
    if not re.search(r'\w', name, re.UNICODE):
        raise ValueError("Name must contain at least one alphanumeric character")
    
    return name


def validate_id(id_value: str) -> str:
    """Validate ID format (UUID or numeric)."""
    if not id_value:
        raise ValueError("ID cannot be empty")
    
    id_value = id_value.strip()
    
    # Check for UUID format or numeric format
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    numeric_pattern = r'^\d+$'
    
    if not (re.match(uuid_pattern, id_value, re.IGNORECASE) or re.match(numeric_pattern, id_value)):
        raise ValueError("ID must be a valid UUID or numeric identifier")
    
    return id_value


def validate_file_size(size_bytes: int, max_size_bytes: int) -> None:
    """Validate file size."""
    if size_bytes <= 0:
        raise ValueError("File size must be greater than 0 bytes")
    
    if size_bytes > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        raise ValueError(f"File size exceeds maximum allowed size of {max_mb:.1f}MB")


def validate_mime_type(mime_type: str, allowed_types: list[str]) -> str:
    """Validate MIME type is in allowed list."""
    if not mime_type:
        raise ValueError("MIME type cannot be empty")
    
    if mime_type not in allowed_types:
        raise ValueError(f"File type {mime_type} is not allowed. Allowed types: {', '.join(allowed_types)}")
    
    return mime_type


def validate_query_param(value: Any, param_name: str, min_val: int = None, max_val: int = None) -> Any:
    """Validate query parameter value."""
    if value is not None:
        if min_val is not None and value < min_val:
            raise ValueError(f"{param_name} must be at least {min_val}")
        if max_val is not None and value > max_val:
            raise ValueError(f"{param_name} must not exceed {max_val}")
    
    return value
