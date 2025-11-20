"""
Authentication endpoints for Vertex AR API.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Optional

from app.auth import AuthSecurityManager, TokenManager, _hash_password, _verify_password
from app.database import Database
from app.models import TokenResponse, UserLogin
from app.main import get_current_app
from app.config import settings
from app.rate_limiter import create_rate_limit_dependency
from logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter()
security = HTTPBearer(auto_error=False)


def get_database() -> Database:
    """Get database instance."""
    app = get_current_app()
    return app.state.database


def get_token_manager() -> TokenManager:
    """Get token manager instance."""
    app = get_current_app()
    return app.state.tokens


def get_auth_security() -> AuthSecurityManager:
    """Get auth security manager instance."""
    app = get_current_app()
    return app.state.auth_security


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Get current authenticated user."""
    token = credentials.credentials if credentials else None
    if not token:
        token = request.cookies.get("authToken")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    tokens = get_token_manager()
    username = tokens.verify_token(token)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired or invalid")

    database = get_database()
    user = database.get_user(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is deactivated")

    return user


async def require_admin(request: Request) -> str:
    """Require admin role for endpoint access. Returns username.
    
    Can authenticate via:
    1. Authorization Bearer token header
    2. authToken cookie
    """
    tokens = get_token_manager()
    database = get_database()
    
    token = None
    
    # Try to get token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    
    # If no header token, try cookie
    if not token:
        token = request.cookies.get("authToken")
    
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    username = tokens.verify_token(token)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired or invalid")
    
    user = database.get_user(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    
    if not user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return username


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(create_rate_limit_dependency("5/minute"))])
async def login_user(
    request: Request,
    credentials: UserLogin
) -> TokenResponse:
    """Login user and return access token."""
    database = get_database()
    auth_security = get_auth_security()
    tokens = get_token_manager()
    
    logger.info(
        "login_attempt",
        username=credentials.username,
        client_host=request.client.host if request.client else None,
    )
    
    locked_until = auth_security.is_locked(credentials.username)
    if locked_until:
        logger.warning(
            "login_failed_account_locked",
            username=credentials.username,
            locked_until=locked_until.isoformat(),
            client_host=request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account locked until {locked_until.isoformat()}",
        )

    user = database.get_user(credentials.username)
    if user is None or not _verify_password(credentials.password, user["hashed_password"]):
        locked_until = auth_security.register_failure(credentials.username)
        if locked_until:
            logger.warning(
                "login_failed_account_locked_multiple_attempts",
                username=credentials.username,
                client_host=request.client.host if request.client else None,
            )
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account locked due to multiple failed attempts",
            )
        logger.warning(
            "login_failed_invalid_credentials",
            username=credentials.username,
            client_host=request.client.host if request.client else None,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    auth_security.reset(credentials.username)
    
    # Update last login timestamp
    database.update_last_login(credentials.username)
    
    token = tokens.issue_token(credentials.username)
    logger.info(
        "login_successful",
        username=credentials.username,
        client_host=request.client.host if request.client else None,
    )
    return TokenResponse(access_token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(create_rate_limit_dependency("5/minute"))])
async def logout_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Logout user and revoke token."""
    tokens = get_token_manager()
    username = tokens.verify_token(credentials.credentials)
    if username is None:
        logger.warning(
            "logout_failed_invalid_token",
            client_host=request.client.host if request.client else None,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired or invalid")
    tokens.revoke_token(credentials.credentials)
    logger.info(
        "logout_successful",
        username=username,
        client_host=request.client.host if request.client else None,
    )