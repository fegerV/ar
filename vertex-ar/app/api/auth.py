"""
Authentication endpoints for Vertex AR API.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter

from app.auth import AuthSecurityManager, TokenManager, _hash_password, _verify_password
from app.database import Database
from app.models import TokenResponse, UserCreate, UserLogin
from app.main import get_current_app
from logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter()
security = HTTPBearer()


def get_database() -> Database:
    """Get database instance."""
    from app.main import get_current_app
    app = get_current_app()
    if not hasattr(app.state, 'database'):
        from pathlib import Path
        BASE_DIR = app.state.config["BASE_DIR"]
        DB_PATH = BASE_DIR / "app_data.db"
        app.state.database = Database(DB_PATH)
    return app.state.database


def get_token_manager() -> TokenManager:
    """Get token manager instance."""
    from app.main import get_current_app
    app = get_current_app()
    if not hasattr(app.state, 'tokens'):
        session_timeout = app.state.config["SESSION_TIMEOUT_MINUTES"]
        app.state.tokens = TokenManager(session_timeout_minutes=session_timeout)
    return app.state.tokens


def get_auth_security() -> AuthSecurityManager:
    """Get auth security manager instance."""
    from app.main import get_current_app
    app = get_current_app()
    if not hasattr(app.state, 'auth_security'):
        max_attempts = app.state.config["AUTH_MAX_ATTEMPTS"]
        lockout_minutes = app.state.config["AUTH_LOCKOUT_MINUTES"]
        app.state.auth_security = AuthSecurityManager(max_attempts=max_attempts, lockout_minutes=lockout_minutes)
    return app.state.auth_security


def get_limiter() -> Limiter:
    """Get rate limiter instance."""
    from app.main import get_current_app
    return get_current_app().state.limiter


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Get current authenticated user."""
    tokens = get_token_manager()
    username = tokens.verify_token(credentials.credentials)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired or invalid")
    return username


def require_admin(username: str = Depends(get_current_user)) -> str:
    """Require admin access."""
    database = get_database()
    user = database.get_user(username)
    if not user or not user.get("is_admin") or not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return username


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    request: Request,
    user: UserCreate,
    limiter: Limiter = Depends(get_limiter)
) -> dict:
    """Register a new user (creates admin user for initial setup)."""
    app = get_current_app()
    auth_rate_limit = app.state.config["AUTH_RATE_LIMIT"]
    
    @limiter.limit(auth_rate_limit)
    async def _register(request: Request, user: UserCreate) -> dict:
        database = get_database()
        existing = database.get_user(user.username)
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
        
        # Check if this is the first user (make them admin)
        stats = database.get_user_stats()
        is_first_user = stats['total_users'] == 0
        
        try:
            database.create_user(
                username=user.username,
                hashed_password=_hash_password(user.password),
                is_admin=is_first_user,  # First user becomes admin
                email=user.email,
                full_name=user.full_name
            )
            logger.info(
                "User registered", 
                username=user.username,
                is_admin=is_first_user,
                email=user.email
            )
        except ValueError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
        
        return {
            "username": user.username,
            "is_admin": is_first_user,
            "message": "Admin user created" if is_first_user else "User created"
        }
    
    return await _register(request, user)


@router.post("/login", response_model=TokenResponse)
async def login_user(
    request: Request,
    credentials: UserLogin,
    limiter: Limiter = Depends(get_limiter)
) -> TokenResponse:
    """Login user and return access token."""
    app = get_current_app()
    auth_rate_limit = app.state.config["AUTH_RATE_LIMIT"]
    
    @limiter.limit(auth_rate_limit)
    async def _login(request: Request, credentials: UserLogin) -> TokenResponse:
        database = get_database()
        auth_security = get_auth_security()
        tokens = get_token_manager()
        
        locked_until = auth_security.is_locked(credentials.username)
        if locked_until:
            logger.warning(
                "Attempt to access locked account",
                username=credentials.username,
                locked_until=locked_until.isoformat(),
            )
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account locked until {locked_until.isoformat()}",
            )

        user = database.get_user(credentials.username)
        if user is None or not _verify_password(credentials.password, user["hashed_password"]):
            locked_until = auth_security.register_failure(credentials.username)
            if locked_until:
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Account locked due to multiple failed attempts",
                )
            logger.warning("Invalid login attempt", username=credentials.username)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        auth_security.reset(credentials.username)
        
        # Update last login timestamp
        database.update_last_login(credentials.username)
        
        token = tokens.issue_token(credentials.username)
        logger.info("User authenticated", username=credentials.username)
        return TokenResponse(access_token=token)
    
    return await _login(request, credentials)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    limiter: Limiter = Depends(get_limiter)
):
    """Logout user and revoke token."""
    app = get_current_app()
    auth_rate_limit = app.state.config["AUTH_RATE_LIMIT"]
    
    @limiter.limit(auth_rate_limit)
    async def _logout(request: Request, credentials: HTTPAuthorizationCredentials) -> None:
        tokens = get_token_manager()
        username = tokens.verify_token(credentials.credentials)
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired or invalid")
        tokens.revoke_token(credentials.credentials)
        logger.info("User logged out", username=username)
    
    await _logout(request, credentials)