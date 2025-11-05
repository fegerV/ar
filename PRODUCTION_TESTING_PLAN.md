# 🧪 Production Testing Plan - Vertex AR

**Дата:** 2024-01-15  
**Версия:** 1.1.0  
**Цель:** Проверка готовности системы к production развертыванию

---

## 📋 ОБЗОР ТЕСТОВ

| Категория | Кол-во тестов | Статус | Время выполнения |
|-----------|---------------|--------|------------------|
| 🔐 Security Tests | 15 | 🟡 Частично | 2 часа |
| 🏗️ Infrastructure Tests | 10 | 🟡 Частично | 1 час |
| 📊 Performance Tests | 8 | 🔴 Не начаты | 3 часа |
| 🔄 Backup/Recovery Tests | 6 | 🔴 Не начаты | 2 часа |
| 📦 Deployment Tests | 12 | 🟡 Частично | 2 часа |
| 🧪 Functional Tests | 25 | 🟢 Готовы | 1 час |
| **ИТОГО** | **76** | **🟡 50%** | **11 часов** |

---

## 🔐 ТЕСТЫ БЕЗОПАСНОСТИ

### 1. Authentication Security Tests

#### 1.1 Rate Limiting Test
```bash
# Цель: Проверить ограничение запросов к auth эндпоинтам
# Ожидаемый результат: 429 Too Many Requests после 5 попыток

#!/bin/bash
echo "Testing rate limiting on /auth/login..."

for i in {1..10}; do
    response=$(curl -s -w "%{http_code}" -o /dev/null -X POST \
        http://localhost:8000/auth/login \
        -H "Content-Type: application/json" \
        -d '{"username":"test","password":"wrong"}')
    
    echo "Request $i: HTTP $response"
    sleep 0.1
done
```

**Критерии успеха:**
- [ ] Первые 5 запросов возвращают 401 или 200
- [ ] Запросы с 6-го возвращают 429
- [ ] Rate limit сбрасывается через 1 минуту

#### 1.2 Brute Force Protection Test
```bash
# Цель: Проверить защиту от подбора пароля
# Ожидаемый результат: Account lockout после 5 неудачных попыток

#!/bin/bash
echo "Testing brute force protection..."

for i in {1..7}; do
    response=$(curl -s -X POST \
        http://localhost:8000/auth/login \
        -H "Content-Type: application/json" \
        -d '{"username":"admin","password":"wrong'$i'"}')
    
    echo "Attempt $i: $response"
done

# Try correct password after lockout
response=$(curl -s -X POST \
    http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"correct_password"}')

echo "Login after lockout: $response"
```

**Критерии успеха:**
- [ ] После 5 неудачных попыток аккаунт блокируется
- [ ] Правильный пароль после блокировки не работает
- [ ] Разблокировка через заданное время

#### 1.3 JWT Token Security Test
```python
# test_jwt_security.py
import pytest
import jwt
import requests
from datetime import datetime, timedelta

def test_jwt_token_expiration():
    """Тест истечения срока действия JWT токена"""
    # Получаем токен
    response = requests.post("http://localhost:8000/auth/login", 
                           json={"username": "admin", "password": "password"})
    token = response.json()["access_token"]
    
    # Декодируем токен для проверки expiration
    decoded = jwt.decode(token, options={"verify_signature": False})
    exp = datetime.fromtimestamp(decoded["exp"])
    now = datetime.now()
    
    # Проверяем что срок действия разумный (не более 24 часов)
    assert (exp - now) <= timedelta(hours=24)
    assert (exp - now) > timedelta(minutes=1)

def test_jwt_token_invalid():
    """Тест невалидного JWT токена"""
    response = requests.get("http://localhost:8000/admin/stats",
                          headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401

def test_jwt_token_expired():
    """Тест просроченного JWT токена"""
    # Создаем просроченный токен
    expired_token = jwt.encode({
        "sub": "admin",
        "exp": datetime.now() - timedelta(hours=1)
    }, "secret", algorithm="HS256")
    
    response = requests.get("http://localhost:8000/admin/stats",
                          headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
```

### 2. Input Validation Tests

