# User Management System

This document describes the comprehensive user management system implemented for Vertex AR.

## Overview

The user management system provides:

- **User Registration & Authentication**: Secure user signup and login with JWT tokens
- **Profile Management**: Users can update their profiles and change passwords
- **Admin Controls**: Admins can manage all users, view statistics, and control access
- **Role-Based Access**: Different permissions for regular users and administrators
- **Security Features**: Rate limiting, account lockouts, and session management

## Features

### User Authentication
- **Registration**: First user automatically becomes admin, subsequent users are regular users
- **Login**: JWT-based authentication with configurable session timeouts
- **Logout**: Token revocation and session cleanup
- **Password Security**: SHA-256 hashing with salt (upgrade to bcrypt recommended for production)

### User Profiles
- **Profile Information**: Username, email, full name, creation date, last login
- **Profile Updates**: Users can update their email and full name
- **Password Changes**: Secure password change with current password verification
- **Account Status**: Active/inactive status with soft delete functionality

### Admin Management
- **User Listing**: Paginated list of all users with filtering options
- **User Search**: Search by username, email, or full name
- **User Creation**: Admins can create new user accounts
- **User Updates**: Admins can modify user properties including roles
- **User Deletion**: Soft delete with account deactivation
- **User Statistics**: Comprehensive user metrics and analytics

### Security Features
- **Rate Limiting**: Configurable rate limits on authentication endpoints
- **Account Lockout**: Temporary lockout after failed login attempts
- **Session Management**: Configurable session timeouts and token revocation
- **Authorization Checks**: Role-based access control on all endpoints
- **Input Validation**: Comprehensive request validation and sanitization

## API Endpoints

### Authentication Endpoints

#### POST /auth/register
Register a new user account.

**Request Body:**
```json
{
  "username": "string (3-150 chars)",
  "password": "string (8-256 chars)",
  "email": "string (optional, max 255 chars)",
  "full_name": "string (optional, max 150 chars)"
}
```

**Response (201):**
```json
{
  "username": "admin",
  "is_admin": true,
  "message": "Admin user created"
}
```

#### POST /auth/login
Authenticate and get access token.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response (200):**
```json
{
  "access_token": "jwt_token_here",
  "token_type": "bearer"
}
```

#### POST /auth/logout
Revoke access token and logout.

**Headers:** `Authorization: Bearer <token>`

**Response (204):** No content

### User Profile Endpoints

#### GET /users/profile
Get current user's profile.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "username": "testuser",
  "email": "test@example.com",
  "full_name": "Test User",
  "created_at": "2024-01-01T12:00:00Z",
  "last_login": "2024-01-01T15:30:00Z"
}
```

#### PUT /users/profile
Update current user's profile.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "email": "string (optional)",
  "full_name": "string (optional)"
}
```

**Response (200):**
```json
{
  "message": "Profile updated successfully"
}
```

#### POST /users/change-password
Change current user's password.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "current_password": "string",
  "new_password": "string (8-256 chars)"
}
```

**Response (200):**
```json
{
  "message": "Password changed successfully. Please login again."
}
```

### Admin User Management Endpoints

#### GET /users/users
List users with optional filtering (admin only).

**Headers:** `Authorization: Bearer <admin_token>`

**Query Parameters:**
- `is_admin`: boolean (optional)
- `is_active`: boolean (optional)
- `limit`: integer (default 50, max 100)
- `offset`: integer (default 0)

**Response (200):**
```json
[
  {
    "username": "user1",
    "email": "user1@example.com",
    "full_name": "User One",
    "is_admin": false,
    "is_active": true,
    "created_at": "2024-01-01T12:00:00Z",
    "last_login": "2024-01-01T15:30:00Z"
  }
]
```

#### GET /users/users/search
Search users by query (admin only).

**Headers:** `Authorization: Bearer <admin_token>`

**Query Parameters:**
- `query`: string (required)
- `limit`: integer (default 50, max 100)
- `offset`: integer (default 0)

**Response (200):** Array of user objects matching the search

#### POST /users/users
Create a new user (admin only).

**Headers:** `Authorization: Bearer <admin_token>`

**Request Body:**
```json
{
  "username": "string (3-150 chars)",
  "password": "string (8-256 chars)",
  "email": "string (optional, max 255 chars)",
  "full_name": "string (optional, max 150 chars)"
}
```

**Response (200):**
```json
{
  "message": "User username created successfully"
}
```

#### PUT /users/users/{username}
Update a user (admin only).

**Headers:** `Authorization: Bearer <admin_token>`

**Request Body:**
```json
{
  "email": "string (optional)",
  "full_name": "string (optional)",
  "is_admin": "boolean (optional)",
  "is_active": "boolean (optional)"
}
```

**Response (200):**
```json
{
  "message": "User username updated successfully"
}
```

#### DELETE /users/users/{username}
Deactivate a user (admin only).

**Headers:** `Authorization: Bearer <admin_token>`

**Response (200):**
```json
{
  "message": "User username deactivated successfully"
}
```

#### GET /users/stats
Get user statistics (admin only).

**Headers:** `Authorization: Bearer <admin_token>`

**Response (200):**
```json
{
  "total_users": 25,
  "active_users": 23,
  "admin_users": 2,
  "recent_logins": 15
}
```

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    username TEXT PRIMARY KEY,
    hashed_password TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    email TEXT,
    full_name TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

### Indexes

```sql
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);
```

## Security Considerations

### Password Security
- Current implementation uses SHA-256 hashing
- **Recommendation**: Upgrade to bcrypt for production use
- Minimum password length: 8 characters
- Password change requires current password verification

### Session Management
- JWT tokens with configurable expiration (default 30 minutes)
- Token revocation on logout and password change
- Session tracking with last login timestamps

### Rate Limiting
- Authentication endpoints: 5 requests per minute
- Global rate limit: 100 requests per minute
- Configurable via environment variables

### Access Control
- Role-based access control (admin vs regular user)
- Admin verification on all admin endpoints
- Active status verification for all authenticated requests

## Configuration

### Environment Variables

```bash
# Authentication
SESSION_TIMEOUT_MINUTES=30
AUTH_MAX_ATTEMPTS=5
AUTH_LOCKOUT_MINUTES=15

