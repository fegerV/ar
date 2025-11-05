#!/bin/bash
set -e

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups"
mkdir -p $BACKUP_DIR

echo "Creating backup..."

# Database backup
if [ -f "vertex-ar/app_data.db" ]; then
    cp vertex-ar/app_data.db $BACKUP_DIR/db_backup_$DATE.db
    echo "Database backed up"
fi

# Storage backup
if [ -d "vertex-ar/storage" ]; then
    tar -czf $BACKUP_DIR/storage_backup_$DATE.tar.gz vertex-ar/storage/
    echo "Storage backed up"
fi

# Cleanup old backups (keep last 7 days)
find $BACKUP_DIR/ -name "*.db" -mtime +7 -delete 2>/dev/null || true
find $BACKUP_DIR/ -name "*.tar.gz" -mtime +7 -delete 2>/dev/null || true

echo "Backup completed: $DATE"