#### 2.1 SQL Injection Test
```python
# test_sql_injection.py
import requests

def test_sql_injection_prevention():
    """Тест защиты от SQL инъекций"""
    malicious_inputs = [
        "'; DROP TABLE users; --",
        "' OR '1'='1",
        "admin' --",
        "' UNION SELECT * FROM users --"
    ]
    
    for payload in malicious_inputs:
        # Test login endpoint
        response = requests.post("http://localhost:8000/auth/login",
                               json={"username": payload, "password": "password"})
        assert response.status_code in [400, 401, 422]
        
        # Test search endpoints if exist
        response = requests.get(f"http://localhost:8000/ar/search?q={payload}")
        assert response.status_code != 500

def test_xss_prevention():
    """Тест защиты от XSS атак"""
    xss_payloads = [
        "<script>alert('xss')</script>",
        "javascript:alert('xss')",
        "<img src=x onerror=alert('xss')>",
        "';alert('xss');//"
    ]
    
    for payload in xss_payloads:
        # Test upload with malicious filename
        files = {'image': (payload, 'fake content', 'image/jpeg')}
        response = requests.post("http://localhost:8000/ar/upload", files=files)
        assert response.status_code in [400, 422]
```

#### 2.2 File Upload Security Test
```python
# test_file_upload_security.py
import requests
import io

def test_malicious_file_upload():
    """Тест загрузки вредоносных файлов"""
    malicious_files = [
        ("malicious.exe", b"MZ\x90\x00", "application/octet-stream"),
        ("script.php", b"<?php system($_GET['cmd']); ?>", "application/x-php"),
        ("shell.sh", b"#!/bin/bash\nrm -rf /", "application/x-sh"),
        ("huge_file.jpg", b"A" * (100 * 1024 * 1024), "image/jpeg")  # 100MB
    ]
    
    for filename, content, content_type in malicious_files:
        files = {'image': (filename, io.BytesIO(content), content_type)}
        response = requests.post("http://localhost:8000/ar/upload", files=files)
        assert response.status_code in [400, 413, 422]

def test_file_type_validation():
    """Тест валидации типов файлов"""
    invalid_types = [
        ("document.pdf", b"%PDF-1.4", "application/pdf"),
        ("archive.zip", b"PK\x03\x04", "application/zip"),
        ("script.js", b"console.log('test')", "application/javascript")
    ]
    
    for filename, content, content_type in invalid_types:
        files = {'image': (filename, io.BytesIO(content), content_type)}
        response = requests.post("http://localhost:8000/ar/upload", files=files)
        assert response.status_code in [400, 422]
```

---

## 📊 ТЕСТЫ ПРОИЗВОДИТЕЛЬНОСТИ

### 1. Load Testing

#### 1.1 Concurrent Users Test
```python
# test_load_performance.py
import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor

async def make_request(session, url, method="GET", data=None):
    """Выполнить HTTP запрос"""
    start_time = time.time()
    try:
        if method == "GET":
            async with session.get(url) as response:
                await response.text()
                return response.status, time.time() - start_time
        elif method == "POST":
            async with session.post(url, json=data) as response:
                await response.text()
                return response.status, time.time() - start_time
    except Exception as e:
        return 500, time.time() - start_time

async def test_concurrent_users():
    """Тест производительности при одновременных пользователях"""
    concurrent_users = [10, 50, 100, 200]
    
    for users in concurrent_users:
        print(f"\nTesting with {users} concurrent users...")
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for _ in range(users):
                tasks.append(make_request(session, "http://localhost:8000/ar/list"))
            
            results = await asyncio.gather(*tasks)
            
            # Анализ результатов
            successful = sum(1 for status, _ in results if status == 200)
            failed = users - successful
            avg_response_time = sum(time for _, time in results) / users
            
            print(f"  Successful: {successful}/{users}")
            print(f"  Failed: {failed}")
            print(f"  Avg Response Time: {avg_response_time:.3f}s")
            
            # Критерии успеха
            assert successful >= users * 0.95, f"Too many failures: {failed}/{users}"
            assert avg_response_time < 2.0, f"Response too slow: {avg_response_time}s"

def test_upload_performance():
    """Тест производительности загрузки файлов"""
    file_sizes = [1, 5, 10, 25]  # MB
    
    for size_mb in file_sizes:
        print(f"\nTesting upload of {size_mb}MB file...")
        
        # Создаем тестовый файл
        file_content = b"A" * (size_mb * 1024 * 1024)
        files = {'image': (f'test_{size_mb}mb.jpg', file_content, 'image/jpeg')}
        
        start_time = time.time()
        response = requests.post("http://localhost:8000/ar/upload", files=files)
        upload_time = time.time() - start_time
        
        print(f"  Upload time: {upload_time:.3f}s")
        print(f"  Status: {response.status_code}")
        
        # Критерии успеха
        assert response.status_code == 200, f"Upload failed: {response.status_code}"
        assert upload_time < size_mb * 0.5, f"Upload too slow: {upload_time}s"
```

