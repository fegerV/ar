# Company Schema Extensions - Implementation Summary

## Overview
This document describes the extensions to the company schema to support storage backend integration with folder selection and category-based content organization.

**Note**: This document references legacy `content_types` CSV field. The system now uses explicit category management via the projects table (`/api/companies/{id}/categories` endpoints) for better organization and flexibility.

## Database Changes (app/database.py)

### Schema Extensions
1. **New Columns Added to `companies` Table**:
   - `storage_type` (TEXT) - Storage backend: `local_disk`, `minio`, or `yandex_disk`
   - `storage_folder_path` (TEXT, nullable) - Custom folder path (defaults to company slug)
   - `yandex_disk_folder_id` (TEXT, nullable) - Stores the Yandex Disk folder path for order storage
   - `storage_connection_id` (TEXT, nullable) - Reference to storage_connections table
   - `backup_provider` (TEXT, nullable) - Backup provider configuration
   - `backup_remote_path` (TEXT, nullable) - Backup storage path

2. **Safe ALTER TABLE Operations**:
   - All column additions are wrapped in try/except blocks to handle existing schemas gracefully
   - Columns are nullable to maintain backward compatibility

3. **Default Company**:
   - Default company "Vertex AR" is auto-provisioned on first startup with `storage_type = 'local_disk'`
   - Categories managed separately via projects table

### New Database Methods

#### Content Type Serialization/Deserialization
```python
@staticmethod
def serialize_content_types(content_types: List[Dict[str, str]]) -> str
```
- Converts list of content type dicts to CSV format: "slug1:label1,slug2:label2"
- Returns default "portraits:Portraits" if empty list provided
- Example: `[{"slug": "portraits", "label": "Portraits"}]` → `"portraits:Portraits"`

```python
@staticmethod
def deserialize_content_types(content_types_str: Optional[str]) -> List[Dict[str, str]]
```
- Converts CSV string to list of dicts with 'slug' and 'label' keys
- Returns default `[{"slug": "portraits", "label": "Portraits"}]` if None or empty
- Handles malformed strings gracefully by skipping invalid entries
- Example: `"portraits:Portraits,diplomas:Diplomas"` → `[{"slug": "portraits", "label": "Portraits"}, ...]`

#### Company CRUD Operations

**Updated Methods**:
```python
def create_company(
    company_id: str, 
    name: str, 
    storage_type: str = "local_disk",  # Default to canonical local storage type
    storage_connection_id: Optional[str] = None,
    yandex_disk_folder_id: Optional[str] = None,
    content_types: Optional[str] = None  # Deprecated: use categories via /api/companies/{id}/categories
) -> None
```
- Now accepts `yandex_disk_folder_id` and `content_types` parameters
- Both fields are optional for backward compatibility
- **Note**: `content_types` is deprecated in favor of category management via projects table

```python
def update_company(
    company_id: str, 
    name: Optional[str] = None,
    storage_type: Optional[str] = None,
    storage_connection_id: Optional[str] = None,
    yandex_disk_folder_id: Optional[str] = None,
    content_types: Optional[str] = None
) -> bool
```
- **NEW**: General-purpose update method for company fields
- All parameters are optional - only provided fields are updated
- Returns True if successful, False otherwise

```python
def get_companies_with_client_count() -> List[Dict[str, Any]]
```
- **UPDATED**: Now includes `yandex_disk_folder_id` and `content_types` in SELECT query
- Returns full company data with client counts

**Existing Setters** (already present):
- `set_company_yandex_folder(company_id, folder_path)` - Dedicated setter for Yandex folder
- `update_company_content_types(company_id, content_types)` - Dedicated setter for content types
- `update_company_storage(...)` - Updates storage configuration including new fields

All methods return the full company record with new fields included.

## Pydantic Models (app/models.py)

### New Models

**CompanyContentType** (Response model):
```python
class CompanyContentType(BaseModel):
    slug: str
    label: str
```
- Simple response model for individual content types

**CompanyYandexFolderUpdate** (Request model):
```python
class CompanyYandexFolderUpdate(BaseModel):
    yandex_disk_folder_id: str
```
- Request model for updating Yandex Disk folder ID
- Validates that folder ID is not empty

### Existing Models (Enhanced)

All existing company models already include the new fields:

**CompanyCreate**:
- Added: `yandex_disk_folder_id: Optional[str]`
- Added: `content_types: Optional[str]`

**CompanyResponse** & **CompanyListItem**:
- Added: `yandex_disk_folder_id: Optional[str]`
- Added: `content_types: Optional[str]`

**CompanyUpdate**:
- Added: `yandex_disk_folder_id: Optional[str]`
- Added: `content_types: Optional[str]`

**CompanyStorageUpdate**:
- Already includes: `yandex_disk_folder_id: Optional[str]`
- Already includes: `content_types: Optional[str]`

### Pre-existing Related Models
These models were already in place from previous features:

- **ContentTypeItem** - Request model for content type input with slug auto-generation
- **CompanyContentTypesUpdate** - List of ContentTypeItem with validation
- **YandexFolderUpdate** - Request model for setting Yandex Disk folder
- **YandexDiskFolder** - Response model for Yandex Disk folder listing
- **YandexDiskFoldersResponse** - Paginated response for folder listings

