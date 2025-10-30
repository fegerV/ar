# Vertex AR - Testing Summary & Plan

## Executive Summary

Данный документ содержит полную информацию о тестировании приложения Vertex AR, включая текущее состояние, проблемы, планы тестирования и рекомендации.

**Дата:** 2024-01-15  
**Версия:** 1.0.0

---

## 1. Обзор существующих тестов

### 1.1 Тестовые файлы

| # | Файл | Размер | Тесты | Категория | Статус |
|---|------|--------|-------|-----------|--------|
| 1 | test_api_endpoints.py | 18,123 строк | ~50 | Integration | ⚠️ Требует настройки |
| 2 | test_admin_panel.py | 13,826 строк | ~35 | Integration | ⚠️ Требует настройки |
| 3 | test_ar_functionality.py | 7,668 строк | ~20 | Integration | ⚠️ Требует настройки |
| 4 | test_ar_upload_functionality.py | 10,040 строк | ~25 | Integration | ⚠️ Требует настройки |
| 5 | test_ar_upload_simple.py | 7,327 строк | ~15 | Integration | ⚠️ Требует настройки |
| 6 | test_deployment.py | 13,105 строк | ~30 | Deployment | ⚠️ Требует настройки |
| 7 | test_documentation.py | 12,143 строк | ~25 | Documentation | ⚠️ Требует настройки |
| 8 | test_performance.py | 15,578 строк | ~40 | Performance | ⚠️ Требует настройки |
| 9 | test_security.py | 12,508 строк | ~35 | Security | ⚠️ Требует настройки |

**Всего:** 9 файлов, ~110,000 строк кода, ~275 тестов

### 1.2 Покрытие кода

| Модуль | Покрытие | Цель | Статус |
|--------|----------|------|--------|
| main.py | ? | > 70% | ❓ Не измерено |
| auth.py | ? | > 80% | ❓ Не измерено |
| database.py | ? | > 90% | ❓ Не измерено |
| file_validator.py | ? | > 80% | ❓ Не измерено |
| nft_marker_generator.py | ? | > 70% | ❓ Не измерено |
| storage.py | ? | > 80% | ❓ Не измерено |
| **Overall** | **?** | **> 70%** | **❓** |

---

## 2. Проблемы при запуске тестов

### 2.1 Критические проблемы

#### Проблема #1: Отсутствующие директории

**Ошибка:**
```python
RuntimeError: Directory '/home/engine/project/vertex-art-ar/storage' does not exist
```

**Причина:** FastAPI приложение монтирует storage директорию при старте, но она не существует.

**Решение:**
```bash
mkdir -p vertex-art-ar/storage/ar_content
mkdir -p vertex-art-ar/storage/nft-markers
mkdir -p vertex-art-ar/storage/qr-codes
mkdir -p vertex-art-ar/static
mkdir -p vertex-art-ar/templates
```

**Статус:** ✅ Исправлено

---

#### Проблема #2: Отсутствие Jinja2

**Ошибка:**
```python
AssertionError: jinja2 must be installed to use Jinja2Templates
```

**Причина:** jinja2 не указан в requirements.txt

**Решение:**
```bash
pip install jinja2>=3.1.0
# Добавлено в requirements.txt
```

**Статус:** ✅ Исправлено

---

#### Проблема #3: Импорты в тестах

**Ошибка:**
```python
ModuleNotFoundError: No module named 'main'
```

**Причина:** Тесты находятся в корневой директории, но импортируют модули из vertex-art-ar/

**Решение:**

**Вариант 1 (рекомендуемый):** Переместить тесты в vertex-art-ar/tests/
```bash
mkdir -p vertex-art-ar/tests
mv test_*.py vertex-art-ar/tests/
```

**Вариант 2:** Добавить путь в PYTHONPATH
```bash
export PYTHONPATH="${PYTHONPATH}:./vertex-art-ar"
pytest
```

**Вариант 3:** Использовать pytest.ini
```ini
# pytest.ini
[pytest]
pythonpath = vertex-art-ar
```

**Статус:** ⚠️ Требует реорганизации

---

### 2.2 Второстепенные проблемы

#### Проблема #4: Отсутствие conftest.py

**Описание:** Нет централизованного места для фикстур

**Решение:** Создать conftest.py с общими фикстурами

