"""
User management endpoints for Vertex AR API.
"""
import csv
from datetime import datetime
from io import BytesIO, StringIO
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.auth import _hash_password, _verify_password, TokenManager
from app.database import Database
from app.models import (
    BulkIdsRequest,
    MessageResponse,
    PaginatedUsersResponse,
    PasswordChange,
    UserCreate,
    UserProfile,
    UserResponse,
    UserSearch,
    UserStats,
    UserUpdate,
)
from app.main import get_current_app
from logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter()


def get_database() -> Database:
    """Get database instance."""
    app = get_current_app()
    return app.state.database


def _user_to_response(user: Dict[str, Any]) -> UserResponse:
    """Convert database row to user response model."""
    return UserResponse(
        username=user["username"],
        email=user.get("email"),
        full_name=user.get("full_name"),
        is_admin=bool(user["is_admin"]),
        is_active=bool(user["is_active"]),
        created_at=user["created_at"],
        last_login=user.get("last_login"),
    )


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
    password_change: PasswordChange,
    current_user: str = Depends(get_current_user)
):
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


@router.get("/users/paginated", response_model=PaginatedUsersResponse)
async def list_users_paginated(
    page: int = 1,
    page_size: int = 25,
    search: Optional[str] = None,
    filter: str = "all",
    admin_user: str = Depends(require_admin),
) -> PaginatedUsersResponse:
    """List users with pagination and optional filters (admin only)."""
    database = get_database()

    page = max(page, 1)
    page_size = max(1, min(page_size, 100))

    filter_value = (filter or "all").lower()
    is_active_filter: Optional[bool] = None
    is_admin_filter: Optional[bool] = None

    if filter_value == "active":
        is_active_filter = True
    elif filter_value == "inactive":
        is_active_filter = False
    elif filter_value == "admin":
        is_admin_filter = True

    total = database.count_users(
        is_admin=is_admin_filter,
        is_active=is_active_filter,
        search=search,
    )

    if total == 0:
        logger.info(
            "users_list_empty",
            filter=filter_value,
            search=search,
            admin=admin_user,
        )
        return PaginatedUsersResponse(
            items=[],
            total=0,
            page=1,
            page_size=page_size,
            total_pages=0,
        )

    total_pages = (total + page_size - 1) // page_size
    if page > total_pages:
        page = total_pages

    offset = (page - 1) * page_size
    users = database.list_users(
        is_admin=is_admin_filter,
        is_active=is_active_filter,
        search=search,
        limit=page_size,
        offset=offset,
    )

    items = [_user_to_response(user) for user in users]

    logger.info(
        "users_list_paginated",
        total=total,
        page=page,
        page_size=page_size,
        returned=len(items),
        filter=filter_value,
        search=search,
        admin=admin_user,
    )

    return PaginatedUsersResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    is_admin: bool = None,
    is_active: bool = None,
    limit: int = 50,
    offset: int = 0,
    admin_user: str = Depends(require_admin)
):
    """List users (admin only)."""
    database = get_database()
    users = database.list_users(is_admin=is_admin, is_active=is_active, limit=limit, offset=offset)

    return [_user_to_response(user) for user in users]


@router.get("/users/search", response_model=list[UserResponse])
async def search_users(
    query: str,
    limit: int = 50,
    offset: int = 0,
    admin_user: str = Depends(require_admin)
):
    """Search users (admin only)."""
    database = get_database()
    users = database.search_users(query, limit=limit, offset=offset)

    return [_user_to_response(user) for user in users]


@router.put("/users/{username}", response_model=MessageResponse)
async def update_user(
    username: str,
    user_update: UserUpdate,
    admin_user: str = Depends(require_admin)
):
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
async def delete_user(
    username: str,
    admin_user: str = Depends(require_admin)
):
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


