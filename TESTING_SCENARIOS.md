# 🎯 Тестовые сценарии Vertex AR

Этот документ содержит готовые тестовые сценарии для проверки функциональности проекта Vertex AR.

---

## 📋 Содержание

1. [Базовые сценарии](#базовые-сценарии)
2. [Полный цикл работы](#полный-цикл-работы)
3. [Негативные сценарии](#негативные-сценарии)
4. [Performance сценарии](#performance-сценарии)
5. [Security сценарии](#security-сценарии)

---

## 🔰 Базовые сценарии

### Сценарий 1: Первый запуск приложения

**Цель:** Проверить что приложение запускается и доступно

```bash
# Шаг 1: Активируйте виртуальное окружение
source .venv/bin/activate

# Шаг 2: Запустите приложение
cd vertex-ar
uvicorn app.main:app --reload

# Шаг 3: Проверьте доступность
curl http://localhost:8000/health

# Ожидаемый результат:
# {"status": "healthy", "version": "1.3.0"}
```

### Сценарий 2: Проверка документации API

**Цель:** Убедиться что Swagger UI работает

```bash
# Откройте в браузере
open http://localhost:8000/docs

# Проверьте что видны все endpoint группы:
# ✓ auth - Authentication
# ✓ users - User Management
# ✓ clients - Client Management
# ✓ portraits - Portrait Management
# ✓ videos - Video Management
# ✓ nft-markers - NFT Marker Generation
# ✓ ar - AR Viewing
```

### Сценарий 3: Запуск базовых тестов

**Цель:** Проверить что тестовая инфраструктура работает

```bash
# Запустите только unit тесты
pytest -m unit -v

# Ожидаемый результат: все unit тесты должны пройти
# Expected: PASSED (X tests)
```

---

## 🔄 Полный цикл работы

### Сценарий 4: Регистрация и аутентификация

**Цель:** Полный цикл создания и входа пользователя

```bash
# Шаг 1: Регистрация нового пользователя
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "demo_user",
    "password": "DemoPass123!",
    "email": "demo@example.com",
    "full_name": "Demo User"
  }'

# Ожидаемый результат: 200 OK
# {
#   "id": 1,
#   "username": "demo_user",
#   "email": "demo@example.com",
#   "full_name": "Demo User",
#   "is_active": true,
#   "created_at": "2024-11-09T..."
# }

# Шаг 2: Вход в систему
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "demo_user",
    "password": "DemoPass123!"
  }'

# Ожидаемый результат: JWT токен
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "token_type": "bearer"
# }

# Шаг 3: Сохраните токен
export TOKEN="<ваш_токен_здесь>"

# Шаг 4: Проверьте профиль
curl -X GET http://localhost:8000/api/users/me \
  -H "Authorization: Bearer $TOKEN"

# Ожидаемый результат: Информация о текущем пользователе
```

### Сценарий 5: Создание клиента и портрета

**Цель:** Полный цикл создания клиента и загрузки портрета

```bash
# Предварительное условие: вы авторизованы (TOKEN установлен)

# Шаг 1: Создайте клиента
curl -X POST http://localhost:8000/api/clients/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Иван Петров",
    "phone": "+79991234567",
    "email": "ivan@example.com"
  }'

# Ожидаемый результат: 201 Created
# {
#   "id": 1,
#   "name": "Иван Петров",
#   "phone": "+79991234567",
#   "email": "ivan@example.com",
#   "created_at": "..."
# }

# Шаг 2: Сохраните client_id
export CLIENT_ID=1

# Шаг 3: Создайте тестовое изображение (если нет)
mkdir -p test_files
# Скопируйте любое JPG изображение в test_files/portrait.jpg

# Шаг 4: Загрузите портрет
curl -X POST http://localhost:8000/api/portraits/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "client_id=$CLIENT_ID" \
  -F "file=@test_files/portrait.jpg"

# Ожидаемый результат: 201 Created
# {
#   "id": 1,
#   "client_id": 1,
#   "filename": "portrait.jpg",
#   "file_path": "/storage/portraits/...",
#   "created_at": "..."
# }

# Шаг 5: Получите список портретов
curl -X GET http://localhost:8000/api/portraits/ \
  -H "Authorization: Bearer $TOKEN"

# Ожидаемый результат: массив портретов
```

### Сценарий 6: Загрузка видео и генерация NFT маркера

**Цель:** Полный AR pipeline

```bash
# Предварительное условие: портрет создан (PORTRAIT_ID установлен)
export PORTRAIT_ID=1

# Шаг 1: Загрузите видео
curl -X POST http://localhost:8000/api/videos/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "portrait_id=$PORTRAIT_ID" \
  -F "file=@test_files/video.mp4"

# Ожидаемый результат: 201 Created

# Шаг 2: Сгенерируйте NFT маркер
curl -X POST http://localhost:8000/api/nft-markers/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"portrait_id\": $PORTRAIT_ID}"

# Ожидаемый результат: 200 OK
# {
#   "portrait_id": 1,
#   "marker_path": "/storage/markers/...",
#   "generated_at": "...",
#   "generation_time": 3.5
# }

# Шаг 3: Получите QR код для просмотра
curl -X GET http://localhost:8000/api/portraits/$PORTRAIT_ID/qr \
  -H "Authorization: Bearer $TOKEN" \
  --output qr_code.png

# Шаг 4: Откройте QR код
open qr_code.png  # macOS
# xdg-open qr_code.png  # Linux
# start qr_code.png  # Windows

# Шаг 5: Отсканируйте QR код камерой телефона
# Вас перенаправит на AR viewer
```

---

## ⚠️ Негативные сценарии

### Сценарий 7: Невалидные данные при регистрации

**Цель:** Проверить валидацию пользовательских данных

```bash
# Тест 1: Слишком короткий пароль
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "123",
    "email": "test@example.com"
  }'

# Ожидаемый результат: 422 Unprocessable Entity
# {
#   "detail": "Password must be at least 8 characters..."
# }

# Тест 2: Невалидный email
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "ValidPass123!",
    "email": "invalid-email"
  }'

# Ожидаемый результат: 422 Unprocessable Entity

# Тест 3: Дубликат username
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "demo_user",
    "password": "ValidPass123!",
    "email": "another@example.com"
  }'

# Ожидаемый результат: 400 Bad Request
# {
#   "detail": "Username already exists"
# }
```

### Сценарий 8: Попытка доступа без авторизации

**Цель:** Проверить защиту endpoints

```bash
# Попытка получить профиль без токена
curl -X GET http://localhost:8000/api/users/me

# Ожидаемый результат: 401 Unauthorized
# {
#   "detail": "Not authenticated"
# }

# Попытка создать клиента без токена
curl -X POST http://localhost:8000/api/clients/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Client",
    "phone": "+1234567890"
  }'

# Ожидаемый результат: 401 Unauthorized
```

### Сценарий 9: Неправильные учётные данные

**Цель:** Проверить механизм блокировки после множественных ошибок

```bash
# Попытка 1-5: Неправильный пароль
for i in {1..5}; do
  echo "Attempt $i"
  curl -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -d '{
      "username": "demo_user",
      "password": "WrongPassword"
    }'
  echo ""
done

# Ожидаемый результат (после 5 попыток): 429 Too Many Requests
# {
#   "detail": "Account locked due to too many failed login attempts"
# }

# Проверка что даже правильный пароль не работает
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "demo_user",
    "password": "DemoPass123!"
  }'

# Ожидаемый результат: 429 Too Many Requests (аккаунт заблокирован)
```

### Сценарий 10: Загрузка невалидных файлов

**Цель:** Проверить валидацию файлов

```bash
# Тест 1: Слишком большой файл
# Создайте файл >10MB
dd if=/dev/zero of=large_file.jpg bs=1M count=15

curl -X POST http://localhost:8000/api/portraits/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "client_id=1" \
  -F "file=@large_file.jpg"

# Ожидаемый результат: 413 Payload Too Large

# Тест 2: Неправильный тип файла
echo "Not an image" > fake_image.txt
curl -X POST http://localhost:8000/api/portraits/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "client_id=1" \
  -F "file=@fake_image.txt"

# Ожидаемый результат: 400 Bad Request
# {
#   "detail": "Invalid file type. Only JPG, PNG allowed"
# }

# Очистка
rm large_file.jpg fake_image.txt
```

---

## ⚡ Performance сценарии

### Сценарий 11: Нагрузочное тестирование с Locust

**Цель:** Проверить производительность под нагрузкой

```bash
# Шаг 1: Установите Locust (если не установлен)
pip install locust

# Шаг 2: Запустите приложение
cd vertex-ar
uvicorn app.main:app &
APP_PID=$!

# Шаг 3: Создайте тестового пользователя для нагрузочного теста
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "readonly",
    "password": "readonly123",
    "email": "readonly@example.com"
  }'

# Шаг 4: Запустите Locust
cd ..
locust -f locustfile.py --host=http://localhost:8000

# Шаг 5: Откройте UI в браузере
open http://localhost:8089

# Шаг 6: Настройте тест
# - Number of users: 50
# - Spawn rate: 5
# - Run time: 60 seconds

# Шаг 7: Анализируйте результаты
# Смотрите на:
# - Requests per second (RPS)
# - Response time (median, 95th percentile)
# - Failure rate (должен быть <1%)

# Шаг 8: Остановите приложение
kill $APP_PID
```

### Сценарий 12: Тест генерации NFT маркеров

**Цель:** Измерить производительность генератора маркеров

```bash
# Запустите специальный performance тест
pytest test_comprehensive_performance.py::test_nft_generation_performance -v -s

# Ожидаемые результаты:
# - Среднее время генерации: < 5 секунд
# - 95th percentile: < 7 секунд
# - Нет ошибок генерации
```

### Сценарий 13: Тест множественной загрузки файлов

**Цель:** Проверить работу с множественными загрузками

```bash
# Создайте скрипт для параллельных загрузок
cat > parallel_upload_test.sh << 'EOF'
#!/bin/bash
TOKEN="$1"
CLIENT_ID="$2"

for i in {1..10}; do
  (
    curl -X POST http://localhost:8000/api/portraits/ \
      -H "Authorization: Bearer $TOKEN" \
      -F "client_id=$CLIENT_ID" \
      -F "file=@test_files/portrait.jpg" \
      -w "\nTime: %{time_total}s\n"
  ) &
done

wait
echo "All uploads completed"
EOF

chmod +x parallel_upload_test.sh

# Запустите тест
./parallel_upload_test.sh "$TOKEN" "$CLIENT_ID"

# Проверьте что все файлы загружены
curl -X GET http://localhost:8000/api/portraits/ \
  -H "Authorization: Bearer $TOKEN" | jq 'length'

# Очистка
rm parallel_upload_test.sh
```

---

## 🔒 Security сценарии

### Сценарий 14: SQL Injection попытки

**Цель:** Проверить защиту от SQL инъекций

```bash
# Попытка SQL injection в username
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin'\'' OR 1=1--",
    "password": "anything"
  }'

# Ожидаемый результат: 401 Unauthorized (не успех)

# Попытка в поле поиска
curl -X GET "http://localhost:8000/api/clients/?search=test'; DROP TABLE users;--" \
  -H "Authorization: Bearer $TOKEN"

# Ожидаемый результат: Безопасная обработка, таблица НЕ удалена
```

### Сценарий 15: XSS попытки

**Цель:** Проверить санитизацию пользовательского ввода

```bash
# Попытка XSS в имени клиента
curl -X POST http://localhost:8000/api/clients/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "<script>alert('XSS')</script>",
    "phone": "+1234567890",
    "email": "test@example.com"
  }'

# Проверьте что данные экранированы
curl -X GET http://localhost:8000/api/clients/ \
  -H "Authorization: Bearer $TOKEN"

# Ожидаемый результат: HTML теги должны быть экранированы
```

### Сценарий 16: Rate Limiting

**Цель:** Проверить работу ограничения частоты запросов

```bash
# Быстрые последовательные запросы
for i in {1..150}; do
  curl -s -X GET http://localhost:8000/health -w "%{http_code}\n" -o /dev/null
done | sort | uniq -c

# Ожидаемый результат:
# - Первые 100 запросов: 200 OK
# - Остальные: 429 Too Many Requests
```

### Сценарий 17: CORS проверка

**Цель:** Проверить настройки CORS

```bash
# Запрос с правильным origin
curl -X GET http://localhost:8000/health \
  -H "Origin: http://localhost:8000" \
  -H "Access-Control-Request-Method: GET" \
  -I

# Ожидаемый результат: Access-Control-Allow-Origin header присутствует

# Запрос с неправильным origin
curl -X GET http://localhost:8000/health \
  -H "Origin: http://evil.com" \
  -H "Access-Control-Request-Method: GET" \
  -I

# Ожидаемый результат: CORS error (Access-Control-Allow-Origin отсутствует)
```

---

## 🧪 Автоматизированные тестовые наборы

### Запуск всех сценариев через pytest

```bash
# Базовые функциональные тесты
pytest -m "unit or integration" -v

# AR функциональность
pytest -m ar -v

# Security тесты
pytest -m security -v

# Performance тесты
pytest -m performance -v

# Полный набор
pytest -v --cov=vertex-ar --cov-report=html
```

### Проверка production readiness

```bash
# Запустите скрипт проверки готовности
./check_production_readiness.sh

# Ожидаемый результат:
# ✓ All critical checks passed
# Production Readiness: 97%
```

---

## 📊 Интерпретация результатов

### Успешный тест

```
✓ Status: 200 OK / 201 Created
✓ Response time: < 200ms
✓ Valid JSON response
✓ Correct data structure
✓ No errors in logs
```

### Проваленный тест

```
✗ Unexpected status code
✗ Response time > 1s
✗ Invalid or missing data
✗ Errors/warnings in logs
✗ Memory/resource leaks
```

### Граничные значения производительности

- **API Response Time:**
  - Good: < 100ms
  - Acceptable: 100-300ms
  - Bad: > 300ms

- **NFT Generation:**
  - Good: < 3s
  - Acceptable: 3-5s
  - Bad: > 5s

- **File Upload:**
  - Good: < 1s для 1MB
  - Acceptable: 1-3s для 1MB
  - Bad: > 3s для 1MB

---

## 🔄 Регрессионное тестирование

### После каждого изменения кода

```bash
# Быстрая проверка
pytest -m "not slow" -v

# Полная проверка (перед commit)
pytest -v
./run_tests.sh coverage
```

### Перед релизом

```bash
# 1. Все тесты
pytest -v

# 2. Performance тесты
pytest -m performance
./run_performance_tests.sh

# 3. Security audit
bandit -r vertex-ar/
safety check

# 4. Production readiness
./check_production_readiness.sh

# 5. Manual smoke test
# Пройдите сценарии 4, 5, 6 вручную
```

---

## 🆘 Troubleshooting

### Если тесты падают

1. **Проверьте виртуальное окружение:**
   ```bash
   which python
   # Должно показать путь внутри .venv
   ```

2. **Переустановите зависимости:**
   ```bash
   pip install -r vertex-ar/requirements.txt --force-reinstall
   ```

3. **Очистите тестовые данные:**
   ```bash
   rm test_app_data.db
   rm -rf test_storage/
   ```

4. **Проверьте логи:**
   ```bash
   tail -f logs/app.log
   ```

5. **Запустите с debug:**
   ```bash
   pytest -vv -s --log-cli-level=DEBUG test_file.py::test_name
   ```

---

## 📚 Дополнительные ресурсы

- [LOCAL_TESTING_GUIDE.md](LOCAL_TESTING_GUIDE.md) - Подробное руководство
- [TESTING_REPORT.md](TESTING_REPORT.md) - Отчёт о тестировании
- [API Documentation](http://localhost:8000/docs) - Swagger UI
- [pytest documentation](https://docs.pytest.org/)
- [Locust documentation](https://docs.locust.io/)

---

**Happy Testing! 🚀**
