# Руководство по тестированию (разработчики)

**Версия:** 1.3.0  
**Дата обновления:** 7 ноября 2024

Документ описывает подходы к тестированию Vertex AR, структуру тестов и практики для разработчиков.

---

## 1. Цели

- Поддерживать покрытие кода на уровне ≥ 78%
- Гарантировать проверку критических сценариев (аутентификация, загрузка контента, генерация маркеров)
- Минимизировать регрессии через авто-тесты и чек-листы

---

## 2. Структура тестов

```
vertex-ar/tests/               # Unit тесты (модульные)
├── test_auth.py               # Аутентификация
├── test_models.py             # Pydantic модели
├── test_database.py           # Работа с БД
└── ...                        # Другие unit тесты

test_files/                    # Integration и Performance тесты
├── test_api_endpoints.py      # REST API, CRUD, валидаторы
├── test_admin_panel.py        # HTML-маршруты, авторизация
├── test_ar_functionality.py   # Просмотр AR-сцен, QR-коды
├── test_ar_upload_functionality.py  # Загрузка изображений и видео
├── test_nft_improvements.py   # Генерация и анализ маркеров
├── test_storage_integration.py # Работа локального и MinIO-хранилищ
├── test_security.py           # Блокировки, rate limiting, валидаторы
├── test_performance.py        # Производительность API
├── test_comprehensive_performance.py # Нагрузочные сценарии генератора
├── test_documentation.py      # Наличие ключевых документов
├── test_deployment.py         # Проверка скриптов и конфигураций
├── run_tests.sh               # Скрипт запуска тестов
└── run_performance_tests.sh   # Скрипт производительных тестов
```

**Unit тесты** в `vertex-ar/tests/` — быстрые, изолированные проверки бизнес-логики.  
**Integration тесты** в `test_files/` — полные сценарии с взаимодействием компонентов.

---

## 3. Локальный запуск

### 3.1 Установка зависимостей
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3.2 Подготовка окружения
```bash
cp .env.example .env
export RUNNING_TESTS=1
mkdir -p vertex-ar/storage vertex-ar/static
```

### 3.3 Запуск тестов
```bash
pytest -n auto
pytest tests/test_api_endpoints.py -k "auth"
```

### 3.4 Покрытие
```bash
pytest --cov=vertex-ar --cov-report=term-missing
```

Результаты в `htmlcov/index.html`.

---

## 4. Категории тестов

| Категория | Цель | Файлы |
| --- | --- | --- |
| Unit | Изолированная логика, валидаторы | `vertex-ar/tests/test_*.py` |
| Integration | Полный цикл API/хранилища | `test_files/test_api_endpoints.py`, `test_files/test_storage_integration.py` |
| E2E/UX | Админ-панель, AR-просмотр | `test_files/test_admin_panel.py`, `test_files/test_ar_functionality.py` |
| Security | Rate limiting, блокировки, валидация | `test_files/test_security.py` |
| Performance | Время генерации, нагрузка | `test_files/test_performance.py`, `test_files/test_comprehensive_performance.py` |
| Documentation | Актуальность README/CHANGELOG/ROADMAP | `test_files/test_documentation.py` |

---

## 5. Покрытие и метрики

- Покрытие кода: **78%**
- Критические потоки: 100% (auth, создание клиента, генерация маркера, запуск AR)
- Среднее время прогона полного набора: 6 минут на 8 vCPU / 16 ГБ RAM
- Производительные тесты: генерация 5 изображений < 20 секунд (p95)

---

## 6. Построение окружения в Docker

```bash
docker-compose -f docker-compose.yml up tests
```

Контейнер запускает pytest и возвращает код статуса.

---

## 7. Отладка и полезные команды

- Логи запросов: `tail -f logs/request.log`
- Повтор генерации маркеров: `python scripts/generate_marker.py --portrait 10`
- Проверка MinIO: `python check_storage.py`
- Проверка готовности: `./check_production_readiness.sh`

---

## 8. Политика для новых тестов

1. Любое новое API изменение сопровождается тестом.
2. Для критических обработчиков файлов — минимум один happy path и один негативный сценарий.
3. Новые флаги `.env` требуют теста или моков.
4. Валидация должна иметь тесты на успешные и ошибочные значения (email, телефон, пароль, URL).
5. При изменении логирования добавляйте проверку request ID/уровней.

---

## 9. Производительность и нагрузка

Запуск: `cd test_files && ./run_performance_tests.sh` (выполняет стресс-тест генератора и API).  
Метрики сохраняются в `performance_results/`.

Рекомендуемые параметры стенда: CPU 4+, RAM 8+ ГБ, SSD.

Альтернативно: `pytest test_files/ -k "performance or load" -v`

---

## 10. CI/CD (план)

- GitHub Actions: линтеры, pytest, pytest-cov, публикация отчёта
- E2E Smoke: контейнер с `uvicorn` + `pytest -m smoke`
- Нагрузочные тесты по расписанию (nightly)

Статус: в разработке (релиз 1.4).

---

## 11. Ретрофит

- Все обнаруженные баги сопровождаются тестами (regression tests)
- Тестовые данные находятся в `test_files/` (изображения, видео, JSON)
- При добавлении новых фикстур используйте фабрики и временные директории (`tmp_path`)
- Используйте `test_files/create_test_video.py` для генерации тестовых видео

---

## 12. Контакты

- QA команда: qa@vertex-ar.example.com
- DevOps: devops@vertex-ar.example.com
- Дежурный чат: Discord #qa

Документ обновляется одновременно с `TESTING_REPORT.md`.
