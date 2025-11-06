"""
Middleware for Vertex AR application.
Provides request/response logging and validation.
"""
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

from logging_setup import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all incoming requests and outgoing responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and response with logging."""
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Log request details
        start_time = time.time()
        
        logger.info(
            "request_started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            client_host=request.client.host if request.client else None,
        )
        
        try:
            # Call next middleware/endpoint
            response = await call_next(request)
            
            # Calculate request duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log response details
            logger.info(
                "request_completed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=f"{duration_ms:.2f}",
                client_host=request.client.host if request.client else None,
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as exc:
            # Log errors
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "request_error",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration_ms=f"{duration_ms:.2f}",
                error=str(exc),
                exc_info=True,
            )
            raise


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log detailed error information."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with error logging."""
        try:
            response = await call_next(request)
            
            # Log 4xx and 5xx status codes
            if response.status_code >= 400:
                logger.warning(
                    "http_error_response",
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                )
            
            return response
            
        except Exception as exc:
            logger.error(
                "unhandled_exception",
                method=request.method,
                path=request.url.path,
                error_type=type(exc).__name__,
                error_message=str(exc),
                exc_info=True,
            )
            raise


class ValidationErrorLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log validation errors in detail."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with validation error logging."""
        try:
            response = await call_next(request)
            
            # Log 422 Unprocessable Entity (validation errors)
            if response.status_code == 422:
                logger.warning(
                    "validation_error",
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                )
            
            return response
            
        except Exception as exc:
            raise
