# Требования к данным для мобильного приложения React Native

**Версия API:** 1.3.0  
**Дата создания:** 2024  
**Целевая платформа:** React Native (iOS/Android)

## Обзор

Этот документ описывает все данные, которые необходимы для разработки мобильного AR-приложения на React Native для просмотра контента, созданного в Vertex AR.

---

## 🎯 Основные требования

### 1. Архитектура AR-контента

Vertex AR использует технологию **AR.js** с NFT (Natural Feature Tracking) маркерами для распознавания изображений. Мобильное приложение должно:

1. Загружать NFT маркеры для распознавания изображений
2. Воспроизводить видео при успешном распознавании
3. Отслеживать статистику просмотров
4. Работать офлайн (после загрузки данных)

### 2. Технология AR.js

**AR.js** - это библиотека для веб-AR, работающая на базе:
- **WebGL** для рендеринга
- **WebRTC** для доступа к камере
- **NFT маркеры** для распознавания изображений

Для React Native потребуется:
- `react-native-webview` или
- Нативная интеграция AR (ARCore/ARKit)

---

## 📊 Структура данных

### 1. Основные сущности

#### Company (Компания)
```json
{
  "id": "uuid",
  "name": "string",
  "created_at": "ISO8601 timestamp"
}
```

#### Client (Клиент)
```json
{
  "id": "uuid",
  "company_id": "uuid",
  "phone": "string",
  "name": "string",
  "created_at": "ISO8601 timestamp"
}
```

#### Portrait (Портрет/AR-изображение)
```json
{
  "id": "uuid",
  "client_id": "uuid",
  "permanent_link": "string",
  "image_path": "string (relative path)",
  "image_preview_path": "string (relative path)",
  "marker_fset": "string (path to .fset file)",
  "marker_fset3": "string (path to .fset3 file)",
  "marker_iset": "string (path to .iset file)",
  "qr_code": "string (base64 encoded PNG)",
  "view_count": "integer",
  "created_at": "ISO8601 timestamp"
}
```

#### Video (Видео для AR)
```json
{
  "id": "uuid",
  "portrait_id": "uuid",
  "video_path": "string (relative path)",
  "video_preview_path": "string (relative path)",
  "description": "string (optional)",
  "is_active": "boolean",
  "created_at": "ISO8601 timestamp",
  "file_size_mb": "integer (optional)"
}
```

---

## 🔌 API Endpoints для мобильного приложения

### 1. Получение списка портретов

**Endpoint:** `GET /api/mobile/portraits`

**Параметры:**
- `company_id` (optional) - фильтр по компании
- `client_id` (optional) - фильтр по клиенту
- `include_inactive` (optional, default: false) - включить портреты без активного видео

