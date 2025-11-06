# Vertex AR — краткая документация проекта

**Версия:** 1.3.0
**Дата обновления:** 7 ноября 2024

---

## 1. Назначение

Vertex AR — серверное приложение на FastAPI, позволяющее загружать портреты, генерировать NFT-маркеры, прикреплять видео и воспроизводить AR-сцены через веб или мобильное устройство. Система включает админ-панель, управление пользователями, валидацию данных и журналы аудита.

---

## 2. Структура проекта

```
vertex-ar/
├── app/
│   ├── main.py              # Точка входа FastAPI
│   ├── api/                 # Маршруты (auth, users, clients, portraits, videos, markers)
│   ├── models.py            # Pydantic-схемы и валидаторы
│   ├── middleware.py        # Request/Error/Validation logging
│   ├── validators.py        # Централизованная валидация данных
│   ├── storage.py           # Абстракции хранилища (local/MinIO)
│   └── ...
├── templates/               # Jinja2-шаблоны (админка, viewer)
├── static/                  # Статические ресурсы (JS, CSS, маркеры)
├── storage/                 # Файлы пользователей (создаётся при запуске)
├── tests/                   # Автотесты приложения
├── README.md                # (создаётся в рамках этой задачи)
├── README_DEPLOYMENT.md     # Указания по развертыванию
├── CHANGELOG.md             # Изменения внутри подпроекта
├── requirements.txt         # Зависимости
└── VERSION                  # Текущая версия приложения
```

---

## 3. Ключевые компоненты

- **Аутентификация:** JWT, роли, политика паролей, блокировка после 5 неудачных попыток.
- **Клиенты и портреты:** CRUD, предпросмотры изображений, постоянные ссылки, QR-коды.
- **Видео:** Несколько роликов на портрет, выбор активного.
- **NFT-маркеры:** Генерация, batch-пайплайн, аналитика, очистка неиспользуемых файлов.
- **Валидация:** Единый модуль для email, телефонов, URL, UUID, файлов.
- **Логирование:** JSON-формат, request ID, уровень ошибок/валидации, совместимость с ELK.

---

## 4. API (обзор)

| Категория | Примеры |
| --- | --- |
| Аутентификация | `POST /auth/register`, `POST /auth/login`, `POST /auth/logout` |
| Пользователи | `GET /api/users`, `POST /api/users`, `GET /api/users/stats` |
| Клиенты | `POST /api/clients`, `GET /api/clients/search` |
| Портреты | `POST /api/portraits`, `GET /portrait/{permanent_link}` |
| Видео | `POST /api/videos`, `POST /api/videos/{id}/activate` |
| NFT-маркеры | `POST /api/nft-markers/batch-generate`, `GET /api/nft-markers/analytics` |
| Просмотр | `GET /ar/{content_id}`, `GET /qr/{content_id}` |

### API Endpoints

- **Аутентификация:** `/auth/login`, `/auth/register`, `/auth/logout`, `/auth/password/change`
- **Загрузка контента:** `/api/portraits`, `/api/videos`, `/api/clients`
- **Генерация маркеров:** `/api/nft-markers/generate`, `/api/nft-markers/batch-generate`, `/api/nft-markers/cleanup`
- **Просмотр контента:** `/portrait/{permanent_link}`, `/ar/{content_id}`, `/qr/{content_id}`

Полное описание см. в `docs/api/endpoints.md`.

---

## 5. Развёртывание

### Быстрый запуск для разработки
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

### Docker
```bash
docker-compose up --build -d
```

### Необходимые переменные окружения
- `STORAGE_TYPE` (`local` или `minio`)
- `MINIO_*` (если используется MinIO/S3)
- `SESSION_TIMEOUT_MINUTES`, `AUTH_MAX_ATTEMPTS`
- `BASE_URL` и CORS-настройки

Подробная инструкция: `README_DEPLOYMENT.md` и `docs/guides/installation.md`.

---

## 6. Тестирование и качество

- Запуск тестов: `pytest --cov=vertex-ar --cov-report=term-missing`
- Производительные сценарии: `../run_performance_tests.sh`
- Проверка готовности к релизу: `../check_production_readiness.sh`
- Покрытие: 78%, 31 автотест (19 — user management).

---

## 7. Документация

- Общий обзор: `../README.md`
- Статус реализации: `../IMPLEMENTATION_STATUS.md`
- Политика безопасности: `../SECURITY.md`
- Руководства: `../docs/README.md`
- История релизов: `../docs/releases/1.x.md`

---

## 8. Контакты и поддержка

- Технические вопросы: support@vertex-ar.example.com
- Безопасность: security@vertex-ar.example.com
- Сообщество: https://discord.gg/vertexar

Документ поддерживается в актуальном состоянии в рамках релиза 1.3.0.
