"""
Enhanced logging system with audit trails and structured logging for Vertex AR application.
"""
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from functools import wraps
from pathlib import Path
import threading
 
from logging_setup import get_logger
 
logger = get_logger(__name__)
 
 
class AuditLogger:
    """Comprehensive audit logging system for security and compliance."""
    
    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file
        self._lock = threading.Lock()
        self._buffer: List[Dict[str, Any]] = []
        self._buffer_size = 100
        
        # Create audit log directory if specified
        if self.log_file:
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
    
    def log_event(
        self,
        event_type: str,
        user: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an audit event with comprehensive context.
        
        Args:
            event_type: Type of event (e.g., 'user_login', 'file_upload', 'data_access')
            user: Username or identifier
            resource_id: ID of the resource being accessed/modified
            resource_type: Type of resource (e.g., 'user', 'portrait', 'video')
            action: Action performed (e.g., 'create', 'read', 'update', 'delete')
            details: Additional event details
            ip_address: Client IP address
            user_agent: Client user agent string
            success: Whether the operation was successful
            error_message: Error message if operation failed
            duration_ms: Operation duration in milliseconds
            metadata: Additional metadata
        """
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "user": user,
            "resource_id": resource_id,
            "resource_type": resource_type,
            "action": action,
            "success": success,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "error_message": error_message,
            "duration_ms": duration_ms,
            "metadata": metadata or {}
        }
        
        # Log to structured logger
        logger.info(
            "Audit event",
            **audit_entry
        )
        
        # Buffer for file logging
        with self._lock:
            self._buffer.append(audit_entry)
            if len(self._buffer) >= self._buffer_size:
                self._flush_buffer()
    
    def _flush_buffer(self) -> None:
        """Flush audit buffer to file."""
        if not self.log_file or not self._buffer:
            return
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                for entry in self._buffer:
                    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            self._buffer.clear()
        except Exception as e:
            logger.error("Failed to flush audit buffer", error=str(e))
    
    def flush(self) -> None:
        """Manually flush the audit buffer."""
        with self._lock:
            self._flush_buffer()
    
    def log_user_action(
        self,
        action: str,
        user: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """Log user-specific action."""
        self.log_event(
            event_type=f"user_{action}",
            user=user,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details,
            **kwargs
        )
    
    def log_file_operation(
        self,
        operation: str,
        user: str,
        file_path: str,
        file_size: Optional[int] = None,
        file_type: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log file operation."""
        details = {
            "file_path": file_path,
            "file_size": file_size,
            "file_type": file_type
        }
        
        self.log_event(
            event_type=f"file_{operation}",
            user=user,
            resource_type="file",
            resource_id=file_path,
            action=operation,
            details=details,
            **kwargs
        )
    
    def log_security_event(
        self,
        event_type: str,
        user: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """Log security-related event."""
        self.log_event(
            event_type=f"security_{event_type}",
            user=user,
            resource_type="security",
            action=event_type,
            details=details,
            **kwargs
        )
    
    def log_api_access(
        self,
        endpoint: str,
        method: str,
        user: Optional[str] = None,
        status_code: int = 200,
        response_time_ms: Optional[int] = None,
        **kwargs
    ) -> None:
        """Log API access."""
        details = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code
        }
        
        self.log_event(
            event_type="api_access",
            user=user,
            resource_type="api",
            action=f"{method} {endpoint}",
            details=details,
            duration_ms=response_time_ms,
            success=200 <= status_code < 400,
            **kwargs
        )
 
 
class OperationLogger:
    """Logger for tracking operations with timing and context."""
    
    def __init__(self, operation_name: str, user: Optional[str] = None, **context):
        self.operation_name = operation_name
        self.user = user
        self.context = context
        self.start_time = None
        self.audit_logger = AuditLogger()
    
    def __enter__(self):
        self.start_time = time.time()
        logger.info(
            "Operation started",
            operation=self.operation_name,
            user=self.user,
            **self.context
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = int((time.time() - self.start_time) * 1000) if self.start_time else None
        
        if exc_type is None:
            logger.info(
                "Operation completed",
                operation=self.operation_name,
                user=self.user,
                duration_ms=duration_ms,
                **self.context
            )
        else:
            logger.error(
                "Operation failed",
                operation=self.operation_name,
                user=self.user,
                duration_ms=duration_ms,
                error=str(exc_val),
                error_type=exc_type.__name__,
                **self.context
            )
        
        # Log to audit if user is specified
        if self.user:
            self.audit_logger.log_event(
                event_type="operation",
                user=self.user,
                action=self.operation_name,
                success=exc_type is None,
                error_message=str(exc_val) if exc_type else None,
                duration_ms=duration_ms,
                metadata=self.context
            )
 
 
def audit_action(
    event_type: str,
    resource_type: str,
    get_resource_id: Optional[callable] = None,
    log_details: Optional[callable] = None
):
    """
    Decorator for automatic audit logging of function calls.
    
    Args:
        event_type: Type of event (e.g., 'create', 'update', 'delete')
        resource_type: Type of resource being operated on
        get_resource_id: Function to extract resource ID from args/kwargs
        log_details: Function to extract additional details from args/kwargs
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract user from kwargs or use default
            user = kwargs.get('username') or kwargs.get('user')
            if not user and args:
                # Try to get user from first argument (usually self)
                user = getattr(args[0], 'user', None) if hasattr(args[0], 'user') else None
            
            # Extract resource ID
            resource_id = None
            if get_resource_id:
                resource_id = get_resource_id(*args, **kwargs)
            
            # Extract additional details
            details = {}
            if log_details:
                details = log_details(*args, **kwargs)
            
            # Start timing
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # Log successful operation
                audit_logger = AuditLogger()
                audit_logger.log_event(
                    event_type=event_type,
                    user=user,
                    resource_id=resource_id,
                    resource_type=resource_type,
                    action=event_type,
                    details=details,
                    success=True,
                    duration_ms=int((time.time() - start_time) * 1000)
                )
                
                return result
                
            except Exception as e:
                # Log failed operation
                audit_logger = AuditLogger()
                audit_logger.log_event(
                    event_type=event_type,
                    user=user,
                    resource_id=resource_id,
                    resource_type=resource_type,
                    action=event_type,
                    details=details,
                    success=False,
                    error_message=str(e),
                    duration_ms=int((time.time() - start_time) * 1000)
                )
                
                raise
        
        return wrapper
    return decorator
 
 
class SecurityLogger:
    """Specialized logger for security events."""
    
    @staticmethod
    def log_login_attempt(
        username: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Log login attempt."""
        audit_logger = AuditLogger()
        audit_logger.log_security_event(
            event_type="login_attempt",
            user=username,
            details={
                "success": success,
                "ip_address": ip_address,
                "user_agent": user_agent
            },
            success=success,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_permission_denied(
        user: str,
        resource_type: str,
        action: str,
        ip_address: Optional[str] = None
    ) -> None:
        """Log permission denied event."""
        audit_logger = AuditLogger()
        audit_logger.log_security_event(
            event_type="permission_denied",
            user=user,
            details={
                "resource_type": resource_type,
                "action": action
            },
            success=False,
            ip_address=ip_address
        )
    
    @staticmethod
    def log_suspicious_activity(
        description: str,
        user: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log suspicious activity."""
        audit_logger = AuditLogger()
        audit_logger.log_security_event(
            event_type="suspicious_activity",
            user=user,
            details={
                "description": description,
                **(details or {})
            },
            success=False,
            ip_address=ip_address
        )
    
    @staticmethod
    def log_data_access(
        user: str,
        resource_type: str,
        resource_id: str,
        action: str = "read",
        ip_address: Optional[str] = None
    ) -> None:
        """Log data access event."""
        audit_logger = AuditLogger()
        audit_logger.log_event(
            event_type="data_access",
            user=user,
            resource_id=resource_id,
            resource_type=resource_type,
            action=action,
            details={},
            success=True,
            ip_address=ip_address
        )
 
 
class PerformanceLogger:
    """Logger for performance monitoring."""
    
    @staticmethod
    def log_slow_operation(
        operation_name: str,
        duration_ms: int,
        threshold_ms: int = 1000,
        **context
    ) -> None:
        """Log slow operation."""
        if duration_ms > threshold_ms:
            logger.warning(
                "Slow operation detected",
                operation=operation_name,
                duration_ms=duration_ms,
                threshold_ms=threshold_ms,
                **context
            )
    
    @staticmethod
    def log_resource_usage(
        operation: str,
        memory_mb: Optional[float] = None,
        cpu_percent: Optional[float] = None,
        disk_usage_percent: Optional[float] = None,
        **context
    ) -> None:
        """Log resource usage."""
        details = {
            "operation": operation,
            "memory_mb": memory_mb,
            "cpu_percent": cpu_percent,
            "disk_usage_percent": disk_usage_percent
        }
        
        # Filter out None values
        details = {k: v for k, v in details.items() if v is not None}
        
        logger.info(
            "Resource usage",
            **details,
            **context
        )
 
 
# Global audit logger instance
audit_logger = AuditLogger(
    log_file="logs/audit.log"
)
 
 
# Context manager for easy operation logging
def log_operation(operation_name: str, user: Optional[str] = None, **context):
    """Context manager for logging operations."""
    return OperationLogger(operation_name, user, **context)
 
 
# Decorator for automatic function logging
def log_function_calls(include_args: bool = False, include_result: bool = False):
    """
    Decorator for automatic function call logging.
    
    Args:
        include_args: Whether to include function arguments in logs
        include_result: Whether to include function result in logs
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            log_data = {
                "function": func_name,
            }
            
            if include_args:
                log_data["args"] = str(args)[:200]  # Limit length
                log_data["kwargs"] = str(kwargs)[:200]  # Limit length
            
            logger.info("Function called", **log_data)
            
            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                
                log_data["duration_ms"] = duration_ms
                log_data["success"] = True
                
                if include_result:
                    log_data["result"] = str(result)[:200]  # Limit length
                
                logger.info("Function completed", **log_data)
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                
                log_data["duration_ms"] = duration_ms
                log_data["success"] = False
                log_data["error"] = str(e)
                
                logger.error("Function failed", **log_data)
                raise
        
        return wrapper
    return decorator