#### 1.2 Stress Testing
```python
# test_stress_performance.py
import time
import psutil
import requests

def test_memory_usage():
    """Тест использования памяти"""
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Выполняем 1000 запросов
    for i in range(1000):
        response = requests.get("http://localhost:8000/ar/list")
        assert response.status_code == 200
        
        if i % 100 == 0:
            current_memory = process.memory_info().rss / 1024 / 1024
            print(f"Request {i}: Memory usage: {current_memory:.1f}MB")
    
    final_memory = process.memory_info().rss / 1024 / 1024
    memory_increase = final_memory - initial_memory
    
    print(f"Initial memory: {initial_memory:.1f}MB")
    print(f"Final memory: {final_memory:.1f}MB")
    print(f"Memory increase: {memory_increase:.1f}MB")
    
    # Критерий успеха: рост памяти не более 100MB
    assert memory_increase < 100, f"Memory leak detected: {memory_increase}MB increase"

def test_cpu_usage():
    """Тест использования CPU"""
    process = psutil.Process()
    
    # Измеряем CPU во время нагрузки
    start_time = time.time()
    cpu_samples = []
    
    while time.time() - start_time < 60:  # 1 минута
        cpu_percent = process.cpu_percent()
        cpu_samples.append(cpu_percent)
        time.sleep(1)
        
        # Выполняем запрос
        requests.get("http://localhost:8000/ar/list")
    
    avg_cpu = sum(cpu_samples) / len(cpu_samples)
    max_cpu = max(cpu_samples)
    
    print(f"Average CPU usage: {avg_cpu:.1f}%")
    print(f"Max CPU usage: {max_cpu:.1f}%")
    
    # Критерии успеха
    assert avg_cpu < 50, f"High average CPU usage: {avg_cpu}%"
    assert max_cpu < 80, f"High peak CPU usage: {max_cpu}%"
```

---

## 🔄 ТЕСТЫ РЕЗЕРВНОГО КОПИРОВАНИЯ

### 1. Backup Creation Test
```bash
#!/bin/bash
# test_backup_creation.sh

echo "Testing backup creation..."

# Запускаем backup скрипт
./scripts/backup.sh

# Проверяем что backup файлы созданы
LATEST_DB=$(ls -t backups/db_backup_*.db | head -1)
LATEST_STORAGE=$(ls -t backups/storage_backup_*.tar.gz | head -1)

if [ -f "$LATEST_DB" ]; then
    echo "✅ Database backup created: $LATEST_DB"
    
    # Проверяем размер файла
    DB_SIZE=$(stat -f%z "$LATEST_DB" 2>/dev/null || stat -c%s "$LATEST_DB")
    ORIGINAL_DB_SIZE=$(stat -f%z "vertex-ar/app_data.db" 2>/dev/null || stat -c%s "vertex-ar/app_data.db")
    
    if [ "$DB_SIZE" -eq "$ORIGINAL_DB_SIZE" ]; then
        echo "✅ Database backup size matches original"
    else
        echo "❌ Database backup size mismatch"
        exit 1
    fi
else
    echo "❌ Database backup not created"
    exit 1
fi

if [ -f "$LATEST_STORAGE" ]; then
    echo "✅ Storage backup created: $LATEST_STORAGE"
else
    echo "❌ Storage backup not created"
    exit 1
fi

echo "✅ Backup creation test passed"
```

### 2. Backup Restore Test
```bash
#!/bin/bash
# test_backup_restore.sh

echo "Testing backup restore..."

# Создаем тестовые данные
curl -X POST http://localhost:8000/auth/register \
    -H "Content-Type: application/json" \
    -d '{"username":"test_restore_user","password":"test_password"}'

# Создаем backup
./scripts/backup.sh
BACKUP_DB=$(ls -t backups/db_backup_*.db | head -1)

# Останавливаем приложение
docker compose down

# Восстанавливаем базу данных
cp "$BACKUP_DB" vertex-ar/app_data.db

# Запускаем приложение
docker compose up -d

# Ждем запуска
sleep 10

# Проверяем что пользователь восстановлен
response=$(curl -s -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"test_restore_user","password":"test_password"}')

if echo "$response" | grep -q "access_token"; then
    echo "✅ User data restored successfully"
else
    echo "❌ User data restore failed"
    exit 1
fi

echo "✅ Backup restore test passed"
```

