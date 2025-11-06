"""
Enhanced file validation and logging wrapper for Vertex AR application.
"""
import hashlib
import os
import tempfile
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union

import magic
from fastapi import HTTPException, UploadFile, status
from logging_setup import get_logger
from PIL import Image

from audit_logging import AuditLogger, OperationLogger, audit_action, log_operation
from validation_utils import EnhancedValidator, ValidationError

logger = get_logger(__name__)


class FileValidationError(ValidationError):
    """Specialized validation error for file operations."""

    pass


class FileMetadata:
    """Container for file metadata."""

    def __init__(
        self,
        filename: str,
        content_type: str,
        size_bytes: int,
        hash_md5: str,
        hash_sha256: str,
        dimensions: Optional[Tuple[int, int]] = None,
        duration_seconds: Optional[float] = None,
        **extra_metadata,
    ):
        self.filename = filename
        self.content_type = content_type
        self.size_bytes = size_bytes
        self.hash_md5 = hash_md5
        self.hash_sha256 = hash_sha256
        self.dimensions = dimensions
        self.duration_seconds = duration_seconds
        self.extra_metadata = extra_metadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "filename": self.filename,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "hash_md5": self.hash_md5,
            "hash_sha256": self.hash_sha256,
        }

        if self.dimensions:
            result["width"] = self.dimensions[0]
            result["height"] = self.dimensions[1]

        if self.duration_seconds:
            result["duration_seconds"] = self.duration_seconds

        result.update(self.extra_metadata)
        return result


