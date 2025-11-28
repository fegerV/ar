#!/usr/bin/env python3
"""
Test script for Projects and Folders API.

Tests basic CRUD operations for projects and folders.

Usage:
    python test_projects_folders_api.py
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import Database
from app.config import settings
from logging_setup import get_logger

logger = get_logger(__name__)


def test_projects_api(db: Database):
    """Test projects API."""
    logger.info("=" * 60)
    logger.info("Testing Projects API")
    logger.info("=" * 60)
    
    # 1. List all projects
    projects = db.list_projects()
    logger.info(f"✓ Found {len(projects)} projects")
    for project in projects:
        logger.info(f"  - {project['name']} (ID: {project['id']}, Company: {project['company_id']})")
    
    # 2. Get project by ID
    if projects:
        project_id = projects[0]['id']
        project = db.get_project(project_id)
        logger.info(f"✓ Get project by ID: {project['name']}")
        
        # 3. Get project folder count
        folder_count = db.get_project_folder_count(project_id)
        logger.info(f"✓ Project has {folder_count} folders")
        
        # 4. Get project portrait count
        portrait_count = db.get_project_portrait_count(project_id)
        logger.info(f"✓ Project has {portrait_count} portraits")
    
    # 5. Test project creation
    import uuid
    test_project_id = str(uuid.uuid4())
    try:
        test_project = db.create_project(
            project_id=test_project_id,
            company_id="vertex-ar-default",
            name="Test Project",
            description="Test project for API testing"
        )
        logger.info(f"✓ Created test project: {test_project['name']}")
        
        # 6. Update project
        success = db.update_project(
            project_id=test_project_id,
            name="Updated Test Project",
            description="Updated description"
        )
        if success:
            logger.info("✓ Updated test project")
        
        # 7. Delete project
        success = db.delete_project(test_project_id)
        if success:
            logger.info("✓ Deleted test project")
    except Exception as e:
        logger.error(f"✗ Error testing project CRUD: {e}")
    
    logger.info("")


def test_folders_api(db: Database):
    """Test folders API."""
    logger.info("=" * 60)
    logger.info("Testing Folders API")
    logger.info("=" * 60)
    
    # 1. Get a project to work with
    projects = db.list_projects()
    if not projects:
        logger.error("✗ No projects found. Please run migration first.")
        return
    
    project_id = projects[0]['id']
    logger.info(f"Using project: {projects[0]['name']} (ID: {project_id})")
    
    # 2. List folders in project
    folders = db.list_folders(project_id=project_id)
    logger.info(f"✓ Found {len(folders)} folders in project")
    for folder in folders:
        portrait_count = db.get_folder_portrait_count(folder['id'])
        logger.info(f"  - {folder['name']} (ID: {folder['id']}, Portraits: {portrait_count})")
    
    # 3. Get folder by ID
    if folders:
        folder_id = folders[0]['id']
        folder = db.get_folder(folder_id)
        logger.info(f"✓ Get folder by ID: {folder['name']}")
    
    # 4. Test folder creation
    import uuid
    test_folder_id = str(uuid.uuid4())
    try:
        test_folder = db.create_folder(
            folder_id=test_folder_id,
            project_id=project_id,
            name="Test Folder",
            description="Test folder for API testing"
        )
        logger.info(f"✓ Created test folder: {test_folder['name']}")
        
        # 5. Update folder
        success = db.update_folder(
            folder_id=test_folder_id,
            name="Updated Test Folder",
            description="Updated description"
        )
        if success:
            logger.info("✓ Updated test folder")
        
        # 6. Delete folder
        success = db.delete_folder(test_folder_id)
        if success:
            logger.info("✓ Deleted test folder")
    except Exception as e:
        logger.error(f"✗ Error testing folder CRUD: {e}")
    
    logger.info("")


def test_portraits_with_folders(db: Database):
    """Test portrait creation with folder assignment."""
    logger.info("=" * 60)
    logger.info("Testing Portraits with Folders")
    logger.info("=" * 60)
    
    # Get a folder to work with
    folders = db.list_folders()
    if not folders:
        logger.error("✗ No folders found. Please run migration first.")
        return
    
    folder_id = folders[0]['id']
    folder_name = folders[0]['name']
    logger.info(f"Using folder: {folder_name} (ID: {folder_id})")
    
    # List portraits in folder
    portraits = db.list_portraits(folder_id=folder_id)
    logger.info(f"✓ Found {len(portraits)} portraits in folder")
    
    # List portraits without folder
    all_portraits = db.list_portraits()
    unassigned = [p for p in all_portraits if not p.get('folder_id')]
    logger.info(f"✓ Found {len(unassigned)} portraits without folder assignment")
    
    logger.info("")


def test_hierarchy_navigation(db: Database):
    """Test navigating the hierarchy."""
    logger.info("=" * 60)
    logger.info("Testing Hierarchy Navigation")
    logger.info("=" * 60)
    
    # Get all companies
    companies = db.list_companies()
    logger.info(f"Companies: {len(companies)}")
    
    for company in companies:
        logger.info(f"\n📁 {company['name']} (ID: {company['id']})")
        
        # Get projects for company
        projects = db.list_projects(company_id=company['id'])
        logger.info(f"  └─ Projects: {len(projects)}")
        
        for project in projects:
            folder_count = db.get_project_folder_count(project['id'])
            portrait_count = db.get_project_portrait_count(project['id'])
            logger.info(f"     └─ {project['name']} ({folder_count} folders, {portrait_count} portraits)")
            
            # Get folders for project
            folders = db.list_folders(project_id=project['id'])
            for folder in folders:
                portrait_count = db.get_folder_portrait_count(folder['id'])
                logger.info(f"        └─ {folder['name']} ({portrait_count} portraits)")
    
    logger.info("")


def main():
    """Main test function."""
    logger.info("Starting Projects and Folders API Tests")
    logger.info("")
    
    # Initialize database
    db = Database(settings.DB_PATH)
    
    try:
        # Run tests
        test_projects_api(db)
        test_folders_api(db)
        test_portraits_with_folders(db)
        test_hierarchy_navigation(db)
        
        logger.info("=" * 60)
        logger.info("✓ All tests completed successfully!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"✗ Tests failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
