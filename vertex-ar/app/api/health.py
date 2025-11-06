"""
Health check endpoints for Vertex AR API.
"""

from app.main import get_current_app
from app.models import HealthResponse
from fastapi import APIRouter

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint for Docker and load balancers."""
    app = get_current_app()
    version = app.state.config["VERSION"]
    return {"status": "healthy", "version": version}


@router.get("/version", response_model=dict)
async def get_version() -> dict:
    """Get API version."""
    app = get_current_app()
    version = app.state.config["VERSION"]
    return {"version": version}
