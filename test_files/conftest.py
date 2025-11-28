"""Shared pytest configuration for all test suites

This conftest.py is shared across unit, integration, and performance tests.
It handles path setup and common fixtures.
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
vertex_ar_path = project_root / "vertex-ar"

if str(vertex_ar_path) not in sys.path:
    sys.path.insert(0, str(vertex_ar_path))

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
