"""
FastAPI middleware for enhanced validation and logging.
"""
import time
import uuid
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from logging_setup import get_logger
from audit_logging import AuditLogger, SecurityLogger, PerformanceLogger
from validation_utils import EnhancedValidator, ValidationError

logger = get_logger(__name__)


class ValidationLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request validation and logging.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        audit_logger: Optional[AuditLogger] = None,
        log_requests: bool = True,
        log_responses: bool = True,
        log_headers: bool = False,
        rate_limit_sensitive: bool = True
    ):
        super().__init__(app)
        self.audit_logger = audit_logger or AuditLogger()
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_headers = log_headers
        self.rate_limit_sensitive = rate_limit_sensitive
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Extract client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # Add request ID to request state
        request.state.request_id = request_id
        request.state.client_ip = client_ip
        request.state.start_time = start_time
        
        # Log incoming request
        if self.log_requests:
            await self._log_request(request, request_id, client_ip, user_agent)
        
        # Process request
        response = None
        exception = None
        
        try:
            response = await call_next(request)
            
            # Log successful response
            if self.log_responses:
                await self._log_response(
                    request, response, request_id, client_ip, user_agent, start_time
                )
            
        except HTTPException as http_exc:
            exception = http_exc
            response = self._create_error_response(http_exc)
            
            # Log HTTP exception
            await self._log_http_exception(
                request, http_exc, request_id, client_ip, user_agent, start_time
            )
            
        except Exception as exc:
            exception = exc
            logger.error(
                "Unhandled exception",
                request_id=request_id,
                error=str(exc),
                error_type=type(exc).__name__,
                path=request.url.path,
                method=request.method,
                client_ip=client_ip
            )
            
            # Create generic error response
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"}
            )
            
            # Log server error
            await self._log_server_error(
                request, exc, request_id, client_ip, user_agent, start_time
            )
        
        # Add response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{int((time.time() - start_time) * 1000)}ms"
        
        # Log to audit trail
        await self._log_audit_trail(
            request, response, exception, request_id, client_ip, user_agent, start_time
        )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def _log_request(
        self, request: Request, request_id: str, client_ip: str, user_agent: str
    ) -> None:
        """Log incoming request details."""
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_ip": client_ip,
            "user_agent": user_agent[:200],  # Limit length
        }
        
        if self.log_headers:
            log_data["headers"] = dict(request.headers)
        
        # Add user info if available
        if hasattr(request.state, 'user'):
            log_data["user"] = request.state.user
        
        logger.info("Request received", **log_data)
    
    async def _log_response(
        self,
        request: Request,
        response: Response,
        request_id: str,
        client_ip: str,
        user_agent: str,
        start_time: float
    ) -> None:
        """Log response details."""
        duration_ms = int((time.time() - start_time) * 1000)
        
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client_ip": client_ip,
        }
        
        # Log slow responses
        if duration_ms > 5000:  # 5 seconds threshold
            PerformanceLogger.log_slow_operation(
                operation_name=f"{request.method} {request.url.path}",
                duration_ms=duration_ms,
                threshold_ms=5000,
                request_id=request_id,
                client_ip=client_ip
            )
        
        logger.info("Response sent", **log_data)
    
    async def _log_http_exception(
        self,
        request: Request,
        exception: HTTPException,
        request_id: str,
        client_ip: str,
        user_agent: str,
        start_time: float
    ) -> None:
        """Log HTTP exception."""
        duration_ms = int((time.time() - start_time) * 1000)
        
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": exception.status_code,
            "duration_ms": duration_ms,
            "client_ip": client_ip,
            "error_detail": exception.detail,
        }
        
        # Log security-related exceptions
        if exception.status_code in [401, 403]:
            user = getattr(request.state, 'user', None)
            SecurityLogger.log_permission_denied(
                user=user or "anonymous",
                resource_type="endpoint",
                action=f"{request.method} {request.url.path}",
                ip_address=client_ip
            )
        
        logger.warning("HTTP exception", **log_data)
    
    async def _log_server_error(
        self,
        request: Request,
        exception: Exception,
        request_id: str,
        client_ip: str,
        user_agent: str,
        start_time: float
    ) -> None:
        """Log server error."""
        duration_ms = int((time.time() - start_time) * 1000)
        
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": 500,
            "duration_ms": duration_ms,
            "client_ip": client_ip,
            "error": str(exception),
            "error_type": type(exception).__name__,
        }
        
        logger.error("Server error", **log_data)
    
    async def _log_audit_trail(
        self,
        request: Request,
        response: Response,
        exception: Optional[Exception],
        request_id: str,
        client_ip: str,
        user_agent: str,
        start_time: float
    ) -> None:
        """Log to audit trail."""
        duration_ms = int((time.time() - start_time) * 1000)
        user = getattr(request.state, 'user', None)
        
        # Determine success based on status code
        success = response.status_code < 400 if response else False
        
        self.audit_logger.log_api_access(
            endpoint=request.url.path,
            method=request.method,
            user=user,
            status_code=response.status_code if response else 500,
            response_time_ms=duration_ms,
            ip_address=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            success=success,
            error_message=str(exception) if exception else None
        )
    
    def _create_error_response(self, exception: HTTPException) -> JSONResponse:
        """Create error response from HTTP exception."""
        return JSONResponse(
            status_code=exception.status_code,
            content={
                "detail": exception.detail,
                "error_code": getattr(exception, 'error_code', None)
            }
        )


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for input validation and sanitization.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        validate_json: bool = True,
        sanitize_input: bool = True,
        max_request_size: int = 100 * 1024 * 1024,  # 100MB
        blocked_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.validate_json = validate_json
        self.sanitize_input = sanitize_input
        self.max_request_size = max_request_size
        self.blocked_paths = blocked_paths or []
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if path is blocked
        if any(request.url.path.startswith(path) for path in self.blocked_paths):
            logger.warning(
                "Blocked path access attempt",
                path=request.url.path,
                client_ip=self._get_client_ip(request)
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to this path is not allowed"
            )
        
        # Validate request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Request too large. Maximum size: {self.max_request_size} bytes"
            )
        
        # Validate and sanitize input
        if self.validate_json or self.sanitize_input:
            await self._validate_and_sanitize_request(request)
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    async def _validate_and_sanitize_request(self, request: Request) -> None:
        """Validate and sanitize request data."""
        # Only process POST, PUT, PATCH requests
        if request.method not in ["POST", "PUT", "PATCH"]:
            return
        
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type and self.validate_json:
            try:
                # Read and validate JSON
                body = await request.body()
                if body:
                    import json
                    data = json.loads(body.decode())
                    
                    # Validate JSON structure
                    if isinstance(data, dict):
                        await self._validate_json_data(data, request)
                    
            except json.JSONDecodeError as e:
                logger.warning(
                    "Invalid JSON in request",
                    path=request.url.path,
                    error=str(e),
                    client_ip=self._get_client_ip(request)
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON format"
                )
    
    async def _validate_json_data(self, data: Dict[str, Any], request: Request) -> None:
        """Validate JSON data for common injection patterns."""
        import re
        
        # Common injection patterns
        injection_patterns = [
            r'<script[^>]*>.*?</script>',  # XSS
            r'javascript:',  # JavaScript protocol
            r'on\w+\s*=',  # Event handlers
            r'expression\s*\(',  # CSS expression
        ]
        
        def check_value(key: str, value: Any) -> None:
            if isinstance(value, str):
                for pattern in injection_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        logger.warning(
                            "Potential injection detected",
                            path=request.url.path,
                            field=key,
                            pattern=pattern,
                            client_ip=self._get_client_ip(request)
                        )
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid content detected in field: {key}"
                        )
                
                # Sanitize if enabled
                if self.sanitize_input:
                    try:
                        sanitized = EnhancedValidator.sanitize_string(value, max_length=10000)
                        # Update the value (this won't actually modify the original request
                        # but serves as validation and logging)
                    except ValidationError as e:
                        logger.warning(
                            "Input sanitization failed",
                            path=request.url.path,
                            field=key,
                            error=e.message,
                            client_ip=self._get_client_ip(request)
                        )
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid input in field: {key}"
                        )
            
            elif isinstance(value, dict):
                for k, v in value.items():
                    check_value(f"{key}.{k}", v)
            
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    check_value(f"{key}[{i}]", item)
        
        # Check all top-level keys
        for key, value in data.items():
            check_value(key, value)


class RateLimitLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging rate limit events.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.audit_logger = AuditLogger()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Check for rate limit headers
        if "X-RateLimit-Limit" in response.headers:
            client_ip = self._get_client_ip(request)
            
            log_data = {
                "path": request.url.path,
                "method": request.method,
                "client_ip": client_ip,
                "rate_limit": response.headers.get("X-RateLimit-Limit"),
                "rate_remaining": response.headers.get("X-RateLimit-Remaining"),
                "rate_reset": response.headers.get("X-RateLimit-Reset"),
            }
            
            # Log if rate limit is being approached
            remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
            limit = int(response.headers.get("X-RateLimit-Limit", 0))
            
            if remaining < limit * 0.1:  # Less than 10% remaining
                logger.warning(
                    "Rate limit nearly exceeded",
                    **log_data
                )
            
            # Log rate limit exceeded
            if response.status_code == 429:
                self.audit_logger.log_security_event(
                    event_type="rate_limit_exceeded",
                    user=getattr(request.state, 'user', None),
                    details=log_data,
                    ip_address=client_ip
                )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"