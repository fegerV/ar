# Vertex AR - Примеры использования API

## 📋 Оглавление

1. [Введение](#введение)
2. [Базовая аутентификация](#базовая-аутентификация)
3. [Работа с AR-контентом](#работа-с-ar-контентом)
4. [Административные функции](#административные-функции)
5. [Интеграция в приложения](#интеграция-в-приложения)
6. [Примеры на разных языках](#примеры-на-разных-языках)
7. [Обработка ошибок](#обработка-ошибок)
8. [Best Practices](#best-practices)

---

## 🎯 Введение

Это руководство содержит практические примеры использования Vertex AR API.

### Базовая информация

**Base URL:**
```
Development: http://localhost:8000
Production: https://yourdomain.com
```

**Аутентификация:**
```
Authorization: Bearer <access_token>
```

### Инструменты для тестирования

- **curl** - командная строка
- **httpie** - улучшенный HTTP клиент
- **Postman** - GUI клиент
- **Insomnia** - альтернатива Postman
- **Python requests** - для скриптов
- **JavaScript fetch** - для веб-приложений

---

## 🔐 Базовая аутентификация

### Регистрация нового пользователя

#### curl

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "SecurePassword123!"
  }'
```

**Ответ:**
```json
{
  "username": "john_doe"
}
```

#### httpie

```bash
http POST http://localhost:8000/auth/register \
  username=john_doe \
  password=SecurePassword123!
```

#### Python

```python
import requests

response = requests.post(
    'http://localhost:8000/auth/register',
    json={
        'username': 'john_doe',
        'password': 'SecurePassword123!'
    }
)

if response.status_code == 201:
    user = response.json()
    print(f"Пользователь создан: {user['username']}")
else:
    print(f"Ошибка: {response.json()}")
```

#### JavaScript

```javascript
async function register(username, password) {
  const response = await fetch('http://localhost:8000/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username, password }),
  });

  if (response.ok) {
    const user = await response.json();
    console.log('Пользователь создан:', user.username);
  } else {
    const error = await response.json();
    console.error('Ошибка:', error);
  }
}

register('john_doe', 'SecurePassword123!');
```

### Вход (получение токена)

#### curl

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "SecurePassword123!"
  }'
```

**Ответ:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### curl с сохранением токена

```bash
# Сохранение токена в переменную
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "SecurePassword123!"
  }' | jq -r '.access_token')

# Проверка
echo $TOKEN

# Использование токена
curl -X GET http://localhost:8000/ar/list \
  -H "Authorization: Bearer $TOKEN"
```

#### Python с сохранением токена

```python
import requests

class VertexARClient:
    def __init__(self, base_url='http://localhost:8000'):
        self.base_url = base_url
        self.token = None
    
    def login(self, username, password):
        """Вход и сохранение токена"""
        response = requests.post(
            f'{self.base_url}/auth/login',
            json={'username': username, 'password': password}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data['access_token']
            return True
        return False
    
    def get_headers(self):
        """Получение заголовков с токеном"""
        return {
            'Authorization': f'Bearer {self.token}'
        }
    
    def logout(self):
        """Выход"""
        if not self.token:
            return False
        
        response = requests.post(
            f'{self.base_url}/auth/logout',
            headers=self.get_headers()
        )
        
        if response.status_code == 204:
            self.token = None
            return True
        return False

# Использование
client = VertexARClient()
if client.login('john_doe', 'SecurePassword123!'):
    print('Успешный вход!')
    # Теперь можно использовать client.get_headers() для запросов
else:
    print('Ошибка входа')
```

#### JavaScript класс для API

```javascript
class VertexARClient {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
    this.token = null;
  }

  async login(username, password) {
    const response = await fetch(`${this.baseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    if (response.ok) {
      const data = await response.json();
      this.token = data.access_token;
      // Сохранение в localStorage
      localStorage.setItem('vertex_ar_token', this.token);
      return true;
    }
    return false;
  }

  async logout() {
    if (!this.token) return false;

    const response = await fetch(`${this.baseUrl}/auth/logout`, {
      method: 'POST',
      headers: this.getHeaders(),
    });

    if (response.ok) {
      this.token = null;
      localStorage.removeItem('vertex_ar_token');
      return true;
    }
    return false;
  }

  getHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  // Восстановление токена из localStorage
  restoreToken() {
    const token = localStorage.getItem('vertex_ar_token');
    if (token) {
      this.token = token;
      return true;
    }
    return false;
  }
}

// Использование
const client = new VertexARClient();
await client.login('john_doe', 'SecurePassword123!');
```

---

## 📸 Работа с AR-контентом

### Загрузка AR-контента

#### curl

```bash
# Убедитесь, что у вас есть токен
TOKEN="your_access_token_here"

# Загрузка изображения и видео
curl -X POST http://localhost:8000/ar/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "image=@portrait.jpg" \
  -F "video=@animation.mp4"
```

**Ответ:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "ar_url": "http://localhost:8000/ar/550e8400-e29b-41d4-a716-446655440000",
  "qr_code_base64": "iVBORw0KGgoAAAANSUhEUg...",
  "image_path": "/storage/ar_content/john_doe/550e.../image.jpg",
  "video_path": "/storage/ar_content/john_doe/550e.../video.mp4",
  "created_at": "2024-01-15T10:30:00"
}
```

#### Python

```python
def upload_ar_content(client, image_path, video_path):
    """Загрузка AR контента"""
    url = f'{client.base_url}/ar/upload'
    
    with open(image_path, 'rb') as img_file, \
         open(video_path, 'rb') as vid_file:
        
        files = {
            'image': ('portrait.jpg', img_file, 'image/jpeg'),
            'video': ('animation.mp4', vid_file, 'video/mp4')
        }
        
        response = requests.post(
            url,
            headers={'Authorization': f'Bearer {client.token}'},
            files=files
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f'Upload failed: {response.json()}')

# Использование
try:
    result = upload_ar_content(
        client,
        'path/to/portrait.jpg',
        'path/to/animation.mp4'
    )
    print(f"Создан AR контент: {result['ar_url']}")
    print(f"ID: {result['id']}")
except Exception as e:
    print(f"Ошибка: {e}")
```

#### JavaScript с отслеживанием прогресса

```javascript
async function uploadARContent(client, imageFile, videoFile, onProgress) {
  const formData = new FormData();
  formData.append('image', imageFile);
  formData.append('video', videoFile);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    // Отслеживание прогресса загрузки
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const percentComplete = (e.loaded / e.total) * 100;
        onProgress(percentComplete);
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status === 200) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        reject(JSON.parse(xhr.responseText));
      }
    });

    xhr.addEventListener('error', () => {
      reject(new Error('Network error'));
    });

    xhr.open('POST', `${client.baseUrl}/ar/upload`);
    xhr.setRequestHeader('Authorization', `Bearer ${client.token}`);
    xhr.send(formData);
  });
}

// Использование
const imageFile = document.querySelector('#image-input').files[0];
const videoFile = document.querySelector('#video-input').files[0];

try {
  const result = await uploadARContent(
    client,
    imageFile,
    videoFile,
    (progress) => {
      console.log(`Прогресс: ${progress.toFixed(2)}%`);
      // Обновление UI
      document.querySelector('#progress').value = progress;
    }
  );
  
  console.log('AR контент создан:', result.ar_url);
  console.log('QR код:', result.qr_code_base64);
} catch (error) {
  console.error('Ошибка загрузки:', error);
}
```

### Получение списка AR-контента

#### curl

```bash
curl -X GET http://localhost:8000/ar/list \
  -H "Authorization: Bearer $TOKEN"
```

**Ответ:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "john_doe",
    "image_path": "/storage/ar_content/john_doe/550e.../image.jpg",
    "video_path": "/storage/ar_content/john_doe/550e.../video.mp4",
    "ar_url": "http://localhost:8000/ar/550e8400-e29b-41d4-a716-446655440000",
    "qr_code": "iVBORw0KGgo...",
    "created_at": "2024-01-15T10:30:00"
  },
  {
    "id": "660f9411-f39c-52e5-b827-557766551111",
    "username": "john_doe",
    "image_path": "/storage/ar_content/john_doe/660f.../image.jpg",
    "video_path": "/storage/ar_content/john_doe/660f.../video.mp4",
    "ar_url": "http://localhost:8000/ar/660f9411-f39c-52e5-b827-557766551111",
    "qr_code": "iVBORw0KGgo...",
    "created_at": "2024-01-16T14:20:00"
  }
]
```

#### Python с пагинацией

```python
def list_ar_content(client, limit=10, offset=0):
    """Получение списка AR контента"""
    url = f'{client.base_url}/ar/list'
    params = {'limit': limit, 'offset': offset}
    
    response = requests.get(
        url,
        headers=client.get_headers(),
        params=params
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f'Failed to get list: {response.json()}')

def get_all_ar_content(client):
    """Получение всего контента с автоматической пагинацией"""
    all_content = []
    limit = 50
    offset = 0
    
    while True:
        batch = list_ar_content(client, limit=limit, offset=offset)
        
        if not batch:
            break
        
        all_content.extend(batch)
        offset += limit
        
        if len(batch) < limit:
            break
    
    return all_content

# Использование
content_list = list_ar_content(client, limit=10, offset=0)
for item in content_list:
    print(f"ID: {item['id']}")
    print(f"URL: {item['ar_url']}")
    print(f"Создан: {item['created_at']}")
    print('---')
```

#### JavaScript с фильтрацией

```javascript
class ARContentManager {
  constructor(client) {
    this.client = client;
    this.cache = new Map();
  }

  async listContent(filters = {}) {
    const params = new URLSearchParams();
    
    if (filters.limit) params.append('limit', filters.limit);
    if (filters.offset) params.append('offset', filters.offset);
    if (filters.username) params.append('username', filters.username);

    const response = await fetch(
      `${this.client.baseUrl}/ar/list?${params}`,
      {
        headers: this.client.getHeaders(),
      }
    );

    if (response.ok) {
      const data = await response.json();
      // Кэширование результатов
      data.forEach(item => this.cache.set(item.id, item));
      return data;
    }

    throw new Error('Failed to fetch content list');
  }

  async getContentById(id) {
    // Проверка кэша
    if (this.cache.has(id)) {
      return this.cache.get(id);
    }

    // Если нет в кэше, загрузить весь список
    await this.listContent();
    return this.cache.get(id);
  }

  async searchContent(query) {
    const allContent = await this.listContent();
    
    return allContent.filter(item =>
      item.username.toLowerCase().includes(query.toLowerCase()) ||
      item.id.includes(query)
    );
  }

  sortByDate(ascending = false) {
    const content = Array.from(this.cache.values());
    
    return content.sort((a, b) => {
      const dateA = new Date(a.created_at);
      const dateB = new Date(b.created_at);
      return ascending ? dateA - dateB : dateB - dateA;
    });
  }
}

// Использование
const manager = new ARContentManager(client);

// Получение списка
const content = await manager.listContent({ limit: 20 });

// Поиск
const results = await manager.searchContent('john');

// Сортировка
const sorted = manager.sortByDate(false); // новые первыми
```

### Удаление AR-контента

#### curl

```bash
# Удаление по ID
curl -X DELETE http://localhost:8000/ar/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer $TOKEN"
```

**Ответ:** `204 No Content` (успешное удаление)

#### Python

```python
def delete_ar_content(client, content_id):
    """Удаление AR контента"""
    url = f'{client.base_url}/ar/{content_id}'
    
    response = requests.delete(
        url,
        headers=client.get_headers()
    )
    
    return response.status_code == 204

def batch_delete(client, content_ids):
    """Массовое удаление контента"""
    results = {}
    
    for content_id in content_ids:
        try:
            success = delete_ar_content(client, content_id)
            results[content_id] = 'deleted' if success else 'failed'
        except Exception as e:
            results[content_id] = f'error: {str(e)}'
    
    return results

# Использование
# Единичное удаление
if delete_ar_content(client, '550e8400-e29b-41d4-a716-446655440000'):
    print('Контент удален')

# Массовое удаление
ids_to_delete = [
    '550e8400-e29b-41d4-a716-446655440000',
    '660f9411-f39c-52e5-b827-557766551111'
]
results = batch_delete(client, ids_to_delete)
print(results)
```

### Скачивание QR-кода

#### curl

```bash
# Скачивание QR-кода
curl -X GET http://localhost:8000/ar/550e8400-e29b-41d4-a716-446655440000/qr \
  -o qrcode.png
```

#### Python

```python
def download_qr_code(client, content_id, output_path):
    """Скачивание QR-кода"""
    url = f'{client.base_url}/ar/{content_id}/qr'
    
    response = requests.get(url)
    
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        return True
    return False

def decode_qr_base64(qr_code_base64, output_path):
    """Декодирование QR из base64 строки"""
    import base64
    
    qr_data = base64.b64decode(qr_code_base64)
    
    with open(output_path, 'wb') as f:
        f.write(qr_data)

# Использование
# Способ 1: Прямое скачивание
download_qr_code(client, content_id, 'qrcode.png')

# Способ 2: Из base64 (из ответа при загрузке)
decode_qr_base64(result['qr_code_base64'], 'qrcode.png')
```

#### JavaScript

```javascript
async function downloadQRCode(client, contentId) {
  const response = await fetch(
    `${client.baseUrl}/ar/${contentId}/qr`,
    { headers: client.getHeaders() }
  );

  if (response.ok) {
    const blob = await response.blob();
    
    // Создание ссылки для скачивания
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `qrcode_${contentId}.png`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }
}

// Отображение QR в img элементе
async function displayQRCode(client, contentId, imgElement) {
  const response = await fetch(
    `${client.baseUrl}/ar/${contentId}/qr`,
    { headers: client.getHeaders() }
  );

  if (response.ok) {
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    imgElement.src = url;
  }
}

// Использование
// Скачивание
await downloadQRCode(client, '550e8400-e29b-41d4-a716-446655440000');

// Отображение
const img = document.querySelector('#qr-image');
await displayQRCode(client, '550e8400-e29b-41d4-a716-446655440000', img);
```

---

## 👨‍💼 Административные функции

### Получение статистики

#### curl

```bash
curl -X GET http://localhost:8000/admin/stats \
  -H "Authorization: Bearer $TOKEN"
```

**Ответ:**
```json
{
  "total_users": 5,
  "total_ar_content": 23,
  "total_views": 1542,
  "storage_usage": {
    "total_gb": 100.0,
    "used_gb": 15.3,
    "free_gb": 84.7,
    "percent_used": 15.3
  },
  "recent_uploads": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "john_doe",
      "created_at": "2024-01-15T10:30:00"
    }
  ]
}
```

#### Python с визуализацией

```python
def get_stats(client):
    """Получение статистики"""
    url = f'{client.base_url}/admin/stats'
    
    response = requests.get(
        url,
        headers=client.get_headers()
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception('Failed to get stats')

def print_stats_report(stats):
    """Красивый вывод статистики"""
    print("=" * 50)
    print("VERTEX AR - СТАТИСТИКА СИСТЕМЫ")
    print("=" * 50)
    print()
    
    print(f"👥 Пользователей:        {stats['total_users']}")
    print(f"📷 AR-контента:          {stats['total_ar_content']}")
    print(f"👁️  Просмотров:          {stats['total_views']}")
    print()
    
    storage = stats['storage_usage']
    print("💾 Использование диска:")
    print(f"   Всего:               {storage['total_gb']:.2f} GB")
    print(f"   Использовано:        {storage['used_gb']:.2f} GB")
    print(f"   Свободно:            {storage['free_gb']:.2f} GB")
    print(f"   Процент:             {storage['percent_used']:.1f}%")
    
    # Визуализация использования
    bar_length = 40
    used_bars = int(storage['percent_used'] / 100 * bar_length)
    free_bars = bar_length - used_bars
    print(f"   [{'█' * used_bars}{'░' * free_bars}]")
    print()
    
    if stats.get('recent_uploads'):
        print("📤 Последние загрузки:")
        for upload in stats['recent_uploads'][:5]:
            print(f"   - {upload['username']}: {upload['created_at']}")
    
    print("=" * 50)

# Использование
stats = get_stats(client)
print_stats_report(stats)
```

#### JavaScript дашборд

```javascript
class AdminDashboard {
  constructor(client, containerId) {
    this.client = client;
    this.container = document.getElementById(containerId);
  }

  async loadStats() {
    const response = await fetch(
      `${this.client.baseUrl}/admin/stats`,
      { headers: this.client.getHeaders() }
    );

    if (response.ok) {
      return await response.json();
    }
    throw new Error('Failed to load stats');
  }

  renderStats(stats) {
    const html = `
      <div class="dashboard">
        <div class="stat-card">
          <h3>👥 Пользователи</h3>
          <div class="stat-value">${stats.total_users}</div>
        </div>
        
        <div class="stat-card">
          <h3>📷 AR-контент</h3>
          <div class="stat-value">${stats.total_ar_content}</div>
        </div>
        
        <div class="stat-card">
          <h3>👁️ Просмотры</h3>
          <div class="stat-value">${stats.total_views.toLocaleString()}</div>
        </div>
        
        <div class="stat-card full-width">
          <h3>💾 Использование диска</h3>
          <div class="storage-info">
            <div class="storage-bar">
              <div class="storage-used" 
                   style="width: ${stats.storage_usage.percent_used}%">
              </div>
            </div>
            <div class="storage-text">
              ${stats.storage_usage.used_gb.toFixed(2)} GB / 
              ${stats.storage_usage.total_gb.toFixed(2)} GB
              (${stats.storage_usage.percent_used.toFixed(1)}%)
            </div>
          </div>
        </div>
        
        <div class="stat-card full-width">
          <h3>📤 Последние загрузки</h3>
          <ul class="recent-uploads">
            ${stats.recent_uploads.map(upload => `
              <li>
                <span class="username">${upload.username}</span>
                <span class="date">${new Date(upload.created_at).toLocaleString()}</span>
              </li>
            `).join('')}
          </ul>
        </div>
      </div>
    `;

    this.container.innerHTML = html;
  }

  async refresh() {
    try {
      const stats = await this.loadStats();
      this.renderStats(stats);
    } catch (error) {
      console.error('Failed to refresh dashboard:', error);
    }
  }

  startAutoRefresh(intervalMs = 30000) {
    this.refresh();
    this.refreshInterval = setInterval(() => this.refresh(), intervalMs);
  }

  stopAutoRefresh() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  }
}

// CSS стили
const dashboardStyles = `
<style>
.dashboard {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  padding: 20px;
}

.stat-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.stat-card.full-width {
  grid-column: 1 / -1;
}

.stat-card h3 {
  margin: 0 0 10px 0;
  font-size: 16px;
  color: #666;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #333;
}

.storage-bar {
  height: 20px;
  background: #e0e0e0;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 10px;
}

.storage-used {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #8BC34A);
  transition: width 0.3s ease;
}

.storage-text {
  font-size: 14px;
  color: #666;
}

.recent-uploads {
  list-style: none;
  padding: 0;
  margin: 0;
}

.recent-uploads li {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #eee;
}

.recent-uploads li:last-child {
  border-bottom: none;
}

.username {
  font-weight: bold;
  color: #333;
}

.date {
  color: #999;
  font-size: 14px;
}
</style>
`;

// Использование
const dashboard = new AdminDashboard(client, 'dashboard-container');
dashboard.startAutoRefresh(30000); // обновление каждые 30 сек
```

---

## 🔌 Интеграция в приложения

### React интеграция

```javascript
// hooks/useVertexAR.js
import { useState, useEffect, useCallback } from 'react';

export function useVertexAR(baseUrl = 'http://localhost:8000') {
  const [client, setClient] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('vertex_ar_token');
    if (token) {
      const newClient = new VertexARClient(baseUrl);
      newClient.token = token;
      setClient(newClient);
      setIsAuthenticated(true);
    }
  }, [baseUrl]);

  const login = useCallback(async (username, password) => {
    setLoading(true);
    setError(null);
    
    try {
      const newClient = new VertexARClient(baseUrl);
      const success = await newClient.login(username, password);
      
      if (success) {
        setClient(newClient);
        setIsAuthenticated(true);
      }
      
      return success;
    } catch (err) {
      setError(err.message);
      return false;
    } finally {
      setLoading(false);
    }
  }, [baseUrl]);

  const logout = useCallback(async () => {
    if (client) {
      await client.logout();
      setClient(null);
      setIsAuthenticated(false);
    }
  }, [client]);

  const uploadContent = useCallback(async (imageFile, videoFile, onProgress) => {
    if (!client) throw new Error('Not authenticated');
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await uploadARContent(client, imageFile, videoFile, onProgress);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [client]);

  return {
    client,
    isAuthenticated,
    loading,
    error,
    login,
    logout,
    uploadContent,
  };
}

