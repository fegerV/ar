"""
User management endpoints for Vertex AR API.
"""

from app.auth import TokenManager, _hash_password, _verify_password
from app.database import Database
from app.main import get_current_app
from app.models import (
    MessageResponse,
    PasswordChange,
    UserCreate,
    UserProfile,
    UserResponse,
    UserSearch,
    UserStats,
    UserUpdate,
)
from fastapi import APIRouter, Depends, HTTPException, Request, status
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
        last_login=user.get("last_login"),
    )


@router.put("/profile", response_model=MessageResponse)
async def update_user_profile(user_update: UserUpdate, current_user: str = Depends(get_current_user)):
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
async def change_password(password_change: PasswordChange, current_user: str = Depends(get_current_user)):
    """Change current user's password."""
    database = get_database()

    logger.info("password_change_attempt", username=current_user)

    # Verify current password
    user = database.get_user(current_user)
    if not user or not user.get("is_active"):
        logger.warning("password_change_failed_user_not_found", username=current_user)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not _verify_password(password_change.current_password, user["hashed_password"]):
        logger.warning("password_change_failed_incorrect_password", username=current_user)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")

    # Update password
    new_hashed_password = _hash_password(password_change.new_password)
    success = database.change_password(current_user, new_hashed_password)
    if not success:
        logger.error("password_change_failed_database_error", username=current_user)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to change password")

    # Revoke all tokens for this user to force re-login
    tokens = get_token_manager()
    tokens.revoke_user(current_user)

    logger.info("password_changed_successfully", username=current_user)

    return MessageResponse(message="Password changed successfully. Please login again.")


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    is_admin: bool = None, is_active: bool = None, limit: int = 50, offset: int = 0, admin_user: str = Depends(require_admin)
):
    """List users (admin only)."""
    database = get_database()
    users = database.list_users(is_admin=is_admin, is_active=is_active, limit=limit, offset=offset)

    return [
        UserResponse(
            username=user["username"],
            email=user.get("email"),
            full_name=user.get("full_name"),
            is_admin=bool(user["is_admin"]),
            is_active=bool(user["is_active"]),
            created_at=user["created_at"],
            last_login=user.get("last_login"),
        )
        for user in users
    ]


@router.get("/users/search", response_model=list[UserResponse])
async def search_users(query: str, limit: int = 50, offset: int = 0, admin_user: str = Depends(require_admin)):
    """Search users (admin only)."""
    database = get_database()
    users = database.search_users(query, limit=limit, offset=offset)

    return [
        UserResponse(
            username=user["username"],
            email=user.get("email"),
            full_name=user.get("full_name"),
            is_admin=bool(user["is_admin"]),
            is_active=bool(user["is_active"]),
            created_at=user["created_at"],
            last_login=user.get("last_login"),
        )
        for user in users
    ]


@router.put("/users/{username}", response_model=MessageResponse)
async def update_user(username: str, user_update: UserUpdate, admin_user: str = Depends(require_admin)):
    """Update a user (admin only)."""
    database = get_database()

    logger.info(
        "user_update_attempt",
        target_username=username,
        admin_user=admin_user,
    )

    # Check if target user exists
    target_user = database.get_user(username)
    if not target_user:
        logger.warning(
            "user_update_failed_user_not_found",
            target_username=username,
            admin_user=admin_user,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Admin cannot modify themselves through this endpoint
    if username == admin_user:
        logger.warning(
            "user_update_failed_self_modification",
            target_username=username,
            admin_user=admin_user,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify yourself through this endpoint")

    # Update user
    update_data = user_update.dict(exclude_unset=True)
    success = database.update_user(username, **update_data)
    if not success:
        logger.error(
            "user_update_failed_database_error",
            target_username=username,
            admin_user=admin_user,
            update_fields=list(update_data.keys()),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update user")

    logger.info(
        "user_updated_successfully",
        target_username=username,
        admin_user=admin_user,
        updated_fields=list(update_data.keys()),
    )

    return MessageResponse(message=f"User {username} updated successfully")


@router.delete("/users/{username}", response_model=MessageResponse)
async def delete_user(username: str, admin_user: str = Depends(require_admin)):
    """Delete/deactivate a user (admin only)."""
    database = get_database()

    logger.info(
        "user_deletion_attempt",
        target_username=username,
        admin_user=admin_user,
    )

    # Check if target user exists
    target_user = database.get_user(username)
    if not target_user:
        logger.warning(
            "user_deletion_failed_user_not_found",
            target_username=username,
            admin_user=admin_user,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Admin cannot delete themselves
    if username == admin_user:
        logger.warning(
            "user_deletion_failed_self_deletion",
            target_username=username,
            admin_user=admin_user,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")

    # Soft delete user (deactivate)
    success = database.delete_user(username)
    if not success:
        logger.error(
            "user_deletion_failed_database_error",
            target_username=username,
            admin_user=admin_user,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to delete user")

    # Revoke all tokens for this user
    tokens = get_token_manager()
    tokens.revoke_user(username)

    logger.info(
        "user_deleted_successfully",
        target_username=username,
        admin_user=admin_user,
    )

    return MessageResponse(message=f"User {username} deactivated successfully")


@router.post("/users", response_model=MessageResponse)
async def create_user(user_create: UserCreate, admin_user: str = Depends(require_admin)):
    """Create a new user (admin only)."""
    database = get_database()

    logger.info(
        "user_creation_attempt",
        username=user_create.username,
        email=user_create.email,
        admin_user=admin_user,
    )

    # Check if user already exists
    existing_user = database.get_user(user_create.username)
    if existing_user:
        logger.warning(
            "user_creation_failed_duplicate",
            username=user_create.username,
            admin_user=admin_user,
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

    # Create user
    hashed_password = _hash_password(user_create.password)
    try:
        database.create_user(
            username=user_create.username,
            hashed_password=hashed_password,
            is_admin=False,  # New users are not admin by default
            email=user_create.email,
            full_name=user_create.full_name,
        )
        logger.info(
            "user_created_successfully",
            username=user_create.username,
            email=user_create.email,
            admin_user=admin_user,
        )
    except ValueError as e:
        logger.error(
            "user_creation_failed",
            username=user_create.username,
            error=str(e),
            admin_user=admin_user,
            exc_info=True,
        )
        if "user_already_exists" in str(e):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
        raise

    return MessageResponse(message=f"User {user_create.username} created successfully")


@router.get("/stats", response_model=UserStats)
async def get_user_stats(admin_user: str = Depends(require_admin)):
    """Get user statistics (admin only)."""
    database = get_database()
    stats = database.get_user_stats()

    return UserStats(**stats)