class EnhancedFileValidator:
    """
    Enhanced file validator with comprehensive checks and logging.
    """

    # File type configurations
    ALLOWED_IMAGE_TYPES = {"image/jpeg": [".jpg", ".jpeg"], "image/png": [".png"], "image/webp": [".webp"]}

    ALLOWED_VIDEO_TYPES = {"video/mp4": [".mp4"], "video/webm": [".webm"]}

    ALLOWED_DOCUMENT_TYPES = {"application/pdf": [".pdf"]}

    # Size limits (in bytes)
    MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB
    MAX_DOCUMENT_SIZE = 20 * 1024 * 1024  # 20MB

    # Image dimension limits
    MIN_IMAGE_DIMENSION = 512
    MAX_IMAGE_DIMENSION = 8192

    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        self.audit_logger = audit_logger or AuditLogger()

    @log_operation("validate_upload_file")
    def validate_upload_file(
        self, file: UploadFile, file_type: str = "auto", max_size: Optional[int] = None, user: Optional[str] = None, **context
    ) -> Tuple[bytes, FileMetadata]:
        """
        Validate uploaded file with comprehensive checks.

        Args:
            file: UploadFile object
            file_type: Expected file type ('image', 'video', 'document', 'auto')
            max_size: Maximum allowed size (overrides default)
            user: User performing the upload
            **context: Additional context for logging

        Returns:
            Tuple of (file_content, file_metadata)

        Raises:
            FileValidationError: If file validation fails
        """
        # Reset file pointer
        file.file.seek(0)

        # Read file content
        try:
            file_content = file.file.read()
            if hasattr(file_content, "__await__"):
                import asyncio

                file_content = asyncio.run(file_content)
        except Exception as e:
            raise FileValidationError(
                f"Failed to read file content: {str(e)}", field="file_content", context={"filename": file.filename}
            )

        # Validate file content
        metadata = self._validate_file_content(
            file_content, file.filename or "unknown", file.content_type, file_type, max_size
        )

        # Log successful validation
        self.audit_logger.log_file_operation(
            operation="validate",
            user=user,
            file_path=file.filename or "unknown",
            file_size=metadata.size_bytes,
            file_type=metadata.content_type,
            **context,
        )

        return file_content, metadata

    def _validate_file_content(
        self, content: bytes, filename: str, declared_content_type: Optional[str], expected_type: str, max_size: Optional[int]
    ) -> FileMetadata:
        """Validate file content and extract metadata."""
        if not content:
            raise FileValidationError("File content is empty", field="file_content", context={"filename": filename})

        # Calculate file hashes
        hash_md5 = hashlib.md5(content).hexdigest()
        hash_sha256 = hashlib.sha256(content).hexdigest()

        # Detect actual MIME type
        try:
            actual_mime_type = magic.from_buffer(content, mime=True)
        except Exception as e:
            logger.warning(f"Failed to detect MIME type: {e}")
            actual_mime_type = declared_content_type or "application/octet-stream"

        # Determine file category
        file_category = self._determine_file_category(actual_mime_type, expected_type)

        # Validate based on category
        if file_category == "image":
            metadata = self._validate_image(content, filename, actual_mime_type, max_size)
        elif file_category == "video":
            metadata = self._validate_video(content, filename, actual_mime_type, max_size)
        elif file_category == "document":
            metadata = self._validate_document(content, filename, actual_mime_type, max_size)
        else:
            raise FileValidationError(
                f"Unsupported file type: {actual_mime_type}",
                field="file_type",
                context={"filename": filename, "mime_type": actual_mime_type, "declared_type": declared_content_type},
            )

        # Add hash information
        metadata.hash_md5 = hash_md5
        metadata.hash_sha256 = hash_sha256

        return metadata

    def _determine_file_category(self, mime_type: str, expected_type: str) -> str:
        """Determine file category based on MIME type and expected type."""
        if expected_type != "auto":
            # Check if expected type matches actual type
            if expected_type == "image" and mime_type in self.ALLOWED_IMAGE_TYPES:
                return "image"
            elif expected_type == "video" and mime_type in self.ALLOWED_VIDEO_TYPES:
                return "video"
            elif expected_type == "document" and mime_type in self.ALLOWED_DOCUMENT_TYPES:
                return "document"
            else:
                raise FileValidationError(
                    f"File type mismatch. Expected {expected_type}, got {mime_type}",
                    field="file_type",
                    context={"mime_type": mime_type, "expected_type": expected_type},
                )

        # Auto-detect
        if mime_type in self.ALLOWED_IMAGE_TYPES:
            return "image"
        elif mime_type in self.ALLOWED_VIDEO_TYPES:
            return "video"
        elif mime_type in self.ALLOWED_DOCUMENT_TYPES:
            return "document"
        else:
            raise FileValidationError(
                f"Unsupported file type: {mime_type}", field="file_type", context={"mime_type": mime_type}
            )

    def _validate_image(self, content: bytes, filename: str, mime_type: str, max_size: Optional[int]) -> FileMetadata:
        """Validate image file."""
        # Check MIME type
        if mime_type not in self.ALLOWED_IMAGE_TYPES:
            raise FileValidationError(
                f"Unsupported image type: {mime_type}",
                field="image_type",
                context={"allowed_types": list(self.ALLOWED_IMAGE_TYPES.keys())},
            )

        # Size validation
        size_limit = max_size or self.MAX_IMAGE_SIZE
        if len(content) > size_limit:
            raise FileValidationError(
                f"Image file too large: {len(content)} bytes > {size_limit} bytes",
                field="image_size",
                context={"actual_size": len(content), "max_size": size_limit},
            )

        # Validate image content and extract metadata
        try:
            with Image.open(BytesIO(content)) as img:
                width, height = img.size

                # Dimension validation
                if width < self.MIN_IMAGE_DIMENSION or height < self.MIN_IMAGE_DIMENSION:
                    raise FileValidationError(
                        f"Image too small: {width}x{height} < {self.MIN_IMAGE_DIMENSION}x{self.MIN_IMAGE_DIMENSION}",
                        field="image_dimensions",
                        context={"width": width, "height": height, "min_dimension": self.MIN_IMAGE_DIMENSION},
                    )

                if width > self.MAX_IMAGE_DIMENSION or height > self.MAX_IMAGE_DIMENSION:
                    raise FileValidationError(
                        f"Image too large: {width}x{height} > {self.MAX_IMAGE_DIMENSION}x{self.MAX_IMAGE_DIMENSION}",
                        field="image_dimensions",
                        context={"width": width, "height": height, "max_dimension": self.MAX_IMAGE_DIMENSION},
                    )

                # Verify image is not corrupted
                img.verify()

                # Reopen for metadata (verify() closes the file)
                with Image.open(BytesIO(content)) as img:
                    dimensions = (img.width, img.height)
                    format_name = img.format
                    mode = img.mode

                    return FileMetadata(
                        filename=filename,
                        content_type=mime_type,
                        size_bytes=len(content),
                        hash_md5="",  # Will be filled by caller
                        hash_sha256="",  # Will be filled by caller
                        dimensions=dimensions,
                        format=format_name,
                        mode=mode,
                    )

        except Exception as e:
            if isinstance(e, FileValidationError):
                raise
            raise FileValidationError(
                f"Image validation failed: {str(e)}", field="image_content", context={"filename": filename, "error": str(e)}
            )

    def _validate_video(self, content: bytes, filename: str, mime_type: str, max_size: Optional[int]) -> FileMetadata:
        """Validate video file."""
        # Check MIME type
        if mime_type not in self.ALLOWED_VIDEO_TYPES:
            raise FileValidationError(
                f"Unsupported video type: {mime_type}",
                field="video_type",
                context={"allowed_types": list(self.ALLOWED_VIDEO_TYPES.keys())},
            )

        # Size validation
        size_limit = max_size or self.MAX_VIDEO_SIZE
        if len(content) > size_limit:
            raise FileValidationError(
                f"Video file too large: {len(content)} bytes > {size_limit} bytes",
                field="video_size",
                context={"actual_size": len(content), "max_size": size_limit},
            )

        # Basic MP4 validation
        if mime_type == "video/mp4":
            if len(content) < 12:
                raise FileValidationError(
                    "Video file too small to be valid MP4", field="video_content", context={"filename": filename}
                )

            # Check for MP4 signature
            if content[4:8] != b"ftyp":
                raise FileValidationError(
                    "Invalid MP4 file signature", field="video_signature", context={"filename": filename}
                )

            # Check MP4 brand
            brand = content[8:12]
            valid_brands = [b"mp41", b"mp42", b"isom", b"MP42", b"avc1", b"hvc1"]

            if brand not in valid_brands:
                raise FileValidationError(
                    f"Unsupported MP4 brand: {brand.decode('utf-8', errors='ignore')}",
                    field="video_brand",
                    context={"filename": filename, "brand": brand.decode("utf-8", errors="ignore")},
                )

        # Try to extract duration (requires additional libraries)
        duration_seconds = None
        try:
            # This would require ffmpeg or similar library
            # For now, we'll skip duration extraction
            pass
        except Exception:
            pass

        return FileMetadata(
            filename=filename,
            content_type=mime_type,
            size_bytes=len(content),
            hash_md5="",  # Will be filled by caller
            hash_sha256="",  # Will be filled by caller
            duration_seconds=duration_seconds,
            brand=content[8:12].decode("utf-8", errors="ignore") if mime_type == "video/mp4" else None,
        )

    def _validate_document(self, content: bytes, filename: str, mime_type: str, max_size: Optional[int]) -> FileMetadata:
        """Validate document file."""
        # Check MIME type
        if mime_type not in self.ALLOWED_DOCUMENT_TYPES:
            raise FileValidationError(
                f"Unsupported document type: {mime_type}",
                field="document_type",
                context={"allowed_types": list(self.ALLOWED_DOCUMENT_TYPES.keys())},
            )

        # Size validation
        size_limit = max_size or self.MAX_DOCUMENT_SIZE
        if len(content) > size_limit:
            raise FileValidationError(
                f"Document file too large: {len(content)} bytes > {size_limit} bytes",
                field="document_size",
                context={"actual_size": len(content), "max_size": size_limit},
            )

        # Basic PDF validation
        if mime_type == "application/pdf":
            if not content.startswith(b"%PDF-"):
                raise FileValidationError("Invalid PDF file signature", field="pdf_signature", context={"filename": filename})

        return FileMetadata(
            filename=filename,
            content_type=mime_type,
            size_bytes=len(content),
            hash_md5="",  # Will be filled by caller
            hash_sha256="",  # Will be filled by caller
        )


