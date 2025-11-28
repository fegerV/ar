# Руководство по разработке мобильного приложения React Native для Vertex AR

## 🎯 Цель

Этот документ предоставляет быстрый старт для разработчиков мобильных приложений, которые хотят интегрировать AR-контент из Vertex AR в свое React Native приложение.

## 📚 Основная документация

Полная документация по интеграции находится в:
- **[Требования к данным для React Native](docs/api/mobile-rn-requirements.md)** - полное описание архитектуры, структур данных и технических требований
- **[Примеры использования API](docs/api/mobile-examples.md)** - готовые примеры кода для React Native
- **[OpenAPI Schema](docs/api/mobile-api-schema.json)** - JSON Schema для генерации клиентов API

## ⚡ Быстрый старт

### 1. Что вам понадобится

**Серверная часть:**
- Запущенный Vertex AR сервер
- API токен для аутентификации (получается через `/auth/login`)

**Клиентская часть (React Native):**
```json
{
  "dependencies": {
    "react-native": "^0.72.0",
    "react-native-webview": "^13.0.0",
    "react-native-fs": "^2.20.0",
    "@react-native-async-storage/async-storage": "^1.19.0",
    "react-native-qrcode-scanner": "^1.5.0",
    "axios": "^1.4.0"
  }
}
```

### 2. Основные API endpoints

#### Получение списка портретов
```
GET /api/mobile/portraits?page=1&page_size=20
Authorization: Bearer {token}
```

#### Получение портрета по ссылке (публичный)
```
GET /api/mobile/portraits/{permanent_link}
```

#### Отслеживание просмотров (публичный)
```
POST /api/mobile/portraits/{portrait_id}/view
Content-Type: application/json

{
  "timestamp": "2024-01-15T10:30:00Z",
  "duration_seconds": 25,
  "device_info": {
    "platform": "ios",
    "os_version": "15.0",
    "app_version": "1.0.0"
  }
}
```

### 3. Структура данных портрета

Каждый портрет содержит:
- **Изображение** - оригинал и preview (WebP)
- **NFT маркеры** - 3 файла для AR.js (.fset, .fset3, .iset)
- **Видео** - активное видео для воспроизведения в AR
- **Клиент** - информация о владельце
- **QR код** - для быстрого доступа

```json
{
  "id": "portrait-uuid",
  "permanent_link": "portrait_abc123",
  "image": {
    "url": "https://server.com/storage/portraits/client-uuid/portrait-uuid.jpg",
    "preview_url": "https://server.com/storage/portraits/.../portrait-uuid_preview.webp"
  },
  "markers": {
    "fset": "https://server.com/nft-markers/portrait-uuid/portrait-uuid.fset",
    "fset3": "https://server.com/nft-markers/portrait-uuid/portrait-uuid.fset3",
    "iset": "https://server.com/nft-markers/portrait-uuid/portrait-uuid.iset"
  },
  "active_video": {
    "id": "video-uuid",
    "url": "https://server.com/storage/videos/portrait-uuid/video-uuid.mp4",
    "preview_url": "https://server.com/.../video-uuid_preview.webp"
  },
  "qr_code": "data:image/png;base64,iVBORw...",
  "view_count": 42
}
```

## 🎨 Архитектура приложения

### Рекомендуемая структура

```
mobile-app/
├── src/
│   ├── api/
│   │   ├── client.js          # API клиент
│   │   ├── auth.js            # Аутентификация
│   │   └── portraits.js       # Портреты API
│   ├── screens/
│   │   ├── PortraitsList.jsx  # Список портретов
│   │   ├── ARViewer.jsx       # AR просмотр
│   │   └── QRScanner.jsx      # QR сканер
│   ├── services/
│   │   ├── cache.js           # Управление кешем
│   │   ├── download.js        # Загрузка файлов
│   │   └── analytics.js       # Аналитика
│   └── utils/
│       ├── storage.js         # AsyncStorage
│       └── offline.js         # Офлайн очередь
```

### Основные компоненты

1. **Portrait Gallery** - отображение списка доступных портретов
2. **AR Viewer** - камера + AR.js для распознавания и воспроизведения
3. **QR Scanner** - сканирование QR кодов для быстрого доступа
4. **Cache Manager** - управление локальным хранилищем маркеров и видео
5. **Analytics Tracker** - отслеживание просмотров и статистики

## 🔧 Технические особенности

### AR.js интеграция

**Вариант 1: WebView (проще, но медленнее)**
- Использовать `react-native-webview`
- Загрузить HTML с AR.js
- Передать URL маркеров и видео

**Вариант 2: Нативный AR (быстрее, сложнее)**
- ARKit для iOS
- ARCore для Android
- Использовать ViroReact или react-native-viro
- Потребуется конвертация NFT маркеров

