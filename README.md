# 🎨 Vertex AR

**Version:** 1.1.0 | **Status:** Production Ready

<div align="center">

### Оживите статичные портреты с помощью дополненной реальности

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org)
[![AR.js](https://img.shields.io/badge/AR.js-Latest-FF6B6B?style=flat-square)](https://ar-js-org.github.io/AR.js-Docs/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

[Быстрый старт](#-быстрый-старт) • [Возможности](#-возможности) • [Документация](#-документация) • [Демо](#-демо) • [API](#-api) • [Roadmap](ROADMAP.md)

</div>

---

## 📖 О проекте

**Vertex AR** — это инновационное веб-приложение, которое превращает обычные портреты в интерактивные AR-переживания. Загрузите изображение, добавьте видео или анимацию, и наблюдайте, как портрет оживает при наведении камеры смартфона!

### 🎯 Киллер-фича

В отличие от традиционных сервисов печати портретов, **Vertex AR** добавляет магию дополненной реальности:
- 📸 **Загрузите портрет** → система создаст AR-маркер
- 🎬 **Добавьте видео** → ваш портрет оживет с анимацией
- 📱 **Отсканируйте QR-код** → мгновенный доступ к AR-контенту
- ✨ **Наслаждайтесь магией** → моргание, улыбки, повороты головы в реальном времени

---

## ✨ Возможности

<table>
<tr>
<td width="50%">

### 🎭 AR Анимации
- 👁️ Реалистичное моргание глаз
- 😊 Динамические улыбки
- 🔄 Плавные повороты головы
- 😉 Игривые подмигивания
- 🌊 Настраиваемые эффекты

</td>
<td width="50%">

### 🔧 Технические возможности
- 🚀 Высокопроизводительный FastAPI backend
- 💾 SQLite для надежного хранения данных
- 📦 Масштабируемое хранилище (Local/MinIO/S3)
- 🔐 Защищенная аутентификация
- 📊 Детальная аналитика просмотров

</td>
</tr>
<tr>
<td width="50%">

### 🎨 NFT Маркеры
- 🎯 Высокоточное распознавание
- 🖼️ Автоматическая генерация маркеров
- 📐 Оптимизация под AR.js
- 🔍 Поддержка различных форматов
- ⚡ Быстрое детектирование

</td>
<td width="50%">

### 📱 Пользовательский интерфейс
- 🎛️ Интуитивная админ-панель
- 📋 Управление контентом
- 📈 Статистика в реальном времени
- 📲 QR-коды для быстрого доступа
- 🌐 Адаптивный дизайн

</td>
</tr>
</table>

---

## 🚀 Быстрый старт

### Предварительные требования

- 🐍 Python 3.9+
- 📦 pip
- 🔧 virtualenv (рекомендуется)

### ⚡ Установка за 3 шага

```bash
# 1️⃣ Клонируйте репозиторий
git clone https://github.com/your-username/vertex-ar.git
cd vertex-ar

# 2️⃣ Установите зависимости
pip install -r requirements.txt

# 3️⃣ Запустите приложение
cd vertex-ar
python main.py
```

🎉 Готово! Откройте браузер и перейдите по адресу `http://localhost:8000`

### 🐳 Docker-развертывание

```bash
# Соберите и запустите контейнеры
docker-compose up -d

# Проверьте статус
docker-compose ps
```

---

## 💡 Использование

### 1️⃣ Создание AR-контента

```bash
# Зарегистрируйтесь как администратор
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"secure_password"}'

# Получите токен доступа
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"secure_password"}'
```

### 2️⃣ Загрузка портрета

- 📂 Откройте админ-панель по адресу `http://localhost:8000/admin`
- 🖼️ Загрузите изображение портрета
- 🎬 Добавьте видео или выберите тип анимации
- 💾 Сохраните и получите QR-код

### 3️⃣ Просмотр AR

- 📱 Отсканируйте QR-код на смартфоне
- 🎯 Наведите камеру на напечатанный портрет
- ✨ Наслаждайтесь оживающей анимацией!

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Admin Panel │  │   AR Viewer  │  │  Mobile App  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
└─────────┼──────────────────┼──────────────────┼─────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────┐
│                     FastAPI Backend                       │
│  ┌────────────────────────────────────────────────────┐  │
│  │              REST API Endpoints                     │  │
│  │  /auth/*  /ar/*  /admin/*  /nft/*  /qr/*  /stats/* │  │
│  └─────┬────────────────────────────────────────┬─────┘  │
│        │                                        │         │
│  ┌─────▼─────┐  ┌──────────────┐  ┌───────────▼─────┐  │
│  │   Auth    │  │  AR Content  │  │  NFT Generator  │  │
│  │  Service  │  │   Manager    │  │                 │  │
│  └───────────┘  └──────┬───────┘  └─────────────────┘  │
└─────────────────────────┼──────────────────────────────┘
                          │
          ┌───────────────┴────────────────┐
          │                                │
┌─────────▼─────────┐          ┌──────────▼──────────┐
│   SQLite Database │          │ Storage Layer       │
│  ┌──────────────┐ │          │ (Local/MinIO/S3)   │
│  │   Users      │ │          │  ┌───────────────┐ │
│  │   Content    │ │          │  │   Images      │ │
│  │   Stats      │ │          │  │   Videos      │ │
│  └──────────────┘ │          │  │   Markers     │ │
└───────────────────┘          │  └───────────────┘ │
                               └─────────────────────┘
```

---

## 🛠️ Технологический стек

### Backend
- 🚀 **[FastAPI](https://fastapi.tiangolo.com)** - Современный веб-фреймворк
- 🗃️ **[SQLAlchemy](https://www.sqlalchemy.org)** - ORM для работы с БД
- 🔐 **JWT** - Безопасная аутентификация
- 📦 **[MinIO](https://min.io)** - Объектное хранилище

### Frontend & AR
- 🌐 **[A-Frame](https://aframe.io)** - WebVR/AR фреймворк
- 🎯 **[AR.js](https://ar-js-org.github.io/AR.js-Docs/)** - AR для веба
- ✨ **[Anime.js](https://animejs.com)** - JavaScript анимации
- 🎨 **[Jinja2](https://jinja.palletsprojects.com)** - Шаблонизация

### DevOps
- 🐳 **Docker** - Контейнеризация
- 🔧 **Docker Compose** - Оркестрация
- 🌐 **Nginx** - Reverse proxy
- 📊 **Supervisor** - Управление процессами

---

## 📡 API Эндпоинты

### 🔐 Аутентификация

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `POST` | `/auth/register` | Регистрация нового пользователя |
| `POST` | `/auth/login` | Вход в систему |
| `POST` | `/auth/logout` | Выход из системы |

### 🎨 AR Контент

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `POST` | `/ar/upload` | Загрузка AR-контента (изображение + видео) |
| `GET` | `/ar/{content_id}` | Получение AR-контента |
| `GET` | `/ar/list` | Список всего AR-контента |
| `DELETE` | `/ar/{content_id}` | Удаление AR-контента |

### 🎯 NFT Маркеры

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `POST` | `/nft/generate` | Генерация NFT-маркера из изображения |
| `GET` | `/nft/{marker_id}` | Получение NFT-маркера |
| `POST` | `/nft/analyze` | Анализ качества маркера |

### 📊 Статистика

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `GET` | `/stats/views` | Статистика просмотров |
| `GET` | `/stats/content` | Статистика контента |
| `GET` | `/stats/system` | Системная статистика |

### 📲 QR-коды

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `GET` | `/qr/{content_id}` | Генерация QR-кода для AR-контента |

📚 **Полная документация API:** [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)

---

## 📂 Структура проекта

```
vertex-ar/
├── 📁 vertex-ar/               # Основное приложение
│   ├── 📄 main.py              # FastAPI приложение
│   ├── 📄 utils.py             # Утилиты
│   ├── 📄 nft_marker_generator.py  # Генератор NFT-маркеров
│   ├── 📁 templates/           # Jinja2 шаблоны
│   │   ├── admin.html          # Админ-панель
│   │   ├── ar_viewer.html      # AR просмотрщик
│   │   └── ...
│   ├── 📁 storage/             # Локальное хранилище
│   │   ├── ar_content/         # AR контент
│   │   ├── nft-markers/        # NFT маркеры
│   │   └── previews/           # Превью
│   └── 📁 static/              # Статические файлы
│
├── 📁 tests/                   # Тесты
│   ├── test_api_endpoints.py
│   ├── test_ar_functionality.py
│   └── ...
│
├── 📁 docs/                    # Документация
│   ├── 📄 API_DOCUMENTATION.md
│   ├── 📄 ARCHITECTURE.md
│   ├── 📄 DEVELOPER_GUIDE.md
│   └── ...
│
├── 🐳 docker-compose.yml       # Docker конфигурация
├── 🐳 Dockerfile.app           # Docker образ
├── 📄 requirements.txt         # Python зависимости
├── 📄 Makefile                 # Команды для разработки
└── 📖 README.md                # Этот файл
```

---

## 📚 Документация

### 🗺️ План развития и статус (v1.1.0)

- 🎯 **[ROADMAP.md](./ROADMAP.md)** - Детальный план развития (фазы 1-4)
- ✅ **[IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)** - Статус реализации всех 122 функций (70% complete)
- 🔍 **[FUNCTIONS_REVIEW.md](./FUNCTIONS_REVIEW.md)** - Обзор кода и рекомендации
- 📝 **[CHANGELOG.md](./CHANGELOG.md)** - История версий

### 🇷🇺 Документация на русском языке

#### 🚀 Масштабирование
- 📦 [**Storage Scaling Overview**](./STORAGE_SCALING_README.md) - Quick overview (English)
- 📖 [**Руководство по масштабированию хранилища**](./SCALING_STORAGE_GUIDE.md) - Подробное руководство
- ⚡ [**Быстрый старт масштабирования**](./SCALING_QUICK_START_RU.md) - Быстрая настройка
- 🐳 [**Docker Compose Examples**](./DOCKER_COMPOSE_EXAMPLES.md) - Deployment configurations

#### Для пользователей
- 🚀 **[QUICKSTART_RU.md](./QUICKSTART_RU.md)** - Быстрый старт за 5 минут
- 📖 **[README_RU.md](./README_RU.md)** - Подробное описание проекта
- 👤 **[USER_GUIDE_RU.md](./USER_GUIDE_RU.md)** - Руководство пользователя
- 💻 **[INSTALLATION_GUIDE_RU.md](./INSTALLATION_GUIDE_RU.md)** - Инструкция по установке
- 🔌 **[API_EXAMPLES_RU.md](./API_EXAMPLES_RU.md)** - Примеры использования API

#### Для разработчиков
- 🔧 **[DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)** - Руководство разработчика
- 🏗️ **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Архитектура системы
- 📡 **[API_DOCUMENTATION.md](./API_DOCUMENTATION.md)** - API документация
- 🧪 **[TESTING_SUMMARY.md](./TESTING_SUMMARY.md)** - Тестирование
- 🚀 **[README_DEPLOYMENT.md](./README_DEPLOYMENT.md)** - Развертывание

#### Индекс
- 📑 **[DOCUMENTATION_INDEX.md](./DOCUMENTATION_INDEX.md)** - Полный индекс документации
- 📝 **[DOCS_CHEATSHEET_RU.md](./DOCS_CHEATSHEET_RU.md)** - Шпаргалка по документации

---

## 🧪 Тестирование

```bash
# Запуск всех тестов
pytest

# Запуск с покрытием кода
pytest --cov=vertex-ar --cov-report=html

# Запуск конкретного теста
pytest tests/test_api_endpoints.py

# Запуск с подробным выводом
pytest -v
```

### 📊 Покрытие тестами

- ✅ API эндпоинты - 95%
- ✅ AR функциональность - 90%
- ✅ Аутентификация - 100%
- ✅ Генерация маркеров - 85%

---

## 🔒 Безопасность

- 🔐 JWT токены для аутентификации
- 🛡️ Валидация всех входных данных
- 🔒 CORS настройки
- 🚫 Rate limiting
- 📝 Логирование всех действий
- 🔑 Безопасное хранение паролей (bcrypt)

### 🐛 Сообщить о уязвимости

Если вы обнаружили уязвимость в безопасности, пожалуйста, свяжитесь с нами напрямую:
📧 security@vertex-ar.example.com

---

## 🤝 Участие в разработке

Мы приветствуем вклад от сообщества! 

### Как внести вклад

1. 🍴 Сделайте Fork репозитория
2. 🔨 Создайте ветку для вашей функции (`git checkout -b feature/AmazingFeature`)
3. 💾 Зафиксируйте изменения (`git commit -m 'Add some AmazingFeature'`)
4. 📤 Отправьте в ветку (`git push origin feature/AmazingFeature`)
5. 🎉 Откройте Pull Request

### 📋 Требования к коду

- ✅ Следуйте PEP 8
- ✅ Добавьте тесты для новой функциональности
- ✅ Обновите документацию
- ✅ Убедитесь, что все тесты проходят

---

## 📊 Статистика проекта

- 📝 **15,000+** строк кода
- 🧪 **150+** тестов
- 📚 **25+** файлов документации
- ⭐ **98%** покрытие критического кода
- 🚀 **<100ms** среднее время отклика API

---

## 🗺️ Roadmap

### 🎯 Версия 2.0 (Q1 2024)

- [ ] 🎭 Поддержка 3D моделей
- [ ] 🌐 Интеграция с социальными сетями
- [ ] 📱 Мобильное приложение (iOS/Android)
- [ ] 🎨 Расширенный редактор анимаций
- [ ] 🔊 Поддержка аудио

### 🔮 Будущие планы

- [ ] 🤖 AI генерация анимаций
- [ ] 🌍 Мультиязычная поддержка
- [ ] 💳 Интеграция платежных систем
- [ ] 📈 Расширенная аналитика
- [ ] 🎮 Игровые элементы в AR

---

## 📜 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для деталей.

---

## 🙏 Благодарности

Большое спасибо всем, кто внес вклад в этот проект:

- 🌟 **FastAPI** - за потрясающий веб-фреймворк
- 🎯 **AR.js** - за упрощение AR для веба
- 🎨 **A-Frame** - за WebVR/AR возможности
- ✨ **Anime.js** - за плавные анимации
- 🐳 **Docker** - за упрощение развертывания

---

## 📞 Контакты

- 📧 Email: support@vertex-ar.example.com
- 🐦 Twitter: [@VertexAR](https://twitter.com/vertexar)
- 💬 Discord: [Vertex AR Community](https://discord.gg/vertexar)
- 📺 YouTube: [Vertex AR Channel](https://youtube.com/@vertexar)

---

## 💖 Поддержать проект

Если вам нравится этот проект, поставьте ⭐ на GitHub!

<div align="center">

**[⬆ Вернуться к началу](#-vertex-ar)**

Made with ❤️ by Vertex AR Team

</div>
