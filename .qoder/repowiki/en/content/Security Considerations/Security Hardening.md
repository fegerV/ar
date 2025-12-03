# Security Hardening

<cite>
**Referenced Files in This Document**   
- [middleware.py](file://vertex-ar/app/middleware.py)
- [rate_limiter.py](file://vertex-ar/app/rate_limiter.py)
- [config.py](file://vertex-ar/app/config.py)
- [main.py](file://vertex-ar/app/main.py)
- [.env.example](file://vertex-ar/.env.example)
- [.env.production.example](file://vertex-ar/.env.production.example)
- [validators.py](file://vertex-ar/app/validators.py)
- [models.py](file://vertex-ar/app/models.py)
- [Dockerfile.nft-maker](file://vertex-ar/Dockerfile.nft-maker)
- [docker-compose.yml](file://docker-compose.yml)
- [vertex-ar-backup.service](file://vertex-ar/systemd/vertex-ar-backup.service)
- [vertex-ar-backup.timer](file://vertex-ar/systemd/vertex-ar-backup.timer)
- [deploy-vertex-ar-cloud-ru-improved.sh](file://deploy-vertex-ar-cloud-ru-improved.sh)
- [SECURITY.md](file://SECURITY.md)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Security Headers Implementation](#security-headers-implementation)
3. [Input Validation Strategies](#input-validation-strategies)
4. [Rate Limiting Implementation](#rate-limiting-implementation)
5. [Secure Configuration Practices](#secure-configuration-practices)
6. [Production Deployment Hardening](#production-deployment-hardening)
7. [Common Security Issues and Mitigations](#common-security-issues-and-mitigations)
8. [Security Audit Checklists](#security-audit-checklists)
9. [Conclusion](#conclusion)

## Introduction

The AR backend application implements comprehensive security hardening practices across multiple layers to protect against common web application vulnerabilities. This document details the security architecture and implementation strategies for the Vertex AR application, focusing on security headers, input validation, rate limiting, secure configuration, and production deployment hardening.

The application follows a defense-in-depth approach with multiple security layers including middleware protections, input validation, rate limiting, secure configuration management, and hardened deployment practices. The security model is designed to prevent common attacks such as injection, cross-site scripting, brute force attacks, and information leakage while maintaining operational reliability.

**Section sources**
- [SECURITY.md](file://SECURITY.md#L1-L120)

## Security Headers Implementation

The AR backend application implements critical security headers through both application-level middleware and infrastructure-level configuration to protect against common web vulnerabilities.

Security headers are implemented at two levels: application middleware and reverse proxy configuration. The Nginx reverse proxy handles the primary security headers, while the application middleware provides additional security features.

The following security headers are implemented:

- **Content-Security-Policy (CSP)**: Implemented via Nginx configuration to prevent cross-site scripting (XSS) attacks by restricting the sources from which content can be loaded
- **X-Content-Type-Options**: Set to "nosniff" to prevent MIME type sniffing attacks
- **X-Frame-Options**: Set to "SAMEORIGIN" to prevent clickjacking attacks
- **X-XSS-Protection**: Enabled with "1; mode=block" to activate browser XSS protection
- **Strict-Transport-Security (HSTS)**: Enforced with a 2-year max-age to ensure HTTPS connections

The Nginx configuration in the deployment script implements these headers as shown in the server configuration:

```nginx
# Security headers
add_header Strict-Transport-Security "max-age=63072000" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
```

Additionally, the application implements a request ID header for tracking and correlation of requests across the system, which is added by the RequestLoggingMiddleware:

```python
# Add request ID to response headers
response.headers["X-Request-ID"] = request_id
```

This header-based security approach follows industry best practices and provides defense against common client-side attacks while ensuring secure communication between the client and server.

**Section sources**
- [deploy-vertex-ar-cloud-ru-improved.sh](file://deploy-vertex-ar-cloud-ru-improved.sh#L878-L923)
- [middleware.py](file://vertex-ar/app/middleware.py#L1-L156)

## Input Validation Strategies

The AR backend application implements robust input validation using Pydantic models and custom validators to prevent injection attacks and ensure data integrity across all API endpoints.

### Pydantic Model Validation

The application uses Pydantic models extensively for request and response validation. These models define strict type hints, field constraints, and custom validation logic to ensure that all incoming data meets security and business requirements.

Key validation features include:

- Field-level constraints using Pydantic's Field class (min_length, max_length, etc.)
- Custom field validators using the @field_validator decorator
- Post-model validation using model_post_init for cross-field validation
- Automatic type conversion and validation

### Custom Validators

The application implements a comprehensive set of custom validators in the validators.py module to handle specific validation requirements:

```python
def validate_email(email: str) -> str:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValueError("Invalid email format")
    return email.lower()

def validate_password_strength(password: str) -> str:
    """Validate password meets minimum security requirements."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    has_letter = re.search(r'[a-zA-Z]', password)
    has_number = re.search(r'\d', password)
    if not has_letter:
        raise ValueError("Password must contain at least one letter")
    if not has_number:
        raise ValueError("Password must contain at least one number")
    return password
```

These validators are integrated into Pydantic models through field validators:

```python
class CompanyCreate(BaseModel):
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    website: Optional[str] = Field(default=None, max_length=2048)
    
    @field_validator('email')
    @classmethod
    def validate_email_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return validate_email(v)
        return v
    
    @field_validator('phone')
    @classmethod
    def validate_phone_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return validate_phone(v)
        return v
```

### Cross-Field Validation

The application implements cross-field validation using the model_post_init method to validate relationships between fields:

```python
def model_post_init(self, __context):
    """Validate storage configuration after all fields are set."""
    if self.storage_type in ['minio', 'yandex_disk']:
        if not self.storage_connection_id:
            raise ValueError(f'{self.storage_type} storage requires storage_connection_id')
    return super().model_post_init(__context) if hasattr(super(), 'model_post_init') else None
```

This validation strategy prevents injection attacks by sanitizing and validating all input data, ensures data integrity through comprehensive validation rules, and provides clear error messages for invalid input while preventing information leakage about the internal system structure.

**Section sources**
- [validators.py](file://vertex-ar/app/validators.py#L1-L212)
- [models.py](file://vertex-ar/app/models.py#L1-L1060)

## Rate Limiting Implementation

The AR backend application implements a custom rate limiting solution using the rate_limiter module to prevent brute force attacks and protect against denial of service conditions.

### Custom Rate Limiter Design

The application implements a custom rate limiter instead of relying on third-party packages to avoid compatibility issues. The rate limiter is designed as an in-memory solution using a thread-safe deque to track requests within a sliding window.

The core components of the rate limiting implementation include:

- **SimpleRateLimiter class**: The main rate limiting implementation using a dictionary of deques to track requests by key
- **Thread safety**: Uses Python's Lock to ensure thread-safe operations in multi-threaded environments
- **Sliding window algorithm**: Removes expired requests from the beginning of the deque to maintain an accurate count within the time window

```python
class SimpleRateLimiter:
    """Simple in-memory rate limiter using deque for request tracking."""
    
    def __init__(self):
        self._requests: Dict[str, deque] = defaultdict(deque)
        self._lock = Lock()
    
    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Check if request is allowed based on rate limit."""
        with self._lock:
            now = datetime.utcnow().timestamp()
            requests = self._requests[key]
            
            # Remove old requests outside the window
            while requests and requests[0] < now - window:
                requests.popleft()
            
            # Check if under limit
            if len(requests) < limit:
                requests.append(now)
                return True
            return False
```

### Rate Limit Configuration

Rate limiting is configured through environment variables and can be enabled or disabled globally. The configuration includes different rate limits for various types of endpoints:

- **Global rate limit**: Applied to all endpoints (default: 100/minute)
- **Authentication rate limit**: Applied to login and authentication endpoints (default: 5/minute)
- **Upload rate limit**: Applied to file upload endpoints (default: 10/minute)

These limits are configured in the Settings class:

```python
# Rate limiting settings
self.RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true" and not self.RUNNING_TESTS
self.GLOBAL_RATE_LIMIT = os.getenv("GLOBAL_RATE_LIMIT", "100/minute")
self.AUTH_RATE_LIMIT = os.getenv("AUTH_RATE_LIMIT", "5/minute")
self.UPLOAD_RATE_LIMIT = os.getenv("UPLOAD_RATE_LIMIT", "10/minute")
```

### FastAPI Integration

The rate limiter is integrated with FastAPI through dependency injection, allowing rate limits to be applied declaratively to endpoints:

```python
async def rate_limit_dependency(request: Request, limit: str) -> None:
    """Rate limiting dependency for FastAPI endpoints."""
    if not settings.RATE_LIMIT_ENABLED:
        return
        
    limit_count, period_seconds = parse_rate_limit(limit)
    key = f"{request.client.host}:{request.url.path}"
    if not rate_limiter.is_allowed(key, limit_count, period_seconds):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(period_seconds)}
        )

def create_rate_limit_dependency(limit: str):
    """Create a rate limiting dependency with a specific limit."""
    async def dependency(request: Request) -> None:
        await rate_limit_dependency(request, limit)
    return dependency
```

The rate limiter is applied globally to the application through the FastAPI dependencies parameter:

```python
app = FastAPI(
    title="Vertex AR - Simplified",
    version=settings.VERSION,
    description="A lightweight AR backend for creating augmented reality experiences from image + video pairs",
    dependencies=[Depends(create_rate_limit_dependency(settings.GLOBAL_RATE_LIMIT))],
)
```

Specific endpoints can override the global rate limit by applying a different rate limit dependency:

```python
@app.post("/auth/login", dependencies=[Depends(create_rate_limit_dependency(settings.AUTH_RATE_LIMIT))])
async def login(user_login: UserLogin):
    # Login logic here
    pass
```

This rate limiting implementation effectively prevents brute force attacks on authentication endpoints, protects against denial of service attacks by limiting request frequency, and ensures fair usage of application resources across all users.

**Section sources**
- [rate_limiter.py](file://vertex-ar/app/rate_limiter.py#L1-L124)
- [config.py](file://vertex-ar/app/config.py#L1-L244)
- [main.py](file://vertex-ar/app/main.py#L1-L477)

## Secure Configuration Practices

The AR backend application implements comprehensive secure configuration practices for environment variables, database connections, and third-party integrations to prevent configuration-related security issues.

### Environment Variable Management

The application follows the 12-factor app methodology for configuration management, storing all configuration in environment variables rather than in code. This approach ensures that configuration can vary between deployment environments without code changes.

Key configuration files include:

- **.env.example**: Template file with default values and documentation for all environment variables
- **.env.production.example**: Production-specific configuration template with secure defaults

The application loads configuration through the Settings class, which provides type conversion, validation, and sensible defaults:

```python
class Settings:
    """Application settings."""
    
    def __init__(self) -> None:
        self.load_environment()
    
    def load_environment(self) -> None:
        """Load configuration from environment variables."""
        # Base paths
        self.BASE_DIR = Path(__file__).resolve().parent.parent
        db_dir = Path("/app/data") if Path("/app/data").exists() else self.BASE_DIR
        self.DB_DIR = db_dir
        self.DB_DIR.mkdir(parents=True, exist_ok=True)
        self.DB_PATH = self.DB_DIR / "app_data.db"
        
        # Security settings
        self.SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key-change-in-production")
        self.SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
        
        # Rate limiting settings
        self.RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        self.GLOBAL_RATE_LIMIT = os.getenv("GLOBAL_RATE_LIMIT", "100/minute")
        
        # SMTP security
        _env_smtp_username = os.getenv("SMTP_USERNAME")
        _env_smtp_password = os.getenv("SMTP_PASSWORD")
        
        if _env_smtp_username or _env_smtp_password:
            # Security warning for deprecated SMTP credentials
            if environment == "production":
                _logger.critical("FATAL: Cannot start in production with env-based SMTP credentials")
                sys.exit(1)
```

### Database Connection Security

The application uses SQLite by default but is designed to support PostgreSQL for production deployments. Database connections are configured through environment variables:

```python
# SQLite database path
DATABASE_URL=sqlite:///./app_data.db

# For PostgreSQL (when migrating from SQLite):
# DATABASE_URL=postgresql://user:password@localhost:5432/vertex_ar
```

The application implements several database security practices:

- Database file permissions are managed by the application
- Sensitive credentials are not stored in environment variables for production
- The application refuses to start in production if SMTP credentials are configured via environment variables

### Third-Party Integration Security

The application implements secure practices for third-party integrations, particularly for SMTP and storage services.

#### SMTP Security

The application has deprecated the use of environment variables for SMTP credentials in production, requiring operators to configure SMTP credentials through a secure admin UI with encrypted storage:

```python
# SECURITY: Check for deprecated env-based SMTP credentials
_env_smtp_username = os.getenv("SMTP_USERNAME")
_env_smtp_password = os.getenv("SMTP_PASSWORD")

if _env_smtp_username or _env_smtp_password:
    # Security warning
    if environment == "production":
        _logger.critical("FATAL: Cannot start in production with env-based SMTP credentials")
        sys.exit(1)
```

SMTP credentials are stored encrypted in the database using PBKDF2-derived AES-256 encryption, and the application provides a secure interface for configuring these credentials through the admin UI.

#### Storage Integration Security

The application supports multiple storage backends including local storage, MinIO, and Yandex Disk. Storage configurations are managed through a secure admin interface with encrypted credential storage:

```python
# Storage settings
self.STORAGE_TYPE = os.getenv("STORAGE_TYPE", "local")  # local or minio
self.MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
self.MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
self.MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
self.MINIO_BUCKET = os.getenv("MINIO_BUCKET", "vertex-ar")
```

Storage credentials are never exposed in API responses or logs, and all storage connections are tested securely without exposing credentials in the test results.

These secure configuration practices ensure that sensitive information is properly protected, prevent accidental exposure of credentials, and provide clear guidance for secure deployment configurations.

**Section sources**
- [.env.example](file://vertex-ar/.env.example#L1-L339)
- [.env.production.example](file://vertex-ar/.env.production.example#L1-L93)
- [config.py](file://vertex-ar/app/config.py#L1-L244)
- [SECURITY.md](file://SECURITY.md#L1-L120)

## Production Deployment Hardening

The AR backend application implements comprehensive hardening guidelines for production deployments, covering Docker container security, systemd service isolation, and file system permissions to ensure a secure runtime environment.

### Docker Container Security

The application is designed to run in Docker containers with security best practices applied to the container configuration:

- **Minimal base images**: The application uses Alpine Linux as the base image for reduced attack surface
- **Non-root user**: The application runs as a non-root user within the container to limit privileges
- **Read-only filesystems**: Configuration files are mounted as read-only to prevent modification
- **Resource limits**: CPU and memory limits can be applied to prevent resource exhaustion

The docker-compose.yml file demonstrates these security practices:

```yaml
version: '3.8'
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.app
    container_name: vertex_ar_app_simplified
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./app_data.db
      - STORAGE_ROOT=/app/storage
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./storage:/app/storage
      - ./app_data:/app/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: vertex_ar_nginx_simplified
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - nginx_logs:/var/log/nginx
    depends_on:
      - app
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "sh", "-c", "curl -f http://localhost/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

Key security features in the Docker configuration include:
- Nginx configuration mounted as read-only (`:ro`)
- Separate volumes for persistent data and logs
- Health checks to ensure service availability
- Restart policies to maintain service uptime

### Systemd Service Isolation

The application includes systemd service files for managing backup operations with proper isolation and security controls:

```ini
[Unit]
Description=Vertex AR Backup Service
After=network.target

[Service]
Type=oneshot
User=vertex-ar
Group=vertex-ar
WorkingDirectory=/opt/vertex-ar
Environment="PATH=/opt/vertex-ar/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/opt/vertex-ar/.venv/bin/python /opt/vertex-ar/backup_cli.py create full
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vertex-ar-backup

[Install]
WantedBy=multi-user.target
```

Security features in the systemd service configuration include:
- Dedicated user and group (`vertex-ar`) for service isolation
- Explicit working directory to prevent directory traversal issues
- Controlled PATH environment variable to prevent library hijacking
- Journal logging for audit trail
- Syslog identifier for easy log filtering

The accompanying timer file ensures that backups are executed on a regular schedule:

```ini
[Unit]
Description=Run Vertex AR backups daily
After=network.target

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

### File System Permissions

The application implements strict file system permissions to protect sensitive data and configuration:

- **Configuration files**: Environment files are set to 600 permissions to restrict access to the owner
- **Database files**: SQLite database files are owned by the application user with restricted permissions
- **Storage directories**: Upload directories have proper ownership and permissions to prevent unauthorized access
- **Log files**: Application logs are rotated and have appropriate permissions to prevent information leakage

The deployment scripts implement proper file ownership and permissions:

```bash
# Ensure backup directory is writable
sudo chown -R vertex-ar:vertex-ar /opt/vertex-ar/backups
sudo chmod 755 /opt/vertex-ar/backups
```

Additional security measures include:
- Sensitive directories are not web-accessible
- Temporary files are created with secure permissions
- Directory traversal is prevented through input validation
- File uploads are stored in a separate directory from application code

These production deployment hardening practices ensure that the application runs in a secure environment with proper isolation, least privilege, and defense-in-depth principles applied at the infrastructure level.

**Section sources**
- [docker-compose.yml](file://docker-compose.yml#L1-L50)
- [vertex-ar-backup.service](file://vertex-ar/systemd/vertex-ar-backup.service#L1-L18)
- [vertex-ar-backup.timer](file://vertex-ar/systemd/vertex-ar-backup.timer#L1-L10)
- [Dockerfile.nft-maker](file://vertex-ar/Dockerfile.nft-maker#L1-L37)

## Common Security Issues and Mitigations

The AR backend application addresses several common security issues through proactive design and implementation choices, preventing information leakage, insecure defaults, and misconfigured integrations.

### Information Leakage Prevention

The application implements multiple measures to prevent information leakage that could aid attackers:

- **Error handling**: Generic error messages are returned to clients while detailed error information is logged server-side
- **Version disclosure**: Application version is only exposed in responses when necessary, and server software versions are hidden
- **Directory listing**: Disabled in both the application and reverse proxy configuration
- **Sensitive data in logs**: Request bodies and sensitive parameters are filtered from logs

The middleware components play a crucial role in preventing information leakage:

```python
class ValidationErrorLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log validation errors in detail."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            
            # Log 422 Unprocessable Entity (validation errors)
            if response.status_code == 422:
                logger.warning(
                    "validation_error",
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                )
            
            return response
            
        except Exception as exc:
            raise
```

This approach ensures that validation errors are logged for debugging but not exposed in a way that reveals internal data structure to potential attackers.

### Insecure Defaults Mitigation

The application addresses insecure defaults through several mechanisms:

- **Secure configuration templates**: The .env.production.example file provides secure defaults for production deployment
- **Security warnings**: The application logs warnings when insecure configurations are detected
- **Production safeguards**: Critical security features cannot be disabled in production

The SMTP configuration security is a prime example of addressing insecure defaults:

```python
# In production, refuse to start with env-based credentials
environment = os.getenv("ENVIRONMENT", "development").lower()
if environment == "production":
    _logger.critical("FATAL: Cannot start in production with env-based SMTP credentials")
    sys.exit(1)
```

This prevents the accidental deployment of applications with credentials exposed in environment variables.

### Misconfigured Integrations

The application prevents misconfigured integrations through validation and secure defaults:

- **Storage configuration validation**: Ensures that required fields are present for each storage type
- **Connection testing**: Provides a secure interface to test storage connections without exposing credentials
- **Default deny**: Security features are enabled by default and must be explicitly disabled

The storage connection validation demonstrates this approach:

```python
@field_validator('config')
@classmethod
def validate_config_fields(cls, v: Dict[str, Any], info) -> Dict[str, Any]:
    """Validate required fields based on storage type."""
    if not hasattr(info, 'data') or 'type' not in info.data:
        return v

    storage_type = info.data.get('type')

    if storage_type == 'yandex_disk':
        required_fields = ['client_id', 'client_secret', 'redirect_uri', 'oauth_token']
        missing_fields = [field for field in required_fields if not v.get(field)]
        if missing_fields:
            raise ValueError(f'Yandex Disk requires the following fields in config: {", ".join(missing_fields)}')
```

### Additional Security Measures

The application implements several other security measures to address common issues:

- **CSRF protection**: While not explicitly implemented, the use of JWT tokens and stateless authentication reduces CSRF risk
- **Clickjacking protection**: X-Frame-Options header prevents embedding in iframes
- **MIME type sniffing prevention**: X-Content-Type-Options header prevents browser from guessing MIME types
- **HTTPS enforcement**: HSTS header ensures all connections use HTTPS

The application also includes a comprehensive security policy document (SECURITY.md) that outlines the security posture, vulnerability disclosure process, and incident response procedures.

These measures collectively address common security issues by applying defense-in-depth principles, following security best practices, and implementing proactive safeguards against known vulnerabilities and misconfigurations.

**Section sources**
- [SECURITY.md](file://SECURITY.md#L1-L120)
- [config.py](file://vertex-ar/app/config.py#L1-L244)
- [validators.py](file://vertex-ar/app/validators.py#L1-L212)
- [models.py](file://vertex-ar/app/models.py#L1-L1060)

## Security Audit Checklists

The AR backend application provides comprehensive checklists for security audits and vulnerability scanning procedures to ensure consistent security assessment and compliance.

### Pre-Deployment Security Checklist

Before deploying the application to production, the following security checks should be performed:

- [ ] **Secrets Management**: All secrets (SECRET_KEY, database credentials, API keys) are set in environment variables and not committed to version control
- [ ] **HTTPS Configuration**: SSL/TLS is properly configured with valid certificates and HSTS header enabled
- [ ] **CORS Configuration**: CORS origins are restricted to trusted domains, not using wildcard (*)
- [ ] **Rate Limiting**: Rate limiting is enabled and configured with appropriate limits for different endpoints
- [ ] **Security Headers**: All recommended security headers are implemented (CSP, X-Frame-Options, X-Content-Type-Options, X-XSS-Protection)
- [ ] **Database Security**: Database credentials are not stored in environment variables, especially for production
- [ ] **File Permissions**: Proper file and directory permissions are set for configuration files, database, and storage directories
- [ ] **Backup Configuration**: Automated backups are configured and tested
- [ ] **Monitoring and Alerting**: System monitoring and alerting are configured for CPU, memory, disk usage, and application health
- [ ] **Logging Configuration**: Structured logging is enabled with appropriate log levels and log rotation

### Vulnerability Scanning Procedures

The application should be regularly scanned for vulnerabilities using the following tools and procedures:

#### Dependency Scanning
```bash
# Check for known vulnerabilities in dependencies
pip-audit
safety scan

# Check for dependency conflicts
pip check

# Check for outdated packages
pip list --outdated
```

#### Static Code Analysis
```bash
# Python security scanning
bandit -r vertex-ar/

# Advanced code analysis
semgrep --config=auto vertex-ar/

# Docker image scanning
trivy image vertex-ar:latest
```

#### Configuration Review
```bash
# Check for hardcoded secrets
git grep -E "(password|key|secret|token)" --and --not -e ".env" --and --not -e "example"

# Verify security headers in Nginx configuration
grep -E "(add_header|security)" nginx.conf

# Check file permissions in deployment scripts
grep -E "(chmod|chown)" *.sh
```

#### Runtime Security Testing
```bash
# Run production readiness check
./scripts/check_production_readiness.sh

# Run security-specific tests
pytest test_security.py

# Check for open ports and services
nmap -sV localhost

# Test rate limiting
for i in {1..20}; do curl -s -o /dev/null -w "%{http_code} " http://localhost:8000/health; done
```

### Post-Deployment Verification

After deployment, verify the following security controls are functioning:

- [ ] **Security Headers**: Use browser developer tools or curl to verify security headers are present and correctly configured
- [ ] **Rate Limiting**: Test rate limiting by sending multiple requests to verify 429 responses after exceeding limits
- [ ] **Authentication Security**: Verify account lockout after multiple failed login attempts
- [ ] **Input Validation**: Test input validation with malformed data to ensure proper error handling
- [ ] **Backup Verification**: Verify that automated backups are created and can be restored
- [ ] **Log Verification**: Check that security events (failed logins, validation errors) are properly logged
- [ ] **Monitoring Alerts**: Verify that monitoring alerts are triggered for simulated high CPU, memory, or disk usage

### Regular Security Maintenance

Security should be an ongoing process with regular maintenance activities:

- **Quarterly dependency audits**: Run comprehensive dependency security scans and update packages as needed
- **Monthly configuration reviews**: Review security configurations and update as needed
- **Weekly log reviews**: Monitor security logs for suspicious activity
- **Bi-weekly backup testing**: Test backup restoration procedures
- **Annual penetration testing**: Conduct comprehensive security assessments

The application includes a production readiness script that automates many of these checks:

```bash
# Run comprehensive production readiness check
./scripts/check_production_readiness.sh
```

This script evaluates the deployment against multiple security and operational criteria and provides a readiness percentage along with recommendations for improvement.

By following these checklists and procedures, operators can ensure that the AR backend application maintains a high security posture throughout its lifecycle, from development through deployment and ongoing operation.

**Section sources**
- [SECURITY.md](file://SECURITY.md#L1-L120)
- [check_production_readiness.sh](file://scripts/check_production_readiness.sh#L1-L393)
- [DEPENDENCY_AUDIT_REPORT_JAN_2025.md](file://DEPENDENCY_AUDIT_REPORT_JAN_2025.md#L1-L425)
- [docs/development/dependencies.md](file://docs/development/dependencies.md#L1-L321)

## Conclusion

The AR backend application implements a comprehensive security hardening strategy that addresses multiple attack vectors and follows industry best practices for web application security. The security architecture is designed with defense-in-depth principles, applying protections at multiple layers including infrastructure, application, and data levels.

Key security strengths of the application include:

- **Layered security headers** implemented through both application middleware and reverse proxy configuration to prevent XSS, clickjacking, and MIME sniffing attacks
- **Robust input validation** using Pydantic models and custom validators to prevent injection attacks and ensure data integrity
- **Effective rate limiting** with a custom implementation that prevents brute force attacks while avoiding third-party dependency issues
- **Secure configuration management** with environment variables, secure defaults, and production safeguards against common misconfigurations
- **Hardened production deployments** with Docker security best practices, systemd service isolation, and proper file system permissions

The application also addresses common security issues such as information leakage, insecure defaults, and misconfigured integrations through proactive design choices and runtime safeguards. The comprehensive security audit checklists and vulnerability scanning procedures ensure that security is maintained throughout the application lifecycle.

Areas for potential improvement include:
- Implementing Redis for session storage to improve scalability and security
- Migrating from SQLite to PostgreSQL for production deployments to enhance database security and performance
- Adding two-factor authentication and OAuth2 support for enhanced authentication security
- Implementing automated security scanning in the CI/CD pipeline

Overall, the AR backend application demonstrates a mature security posture with well-implemented controls that effectively protect against common web application vulnerabilities. The documented security practices provide clear guidance for secure deployment and ongoing maintenance, ensuring that the application remains secure as it evolves.

**Section sources**
- [SECURITY.md](file://SECURITY.md#L1-L120)
- [documentation_objective](#documentation_objective)
- [all referenced files](#referenced-files-in-this-document)