### Кеширование

**Что кешировать:**
- ✅ Метаданные портретов (JSON) - обязательно
- ✅ Preview изображений (WebP) - обязательно
- ✅ NFT маркеры (.fset, .fset3, .iset) - обязательно
- ⚠️ Полные видео (MP4) - опционально (большой размер)

**Размеры файлов:**
- Один портрет (метаданные): ~5 KB
- Preview изображение: ~50-100 KB
- NFT маркеры: ~500 KB - 2 MB
- Видео: 5-50 MB

**Оценка:** 100 портретов с маркерами ≈ 100-200 MB

### Офлайн режим

1. Загрузить список портретов при наличии сети
2. Кешировать маркеры для избранных портретов
3. Сохранять события просмотров в локальную очередь
4. Синхронизировать при восстановлении соединения

## 📱 Пример использования

### Минимальный AR Viewer

```jsx
import React from 'react';
import { WebView } from 'react-native-webview';

const ARViewer = ({ portrait }) => {
  const html = `
    <!DOCTYPE html>
    <html>
      <head>
        <script src="https://cdn.jsdelivr.net/npm/ar.js@3.4.5/aframe/build/aframe-ar-nft.js"></script>
      </head>
      <body style="margin: 0;">
        <a-scene embedded arjs>
          <a-assets>
            <video id="vid" src="${portrait.active_video.url}"
                   loop playsinline></video>
          </a-assets>
          <a-nft type="nft"
                 url="${portrait.markers.fset.replace('.fset', '')}"
                 smooth="true">
            <a-video src="#vid" width="1" height="1"
                     rotation="-90 0 0"></a-video>
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
      allowsInlineMediaPlayback={true}
    />
  );
};
```

### Отслеживание просмотров

```javascript
import { useEffect, useState } from 'react';

const useViewTracking = (portraitId) => {
  const [startTime] = useState(Date.now());

  useEffect(() => {
    return () => {
      const duration = Math.round((Date.now() - startTime) / 1000);
      if (duration > 2) {
        fetch(`${API_URL}/api/mobile/portraits/${portraitId}/view`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            timestamp: new Date().toISOString(),
            duration_seconds: duration,
            device_info: {
              platform: Platform.OS,
              os_version: String(Platform.Version),
              app_version: '1.0.0'
            }
          })
        }).catch(console.error);
      }
    };
  }, [portraitId]);
};
```

## 🔐 Безопасность

1. **Токены:** Храните JWT токены в защищенном хранилище
2. **HTTPS:** Используйте только HTTPS в продакшене
3. **Публичные endpoints:** `/api/mobile/portraits/{link}` и `/view` доступны без токена
4. **Rate limiting:** Учитывайте лимиты запросов (100/min глобально)

## 📊 Метрики и аналитика

Отслеживайте:
- Количество просмотров портретов
- Время сканирования маркера (scan_time_ms)
- Средний FPS (для оптимизации)
- Количество потерь маркера (marker_lost_count)
- Длительность просмотров

```javascript
await trackPortraitView(portraitId, duration, {
  scan_time_ms: 1200,      // Время до распознавания
  fps_average: 28.5,       // Средний FPS
  marker_lost_count: 3     // Сколько раз потерян маркер
});
```

## 🚀 Roadmap

### MVP (v1.0)
- [x] API endpoints для мобильного приложения
- [x] Документация и примеры
- [x] OpenAPI Schema
- [ ] React Native пример приложения
- [ ] Тестирование на iOS/Android

### v1.1
- [ ] Оффлайн режим с синхронизацией
- [ ] Управление кешем
- [ ] Фоновая загрузка маркеров
- [ ] Push уведомления о новом контенте

### v2.0
- [ ] Нативная AR интеграция (ARKit/ARCore)
- [ ] Создание контента в приложении
- [ ] Социальный шеринг
- [ ] Расширенная аналитика

## 🆘 Поддержка

**Вопросы и проблемы:**
- GitHub Issues: [создать issue](https://github.com/fegerV/AR/issues)
- Email: dev@vertex-ar.example.com
- Документация: [docs/api/mobile-rn-requirements.md](docs/api/mobile-rn-requirements.md)

**Полезные ресурсы:**
- [AR.js Documentation](https://ar-js-org.github.io/AR.js-Docs/)
- [React Native WebView](https://github.com/react-native-webview/react-native-webview)
- [ViroReact](https://github.com/NativeVision/viro)

## 📄 Лицензия

См. [LICENSE](LICENSE) в корне проекта.

---

**Версия:** 1.0.0
**Последнее обновление:** 2024
**Статус:** ✅ Готово к использованию
