# Authentication API

<cite>
**Referenced Files in This Document**   
- [auth.py](file://vertex-ar/app/api/auth.py)
- [auth.py](file://vertex-ar/app/auth.py)
- [models.py](file://vertex-ar/app/models.py)
- [users.py](file://vertex-ar/app/api/users.py)
- [rate_limiter.py](file://vertex-ar/app/rate_limiter.py)
- [USER_MANAGEMENT.md](file://docs/guides/USER_MANAGEMENT.md)
- [backend-integration.md](file://docs/mobile/backend-integration.md)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Authentication Flow](#authentication-flow)
3. [API Endpoints](#api-endpoints)
   - [POST /auth/login](#post-authlogin)
   - [POST /auth/logout](#post-authlogout)
   - [POST /users/change-password](#post-userschange-password)
4. [Request/Response Schemas](#requestresponse-schemas)
5. [Authentication Mechanisms](#authentication-mechanisms)
6. [Security Policies](#security-policies)
   - [Rate Limiting](#rate-limiting)
   - [Account Lockout](#account-lockout)
7. [Error Handling](#error-handling)
8. [Curl Examples](#curl-examples)
9. [Security Considerations](#security-considerations)

## Introduction

The Authentication API provides JWT-based authentication for the Vertex AR application, enabling secure user access to protected resources. This API handles user authentication, session management, and security enforcement through a combination of bearer tokens and cookie-based authentication. The system implements robust security features including rate limiting, account lockout policies, and password validation to protect against common security threats.

The authentication system is built on FastAPI with JWT tokens for stateless authentication, while maintaining session state in the database for scalability across Uvicorn workers. All authentication endpoints are protected by rate limiting and account lockout mechanisms to prevent brute force attacks.

**Section sources**
- [USER_MANAGEMENT.md](file://docs/guides/USER_MANAGEMENT.md#L40-L43)
- [backend-integration.md](file://docs/mobile/backend-integration.md#L133-L134)

## Authentication Flow

The JWT-based authentication flow follows a standard pattern for secure API access. Users first authenticate with their credentials via the login endpoint, which validates the username and password against the stored hashed values. Upon successful authentication, the system issues a JWT access token that can be used for subsequent requests.

The authentication flow supports two methods of token transmission: through the Authorization header as a Bearer token or via an authToken cookie. This dual mechanism provides flexibility for different client types, including web applications that may prefer cookie-based authentication and mobile or third-party applications that typically use header-based authentication.

After authentication, the token is validated on each request to protected endpoints. The system checks the token's validity, verifies it hasn't expired, and confirms the associated user account is active. The token's last seen timestamp is updated on each valid request to maintain the session's active status.

```mermaid
sequenceDiagram
participant Client
participant API
participant Database
Client->>API : POST /auth/login with credentials
API->>Database : Verify username and password
Database-->>API : User data
API->>API : Check account lockout status
API->>API : Issue JWT token
API->>Database : Store session
API-->>Client : 200 OK with access_token
Client->>API : Subsequent requests with token
API->>Database : Validate token and session
Database-->>API : Session data
API->>API : Update last_seen timestamp
API-->>Client : Requested resource
Client->>API : POST /auth/logout
API->>Database : Revoke session
API-->>Client : 204 No Content
```

**Diagram sources**
- [auth.py](file://vertex-ar/app/api/auth.py#L109-L169)
- [auth.py](file://vertex-ar/app/auth.py#L27-L93)

## API Endpoints

### POST /auth/login

Authenticates a user and returns an access token.

**URL Pattern:** `/auth/login`

**HTTP Method:** POST

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response (200 OK):**
```json
{
  "access_token": "jwt_token_here",
  "token_type": "bearer"
}
```

**Additional Headers:**
- Sets `authToken` cookie with the JWT token
- `Content-Type: application/json`

The login endpoint verifies the provided credentials against the stored user data. It implements rate limiting (5 requests per minute) and account lockout after multiple failed attempts. Upon successful authentication, it updates the user's last login timestamp and issues a new JWT token.

**Section sources**
- [auth.py](file://vertex-ar/app/api/auth.py#L109-L169)
- [USER_MANAGEMENT.md](file://docs/guides/USER_MANAGEMENT.md#L70-L87)

### POST /auth/logout

Logs out the current user and revokes their access token.

**URL Pattern:** `/auth/logout`

**HTTP Method:** POST

**Headers:** `Authorization: Bearer <token>` or valid `authToken` cookie

**Response (204 No Content):** No content

The logout endpoint invalidates the current session by revoking the JWT token. This prevents further use of the token for authentication. The endpoint requires valid authentication and is also protected by rate limiting (5 requests per minute).

**Section sources**
- [auth.py](file://vertex-ar/app/api/auth.py#L172-L192)
- [USER_MANAGEMENT.md](file://docs/guides/USER_MANAGEMENT.md#L89-L94)

### POST /users/change-password

Changes the current user's password.

**URL Pattern:** `/users/change-password`

**HTTP Method:** POST

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "current_password": "string",
  "new_password": "string"
}
```

**Response (200 OK):**
```json
{
  "message": "Password changed successfully"
}
```

This endpoint requires the user to provide their current password for verification before allowing a password change. After successfully changing the password, the system revokes all other active sessions for the user (except the current one), forcing re-authentication on other devices. This enhances security by ensuring that if a password was compromised, all active sessions are terminated.

**Section sources**
- [users.py](file://vertex-ar/app/api/users.py#L130-L167)
- [USER_MANAGEMENT.md](file://docs/guides/USER_MANAGEMENT.md#L134-L152)

## Request/Response Schemas

The Authentication API uses Pydantic models to define request and response schemas, ensuring data validation and type safety.

### UserLogin Model
```python
class UserLogin(BaseModel):
    username: str
    password: str
```

Used for login requests, this model accepts a username and password without additional validation constraints, as validation is handled at the authentication layer.

### TokenResponse Model
```python
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

The standard response for successful authentication, containing the JWT access token and token type (always "bearer" in this implementation).

### PasswordChange Model
```python
class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=256)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password_field(cls, v: str) -> str:
        return validate_password_strength(v)
```

Used for password change requests, this model includes validation for the new password, ensuring it meets the minimum length requirement and passes password strength validation.

**Section sources**
- [models.py](file://vertex-ar/app/models.py#L20-L67)
- [validators.py](file://vertex-ar/app/validators.py)

## Authentication Mechanisms

The Authentication API supports two mechanisms for transmitting authentication tokens: Bearer tokens in the Authorization header and authToken cookies.

### Bearer Token Authentication

The primary authentication method uses the HTTP Authorization header with the Bearer scheme:

```
Authorization: Bearer <access_token>
```

Clients should include this header in all requests to protected endpoints. The token is extracted from the header and validated against the database-stored session.

### Cookie-Based Authentication

For web applications, the system also supports cookie-based authentication:

```
Cookie: authToken=<access_token>
```

When a user logs in, the server sets an `authToken` cookie that is automatically sent with subsequent requests. This method is particularly useful for browser-based clients that handle cookies automatically.

The authentication system checks both mechanisms, giving priority to the Authorization header if present. This allows clients to use the method that best fits their architecture while maintaining consistent security enforcement.

```mermaid
flowchart TD
Start([Request Received]) --> CheckHeader["Check Authorization Header"]
CheckHeader --> HeaderPresent{"Header Present?"}
HeaderPresent --> |Yes| ExtractBearer["Extract Bearer Token"]
HeaderPresent --> |No| CheckCookie["Check authToken Cookie"]
CheckCookie --> CookiePresent{"Cookie Present?"}
CookiePresent --> |Yes| ExtractCookie["Extract Token from Cookie"]
CookiePresent --> |No| Return401["Return 401 Unauthorized"]
ExtractBearer --> ValidateToken["Validate Token"]
ExtractCookie --> ValidateToken
ValidateToken --> TokenValid{"Token Valid?"}
TokenValid --> |Yes| ProcessRequest["Process Request"]
TokenValid --> |No| Return401
ProcessRequest --> ReturnResponse["Return Response"]
```

**Diagram sources**
- [auth.py](file://vertex-ar/app/api/auth.py#L41-L65)
- [auth.py](file://vertex-ar/app/api/auth.py#L68-L106)

## Security Policies

### Rate Limiting

All authentication endpoints are protected by rate limiting to prevent brute force attacks. The system implements a limit of 5 requests per minute per client IP address and endpoint combination.

The rate limiting is implemented using a sliding window algorithm that tracks requests by client IP and request path. When the limit is exceeded, the API returns a 429 Too Many Requests status code with a Retry-After header indicating when the client can retry.

```python
@router.post("/login", dependencies=[Depends(create_rate_limit_dependency("5/minute"))])
@router.post("/logout", dependencies=[Depends(create_rate_limit_dependency("5/minute"))])
```

The rate limiting configuration is defined in the `rate_limiter.py` module and can be disabled via configuration settings for development or testing purposes.

**Section sources**
- [rate_limiter.py](file://vertex-ar/app/rate_limiter.py#L39-L124)
- [auth.py](file://vertex-ar/app/api/auth.py#L109-L110)

### Account Lockout

The system implements an account lockout policy to protect against password guessing attacks. After 5 failed login attempts within a sliding window, the account is temporarily locked for 15 minutes.

The lockout mechanism is managed by the `AuthSecurityManager` class, which tracks failed attempts and lockout status in memory with thread safety. When an account is locked, the system returns a 423 Locked status code with details about when the lockout period ends.

```python
def register_failure(self, username: str) -> Optional[datetime]:
    with self._lock:
        # ... check existing lockout
        attempts = self._failed_attempts.get(username, 0) + 1
        if attempts >= self._max_attempts:  # Default: 5
            locked_until = now + self._lockout_duration  # Default: 15 minutes
            self._lockouts[username] = locked_until
            self._failed_attempts[username] = 0
            return locked_until
        # ... update attempts
```

The lockout state is automatically cleared after the lockout period expires, allowing legitimate users to try again without administrative intervention.

```mermaid
stateDiagram-v2
[*] --> Active
Active --> FailedAttempt : Invalid credentials
FailedAttempt --> Active : Valid credentials
FailedAttempt --> FailedAttempt : Invalid credentials
FailedAttempt --> Locked : After 5 failures
Locked --> Active : After 15 minutes
Active --> Authenticated : Valid credentials
Authenticated --> Active : Logout
```

**Diagram sources**
- [auth.py](file://vertex-ar/app/auth.py#L108-L152)
- [auth.py](file://vertex-ar/app/api/auth.py#L125-L150)

## Error Handling

The Authentication API implements comprehensive error handling to provide clear feedback while maintaining security.

### Common Error Responses

**401 Unauthorized**: Returned when authentication credentials are invalid or missing.
```json
{
  "detail": "Invalid credentials"
}
```

**423 Locked**: Returned when an account is temporarily locked due to multiple failed login attempts.
```json
{
  "detail": "Account locked until 2024-01-01T12:00:00Z"
}
```

**429 Too Many Requests**: Returned when rate limiting is exceeded.
```json
{
  "detail": "Rate limit exceeded"
}
```
With response header: `Retry-After: 60` (seconds)

**403 Forbidden**: Returned when a user is authenticated but lacks required permissions.
```json
{
  "detail": "User is deactivated"
}
```

The error handling system is designed to provide enough information for clients to handle errors appropriately while avoiding information leakage that could aid attackers. For example, the system returns the same "Invalid credentials" message for both non-existent usernames and incorrect passwords to prevent username enumeration.

**Section sources**
- [auth.py](file://vertex-ar/app/api/auth.py#L47-L60)
- [auth.py](file://vertex-ar/app/api/auth.py#L133-L156)

## Curl Examples

### Login with Credentials

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "securePassword123"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Authenticated Request with Bearer Token

```bash
curl -X GET "http://localhost:8000/users/profile" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Logout

```bash
curl -X POST "http://localhost:8000/auth/logout" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -v
```

**Response:** HTTP 204 No Content

### Change Password

```bash
curl -X POST "http://localhost:8000/users/change-password" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "oldPassword123",
    "new_password": "newSecurePassword456"
  }'
```

**Response:**
```json
{
  "message": "Password changed successfully"
}
```

**Section sources**
- [backend-integration.md](file://docs/mobile/backend-integration.md#L135-L258)
- [USER_MANAGEMENT.md](file://docs/guides/USER_MANAGEMENT.md)

## Security Considerations

### Password Validation

The system enforces strong password policies through validation rules:

- Minimum 8 characters
- Must contain both letters and numbers
- Maximum 256 characters
- No common password patterns

The password strength validation is implemented in the `validate_password_strength` function and applied to both user registration and password changes.

### Token Security

JWT tokens have a default expiration of 30 minutes, after which they must be refreshed by re-authenticating. Tokens are stored in the database with session information, allowing for revocation on logout or password change. The system uses cryptographically secure random generation for token values (32 bytes, URL-safe base64 encoded).

### Account Security

When a user changes their password, the system automatically revokes all other active sessions for that user, requiring re-authentication on other devices. This prevents unauthorized access if a password was compromised on one device.

The account lockout policy (5 attempts in 15 minutes) balances security with usability, preventing brute force attacks while allowing legitimate users to recover from occasional mistakes.

### Rate Limiting Configuration

Rate limiting is configurable via environment variables and can be adjusted based on deployment requirements. The current configuration of 5 requests per minute provides strong protection against automated attacks while allowing for normal user behavior.

**Section sources**
- [USER_MANAGEMENT.md](file://docs/guides/USER_MANAGEMENT.md#L290-L304)
- [validators.py](file://vertex-ar/app/validators.py)
- [auth.py](file://vertex-ar/app/auth.py#L30-L31)