@router.post("/users/bulk-delete", response_model=MessageResponse)
async def bulk_delete_users(
    payload: BulkIdsRequest,
    admin_user: str = Depends(require_admin),
) -> MessageResponse:
    """Bulk deactivate users (admin only)."""
    database = get_database()
    tokens = get_token_manager()

    unique_usernames = [username for username in dict.fromkeys(payload.ids) if username]
    if not unique_usernames:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No usernames provided")

    skipped_self = False
    skipped_admins: List[str] = []
    deleted = 0

    for username in unique_usernames:
        if username == admin_user:
            skipped_self = True
            continue

        user = database.get_user(username)
        if not user:
            continue

        if user.get("is_admin"):
            skipped_admins.append(username)
            continue

        if database.delete_user(username):
            deleted += 1
            tokens.revoke_user(username)

    logger.info(
        "users_bulk_delete",
        requested=len(unique_usernames),
        deleted=deleted,
        skipped_admins=len(skipped_admins),
        skipped_self=skipped_self,
        admin=admin_user,
    )

    info_parts = []
    if skipped_admins:
        info_parts.append(f"администраторов пропущено: {len(skipped_admins)}")
    if skipped_self:
        info_parts.append("ваш аккаунт не может быть деактивирован")

    if deleted == 0:
        message = "Пользователи не найдены или уже деактивированы"
        if info_parts:
            message += f" ({'; '.join(info_parts)})"
        return MessageResponse(message=message)

    extra = f" ({'; '.join(info_parts)})" if info_parts else ""
    return MessageResponse(message=f"Деактивировано пользователей: {deleted}{extra}")


@router.get("/users/export")
async def export_users(
    format: str = "csv",
    search: Optional[str] = None,
    filter: str = "all",
    ids: Optional[str] = None,
    admin_user: str = Depends(require_admin),
):
    """Export users in CSV or Excel format."""
    database = get_database()

    filter_value = (filter or "all").lower()
    is_active_filter: Optional[bool] = None
    is_admin_filter: Optional[bool] = None

    if filter_value == "active":
        is_active_filter = True
    elif filter_value == "inactive":
        is_active_filter = False
    elif filter_value == "admin":
        is_admin_filter = True

    selected_ids: List[str] = []
    if ids:
        selected_ids = [username.strip() for username in ids.split(",") if username.strip()]

    if selected_ids:
        users = [user for username in selected_ids if (user := database.get_user(username))]
    else:
        total = database.count_users(
            is_admin=is_admin_filter,
            is_active=is_active_filter,
            search=search,
        )
        if total:
            users = database.list_users(
                is_admin=is_admin_filter,
                is_active=is_active_filter,
                search=search,
                limit=total,
                offset=0,
            )
        else:
            users = []

    export_rows = [
        (
            user["username"],
            user.get("full_name") or "",
            user.get("email") or "",
            "Да" if user.get("is_admin") else "Нет",
            "Да" if user.get("is_active") else "Нет",
            user.get("created_at"),
            user.get("last_login") or "",
        )
        for user in users
    ]

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    format_lower = format.lower()

    if format_lower == "csv":
        text_buffer = StringIO()
        text_buffer.write("\ufeff")
        writer = csv.writer(text_buffer, delimiter=";")
        writer.writerow([
            "Имя пользователя",
            "Полное имя",
            "Email",
            "Администратор",
            "Активен",
            "Создан",
            "Последний вход",
        ])
        for row in export_rows:
            writer.writerow(row)
        byte_buffer = BytesIO(text_buffer.getvalue().encode("utf-8"))
        byte_buffer.seek(0)
        filename = f"users_{timestamp}.csv"
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        logger.info(
            "users_export_csv",
            total=len(export_rows),
            search=search,
            filter=filter_value,
            ids=len(selected_ids) if selected_ids else None,
            admin=admin_user,
        )
        return StreamingResponse(byte_buffer, media_type="text/csv; charset=utf-8", headers=headers)

    if format_lower in {"xlsx", "excel"}:
        try:
            from openpyxl import Workbook
        except ImportError as exc:
            logger.error("openpyxl_not_installed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Excel export is not available",
            ) from exc

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Users"
        sheet.append([
            "Имя пользователя",
            "Полное имя",
            "Email",
            "Администратор",
            "Активен",
            "Создан",
            "Последний вход",
        ])
        for row in export_rows:
            sheet.append(row)
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        filename = f"users_{timestamp}.xlsx"
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        logger.info(
            "users_export_excel",
            total=len(export_rows),
            search=search,
            filter=filter_value,
            ids=len(selected_ids) if selected_ids else None,
            admin=admin_user,
        )
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers,
        )

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported export format")


@router.post("/users", response_model=MessageResponse)
async def create_user(
    user_create: UserCreate,
    admin_user: str = Depends(require_admin)
):
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
            full_name=user_create.full_name
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