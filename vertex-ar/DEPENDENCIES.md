# Dependencies Documentation

## Overview
This document provides comprehensive information about the Python dependencies used in the Vertex AR project, their versions, security status, and compatibility requirements.

**Last Updated:** January 2025  
**Python Version:** 3.10+  
**Target Version:** 3.11 (as specified in pyproject.toml)

## Security Audit Results

### ✅ Security Status: PASSED

**Audit Date:** January 2025

- ✅ **pip check:** No broken requirements found
- ✅ **pip-audit:** No vulnerabilities detected
- ⚠️ **safety check:** 2 known issues in transitive dependencies (see Known Issues section)

### Known Security Issues

#### 1. ecdsa Package (Transitive Dependency)
- **Package:** `ecdsa==0.19.1`
- **Source:** Transitive dependency via `python-jose[cryptography]`
- **Vulnerabilities:**
  - CVE-2024-23342 (Minerva side-channel attack)
  - General side-channel vulnerability warning
- **Status:** ⚠️ ACCEPTED RISK
- **Reason:** 
  - No fix versions available from upstream
  - Python does not provide side-channel secure primitives (except hmac.compare_digest())
  - Used only for JWT token signing in controlled environment
  - Risk is minimal in our deployment architecture
- **Mitigation:** 
  - Limited exposure time for tokens
  - TLS/SSL encryption for all communications
  - Regular token rotation

## Critical Dependencies

### Core Web Framework

#### FastAPI (>=0.122.0)
- **Category:** Core Framework
- **Current Version:** 0.122.0
- **Purpose:** Main web framework for REST API
- **Compatibility:** ✅ Python 3.10+, Pydantic v2
- **Notes:** Latest stable version with full Pydantic v2 support

#### Uvicorn (>=0.38.0)
- **Category:** ASGI Server
- **Current Version:** 0.38.0
- **Purpose:** Production-grade ASGI server
- **Compatibility:** ✅ FastAPI 0.122.0+
- **Notes:** Includes standard extras (uvloop, httptools, websockets)

#### Starlette (>=0.50.0)
- **Category:** ASGI Framework
- **Current Version:** 0.50.0
- **Purpose:** FastAPI's underlying ASGI framework
- **Compatibility:** ✅ FastAPI 0.122.0+

### Data Validation (Pydantic v2)

#### Pydantic (>=2.12.0) 🔴 CRITICAL
- **Category:** Data Validation
- **Current Version:** 2.12.5
- **Purpose:** Data validation and settings management
- **Compatibility:** ✅ FastAPI 0.122.0+, Python 3.10+
- **Migration Notes:** 
  - Migrated from Pydantic v1 to v2
  - Breaking changes documented in Pydantic v2 migration guide
  - All models updated to use v2 syntax

#### Pydantic-Core (>=2.18.0) 🔴 CRITICAL
- **Category:** Data Validation Core
- **Current Version:** 2.41.5
- **Purpose:** Core validation logic for Pydantic v2
- **Compatibility:** ✅ Pydantic 2.12.0+
- **Notes:** Rust-based performance improvements

### Database

#### SQLAlchemy (>=2.0.44) 🔴 CRITICAL
- **Category:** ORM
- **Current Version:** 2.0.44
- **Purpose:** Database ORM and query builder
- **Compatibility:** ✅ asyncpg 0.29.0+, Python 3.10+
- **Notes:** 
  - Using SQLAlchemy 2.0 modern async API
  - All models use declarative_base and async sessions

#### asyncpg (>=0.29.0) 🔴 CRITICAL
- **Category:** Database Driver
- **Current Version:** 0.29.0+
- **Purpose:** Async PostgreSQL driver
- **Compatibility:** ✅ SQLAlchemy 2.0+
- **Notes:** High-performance async PostgreSQL driver

### Object Storage

#### MinIO (>=7.2.20)
- **Category:** Storage Client
- **Current Version:** 7.2.20
- **Purpose:** MinIO/S3-compatible object storage client
- **Compatibility:** ✅ boto3 1.26.0+
- **Notes:** Used for remote storage adapter

#### boto3 (>=1.26.0)
- **Category:** AWS SDK
- **Current Version:** 1.26.0+
- **Purpose:** AWS S3 integration
- **Compatibility:** ✅ MinIO 7.2.0+
- **Notes:** S3-compatible storage backend

### Image Processing

#### Pillow (>=12.0.0)
- **Category:** Image Processing
- **Current Version:** 12.0.0
- **Purpose:** NFT marker generation and image processing
- **Security:** ✅ Latest version with security patches
- **Notes:** Critical for portrait processing pipeline

#### OpenCV-Python-Headless (>=4.12.0)
- **Category:** Computer Vision
- **Current Version:** 4.12.0.88
- **Purpose:** Advanced image processing for AR markers
- **Notes:** Headless version (no GUI dependencies)