```python
# vertex-art-ar/tests/conftest.py
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from main import app, Database

@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)

@pytest.fixture
def test_db(tmp_path):
    """Test database."""
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    yield db
    # Cleanup
    if db_path.exists():
        db_path.unlink()

@pytest.fixture
def authenticated_client(client):
    """Authenticated test client."""
    # Register and login
    client.post("/auth/register", json={
        "username": "testuser",
        "password": "testpass123"
    })
    response = client.post("/auth/login", json={
        "username": "testuser",
        "password": "testpass123"
    })
    token = response.json()["access_token"]
    
    # Add token to headers
    client.headers["Authorization"] = f"Bearer {token}"
    return client

@pytest.fixture
def storage_dir(tmp_path):
    """Temporary storage directory."""
    storage = tmp_path / "storage"
    storage.mkdir()
    (storage / "ar_content").mkdir()
    (storage / "nft-markers").mkdir()
    (storage / "qr-codes").mkdir()
    return storage

@pytest.fixture
def sample_image(tmp_path):
    """Sample image file for testing."""
    from PIL import Image
    img_path = tmp_path / "test.jpg"
    img = Image.new('RGB', (800, 600), color='red')
    img.save(img_path)
    return img_path

@pytest.fixture
def sample_video(tmp_path):
    """Sample video file for testing."""
    import cv2
    video_path = tmp_path / "test.mp4"
    
    # Create a simple video
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(video_path), fourcc, 20.0, (640, 480))
    
    for _ in range(30):  # 30 frames
        frame = cv2.imread(str(tmp_path / "test.jpg"))
        out.write(frame)
    
    out.release()
    return video_path
```

**Статус:** 📝 Создано в этом документе

---

## 3. План тестирования

### 3.1 Unit Tests

#### 3.1.1 Auth Module (auth.py)

```python
# tests/unit/test_auth.py
import pytest
from auth import hash_password, verify_password, create_token, verify_token

class TestPasswordHashing:
    def test_hash_password(self):
        """Test password hashing."""
        password = "secure_password123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt prefix
    
    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "secure_password123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "secure_password123"
        hashed = hash_password(password)
        
        assert verify_password("wrong_password", hashed) is False
    
    def test_same_password_different_hashes(self):
        """Test that same password produces different hashes (salt)."""
        password = "secure_password123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

class TestTokenManagement:
    def test_create_token(self):
        """Test token creation."""
        token = create_token("testuser")
        
        assert token is not None
        assert len(token) > 20
    
    def test_verify_token_valid(self):
        """Test token verification with valid token."""
        username = "testuser"
        token = create_token(username)
        
        verified_username = verify_token(token)
        assert verified_username == username
    
    def test_verify_token_invalid(self):
        """Test token verification with invalid token."""
        invalid_token = "invalid.token.here"
        
        assert verify_token(invalid_token) is None
```

**Coverage Goal:** > 90%

---

#### 3.1.2 Database Module (database.py)

```python
# tests/unit/test_database.py
import pytest
from database import Database

class TestUserOperations:
    def test_create_user(self, test_db):
        """Test user creation."""
        username = "testuser"
        password_hash = "hashed_password"
        
        test_db.create_user(username, password_hash)
        user = test_db.get_user(username)
        
        assert user is not None
        assert user["username"] == username
        assert user["hashed_password"] == password_hash
        assert user["is_admin"] == 0
    
    def test_create_admin_user(self, test_db):
        """Test admin user creation."""
        username = "admin"
        password_hash = "hashed_password"
        
        test_db.create_user(username, password_hash, is_admin=True)
        user = test_db.get_user(username)
        
        assert user["is_admin"] == 1
    
    def test_create_duplicate_user(self, test_db):
        """Test that duplicate usernames raise error."""
        username = "testuser"
        password_hash = "hashed_password"
        
        test_db.create_user(username, password_hash)
        
        with pytest.raises(ValueError):
            test_db.create_user(username, password_hash)
    
    def test_get_nonexistent_user(self, test_db):
        """Test getting user that doesn't exist."""
        user = test_db.get_user("nonexistent")
        
        assert user is None

class TestARContentOperations:
    def test_create_ar_content(self, test_db):
        """Test AR content creation."""
        # First create a user
        test_db.create_user("testuser", "hash")
        
        content_data = {
            "content_id": "test-123",
            "username": "testuser",
            "image_path": "/path/to/image.jpg",
            "video_path": "/path/to/video.mp4",
            "marker_fset": "/path/to/marker.fset",
            "marker_fset3": "/path/to/marker.fset3",
            "marker_iset": "/path/to/marker.iset",
            "ar_url": "http://localhost:8000/ar/test-123",
            "qr_code": "base64_qr_code"
        }
        
        result = test_db.create_ar_content(**content_data)
        
        assert result is not None
        assert result["id"] == "test-123"
        assert result["username"] == "testuser"
    
    def test_get_ar_content(self, test_db):
        """Test getting AR content."""
        # Setup
        test_db.create_user("testuser", "hash")
        content_data = {...}  # Same as above
        test_db.create_ar_content(**content_data)
        
        # Test
        content = test_db.get_ar_content("test-123")
        
        assert content is not None
        assert content["id"] == "test-123"
    
    def test_list_ar_content(self, test_db):
        """Test listing AR content."""
        # Create multiple contents
        test_db.create_user("user1", "hash")
        test_db.create_user("user2", "hash")
        
        # Create content for each user
        # ...
        
        # Test list all
        all_content = test_db.list_ar_content()
        assert len(all_content) == 2
        
        # Test list by user
        user1_content = test_db.list_ar_content("user1")
        assert len(user1_content) == 1
        assert user1_content[0]["username"] == "user1"
```