---

## 📦 ТЕСТЫ РАЗВЕРТЫВАНИЯ

### 1. Docker Deployment Test
```bash
#!/bin/bash
# test_docker_deployment.sh

echo "Testing Docker deployment..."

# Очищаем предыдущие контейнеры
docker compose down -v
docker system prune -f

# Собираем образы
echo "Building Docker images..."
docker compose build

# Запускаем сервисы
echo "Starting services..."
docker compose up -d

# Ждем запуска
echo "Waiting for services to start..."
sleep 30

# Проверяем health checks
echo "Checking service health..."

# Проверка приложения
app_health=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ "$app_health" = "200" ]; then
    echo "✅ Application health check passed"
else
    echo "❌ Application health check failed: $app_health"
    exit 1
fi

# Проверка Nginx
nginx_health=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/)
if [ "$nginx_health" = "200" ]; then
    echo "✅ Nginx health check passed"
else
    echo "❌ Nginx health check failed: $nginx_health"
    exit 1
fi

# Проверка статуса контейнеров
container_status=$(docker compose ps --format "table {{.Name}}\t{{.Status}}")
echo "Container status:"
echo "$container_status"

# Проверяем что все контейнеры работают
if echo "$container_status" | grep -q "Up"; then
    echo "✅ All containers are running"
else
    echo "❌ Some containers are not running"
    exit 1
fi

echo "✅ Docker deployment test passed"
```

### 2. SSL/TLS Test
```bash
#!/bin/bash
# test_ssl_configuration.sh

echo "Testing SSL/TLS configuration..."

# Проверяем HTTPS доступ
https_response=$(curl -s -o /dev/null -w "%{http_code}" https://localhost -k)
if [ "$https_response" = "200" ]; then
    echo "✅ HTTPS access working"
else
    echo "❌ HTTPS access failed: $https_response"
    exit 1
fi

# Проверяем SSL certificate
ssl_info=$(openssl s_client -connect localhost:443 -servername localhost 2>/dev/null | openssl x509 -noout -dates)
if echo "$ssl_info" | grep -q "notAfter"; then
    echo "✅ SSL certificate is valid"
    echo "Certificate dates:"
    echo "$ssl_info"
else
    echo "❌ SSL certificate issue"
    exit 1
fi

# Проверяем redirect с HTTP на HTTPS
http_response=$(curl -s -o /dev/null -w "%{redirect_url}" http://localhost)
if echo "$http_response" | grep -q "https://"; then
    echo "✅ HTTP to HTTPS redirect working"
else
    echo "❌ HTTP to HTTPS redirect not working"
    exit 1
fi

echo "✅ SSL/TLS configuration test passed"
```

---

## 🏗️ ТЕСТЫ ИНФРАСТРУКТУРЫ

### 1. Resource Limits Test
```python
# test_resource_limits.py
import docker
import time

def test_container_resource_limits():
    """Тест лимитов ресурсов контейнеров"""
    client = docker.from_env()
    
    # Получаем информацию о контейнере приложения
    container = client.containers.get("vertex_ar_app_simplified")
    
    # Проверяем memory limit
    stats = container.stats(stream=False)
    memory_usage = stats['memory_stats']['usage']
    memory_limit = stats['memory_stats']['limit']
    memory_percent = (memory_usage / memory_limit) * 100
    
    print(f"Memory usage: {memory_usage / 1024 / 1024:.1f}MB")
    print(f"Memory limit: {memory_limit / 1024 / 1024:.1f}MB")
    print(f"Memory usage percent: {memory_percent:.1f}%")
    
    # Критерий успеха: использование памяти не более 80%
    assert memory_percent < 80, f"Memory usage too high: {memory_percent}%"
    
    # Проверяем CPU limit
    cpu_usage = stats['cpu_stats']['cpu_usage']['total_usage']
    cpu_limit = stats['cpu_stats']['system_cpu_usage']
    
    print(f"CPU usage: {cpu_usage}")
    print(f"CPU system usage: {cpu_limit}")

def test_volume_mounts():
    """Тест монтирования томов"""
    client = docker.from_env()
    container = client.containers.get("vertex_ar_app_simplified")
    
    # Проверяем что storage смонтирован
    mounts = container.attrs['Mounts']
    storage_mounted = any(
        mount['Destination'] == '/app/storage' 
        for mount in mounts
    )
    
    assert storage_mounted, "Storage volume not mounted"
    print("✅ Storage volume properly mounted")
    
    # Проверяем что база данных смонтирована
    db_mounted = any(
        mount['Destination'] == '/app/app_data.db' 
        for mount in mounts
    )
    
    assert db_mounted, "Database volume not mounted"
    print("✅ Database volume properly mounted")
```

