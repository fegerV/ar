# Systemd Service Files for Vertex AR

This directory contains systemd service and timer files for automated backup management.

## Files

- `vertex-ar-backup.service` - Service definition for running backups
- `vertex-ar-backup.timer` - Timer for scheduling automatic backups

## Installation

### 1. Copy service files to systemd directory

```bash
sudo cp systemd/vertex-ar-backup.service /etc/systemd/system/
sudo cp systemd/vertex-ar-backup.timer /etc/systemd/system/
```

### 2. Update paths in service file

Edit `/etc/systemd/system/vertex-ar-backup.service` and update:
- `User` and `Group` to match your installation
- `WorkingDirectory` to your Vertex AR installation path
- `Environment` PATH to include your virtual environment

### 3. Reload systemd

```bash
sudo systemctl daemon-reload
```

### 4. Enable and start the timer

```bash
# Enable timer to start on boot
sudo systemctl enable vertex-ar-backup.timer

# Start the timer now
sudo systemctl start vertex-ar-backup.timer
```

## Checking Status

### Timer status
```bash
sudo systemctl status vertex-ar-backup.timer
```

### List all timers
```bash
systemctl list-timers --all | grep vertex-ar
```

### View next scheduled run
```bash
systemctl status vertex-ar-backup.timer
```

### View backup logs
```bash
journalctl -u vertex-ar-backup.service -n 50
```

### View last backup execution
```bash
journalctl -u vertex-ar-backup.service -n 1 --no-pager
```

## Manual Backup Trigger

You can manually trigger a backup at any time:

```bash
sudo systemctl start vertex-ar-backup.service
```

## Customizing Schedule

Edit the timer file to change the backup schedule:

```bash
sudo nano /etc/systemd/system/vertex-ar-backup.timer
```

Examples:
- Daily at 3 AM: `OnCalendar=*-*-* 03:00:00`
- Every 6 hours: `OnCalendar=00/6:00`
- Weekly on Sunday at 2 AM: `OnCalendar=Sun *-*-* 02:00:00`
- Monthly on 1st at midnight: `OnCalendar=*-*-01 00:00:00`

After editing, reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart vertex-ar-backup.timer
```

## Disabling Automatic Backups

```bash
sudo systemctl stop vertex-ar-backup.timer
sudo systemctl disable vertex-ar-backup.timer
```

## Troubleshooting

### Timer not running
```bash
# Check timer status
sudo systemctl status vertex-ar-backup.timer

# Check if enabled
sudo systemctl is-enabled vertex-ar-backup.timer

# Enable if needed
sudo systemctl enable vertex-ar-backup.timer
sudo systemctl start vertex-ar-backup.timer
```

### Backup fails
```bash
# Check logs
journalctl -u vertex-ar-backup.service -f

# Test backup manually
sudo -u vertex-ar /opt/vertex-ar/.venv/bin/python /opt/vertex-ar/backup_cli.py create full

# Check permissions
ls -la /opt/vertex-ar/backups
```

### Wrong user/permissions
```bash
# Ensure backup directory is writable
sudo chown -R vertex-ar:vertex-ar /opt/vertex-ar/backups
sudo chmod 755 /opt/vertex-ar/backups
```