**Coverage Goal:** > 95%

---

#### 3.1.3 File Validator (file_validator.py)

```python
# tests/unit/test_file_validator.py
import pytest
from file_validator import FileValidator, FileValidationError

class TestImageValidation:
    def test_validate_valid_jpeg(self, sample_image):
        """Test validation of valid JPEG image."""
        validator = FileValidator()
        
        is_valid, error = validator.validate_image(sample_image)
        
        assert is_valid is True
        assert error is None
    
    def test_validate_too_large_image(self, tmp_path):
        """Test validation fails for too large image."""
        from PIL import Image
        
        # Create a large image
        img_path = tmp_path / "large.jpg"
        img = Image.new('RGB', (10000, 10000))
        img.save(img_path)
        
        validator = FileValidator(max_image_size_mb=1)
        is_valid, error = validator.validate_image(img_path)
        
        assert is_valid is False
        assert "too large" in error.lower()
    
    def test_validate_invalid_format(self, tmp_path):
        """Test validation fails for invalid format."""
        # Create a text file masquerading as image
        fake_img = tmp_path / "fake.jpg"
        fake_img.write_text("This is not an image")
        
        validator = FileValidator()
        is_valid, error = validator.validate_image(fake_img)
        
        assert is_valid is False

class TestVideoValidation:
    def test_validate_valid_mp4(self, sample_video):
        """Test validation of valid MP4 video."""
        validator = FileValidator()
        
        is_valid, error = validator.validate_video(sample_video)
        
        assert is_valid is True
        assert error is None
    
    def test_validate_too_large_video(self):
        """Test validation fails for too large video."""
        # Similar to image test
        pass
```

**Coverage Goal:** > 85%

---

### 3.2 Integration Tests

#### 3.2.1 API Endpoints

