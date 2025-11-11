# Order Creation API Examples
# Примеры использования API создания заказов

---

## Table of Contents / Содержание
1. [Authentication](#authentication)
2. [Create Order](#create-order)
3. [Admin Panel Upload](#admin-panel-upload)
4. [Error Handling](#error-handling)
5. [cURL Examples](#curl-examples)
6. [Python Examples](#python-examples)
7. [JavaScript Examples](#javascript-examples)

---

## Authentication / Аутентификация

### Login to Get Token / Авторизация для получения токена

**Endpoint:** `POST /api/auth/login`

#### Request (JSON):
```json
{
  "username": "admin",
  "password": "Qwerty123!@#"
}
```

#### Response (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Response (401 Unauthorized):
```json
{
  "detail": "Invalid credentials"
}
```

---

## Create Order / Создание заказа

### Endpoint: `POST /api/orders/create`

**Authentication:** Bearer token (required)  
**Content-Type:** `multipart/form-data`

### Request Parameters:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `phone` | string | ✅ | Customer phone number |
| `name` | string | ✅ | Customer name |
| `image` | file | ✅ | Portrait image (JPEG/PNG) |
| `video` | file | ✅ | Animation video (MP4) |

### Success Response (201 Created):

```json
{
  "client": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "phone": "+7 (999) 123-45-67",
    "name": "Иван Петров",
    "created_at": "2024-11-11T13:00:00.000000Z"
  },
  "portrait": {
    "id": "223e4567-e89b-12d3-a456-426614174001",
    "client_id": "123e4567-e89b-12d3-a456-426614174000",
    "permanent_link": "portrait_223e4567-e89b-12d3-a456-426614174001",
    "qr_code_base64": "iVBORw0KGgoAAAANSUhEUgAAAM0AAADNCAMAAADt99aSAAAAy0lEQVR4nO3BMQEAAADCoPVPbQhfoAAAAOA1v9QAATX3/LkAAAAASUVORK5CYII=",
    "image_path": "/storage/portraits/123e4567-e89b-12d3-a456-426614174000/223e4567/223e4567.jpg",
    "view_count": 0,
    "created_at": "2024-11-11T13:00:00.000000Z"
  },
  "video": {
    "id": "323e4567-e89b-12d3-a456-426614174002",
    "portrait_id": "223e4567-e89b-12d3-a456-426614174001",
    "video_path": "/storage/portraits/123e4567-e89b-12d3-a456-426614174000/223e4567/323e4567.mp4",
    "is_active": true,
    "created_at": "2024-11-11T13:00:00.000000Z"
  }
}
```

### Error Responses:

#### 400 Bad Request - Invalid File Type
```json
{
  "detail": "Invalid image file"
}
```

#### 400 Bad Request - Missing Field
```json
{
  "detail": "Field required"
}
```

#### 401 Unauthorized - Missing Token
```json
{
  "detail": "Not authenticated"
}
```

#### 403 Forbidden - Insufficient Permissions
```json
{
  "detail": "Not enough permissions"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Failed to create order"
}
```

---

## Admin Panel Upload / Загрузка из админ-панели

### Web Interface / Веб-интерфейс

#### URL: `http://localhost:8000/admin/orders`

#### Form Fields:
- **Customer Name** (required)
- **Phone Number** (required)
- **Portrait Image** - JPEG/PNG file (required)
- **Animation Video** - MP4 file (required)

#### Workflow:
1. Navigate to `/admin` or `/admin/orders`
2. Login with admin credentials
3. Fill in customer name and phone
4. Upload portrait image
5. Upload animation video
6. Click "Create Order"
7. System generates NFT markers and QR code
8. Order confirmation displayed

### Behind the Scenes / Под капотом

When admin submits form:
1. **Authentication** - Session token validated
2. **Validation** - Phone and name format checked
3. **File Validation** - Image and video MIME types verified
4. **Storage** - Files saved to disk/MinIO
5. **NFT Generation** - Markers created (.fset, .fset3, .iset)
6. **QR Code** - Generated for AR viewer link
7. **Database** - Client, portrait, video records created
8. **Response** - Order details returned to admin

---

## Error Handling / Обработка ошибок

### Phone Validation Error
```json
{
  "detail": "Invalid phone format"
}
```

### Name Validation Error
```json
{
  "detail": "Invalid name format"
}
```

### File Size Error
```json
{
  "detail": "File too large"
}
```

### Storage Error
```json
{
  "detail": "Failed to create order"
}
```

### All errors are logged with context:
```json
{
  "timestamp": "2024-11-11T13:00:00.000000Z",
  "level": "error",
  "message": "Failed to create order",
  "admin": "admin_username",
  "client_phone": "+7 (999) 123-45-67",
  "exception": "FileNotFoundError: Storage directory not accessible"
}
```

---

## cURL Examples

### 1. Login to Get Token

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "Qwerty123!@#"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. Create Order with Token

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X POST "http://localhost:8000/api/orders/create" \
  -H "Authorization: Bearer $TOKEN" \
  -F "phone=+7 (999) 123-45-67" \
  -F "name=Иван Петров" \
  -F "image=@portrait.jpg" \
  -F "video=@animation.mp4"
```

### 3. Create Order (Inline)

```bash
curl -X POST "http://localhost:8000/api/orders/create" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -F "phone=+7 (999) 123-45-67" \
  -F "name=Иван Петров" \
  -F "image=@/path/to/portrait.jpg;type=image/jpeg" \
  -F "video=@/path/to/animation.mp4;type=video/mp4"
```

### 4. Create Multiple Orders from Script

```bash
#!/bin/bash

# Get token
TOKEN=$(curl -s -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Qwerty123!@#"}' | jq -r '.access_token')

# Create multiple orders
for i in {1..5}; do
  echo "Creating order $i..."
  
  curl -X POST "http://localhost:8000/api/orders/create" \
    -H "Authorization: Bearer $TOKEN" \
    -F "phone=+7 (999) 111-11-$i" \
    -F "name=Customer $i" \
    -F "image=@portrait.jpg" \
    -F "video=@animation.mp4"
  
  echo ""
  sleep 1
done
```

---

## Python Examples

### 1. Basic Order Creation

```python
import requests
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "Qwerty123!@#"

# Login
login_response = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={"username": USERNAME, "password": PASSWORD}
)
token = login_response.json()["access_token"]

# Prepare files
image_path = Path("portrait.jpg")
video_path = Path("animation.mp4")

# Create order
headers = {"Authorization": f"Bearer {token}"}

with open(image_path, "rb") as image_file, \
     open(video_path, "rb") as video_file:
    
    response = requests.post(
        f"{BASE_URL}/api/orders/create",
        headers=headers,
        data={
            "phone": "+7 (999) 123-45-67",
            "name": "Иван Петров"
        },
        files={
            "image": ("portrait.jpg", image_file, "image/jpeg"),
            "video": ("animation.mp4", video_file, "video/mp4")
        }
    )

# Handle response
if response.status_code == 201:
    order_data = response.json()
    print(f"Order created successfully!")
    print(f"Client ID: {order_data['client']['id']}")
    print(f"Portrait ID: {order_data['portrait']['id']}")
    print(f"Permanent Link: {order_data['portrait']['permanent_link']}")
else:
    print(f"Error: {response.status_code}")
    print(response.json())
```

### 2. Using TestClient (FastAPI)

```python
from fastapi.testclient import TestClient
from pathlib import Path
from io import BytesIO
from PIL import Image

# Create test client
from app.main import create_app

app = create_app()
client = TestClient(app)

# Create test image
def create_test_image():
    img = Image.new('RGB', (640, 480), color='red')
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer

# Login
login_response = client.post(
    "/api/auth/login",
    json={"username": "admin", "password": "Qwerty123!@#"}
)
token = login_response.json()["access_token"]

# Create order
response = client.post(
    "/api/orders/create",
    headers={"Authorization": f"Bearer {token}"},
    data={
        "phone": "+7 (999) 123-45-67",
        "name": "Test Customer"
    },
    files={
        "image": ("test.jpg", create_test_image(), "image/jpeg"),
        "video": ("test.mp4", b"video_data", "video/mp4")
    }
)

assert response.status_code == 201
order = response.json()
print(f"Order: {order}")
```

### 3. Batch Order Creation

```python
import requests
from pathlib import Path
import time

BASE_URL = "http://localhost:8000"

# Login
login_response = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={"username": "admin", "password": "Qwerty123!@#"}
)
token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Create multiple orders
orders = [
    {"phone": "+7 (999) 001-00-00", "name": "Customer 1"},
    {"phone": "+7 (999) 002-00-00", "name": "Customer 2"},
    {"phone": "+7 (999) 003-00-00", "name": "Customer 3"},
]

image_path = Path("portrait.jpg")
video_path = Path("animation.mp4")

for order_data in orders:
    print(f"Creating order for {order_data['name']}...")
    
    with open(image_path, "rb") as image_file, \
         open(video_path, "rb") as video_file:
        
        response = requests.post(
            f"{BASE_URL}/api/orders/create",
            headers=headers,
            data=order_data,
            files={
                "image": ("portrait.jpg", image_file, "image/jpeg"),
                "video": ("animation.mp4", video_file, "video/mp4")
            }
        )
    
    if response.status_code == 201:
        print(f"✓ Order created: {response.json()['portrait']['id']}")
    else:
        print(f"✗ Error: {response.status_code}")
    
    time.sleep(1)  # Rate limiting
```

---

## JavaScript/TypeScript Examples

### 1. Fetch API

```javascript
// Configuration
const BASE_URL = "http://localhost:8000";
const USERNAME = "admin";
const PASSWORD = "Qwerty123!@#";

async function createOrder() {
  try {
    // Step 1: Login
    const loginResponse = await fetch(`${BASE_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: USERNAME,
        password: PASSWORD
      })
    });

    const { access_token } = await loginResponse.json();

    // Step 2: Prepare form data
    const formData = new FormData();
    formData.append("phone", "+7 (999) 123-45-67");
    formData.append("name", "Иван Петров");
    
    // Add image file (from file input)
    const imageInput = document.getElementById("imageInput");
    formData.append("image", imageInput.files[0]);
    
    // Add video file
    const videoInput = document.getElementById("videoInput");
    formData.append("video", videoInput.files[0]);

    // Step 3: Create order
    const orderResponse = await fetch(`${BASE_URL}/api/orders/create`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${access_token}`
      },
      body: formData
    });

    const orderData = await orderResponse.json();

    if (orderResponse.ok) {
      console.log("✓ Order created successfully!");
      console.log("Client ID:", orderData.client.id);
      console.log("Portrait ID:", orderData.portrait.id);
      console.log("QR Code:", orderData.portrait.qr_code_base64);
      
      // Display QR code
      const qrImage = new Image();
      qrImage.src = `data:image/png;base64,${orderData.portrait.qr_code_base64}`;
      document.getElementById("qrContainer").appendChild(qrImage);
    } else {
      console.error("✗ Error:", orderData);
    }

  } catch (error) {
    console.error("Error:", error);
  }
}
```

### 2. React Component

```jsx
import React, { useState } from 'react';

function OrderCreationForm() {
  const [phone, setPhone] = useState('');
  const [name, setName] = useState('');
  const [imageFile, setImageFile] = useState(null);
  const [videoFile, setVideoFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      // Get token
      const loginRes = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: 'admin',
          password: 'Qwerty123!@#'
        })
      });

      const { access_token } = await loginRes.json();

      // Create order
      const formData = new FormData();
      formData.append('phone', phone);
      formData.append('name', name);
      formData.append('image', imageFile);
      formData.append('video', videoFile);

      const orderRes = await fetch('/api/orders/create', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${access_token}` },
        body: formData
      });

      if (orderRes.ok) {
        const order = await orderRes.json();
        setMessage(`✓ Order created! Portrait ID: ${order.portrait.id}`);
        // Reset form
        setPhone('');
        setName('');
        setImageFile(null);
        setVideoFile(null);
      } else {
        const error = await orderRes.json();
        setMessage(`✗ Error: ${error.detail}`);
      }
    } catch (error) {
      setMessage(`✗ Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="order-form">
      <h2>Create Order</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Customer Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <input
          type="tel"
          placeholder="Phone Number"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          required
        />
        <input
          type="file"
          accept="image/*"
          onChange={(e) => setImageFile(e.target.files[0])}
          required
        />
        <input
          type="file"
          accept="video/*"
          onChange={(e) => setVideoFile(e.target.files[0])}
          required
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Creating...' : 'Create Order'}
        </button>
      </form>
      {message && <p>{message}</p>}
    </div>
  );
}

export default OrderCreationForm;
```

### 3. Axios Helper

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 30000
});

class OrderAPI {
  static async login(username, password) {
    const response = await api.post('/auth/login', { username, password });
    return response.data.access_token;
  }

  static async createOrder(token, phone, name, imageFile, videoFile) {
    const formData = new FormData();
    formData.append('phone', phone);
    formData.append('name', name);
    formData.append('image', imageFile);
    formData.append('video', videoFile);

    return api.post('/orders/create', formData, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
  }
}

// Usage
(async () => {
  const token = await OrderAPI.login('admin', 'Qwerty123!@#');
  const response = await OrderAPI.createOrder(
    token,
    '+7 (999) 123-45-67',
    'Customer Name',
    imageFileObject,
    videoFileObject
  );
  console.log('Order created:', response.data);
})();
```

---

## Error Codes Reference / Справочник кодов ошибок

| Code | Message | Cause |
|------|---------|-------|
| 400 | Invalid image file | Image MIME type is not image/* |
| 400 | Invalid video file | Video MIME type is not video/* |
| 400 | Field required | Missing required form field |
| 401 | Not authenticated | Missing or invalid Bearer token |
| 403 | Not enough permissions | User is not admin |
| 422 | Validation error | Phone or name format invalid |
| 429 | Too many requests | Rate limit exceeded |
| 500 | Failed to create order | Server error (check logs) |

---

## Response Format / Формат ответа

### Success (201 Created):
```json
{
  "client": {
    "id": "string (UUID)",
    "phone": "string",
    "name": "string",
    "created_at": "string (ISO 8601)"
  },
  "portrait": {
    "id": "string (UUID)",
    "client_id": "string (UUID)",
    "permanent_link": "string",
    "qr_code_base64": "string (base64 PNG image)",
    "image_path": "string (file path)",
    "view_count": "integer",
    "created_at": "string (ISO 8601)"
  },
  "video": {
    "id": "string (UUID)",
    "portrait_id": "string (UUID)",
    "video_path": "string (file path)",
    "is_active": "boolean",
    "created_at": "string (ISO 8601)"
  }
}
```

### Error:
```json
{
  "detail": "string (error message)"
}
```

---

## Rate Limiting / Ограничение частоты

Default: **10 requests per minute** per admin user

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 9
X-RateLimit-Reset: 1699695956
```

---

## Logging / Логирование

All operations are logged with context:

```json
{
  "timestamp": "2024-11-11T13:00:00.000000Z",
  "level": "info",
  "message": "Order created successfully",
  "portrait_id": "uuid",
  "client_id": "uuid",
  "admin": "admin_username",
  "request_id": "uuid"
}
```

Check logs:
```bash
docker logs vertex-ar-app
# or
tail -f /var/log/vertex-ar/app.log
```

---

## Support / Поддержка

For issues or questions:
1. Check the logs with full context
2. Verify file formats (JPEG for image, MP4 for video)
3. Ensure admin authentication is working
4. Check database connectivity
5. Review error codes above

Contact: support@vertex-ar.com