// components/ARUploader.jsx
import React, { useState } from 'react';
import { useVertexAR } from '../hooks/useVertexAR';

function ARUploader() {
  const { uploadContent, loading } = useVertexAR();
  const [imageFile, setImageFile] = useState(null);
  const [videoFile, setVideoFile] = useState(null);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!imageFile || !videoFile) {
      alert('Выберите изображение и видео');
      return;
    }

    try {
      const data = await uploadContent(
        imageFile,
        videoFile,
        setProgress
      );
      setResult(data);
    } catch (error) {
      alert('Ошибка загрузки: ' + error.message);
    }
  };

  return (
    <div className="ar-uploader">
      <form onSubmit={handleSubmit}>
        <div>
          <label>Изображение:</label>
          <input
            type="file"
            accept="image/jpeg,image/png"
            onChange={(e) => setImageFile(e.target.files[0])}
          />
        </div>

        <div>
          <label>Видео:</label>
          <input
            type="file"
            accept="video/mp4,video/webm"
            onChange={(e) => setVideoFile(e.target.files[0])}
          />
        </div>

        <button type="submit" disabled={loading}>
          {loading ? 'Загрузка...' : 'Загрузить'}
        </button>
      </form>

      {loading && (
        <div className="progress-bar">
          <div 
            className="progress-fill" 
            style={{ width: `${progress}%` }}
          />
          <span>{progress.toFixed(0)}%</span>
        </div>
      )}

      {result && (
        <div className="result">
          <h3>AR контент создан!</h3>
          <p>URL: <a href={result.ar_url}>{result.ar_url}</a></p>
          <img src={`data:image/png;base64,${result.qr_code_base64}`} alt="QR код" />
        </div>
      )}
    </div>
  );
}