```python
# tests/integration/test_api_endpoints.py
import pytest
from fastapi.testclient import TestClient

class TestHealthEndpoints:
    def test_health_check(self, client):
        """Test /health endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert "version" in response.json()
    
    def test_version(self, client):
        """Test /version endpoint."""
        response = client.get("/version")
        
        assert response.status_code == 200
        assert "version" in response.json()
    
    def test_root(self, client):
        """Test / endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        assert "Hello" in response.json()

class TestAuthEndpoints:
    def test_register_success(self, client):
        """Test successful user registration."""
        response = client.post("/auth/register", json={
            "username": "newuser",
            "password": "secure_pass123"
        })
        
        assert response.status_code == 201
        assert response.json()["username"] == "newuser"
    
    def test_register_duplicate(self, client):
        """Test registration with existing username fails."""
        # Register first user
        client.post("/auth/register", json={
            "username": "existinguser",
            "password": "pass123"
        })
        
        # Try to register again
        response = client.post("/auth/register", json={
            "username": "existinguser",
            "password": "different_pass"
        })
        
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()
    
    def test_login_success(self, client):
        """Test successful login."""
        # Register user
        client.post("/auth/register", json={
            "username": "loginuser",
            "password": "pass123"
        })
        
        # Login
        response = client.post("/auth/login", json={
            "username": "loginuser",
            "password": "pass123"
        })
        
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"
    
    def test_login_wrong_password(self, client):
        """Test login with wrong password fails."""
        # Register user
        client.post("/auth/register", json={
            "username": "user",
            "password": "correct_pass"
        })
        
        # Login with wrong password
        response = client.post("/auth/login", json={
            "username": "user",
            "password": "wrong_pass"
        })
        
        assert response.status_code == 401
    
    def test_logout(self, authenticated_client):
        """Test logout."""
        response = authenticated_client.post("/auth/logout")
        
        assert response.status_code == 204

class TestARContentEndpoints:
    def test_upload_ar_content(self, authenticated_client, sample_image, sample_video):
        """Test AR content upload."""
        with open(sample_image, "rb") as img, open(sample_video, "rb") as vid:
            response = authenticated_client.post(
                "/ar/upload",
                files={
                    "image": ("image.jpg", img, "image/jpeg"),
                    "video": ("video.mp4", vid, "video/mp4")
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "ar_url" in data
        assert "qr_code_base64" in data
    
    def test_upload_without_auth(self, client, sample_image, sample_video):
        """Test upload without authentication fails."""
        with open(sample_image, "rb") as img, open(sample_video, "rb") as vid:
            response = client.post(
                "/ar/upload",
                files={
                    "image": ("image.jpg", img, "image/jpeg"),
                    "video": ("video.mp4", vid, "video/mp4")
                }
            )
        
        assert response.status_code == 401
    
    def test_list_ar_content(self, authenticated_client):
        """Test listing AR content."""
        response = authenticated_client.get("/ar/list")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_view_ar_content(self, client, authenticated_client, sample_image, sample_video):
        """Test viewing AR content."""
        # First upload content
        with open(sample_image, "rb") as img, open(sample_video, "rb") as vid:
            upload_response = authenticated_client.post(
                "/ar/upload",
                files={
                    "image": ("image.jpg", img, "image/jpeg"),
                    "video": ("video.mp4", vid, "video/mp4")
                }
            )
        
        content_id = upload_response.json()["id"]
        
        # View content (no auth required)
        response = client.get(f"/ar/{content_id}")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
```

**Coverage Goal:** > 80%

---

### 3.3 End-to-End Tests

```python
# tests/e2e/test_full_workflow.py
import pytest

class TestCompleteARWorkflow:
    """Test complete AR content creation and viewing workflow."""
    
    def test_full_ar_workflow(self, client, sample_image, sample_video):
        """Test complete workflow from registration to AR viewing."""
        
        # 1. Register user
        register_response = client.post("/auth/register", json={
            "username": "e2e_user",
            "password": "e2e_pass123"
        })
        assert register_response.status_code == 201
        
        # 2. Login
        login_response = client.post("/auth/login", json={
            "username": "e2e_user",
            "password": "e2e_pass123"
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # 3. Upload AR content
        headers = {"Authorization": f"Bearer {token}"}
        with open(sample_image, "rb") as img, open(sample_video, "rb") as vid:
            upload_response = client.post(
                "/ar/upload",
                files={
                    "image": ("image.jpg", img, "image/jpeg"),
                    "video": ("video.mp4", vid, "video/mp4")
                },
                headers=headers
            )
        assert upload_response.status_code == 200
        content_id = upload_response.json()["id"]
        ar_url = upload_response.json()["ar_url"]
        
        # 4. List content
        list_response = client.get("/ar/list", headers=headers)
        assert list_response.status_code == 200
        assert len(list_response.json()) >= 1
        
        # 5. View AR content
        view_response = client.get(f"/ar/{content_id}")
        assert view_response.status_code == 200
        
        # 6. Get QR code
        qr_response = client.get(f"/ar/{content_id}/qr")
        assert qr_response.status_code == 200
        
        # 7. Logout
        logout_response = client.post("/auth/logout", headers=headers)
        assert logout_response.status_code == 204
```

---

### 3.4 Performance Tests

```python
# tests/performance/test_load.py
import pytest
from locust import HttpUser, task, between

class ARUploadUser(HttpUser):
    """Simulate AR content upload load."""
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login before starting tasks."""
        response = self.client.post("/auth/login", json={
            "username": "loadtest",
            "password": "loadpass"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def view_ar_content(self):
        """View AR content."""
        self.client.get("/ar/sample-id")
    
    @task(1)
    def list_content(self):
        """List AR content."""
        self.client.get("/ar/list", headers=self.headers)
    
    @task(2)
    def health_check(self):
        """Health check."""
        self.client.get("/health")

# Run with: locust -f tests/performance/test_load.py
```

