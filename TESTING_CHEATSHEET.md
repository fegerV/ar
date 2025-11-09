# 🚀 Шпаргалка по тестированию Vertex AR

Быстрая справка по командам для тестирования проекта.

---

## 📦 Первоначальная настройка

```bash
# Клонирование и настройка
git clone https://github.com/your-org/vertex-ar.git
cd vertex-ar
python -m venv .venv
source .venv/bin/activate
pip install -r vertex-ar/requirements.txt
pip install -r vertex-ar/requirements-dev.txt
cp .env.example .env

# Быстрая настройка и демо
./quick_test.sh setup
./quick_test.sh demo
```

---

## ⚡ Быстрые команды

### Запуск тестов

```bash
# Все тесты
pytest -v

# Быстрые (без медленных)
pytest -m "not slow" -v

# Только unit
pytest -m unit -v

# С покрытием
pytest --cov=vertex-ar --cov-report=html

# Конкретный файл
pytest vertex-ar/tests/test_auth.py -v

# Конкретный тест
pytest vertex-ar/tests/test_auth.py::test_user_registration -v

# Упавшие тесты
pytest --lf -v
```

### Скрипт quick_test.sh

```bash
./quick_test.sh all       # Все тесты
./quick_test.sh quick     # Быстрые тесты
./quick_test.sh unit      # Unit тесты
./quick_test.sh api       # API тесты
./quick_test.sh demo      # Демонстрация
./quick_test.sh coverage  # С покрытием
./quick_test.sh setup     # Настройка окружения
./quick_test.sh clean     # Очистка
```

### Запуск приложения

```bash
# Development режим
cd vertex-ar
uvicorn app.main:app --reload

# Production режим
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Docker
docker compose up -d
docker compose logs -f app
docker compose down
```

---

## 🔍 Тестирование по типам

### Unit тесты
```bash
pytest -m unit -v
```

### Integration тесты
```bash
pytest -m integration -v
```

### AR функциональность
```bash
pytest -m ar -v
```

### Performance тесты
```bash
pytest -m performance -v
./run_performance_tests.sh
```

### Security тесты
```bash
pytest -m security -v
bandit -r vertex-ar/
```

---

## 🌐 API тестирование

### Регистрация
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "TestPass123!",
    "email": "test@example.com",
    "full_name": "Test User"
  }'
```

### Вход
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "TestPass123!"
  }'

# Сохраните токен
export TOKEN="your-token-here"
```

### Получение профиля
```bash
curl -X GET http://localhost:8000/api/users/me \
  -H "Authorization: Bearer $TOKEN"
```

### Создание клиента
```bash
curl -X POST http://localhost:8000/api/clients/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Client",
    "phone": "+1234567890",
    "email": "client@example.com"
  }'
```

### Health check
```bash
curl http://localhost:8000/health
```

---

## 🐛 Отладка

### Запуск с breakpoint
```python
import pdb; pdb.set_trace()
```

### Pytest debug режим
```bash
pytest -vv -s --log-cli-level=DEBUG test_file.py::test_name
```

### Остановка на первой ошибке
```bash
pytest -x --pdb
```

### Просмотр логов
```bash
tail -f logs/app.log
docker compose logs -f app
```

---

## 📊 Coverage

### Генерация отчёта
```bash
pytest --cov=vertex-ar --cov-report=html
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Coverage в терминале
```bash
pytest --cov=vertex-ar --cov-report=term-missing
```

---

## 🔧 Code Quality

### Форматирование
```bash
black vertex-ar/
isort vertex-ar/
```

### Линтинг
```bash
flake8 vertex-ar/
```

### Типы
```bash
mypy vertex-ar/
```

### Безопасность
```bash
bandit -r vertex-ar/
safety check
```

### Всё сразу (pre-commit)
```bash
black vertex-ar/ && isort vertex-ar/ && flake8 vertex-ar/ && pytest -m "not slow"
```

---

## ⚡ Performance Testing

### Locust
```bash
pip install locust
locust -f locustfile.py --host=http://localhost:8000
# Откройте: http://localhost:8089
```

### Performance скрипт
```bash
./run_performance_tests.sh
```

### Memory profiling
```bash
pytest test_memory_profiler.py -v
```

---

## 🐳 Docker

### Базовые команды
```bash
docker compose build       # Собрать образы
docker compose up -d       # Запустить в фоне
docker compose ps          # Статус
docker compose logs -f app # Логи
docker compose down        # Остановить
docker compose down -v     # Остановить + удалить volumes
```

### Тесты в Docker
```bash
docker compose run --rm app pytest -v
docker compose run --rm app bash  # Интерактивная оболочка
```

---

## 🧹 Очистка

```bash
# Скрипт очистки
./quick_test.sh clean

