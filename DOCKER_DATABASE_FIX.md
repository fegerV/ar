# Docker Database Mount and Environment Directory Fix

## Problem Description

The application was experiencing database connection failures when running in Docker containers due to misalignment between:

1. **Database path configuration** (`config.py` line 19): `self.DB_PATH = self.BASE_DIR / "app_data.db"`
   - Inside Docker: `BASE_DIR = /app` → `DB_PATH = /app/app_data.db`

2. **Docker compose mount** (`docker-compose.yml` line 24): `./app_data.db:/app/app_data.db`
   - This attempted to mount a file that didn't exist on the host

3. **Missing `.env` file**: The `.env` file didn't exist, causing environment variables to not be loaded

## Solutions Implemented

### 1. **Created `.env` File** (`/home/engine/project/.env`)
   - Based on `.env.example` with production-ready defaults
   - Contains all necessary environment variables for the application
   - Properly ignored in `.gitignore`

### 2. **Fixed Docker Volume Mounting** (`docker-compose.yml`)
   **Before:**
   ```yaml
   volumes:
     - ./storage:/app/storage
     - ./app_data.db:/app/app_data.db  # Problem: file doesn't exist
   ```

   **After:**
   ```yaml
   volumes:
     - ./storage:/app/storage
     - ./app_data:/app/data  # Solution: mount directory instead of file
   ```

   This approach:
   - Mounts the host directory `./app_data/` to `/app/data/` in the container
   - Allows the database file to be created inside the container
   - Persists the database between container restarts
   - No pre-existing files required on the host

### 3. **Updated Configuration Logic** (`vertex-ar/app/config.py`)
   - Added automatic detection of Docker environment
   - Checks if `/app/data` exists (Docker indicator)
   - Uses `/app/data` for database if in Docker, otherwise uses `BASE_DIR`
   - Ensures database directory is created with proper permissions
   ```python
   db_dir = Path("/app/data") if Path("/app/data").exists() else self.BASE_DIR
   self.DB_DIR = db_dir
   self.DB_DIR.mkdir(parents=True, exist_ok=True)  # Create if needed
   ```

### 4. **Improved Database Initialization** (`vertex-ar/app/database.py`)
   - Added explicit directory creation in `Database.__init__`
   - Ensures parent directories exist before SQLite connection
   - Improved path handling with `Path(path)` conversion
   ```python
   self.path.parent.mkdir(parents=True, exist_ok=True)
   self._connection = sqlite3.connect(str(self.path), check_same_thread=False)
   ```

### 5. **Updated `.gitignore`**
   - Added `app_data/` directory exclusion
   - Added `!app_data/.gitkeep` to keep directory structure
   - Ensures database files are not committed to repository

## Directory Structure

```
/home/engine/project/
├── .env                          # ✓ Created - environment variables
├── app_data/                     # ✓ Created - persistent database storage
│   └── .gitkeep                  # Keeps directory in git
├── docker-compose.yml            # ✓ Updated - volume mounts
├── Dockerfile.app                # No changes needed
└── vertex-ar/
    ├── app/
    │   ├── config.py             # ✓ Updated - DB path detection
    │   ├── database.py           # ✓ Updated - directory creation
    │   └── main.py               # No changes needed
    └── ...
```

## How It Works in Docker

1. **Build Time**: Dockerfile copies application to `/app`
2. **Container Start**:
   - Docker mounts `./app_data:/app/data`
   - `config.py` detects `/app/data` exists and sets `DB_DIR = /app/data`
   - Database path becomes `/app/data/app_data.db`
3. **Runtime**:
   - `Database` class creates parent directories if needed
   - SQLite creates database file in persistent volume
   - Database persists between container restarts

## How It Works Locally (Without Docker)

1. **Development Setup**:
   - `config.py` checks for `/app/data` (doesn't exist locally)
   - Falls back to `BASE_DIR` which is `vertex-ar/` directory
   - Database path becomes `vertex-ar/app_data.db`
2. **Local Development**:
   - Works as before for local testing
   - No need for Docker volumes
   - Database file stored in project directory

## Verification Steps

1. ✅ Python files compile without errors
2. ✅ docker-compose.yml is valid YAML
3. ✅ `.env` file exists with all required variables
4. ✅ `app_data/` directory exists with `.gitkeep`
5. ✅ Database directory creation logic implemented
6. ✅ Environment detection logic implemented

## Benefits

- **No File Mount Issues**: Uses directory mount instead of file mount
- **Automatic Initialization**: Database directory created automatically
- **Development Friendly**: Works both in Docker and locally
- **Persistent Storage**: Database survives container restarts
- **No Pre-existing Files**: No need to create empty database files
- **Clean Git History**: Database files properly ignored
- **Production Ready**: Proper error handling and logging

## Related Files Modified

1. `/home/engine/project/.env` - NEW
2. `/home/engine/project/app_data/.gitkeep` - NEW
3. `/home/engine/project/docker-compose.yml` - MODIFIED
4. `/home/engine/project/.gitignore` - MODIFIED
5. `/home/engine/project/vertex-ar/app/config.py` - MODIFIED
6. `/home/engine/project/vertex-ar/app/database.py` - MODIFIED

## Testing

To verify the fix works:

1. **Local Testing**:
   ```bash
   cd /home/engine/project
   python vertex-ar/main.py
   ```

2. **Docker Testing**:
   ```bash
   docker-compose build
   docker-compose up
   # Check logs for any database errors
   docker-compose down
   ```

3. **Check Persistence**:
   ```bash
   # After running in Docker
   ls -la app_data/app_data.db  # Should exist
   ```

## Notes

- The fix maintains backward compatibility with local development
- Docker volumes are the recommended approach for persistent storage
- No database migration needed - uses existing schema initialization
- Credentials can be changed in `.env` file before deployment