---

## 4. Метрики и KPI

### 4.1 Coverage Metrics

| Метрика | Текущее | Цель | Статус |
|---------|---------|------|--------|
| Line Coverage | ? | > 70% | ❓ |
| Branch Coverage | ? | > 60% | ❓ |
| Function Coverage | ? | > 80% | ❓ |

### 4.2 Performance Metrics

| Метрика | Текущее | Цель | Статус |
|---------|---------|------|--------|
| API Response Time | ? | < 200ms | ❓ |
| AR Upload Time | ? | < 10s | ❓ |
| NFT Generation Time | ? | < 5s | ❓ |
| Throughput | ? | > 100 req/s | ❓ |

### 4.3 Quality Metrics

| Метрика | Текущее | Цель | Статус |
|---------|---------|------|--------|
| Passing Tests | 0/275 | 275/275 | ❌ |
| Flaky Tests | ? | 0 | ❓ |
| Test Execution Time | ? | < 60s | ❓ |

---

## 5. Roadmap

### Phase 1: Foundation (Week 1)
- [x] Исправить критические ошибки (imports, directories)
- [x] Создать conftest.py с фикстурами
- [ ] Настроить pytest.ini
- [ ] Запустить все существующие тесты
- [ ] Исправить падающие тесты

### Phase 2: Unit Tests (Week 2)
- [ ] Добавить unit tests для auth.py (> 90% coverage)
- [ ] Добавить unit tests для database.py (> 95% coverage)
- [ ] Добавить unit tests для file_validator.py (> 85% coverage)
- [ ] Добавить unit tests для nft_marker_generator.py (> 70% coverage)
- [ ] Добавить unit tests для storage modules (> 80% coverage)

### Phase 3: Integration Tests (Week 3)
- [ ] Добавить API endpoint tests
- [ ] Добавить database integration tests
- [ ] Добавить file upload tests
- [ ] Добавить NFT marker generation tests

### Phase 4: Advanced Testing (Week 4)
- [ ] E2E tests
- [ ] Performance tests
- [ ] Security tests
- [ ] Load tests
- [ ] Stress tests

### Phase 5: CI/CD (Ongoing)
- [ ] Настроить GitHub Actions
- [ ] Автоматические тесты на PR
- [ ] Coverage reporting
- [ ] Performance benchmarks

---

## 6. Best Practices

### 6.1 Naming Conventions

```python
# Test class names
class TestFeatureName:
    pass

# Test method names
def test_should_do_something_when_condition():
    pass

# Fixture names
@pytest.fixture
def authenticated_user():
    pass
```

### 6.2 Test Structure (AAA Pattern)

```python
def test_something():
    # Arrange: Setup test data
    user = User(username="test")
    
    # Act: Execute the code under test
    result = user.login(password="pass")
    
    # Assert: Verify the result
    assert result is True
```

### 6.3 Test Independence

```python
# ✅ GOOD: Each test is independent
def test_create_user():
    db = create_test_db()  # Fresh database
    user = db.create_user("test")
    assert user is not None

# ❌ BAD: Tests depend on each other
shared_db = None

def test_create_user():
    global shared_db
    user = shared_db.create_user("test")

def test_get_user():
    global shared_db
    user = shared_db.get_user("test")  # Depends on previous test
```

---

## 7. Commands

### Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/test_auth.py

# Specific test
pytest tests/test_auth.py::test_password_hashing

# With coverage
pytest --cov=vertex-art-ar --cov-report=html

# Verbose
pytest -v

# Stop on first failure
pytest -x

# Parallel execution
pytest -n auto
```

### Coverage Reports

```bash
# Generate HTML report
pytest --cov=vertex-art-ar --cov-report=html
open htmlcov/index.html

# Generate terminal report
pytest --cov=vertex-art-ar --cov-report=term-missing

# Generate XML (for CI)
pytest --cov=vertex-art-ar --cov-report=xml
```

---

## 8. Resources

### Documentation
- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Locust](https://docs.locust.io/)

### Tools
- pytest - Test framework
- pytest-cov - Coverage plugin
- pytest-xdist - Parallel execution
- locust - Load testing
- httpx - HTTP client for tests

---

**Версия:** 1.0.0  
**Последнее обновление:** 2024-01-15  
**Статус:** 📝 Draft → 🔄 In Progress
