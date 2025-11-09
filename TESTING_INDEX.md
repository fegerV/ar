# 📚 Индекс тестовой документации Vertex AR

Полный указатель всех документов и ресурсов связанных с тестированием проекта.

---

## 🎯 С чего начать?

### Новичок в проекте?

1. **[QUICK_START_RU.md](QUICK_START_RU.md)** - Начните здесь! (5 минут)
   - Минимальная настройка
   - Первый запуск тестов
   - Быстрая демонстрация

2. **[TESTING_SCENARIOS.md](TESTING_SCENARIOS.md)** - Готовые примеры
   - Базовые сценарии
   - Негативные тесты
   - Performance тестирование

### Хотите глубже разобраться?

3. **[LOCAL_TESTING_GUIDE.md](LOCAL_TESTING_GUIDE.md)** - Полное руководство
   - Все типы тестов
   - Отладка и troubleshooting
   - Docker тестирование
   - Лучшие практики

### Настройка инструментов?

4. **[IDE_TESTING_SETUP.md](IDE_TESTING_SETUP.md)** - Конфигурация IDE
   - VS Code
   - PyCharm
   - Vim/Neovim
   - Sublime Text

---

## 📋 Все документы по тестированию

### Основные руководства

| Документ | Описание | Время чтения | Уровень |
|----------|----------|--------------|---------|
| [QUICK_START_RU.md](QUICK_START_RU.md) | Быстрый старт | 5 мин | Начинающий |
| [LOCAL_TESTING_GUIDE.md](LOCAL_TESTING_GUIDE.md) | Полное руководство | 30 мин | Все уровни |
| [TESTING_SCENARIOS.md](TESTING_SCENARIOS.md) | Тестовые сценарии | 20 мин | Средний |
| [IDE_TESTING_SETUP.md](IDE_TESTING_SETUP.md) | Настройка IDE | 15 мин | Средний |
| [TESTING_REPORT.md](TESTING_REPORT.md) | Отчёт о тестировании | 10 мин | Любой |

### Конфигурационные файлы

| Файл | Назначение |
|------|-----------|
| `pytest.ini` | Конфигурация pytest |
| `locustfile.py` | Нагрузочное тестирование |
| `quick_test.sh` | Универсальный скрипт тестирования |
| `run_tests.sh` | Скрипт запуска тестов |
| `run_performance_tests.sh` | Performance тесты |
| `.vscode/` | Настройки VS Code |
| `.github/workflows/` | CI/CD тесты |

### Тестовые файлы

#### Основные тесты (vertex-ar/tests/)

```
vertex-ar/tests/
├── test_api.py              # API endpoint тесты
├── test_ar_features.py      # AR функциональность  
├── test_auth.py             # Аутентификация
├── test_database.py         # База данных
├── test_models.py           # Pydantic модели
├── test_nft_generation.py   # NFT маркеры
├── test_storage.py          # Файловое хранилище
├── test_storage_adapter.py  # Storage adapter
└── test_user_management.py  # Управление пользователями
```

#### Дополнительные тесты (корень проекта)

```
./
├── test_admin_panel.py              # Админ панель
├── test_api_endpoints.py            # API endpoints (legacy)
├── test_ar_functionality.py         # AR функции
├── test_ar_upload_functionality.py  # AR загрузка
├── test_ar_upload_simple.py         # AR загрузка (простой)
├── test_comprehensive_performance.py # Комплексная производительность
├── test_deployment.py               # Развёртывание
├── test_documentation.py            # Документация
├── test_memory_profiler.py          # Профилирование памяти
├── test_nft_improvements.py         # NFT улучшения
├── test_orders_api.py               # API заказов
├── test_performance.py              # Производительность
├── test_portraits_automated.py      # Портреты (автоматизированный)
├── test_portraits_load.py           # Портреты (нагрузка)
├── test_psutil_basic.py             # Psutil тесты
├── test_refactored_app.py           # Рефакторинг
├── test_security.py                 # Безопасность
├── test_storage_integration.py      # Storage интеграция
└── test_ui_improvements.py          # UI улучшения
```

---

## 🔍 Навигация по типам тестов

### Unit тесты

**Что тестируют:** Отдельные функции и методы

**Файлы:**
- `vertex-ar/tests/test_models.py` - Pydantic модели
- `vertex-ar/tests/test_auth.py` - Логика аутентификации
- `vertex-ar/tests/test_database.py` - Операции с БД

**Запуск:**
```bash
pytest -m unit -v
```

