# Vertex AR - Developer Guide

## Оглавление

1. [Введение](#введение)
2. [Настройка окружения разработки](#настройка-окружения-разработки)
3. [Структура проекта](#структура-проекта)
4. [Соглашения о кодировании](#соглашения-о-кодировании)
5. [Workflow разработки](#workflow-разработки)
6. [Тестирование](#тестирование)
7. [Отладка](#отладка)
8. [Добавление новых функций](#добавление-новых-функций)
9. [Contributing Guidelines](#contributing-guidelines)
10. [Troubleshooting](#troubleshooting)

---

## Введение

Это руководство для разработчиков, работающих над проектом Vertex AR. Здесь описаны все необходимые шаги для начала разработки, стандарты кодирования и best practices.

### Предварительные требования

- Python 3.11 или выше
- Git
- Docker и Docker Compose (опционально)
- Node.js 16+ (для frontend разработки)
- Базовые знания FastAPI, SQLAlchemy, A-Frame

---

## Настройка окружения разработки

### 1. Клонирование репозитория

```bash
git clone https://github.com/your-org/vertex-ar.git
cd vertex-ar
```

### 2. Создание виртуального окружения

```bash
# Linux/macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

### 3. Установка зависимостей

```bash
# Production зависимости
pip install -r vertex-art-ar/requirements.txt

# Development зависимости
pip install pytest pytest-asyncio pytest-cov flake8 pylint mypy black isort httpx
```

### 4. Настройка переменных окружения

Создайте файл `.env` в директории `vertex-art-ar/`:

```bash
cp vertex-art-ar/.env.example vertex-art-ar/.env
```

Отредактируйте `.env`:

```env
# Application
DEBUG=True
SECRET_KEY=your-secret-key-here
APP_HOST=0.0.0.0
APP_PORT=8000

# Database
DATABASE_URL=sqlite:///./app_data.db

# Storage
STORAGE_TYPE=local
STORAGE_PATH=./storage

# MinIO (optional)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=vertex-ar

# Logging
LOG_LEVEL=INFO
```

### 5. Создание необходимых директорий

```bash
cd vertex-art-ar
mkdir -p storage static templates
mkdir -p storage/ar_content storage/nft-markers storage/qr-codes
```

### 6. Инициализация базы данных

```bash
python -c "from main import database; print('Database initialized')"
```

### 7. Запуск приложения

```bash
# Development mode
python main.py

# С автоперезагрузкой
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Приложение будет доступно по адресу: http://localhost:8000

### 8. Настройка IDE

#### VS Code

Установите расширения:
- Python
- Pylance
- Python Test Explorer
- Docker (optional)

Создайте `.vscode/settings.json`:

```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

#### PyCharm

1. Настройте Python interpreter → выберите `.venv`
2. Enable: Settings → Tools → Python Integrated Tools → Testing → pytest
3. Enable: Settings → Editor → Code Style → Python → Set from → PEP 8

---

## Структура проекта

```
vertex-ar/
├── vertex-art-ar/                 # Основное приложение
│   ├── main.py                   # FastAPI application
│   ├── auth.py                   # Authentication module
│   ├── database.py               # Database layer
│   ├── models.py                 # SQLAlchemy models
│   ├── file_validator.py        # File validation
│   ├── nft_marker_generator.py  # NFT marker generation
│   ├── storage.py                # Storage abstraction
│   ├── storage_local.py          # Local storage implementation
│   ├── preview_generator.py      # Preview generation
│   ├── notification_handler.py   # Notifications
│   ├── notifications.py          # Notification models
│   ├── utils.py                  # Utility functions
│   ├── requirements.txt          # Python dependencies
│   ├── .env                      # Environment variables (не коммитить!)
│   │
│   ├── templates/                # Jinja2 templates
│   │   ├── admin.html
│   │   ├── ar_viewer.html
│   │   └── ar_viewer_animated.html
│   │
│   ├── storage/                  # File storage (не коммитить!)
│   │   ├── ar_content/
│   │   ├── nft-markers/
│   │   └── qr-codes/
│   │
│   └── tests/                    # Unit tests
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_database.py
│       └── ...
│
├── test_*.py                      # Integration tests (root level)
├── API_DOCUMENTATION.md           # API docs
├── ARCHITECTURE.md                # Architecture docs
├── DEVELOPER_GUIDE.md             # This file
├── TASK_BREAKDOWN.md              # Task breakdown
├── README.md                      # Main readme
├── CHANGELOG.md                   # Change log
├── docker-compose.yml             # Docker compose
├── Dockerfile.app                 # App dockerfile
└── .gitignore                     # Git ignore
```

### Модули и их назначение

| Модуль | Назначение | Зависимости |
|--------|-----------|-------------|
| `main.py` | FastAPI app, routing, middleware | auth, database, storage |
| `auth.py` | Authentication, password hashing | passlib, python-jose |
| `database.py` | Database operations | sqlite3, threading |
| `models.py` | SQLAlchemy models | sqlalchemy |
| `file_validator.py` | File validation | python-magic, pathlib |
| `nft_marker_generator.py` | NFT marker generation | opencv, numpy, pillow |
| `storage.py` | Storage interface | - |
| `storage_local.py` | Local storage impl | pathlib |
| `preview_generator.py` | Image/video previews | pillow, opencv |
| `notification_handler.py` | Notifications | requests |
| `utils.py` | Utility functions | - |

---

## Соглашения о кодировании

### Python Style Guide

Следуем **PEP 8** с некоторыми дополнениями:

#### Общие правила

1. **Длина строки**: Максимум 120 символов
2. **Отступы**: 4 пробела (не табы)
3. **Кодировка**: UTF-8
4. **Импорты**: Группировать и сортировать
5. **Docstrings**: Google style

#### Именование

```python
# Переменные и функции: snake_case
user_name = "John"
def get_user_data():
    pass

# Классы: PascalCase
class UserManager:
    pass

# Константы: UPPER_SNAKE_CASE
MAX_FILE_SIZE = 10 * 1024 * 1024

# Приватные: _leading_underscore
def _internal_function():
    pass
```

#### Импорты

```python
# Порядок импортов:
# 1. Standard library
import os
import sys
from pathlib import Path

# 2. Third-party
from fastapi import FastAPI, HTTPException
import numpy as np

# 3. Local
from auth import verify_password
from database import Database
```

#### Type Hints

Используйте type hints для всех функций:

```python
from typing import Optional, List, Dict, Any

def create_user(
    username: str,
    password: str,
    is_admin: bool = False
) -> Dict[str, Any]:
    """Create a new user.
    
    Args:
        username: The username
        password: Plain text password
        is_admin: Whether user is admin
        
    Returns:
        User dictionary with metadata
        
    Raises:
        ValueError: If username already exists
    """
    pass
```

#### Docstrings

**Google Style Docstrings:**

```python
def upload_ar_content(
    image_path: str,
    video_path: str,
    config: NFTMarkerConfig
) -> ARContentResponse:
    """Upload and process AR content.
    
    This function handles the complete workflow of uploading AR content:
    - Validates files
    - Generates NFT markers
    - Creates QR codes
    - Stores in database
    
    Args:
        image_path: Path to the portrait image
        video_path: Path to the animation video
        config: NFT marker generation configuration
        
    Returns:
        ARContentResponse with content ID and URLs
        
    Raises:
        HTTPException: If file validation fails
        ValueError: If marker generation fails
        
    Example:
        >>> config = NFTMarkerConfig(feature_density="high")
        >>> result = upload_ar_content("image.jpg", "video.mp4", config)
        >>> print(result.ar_url)
        http://localhost:8000/ar/abc-123
    """
    pass
```

#### Error Handling

```python
# Используйте специфичные exceptions
try:
    user = database.get_user(username)
except sqlite3.DatabaseError as e:
    logger.error(f"Database error: {e}")
    raise HTTPException(
        status_code=500,
        detail="Database error occurred"
    )

# Не используйте bare except
# BAD
try:
    do_something()
except:  # Плохо!
    pass

# GOOD
try:
    do_something()
except ValueError as e:
    logger.error(f"Value error: {e}")
    raise
```

#### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Используйте правильные уровни
logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical error")

# F-strings для formatting
logger.info(f"User {username} logged in successfully")

# Не логируйте секреты!
# BAD
logger.info(f"Password: {password}")  # Никогда!

# GOOD
logger.info(f"User {username} authenticated")
```

---

## Workflow разработки

### Git Workflow

Используем **Git Flow**:

```
main (production)
  ↓
develop (development)
  ↓
feature/feature-name (new features)
hotfix/bug-name (urgent fixes)
```

#### Создание feature branch

```bash
# Синхронизация с develop
git checkout develop
git pull origin develop

# Создание feature branch
git checkout -b feature/add-video-filters

# Работа над feature
# ... делаем изменения ...
git add .
git commit -m "feat: add video filter functionality"

# Push в remote
git push origin feature/add-video-filters
```

#### Commit Messages

Следуем **Conventional Commits**:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: Новая функциональность
- `fix`: Исправление бага
- `docs`: Изменения в документации
- `style`: Форматирование, пробелы (не влияет на код)
- `refactor`: Рефакторинг кода
- `test`: Добавление тестов
- `chore`: Обновление зависимостей, конфигурации

**Примеры:**

```bash
git commit -m "feat(auth): add two-factor authentication"
git commit -m "fix(database): prevent SQL injection in user queries"
git commit -m "docs(api): update authentication endpoint documentation"
git commit -m "test(nft): add unit tests for marker generation"
git commit -m "refactor(storage): extract storage interface"
```

#### Pull Request Process

1. **Создайте PR** с описанием изменений
2. **Заполните template**:
   ```markdown
   ## Description
   Brief description of changes
   
   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Breaking change
   
   ## Testing
   - [ ] Unit tests pass
   - [ ] Integration tests pass
   - [ ] Manual testing completed
   
   ## Checklist
   - [ ] Code follows style guide
   - [ ] Documentation updated
   - [ ] No console warnings
   ```
3. **Request review** от минимум 1 разработчика
4. **Address feedback** и делайте изменения
5. **Merge** после approval

---

## Тестирование

### Unit Tests

```bash
# Запуск всех тестов
pytest

# Конкретный файл
pytest tests/test_auth.py

# Конкретный тест
pytest tests/test_auth.py::test_password_hashing

# С coverage
pytest --cov=vertex-art-ar --cov-report=html

# Verbose mode
pytest -v

# Stop on first failure
pytest -x
```

### Написание тестов

```python
# tests/test_auth.py
import pytest
from auth import hash_password, verify_password

def test_password_hashing():
    """Test password hashing and verification."""
    password = "secure_password123"
    hashed = hash_password(password)
    
    # Check hash is not plain text
    assert hashed != password
    
    # Check verification works
    assert verify_password(password, hashed) is True
    
    # Check wrong password fails
    assert verify_password("wrong_password", hashed) is False


@pytest.fixture
def test_database():
    """Create a test database."""
    db = Database(":memory:")
    yield db
    # Cleanup if needed


def test_create_user(test_database):
    """Test user creation."""
    username = "testuser"
    password = "testpass"
    
    test_database.create_user(username, password)
    user = test_database.get_user(username)
    
    assert user is not None
    assert user["username"] == username
```

### Integration Tests

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_register_and_login():
    """Test user registration and login flow."""
    # Register
    register_data = {
        "username": "testuser",
        "password": "testpass123"
    }
    response = client.post("/auth/register", json=register_data)
    assert response.status_code == 201
    
    # Login
    response = client.post("/auth/login", json=register_data)
    assert response.status_code == 200
    assert "access_token" in response.json()
```

### Test Coverage Goals

- **Unit tests**: > 70% coverage
- **Integration tests**: > 50% coverage
- **Critical paths**: 100% coverage

---

## Отладка

### Logging

```python
# Включить debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# В main.py
logger.debug(f"Processing file: {filename}")
logger.debug(f"Database query: {query}")
```

### Python Debugger

```python
# Вставить breakpoint
import pdb; pdb.set_trace()

# Или в Python 3.7+
breakpoint()
```

**Команды pdb:**
```
n - next line
s - step into
c - continue
p variable - print variable
l - list code
q - quit
```

### VS Code Debugger

Создайте `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "main:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
      ],
      "jinja": true,
      "justMyCode": false
    }
  ]
}
```

### FastAPI Debugging

```python
# Включить debug mode
app = FastAPI(debug=True)

# Automatic interactive docs
# http://localhost:8000/docs
# http://localhost:8000/redoc
```

---

## Добавление новых функций

### Добавление нового API endpoint

1. **Определите модель данных** (если нужно):

```python
# main.py
class NewFeatureRequest(BaseModel):
    param1: str
    param2: int
    param3: Optional[bool] = False
```

2. **Создайте endpoint**:

```python
@app.post("/api/new-feature", tags=["features"])
async def new_feature(
    request: NewFeatureRequest,
    username: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Description of new feature.
    
    Args:
        request: Request parameters
        username: Authenticated user
        
    Returns:
        Response with results
    """
    # Validation
    if not request.param1:
        raise HTTPException(
            status_code=400,
            detail="param1 is required"
        )
    
    # Business logic
    result = process_feature(request)
    
    # Database operation
    database.save_feature(result)
    
    return {"status": "success", "data": result}
```

3. **Добавьте тесты**:

```python
def test_new_feature():
    """Test new feature endpoint."""
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    data = {
        "param1": "value1",
        "param2": 42
    }
    
    response = client.post(
        "/api/new-feature",
        json=data,
        headers=headers
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
```

4. **Обновите документацию**:

Добавьте описание в `API_DOCUMENTATION.md`

### Добавление нового модуля

1. **Создайте файл**:

```python
# new_module.py
"""
Module for new functionality.
"""
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class NewFeature:
    """Handle new feature operations."""
    
    def __init__(self, config: dict):
        """
        Initialize feature.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        logger.info("NewFeature initialized")
    
    def process(self, data: str) -> Optional[str]:
        """
        Process data.
        
        Args:
            data: Input data
            
        Returns:
            Processed result or None if error
        """
        try:
            result = self._internal_process(data)
            return result
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            return None
    
    def _internal_process(self, data: str) -> str:
        """Internal processing logic."""
        return data.upper()
```

2. **Добавьте тесты**:

```python
# tests/test_new_module.py
import pytest
from new_module import NewFeature


@pytest.fixture
def feature():
    """Create feature instance."""
    config = {"key": "value"}
    return NewFeature(config)


def test_process(feature):
    """Test processing."""
    result = feature.process("hello")
    assert result == "HELLO"


def test_process_error(feature, monkeypatch):
    """Test error handling."""
    def mock_process(self, data):
        raise ValueError("Test error")
    
    monkeypatch.setattr(
        NewFeature,
        "_internal_process",
        mock_process
    )
    
    result = feature.process("hello")
    assert result is None
```

---

## Contributing Guidelines

### Code Review Checklist

**Reviewer должен проверить:**

- [ ] Код следует style guide
- [ ] Есть docstrings для всех публичных функций
- [ ] Есть type hints
- [ ] Есть unit tests (coverage > 70%)
- [ ] Тесты проходят
- [ ] Нет hardcoded секретов
- [ ] Нет console.log/print statements
- [ ] Обновлена документация
- [ ] Нет breaking changes (или они документированы)
- [ ] Performance: нет N+1 queries, утечек памяти

### Before Submitting PR

```bash
# 1. Форматирование
black vertex-art-ar/*.py

# 2. Импорты
isort vertex-art-ar/*.py

# 3. Linting
flake8 vertex-art-ar/

# 4. Type checking
mypy vertex-art-ar/

# 5. Tests
pytest --cov=vertex-art-ar

# 6. Security check
pip-audit
```

---

## Troubleshooting

### Common Issues

#### 1. Import Errors

**Проблема:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Решение:**
```bash
# Активируйте venv
source .venv/bin/activate

# Переустановите зависимости
pip install -r requirements.txt
```

#### 2. Database Locked

**Проблема:**
```
sqlite3.OperationalError: database is locked
```

**Решение:**
- SQLite не поддерживает concurrent writes
- Используйте connection pooling
- Рассмотрите миграцию на PostgreSQL

#### 3. Storage Directory Not Found

**Проблема:**
```
RuntimeError: Directory 'storage' does not exist
```

**Решение:**
```bash
mkdir -p storage/ar_content storage/nft-markers storage/qr-codes
```

#### 4. NFT Marker Generation Fails

**Проблема:**
```
ValueError: Not enough features detected
```

**Решение:**
- Проверьте качество изображения
- Убедитесь, что изображение имеет достаточно деталей
- Попробуйте разные настройки `feature_density`

### Getting Help

1. **Проверьте документацию**
2. **Поиск в Issues**: GitHub Issues
3. **Stack Overflow**: Тег `vertex-ar`
4. **Slack/Discord**: Community channel
5. **Email**: dev-support@vertex-ar.com

---

## Resources

### Documentation
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [A-Frame Docs](https://aframe.io/docs/)
- [AR.js Docs](https://ar-js-org.github.io/AR.js-Docs/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)

### Tutorials
- [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/)
- [Python Testing with pytest](https://docs.pytest.org/)
- [AR.js NFT Markers](https://ar-js-org.github.io/AR.js-Docs/marker-based/)

### Tools
- [Postman](https://www.postman.com/) - API testing
- [DBeaver](https://dbeaver.io/) - Database management
- [Docker Desktop](https://www.docker.com/products/docker-desktop)

---

**Happy Coding! 🚀**

**Версия документации:** 1.0.0  
**Последнее обновление:** 2024-01-15
