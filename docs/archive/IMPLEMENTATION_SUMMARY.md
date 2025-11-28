# Projects & Folders Backend Implementation Summary

## Overview

Successfully implemented hierarchical organization for AR content in Vertex AR with **Company → Project → Folder → Portrait → Video** structure.

## What Was Implemented

### 1. Database Schema Changes

#### New Tables
- **`projects`**: Projects within companies
  - Fields: `id`, `company_id`, `name`, `description`, `created_at`
  - Constraint: `UNIQUE(company_id, name)`
  - Foreign key: `company_id` references `companies(id)` with CASCADE DELETE

- **`folders`**: Folders/categories within projects
  - Fields: `id`, `project_id`, `name`, `description`, `created_at`
  - Constraint: `UNIQUE(project_id, name)`
  - Foreign key: `project_id` references `projects(id)` with CASCADE DELETE

#### Updated Tables
- **`portraits`**: Added optional `folder_id` column (nullable for backward compatibility)
  - Index created on `folder_id` for performance

### 2. Pydantic Models (app/models.py)

Added complete model sets for both entities:
- `ProjectCreate`, `ProjectUpdate`, `ProjectResponse`, `ProjectListItem`, `PaginatedProjectsResponse`
- `FolderCreate`, `FolderUpdate`, `FolderResponse`, `FolderListItem`, `PaginatedFoldersResponse`
- Updated `PortraitResponse` to include `folder_id` field

### 3. Database Methods (app/database.py)

#### Projects
- `create_project(project_id, company_id, name, description)` - Create new project
- `get_project(project_id)` - Get project by ID
- `get_project_by_name(company_id, name)` - Find project by name in company
- `list_projects(company_id, limit, offset)` - List with pagination
- `count_projects(company_id)` - Count projects
- `update_project(project_id, name, description)` - Update project
- `delete_project(project_id)` - Delete with cascade
- `get_project_folder_count(project_id)` - Get folder count
- `get_project_portrait_count(project_id)` - Get portrait count across folders

#### Folders
- `create_folder(folder_id, project_id, name, description)` - Create new folder
- `get_folder(folder_id)` - Get folder by ID
- `get_folder_by_name(project_id, name)` - Find folder by name in project
- `list_folders(project_id, limit, offset)` - List with pagination
- `count_folders(project_id)` - Count folders
- `update_folder(folder_id, name, description)` - Update folder
- `delete_folder(folder_id)` - Delete folder
- `get_folder_portrait_count(folder_id)` - Get portrait count in folder

#### Portraits (Updated)
- `create_portrait(...)` - Now accepts optional `folder_id` parameter
- `list_portraits(client_id, folder_id)` - Now supports filtering by folder

### 4. API Endpoints

#### Projects API (`app/api/projects.py`)
- `POST /api/projects` - Create project (requires `name`, `company_id`, optional `description`)
- `GET /api/projects` - List projects with pagination (optional `company_id` filter)
- `GET /api/projects/{project_id}` - Get specific project
- `PUT /api/projects/{project_id}` - Update project
- `DELETE /api/projects/{project_id}` - Delete project (cascades to folders)

#### Folders API (`app/api/folders.py`)
- `POST /api/folders` - Create folder (requires `name`, `project_id`, optional `description`)
- `GET /api/folders` - List folders with pagination (optional `project_id` filter)
- `GET /api/folders/{folder_id}` - Get specific folder
- `PUT /api/folders/{folder_id}` - Update folder
- `DELETE /api/folders/{folder_id}` - Delete folder (prevents if has portraits)

#### Portraits API (Updated)
- `POST /api/portraits/` - Now accepts optional `folder_id` form parameter
- `GET /api/portraits/` - Now supports `folder_id` query parameter for filtering

### 5. Migration Script

**`migrate_to_projects_folders.py`**
- Creates default project "Default Project" in default company
- Creates three default folders:
  - "Портреты" (Portraits)
  - "Дипломы AR" (AR Diplomas)
  - "Сертификаты" (Certificates)
- Provides helper functions for assigning portraits to folders
- Can be run multiple times safely (idempotent)

### 6. Testing