### Integration тесты

**Что тестируют:** Взаимодействие компонентов

**Файлы:**
- `vertex-ar/tests/test_api.py` - API endpoints
- `vertex-ar/tests/test_user_management.py` - Управление пользователями
- `test_storage_integration.py` - Storage интеграция

**Запуск:**
```bash
pytest -m integration -v
```

### AR Feature тесты

**Что тестируют:** AR функциональность

**Файлы:**
- `vertex-ar/tests/test_ar_features.py` - AR функции
- `vertex-ar/tests/test_nft_generation.py` - NFT генерация
- `test_ar_functionality.py` - AR функциональность
- `test_ar_upload_functionality.py` - Загрузка AR

**Запуск:**
```bash
pytest -m ar -v
```

### Performance тесты

**Что тестируют:** Производительность и нагрузка

**Файлы:**
- `test_comprehensive_performance.py` - Комплексные тесты
- `test_performance.py` - Базовая производительность
- `test_memory_profiler.py` - Профилирование памяти
- `test_portraits_load.py` - Нагрузка на портреты

**Запуск:**
```bash
pytest -m performance -v
./run_performance_tests.sh
```

### Security тесты

**Что тестируют:** Безопасность приложения

**Файлы:**
- `test_security.py` - Тесты безопасности
- Parts of `test_auth.py` - Аутентификация

**Запуск:**
```bash
pytest -m security -v
bandit -r vertex-ar/
```

### Storage тесты

**Что тестируют:** Файловое хранилище

**Файлы:**
- `vertex-ar/tests/test_storage.py` - Storage тесты
- `vertex-ar/tests/test_storage_adapter.py` - Adapter тесты
- `test_storage_integration.py` - Интеграция

**Запуск:**
```bash
pytest -m storage -v
```

---

## 🛠️ Скрипты и утилиты

### Скрипты запуска тестов

| Скрипт | Описание | Использование |
|--------|----------|---------------|
| `quick_test.sh` | Универсальный тестовый скрипт | `./quick_test.sh [all\|quick\|unit\|api\|setup\|demo\|coverage\|clean]` |
| `run_tests.sh` | Базовый запуск тестов | `./run_tests.sh [all\|fast\|coverage\|verbose\|failed]` |
| `run_performance_tests.sh` | Performance тесты | `./run_performance_tests.sh` |

### Примеры использования

```bash
# Быстрый старт для новичков
./quick_test.sh demo

# Быстрые тесты (исключая медленные)
./quick_test.sh quick

# Unit тесты
./quick_test.sh unit

# Тесты с покрытием + HTML отчёт
./quick_test.sh coverage

# Настройка окружения
./quick_test.sh setup

# Очистка тестовых данных
./quick_test.sh clean

# Performance тестирование
./run_performance_tests.sh

# Нагрузочное тестирование
locust -f locustfile.py --host=http://localhost:8000
```

---

## 📊 Маркеры pytest

Проект использует следующие маркеры для категоризации тестов:

```python
@pytest.mark.unit          # Unit тесты
@pytest.mark.integration   # Integration тесты
@pytest.mark.slow          # Медленные тесты (>5 сек)
@pytest.mark.api           # API endpoint тесты
@pytest.mark.storage       # Storage тесты
@pytest.mark.auth          # Authentication тесты
@pytest.mark.nft           # NFT-related тесты
@pytest.mark.ar            # AR функциональность
@pytest.mark.admin         # Admin panel тесты
@pytest.mark.security      # Security тесты
@pytest.mark.performance   # Performance тесты
```

### Примеры использования маркеров

```bash
# Только unit тесты
pytest -m unit

# Только integration тесты
pytest -m integration

# Исключить медленные тесты
pytest -m "not slow"

# AR и NFT тесты
pytest -m "ar or nft"

# Unit и integration, но не медленные
pytest -m "(unit or integration) and not slow"
```

---

## 🎓 Учебные материалы

### Для начинающих

1. **Прочитайте:** [QUICK_START_RU.md](QUICK_START_RU.md)
2. **Запустите:** `./quick_test.sh demo`
3. **Изучите:** Посмотрите на вывод и как работает API
4. **Попробуйте:** Измените код и запустите тесты снова

### Для разработчиков

1. **Прочитайте:** [LOCAL_TESTING_GUIDE.md](LOCAL_TESTING_GUIDE.md)
2. **Настройте:** Следуйте [IDE_TESTING_SETUP.md](IDE_TESTING_SETUP.md)
3. **Практикуйте:** Пройдите сценарии из [TESTING_SCENARIOS.md](TESTING_SCENARIOS.md)
4. **Пишите:** Создавайте собственные тесты