#### NumPy (>=2.0.0)
- **Category:** Numerical Computing
- **Current Version:** 2.2.6
- **Purpose:** Array operations for image processing
- **Compatibility:** ✅ OpenCV 4.12.0+

#### QRCode[pil] (>=8.0)
- **Category:** QR Code Generation
- **Current Version:** 8.2
- **Purpose:** Generate QR codes for AR experiences
- **Notes:** Includes PIL support for image generation

### Authentication & Security

#### passlib[bcrypt] (>=1.7.4)
- **Category:** Password Hashing
- **Current Version:** 1.7.4
- **Purpose:** Secure password hashing with bcrypt
- **Security:** ✅ Industry standard for password hashing

#### python-jose[cryptography] (>=3.5.0)
- **Category:** JWT Handling
- **Current Version:** 3.5.0
- **Purpose:** JWT token generation and validation
- **Dependencies:** cryptography, ecdsa (transitive)
- **Notes:** See Known Issues for ecdsa vulnerability

### Monitoring & Instrumentation

#### prometheus-fastapi-instrumentator (>=7.1.0)
- **Category:** Monitoring
- **Current Version:** 7.1.0
- **Purpose:** Prometheus metrics for FastAPI
- **Compatibility:** ✅ FastAPI 0.122.0+, Prometheus
- **Notes:** Exposes /metrics endpoint

#### Sentry-SDK (>=2.46.0)
- **Category:** Error Tracking
- **Current Version:** 2.46.0
- **Purpose:** Application error tracking and monitoring
- **Compatibility:** ✅ FastAPI 0.122.0+
- **Notes:** Optional (controlled via environment)

#### structlog (>=25.5.0) 🔴 CRITICAL
- **Category:** Logging
- **Current Version:** 25.5.0
- **Purpose:** Structured logging with JSON output
- **Compatibility:** ✅ Python 3.10+
- **Notes:** Used for all application logging

### HTTP Clients

#### requests (>=2.32.0)
- **Category:** HTTP Client
- **Current Version:** 2.32.4
- **Purpose:** Synchronous HTTP requests
- **Security:** ✅ Latest stable version

#### httpx (>=0.28.0)
- **Category:** Async HTTP Client
- **Current Version:** 0.28.0+
- **Purpose:** Async HTTP requests (testing, external APIs)
- **Compatibility:** ✅ FastAPI 0.122.0+

#### aiohttp (>=3.11.0)
- **Category:** Async HTTP Client
- **Current Version:** 3.11.0+
- **Purpose:** Telegram notifications and async requests
- **Compatibility:** ✅ Python 3.10+

### Task Scheduling

#### APScheduler (>=3.10.0)
- **Category:** Task Scheduler
- **Current Version:** 3.10.0+
- **Purpose:** Background task scheduling (lifecycle checks, backups)
- **Notes:** Used for video scheduler and lifecycle notifications

### Email

#### aiosmtplib (>=3.0.0)
- **Category:** Email Client
- **Current Version:** 3.0.0+
- **Purpose:** Async SMTP client for notifications
- **Notes:** Used for lifecycle notifications to clients

### Other Dependencies

#### Jinja2 (>=3.1.6)
- **Category:** Templating
- **Current Version:** 3.1.6
- **Purpose:** HTML template rendering for admin panel
- **Security:** ✅ Latest stable version

#### python-multipart (>=0.0.20)
- **Category:** Form Parsing
- **Current Version:** 0.0.20
- **Purpose:** Multipart form data parsing for file uploads

#### openpyxl (>=3.1.5)
- **Category:** Excel Processing
- **Current Version:** 3.1.5
- **Purpose:** Excel export for reports

#### docker (>=7.0.0)
- **Category:** Docker Integration
- **Current Version:** 7.0.0+
- **Purpose:** Docker API client for container management

#### slowapi (>=0.1.9)
- **Category:** Rate Limiting
- **Current Version:** 0.1.9
- **Purpose:** Rate limiting for API endpoints

#### psutil (>=7.1.0)
- **Category:** System Monitoring
- **Current Version:** 7.1.3
- **Purpose:** System resource monitoring

## Testing Dependencies

### Core Testing

#### pytest (>=9.0.0)
- **Category:** Testing Framework
- **Current Version:** 9.0.1
- **Purpose:** Main testing framework
- **Plugins:** pytest-cov, pytest-mock, pytest-asyncio, pytest-xdist, pytest-timeout

#### pytest-asyncio (>=1.3.0)
- **Category:** Testing Plugin
- **Current Version:** 1.3.0
- **Purpose:** Async test support

#### pytest-cov (>=7.0.0)
- **Category:** Testing Plugin
- **Current Version:** 7.0.0
- **Purpose:** Code coverage reporting
- **Config:** 80% minimum coverage required