# Ручная очистка
rm -f test_app_data.db app_data.db
rm -rf test_storage/ htmlcov/ .pytest_cache/
find . -type d -name "__pycache__" -exec rm -rf {} +
```

---

## 📝 Полезные alias'ы

Добавьте в `~/.bashrc` или `~/.zshrc`:

```bash
alias va='source .venv/bin/activate'
alias vtest='pytest -v'
alias vquick='pytest -m "not slow" -v'
alias vcov='pytest --cov=vertex-ar --cov-report=html'
alias vrun='cd vertex-ar && uvicorn app.main:app --reload'
alias vdemo='./quick_test.sh demo'
alias vclean='./quick_test.sh clean'
```

---

## 🎯 Маркеры pytest

```bash
@pytest.mark.unit          # Unit тесты
@pytest.mark.integration   # Integration тесты
@pytest.mark.slow          # Медленные тесты
@pytest.mark.api           # API тесты
@pytest.mark.storage       # Storage тесты
@pytest.mark.auth          # Auth тесты
@pytest.mark.nft           # NFT тесты
@pytest.mark.ar            # AR тесты
@pytest.mark.admin         # Admin тесты
@pytest.mark.security      # Security тесты
@pytest.mark.performance   # Performance тесты
```

### Использование
```bash
pytest -m unit              # Только unit
pytest -m "not slow"        # Без медленных
pytest -m "unit or api"     # Unit или API
pytest -m "unit and not slow"  # Unit без медленных
```

---

## 🔑 Переменные окружения для тестов

```bash
# Отключить rate limiting
export RATE_LIMIT_ENABLED=false

# Debug режим
export DEBUG=true

# Тестовая БД
export DATABASE_URL=sqlite:///./test.db

# Уровень логирования
export LOG_LEVEL=DEBUG
```

---

## 📚 Документация

| Файл | Описание |
|------|----------|
| [QUICK_START_RU.md](QUICK_START_RU.md) | Быстрый старт (5 мин) |
| [LOCAL_TESTING_GUIDE.md](LOCAL_TESTING_GUIDE.md) | Полное руководство |
| [TESTING_SCENARIOS.md](TESTING_SCENARIOS.md) | Готовые сценарии |
| [IDE_TESTING_SETUP.md](IDE_TESTING_SETUP.md) | Настройка IDE |
| [TESTING_INDEX.md](TESTING_INDEX.md) | Индекс документации |

---

## 🆘 Troubleshooting

### ModuleNotFoundError
```bash
source .venv/bin/activate
pip install -r vertex-ar/requirements.txt --force-reinstall
```

### Database locked
```bash
rm test_app_data.db app_data.db
```

### Port 8000 occupied
```bash
lsof -i :8000
kill -9 <PID>
```

### Permission denied
```bash
chmod +x quick_test.sh run_tests.sh
```

---

## 📊 Быстрая проверка статуса

```bash
# Проверка всего стека
pytest -v && \
black --check vertex-ar/ && \
flake8 vertex-ar/ && \
./check_production_readiness.sh
```

---

## 🚀 VS Code

### Горячие клавиши
- `Ctrl+Shift+P` → "Test: Run All Tests"
- `Ctrl+Shift+P` → "Test: Run Failed Tests"
- `F5` → Start Debugging
- `Shift+F5` → Stop Debugging

### Tasks (Ctrl+Shift+P → "Tasks: Run Task")
- Run All Tests
- Run Quick Tests
- Run Tests with Coverage
- Start FastAPI Server
- Format Code
- Pre-commit Check

---

## 💡 Pro Tips

```bash
# Автоматический перезапуск тестов
pip install pytest-watch
ptw -- -v

# Parallel execution
pip install pytest-xdist
pytest -n auto

# Детальный traceback
pytest --tb=long

# Короткий traceback
pytest --tb=line

# Без traceback
pytest --tb=no

# Показать 10 самых медленных тестов
pytest --durations=10

# Запуск с timeout
pytest --timeout=60
```

---

**🔗 Быстрые ссылки:**
- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/health
- Admin: http://localhost:8000/admin
- Locust UI: http://localhost:8089

---

**Сохраните эту шпаргалку для быстрого доступа! 📌**