### Для QA инженеров

1. **Изучите:** Все документы выше
2. **Запустите:** Все типы тестов
3. **Анализируйте:** Coverage отчёты
4. **Улучшайте:** Добавьте edge cases и negative scenarios

---

## 🔄 Workflow рекомендации

### Ежедневная разработка

```bash
# Утром - проверьте что всё работает
./quick_test.sh quick

# Во время разработки - автоматические тесты
ptw -- -v

# Перед commit - полная проверка
pytest -v
```

### Перед pull request

```bash
# 1. Все тесты
pytest -v

# 2. Coverage
pytest --cov=vertex-ar --cov-report=html

# 3. Linting
black vertex-ar/
isort vertex-ar/
flake8 vertex-ar/

# 4. Security
bandit -r vertex-ar/
```

### Перед релизом

```bash
# 1. Полный набор тестов
pytest -v

# 2. Performance тесты
./run_performance_tests.sh

# 3. Security audit
bandit -r vertex-ar/
safety check

# 4. Production readiness
./check_production_readiness.sh

# 5. Manual testing
./quick_test.sh demo
```

---

## 🐛 Troubleshooting

### Частые проблемы и их решения

| Проблема | Решение | Документ |
|----------|---------|----------|
| Тесты не запускаются | Проверьте виртуальное окружение | [QUICK_START_RU.md](QUICK_START_RU.md#troubleshooting) |
| ModuleNotFoundError | Переустановите зависимости | [LOCAL_TESTING_GUIDE.md](LOCAL_TESTING_GUIDE.md#отладка-и-troubleshooting) |
| Database locked | Удалите тестовую БД | [QUICK_START_RU.md](QUICK_START_RU.md#troubleshooting) |
| Порт 8000 занят | Освободите порт или используйте другой | [QUICK_START_RU.md](QUICK_START_RU.md#troubleshooting) |
| Permission denied | Дайте права на скрипты | [QUICK_START_RU.md](QUICK_START_RU.md#troubleshooting) |

### Получение помощи

1. **Документация:** Смотрите файлы выше
2. **Логи:** `tail -f logs/app.log`
3. **Debug:** `pytest -vv -s --log-cli-level=DEBUG`
4. **Issues:** GitHub Issues

---

## 📈 Метрики качества

### Текущее состояние

- **Покрытие кода:** 78%
- **Количество тестов:** 31+
- **Типы тестов:** Unit, Integration, AR, Performance, Security
- **CI/CD:** GitHub Actions
- **Production readiness:** 97%

### Целевые показатели

- **Покрытие кода:** >80%
- **Response time:** <100ms (p95)
- **NFT generation:** <5s (p95)
- **Test execution:** <60s (full suite)

---

## 🎯 Чек-лист для нового разработчика

- [ ] Прочитал [QUICK_START_RU.md](QUICK_START_RU.md)
- [ ] Настроил виртуальное окружение
- [ ] Установил зависимости
- [ ] Запустил `./quick_test.sh demo`
- [ ] Все тесты прошли: `pytest -v`
- [ ] Настроил IDE по [IDE_TESTING_SETUP.md](IDE_TESTING_SETUP.md)
- [ ] Изучил существующие тесты в `vertex-ar/tests/`
- [ ] Прошёл базовые сценарии из [TESTING_SCENARIOS.md](TESTING_SCENARIOS.md)
- [ ] Написал свой первый тест
- [ ] Понял как работает CI/CD

---

## 🚀 Быстрые команды

```bash
# Демо для ознакомления
./quick_test.sh demo

# Все тесты
pytest -v

# Быстрые тесты
./quick_test.sh quick

# С покрытием
pytest --cov=vertex-ar --cov-report=html

# Только unit
pytest -m unit -v

# Performance
./run_performance_tests.sh

# Нагрузка
locust -f locustfile.py

# Очистка
./quick_test.sh clean
```

---

## 📞 Контакты и ресурсы

- **Email:** support@vertex-ar.example.com
- **Discord:** [Vertex AR Community](https://discord.gg/vertexar)
- **GitHub:** [Issues](https://github.com/your-org/vertex-ar/issues)
- **Docs:** [docs/](docs/)

---

**Удачного тестирования! 🚀**

*Последнее обновление: Ноябрь 2024*
