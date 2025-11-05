# Next Steps - Vertex AR v1.1.0

**Last Updated:** 2024-01-15  
**Current Version:** 1.1.0  
**Target Version:** 1.2.0

---

## ✅ Completed in v1.1.0

- [x] Created VERSION file
- [x] Created comprehensive ROADMAP.md
- [x] Created IMPLEMENTATION_STATUS.md
- [x] Created FUNCTIONS_REVIEW.md
- [x] Updated CHANGELOG.md
- [x] Updated README.md with new documentation links
- [x] Established version management system

---

## 🎯 Immediate Actions (This Week)

### 1. Fix Critical Code Issues (Priority: 🔴 CRITICAL)

**Task:** Fix undefined names and critical flake8 errors

```bash
# Run flake8 to see current errors
cd vertex-ar
flake8 --select=F821,F401 *.py

# Expected issues:
# - F821: Undefined name 'Request' (already fixed in main.py)
# - F401: Unused imports

# Action:
# - Remove all unused imports
# - Verify all names are defined
```

**Files to fix:**
- `auth.py` - Remove unused imports
- `database.py` - Format issues
- `file_validator.py` - Whitespace cleanup

**Estimated Time:** 2 hours

---

### 2. Run Code Formatters (Priority: 🔴 CRITICAL)

**Task:** Format all Python files with black and isort

```bash
# Install formatters if not already installed
pip install black isort

# Run black formatter
cd vertex-ar
black *.py
black tests/*.py

# Run isort for import sorting
isort *.py
isort tests/*.py

# Verify no errors
flake8 --max-line-length=120 *.py
```

**Expected Result:**
- All files formatted consistently
- Imports sorted alphabetically
- Line length under 120 characters

**Estimated Time:** 1 hour

---

### 3. Add Rate Limiting (Priority: 🔴 CRITICAL - Security)

**Task:** Implement rate limiting on authentication endpoints

```bash
# Install slowapi
pip install slowapi

# Add to requirements.txt
echo "slowapi>=0.1.9" >> requirements.txt
```

**Code Changes:**

```python
# In main.py, add at top:
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# After app creation:
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Update login endpoint:
@app.post("/api/auth/login")
@limiter.limit("5/minute")
async def login(username: str = Form(...), password: str = Form(...)):
    # existing code...
    pass
```

**Estimated Time:** 2 hours

---

### 4. Configure CORS Properly (Priority: 🔴 CRITICAL - Security)

**Task:** Restrict CORS to specific origins

**Current (INSECURE):**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows ANY origin!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Update to:**
```python
import os

# In .env file, add:
# ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000,https://yourdomain.com

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
```

**Estimated Time:** 1 hour

---

### 5. Create .env.example (Priority: 🟡 HIGH)

**Task:** Document all environment variables

```bash
# Create .env.example in project root
cat > .env.example << 'EOF'
# Vertex AR Configuration Example
# Copy this file to .env and update with your values

# Application
SECRET_KEY=change-me-to-random-string-in-production
DEBUG=False
BASE_URL=http://localhost:8000

# Admin Credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-me-in-production
# OR use hashed password:
# ADMIN_PASSWORD_HASH=$2b$12$...

# JWT Configuration
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Storage Configuration
STORAGE_TYPE=local  # Options: local, minio
STORAGE_PATH=./storage

# MinIO Configuration (if STORAGE_TYPE=minio)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=vertex-art-bucket
MINIO_SECURE=false

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:8000,http://localhost:3000

# Database
DATABASE_URL=sqlite:///./app_data.db

# Optional: Telegram Notifications
TELEGRAM_BOT_TOKEN=your-bot-token-here
TELEGRAM_CHAT_ID=your-chat-id-here
EOF
```

**Estimated Time:** 30 minutes

---

## 🚀 Short Term (Next 2 Weeks)

### 6. Begin main.py Refactoring (Priority: 🔴 HIGH)

**Task:** Split main.py into modular structure

