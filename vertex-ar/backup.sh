#!/bin/bash
# Automated backup script for Vertex AR
# Can be run manually or via cron

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$SCRIPT_DIR/backups}"
MAX_BACKUPS="${MAX_BACKUPS:-7}"
BACKUP_TYPE="${BACKUP_TYPE:-full}"
LOG_FILE="${LOG_FILE:-$BACKUP_DIR/backup.log}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
    
    if [ "$level" = "ERROR" ]; then
        echo -e "${RED}✗ $message${NC}"
    elif [ "$level" = "SUCCESS" ]; then
        echo -e "${GREEN}✓ $message${NC}"
    elif [ "$level" = "WARNING" ]; then
        echo -e "${YELLOW}⚠ $message${NC}"
    fi
}

# Check if Python is available
check_python() {
    if ! command -v python3 &> /dev/null; then
        log "ERROR" "Python 3 is not installed"
        exit 1
    fi
}

# Activate virtual environment if exists
activate_venv() {
    if [ -d "$SCRIPT_DIR/.venv" ]; then
        log "INFO" "Activating virtual environment"
        source "$SCRIPT_DIR/.venv/bin/activate"
    elif [ -d "$SCRIPT_DIR/../.venv" ]; then
        log "INFO" "Activating virtual environment from parent directory"
        source "$SCRIPT_DIR/../.venv/bin/activate"
    fi
}

# Check disk space
check_disk_space() {
    local required_mb=1000  # Require at least 1GB free space
    local available_mb=$(df -m "$BACKUP_DIR" | awk 'NR==2 {print $4}')
    
    if [ "$available_mb" -lt "$required_mb" ]; then
        log "WARNING" "Low disk space: ${available_mb}MB available (recommended: ${required_mb}MB)"
        return 1
    fi
    
    log "INFO" "Disk space check: ${available_mb}MB available"
    return 0
}

# Create backup
create_backup() {
    log "INFO" "Starting $BACKUP_TYPE backup"
    
    cd "$SCRIPT_DIR"
    
    if python3 backup_cli.py create --type "$BACKUP_TYPE" --max-backups "$MAX_BACKUPS" --backup-dir "$BACKUP_DIR"; then
        log "SUCCESS" "Backup completed successfully"
        return 0
    else
        log "ERROR" "Backup failed"
        return 1
    fi
}

# Send notification (if configured)
send_notification() {
    local status=$1
    local message=$2
    
    # Check if Telegram notification is configured
    if [ -f "$SCRIPT_DIR/notification_handler.py" ] && [ -n "$TELEGRAM_BOT_TOKEN" ]; then
        log "INFO" "Sending notification"
        python3 "$SCRIPT_DIR/notification_handler.py" --message "Backup $status: $message" || true
    fi
}

# Get backup statistics
show_stats() {
    log "INFO" "Backup statistics:"
    python3 backup_cli.py stats --backup-dir "$BACKUP_DIR"
}

# Main function
main() {
    local start_time=$(date +%s)
    
    echo "========================================="
    echo "Vertex AR Backup System"
    echo "========================================="
    echo "Start time: $(date)"
    echo "Backup type: $BACKUP_TYPE"
    echo "Backup directory: $BACKUP_DIR"
    echo "Max backups: $MAX_BACKUPS"
    echo "========================================="
    echo ""
    
    # Create backup directory and log file directory
    mkdir -p "$BACKUP_DIR"
    touch "$LOG_FILE"
    
    # Check prerequisites
    check_python
    activate_venv
    
    # Check disk space
    if ! check_disk_space; then
        log "WARNING" "Continuing despite low disk space..."
    fi
    
    # Create backup
    if create_backup; then
        # Show statistics
        show_stats
        
        # Calculate duration
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        log "SUCCESS" "Backup completed in ${duration}s"
        send_notification "SUCCESS" "Completed in ${duration}s"
        
        echo ""
        echo "========================================="
        echo "Backup completed successfully!"
        echo "Duration: ${duration}s"
        echo "========================================="
        
        exit 0
    else
        # Calculate duration
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        log "ERROR" "Backup failed after ${duration}s"
        send_notification "FAILED" "Failed after ${duration}s"
        
        echo ""
        echo "========================================="
        echo "Backup failed!"
        echo "Duration: ${duration}s"
        echo "========================================="
        
        exit 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --type)
            BACKUP_TYPE="$2"
            shift 2
            ;;
        --max-backups)
            MAX_BACKUPS="$2"
            shift 2
            ;;
        --backup-dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --type TYPE          Backup type: full, database, or storage (default: full)"
            echo "  --max-backups NUM    Maximum number of backups to keep (default: 7)"
            echo "  --backup-dir DIR     Backup directory (default: ./backups)"
            echo "  --help               Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  BACKUP_TYPE         Backup type (default: full)"
            echo "  MAX_BACKUPS         Maximum backups to keep (default: 7)"
            echo "  BACKUP_DIR          Backup directory (default: ./backups)"
            echo "  LOG_FILE            Log file path (default: \$BACKUP_DIR/backup.log)"
            echo "  TELEGRAM_BOT_TOKEN  Telegram bot token for notifications (optional)"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Create full backup"
            echo "  $0 --type database                    # Create database backup only"
            echo "  $0 --max-backups 14                   # Keep 14 most recent backups"
            echo "  BACKUP_TYPE=storage $0                # Create storage backup via env var"
            echo ""
            echo "Cron examples:"
            echo "  # Daily backup at 2 AM"
            echo "  0 2 * * * /path/to/backup.sh --type full >> /var/log/vertex-ar-backup.log 2>&1"
            echo ""
            echo "  # Database backup every 6 hours"
            echo "  0 */6 * * * /path/to/backup.sh --type database"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main function
main
