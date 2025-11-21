"""
User profile management endpoints for Vertex AR API.
Only contains profile management for administrators (no user management).
"""
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.utils import hash_password, verify_password
from app.auth import TokenManager
from app.database import Database
from app.models import (
    MessageResponse,
    UserProfile,
    UserUpdate,
    PasswordChange,
)
from app.main import get_current_app
from logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter()


def get_database() -> Database:
    """Get database instance."""
    app = get_current_app()
    return app.state.database


def get_token_manager():
    """Get token manager instance."""
    app = get_current_app()
    return app.state.tokens


async def get_current_user(request: Request) -> str:
    """Get current authenticated user from token."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.split(" ")[1]
    tokens = get_token_manager()
    username = tokens.verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username


def require_admin(username: str = Depends(get_current_user)) -> str:
    """Require admin access."""
    database = get_database()
    user = database.get_user(username)
    if not user or not user.get("is_admin") or not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return username


@router.get("/profile", response_model=UserProfile)
async def get_user_profile(current_user: str = Depends(get_current_user)):
    """Get current user's profile."""
    database = get_database()

    logger.info("profile_fetch_attempt", username=current_user)

    user = database.get_user(current_user)
    if not user or not user.get("is_active"):
        logger.warning("profile_fetch_failed_user_not_found", username=current_user)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    logger.info("profile_fetched_successfully", username=current_user)

    return UserProfile(
        username=user["username"],
        email=user.get("email"),
        full_name=user.get("full_name"),
        created_at=user["created_at"],
        last_login=user.get("last_login")
    )


@router.put("/profile", response_model=MessageResponse)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: str = Depends(get_current_user)
):
    """Update current user's profile."""
    database = get_database()

    logger.info("profile_update_attempt", username=current_user)

    # Users can only update their own email and full_name
    update_data = {}
    if user_update.email is not None:
        update_data["email"] = user_update.email
    if user_update.full_name is not None:
        update_data["full_name"] = user_update.full_name

    if not update_data:
        logger.warning("profile_update_failed_no_fields", username=current_user)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    success = database.update_user(current_user, **update_data)
    if not success:
        logger.error("profile_update_failed_database_error", username=current_user, update_fields=list(update_data.keys()))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update profile")

    logger.info("profile_updated_successfully", username=current_user, updated_fields=list(update_data.keys()))

    return MessageResponse(message="Profile updated successfully")


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: Request,
    password_change: PasswordChange,
    current_user: str = Depends(get_current_user)
):
    """Change current user's password."""
    database = get_database()

    logger.info("password_change_attempt", username=current_user)

    # Get current user
    user = database.get_user(current_user)
    if not user or not user.get("is_active"):
        logger.warning("password_change_failed_user_not_found", username=current_user)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Verify current password
    if not verify_password(password_change.current_password, user["hashed_password"]):
        logger.warning("password_change_failed_invalid_current_password", username=current_user)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    # Hash new password
    new_password_hash = hash_password(password_change.new_password)

    # Update password
    success = database.change_password(current_user, new_password_hash)
    if not success:
        logger.error("password_change_failed_database_error", username=current_user)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to change password")

    # Revoke all other tokens for this user (force re-login on other devices)
    tokens = get_token_manager()
    # Получаем токен из заголовка запроса для сохранения текущей сессии
    auth_header = request.headers.get("Authorization")
    current_token = None
    if auth_header and auth_header.startswith("Bearer "):
        current_token = auth_header.split(" ")[1]
    tokens.revoke_user_except_current(current_user, current_token)

    logger.info("password_changed_successfully", username=current_user)

    return MessageResponse(message="Password changed successfully")