# Rate Limiting
RATE_LIMIT_ENABLED=true
GLOBAL_RATE_LIMIT=100/minute
AUTH_RATE_LIMIT=5/minute
UPLOAD_RATE_LIMIT=10/minute

# Database
DATABASE_URL=sqlite:///./vertex_art.db
```

## Migration Guide

### From Existing System
The user management system includes automatic database migration:
- New columns are added to existing users table
- Existing users are marked as active by default
- First registered user automatically becomes admin

### Data Migration
```python
# Example migration script
database = Database("path/to/database.db")

# Update existing users to be active
database._execute("UPDATE users SET is_active = 1 WHERE is_active IS NULL")

# Set first user as admin if no admins exist
stats = database.get_user_stats()
if stats['admin_users'] == 0:
    first_user = database.list_users(limit=1)
    if first_user:
        database.update_user(first_user[0]['username'], is_admin=True)
```

## Testing

### Automated Tests
Run the comprehensive test suite:
```bash
cd vertex-ar
python -m pytest tests/test_user_management.py -v
```

### Manual Testing
Use the manual test script:
```bash
cd vertex-ar
python test_user_management_manual.py
```

### Test Coverage
- User registration and authentication
- Profile management and password changes
- Admin user management operations
- Authorization and security controls
- Edge cases and error handling

## Best Practices

### For Users
- Use strong passwords (minimum 8 characters)
- Keep login credentials secure
- Logout when finished using the application
- Update password periodically

### For Administrators
- Regularly review user accounts and permissions
- Monitor user statistics for unusual activity
- Use descriptive names and emails for user accounts
- Deactivate accounts that are no longer needed

### For Developers
- Use HTTPS in production
- Implement proper input validation
- Log security events for monitoring
- Regularly update dependencies
- Consider upgrading to bcrypt for password hashing

## Troubleshooting

### Common Issues

1. **"Admin access required" error**
   - Verify user has admin privileges
   - Check if user account is active
   - Ensure token is valid and not expired

2. **"Token expired or invalid" error**
   - Login again to get a fresh token
   - Check session timeout configuration
   - Verify token format in Authorization header

3. **"Account locked" error**
   - Wait for lockout period to expire
   - Contact administrator to unlock account
   - Check login attempt limits

4. **Database migration issues**
   - Ensure database file is writable
   - Check for existing conflicting schema
   - Review migration logs for specific errors

## Future Enhancements

### Planned Features
- Email verification for user registration
- Password reset functionality
- Two-factor authentication (2FA)
- User groups and permissions
- Audit logging for admin actions
- OAuth2/OIDC integration
- API key management for service accounts

### Security Improvements
- Bcrypt password hashing
- Advanced rate limiting with Redis
- IP-based access controls
- Device management and tracking
- Anomaly detection for security events

## Support

For issues related to the user management system:
1. Check the application logs for error details
2. Verify configuration settings
3. Review the troubleshooting section
4. Contact the development team with specific error messages

---

**Version**: 1.0.0
**Last Updated**: 2024-01-01
**Compatibility**: Vertex AR v1.1.0+
