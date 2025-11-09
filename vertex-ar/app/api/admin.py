"""
Admin panel endpoints for Vertex AR API.
"""
from fastapi import APIRouter, Request, Response, File, UploadFile, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.auth import get_current_user, require_admin
from app.database import Database
from app.main import get_current_app
from app.models import ARContentResponse
from app.rate_limiter import create_rate_limit_dependency
from app.auth import TokenManager, _verify_password
from logging_setup import get_logger

logger = get_logger(__name__)
router = APIRouter()


def get_database() -> Database:
    """Get database instance."""
    from app.main import get_current_app
    app = get_current_app()
    if not hasattr(app.state, 'database'):
        from pathlib import Path
        BASE_DIR = app.state.config["BASE_DIR"]
        DB_PATH = BASE_DIR / "app_data.db"
        from app.database import Database
        app.state.database = Database(DB_PATH)
    return app.state.database


def get_templates() -> Jinja2Templates:
    """Get Jinja2 templates instance."""
    from app.main import get_current_app
    app = get_current_app()
    if not hasattr(app.state, 'templates'):
        BASE_DIR = app.state.config["BASE_DIR"]
        app.state.templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
    return app.state.templates


@router.get("/", response_class=HTMLResponse)
async def admin_panel(request: Request) -> HTMLResponse:
    """Serve admin panel or login page."""
    auth_token = request.cookies.get("authToken")
    if not auth_token:
        templates = get_templates()
        error = request.query_params.get("error")
        return templates.TemplateResponse("login.html", {"request": request, "error": error})
    
    database = get_database()
    templates = get_templates()
    
    # Get AR content list for admin display
    records = database.list_ar_content()
    return templates.TemplateResponse("admin.html", {"request": request, "records": records})


@router.get("/orders", response_class=HTMLResponse)
async def admin_orders_panel(request: Request) -> HTMLResponse:
    """Serve new admin panel for orders management."""
    auth_token = request.cookies.get("authToken")
    if not auth_token:
        return RedirectResponse(url="/admin", status_code=status.HTTP_302_FOUND)
    
    templates = get_templates()
    return templates.TemplateResponse("admin_orders.html", {"request": request})


@router.post("/login")
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
) -> RedirectResponse:
    """Handle admin login from HTML form."""
    database = get_database()
    
    try:
        user = database.get_user(username)
        if user is None or not _verify_password(password, user["hashed_password"]):
            logger.warning(f"Admin login failed for user: {username}")
            return RedirectResponse(
                url="/admin?error=invalid_credentials",
                status_code=status.HTTP_302_FOUND
            )
        
        if not user.get("is_admin"):
            logger.warning(f"Non-admin login attempt by user: {username}")
            return RedirectResponse(
                url="/admin?error=invalid_credentials",
                status_code=status.HTTP_302_FOUND
            )
        
        app = get_current_app()
        tokens = app.state.tokens
        token = tokens.issue_token(username)
        
        logger.info(f"Admin login successful for user: {username}")
        
        response = RedirectResponse(url="/admin/orders", status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key="authToken",
            value=token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=86400
        )
        return response
    except Exception as e:
        logger.error(f"Error during admin login: {e}")
        return RedirectResponse(
            url="/admin?error=invalid_credentials",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/upload", response_model=ARContentResponse, dependencies=[Depends(create_rate_limit_dependency("10/minute"))])
async def upload_ar_content_admin(
    request: Request,
    image: UploadFile = File(...),
    video: UploadFile = File(...),
    username: str = Depends(require_admin)
) -> ARContentResponse:
    """
    Upload image and video to create AR content via admin panel.
    Supports both Authorization header and cookie-based authentication.
    """
    from app.api.ar import upload_ar_content
    return await upload_ar_content(request, image, video, username)