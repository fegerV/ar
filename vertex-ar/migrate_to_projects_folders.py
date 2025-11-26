#!/usr/bin/env python3
"""
Migration script to create default project and folder structure.

This script creates a default project and folder for the default company,
which helps organize existing and new AR content.

Usage:
    python migrate_to_projects_folders.py
"""
import sys
import uuid
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import Database
from app.config import settings
from logging_setup import get_logger

logger = get_logger(__name__)


def create_default_structure(db: Database):
    """Create default project and folder structure."""
    
    # Check if default company exists
    default_company = db.get_company("vertex-ar-default")
    if not default_company:
        logger.error("Default company 'vertex-ar-default' not found. Creating it first.")
        db.create_company("vertex-ar-default", "Vertex AR")
        default_company = db.get_company("vertex-ar-default")
    
    logger.info(f"Found default company: {default_company['name']}")
    
    # Create default project if it doesn't exist
    default_project_id = "default-project"
    existing_project = db.get_project(default_project_id)
    
    if not existing_project:
        logger.info("Creating default project...")
        project = db.create_project(
            project_id=default_project_id,
            company_id="vertex-ar-default",
            name="Default Project",
            description="Default project for organizing AR content"
        )
        logger.info(f"✓ Created default project: {project['name']}")
    else:
        logger.info(f"✓ Default project already exists: {existing_project['name']}")
        project = existing_project
    
    # Create default folders
    default_folders = [
        {
            "id": "default-portraits",
            "name": "Портреты",
            "description": "Портреты с AR-анимацией"
        },
        {
            "id": "default-diplomas",
            "name": "Дипломы AR",
            "description": "AR-дипломы с анимацией"
        },
        {
            "id": "default-certificates",
            "name": "Сертификаты",
            "description": "Сертификаты с AR-эффектами"
        }
    ]
    
    for folder_data in default_folders:
        existing_folder = db.get_folder(folder_data["id"])
        if not existing_folder:
            logger.info(f"Creating folder: {folder_data['name']}...")
            folder = db.create_folder(
                folder_id=folder_data["id"],
                project_id=default_project_id,
                name=folder_data["name"],
                description=folder_data["description"]
            )
            logger.info(f"✓ Created folder: {folder['name']}")
        else:
            logger.info(f"✓ Folder already exists: {existing_folder['name']}")
    
    # Report statistics
    logger.info("\n=== Migration Summary ===")
    logger.info(f"Company: {default_company['name']} (ID: {default_company['id']})")
    logger.info(f"Project: {project['name']} (ID: {project['id']})")
    
    folders = db.list_folders(project_id=project['id'])
    logger.info(f"Folders: {len(folders)}")
    for folder in folders:
        portrait_count = db.get_folder_portrait_count(folder['id'])
        logger.info(f"  - {folder['name']}: {portrait_count} portraits")
    
    # Check for portraits without folder assignment
    all_portraits = db.list_portraits()
    unassigned_portraits = [p for p in all_portraits if not p.get('folder_id')]
    
    if unassigned_portraits:
        logger.info(f"\n⚠ Found {len(unassigned_portraits)} portraits without folder assignment")
        logger.info("You can manually assign them to folders using the update_portrait_folder() function")
    else:
        logger.info("\n✓ All portraits are assigned to folders")
    
    logger.info("\n=== Migration Complete ===")


def update_portrait_folder(db: Database, portrait_id: str, folder_id: str):
    """
    Helper function to assign a portrait to a folder.
    
    Args:
        db: Database instance
        portrait_id: ID of the portrait to update
        folder_id: ID of the folder to assign
    """
    # Verify portrait exists
    portrait = db.get_portrait(portrait_id)
    if not portrait:
        logger.error(f"Portrait {portrait_id} not found")
        return False
    
    # Verify folder exists
    folder = db.get_folder(folder_id)
    if not folder:
        logger.error(f"Folder {folder_id} not found")
        return False
    
    # Update portrait
    db._execute(
        "UPDATE portraits SET folder_id = ? WHERE id = ?",
        (folder_id, portrait_id)
    )
    
    logger.info(f"✓ Assigned portrait {portrait_id} to folder {folder['name']}")
    return True


def assign_all_unassigned_portraits(db: Database, default_folder_id: str = "default-portraits"):
    """
    Assign all unassigned portraits to a default folder.
    
    Args:
        db: Database instance
        default_folder_id: ID of the folder to assign portraits to
    """
    # Verify folder exists
    folder = db.get_folder(default_folder_id)
    if not folder:
        logger.error(f"Folder {default_folder_id} not found")
        return
    
    # Get unassigned portraits
    all_portraits = db.list_portraits()
    unassigned_portraits = [p for p in all_portraits if not p.get('folder_id')]
    
    if not unassigned_portraits:
        logger.info("No unassigned portraits found")
        return
    
    logger.info(f"Assigning {len(unassigned_portraits)} portraits to folder '{folder['name']}'...")
    
    for portrait in unassigned_portraits:
        db._execute(
            "UPDATE portraits SET folder_id = ? WHERE id = ?",
            (default_folder_id, portrait['id'])
        )
    
    logger.info(f"✓ Assigned {len(unassigned_portraits)} portraits to folder '{folder['name']}'")


def main():
    """Main migration function."""
    logger.info("Starting migration to projects and folders structure...")
    
    # Initialize database
    db = Database(settings.DB_PATH)
    
    try:
        # Create default structure
        create_default_structure(db)
        
        # Optional: Assign all unassigned portraits to default folder
        # Uncomment the line below to automatically assign all portraits
        # assign_all_unassigned_portraits(db, "default-portraits")
        
        logger.info("\n✓ Migration completed successfully!")
        logger.info("\nNext steps:")
        logger.info("1. Start the Vertex AR application")
        logger.info("2. Use the new /api/projects and /api/folders endpoints")
        logger.info("3. Create portraits with folder_id parameter")
        logger.info("4. Filter portraits by folder_id")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
