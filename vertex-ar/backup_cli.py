#!/usr/bin/env python3
"""
Command-line interface for Vertex AR backup management.
"""
import argparse
import sys
from pathlib import Path
from typing import Optional

from backup_manager import create_backup_manager
from logging_setup import get_logger

logger = get_logger(__name__)


def format_size(size_bytes: int) -> str:
    """Format size in bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def cmd_create(args):
    """Create a new backup."""
    manager = create_backup_manager(
        backup_dir=Path(args.backup_dir) if args.backup_dir else None,
        max_backups=args.max_backups
    )
    
    if args.type == "database":
        print("Creating database backup...")
        result = manager.backup_database()
    elif args.type == "storage":
        print("Creating storage backup...")
        result = manager.backup_storage()
    elif args.type == "full":
        print("Creating full backup (database + storage)...")
        result = manager.create_full_backup()
    else:
        print(f"Error: Unknown backup type '{args.type}'")
        return 1
    
    if result.get("success"):
        print("✓ Backup created successfully")
        if "metadata" in result:
            metadata = result["metadata"]
            print(f"  Path: {metadata.get('backup_path')}")
            if "file_size" in metadata:
                print(f"  Size: {format_size(metadata['file_size'])}")
            if "checksum" in metadata:
                print(f"  Checksum: {metadata['checksum'][:16]}...")
    else:
        print(f"✗ Backup failed: {result.get('error')}")
        return 1
    
    # Rotate old backups
    if not args.no_rotate:
        print("\nRotating old backups...")
        removed = manager.rotate_backups()
        if sum(removed.values()) > 0:
            print(f"  Removed: {removed}")
        else:
            print("  No old backups to remove")
    
    return 0


def cmd_list(args):
    """List available backups."""
    manager = create_backup_manager(
        backup_dir=Path(args.backup_dir) if args.backup_dir else None
    )
    
    backups = manager.list_backups(args.type)
    
    if not backups:
        print(f"No {args.type} backups found")
        return 0
    
    print(f"\n{args.type.capitalize()} Backups ({len(backups)} total):\n")
    print(f"{'Timestamp':<20} {'Type':<10} {'Size':<12} {'Path'}")
    print("-" * 80)
    
    for backup in backups:
        timestamp = backup.get("timestamp", "unknown")
        backup_type = backup.get("type", "unknown")
        
        # Get size
        if backup_type == "full":
            db_size = backup.get("database", {}).get("file_size", 0)
            st_size = backup.get("storage", {}).get("file_size", 0)
            size = db_size + st_size
        else:
            size = backup.get("file_size", 0)
        
        # Get path
        if backup_type == "full":
            path = f"full_backup_{timestamp}.json"
        else:
            path = Path(backup.get("backup_path", "")).name
        
        print(f"{timestamp:<20} {backup_type:<10} {format_size(size):<12} {path}")
    
    return 0


def cmd_stats(args):
    """Show backup statistics."""
    manager = create_backup_manager(
        backup_dir=Path(args.backup_dir) if args.backup_dir else None
    )
    
    stats = manager.get_backup_stats()
    
    print("\nBackup Statistics:\n")
    print(f"  Backup directory: {stats['backup_dir']}")
    print(f"\nBackup counts:")
    print(f"  Database backups: {stats['database_backups']}")
    print(f"  Storage backups:  {stats['storage_backups']}")
    print(f"  Full backups:     {stats['full_backups']}")
    print(f"  Total backups:    {stats['total_backups']}")
    print(f"\nStorage usage:")
    print(f"  Database backups: {stats['database_size_mb']:.2f} MB")
    print(f"  Storage backups:  {stats['storage_size_mb']:.2f} MB")
    print(f"  Total size:       {stats['total_size_mb']:.2f} MB")
    
    if stats['latest_backup']:
        latest = stats['latest_backup']
        print(f"\nLatest backup:")
        print(f"  Timestamp: {latest.get('timestamp')}")
        print(f"  Type: {latest.get('type')}")
        print(f"  Created: {latest.get('created_at')}")
    else:
        print("\nNo backups found")
    
    return 0


def cmd_restore(args):
    """Restore from backup."""
    manager = create_backup_manager(
        backup_dir=Path(args.backup_dir) if args.backup_dir else None
    )
    
    backup_path = Path(args.backup_path)
    
    if not backup_path.exists():
        print(f"Error: Backup file not found: {backup_path}")
        return 1
    
    # Confirm restoration
    if not args.yes:
        print(f"\n⚠️  WARNING: This will restore from backup and overwrite current data!")
        print(f"   Backup: {backup_path}")
        response = input("\nAre you sure you want to continue? (yes/no): ")
        if response.lower() not in ["yes", "y"]:
            print("Restore cancelled")
            return 0
    
    print(f"\nRestoring from {backup_path}...")
    
    # Detect backup type from filename
    if "db_backup" in backup_path.name or backup_path.suffix == ".db":
        success = manager.restore_database(backup_path, verify_checksum=not args.no_verify)
    elif "storage_backup" in backup_path.name:
        success = manager.restore_storage(backup_path, verify_checksum=not args.no_verify)
    else:
        print(f"Error: Cannot determine backup type from filename: {backup_path.name}")
        return 1
    
    if success:
        print("✓ Restore completed successfully")
        return 0
    else:
        print("✗ Restore failed")
        return 1


def cmd_rotate(args):
    """Rotate (remove old) backups."""
    manager = create_backup_manager(
        backup_dir=Path(args.backup_dir) if args.backup_dir else None,
        max_backups=args.max_backups
    )
    
    print(f"Rotating backups (keeping {args.max_backups} most recent)...")
    
    removed = manager.rotate_backups()
    
    if sum(removed.values()) > 0:
        print(f"✓ Removed old backups: {removed}")
    else:
        print("No old backups to remove")
    
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Vertex AR Backup Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create full backup
  python backup_cli.py create --type full
  
  # Create database backup only
  python backup_cli.py create --type database
  
  # List all backups
  python backup_cli.py list
  
  # Show backup statistics
  python backup_cli.py stats
  
  # Restore from backup
  python backup_cli.py restore backups/database/db_backup_20240101_120000.db
  
  # Rotate old backups
  python backup_cli.py rotate --max-backups 7
        """
    )
    
    parser.add_argument(
        "--backup-dir",
        help="Backup directory (default: ./backups)",
        default=None
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new backup")
    create_parser.add_argument(
        "--type",
        choices=["database", "storage", "full"],
        default="full",
        help="Type of backup to create (default: full)"
    )
    create_parser.add_argument(
        "--max-backups",
        type=int,
        default=7,
        help="Maximum number of backups to keep after rotation (default: 7)"
    )
    create_parser.add_argument(
        "--no-rotate",
        action="store_true",
        help="Don't rotate old backups after creating new one"
    )
    
    # List command
    list_parser = subparsers.add_parser("list", help="List available backups")
    list_parser.add_argument(
        "--type",
        choices=["database", "storage", "full", "all"],
        default="all",
        help="Type of backups to list (default: all)"
    )
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show backup statistics")
    
    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument(
        "backup_path",
        help="Path to backup file to restore from"
    )
    restore_parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt"
    )
    restore_parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip checksum verification"
    )
    
    # Rotate command
    rotate_parser = subparsers.add_parser("rotate", help="Rotate (remove old) backups")
    rotate_parser.add_argument(
        "--max-backups",
        type=int,
        default=7,
        help="Maximum number of backups to keep (default: 7)"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    if args.command == "create":
        return cmd_create(args)
    elif args.command == "list":
        return cmd_list(args)
    elif args.command == "stats":
        return cmd_stats(args)
    elif args.command == "restore":
        return cmd_restore(args)
    elif args.command == "rotate":
        return cmd_rotate(args)
    else:
        print(f"Error: Unknown command '{args.command}'")
        return 1


if __name__ == "__main__":
    sys.exit(main())