export default ARUploader;
```

### Vue.js интеграция

```javascript
// composables/useVertexAR.js
import { ref, computed } from 'vue';

export function useVertexAR(baseUrl = 'http://localhost:8000') {
  const client = ref(null);
  const token = ref(localStorage.getItem('vertex_ar_token'));
  const loading = ref(false);
  const error = ref(null);

  const isAuthenticated = computed(() => !!token.value);

  async function login(username, password) {
    loading.value = true;
    error.value = null;

    try {
      const newClient = new VertexARClient(baseUrl);
      const success = await newClient.login(username, password);

      if (success) {
        client.value = newClient;
        token.value = newClient.token;
      }

      return success;
    } catch (err) {
      error.value = err.message;
      return false;
    } finally {
      loading.value = false;
    }
  }

  async function logout() {
    if (client.value) {
      await client.value.logout();
      client.value = null;
      token.value = null;
    }
  }

  async function listContent() {
    if (!client.value) throw new Error('Not authenticated');
    
    loading.value = true;
    error.value = null;

    try {
      const response = await fetch(`${baseUrl}/ar/list`, {
        headers: client.value.getHeaders(),
      });

      if (response.ok) {
        return await response.json();
      }

      throw new Error('Failed to fetch content');
    } catch (err) {
      error.value = err.message;
      throw err;
    } finally {
      loading.value = false;
    }
  }

  return {
    client,
    token,
    isAuthenticated,
    loading,
    error,
    login,
    logout,
    listContent,
  };
}

