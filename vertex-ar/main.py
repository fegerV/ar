"""
Main entry point for Vertex AR application.
Uses the modular app structure from app/main.py
"""
import uvicorn
from app.main import create_app


def main():
    """Main entry point."""
    app = create_app()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        access_log=True,
    )


if __name__ == "__main__":
    main()