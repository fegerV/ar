"""
Custom rate limiting implementation for Vertex AR.
Replaces SlowAPI to avoid compatibility issues.
"""
from collections import defaultdict, deque
from datetime import datetime
from threading import Lock
from typing import Dict

from fastapi import HTTPException, Request


class SimpleRateLimiter:
    """Simple in-memory rate limiter using deque for request tracking."""
    
    def __init__(self):
        self._requests: Dict[str, deque] = defaultdict(deque)
        self._lock = Lock()
    
    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Check if request is allowed based on rate limit.
        
        Args:
            key: Unique identifier for the client (usually IP + endpoint)
            limit: Maximum number of requests allowed
            window: Time window in seconds
            
        Returns:
            True if request is allowed, False otherwise
        """
        with self._lock:
            now = datetime.utcnow().timestamp()
            requests = self._requests[key]
            
            # Remove old requests outside the window
            while requests and requests[0] < now - window:
                requests.popleft()
            
            # Check if under limit
            if len(requests) < limit:
                requests.append(now)
                return True
            return False
    
    def get_retry_after(self, limit: str) -> int:
        """Get retry after header value for a given limit.
        
        Args:
            limit: Rate limit string like "5/minute"
            
        Returns:
            Retry after time in seconds
        """
        limit_count, period = limit.split('/')
        period_seconds = {
            'second': 1,
            'minute': 60,
            'hour': 3600,
            'day': 86400
        }[period]
        return period_seconds


# Global rate limiter instance
rate_limiter = SimpleRateLimiter()


def parse_rate_limit(limit: str) -> tuple[int, int]:
    """Parse rate limit string into count and window seconds.
    
    Args:
        limit: Rate limit string like "5/minute"
        
    Returns:
        Tuple of (limit_count, period_seconds)
    """
    limit_count, period = limit.split('/')
    period_seconds = {
        'second': 1,
        'minute': 60,
        'hour': 3600,
        'day': 86400
    }[period]
    return int(limit_count), period_seconds


async def rate_limit_dependency(request: Request, limit: str) -> None:
    """Rate limiting dependency for FastAPI endpoints.
    
    Args:
        request: FastAPI request object
        limit: Rate limit string like "5/minute"
        
    Raises:
        HTTPException: If rate limit is exceeded
    """
    from app.config import settings
    
    if not settings.RATE_LIMIT_ENABLED:
        return
        
    limit_count, period_seconds = parse_rate_limit(limit)
    
    key = f"{request.client.host}:{request.url.path}"
    if not rate_limiter.is_allowed(key, limit_count, period_seconds):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(period_seconds)}
        )


def create_rate_limit_dependency(limit: str):
    """Create a rate limiting dependency with a specific limit.
    
    Args:
        limit: Rate limit string like "5/minute"
        
    Returns:
        Async dependency function
    """
    async def dependency(request: Request) -> None:
        await rate_limit_dependency(request, limit)
    return dependency