// components/ARContentList.vue
<template>
  <div class="ar-content-list">
    <h2>AR Контент</h2>

    <div v-if="loading">Загрузка...</div>
    <div v-else-if="error">Ошибка: {{ error }}</div>

    <div v-else class="content-grid">
      <div 
        v-for="item in content" 
        :key="item.id" 
        class="content-card"
      >
        <img :src="item.image_path" :alt="item.id" />
        <h3>{{ item.id }}</h3>
        <p>Создан: {{ formatDate(item.created_at) }}</p>
        <a :href="item.ar_url" target="_blank">Открыть AR</a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useVertexAR } from '../composables/useVertexAR';

const { listContent, loading, error } = useVertexAR();
const content = ref([]);

onMounted(async () => {
  try {
    content.value = await listContent();
  } catch (err) {
    console.error('Failed to load content:', err);
  }
});

function formatDate(dateString) {
  return new Date(dateString).toLocaleString('ru-RU');
}
</script>
```

---

## 🌍 Примеры на разных языках

### Python (полный пример)

```python
#!/usr/bin/env python3
"""
Полный пример работы с Vertex AR API
"""

import requests
from pathlib import Path
import base64
import json

class VertexARAPI:
    def __init__(self, base_url='http://localhost:8000'):
        self.base_url = base_url
        self.token = None
        self.session = requests.Session()
    
    def login(self, username, password):
        """Авторизация"""
        response = self.session.post(
            f'{self.base_url}/auth/login',
            json={'username': username, 'password': password}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data['access_token']
            self.session.headers.update({
                'Authorization': f'Bearer {self.token}'
            })
            return True
        return False
    
    def upload_ar_content(self, image_path, video_path):
        """Загрузка AR контента"""
        with open(image_path, 'rb') as img, open(video_path, 'rb') as vid:
            files = {
                'image': ('image.jpg', img, 'image/jpeg'),
                'video': ('video.mp4', vid, 'video/mp4')
            }
            
            response = self.session.post(
                f'{self.base_url}/ar/upload',
                files=files
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f'Upload failed: {response.text}')
    
    def list_content(self):
        """Список контента"""
        response = self.session.get(f'{self.base_url}/ar/list')
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f'Failed to get list: {response.text}')
    
    def get_stats(self):
        """Статистика"""
        response = self.session.get(f'{self.base_url}/admin/stats')
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f'Failed to get stats: {response.text}')
    
    def download_qr(self, content_id, output_path):
        """Скачивание QR-кода"""
        response = self.session.get(f'{self.base_url}/ar/{content_id}/qr')
        
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True
        return False
    
    def delete_content(self, content_id):
        """Удаление контента"""
        response = self.session.delete(f'{self.base_url}/ar/{content_id}')
        return response.status_code == 204

