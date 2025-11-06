# Примеры использования API Vertex AR

Ниже приведены основные сценарии работы с API. Все запросы выполняются к `http://localhost:8000`. Замените значения токенов и файлов на свои.

---

## 1. Получение токена

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "secret123"}'
```

Ответ:
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

## 2. Создание клиента

```bash
curl -X POST http://localhost:8000/api/clients \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "name": "Мария Иванова",
        "phone": "+79991234567"
      }'
```

---

## 3. Загрузка портрета и генерация маркеров

```bash
curl -X POST http://localhost:8000/api/portraits \
  -H "Authorization: Bearer $TOKEN" \
  -F "client_id=1" \
  -F "image=@/path/to/portrait.jpg" \
  -F "marker_preset=high"
```

Ответ содержит идентификатор портрета, постоянную ссылку и данные маркера.

---

## 4. Загрузка видео и активация

```bash
curl -X POST http://localhost:8000/api/videos \
  -H "Authorization: Bearer $TOKEN" \
  -F "portrait_id=12" \
  -F "video=@/path/to/video.mp4"

curl -X POST http://localhost:8000/api/videos/45/activate \
  -H "Authorization: Bearer $TOKEN"
```

---

## 5. Batch-генерация NFT-маркеров

```bash
curl -X POST http://localhost:8000/api/nft-markers/batch-generate \
  -H "Authorization: Bearer $TOKEN" \
  -F "images=@/img/portrait1.jpg" \
  -F "images=@/img/portrait2.jpg" \
  -F "preset=high" \
  -F "async=false"
```

Ответ:
```json
{
  "processed": 2,
  "failed": [],
  "duration_ms": 7120,
  "markers": [
    {
      "filename": "portrait1.jpg",
      "marker_id": "bf1c...",
      "quality": "high",
      "feature_points": 567
    },
    {
      "filename": "portrait2.jpg",
      "marker_id": "c93a...",
      "quality": "high",
      "feature_points": 612
    }
  ]
}
```

---

## 6. Python-клиент (requests)

```python
import requests

BASE_URL = "http://localhost:8000"

def login(username: str, password: str) -> str:
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "username": username,
        "password": password,
    })
    resp.raise_for_status()
    return resp.json()["access_token"]

def create_client(token: str, name: str, phone: str) -> dict:
    resp = requests.post(
        f"{BASE_URL}/api/clients",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "phone": phone},
    )
    resp.raise_for_status()
    return resp.json()

if __name__ == "__main__":
    token = login("admin", "secret123")
    client = create_client(token, "Студия AR", "+79991112233")
    print("Создан клиент", client)
```

---

## 7. Получение аналитики по маркерам

```bash
curl -X GET http://localhost:8000/api/nft-markers/analytics \
  -H "Authorization: Bearer $TOKEN"
```

Ответ содержит данные о скорости генерации, hit-rate кэша, распределение по preset’ам.

---

## 8. Просмотр AR-контента

```bash
# Откройте в браузере
http://localhost:8000/portrait/4a2c8bc0-21da-43df-915d-55b2a3c2a1d5

# Получите QR-код
curl -X GET http://localhost:8000/qr/4a2c8bc0-21da-43df-915d-55b2a3c2a1d5 --output qr.png
```

---

## 9. Обработка ошибок

```bash
curl -X POST http://localhost:8000/api/clients \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Мария", "phone": "123"}'
```

Ответ 422:
```json
{
  "detail": "Неверный формат телефона",
  "code": "validation_error",
  "fields": {
    "phone": ["Должен содержать 11 цифр и начинаться с +7"]
  },
  "request_id": "9b92..."
}
```

---

## 10. Автоматизация

- Планируйте повторные запросы при ответах 429, 502, 503.  
- Храните токены в безопасном месте и обновляйте их заранее.  
- Для интеграций используйте сервисные аккаунты с ограниченными правами.

Больше примеров вы найдёте в репозитории `examples/` (если доступно) и в `tests/`.