---

## 📋 ПОЛНЫЙ ТЕСТОВЫЙ RUN

### Запуск всех тестов
```bash
#!/bin/bash
# run_all_production_tests.sh

echo "🚀 Starting Production Readiness Tests..."
echo "========================================"

# Создаем директорию для результатов
mkdir -p test_results
TEST_START_TIME=$(date +%Y%m%d_%H%M%S)

# 1. Security Tests
echo "🔐 Running Security Tests..."
python test_jwt_security.py > test_results/security_jwt_$TEST_START_TIME.log 2>&1
python test_sql_injection.py > test_results/security_sql_$TEST_START_TIME.log 2>&1
python test_file_upload_security.py > test_results/security_files_$TEST_START_TIME.log 2>&1

# 2. Performance Tests
echo "📊 Running Performance Tests..."
python test_load_performance.py > test_results/performance_load_$TEST_START_TIME.log 2>&1
python test_stress_performance.py > test_results/performance_stress_$TEST_START_TIME.log 2>&1

# 3. Backup Tests
echo "🔄 Running Backup Tests..."
./test_backup_creation.sh > test_results/backup_create_$TEST_START_TIME.log 2>&1
./test_backup_restore.sh > test_results/backup_restore_$TEST_START_TIME.log 2>&1

# 4. Deployment Tests
echo "📦 Running Deployment Tests..."
./test_docker_deployment.sh > test_results/deployment_docker_$TEST_START_TIME.log 2>&1
./test_ssl_configuration.sh > test_results/deployment_ssl_$TEST_START_TIME.log 2>&1

# 5. Infrastructure Tests
echo "🏗️ Running Infrastructure Tests..."
python test_resource_limits.py > test_results/infrastructure_resources_$TEST_START_TIME.log 2>&1

# 6. Functional Tests
echo "🧪 Running Functional Tests..."
python test_api_endpoints.py > test_results/functional_api_$TEST_START_TIME.log 2>&1
python test_ar_functionality.py > test_results/functional_ar_$TEST_START_TIME.log 2>&1

echo "========================================"
echo "✅ All tests completed!"
echo "📁 Results saved in test_results/"

# Генерируем отчет
cat > test_results/summary_$TEST_START_TIME.md << EOF
# Production Test Results

**Date:** $(date)  
**Test Run:** $TEST_START_TIME

## Test Categories
- [x] Security Tests
- [x] Performance Tests  
- [x] Backup Tests
- [x] Deployment Tests
- [x] Infrastructure Tests
- [x] Functional Tests

## Detailed Results
See individual log files in this directory.

## Next Steps
1. Review any failed tests
2. Fix identified issues
3. Re-run failed tests
4. Prepare production deployment
EOF

echo "📄 Summary report generated: test_results/summary_$TEST_START_TIME.md"
```

---

## 📊 КРИТЕРИИ УСПЕХА

### Production Ready Criteria
- [ ] **100%** Security tests pass
- [ ] **95%** Performance tests meet requirements
- [ ] **100%** Backup/Restore tests pass
- [ ] **100%** Deployment tests pass
- [ ] **100%** Infrastructure tests pass
- [ ] **98%** Functional tests pass

### Performance Benchmarks
- [ ] Response time < 200ms (p95)
- [ ] 100+ concurrent users supported
- [ ] Memory usage < 1GB
- [ ] CPU usage < 50% average
- [ ] Upload speed > 10MB/s for 25MB files

### Security Requirements
- [ ] Rate limiting active
- [ ] Brute force protection working
- [ ] Input validation comprehensive
- [ ] File upload security enforced
- [ ] JWT tokens properly secured

---

**⚠️ ВАЖНО:** Все тесты должны быть выполнены в production-like среде перед развертыванием. Любые неудачные тесты должны быть проанализированы и исправлены.