def main():
    # Создание клиента
    api = VertexARAPI('http://localhost:8000')
    
    # Логин
    if not api.login('admin', 'password'):
        print('Ошибка входа')
        return
    
    print('✅ Успешный вход')
    
    # Загрузка контента
    try:
        result = api.upload_ar_content(
            'portrait.jpg',
            'animation.mp4'
        )
        print(f'✅ Контент загружен: {result["ar_url"]}')
        content_id = result['id']
    except Exception as e:
        print(f'❌ Ошибка загрузки: {e}')
        return
    
    # Скачивание QR-кода
    if api.download_qr(content_id, f'qr_{content_id}.png'):
        print(f'✅ QR-код сохранен')
    
    # Получение списка
    content_list = api.list_content()
    print(f'✅ Всего контента: {len(content_list)}')
    
    # Статистика
    stats = api.get_stats()
    print(f'✅ Пользователей: {stats["total_users"]}')
    print(f'✅ AR-контента: {stats["total_ar_content"]}')
    print(f'✅ Просмотров: {stats["total_views"]}')

if __name__ == '__main__':
    main()
```

### Go

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "io"
    "mime/multipart"
    "net/http"
    "os"
)

type VertexARClient struct {
    BaseURL string
    Token   string
    Client  *http.Client
}

type LoginRequest struct {
    Username string `json:"username"`
    Password string `json:"password"`
}

type LoginResponse struct {
    AccessToken string `json:"access_token"`
    TokenType   string `json:"token_type"`
}

type ARContent struct {
    ID          string `json:"id"`
    ARURL       string `json:"ar_url"`
    QRCodeBase64 string `json:"qr_code_base64"`
    ImagePath   string `json:"image_path"`
    VideoPath   string `json:"video_path"`
    CreatedAt   string `json:"created_at"`
}

func NewVertexARClient(baseURL string) *VertexARClient {
    return &VertexARClient{
        BaseURL: baseURL,
        Client:  &http.Client{},
    }
}

func (c *VertexARClient) Login(username, password string) error {
    loginReq := LoginRequest{
        Username: username,
        Password: password,
    }

    jsonData, err := json.Marshal(loginReq)
    if err != nil {
        return err
    }

    req, err := http.NewRequest("POST", c.BaseURL+"/auth/login", bytes.NewBuffer(jsonData))
    if err != nil {
        return err
    }
    req.Header.Set("Content-Type", "application/json")

    resp, err := c.Client.Do(req)
    if err != nil {
        return err
    }
    defer resp.Body.Close()

    if resp.StatusCode != 200 {
        return fmt.Errorf("login failed: %s", resp.Status)
    }

    var loginResp LoginResponse
    if err := json.NewDecoder(resp.Body).Decode(&loginResp); err != nil {
        return err
    }

    c.Token = loginResp.AccessToken
    return nil
}

func (c *VertexARClient) UploadARContent(imagePath, videoPath string) (*ARContent, error) {
    body := &bytes.Buffer{}
    writer := multipart.NewWriter(body)

    // Добавление изображения
    imageFile, err := os.Open(imagePath)
    if err != nil {
        return nil, err
    }
    defer imageFile.Close()

    imagePart, err := writer.CreateFormFile("image", imagePath)
    if err != nil {
        return nil, err
    }
    if _, err := io.Copy(imagePart, imageFile); err != nil {
        return nil, err
    }

    // Добавление видео
    videoFile, err := os.Open(videoPath)
    if err != nil {
        return nil, err
    }
    defer videoFile.Close()

    videoPart, err := writer.CreateFormFile("video", videoPath)
    if err != nil {
        return nil, err
    }
    if _, err := io.Copy(videoPart, videoFile); err != nil {
        return nil, err
    }

    writer.Close()

    req, err := http.NewRequest("POST", c.BaseURL+"/ar/upload", body)
    if err != nil {
        return nil, err
    }
    req.Header.Set("Content-Type", writer.FormDataContentType())
    req.Header.Set("Authorization", "Bearer "+c.Token)

    resp, err := c.Client.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    if resp.StatusCode != 200 {
        return nil, fmt.Errorf("upload failed: %s", resp.Status)
    }

    var result ARContent
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return nil, err
    }

    return &result, nil
}

func (c *VertexARClient) ListContent() ([]ARContent, error) {
    req, err := http.NewRequest("GET", c.BaseURL+"/ar/list", nil)
    if err != nil {
        return nil, err
    }
    req.Header.Set("Authorization", "Bearer "+c.Token)

    resp, err := c.Client.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    if resp.StatusCode != 200 {
        return nil, fmt.Errorf("list failed: %s", resp.Status)
    }

    var content []ARContent
    if err := json.NewDecoder(resp.Body).Decode(&content); err != nil {
        return nil, err
    }

    return content, nil
}

func main() {
    client := NewVertexARClient("http://localhost:8000")

    // Логин
    if err := client.Login("admin", "password"); err != nil {
        fmt.Printf("Login failed: %v\n", err)
        return
    }
    fmt.Println("✅ Logged in")

    // Загрузка контента
    result, err := client.UploadARContent("portrait.jpg", "animation.mp4")
    if err != nil {
        fmt.Printf("Upload failed: %v\n", err)
        return
    }
    fmt.Printf("✅ Content uploaded: %s\n", result.ARURL)

    // Список контента
    contentList, err := client.ListContent()
    if err != nil {
        fmt.Printf("List failed: %v\n", err)
        return
    }
    fmt.Printf("✅ Total content: %d\n", len(contentList))
}
```

