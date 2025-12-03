# Storage Management API

<cite>
**Referenced Files in This Document**   
- [storage_management.py](file://vertex-ar/app/api/storage_management.py)
- [models.py](file://vertex-ar/app/models.py)
- [storage_minio.py](file://vertex-ar/app/storage_minio.py)
- [storage_yandex.py](file://vertex-ar/app/storage_yandex.py)
- [encryption.py](file://vertex-ar/app/encryption.py)
- [database.py](file://vertex-ar/app/database.py)
- [storage_config.json](file://vertex-ar/config/storage_config.json)
- [companies.py](file://vertex-ar/app/api/companies.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [API Endpoints](#api-endpoints)
3. [Request/Response Schemas](#requestresponse-schemas)
4. [Storage Connection Testing](#storage-connection-testing)
5. [Company Storage Configuration](#company-storage-configuration)
6. [Security Considerations](#security-considerations)
7. [Examples](#examples)
8. [Error Handling](#error-handling)

## Introduction

The Storage Management API provides comprehensive functionality for managing storage connections in the Vertex AR application. This API enables administrators to create, read, update, delete, and test storage connections for various backend storage systems, including MinIO and Yandex Disk.

The system is designed with security as a primary concern, implementing encryption for sensitive credentials at rest and masking them in API responses. Storage connections serve as reusable configurations that can be assigned to companies, enabling centralized management of storage infrastructure.

Key features include:
- Secure storage connection management with encrypted credentials
- Comprehensive testing mechanism for validating connectivity
- Integration with company configurations
- Support for multiple storage backends
- Audit logging for all storage connection operations

This documentation covers all API endpoints, request/response schemas, testing mechanisms, and security considerations for the storage management system.

**Section sources**
- [storage_management.py](file://vertex-ar/app/api/storage_management.py#L1-L667)

## API Endpoints

The Storage Management API provides RESTful endpoints for managing storage connections. All endpoints require admin authentication via session cookie.

### List Storage Connections
```mermaid
flowchart TD
A[Client] --> B[GET /storages]
B --> C{Authentication}
C --> |Valid| D[Query Database]
D --> E[Mask Sensitive Fields]
E --> F[Return Connections]
C --> |Invalid| G[Return 401]
```

Retrieves a list of all storage connections with optional filtering.

**URL**: `GET /storages`

**Parameters**:
- `active_only` (boolean, default: true): Filter to return only active connections
- `tested_only` (boolean, default: false): Filter to return only tested connections

**Section sources**
- [storage_management.py](file://vertex-ar/app/api/storage_management.py#L294-L325)

### Create Storage Connection
```mermaid
flowchart TD
A[Client] --> B[POST /storages]
B --> C{Authentication}
C --> |Valid| D[Validate Name]
D --> E{Name Exists?}
E --> |Yes| F[Return 409]
E --> |No| G[Encrypt Credentials]
G --> H[Store in Database]
H --> I[Return Created Connection]
C --> |Invalid| J[Return 401]
```

Creates a new storage connection with encrypted sensitive fields.

**URL**: `POST /storages`

**Section sources**
- [storage_management.py](file://vertex-ar/app/api/storage_management.py#L328-L392)

### Get Storage Connection
```mermaid
flowchart TD
    A["Client"] --> B["GET /storages/{connection_id}"]
    B --> C{"Authentication"}
    C --> |"Valid"| D["Query Database"]
    D --> E{"Connection Found?"}
    E --> |"No"| F["Return 404"]
    E --> |"Yes"| G["Mask Sensitive Fields"]
    G --> H["Return Connection"]
    C --> |"Invalid"| I["Return 401"]
```

Retrieves a specific storage connection by ID with masked sensitive fields.

**URL**: `GET /storages/{connection_id}`

**Path Parameters**:
- `connection_id` (string): Unique identifier of the storage connection

**Section sources**
- [storage_management.py](file://vertex-ar/app/api/storage_management.py#L395-L421)

### Update Storage Connection
```mermaid
flowchart TD
    A["Client"] --> B["PUT /storages/{connection_id}"]
    B --> C{"Authentication"}
    C --> |Valid| D{"Connection Exists?"}
    D --> |No| E["Return 404"]
    D --> |Yes| F["Validate Name Conflict"]
    F --> G{"Name Changed?"}
    G --> |Yes| H{"Name Exists?"}
    H --> |Yes| I["Return 409"]
    H --> |No| J["Encrypt New Config"]
    G --> |No| J
    J --> K["Update Database"]
    K --> L{"Config Changed?"}
    L --> |Yes| M["Reset Test Status"]
    L --> |No| N["Keep Test Status"]
    M --> O["Return Updated Connection"]
    N --> O
    C --> |Invalid| P["Return 401"]
```

Updates an existing storage connection. If the configuration is updated, the test status is reset requiring re-validation.

**URL**: `PUT /storages/{connection_id}`

**Path Parameters**:
- `connection_id` (string): Unique identifier of the storage connection

**Section sources**
- [storage_management.py](file://vertex-ar/app/api/storage_management.py#L424-L495)

### Delete Storage Connection
```mermaid
flowchart TD
    A["Client"] --> B["DELETE /storages/{connection_id}"]
    B --> C{"Authentication"}
    C --> |Valid| D{"Connection Exists?"}
    D --> |No| E["Return 404"]
    D --> |Yes| F{"In Use by Companies?"}
    F --> |Yes| G["Return 400"]
    F --> |No| H["Delete from Database"]
    H --> I["Return Success"]
    C --> |Invalid| J["Return 401"]
```

Deletes a storage connection. The connection cannot be deleted if it is currently assigned to any company.

**URL**: `DELETE /storages/{connection_id}`

**Path Parameters**:
- `connection_id` (string): Unique identifier of the storage connection

**Section sources**
- [storage_management.py](file://vertex-ar/app/api/storage_management.py#L498-L533)

### Test Storage Connection
```mermaid
flowchart TD
A[Client] --> B[POST /storages/test]
B --> C{Authentication}
C --> |Valid| D[Get Connection]
D --> E{Connection Found?}
E --> |No| F[Return 404]
E --> |Yes| G[Decrypt Credentials]
G --> H[Test Connectivity]
H --> I{Success?}
I --> |Yes| J[Update Test Result: Success]
I --> |No| K[Update Test Result: Failure]
J --> L[Return Test Response]
K --> L
C --> |Invalid| M[Return 401]
```

Tests connectivity to a storage backend using the stored credentials. This endpoint decrypts the stored credentials to perform the test.

**URL**: `POST /storages/test`

**Request Body**: StorageTestRequest object with connection_id

**Section sources**
- [storage_management.py](file://vertex-ar/app/api/storage_management.py#L536-L569)

### Get Available Storage Options
Retrieves a list of available storage options for company configuration, including both local storage and configured remote connections.

**URL**: `GET /storage-options`

**Section sources**
- [storage_management.py](file://vertex-ar/app/api/storage_management.py#L572-L597)

## Request/Response Schemas

### StorageConnectionCreate
Request schema for creating a new storage connection.

```json
{
  "name": "string",
  "type": "minio|yandex_disk",
  "config": {
    "endpoint": "string",
    "access_key": "string",
    "secret_key": "string",
    "bucket": "string",
    "oauth_token": "string",
    "client_secret": "string",
    "client_id": "string",
    "redirect_uri": "string"
  }
}
```

**Validation Rules**:
- `name`: Required, 1-255 characters, must be unique
- `type`: Required, must be "minio" or "yandex_disk"
- `config`: Required, structure depends on type:
  - MinIO: Requires endpoint, access_key, secret_key, bucket
  - Yandex Disk: Requires client_id, client_secret, redirect_uri, oauth_token

**Section sources**
- [models.py](file://vertex-ar/app/models.py#L316-L367)

### StorageConnectionUpdate
Request schema for updating an existing storage connection.

```json
{
  "name": "string",
  "config": {
    "endpoint": "string",
    "access_key": "string",
    "secret_key": "string",
    "bucket": "string",
    "oauth_token": "string",
    "client_secret": "string"
  },
  "is_active": true
}
```

**Validation Rules**:
- All fields are optional
- If `config` is provided, validates non-empty values for relevant fields
- If `name` is provided, validates uniqueness

**Section sources**
- [models.py](file://vertex-ar/app/models.py#L369-L403)

### StorageConnectionResponse
Response schema for storage connections with masked sensitive fields.

```json
{
  "id": "string",
  "name": "string",
  "type": "minio|yandex_disk",
  "config": {
    "endpoint": "string",
    "access_key": "***",
    "secret_key": "***",
    "bucket": "string",
    "oauth_token": "***",
    "client_secret": "***"
  },
  "is_active": true,
  "is_tested": true,
  "test_result": "string",
  "created_at": "string",
  "updated_at": "string"
}
```

**Field Descriptions**:
- `id`: Unique identifier for the connection
- `name`: User-friendly name for the connection
- `type`: Storage backend type
- `config`: Configuration with sensitive fields masked
- `is_active`: Whether the connection is enabled
- `is_tested`: Whether the connection has passed connectivity test
- `test_result`: Message from last test attempt
- `created_at`: Timestamp of creation
- `updated_at`: Timestamp of last update

**Section sources**
- [models.py](file://vertex-ar/app/models.py#L406-L415)

### StorageTestRequest
Request schema for testing a storage connection.

```json
{
  "connection_id": "string"
}
```

**Section sources**
- [models.py](file://vertex-ar/app/models.py#L418-L420)

### StorageTestResponse
Response schema for storage connection test results.

```json
{
  "success": true,
  "message": "string",
  "details": {}
}
```

**Section sources**
- [models.py](file://vertex-ar/app/models.py#L422-L425)

## Storage Connection Testing

The storage connection testing mechanism validates connectivity to storage backends using the stored credentials. The testing process follows a secure workflow that temporarily decrypts credentials for testing purposes while ensuring they remain protected in storage and responses.

### Testing Workflow
```mermaid
sequenceDiagram
participant Client
participant API
participant Database
participant StorageBackend
Client->>API : POST /storages/test
API->>Database : Get connection by ID
Database-->>API : Return connection data
API->>API : Decrypt sensitive fields
API->>StorageBackend : Test connectivity
alt Success
StorageBackend-->>API : Connection successful
API->>Database : Update test result (success)
Database-->>API : Acknowledge update
API-->>Client : Return success response
else Failure
StorageBackend-->>API : Connection failed
API->>Database : Update test result (failure)
Database-->>API : Acknowledge update
API-->>Client : Return failure response
end
```

### Backend-Specific Testing

**MinIO Testing**:
- Validates endpoint connectivity
- Authenticates with access_key and secret_key
- Checks bucket existence or creation capability
- Returns connection details on success

**Yandex Disk Testing**:
- Validates OAuth token validity
- Authenticates with Yandex Disk API
- Retrieves storage information
- Returns storage details on success

When a storage connection's configuration is updated, the test status is automatically reset to false, requiring administrators to retest the connection before it can be used by companies.

**Section sources**
- [storage_management.py](file://vertex-ar/app/api/storage_management.py#L149-L291)

## Company Storage Configuration

Storage connections are linked to company configurations, allowing companies to use predefined storage backends. This relationship ensures that only validated and tested connections can be assigned to companies.

### Configuration Workflow
```mermaid
flowchart TD
A[Create Storage Connection] --> B[Test Connection]
B --> C{Test Successful?}
C --> |Yes| D[Update Company Storage]
C --> |No| E[Fix Configuration]
E --> B
D --> F[Company Uses Storage]
```

### Validation Rules
When assigning a storage connection to a company, the following validation rules apply:

1. **Active Status**: The storage connection must be active (is_active = true)
2. **Tested Status**: The storage connection must have passed connectivity test (is_tested = true)
3. **Required Fields**: 
   - MinIO connections require storage_connection_id
   - Yandex Disk connections require both storage_connection_id and yandex_disk_folder_id

These validations occur during both company creation and storage configuration updates.

### Update Endpoint
The company storage configuration is updated through a dedicated endpoint that enforces these validation rules:

**URL**: `PATCH /companies/{company_id}/storage`

**Request Body**: CompanyStorageUpdate object with storage_type, storage_connection_id, and yandex_disk_folder_id

**Section sources**
- [companies.py](file://vertex-ar/app/api/companies.py#L104-L116)
- [storage_management.py](file://vertex-ar/app/api/storage_management.py#L600-L666)

## Security Considerations

The storage management system implements multiple security layers to protect sensitive credentials and ensure secure operation.

### Credential Encryption
Sensitive credentials are encrypted at rest using AES-256 encryption with PBKDF2 key derivation:

```mermaid
flowchart TD
A[Raw Credentials] --> B[PBKDF2 Key Derivation]
B --> C[AES-256 Encryption]
C --> D[Base64 Encoding]
D --> E[Stored in Database]
```

**Encryption Details**:
- Algorithm: AES-256 in CBC mode via Fernet
- Key derivation: PBKDF2HMAC with SHA256
- Iterations: 100,000
- Salt: Static salt for consistency
- Key source: ENCRYPTION_SECRET environment variable or default secret

**Fields Encrypted**:
- MinIO: access_key, secret_key
- Yandex Disk: oauth_token, client_secret

**Section sources**
- [encryption.py](file://vertex-ar/app/encryption.py#L16-L83)

### Credential Masking
In API responses, sensitive fields are masked to prevent exposure:

**Masking Rules**:
- MinIO: Show last 4 characters (e.g., "***abcd")
- Yandex Disk: Show last 8 characters (e.g., "***12345678")

This ensures that even if API responses are intercepted, full credentials cannot be obtained.

### Secure Testing
The testing mechanism follows the principle of least privilege:
- Credentials are decrypted only for the duration of the test
- Decrypted credentials are not included in API responses
- Test results contain only success/failure status and non-sensitive details
- All testing operations are logged for audit purposes

### Access Control
All storage management endpoints require admin authentication:
- Session-based authentication via authToken cookie
- Role verification to ensure user has admin privileges
- Detailed audit logging of all operations

**Section sources**
- [storage_management.py](file://vertex-ar/app/api/storage_management.py#L110-L147)

## Examples

### MinIO Connection Configuration
Example of creating a MinIO storage connection:

```json
{
  "name": "Production MinIO",
  "type": "minio",
  "config": {
    "endpoint": "minio.example.com:9000",
    "access_key": "AKIAIOSFODNN7EXAMPLE",
    "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "bucket": "vertex-ar-production",
    "secure": true
  }
}
```

After creation, the response will mask sensitive fields:
```json
{
  "id": "storage-abc12345",
  "name": "Production MinIO",
  "type": "minio",
  "config": {
    "endpoint": "minio.example.com:9000",
    "access_key": "***KEY",
    "secret_key": "***KEY",
    "bucket": "vertex-ar-production",
    "secure": true
  },
  "is_active": true,
  "is_tested": false,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### Yandex Disk Connection Configuration
Example of creating a Yandex Disk storage connection:

```json
{
  "name": "Yandex Cloud Storage",
  "type": "yandex_disk",
  "config": {
    "client_id": "your-client-id",
    "client_secret": "your-client-secret",
    "redirect_uri": "https://your-app.com/callback",
    "oauth_token": "ya29.a0AfB_byCHmZI...",
    "base_path": "vertex-ar/company-data"
  }
}
```

The response will mask sensitive fields:
```json
{
  "id": "storage-xyz98765",
  "name": "Yandex Cloud Storage",
  "type": "yandex_disk",
  "config": {
    "client_id": "your-client-id",
    "client_secret": "***SECRET",
    "redirect_uri": "https://your-app.com/callback",
    "oauth_token": "***765",
    "base_path": "vertex-ar/company-data"
  },
  "is_active": true,
  "is_tested": false,
  "created_at": "2025-01-15T10:35:00Z",
  "updated_at": "2025-01-15T10:35:00Z"
}
```

### Testing a Connection
To test a storage connection, send a POST request with the connection ID:

```json
{
  "connection_id": "storage-abc12345"
}
```

Successful test response:
```json
{
  "success": true,
  "message": "MinIO connection successful",
  "details": {
    "endpoint": "minio.example.com:9000",
    "bucket": "vertex-ar-production",
    "secure": true
  }
}
```

Failed test response:
```json
{
  "success": false,
  "message": "MinIO connection failed: Invalid access key"
}
```

**Section sources**
- [storage_management.py](file://vertex-ar/app/api/storage_management.py#L349-L350)
- [storage_management.py](file://vertex-ar/app/api/storage_management.py#L35-L44)
- [storage_management.py](file://vertex-ar/app/api/storage_management.py#L34-L37)

## Error Handling

The Storage Management API implements comprehensive error handling with appropriate HTTP status codes and descriptive error messages.

### Common Error Responses

**401 Unauthorized**: Authentication failed
```json
{
  "detail": "Not authenticated"
}
```

**403 Forbidden**: User lacks admin privileges
```json
{
  "detail": "Admin access required"
}
```

**404 Not Found**: Resource not found
```json
{
  "detail": "Storage connection not found"
}
```

**409 Conflict**: Resource name already exists
```json
{
  "detail": "Storage connection 'Production MinIO' already exists"
}
```

**400 Bad Request**: Invalid request or validation error
```json
{
  "detail": "Storage connection must be active and tested"
}
```

**500 Internal Server Error**: Server-side error
```json
{
  "detail": "Failed to create storage connection"
}
```

### Validation Error Handling
The API performs thorough validation on all requests:

1. **Name Validation**: Ensures connection names are unique and properly formatted
2. **Type Validation**: Confirms storage type is supported (minio, yandex_disk)
3. **Config Validation**: Verifies required fields are present and non-empty
4. **State Validation**: Ensures connections are active and tested before assignment

When configuration updates occur, the system automatically resets the test status, requiring administrators to revalidate the connection before it can be used.

**Section sources**
- [storage_management.py](file://vertex-ar/app/api/storage_management.py#L340-L344)
- [storage_management.py](file://vertex-ar/app/api/storage_management.py#L443-L450)
- [storage_management.py](file://vertex-ar/app/api/storage_management.py#L627-L631)