**`test_projects_folders_api.py`**
- Tests all CRUD operations for projects
- Tests all CRUD operations for folders
- Tests portrait filtering by folder
- Tests hierarchy navigation
- Verifies all relationships and counts

### 7. Documentation

**`PROJECTS_FOLDERS_FEATURE.md`**
- Complete feature documentation
- Database schema details
- API endpoint specifications
- Usage examples and code samples
- UI integration guidelines
- Migration notes

## Files Modified

1. `vertex-ar/app/models.py` - Added Project and Folder models
2. `vertex-ar/app/database.py` - Added tables, indexes, and CRUD methods
3. `vertex-ar/app/main.py` - Registered new routers, exposed database globally
4. `vertex-ar/app/api/portraits.py` - Added folder_id support

## Files Created

1. `vertex-ar/app/api/projects.py` - Projects API endpoints
2. `vertex-ar/app/api/folders.py` - Folders API endpoints
3. `vertex-ar/migrate_to_projects_folders.py` - Migration script
4. `vertex-ar/test_projects_folders_api.py` - Test script
5. `vertex-ar/PROJECTS_FOLDERS_FEATURE.md` - Feature documentation

## Backward Compatibility

✅ **Fully backward compatible:**
- Existing portraits continue to work without folder_id
- Client-based structure still functional
- All existing API endpoints unchanged
- No breaking changes to database schema
- folder_id is optional everywhere

## Testing Results

✅ All tests passed:
- ✓ Project CRUD operations
- ✓ Folder CRUD operations
- ✓ Portrait filtering by folder
- ✓ Hierarchy navigation
- ✓ Default structure creation via migration

## Usage Example

```python
# 1. Create a project
project_data = {
    "name": "Graduation 2024",
    "description": "AR diplomas for graduation",
    "company_id": "vertex-ar-default"
}
response = requests.post(
    "http://localhost:8000/api/projects",
    json=project_data,
    headers={"Authorization": f"Bearer {token}"}
)
project = response.json()

# 2. Create a folder
folder_data = {
    "name": "Дипломы AR",
    "description": "AR-enhanced diplomas",
    "project_id": project["id"]
}
response = requests.post(
    "http://localhost:8000/api/folders",
    json=folder_data,
    headers={"Authorization": f"Bearer {token}"}
)
folder = response.json()

# 3. Create portrait in folder
with open("diploma.jpg", "rb") as f:
    files = {"image": f}
    data = {
        "client_id": client_id,
        "folder_id": folder["id"]  # NEW!
    }
    response = requests.post(
        "http://localhost:8000/api/portraits/",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {token}"}
    )
```

## Next Steps for UI Integration

1. **Company Selection**: First-level dropdown
2. **Project Management**: 
   - List/create/edit projects within company
   - Show folder and portrait counts
3. **Folder Management**:
   - List/create/edit folders within project
   - Show portrait counts
4. **File Upload**:
   - Require: Company → Project → Folder selection
   - Allow creating new project/folder inline
   - Maintain client association

## Running the Migration

```bash
cd vertex-ar
python migrate_to_projects_folders.py
```

## Running the Tests

```bash
cd vertex-ar
python test_projects_folders_api.py
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Look for "projects" and "folders" tags for the new endpoints.

## Database Changes Applied

The following changes are automatically applied on application startup:
1. Create `projects` table (if not exists)
2. Create `folders` table (if not exists)
3. Add `folder_id` column to `portraits` (if not exists)
4. Create indexes for performance

No manual SQL execution required!

## Feature Status

🟢 **COMPLETE AND TESTED**

All components implemented, tested, and documented:
- ✅ Database schema
- ✅ Pydantic models
- ✅ Database methods
- ✅ API endpoints
- ✅ Migration script
- ✅ Test script
- ✅ Documentation
- ✅ Backward compatibility verified
- ✅ All tests passing

## Support

For questions or issues, refer to:
- `vertex-ar/PROJECTS_FOLDERS_FEATURE.md` - Complete documentation
- `vertex-ar/test_projects_folders_api.py` - Usage examples
- Swagger UI at `/docs` - Interactive API testing