---

## ⚠️ Обработка ошибок

### Типы ошибок

```python
class VertexARError(Exception):
    """Базовый класс для всех ошибок"""
    pass

class AuthenticationError(VertexARError):
    """Ошибка аутентификации"""
    pass

class UploadError(VertexARError):
    """Ошибка загрузки"""
    pass

class NotFoundError(VertexARError):
    """Ресурс не найден"""
    pass

class PermissionError(VertexARError):
    """Недостаточно прав"""
    pass

def handle_response(response):
    """Обработка HTTP ответа"""
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 201:
        return response.json()
    elif response.status_code == 204:
        return None
    elif response.status_code == 400:
        raise VertexARError(f'Bad request: {response.json()}')
    elif response.status_code == 401:
        raise AuthenticationError('Unauthorized')
    elif response.status_code == 403:
        raise PermissionError('Forbidden')
    elif response.status_code == 404:
        raise NotFoundError('Not found')
    elif response.status_code == 409:
        raise VertexARError(f'Conflict: {response.json()}')
    elif response.status_code == 413:
        raise UploadError('File too large')
    elif response.status_code >= 500:
        raise VertexARError(f'Server error: {response.status_code}')
    else:
        raise VertexARError(f'Unknown error: {response.status_code}')

# Использование
try:
    response = requests.post(url, json=data)
    result = handle_response(response)
except AuthenticationError:
    print('Требуется повторный вход')
except UploadError as e:
    print(f'Ошибка загрузки: {e}')
except VertexARError as e:
    print(f'Ошибка API: {e}')
```