**Response:**
```json
{
  "portraits": [
    {
      "id": "portrait-uuid",
      "permanent_link": "portrait_abc123",
      "client": {
        "id": "client-uuid",
        "name": "Иван Иванов",
        "phone": "+79991234567"
      },
      "image": {
        "url": "https://example.com/storage/portraits/client-uuid/portrait-uuid.jpg",
        "preview_url": "https://example.com/storage/portraits/client-uuid/portrait-uuid_preview.webp",
        "width": 1920,
        "height": 1080
      },
      "markers": {
        "fset": "https://example.com/nft-markers/portrait-uuid/portrait-uuid.fset",
        "fset3": "https://example.com/nft-markers/portrait-uuid/portrait-uuid.fset3",
        "iset": "https://example.com/nft-markers/portrait-uuid/portrait-uuid.iset"
      },
      "active_video": {
        "id": "video-uuid",
        "url": "https://example.com/storage/videos/portrait-uuid/video-uuid.mp4",
        "preview_url": "https://example.com/storage/videos/portrait-uuid/video-uuid_preview.webp",
        "description": "Видео поздравление",
        "file_size_mb": 15,
        "duration_seconds": 30
      },
      "qr_code": "data:image/png;base64,iVBORw0KG...",
      "view_count": 42,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

### 2. Получение конкретного портрета по permanent_link

**Endpoint:** `GET /api/mobile/portraits/{permanent_link}`

**Response:** Объект портрета (см. выше)

### 3. Отправка статистики просмотра

**Endpoint:** `POST /api/mobile/portraits/{portrait_id}/view`

**Body:**
```json
{
  "timestamp": "ISO8601",
  "duration_seconds": 15,
  "device_info": {
    "platform": "ios|android",
    "os_version": "15.0",
    "app_version": "1.0.0"
  }
}
```

**Response:**
```json
{
  "success": true,
  "view_count": 43
}
```

### 4. Получение компаний

**Endpoint:** `GET /api/mobile/companies`

**Response:**
```json
{
  "companies": [
    {
      "id": "company-uuid",
      "name": "Vertex AR",
      "portraits_count": 150,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

## 🎨 Ресурсы для загрузки

### 1. Изображения
- **Оригинал:** `/storage/portraits/{client_id}/{portrait_id}.jpg`
- **Preview:** `/storage/portraits/{client_id}/{portrait_id}_preview.webp` (300x300px)
- **Формат:** JPG (оригинал), WebP (preview)

### 2. Видео
- **Оригинал:** `/storage/videos/{portrait_id}/{video_id}.mp4`
- **Preview:** `/storage/videos/{portrait_id}/{video_id}_preview.webp`
- **Формат:** MP4 (H.264)
- **Рекомендуемое разрешение:** 720p-1080p
- **Битрейт:** 2-5 Mbps

### 3. NFT Маркеры
Для каждого портрета генерируются 3 файла:

- **`.fset`** - Feature Set (основные характеристики изображения)
- **`.fset3`** - Feature Set Level 3 (детализированные данные)
- **`.iset`** - Image Set (сжатое представление изображения)

**Расположение:** `/nft-markers/{portrait_id}/`

**Использование в AR.js:**
```html
<a-nft
  type="nft"
  url="/nft-markers/portrait-uuid/portrait-uuid"
  smooth="true"
  smoothCount="10"
  smoothTolerance="0.01"
  smoothThreshold="5"
>
  <a-video
    src="#video"
    position="0 0 0"
    width="1"
    height="1"
    rotation="-90 0 0"
  ></a-video>
</a-nft>
```

### 4. QR коды
- **Формат:** Base64-encoded PNG
- **Содержимое:** URL вида `https://example.com/portrait/{permanent_link}`
- **Размер:** 300x300px
- **Использование:** Быстрый доступ к AR контенту через камеру

---

## 🔐 Аутентификация

### Публичный доступ
Портреты с `permanent_link` доступны без аутентификации:
```
GET /portrait/{permanent_link}
```

### API доступ (требуется токен)
Для получения списков и управления контентом:
```
Authorization: Bearer {access_token}
```

**Получение токена:**
```http
POST /auth/login
Content-Type: application/json

{
  "username": "user",
  "password": "password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

---

## 📱 Архитектура мобильного приложения

### Рекомендуемый стек

```
React Native (0.72+)
├── react-native-webview (WebGL AR.js)
├── react-native-fs (загрузка файлов)
├── @react-native-async-storage/async-storage (кеш)
├── react-native-qrcode-scanner (QR сканер)
└── axios (HTTP клиент)
```

### Альтернатива: Нативный AR

```
React Native (0.72+)
├── react-native-viro (ARCore/ARKit)
├── или ViroReact
└── Потребуется конвертация NFT маркеров
```

### Основные экраны

1. **Список портретов** - галерея доступного AR контента
2. **AR Scanner** - камера для распознавания изображений
3. **QR Scanner** - сканирование QR кодов
4. **Детали портрета** - информация, статистика
5. **Настройки** - выбор компании, кеш

---

## 💾 Стратегия кеширования

### Что кешировать локально:

1. **Метаданные портретов** (JSON) - 7 дней
2. **Preview изображений** (WebP) - 30 дней
3. **NFT маркеры** (.fset, .fset3, .iset) - постоянно
4. **Видео** (опционально) - по выбору пользователя

### Размеры файлов:

- Portrait preview: ~50-100 KB (WebP)
- NFT маркеры (все 3 файла): ~500 KB - 2 MB
- Video preview: ~100-200 KB (WebP)
- Video full: 5-50 MB (MP4)

**Оценка:** 
- 100 портретов с маркерами: ~100-200 MB
- 100 портретов с видео: ~1-5 GB

---

## 🔄 Синхронизация данных

### Initial Load (первая загрузка)
```
1. GET /api/mobile/companies → выбор компании
2. GET /api/mobile/portraits?company_id=X → список портретов
3. Загрузка preview изображений
4. Фоновая загрузка NFT маркеров (по приоритету)
```

### Incremental Update (обновление)
```
1. GET /api/mobile/portraits?updated_since=2024-01-15T10:00:00Z
2. Обновление измененных портретов
3. Удаление устаревших из кеша
```

### Offline Mode
```
- Использование закешированных данных
- Очередь событий view для отправки при восстановлении сети
- Индикация устаревших данных
```

---

## 🎥 Работа с AR контентом

### Процесс распознавания

1. **Инициализация AR.js**
```javascript
const arScene = new ARScene({
  markerUrl: '/nft-markers/portrait-uuid/portrait-uuid',
  videoUrl: '/storage/videos/...'
});
```

2. **Обнаружение маркера**
```javascript
arScene.on('markerFound', (marker) => {
  // Начать воспроизведение видео
  videoElement.play();
  // Отправить событие view
  trackView(marker.portraitId);
});
```

3. **Потеря маркера**
```javascript
arScene.on('markerLost', (marker) => {
  // Приостановить видео
  videoElement.pause();
});
```

### Оптимизация производительности

- **Предзагрузка видео** перед стартом AR сканирования
- **Уменьшение разрешения камеры** для слабых устройств (640x480 вместо 1280x720)
- **Ограничение FPS** до 30fps
- **Adaptive quality** - снижение качества при низком FPS

---

## 📊 Аналитика и метрики

### События для отслеживания:

1. **portrait_viewed** - портрет просмотрен в AR
2. **portrait_scanned** - QR код отсканирован
3. **video_started** - видео начало воспроизведение
4. **video_completed** - видео просмотрено до конца
5. **marker_scan_duration** - время до распознавания маркера

### Данные для отправки:
```json
{
  "event": "portrait_viewed",
  "portrait_id": "uuid",
  "timestamp": "ISO8601",
  "session_id": "uuid",
  "duration_seconds": 15,
  "device": {
    "platform": "ios",
    "model": "iPhone 14",
    "os_version": "16.0"
  },
  "ar_info": {
    "scan_time_ms": 1500,
    "fps_average": 28,
    "marker_lost_count": 2
  }
}
```

---

## 🛠️ Вспомогательные endpoints

### Получение информации о файле
```http
HEAD /storage/portraits/{client_id}/{portrait_id}.jpg
```
**Response Headers:**
- `Content-Length`: размер в байтах
- `Content-Type`: image/jpeg
- `Last-Modified`: дата изменения

### Проверка доступности маркера
```http
GET /api/mobile/portraits/{portrait_id}/marker-status
```
**Response:**
```json
{
  "available": true,
  "files": {
    "fset": { "size": 850000, "updated_at": "2024-01-15T10:00:00Z" },
    "fset3": { "size": 650000, "updated_at": "2024-01-15T10:00:00Z" },
    "iset": { "size": 450000, "updated_at": "2024-01-15T10:00:00Z" }
  },
  "total_size_mb": 1.85
}
```

---

## 🔗 Примеры интеграции

### React Native WebView подход

```jsx
import React from 'react';
import { WebView } from 'react-native-webview';

const ARViewer = ({ portraitId, markerUrl, videoUrl }) => {
  const html = `
    <!DOCTYPE html>
    <html>
      <head>
        <script src="https://cdn.jsdelivr.net/npm/ar.js@3.4.5/aframe/build/aframe-ar-nft.js"></script>
      </head>
      <body style="margin: 0; overflow: hidden;">
        <a-scene
          vr-mode-ui="enabled: false"
          renderer="logarithmicDepthBuffer: true;"
          embedded
          arjs="trackingMethod: best; sourceType: webcam; debugUIEnabled: false;"
        >
          <a-assets>
            <video id="vid" src="${videoUrl}" preload="auto" loop crossorigin="anonymous" playsinline></video>
          </a-assets>

          <a-nft
            type="nft"
            url="${markerUrl}"
            smooth="true"
            smoothCount="10"
            smoothTolerance=".01"
            smoothThreshold="5"
          >
            <a-video
              src="#vid"
              position="0 0 0"
              width="1"
              height="1"
              rotation="-90 0 0"
            ></a-video>
          </a-nft>

          <a-entity camera></a-entity>
        </a-scene>
      </body>
    </html>
  `;

  return (
    <WebView
      source={{ html }}
      mediaPlaybackRequiresUserAction={false}
      allowsInlineMediaPlayback
      javaScriptEnabled
      domStorageEnabled
    />
  );
};
```

### Загрузка и кеширование файлов

```javascript
import RNFS from 'react-native-fs';
import AsyncStorage from '@react-native-async-storage/async-storage';

const downloadMarkerFiles = async (portraitId, markerUrls) => {
  const cacheDir = `${RNFS.DocumentDirectoryPath}/markers/${portraitId}`;
  
  // Создать директорию если не существует
  await RNFS.mkdir(cacheDir);
  
  // Скачать все файлы маркера
  for (const [fileType, url] of Object.entries(markerUrls)) {
    const filePath = `${cacheDir}/${portraitId}.${fileType}`;
    
    // Проверить существование
    const exists = await RNFS.exists(filePath);
    if (!exists) {
      await RNFS.downloadFile({
        fromUrl: url,
        toFile: filePath
      }).promise;
    }
  }
  
  // Сохранить метаданные
  await AsyncStorage.setItem(
    `marker_${portraitId}`,
    JSON.stringify({
      downloaded_at: new Date().toISOString(),
      cache_dir: cacheDir
    })
  );
  
  return cacheDir;
};
```

### Отправка статистики просмотров

```javascript
const trackPortraitView = async (portraitId, duration) => {
  try {
    await fetch(`${API_BASE_URL}/api/mobile/portraits/${portraitId}/view`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        timestamp: new Date().toISOString(),
        duration_seconds: Math.round(duration),
        device_info: {
          platform: Platform.OS,
          os_version: Platform.Version.toString(),
          app_version: APP_VERSION
        }
      })
    });
  } catch (error) {
    // Сохранить в очередь для повторной отправки
    await queueOfflineEvent('portrait_view', {
      portraitId,
      duration,
      timestamp: new Date().toISOString()
    });
  }
};
```

---

## ⚠️ Важные замечания

### Ограничения AR.js в WebView

1. **Производительность** - WebView медленнее нативного AR
2. **Доступ к камере** - может требовать дополнительных разрешений
3. **Размер маркеров** - большие изображения могут не распознаваться
4. **Освещение** - требуется хорошее освещение для распознавания

### Рекомендации по изображениям

1. **Контрастность** - высококонтрастные изображения лучше распознаются
2. **Детали** - изображения с множеством деталей работают лучше
3. **Размер** - минимум 640x480px, оптимально 1280x720px
4. **Избегать** - однотонные, размытые, с бликами изображения

### Оптимизация видео

1. **Кодек** - H.264 (максимальная совместимость)
2. **Контейнер** - MP4
3. **Разрешение** - 720p (баланс качества и размера)
4. **Битрейт** - 2-3 Mbps (достаточно для мобильного)
5. **Длительность** - рекомендуется 15-30 секунд

---

## 🚀 Roadmap мобильного приложения

### MVP (v1.0)
- ✅ Список портретов с preview
- ✅ AR просмотр через WebView
- ✅ QR код сканер
- ✅ Базовый кеш маркеров
- ✅ Отправка статистики просмотров

### v1.1
- 📋 Оффлайн режим с очередью событий
- 📋 Управление кешем (очистка, выборочная загрузка)
- 📋 Фильтрация по компаниям
- 📋 История просмотров

### v1.2
- 📋 Нативный AR (ARCore/ARKit)
- 📋 Расширенная аналитика
- 📋 Уведомления о новом контенте
- 📋 Социальный шеринг

### v2.0
- 📋 Создание контента в приложении
- 📋 Редактирование видео
- 📋 Мультиязычность
- 📋 Dark mode

---

## 📞 Поддержка

При возникновении вопросов по интеграции:
- Email: dev@vertex-ar.example.com
- GitHub Issues: [github.com/vertex-ar/issues](https://github.com/vertex-ar/issues)
- API Documentation: https://example.com/api/docs

---

**Последнее обновление:** 2024  
**Версия документа:** 1.0.0
