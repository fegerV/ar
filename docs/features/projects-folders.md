# Projects and Folders Feature

## Overview

This feature adds hierarchical organization for AR content in Vertex AR through a **Company → Project → Folder → Portrait → Video** structure, replacing the flat **Company → Client → Portrait → Video** structure.

## Automatic Folder Provisioning

When a new company is created through the API, Vertex AR automatically provisions a default folder structure for local storage companies. This includes creating directories for the standard content types:

- `portraits`
- `certificates`
- `diplomas`

Each category gets its own directory with the standard subdirectories:

- `Image`
- `QR`
- `nft_markers`
- `nft_cache`

This ensures that newly created companies have the required folder structure immediately available without manual intervention.

## Architecture

### Database Schema

#### Projects Table
```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE,
    UNIQUE(company_id, name)
)
```

#### Folders Table
```sql
CREATE TABLE folders (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, name)
)
```

#### Portraits Table Updates
- Added `folder_id TEXT` column (nullable for backward compatibility)
- Created index on `folder_id` for performance

### Hierarchy Structure

```
Company
  ├── Project 1
  │   ├── Folder 1 (e.g., "Дипломы AR")
  │   │   ├── Portrait 1
  │   │   │   └── Video 1, Video 2, ...
  │   │   └── Portrait 2
  │   │       └── Video 1, Video 2, ...
  │   └── Folder 2 (e.g., "Портреты")
  │       └── Portrait 3
  │           └── Video 1
  └── Project 2
      └── Folder 1
          └── Portrait 4
```

## API Endpoints

### Projects API (`/api/projects`)

#### Create Project
```http
POST /api/projects
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "AR Diplomas 2024",
  "description": "AR diplomas project for graduation ceremony",
  "company_id": "company-uuid"
}
```

#### List Projects
```http
GET /api/projects?company_id=<company-uuid>&page=1&page_size=20
Authorization: Bearer <token>
```

Response includes:
- `folder_count`: Number of folders in the project
- `portrait_count`: Total number of portraits across all folders

#### Get Project
```http
GET /api/projects/{project_id}
Authorization: Bearer <token>
```

#### Update Project
```http
PUT /api/projects/{project_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Updated Project Name",
  "description": "Updated description"
}
```

#### Delete Project
```http
DELETE /api/projects/{project_id}
Authorization: Bearer <token>
```

### Folders API (`/api/folders`)

#### Create Folder
```http
POST /api/folders
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Дипломы AR",
  "description": "AR-enhanced graduation diplomas",
  "project_id": "project-uuid"
}
```

#### List Folders
```http
GET /api/folders?project_id=<project-uuid>&company_id=<company-uuid>&page=1&page_size=20
Authorization: Bearer <token>
```

Query Parameters:
- `project_id`: Filter folders by project ID
- `company_id`: Filter folders by company ID (returns folders from all projects of the company)

Response includes:
- `portrait_count`: Number of portraits in the folder

**Note**: When both `project_id` and `company_id` are provided, `project_id` takes precedence.

#### Get Folder
```http
GET /api/folders/{folder_id}
Authorization: Bearer <token>
```

#### Update Folder
```http
PUT /api/folders/{folder_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Updated Folder Name",
  "description": "Updated description"
}
```

#### Delete Folder
```http
DELETE /api/folders/{folder_id}
Authorization: Bearer <token>
```

**Note**: Folders with portraits cannot be deleted. Remove or reassign portraits first.

### Portraits API Updates

The existing portraits API has been enhanced to support folders:

#### Create Portrait with Folder
```http
POST /api/portraits/
Authorization: Bearer <token>
Content-Type: multipart/form-data

client_id: <client-uuid>
folder_id: <folder-uuid>  # Optional
image: <file>
```

#### List Portraits with Folder Filter
```http
GET /api/portraits/?folder_id=<folder-uuid>
Authorization: Bearer <token>
```