---

## ✅ Best Practices

### 1. Переиспользование соединений

```python
# ✅ Хорошо - переиспользование session
session = requests.Session()
session.headers.update({'Authorization': f'Bearer {token}'})

for i in range(100):
    response = session.get(f'{base_url}/ar/list')

# ❌ Плохо - создание нового соединения каждый раз
for i in range(100):
    response = requests.get(
        f'{base_url}/ar/list',
        headers={'Authorization': f'Bearer {token}'}
    )
```

### 2. Ретраи при ошибках

```python
from time import sleep

def request_with_retry(func, max_retries=3, delay=1):
    """Выполнение запроса с ретраями"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            print(f'Attempt {attempt + 1} failed: {e}')
            sleep(delay * (attempt + 1))  # Exponential backoff

# Использование
result = request_with_retry(
    lambda: client.upload_content(image, video)
)
```

### 3. Кэширование результатов

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedVertexARClient:
    def __init__(self, client):
        self.client = client
        self.cache = {}
        self.cache_ttl = timedelta(minutes=5)
    
    def get_content_list(self, force_refresh=False):
        """Получение списка с кэшированием"""
        cache_key = 'content_list'
        
        if not force_refresh and cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_ttl:
                return cached_data
        
        # Загрузка свежих данных
        data = self.client.list_content()
        self.cache[cache_key] = (data, datetime.now())
        return data
```

### 4. Асинхронные запросы

```python
import asyncio
import aiohttp

class AsyncVertexARClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
    
    async def login(self, username, password):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{self.base_url}/auth/login',
                json={'username': username, 'password': password}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.token = data['access_token']
                    return True
                return False
    
    async def get_content(self, content_id):
        headers = {'Authorization': f'Bearer {self.token}'}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'{self.base_url}/ar/{content_id}',
                headers=headers
            ) as response:
                return await response.json()
    
    async def get_multiple_content(self, content_ids):
        """Параллельная загрузка нескольких контентов"""
        tasks = [self.get_content(cid) for cid in content_ids]
        return await asyncio.gather(*tasks)

# Использование
async def main():
    client = AsyncVertexARClient('http://localhost:8000')
    await client.login('admin', 'password')
    
    # Параллельная загрузка
    content_ids = ['id1', 'id2', 'id3']
    results = await client.get_multiple_content(content_ids)
    print(results)

asyncio.run(main())
```

---

**Версия документа**: 1.0.0  
**Последнее обновление**: 2024  
**Проект**: Vertex AR

📧 Поддержка: support@vertex-ar.com  
📚 Документация: https://docs.vertex-ar.com
