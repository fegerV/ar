#!/usr/bin/env python3
"""
Migration Script: Drop content_types Column

This script can be run standalone to drop the legacy content_types column
from the companies table and normalize storage_type values.

The migration:
1. Checks if content_types column exists
2. Creates a new table without the column
3. Copies all data with normalized storage_type (local → local_disk)
4. Drops old table and renames new table
5. Recreates indexes

Usage:
    python scripts/migrate_drop_content_types.py [--db-path PATH]

The migration is also automatically run on application startup via
app/database.py:_migrate_drop_content_types()
"""

import argparse
import sqlite3
import sys
from pathlib import Path


def migrate_drop_content_types(db_path: Path) -> None:
    """
    Drop the content_types column from companies table.
    
    Args:
        db_path: Path to SQLite database file
    """
    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    try:
        # Check if content_types column exists
        cursor = conn.execute("PRAGMA table_info(companies)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "content_types" not in columns:
            print("✓ Migration already applied - content_types column not found")
            return
        
        print("Starting migration: Dropping content_types column...")
        
        # Start transaction
        conn.execute("BEGIN TRANSACTION")
        
        try:
            # Create new table without content_types column
            print("Creating new companies table without content_types...")
            conn.execute("""
                CREATE TABLE companies_new (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    storage_type TEXT NOT NULL DEFAULT 'local_disk',
                    storage_connection_id TEXT,
                    yandex_disk_folder_id TEXT,
                    storage_folder_path TEXT,
                    backup_provider TEXT,
                    backup_remote_path TEXT,
                    email TEXT,
                    description TEXT,
                    city TEXT,
                    phone TEXT,
                    website TEXT,
                    social_links TEXT,
                    manager_name TEXT,
                    manager_phone TEXT,
                    manager_email TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Copy data with normalized storage_type
            print("Copying data and normalizing storage_type values...")
            copy_columns = [col for col in columns if col != "content_types"]
            columns_str = ", ".join(copy_columns)
            
            # Build SELECT with CASE for storage_type normalization
            select_columns = []
            for col in copy_columns:
                if col == "storage_type":
                    select_columns.append("CASE WHEN storage_type = 'local' THEN 'local_disk' ELSE storage_type END")
                else:
                    select_columns.append(col)
            select_str = ", ".join(select_columns)
            
            conn.execute(f"""
                INSERT INTO companies_new ({columns_str})
                SELECT {select_str}
                FROM companies
            """)
            
            # Get count for verification
            cursor = conn.execute("SELECT COUNT(*) FROM companies_new")
            migrated_count = cursor.fetchone()[0]
            print(f"✓ Migrated {migrated_count} companies")
            
            # Check for normalized storage_type values
            cursor = conn.execute("SELECT COUNT(*) FROM companies_new WHERE storage_type = 'local_disk'")
            local_disk_count = cursor.fetchone()[0]
            if local_disk_count > 0:
                print(f"✓ Normalized storage_type: {local_disk_count} companies now use 'local_disk'")
            
            # Drop old table
            print("Dropping old companies table...")
            conn.execute("DROP TABLE companies")
            
            # Rename new table
            print("Renaming new table to companies...")
            conn.execute("ALTER TABLE companies_new RENAME TO companies")
            
            # Recreate index
            print("Recreating indexes...")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_companies_storage ON companies(storage_connection_id)")
            
            # Commit transaction
            conn.commit()
            print("✓ Migration completed successfully!")
            
            # Verify schema
            print("\nVerifying schema...")
            cursor = conn.execute("PRAGMA table_info(companies)")
            final_columns = [row[1] for row in cursor.fetchall()]
            
            if "content_types" in final_columns:
                print("✗ ERROR: content_types column still exists!")
                sys.exit(1)
            else:
                print("✓ Schema verification passed - content_types column removed")
            
            print(f"\nFinal schema has {len(final_columns)} columns:")
            for col in final_columns:
                print(f"  - {col}")
            
        except Exception as e:
            # Rollback on any error
            print(f"✗ Migration failed: {e}")
            conn.execute("ROLLBACK")
            raise
            
    finally:
        conn.close()


def main():
    """Main entry point for standalone execution."""
    parser = argparse.ArgumentParser(
        description="Drop content_types column from companies table"
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("vertex-ar/vertex_ar.db"),
        help="Path to SQLite database file (default: vertex-ar/vertex_ar.db)"
    )
    
    args = parser.parse_args()
    
    if not args.db_path.exists():
        print(f"✗ Database file not found: {args.db_path}")
        print("Please specify the correct path with --db-path")
        sys.exit(1)
    
    # Create backup before migration
    backup_path = args.db_path.with_suffix(".db.backup")
    print(f"Creating backup: {backup_path}")
    import shutil
    shutil.copy2(args.db_path, backup_path)
    print("✓ Backup created")
    
    try:
        migrate_drop_content_types(args.db_path)
        print("\n✓ Migration completed successfully!")
        print(f"  Backup saved to: {backup_path}")
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        print(f"  Backup available at: {backup_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