### Performance Testing

#### Locust (>=2.42.0)
- **Category:** Load Testing
- **Current Version:** 2.42.5
- **Purpose:** Load and performance testing

## Development Dependencies

### Code Quality

#### Black (>=25.0.0)
- **Category:** Code Formatter
- **Current Version:** 25.0.0+
- **Purpose:** Automatic code formatting
- **Config:** Line length 127, Python 3.11 target

#### isort (>=7.0.0)
- **Category:** Import Sorter
- **Current Version:** 7.0.0
- **Purpose:** Import statement organization
- **Config:** Black-compatible profile

#### flake8 (>=7.1.0)
- **Category:** Linter
- **Current Version:** 7.1.0+
- **Purpose:** Code style checking

#### mypy (>=1.18.0)
- **Category:** Type Checker
- **Current Version:** 1.18.2
- **Purpose:** Static type checking
- **Config:** Strict mode enabled

#### pre-commit (>=4.5.0)
- **Category:** Git Hooks
- **Current Version:** 4.5.0
- **Purpose:** Pre-commit hook management

### Security Scanning

#### bandit (>=1.8.0)
- **Category:** Security Scanner
- **Current Version:** 1.8.0+
- **Purpose:** Python security issue detection

#### safety (>=3.7.0)
- **Category:** Vulnerability Scanner
- **Current Version:** 3.7.0
- **Purpose:** Known vulnerability detection
- **Notes:** Deprecated `check` command, use `scan` instead

#### pip-audit (>=2.9.0)
- **Category:** Vulnerability Scanner
- **Current Version:** 2.9.0
- **Purpose:** PyPI vulnerability scanning

## Compatibility Matrix

### Python Version Support
- **Minimum:** Python 3.10
- **Recommended:** Python 3.11
- **Tested:** Python 3.10.19

### Key Compatibility Requirements

| Component | Requires | Compatible With |
|-----------|----------|-----------------|
| FastAPI 0.122.0 | Pydantic >=2.0, Starlette >=0.50 | Python 3.10+ |
| Pydantic 2.12.5 | Python 3.10+ | FastAPI 0.104+ |
| SQLAlchemy 2.0.44 | asyncpg 0.29+ | Python 3.10+ |
| structlog 25.5.0 | Python 3.10+ | All versions |
| pytest 9.0.1 | Python 3.10+ | All plugins |

## Update History

### January 2025 - Major Dependency Update
- ✅ Updated FastAPI 0.104.0 → 0.122.0
- ✅ Added explicit Pydantic v2 support (>=2.12.0)
- ✅ Updated SQLAlchemy 2.0.0 → 2.0.44
- ✅ Updated all minimum versions to current secure releases
- ✅ Added boto3 for S3 compatibility
- ✅ Updated testing framework (pytest 7.4.0 → 9.0.1)
- ✅ Updated development tools (black, mypy, etc.)
- ✅ Added pip-audit to security scanning tools
- ✅ Improved requirements.txt organization with categories

### Security Audit Results
- ✅ pip check: PASSED (no conflicts)
- ✅ pip-audit: PASSED (no vulnerabilities)
- ⚠️ safety check: 2 accepted risks in ecdsa (no fix available)

## Installation Instructions

### Production Environment
```bash
pip install -r requirements.txt
```

### Development Environment
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Minimal Installation
```bash
pip install -r requirements-simple.txt
```

## Maintenance Guidelines

### Updating Dependencies
1. Check for security vulnerabilities: `safety scan` and `pip-audit`
2. Check for outdated packages: `pip list --outdated`
3. Update requirements.txt with new minimum versions
4. Run full test suite: `pytest`
5. Check for conflicts: `pip check`
6. Update this documentation

### Security Best Practices
- Run security scans weekly
- Update dependencies monthly
- Monitor CVE databases for critical packages
- Review transitive dependencies
- Document accepted security risks

### Version Pinning Strategy
- Use minimum version constraints (>=) for flexibility
- Pin critical security-sensitive packages to recent versions
- Avoid upper bounds unless necessary for compatibility
- Test thoroughly after updates

## Support & Resources

### Official Documentation
- FastAPI: https://fastapi.tiangolo.com/
- Pydantic: https://docs.pydantic.dev/
- SQLAlchemy: https://docs.sqlalchemy.org/
- structlog: https://www.structlog.org/

### Security Resources
- PyPI Advisory Database: https://pypi.org/project/pip-audit/
- Safety DB: https://pyup.io/safety/
- CVE Database: https://cve.mitre.org/

### Support Contacts
- GitHub Issues: [Repository Issues]
- Security Issues: [Security Policy]

---
**Note:** This document should be updated after every major dependency update or security audit.
