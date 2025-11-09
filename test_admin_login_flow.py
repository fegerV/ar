"""Tests for default admin login flow."""
import os
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

# Ensure we can import the application package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "vertex-ar"))

from app.auth import _hash_password  # noqa: E402
from app.config import settings  # noqa: E402
from app.main import create_app  # noqa: E402


def test_default_admin_can_login_and_access_dashboard():
    """Ensure the seeded admin can authenticate via the HTML admin panel."""
    original_db_path = settings.DB_PATH
    original_storage_root = settings.STORAGE_ROOT
    original_rate_limit_enabled = settings.RATE_LIMIT_ENABLED
    original_running_tests = settings.RUNNING_TESTS
    original_env_rate_limit = os.environ.get("RATE_LIMIT_ENABLED")
    original_env_running_tests = os.environ.get("RUNNING_TESTS")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            temp_db_path = temp_path / "app_data.db"
            temp_storage_root = temp_path / "storage"
            temp_storage_root.mkdir(parents=True, exist_ok=True)

            settings.DB_PATH = temp_db_path
            settings.STORAGE_ROOT = temp_storage_root
            settings.RATE_LIMIT_ENABLED = False
            settings.RUNNING_TESTS = True

            os.environ["RATE_LIMIT_ENABLED"] = "false"
            os.environ["RUNNING_TESTS"] = "1"

            app = create_app()
            with TestClient(app) as client:
                admin_user = app.state.database.get_user(settings.DEFAULT_ADMIN_USERNAME)
                assert admin_user is not None
                assert admin_user["is_admin"] == 1
                assert admin_user["is_active"] == 1
                assert admin_user["hashed_password"] == _hash_password(settings.DEFAULT_ADMIN_PASSWORD)

                login_page = client.get("/admin")
                assert login_page.status_code == 200
                assert "Admin Login" in login_page.text

                login_response = client.post(
                    "/admin/login",
                    data={
                        "username": settings.DEFAULT_ADMIN_USERNAME,
                        "password": settings.DEFAULT_ADMIN_PASSWORD,
                    },
                    follow_redirects=False,
                )
                assert login_response.status_code == 302
                assert login_response.headers["location"] == "/admin"
                assert client.cookies.get("authToken")

                dashboard_response = client.get("/admin")
                assert dashboard_response.status_code == 200
                assert "Admin Panel" in dashboard_response.text
    finally:
        # Restore global settings and environment variables
        settings.DB_PATH = original_db_path
        settings.STORAGE_ROOT = original_storage_root
        settings.RATE_LIMIT_ENABLED = original_rate_limit_enabled
        settings.RUNNING_TESTS = original_running_tests

        if original_env_rate_limit is None:
            os.environ.pop("RATE_LIMIT_ENABLED", None)
        else:
            os.environ["RATE_LIMIT_ENABLED"] = original_env_rate_limit

        if original_env_running_tests is None:
            os.environ.pop("RUNNING_TESTS", None)
        else:
            os.environ["RUNNING_TESTS"] = original_env_running_tests