**Target Structure:**
```
vertex-ar/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app initialization
│   ├── config.py            # Configuration management
│   │
│   ├── api/                 # API routes
│   │   ├── __init__.py
│   │   ├── auth.py          # Authentication routes
│   │   ├── ar_content.py    # AR content routes
│   │   ├── clients.py       # Client management
│   │   ├── portraits.py     # Portrait routes
│   │   ├── videos.py        # Video routes
│   │   └── admin.py         # Admin panel routes
│   │
│   ├── core/                # Business logic
│   │   ├── __init__.py
│   │   ├── auth.py          # Auth logic
│   │   ├── nft_generator.py # NFT generation
│   │   └── file_handler.py  # File operations
│   │
│   ├── db/                  # Database
│   │   ├── __init__.py
│   │   ├── database.py      # Database class
│   │   └── models.py        # SQLAlchemy models
│   │
│   └── schemas/             # Pydantic models
│       ├── __init__.py
│       ├── user.py
│       ├── ar_content.py
│       ├── client.py
│       └── portrait.py
│
└── tests/
    ├── conftest.py
    ├── test_api/
    ├── test_core/
    └── test_db/
```

**Phase 1 - Extract Database Class:**
```bash
# 1. Create new structure
mkdir -p vertex-ar/app/db
touch vertex-ar/app/db/__init__.py

# 2. Move Database class from main.py to app/db/database.py
# 3. Update imports in main.py
# 4. Test that everything still works
```

**Estimated Time:** 8 hours over 2 weeks

---

### 7. Add Input Validation (Priority: 🟡 HIGH)

**Task:** Create Pydantic models for all API inputs

**Example:**
```python
# app/schemas/client.py
from pydantic import BaseModel, Field, validator
import re

class CreateClientRequest(BaseModel):
    phone: str = Field(..., description="Client phone number")
    name: str = Field(..., min_length=2, max_length=100)
    
    @validator('phone')
    def validate_phone(cls, v):
        # International phone format
        if not re.match(r'^\+?[1-9]\d{1,14}$', v):
            raise ValueError('Invalid phone format')
        return v

class ClientResponse(BaseModel):
    id: str
    phone: str
    name: str
    created_at: str
    
    class Config:
        from_attributes = True

# Usage in routes:
@app.post("/api/clients", response_model=ClientResponse)
async def create_client(request: CreateClientRequest):
    # Validation happens automatically
    pass
```

**Estimated Time:** 6 hours

---

### 8. Improve Error Handling (Priority: 🟡 HIGH)

**Task:** Standardize error responses

```python
# app/core/exceptions.py
from fastapi import HTTPException, status

class VertexARException(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)

class NotFoundError(VertexARException):
    def __init__(self, resource: str, id: str):
        super().__init__(
            detail=f"{resource} with id '{id}' not found",
            status_code=status.HTTP_404_NOT_FOUND
        )

class ValidationError(VertexARException):
    def __init__(self, detail: str):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

# Usage:
if not content:
    raise NotFoundError("AR Content", content_id)
```

**Estimated Time:** 4 hours

---

### 9. Add Security Headers (Priority: 🟡 HIGH)

**Task:** Add security headers middleware

```python
# In main.py
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

# Add security headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# In production, redirect HTTP to HTTPS
if not DEBUG:
    app.add_middleware(HTTPSRedirectMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["yourdomain.com", "www.yourdomain.com"])
```

**Estimated Time:** 2 hours

---

### 10. Create Test Fixtures (Priority: 🟡 HIGH)

**Task:** Set up pytest with proper fixtures

```python
# tests/conftest.py
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import Database

@pytest.fixture
def test_db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    yield db
    # Cleanup
    if db_path.exists():
        db_path.unlink()

@pytest.fixture
def client(test_db):
    """Create test client."""
    app.state.db = test_db
    return TestClient(app)

@pytest.fixture
def auth_headers(client):
    """Get authentication headers."""
    response = client.post("/api/auth/login", data={
        "username": "admin",
        "password": "secret"
    })
    token = response.cookies.get("access_token")
    return {"Cookie": f"access_token={token}"}

@pytest.fixture
def storage_dir(tmp_path):
    """Create temporary storage directory."""
    storage = tmp_path / "storage"
    storage.mkdir()
    (storage / "ar_content").mkdir()
    (storage / "nft-markers").mkdir()
    return storage

# Usage in tests:
def test_create_client(client, auth_headers):
    response = client.post(
        "/api/clients",
        json={"phone": "+1234567890", "name": "Test User"},
        headers=auth_headers
    )
    assert response.status_code == 200
```

**Estimated Time:** 4 hours

---

## 📅 Medium Term (Next Month)