## Pydantic Models

### ProjectCreate
```python
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    company_id: str
```

### ProjectResponse
```python
class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    company_id: str
    created_at: str
```

### FolderCreate
```python
class FolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    project_id: str
```

### FolderResponse
```python
class FolderResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    project_id: str
    created_at: str
```

### PortraitResponse (Updated)
```python
class PortraitResponse(BaseModel):
    id: str
    client_id: str
    folder_id: Optional[str] = None  # New field
    permanent_link: str
    qr_code_base64: Optional[str]
    image_path: str
    image_url: Optional[str] = None
    preview_url: Optional[str] = None
    view_count: int
    created_at: str
```

## Database Methods

### Project Methods
- `create_project(project_id, company_id, name, description=None)`
- `get_project(project_id)`
- `get_project_by_name(company_id, name)`
- `list_projects(company_id=None, limit=None, offset=0)`
- `count_projects(company_id=None)`
- `update_project(project_id, name=None, description=None)`
- `delete_project(project_id)`
- `get_project_folder_count(project_id)`
- `get_project_portrait_count(project_id)`

### Folder Methods
- `create_folder(folder_id, project_id, name, description=None)`
- `get_folder(folder_id)`
- `get_folder_by_name(project_id, name)`
- `list_folders(project_id=None, company_id=None, limit=None, offset=0)`
- `count_folders(project_id=None, company_id=None)`
- `update_folder(folder_id, name=None, description=None)`
- `delete_folder(folder_id)`
- `get_folder_portrait_count(folder_id)`

### Updated Portrait Methods
- `create_portrait(..., folder_id=None)` - Now accepts optional folder_id
- `list_portraits(client_id=None, folder_id=None)` - Now supports folder filtering

## Backward Compatibility

The implementation maintains full backward compatibility:

1. **Client-based structure still works**: Portraits can still be created with just `client_id` without `folder_id`
2. **Optional folder_id**: The `folder_id` column in portraits table is nullable
3. **Existing API continues to work**: All existing client and portrait endpoints function as before
4. **Migration-free**: Existing data remains intact and functional

## Usage Examples

### Creating a Complete Hierarchy

```python
import requests

BASE_URL = "http://localhost:8000"
TOKEN = "your-jwt-token"
headers = {"Authorization": f"Bearer {TOKEN}"}

# 1. Create a company (if not exists)
company_data = {"name": "Vertex AR"}
company = requests.post(f"{BASE_URL}/api/companies", json=company_data, headers=headers).json()

# 2. Create a project
project_data = {
    "name": "Graduation 2024",
    "description": "AR diplomas for graduation ceremony",
    "company_id": company["id"]
}
project = requests.post(f"{BASE_URL}/api/projects", json=project_data, headers=headers).json()

# 3. Create folders
diploma_folder = requests.post(
    f"{BASE_URL}/api/folders",
    json={
        "name": "Дипломы AR",
        "description": "AR-enhanced diplomas",
        "project_id": project["id"]
    },
    headers=headers
).json()

portraits_folder = requests.post(
    f"{BASE_URL}/api/folders",
    json={
        "name": "Портреты выпускников",
        "description": "Graduate portraits",
        "project_id": project["id"]
    },
    headers=headers
).json()

# 4. Create client
client_data = {
    "name": "Ivan Petrov",
    "phone": "+79001234567",
    "company_id": company["id"]
}
client = requests.post(f"{BASE_URL}/api/clients", json=client_data, headers=headers).json()

# 5. Upload portrait to folder
with open("diploma.jpg", "rb") as f:
    files = {"image": f}
    data = {
        "client_id": client["id"],
        "folder_id": diploma_folder["id"]
    }
    portrait = requests.post(
        f"{BASE_URL}/api/portraits/",
        files=files,
        data=data,
        headers=headers
    ).json()

# 6. Upload video to portrait
with open("animation.mp4", "rb") as f:
    files = {"video": f}
    data = {"portrait_id": portrait["id"]}
    video = requests.post(
        f"{BASE_URL}/api/videos/",
        files=files,
        data=data,
        headers=headers
    ).json()
```