## API Endpoints (app/api/companies.py & storage_management.py)

All endpoints have been updated to include the new fields:

### Company Management Endpoints

**POST /api/companies** - Create company
- Accepts `yandex_disk_folder_id` and `content_types` in request body
- Returns full company record including new fields

**GET /api/companies** - List companies
- Returns all companies with new fields included in response

**GET /api/companies/{id}** - Get company
- Returns company record with new fields

**POST /api/companies/{id}/yandex-disk-folder** - Set Yandex Disk folder
- Validates company uses Yandex Disk storage
- Verifies folder exists on Yandex Disk
- Updates `yandex_disk_folder_id` field
- Clears storage adapter cache

**POST /api/companies/{id}/content-types** - Update content types
- Accepts list of content types with labels and optional slugs
- Auto-generates slugs from labels if not provided
- Validates uniqueness of slugs
- Saves as CSV format to database
- Returns normalized list for UI feedback

**PATCH /api/companies/{id}/storage** - Update storage configuration
- Updates all storage-related fields including new ones
- Located in storage_management.py

## Data Format

### Content Types Storage Format
Content types are stored as a CSV string in the database:
```
"slug1:label1,slug2:label2,slug3:label3"
```

Examples:
- Single type: `"portraits:Portraits"`
- Multiple types: `"portraits:Portraits,diplomas:Diplomas AR,certificates:Certificates"`

### Default Content Types
All companies are initialized with at least one content type:
- Default: `"portraits:Portraits"`

### Yandex Disk Folder ID
Stores the full path to the Yandex Disk folder:
- Example: `"/Company Name/Orders"`
- Example: `"/app/company-abc123"`
- NULL if not configured

## Backward Compatibility

All changes maintain full backward compatibility:

1. **Nullable Columns**: Both new columns are nullable with no constraints
2. **Safe Migrations**: ALTER TABLE operations wrapped in try/except blocks
3. **Default Values**: Existing companies automatically get default content_types
4. **Optional Fields**: All Pydantic models use Optional for new fields
5. **Graceful Fallbacks**: Database methods handle None/NULL values gracefully
6. **Legacy Data**: Companies without new fields continue to work normally

## Testing

Comprehensive test coverage includes:

1. **Serialize/Deserialize**: Content type format conversion
2. **Default Company**: Proper initialization with default values
3. **CRUD Operations**: Create, read, update operations with new fields
4. **Edge Cases**: Empty strings, None values, malformed data
5. **API Integration**: All endpoints return new fields correctly
6. **Backward Compatibility**: Legacy data loads without errors

All tests pass successfully.

## Usage Examples

### Creating a Company with Content Types
```python
db.create_company(
    company_id="company-123",
    name="Acme Corp",
    storage_type="yandex_disk",
    storage_connection_id="conn-456",
    yandex_disk_folder_id="/Acme Corp/Orders",
    content_types="portraits:Portraits,diplomas:Diplomas AR,certificates:Certificates"
)
```

### Updating Content Types
```python
# Using dedicated setter
db.update_company_content_types(
    "company-123",
    "videos:Videos,photos:Photos"
)

# Or using general update method
db.update_company(
    "company-123",
    content_types="videos:Videos,photos:Photos"
)
```

### Deserializing Content Types for Display
```python
company = db.get_company("company-123")
content_types_list = db.deserialize_content_types(company["content_types"])
# Returns: [{"slug": "videos", "label": "Videos"}, {"slug": "photos", "label": "Photos"}]
```

### Serializing Content Types for Storage
```python
content_types = [
    {"slug": "portraits", "label": "Portrait Photos"},
    {"slug": "videos", "label": "AR Videos"}
]
content_types_str = db.serialize_content_types(content_types)
# Returns: "portraits:Portrait Photos,videos:AR Videos"

db.update_company_content_types("company-123", content_types_str)
```

## Files Modified

1. **vertex-ar/app/database.py**:
   - Added columns to companies table (lines 430-448)
   - Updated `ensure_default_company` logic (lines 155-174)
   - Added `update_company()` method (lines 1552-1610)
   - Updated `get_companies_with_client_count()` query (lines 1625-1575)
   - Added `serialize_content_types()` static method (lines 1653-1678)
   - Added `deserialize_content_types()` static method (lines 1680-1708)

2. **vertex-ar/app/models.py**:
   - Added `CompanyYandexFolderUpdate` model (lines 221-230)
   - Added `CompanyContentType` model (lines 233-236)
   - All existing company models already include new fields

3. **vertex-ar/app/api/companies.py**:
   - All endpoints already using new fields (no changes needed)

4. **vertex-ar/app/api/storage_management.py**:
   - PATCH endpoint already using new fields (no changes needed)

## Notes

- The content_types field uses CSV format rather than JSON for simplicity and compatibility
- Helper methods are static and can be called without a database instance
- All database operations are thread-safe (using existing _lock mechanism)
- Storage adapter cache is cleared when folder selection changes
- Folder existence is verified via Yandex Disk API before persisting selection