class SecureFileStorage:
    """
    Secure file storage with validation and logging.
    """

    def __init__(
        self, base_path: Union[str, Path], validator: Optional[EnhancedFileValidator] = None, create_dirs: bool = True
    ):
        self.base_path = Path(base_path)
        self.validator = validator or EnhancedFileValidator()
        self.audit_logger = AuditLogger()

        if create_dirs:
            self.base_path.mkdir(parents=True, exist_ok=True)

    @audit_action("store_file", "file")
    async def store_file(
        self,
        file: UploadFile,
        subdirectory: str = "",
        custom_filename: Optional[str] = None,
        user: Optional[str] = None,
        **context,
    ) -> Tuple[Path, FileMetadata]:
        """
        Store file securely with validation.

        Args:
            file: UploadFile object
            subdirectory: Subdirectory within base path
            custom_filename: Custom filename (optional)
            user: User storing the file
            **context: Additional context

        Returns:
            Tuple of (file_path, metadata)
        """
        # Validate file
        file_content, metadata = self.validator.validate_upload_file(file, user=user, **context)

        # Generate secure filename
        if custom_filename:
            safe_filename = self._generate_safe_filename(custom_filename, metadata.content_type)
        else:
            safe_filename = self._generate_secure_filename(metadata.filename, metadata.content_type)

        # Create target directory
        target_dir = self.base_path
        if subdirectory:
            target_dir = target_dir / subdirectory
        target_dir.mkdir(parents=True, exist_ok=True)

        # Full file path
        file_path = target_dir / safe_filename

        # Ensure filename is unique
        file_path = self._ensure_unique_filename(file_path)

        # Write file
        try:
            with open(file_path, "wb") as f:
                f.write(file_content)
        except Exception as e:
            raise FileValidationError(f"Failed to write file: {str(e)}", field="file_write", context={"path": str(file_path)})

        # Log successful storage
        self.audit_logger.log_file_operation(
            operation="store",
            user=user,
            file_path=str(file_path),
            file_size=metadata.size_bytes,
            file_type=metadata.content_type,
            **context,
        )

        return file_path, metadata

    def _generate_safe_filename(self, filename: str, content_type: str) -> str:
        """Generate safe filename."""
        # Remove path traversal attempts
        safe_name = filename.replace("..", "").replace("/", "").replace("\\", "")

        # Get file extension
        if "." not in safe_name:
            # Add extension based on content type
            if content_type == "image/jpeg":
                safe_name += ".jpg"
            elif content_type == "image/png":
                safe_name += ".png"
            elif content_type == "image/webp":
                safe_name += ".webp"
            elif content_type == "video/mp4":
                safe_name += ".mp4"
            elif content_type == "video/webm":
                safe_name += ".webm"
            elif content_type == "application/pdf":
                safe_name += ".pdf"

        return safe_name

    def _generate_secure_filename(self, original_name: str, content_type: str) -> str:
        """Generate secure filename with UUID."""
        # Get file extension
        if "." in original_name:
            extension = original_name.rsplit(".", 1)[1].lower()
        else:
            # Add extension based on content type
            if content_type == "image/jpeg":
                extension = "jpg"
            elif content_type == "image/png":
                extension = "png"
            elif content_type == "image/webp":
                extension = "webp"
            elif content_type == "video/mp4":
                extension = "mp4"
            elif content_type == "video/webm":
                extension = "webm"
            elif content_type == "application/pdf":
                extension = "pdf"
            else:
                extension = "bin"

        # Generate UUID-based filename
        return f"{uuid.uuid4()}.{extension}"

    def _ensure_unique_filename(self, file_path: Path) -> Path:
        """Ensure filename is unique by adding counter if needed."""
        if not file_path.exists():
            return file_path

        base_name = file_path.stem
        extension = file_path.suffix
        parent_dir = file_path.parent

        counter = 1
        while True:
            new_name = f"{base_name}_{counter}{extension}"
            new_path = parent_dir / new_name
            if not new_path.exists():
                return new_path
            counter += 1

    @audit_action("delete_file", "file")
    def delete_file(self, file_path: Union[str, Path], user: Optional[str] = None, **context) -> bool:
        """Delete file securely."""
        path = Path(file_path)

        if not path.exists():
            logger.warning("Attempted to delete non-existent file", path=str(path), user=user)
            return False

        try:
            path.unlink()

            # Log deletion
            self.audit_logger.log_file_operation(operation="delete", user=user, file_path=str(path), **context)

            return True

        except Exception as e:
            logger.error("Failed to delete file", path=str(path), error=str(e), user=user)
            return False

    def get_file_info(self, file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """Get file information."""
        path = Path(file_path)

        if not path.exists():
            return None

        stat = path.stat()

        return {
            "path": str(path),
            "size_bytes": stat.st_size,
            "modified_time": stat.st_mtime,
            "is_file": path.is_file(),
            "is_directory": path.is_directory(),
            "extension": path.suffix,
        }


# Global validator instance
file_validator = EnhancedFileValidator()