### Filtering and Navigation

```python
# Get all projects for a company
projects = requests.get(
    f"{BASE_URL}/api/projects?company_id={company_id}",
    headers=headers
).json()

# Get all folders in a project
folders = requests.get(
    f"{BASE_URL}/api/folders?project_id={project_id}",
    headers=headers
).json()

# Get all portraits in a folder
portraits = requests.get(
    f"{BASE_URL}/api/portraits/?folder_id={folder_id}",
    headers=headers
).json()
```

## Implementation Files

### Modified Files
- `app/models.py` - Added Project and Folder Pydantic models
- `app/database.py` - Added tables, indexes, and CRUD methods
- `app/main.py` - Registered new routers
- `app/api/portraits.py` - Added folder_id support

### New Files
- `app/api/projects.py` - Projects API endpoints
- `app/api/folders.py` - Folders API endpoints

## UI Integration Guidelines

When integrating this feature into the UI:

1. **Company Selection**: First level - select company
2. **Project Management**:
   - List/create/edit projects within selected company
   - Show folder count and portrait count for each project
3. **Folder Management**:
   - List/create/edit folders within selected project
   - Show portrait count for each folder
4. **File Upload**:
   - Require selection of: Company → Project → Folder
   - Allow creating new project/folder on the fly
   - Maintain client association for backward compatibility

### Recommended UI Flow

```
┌─────────────────────────────────────────┐
│  Select Company: [Vertex AR ▼]          │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Select/Create Project:                 │
│  ○ Graduation 2024 (3 folders, 45 files)│
│  ○ Corporate Events (2 folders, 12 files)│
│  + Create New Project                    │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Select/Create Folder:                  │
│  ○ Дипломы AR (45 portraits)            │
│  ○ Портреты выпускников (0 portraits)   │
│  + Create New Folder                     │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Upload Files                            │
│  [Select Image] [Select Video]          │
│  Client: [Name] [Phone]                 │
│  [Upload]                               │
└─────────────────────────────────────────┘
```

## Testing

Run the application and test the new endpoints:

```bash
# Start the server
cd vertex-ar
uvicorn app.main:app --reload

# Test project creation
curl -X POST http://localhost:8000/api/projects \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Project", "company_id": "vertex-ar-default"}'

# Test folder creation
curl -X POST http://localhost:8000/api/folders \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Folder", "project_id": "PROJECT_ID"}'

# List projects
curl http://localhost:8000/api/projects \
  -H "Authorization: Bearer YOUR_TOKEN"

# List folders
curl http://localhost:8000/api/folders?project_id=PROJECT_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Future Enhancements

Potential future improvements:

1. **Bulk Operations**: Move multiple portraits between folders
2. **Project Templates**: Pre-configured project/folder structures
3. **Access Control**: Per-project/folder permissions
4. **Statistics**: Analytics per project/folder
5. **Search**: Full-text search across hierarchy
6. **Tags**: Additional categorization beyond folders
7. **Nested Folders**: Support for folder hierarchies (folders within folders)
8. **Project Archiving**: Archive completed projects

## Migration Notes

No database migration is required for existing deployments:

1. Database schema is automatically updated on startup
2. Existing portraits continue to work without folder_id
3. New portraits can optionally use folders
4. Gradual migration is possible - move portraits to folders as needed

To migrate existing portraits to the new structure:

```python
# Example migration script
portraits = database.list_portraits()
for portrait in portraits:
    # Create project/folder structure based on client or company
    # Update portrait with folder_id
    database._execute(
        "UPDATE portraits SET folder_id = ? WHERE id = ?",
        (folder_id, portrait["id"])
    )
```