### 11. Background Job Queue (Priority: 🟡 MEDIUM)

**Task:** Implement async processing for NFT generation

```bash
# Option 1: FastAPI BackgroundTasks (simple)
# Built-in, no extra dependencies

# Option 2: Celery + Redis (production)
pip install celery redis

# Option 3: RQ (lightweight)
pip install rq redis
```

**Example with BackgroundTasks:**
```python
from fastapi import BackgroundTasks

def process_nft_marker(image_path: Path, content_id: str):
    """Background task for NFT generation."""
    generator = NFTMarkerGenerator(STORAGE_ROOT)
    marker = generator.generate_marker(image_path)
    # Update database with marker info
    db.update_ar_content_markers(content_id, marker)

@app.post("/api/ar-content")
async def upload_ar_content(
    background_tasks: BackgroundTasks,
    image: UploadFile,
    video: UploadFile
):
    # Save files
    image_path = save_file(image)
    video_path = save_file(video)
    
    # Create content record with "processing" status
    content = db.create_ar_content(content_id, username, image_path, video_path)
    
    # Process in background
    background_tasks.add_task(process_nft_marker, image_path, content_id)
    
    return {"status": "processing", "id": content_id}
```

**Estimated Time:** 8 hours

---

### 12. Redis Caching (Priority: 🟡 MEDIUM)

**Task:** Add caching layer for frequently accessed data

```bash
pip install redis fastapi-cache2
```

**Implementation:**
```python
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from redis import asyncio as aioredis

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://localhost:6379")
    FastAPICache.init(RedisBackend(redis), prefix="vertex-ar:")

@app.get("/api/ar-content/{content_id}")
@cache(expire=3600)  # Cache for 1 hour
async def get_ar_content(content_id: str):
    return db.get_ar_content(content_id)
```

**Estimated Time:** 6 hours

---

### 13. Comprehensive Testing (Priority: 🟡 MEDIUM)

**Task:** Achieve >70% test coverage

```bash
# Install coverage tool
pip install pytest-cov

# Run tests with coverage
pytest --cov=vertex-ar --cov-report=html

# Target coverage:
# - Unit tests: >70%
# - Integration tests: >50%
# - E2E tests: Critical paths
```

**Areas to test:**
- All API endpoints
- Database operations
- File upload/validation
- NFT marker generation
- Authentication/authorization
- Error handling

**Estimated Time:** 20 hours

---

### 14. CI/CD Pipeline (Priority: 🟡 MEDIUM)

**Task:** Set up automated testing and deployment

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: pytest --cov=vertex-ar
      
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install black flake8 isort
      - run: black --check vertex-ar/
      - run: flake8 vertex-ar/
      - run: isort --check-only vertex-ar/
```

**Estimated Time:** 4 hours

---

## 📊 Progress Tracking

### Week 1 Goals
- [ ] Fix critical flake8 errors
- [ ] Run black and isort formatters
- [ ] Add rate limiting
- [ ] Configure CORS
- [ ] Create .env.example

### Week 2 Goals
- [ ] Begin main.py refactoring
- [ ] Add input validation
- [ ] Improve error handling
- [ ] Add security headers
- [ ] Create test fixtures

### Month 1 Goals
- [ ] Complete main.py refactoring
- [ ] Implement background jobs
- [ ] Add Redis caching
- [ ] Achieve >70% test coverage
- [ ] Set up CI/CD

---

## 🎯 Success Criteria

### Version 1.2.0 Release
- ✅ All critical flake8 errors fixed
- ✅ Code formatted with black
- ✅ Rate limiting implemented
- ✅ CORS properly configured
- ✅ main.py refactored into modules
- ✅ Input validation with Pydantic
- ✅ Comprehensive error handling
- ✅ Test coverage >70%

---

## 📝 Notes

- Keep IMPLEMENTATION_STATUS.md updated as tasks are completed
- Update CHANGELOG.md for each change
- Test thoroughly after each change
- Commit small, focused changes
- Write clear commit messages

---

## 🤝 Need Help?

- Review [FUNCTIONS_REVIEW.md](./FUNCTIONS_REVIEW.md) for detailed code improvement guidance
- Check [ROADMAP.md](./ROADMAP.md) for long-term planning
- See [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) for current status

---

**Last Updated:** 2024-01-15  
**Next Review:** 2024-01-22
