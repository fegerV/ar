"""Tests for order creation endpoints compatibility."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import create_app
from fastapi.testclient import TestClient


def test_order_creation_endpoints_require_authentication() -> None:
    """Ensure both /orders/create and /api/orders/create enforce authentication."""
    app = create_app()
    with TestClient(app) as client:
        for path in ("/orders/create", "/api/orders/create"):
            response = client.post(path)
            assert response.status_code == 401
            assert response.json().get("detail") == "Not authenticated"
