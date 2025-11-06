"""
Enhanced validation utilities for Vertex AR application.
Provides comprehensive validation for various data types and inputs.
"""
import imghdr
import re
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import magic
from logging_setup import get_logger
from PIL import Image

logger = get_logger(__name__)


class ValidationError(Exception):
    """Custom validation error with detailed context."""

    def __init__(self, message: str, field: str = None, value: Any = None, context: Dict[str, Any] = None):
        self.message = message
        self.field = field
        self.value = value
        self.context = context or {}
        super().__init__(self.message)


class ValidationLogger:
    """Utility class for logging validation events."""

    @staticmethod
    def log_validation_success(field: str, value: Any, context: Dict[str, Any] = None) -> None:
        """Log successful validation."""
        logger.info("Validation successful", field=field, value_type=type(value).__name__, context=context or {})

    @staticmethod
    def log_validation_error(field: str, value: Any, error: str, context: Dict[str, Any] = None) -> None:
        """Log validation failure."""
        logger.warning(
            "Validation failed",
            field=field,
            value=str(value)[:100],  # Limit value length in logs
            error=error,
            context=context or {},
        )


class EnhancedValidator:
    """Enhanced validation utilities with comprehensive checks."""

    # Phone number patterns for different regions
    PHONE_PATTERNS = {
        "international": r"^\+?[1-9]\d{1,14}$",
        "us": r"^\+1\d{10}$",
        "eu": r"^\+[3-9]\d{10,14}$",
        "ru": r"^\+7\d{10}$|^8\d{10}$",
    }

    # Email validation regex
    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    # Username validation regex
    USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,50}$")

    # File size limits (in bytes)
    MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB
    MIN_IMAGE_DIMENSION = 512
    MAX_IMAGE_DIMENSION = 8192

    @classmethod
    def validate_phone_number(cls, phone: str, region: str = "international") -> str:
        """
        Validate phone number format for specified region.

        Args:
            phone: Phone number string
            region: Region pattern to use ('international', 'us', 'eu', 'ru')

        Returns:
            Normalized phone number

        Raises:
            ValidationError: If phone number is invalid
        """
        if not phone:
            raise ValidationError("Phone number is required", field="phone", value=phone)

        # Remove spaces, dashes, parentheses
        normalized_phone = re.sub(r"[\s\-\(\)]", "", phone)

        pattern = cls.PHONE_PATTERNS.get(region, cls.PHONE_PATTERNS["international"])
        if not re.match(pattern, normalized_phone):
            ValidationLogger.log_validation_error("phone", phone, f"Invalid phone format for region: {region}")
            raise ValidationError(
                f"Invalid phone number format for region: {region}", field="phone", value=phone, context={"region": region}
            )

        ValidationLogger.log_validation_success("phone", normalized_phone)
        return normalized_phone

    @classmethod
    def validate_email(cls, email: str) -> str:
        """
        Validate email format.

        Args:
            email: Email address string

        Returns:
            Normalized email address

        Raises:
            ValidationError: If email is invalid
        """
        if not email:
            raise ValidationError("Email is required", field="email", value=email)

        email_lower = email.lower().strip()

        if not cls.EMAIL_REGEX.match(email_lower):
            ValidationLogger.log_validation_error("email", email, "Invalid email format")
            raise ValidationError("Invalid email format", field="email", value=email)

        # Additional length checks
        if len(email_lower) > 255:
            raise ValidationError("Email address too long (max 255 characters)", field="email", value=email)

        ValidationLogger.log_validation_success("email", email_lower)
        return email_lower

    @classmethod
    def validate_username(cls, username: str) -> str:
        """
        Validate username format.

        Args:
            username: Username string

        Returns:
            Normalized username

        Raises:
            ValidationError: If username is invalid
        """
        if not username:
            raise ValidationError("Username is required", field="username", value=username)

        username_trimmed = username.strip()

        if not cls.USERNAME_REGEX.match(username_trimmed):
            ValidationLogger.log_validation_error("username", username, "Invalid username format")
            raise ValidationError(
                "Username must be 3-50 characters, contain only letters, numbers, underscores, and hyphens",
                field="username",
                value=username,
            )

        ValidationLogger.log_validation_success("username", username_trimmed)
        return username_trimmed

    @classmethod
    def validate_uuid(cls, uuid_str: str, field_name: str = "uuid") -> str:
        """
        Validate UUID string format.

        Args:
            uuid_str: UUID string to validate
            field_name: Name of the field for error reporting

        Returns:
            Validated UUID string

        Raises:
            ValidationError: If UUID is invalid
        """
        if not uuid_str:
            raise ValidationError(f"{field_name} is required", field=field_name, value=uuid_str)

        try:
            uuid.UUID(uuid_str)
        except ValueError:
            ValidationLogger.log_validation_error(field_name, uuid_str, "Invalid UUID format")
            raise ValidationError(f"Invalid {field_name} format", field=field_name, value=uuid_str)

        ValidationLogger.log_validation_success(field_name, uuid_str)
        return uuid_str

    @classmethod
    def validate_file_size(cls, file_content: bytes, max_size: int, file_type: str = "file") -> None:
        """
        Validate file size.

        Args:
            file_content: File content as bytes
            max_size: Maximum allowed size in bytes
            file_type: Type of file for error messages

        Raises:
            ValidationError: If file is too large
        """
        file_size = len(file_content)

        if file_size > max_size:
            size_mb = file_size / (1024 * 1024)
            max_mb = max_size / (1024 * 1024)
            ValidationLogger.log_validation_error(
                f"{file_type}_size", file_size, f"File too large: {size_mb:.2f}MB > {max_mb:.2f}MB"
            )
            raise ValidationError(
                f"{file_type.capitalize()} file too large: {size_mb:.2f}MB. Maximum allowed: {max_mb:.2f}MB",
                field=f"{file_type}_size",
                value=file_size,
                context={"max_size": max_size},
            )

        ValidationLogger.log_validation_success(f"{file_type}_size", file_size, {"max_size": max_size})

    @classmethod
    def validate_image_content(cls, file_content: bytes, filename: str = None) -> Dict[str, Any]:
        """
        Comprehensive image content validation.

        Args:
            file_content: Image file content as bytes
            filename: Original filename (optional)

        Returns:
            Dictionary with image metadata

        Raises:
            ValidationError: If image is invalid
        """
        if not file_content:
            raise ValidationError("Image content is empty", field="image_content")

        # File size validation
        cls.validate_file_size(file_content, cls.MAX_IMAGE_SIZE, "image")

        # MIME type validation using python-magic
        try:
            mime_type = magic.from_buffer(file_content, mime=True)
            allowed_types = ["image/jpeg", "image/png", "image/webp"]

            if mime_type not in allowed_types:
                ValidationLogger.log_validation_error("image_mime", mime_type, f"Unsupported image type: {mime_type}")
                raise ValidationError(
                    f"Unsupported image type: {mime_type}. Allowed types: {', '.join(allowed_types)}",
                    field="image_type",
                    value=mime_type,
                )
        except Exception as e:
            # Fallback to imghdr if magic fails
            image_type = imghdr.what(None, file_content)
            if image_type not in ["jpeg", "png", "webp"]:
                raise ValidationError("Unable to determine image type or unsupported format")
            mime_type = f"image/{image_type}"

        # Image validation using PIL
        try:
            with Image.open(BytesIO(file_content)) as img:
                width, height = img.size

                # Dimension validation
                if width < cls.MIN_IMAGE_DIMENSION or height < cls.MIN_IMAGE_DIMENSION:
                    ValidationLogger.log_validation_error(
                        "image_dimensions",
                        f"{width}x{height}",
                        f"Image too small: {width}x{height} < {cls.MIN_IMAGE_DIMENSION}x{cls.MIN_IMAGE_DIMENSION}",
                    )
                    raise ValidationError(
                        f"Image too small. Minimum dimensions: {cls.MIN_IMAGE_DIMENSION}x{cls.MIN_IMAGE_DIMENSION}px",
                        field="image_dimensions",
                        value=f"{width}x{height}",
                        context={"min_dimension": cls.MIN_IMAGE_DIMENSION},
                    )

                if width > cls.MAX_IMAGE_DIMENSION or height > cls.MAX_IMAGE_DIMENSION:
                    ValidationLogger.log_validation_error(
                        "image_dimensions",
                        f"{width}x{height}",
                        f"Image too large: {width}x{height} > {cls.MAX_IMAGE_DIMENSION}x{cls.MAX_IMAGE_DIMENSION}",
                    )
                    raise ValidationError(
                        f"Image too large. Maximum dimensions: {cls.MAX_IMAGE_DIMENSION}x{cls.MAX_IMAGE_DIMENSION}px",
                        field="image_dimensions",
                        value=f"{width}x{height}",
                        context={"max_dimension": cls.MAX_IMAGE_DIMENSION},
                    )

                # Verify image is not corrupted
                img.verify()

                metadata = {
                    "width": width,
                    "height": height,
                    "format": img.format,
                    "mode": img.mode,
                    "mime_type": mime_type,
                    "size_bytes": len(file_content),
                }

        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            ValidationLogger.log_validation_error("image_content", str(e)[:50], "Image is corrupted or invalid")
            raise ValidationError("Image is corrupted or invalid", field="image_content", context={"error": str(e)})

        ValidationLogger.log_validation_success("image_content", metadata, {"filename": filename})
        return metadata

    @classmethod
    def validate_video_content(cls, file_content: bytes, filename: str = None) -> Dict[str, Any]:
        """
        Comprehensive video content validation.

        Args:
            file_content: Video file content as bytes
            filename: Original filename (optional)

        Returns:
            Dictionary with video metadata

        Raises:
            ValidationError: If video is invalid
        """
        if not file_content:
            raise ValidationError("Video content is empty", field="video_content")

        # File size validation
        cls.validate_file_size(file_content, cls.MAX_VIDEO_SIZE, "video")

        # Basic MP4 validation using file signature
        if len(file_content) < 12:
            raise ValidationError("Video file too small to be valid", field="video_content")

        # Check for MP4 signature
        if file_content[4:8] != b"ftyp":
            ValidationLogger.log_validation_error("video_signature", "missing_ftyp", "Invalid MP4 file signature")
            raise ValidationError(
                "Invalid video format. Expected MP4 file with ftyp header", field="video_format", value="unknown"
            )

        # Check MP4 brand
        brand = file_content[8:12]
        valid_brands = [b"mp41", b"mp42", b"isom", b"MP42", b"avc1", b"hvc1"]

        if brand not in valid_brands:
            ValidationLogger.log_validation_error(
                "video_brand", brand.decode("utf-8", errors="ignore"), f"Unsupported MP4 brand: {brand}"
            )
            raise ValidationError(
                f"Unsupported MP4 brand: {brand.decode('utf-8', errors='ignore')}",
                field="video_brand",
                value=brand.decode("utf-8", errors="ignore"),
            )

        # MIME type validation
        try:
            mime_type = magic.from_buffer(file_content, mime=True)
            if mime_type != "video/mp4":
                ValidationLogger.log_validation_error("video_mime", mime_type, f"Invalid video MIME type: {mime_type}")
                raise ValidationError(
                    f"Invalid video type: {mime_type}. Expected: video/mp4", field="video_type", value=mime_type
                )
        except Exception:
            # If magic fails, rely on signature check
            mime_type = "video/mp4"

        metadata = {"mime_type": mime_type, "brand": brand.decode("utf-8", errors="ignore"), "size_bytes": len(file_content)}

        ValidationLogger.log_validation_success("video_content", metadata, {"filename": filename})
        return metadata

    @classmethod
    def sanitize_string(cls, input_str: str, max_length: int = 1000, allow_html: bool = False) -> str:
        """
        Sanitize string input to prevent security issues.

        Args:
            input_str: Input string to sanitize
            max_length: Maximum allowed length
            allow_html: Whether to allow HTML tags

        Returns:
            Sanitized string
        """
        if not input_str:
            return ""

        # Length limit
        if len(input_str) > max_length:
            ValidationLogger.log_validation_error(
                "string_length", len(input_str), f"String too long: {len(input_str)} > {max_length}"
            )
            raise ValidationError(
                f"String too long. Maximum allowed: {max_length} characters",
                field="string_length",
                value=len(input_str),
                context={"max_length": max_length},
            )

        sanitized = input_str.strip()

        # Remove potentially dangerous characters
        dangerous_chars = ["\x00", "\r", "\n", "\t"] if not allow_html else ["\x00"]
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, "")

        # Basic XSS prevention if HTML is not allowed
        if not allow_html:
            # Remove HTML tags
            import re

            sanitized = re.sub(r"<[^>]+>", "", sanitized)
            # Remove JavaScript patterns
            sanitized = re.sub(r"javascript:", "", sanitized, flags=re.IGNORECASE)

        ValidationLogger.log_validation_success("string_sanitization", len(sanitized))
        return sanitized

    @classmethod
    def validate_pagination_params(cls, limit: int, offset: int) -> Tuple[int, int]:
        """
        Validate pagination parameters.

        Args:
            limit: Number of items per page
            offset: Number of items to skip

        Returns:
            Tuple of validated (limit, offset)
        """
        if limit < 1:
            raise ValidationError("Limit must be at least 1", field="limit", value=limit)
        if limit > 100:
            raise ValidationError("Limit cannot exceed 100", field="limit", value=limit)

        if offset < 0:
            raise ValidationError("Offset cannot be negative", field="offset", value=offset)

        ValidationLogger.log_validation_success("pagination", {"limit": limit, "offset": offset})
        return limit, offset


def validate_and_log(validator_func, field_name: str, value: Any, **kwargs):
    """
    Helper function to validate and log in one call.

    Args:
        validator_func: Validation function to call
        field_name: Name of the field being validated
        value: Value to validate
        **kwargs: Additional arguments for validator

    Returns:
        Validated value
    """
    try:
        result = validator_func(value, **kwargs)
        ValidationLogger.log_validation_success(field_name, result)
        return result
    except ValidationError as e:
        ValidationLogger.log_validation_error(field_name, value, e.message, e.context)
        raise
