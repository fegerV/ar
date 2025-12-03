# Application Settings

<cite>
**Referenced Files in This Document**   
- [.env.example](file://.env.example)
- [.env.production.example](file://.env.production.example)
- [app/config.py](file://vertex-ar/app/config.py)
- [app/main.py](file://vertex-ar/app/main.py)
- [app/api/health.py](file://vertex-ar/app/api/health.py)
- [app/monitoring.py](file://vertex-ar/app/monitoring.py)
- [app/api/ar.py](file://vertex-ar/app/api/ar.py)
- [VERSION](file://vertex-ar/VERSION)
- [docs/monitoring/web-health-check.md](file://docs/monitoring/web-health-check.md)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Core Environment Variables](#core-environment-variables)
3. [Security Configuration](#security-configuration)
4. [Network and Deployment Settings](#network-and-deployment-settings)
5. [Health Check and Monitoring Configuration](#health-check-and-monitoring-configuration)
6. [Practical Configuration Examples](#practical-configuration-examples)
7. [Troubleshooting Common Issues](#troubleshooting-common-issues)
8. [Best Practices for Production](#best-practices-for-production)

## Introduction
This document provides comprehensive documentation for the application-level environment variables in the Vertex AR system. The configuration system is designed to support both development and production environments with appropriate security measures and performance optimizations. The environment variables control critical aspects of the application including security, network binding, AR content generation, and monitoring systems. Understanding these settings is essential for proper deployment, security, and operation of the Vertex AR platform.

**Section sources**
- [.env.example](file://.env.example#L1-L339)
- [.env.production.example](file://.env.production.example#L1-L93)

## Core Environment Variables

The Vertex AR system uses environment variables to configure its behavior across different deployment environments. These variables are loaded from `.env` files and provide flexibility for development, staging, and production deployments.

### DEBUG Mode
The DEBUG variable controls the application's debug mode, which affects error reporting and development features.

**Purpose**: When set to `True`, the application provides detailed error messages and enables development features like automatic code reloading. In production, this should always be set to `False` to prevent information disclosure.

**Security Implications**: Enabling debug mode in production can expose sensitive system information, stack traces, and potentially reveal implementation details that could be exploited by attackers.

**Production Requirements**: Must be disabled (`DEBUG=False`) in production environments to ensure proper error handling and security.

### SECRET_KEY for JWT Security
The SECRET_KEY is used for signing JSON Web Tokens (JWT) that authenticate users and maintain session security.

**Purpose**: This key is critical for the cryptographic signing of authentication tokens. It ensures that tokens cannot be forged or tampered with.

**Security Implications**: Using a weak or predictable secret key compromises the entire authentication system. The default value in the example file (`change-this-to-a-secure-random-key-in-production`) must be replaced with a cryptographically secure random key.

**Production Requirements**: Generate a secure random key using a command like `python -c "import secrets; print(secrets.token_urlsafe(32))"` and store it securely. Never commit this key to version control.

### APP_HOST and APP_PORT
These variables control the network interface and port on which the application binds.

**Purpose**: APP_HOST specifies the network interface to bind to (e.g., `0.0.0.0` for all interfaces, `127.0.0.1` for localhost only). APP_PORT specifies the TCP port number for the web server.

**Common Issues**: Incorrect host configuration can prevent external access, while port conflicts can prevent the application from starting. Ensure the specified port is not already in use by another service.

### BASE_URL for AR Content Generation
The BASE_URL is used to generate absolute URLs for AR content, QR codes, and other public-facing resources.

**Purpose**: This URL forms the base for all generated AR content links, QR codes, and public resource references. It must be accessible to end-users' devices.

**AR Content Generation**: When creating AR experiences, the system combines BASE_URL with specific paths to create complete URLs for accessing content. For example, an AR experience might be accessible at `${BASE_URL}/ar/{content_id}`.

**Common Issues**: Incorrect BASE_URL settings result in broken AR links and non-functional QR codes. If using HTTPS, ensure the BASE_URL reflects the secure protocol.

### ENVIRONMENT for Deployment Context
While not explicitly defined in the example files, the environment context is inferred from other settings and affects application behavior.

**Purpose**: Different deployment contexts (development, staging, production) require different configurations for security, logging, and performance.

**Configuration Impact**: The environment affects settings like debug mode, error reporting, and monitoring thresholds. Production environments should have stricter security settings and more comprehensive monitoring.

**Section sources**
- [.env.example](file://.env.example#L8-L26)
- [app/config.py](file://vertex-ar/app/config.py#L35-L40)
- [app/main.py](file://vertex-ar/app/main.py#L90-L91)

## Security Configuration

The Vertex AR system implements multiple security measures through environment variable configuration to protect against common vulnerabilities and ensure secure operation.

### JWT Token Security
The SECRET_KEY environment variable is fundamental to the application's authentication security.

**Implementation**: The key is used by the TokenManager class to sign and verify JWT tokens. These tokens are issued upon successful authentication and used to maintain user sessions.

**Key Management**: The system warns against using predictable keys and provides guidance for generating cryptographically secure random keys. The key should be at least 32 bytes long and generated using a secure random number generator.

**Security Best Practices**: Rotate the secret key periodically in production, especially if a security incident is suspected. Store the key in a secure secrets management system rather than in files when possible.

### CORS Configuration
Cross-Origin Resource Sharing (CORS) settings control which domains can access the API.

**Purpose**: CORS prevents unauthorized websites from making requests to the API, protecting against cross-site request forgery (CSRF) attacks.

**Configuration**: The CORS_ORIGINS variable accepts a comma-separated list of allowed origins. In development, this might be set to `*` for convenience, but in production, it should list only trusted domains.

**Security Implications**: Overly permissive CORS settings can expose the API to unauthorized access from malicious websites. Always specify exact domains in production rather than using wildcards.

### SMTP Credential Security
The system includes security measures for email configuration to prevent credential exposure.

**Deprecation Warning**: The documentation explicitly states that SMTP_USERNAME and SMTP_PASSWORD environment variables are deprecated and insecure. These should not be used in production.

**Secure Alternative**: SMTP credentials should be configured through the admin UI at `/admin/notification-settings` where they can be stored encrypted in the database.

**Production Enforcement**: The application will refuse to start in production if SMTP credentials are detected in environment variables, preventing accidental exposure.

**Section sources**
- [.env.example](file://.env.example#L118-L129)
- [app/config.py](file://vertex-ar/app/config.py#L81-L113)
- [.env.example](file://.env.example#L160-L168)

## Network and Deployment Settings

The network configuration variables control how the application binds to network interfaces and how external systems can access its services.

### Network Binding Configuration
The APP_HOST and APP_PORT variables determine the network interface and port for the web server.

**Binding Options**: 
- `APP_HOST=0.0.0.0` binds to all available network interfaces, making the service accessible from external networks.
- `APP_HOST=127.0.0.1` binds only to the loopback interface, restricting access to the local machine.

**Port Selection**: The default APP_PORT is 8000, but this can be changed to any available port. Common alternatives include 80 (HTTP) or 443 (HTTPS) when running without a reverse proxy.

**Firewall Considerations**: Ensure that the selected port is open in any firewalls or security groups protecting the server.

### Version Management
The VERSION file provides version information that is exposed through the API.

**Implementation**: The application reads the VERSION file from the root directory and exposes this information through the `/version` endpoint. If the file is not found, a default version is used.

**Usage**: This allows administrators and monitoring systems to verify which version of the application is running, facilitating version tracking and update management.

**Section sources**
- [app/config.py](file://vertex-ar/app/config.py#L28-L32)
- [app/api/health.py](file://vertex-ar/app/api/health.py#L16-L17)
- [VERSION](file://vertex-ar/VERSION#L1-L2)

## Health Check and Monitoring Configuration

The monitoring system uses specific environment variables to ensure reliable health checks and prevent false alerts in complex deployment scenarios.

### INTERNAL_HEALTH_URL Configuration
The INTERNAL_HEALTH_URL provides an alternative endpoint for health monitoring when the public BASE_URL has connectivity issues.

**Purpose**: In production deployments, the BASE_URL might point to an external domain with TLS/SSL certificates, load balancers, or rate limiting that could interfere with health checks. The INTERNAL_HEALTH_URL allows monitoring systems to check the application's health directly through the internal network.

**Implementation**: The monitoring system attempts health checks in the following priority order:
1. INTERNAL_HEALTH_URL (if configured)
2. BASE_URL (public URL)
3. localhost fallback (`http://localhost:{APP_PORT}/health`)
4. 127.0.0.1 fallback (`http://127.0.0.1:{APP_PORT}/health`)

**Best Practice**: In production, set INTERNAL_HEALTH_URL to `http://localhost:8000` or `http://127.0.0.1:8000` to ensure reliable health checks that aren't affected by external network conditions.

### Monitoring System Behavior
The health check system provides detailed diagnostics to distinguish between different types of failures.

**Status Determination**:
- **Operational**: At least one URL returns HTTP 200
- **Degraded**: All HTTP attempts fail, but the process is running and the port is accepting connections
- **Failed**: All HTTP attempts fail, and the process is not running or the port is not accepting connections

**Diagnostic Information**: The system captures detailed information about each health check attempt, including response times, error messages, and process/port status, helping administrators diagnose the root cause of issues.

**Section sources**
- [.env.example](file://.env.example#L22-L26)
- [app/config.py](file://vertex-ar/app/config.py#L37-L38)
- [docs/monitoring/web-health-check.md](file://docs/monitoring/web-health-check.md#L68-L76)
- [app/monitoring.py](file://vertex-ar/app/monitoring.py#L947-L968)

## Practical Configuration Examples

### Development Environment Configuration
A typical development `.env` file includes permissive settings for ease of development:

```env
DEBUG=True
SECRET_KEY=change-this-to-a-secure-random-key-in-production
APP_HOST=0.0.0.0
APP_PORT=8000
BASE_URL=http://localhost:8000
INTERNAL_HEALTH_URL=
CORS_ORIGINS=*
```

**Characteristics**: This configuration enables debug mode, uses a placeholder secret key (which should never be used in production), binds to all interfaces, and allows CORS from any origin. The BASE_URL points to localhost, suitable for development testing.

### Production Environment Configuration
The production configuration prioritizes security and reliability:

```env
DEBUG=False
SECRET_KEY=CHANGE-THIS-TO-SECURE-RANDOM-KEY-IN-PRODUCTION
APP_HOST=0.0.0.0
APP_PORT=8000
BASE_URL=https://yourdomain.com
INTERNAL_HEALTH_URL=http://localhost:8000
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
RATE_LIMIT_ENABLED=True
```

**Characteristics**: Debug mode is disabled, a secure random secret key is required, and CORS is restricted to trusted domains. The INTERNAL_HEALTH_URL is configured for reliable monitoring, and rate limiting is enabled to protect against abuse.

**Section sources**
- [.env.example](file://.env.example#L8-L26)
- [.env.production.example](file://.env.production.example#L8-L13)

## Troubleshooting Common Issues

### Connection and Network Issues
**Symptoms**: Application fails to start, or clients cannot connect to the service.

**Causes and Solutions**:
- **Port in use**: Another process is using the configured APP_PORT. Check with `netstat -tlnp | grep <port>` and either stop the conflicting service or change APP_PORT.
- **Host binding issues**: If APP_HOST is set to `127.0.0.1`, the service will only accept local connections. Change to `0.0.0.0` to allow external access.
- **Firewall blocking**: Ensure the configured port is open in any firewalls or security groups.

### AR Content and URL Issues
**Symptoms**: QR codes don't work, or AR content cannot be accessed.

**Causes and Solutions**:
- **Incorrect BASE_URL**: If BASE_URL doesn't match the actual domain and protocol, generated URLs will be incorrect. Verify that BASE_URL includes the correct protocol (http:// or https://) and domain.
- **HTTPS configuration**: If using HTTPS, ensure that the reverse proxy or web server is properly configured to handle SSL/TLS termination.
- **Network accessibility**: Verify that the BASE_URL is accessible from external networks, not just locally.

### Security Configuration Issues
**Symptoms**: Application refuses to start, or security warnings are displayed.

**Causes and Solutions**:
- **Insecure SMTP credentials**: Remove SMTP_USERNAME and SMTP_PASSWORD from environment variables and configure SMTP through the admin UI instead.
- **Weak SECRET_KEY**: Generate a secure random key using the recommended command and update the environment variable.
- **Debug mode in production**: Set DEBUG=False in production environments to prevent information disclosure.

**Section sources**
- [.env.example](file://.env.example#L328-L339)
- [app/config.py](file://vertex-ar/app/config.py#L81-L113)

## Best Practices for Production

### Security Hardening
- **Disable debug mode**: Always set `DEBUG=False` in production to prevent detailed error messages from being exposed.
- **Use secure random keys**: Generate a strong SECRET_KEY using `python -c "import secrets; print(secrets.token_urlsafe(32))"` and store it securely.
- **Restrict CORS origins**: Specify exact domains in CORS_ORIGINS rather than using wildcards.
- **Enable rate limiting**: Set `RATE_LIMIT_ENABLED=True` to protect against abuse and denial-of-service attacks.

### Monitoring and Reliability
- **Configure INTERNAL_HEALTH_URL**: Set this to `http://localhost:8000` or `http://127.0.0.1:8000` to ensure reliable health checks that aren't affected by external network conditions.
- **Enable comprehensive logging**: Configure appropriate log levels and ensure logs are stored securely and rotated regularly.
- **Set up alerting**: Configure Telegram and email notifications for critical system alerts.

### Deployment and Maintenance
- **Use version control**: Never commit `.env` files to version control. Use `.env.example` as a template.
- **Regular backups**: Enable and test the automated backup system to protect against data loss.
- **Update management**: Monitor the VERSION file and update procedures to ensure smooth version upgrades.

**Section sources**
- [.env.example](file://.env.example#L328-L339)
- [.env.production.example](file://.env.production.example#L71-L93)