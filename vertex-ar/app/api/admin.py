"""
Admin panel endpoints for Vertex AR API.
"""

from app.api.auth import get_current_user
from app.database import Database
from app.main import get_current_app
from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()


def get_database() -> Database:
    """Get database instance."""
    from app.main import get_current_app

    app = get_current_app()
    if not hasattr(app.state, "database"):
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
    if not hasattr(app.state, "templates"):
        BASE_DIR = app.state.config["BASE_DIR"]
        app.state.templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
    return app.state.templates


@router.get("/", response_class=HTMLResponse)
async def admin_panel(request: Request) -> HTMLResponse:
    """Serve admin panel HTML page."""
    database = get_database()
    templates = get_templates()

    # Get AR content list for admin display
    records = database.list_ar_content()
    return templates.TemplateResponse("admin.html", {"request": request, "records": records})


@router.get("/orders", response_class=HTMLResponse)
async def admin_orders_panel(request: Request) -> HTMLResponse:
    """Serve new admin panel for orders management."""
    templates = get_templates()
    return templates.TemplateResponse("admin_orders.html", {"request": request})
