# Примеры использования Mobile API

Этот документ содержит практические примеры интеграции Vertex AR Mobile API в React Native приложение.

## Оглавление

1. [Аутентификация](#аутентификация)
2. [Получение списка портретов](#получение-списка-портретов)
3. [Получение портрета по ссылке](#получение-портрета-по-ссылке)
4. [Отслеживание просмотров](#отслеживание-просмотров)
5. [Управление кешем](#управление-кешем)
6. [Полный пример React Native компонента](#полный-пример-react-native-компонента)

---

## Аутентификация

### Получение токена доступа

```javascript
const API_BASE_URL = 'https://your-vertex-ar-server.com';

async function login(username, password) {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      throw new Error('Authentication failed');
    }

    const data = await response.json();
    return data.access_token;
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
}

// Сохранение токена
import AsyncStorage from '@react-native-async-storage/async-storage';

async function saveToken(token) {
  await AsyncStorage.setItem('auth_token', token);
}

async function getToken() {
  return await AsyncStorage.getItem('auth_token');
}
```

### Использование токена в запросах

```javascript
async function fetchWithAuth(url, options = {}) {
  const token = await getToken();
  
  const headers = {
    ...options.headers,
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };

  return fetch(url, { ...options, headers });
}
```

---

## Получение списка портретов

### Базовый запрос

```javascript
async function getPortraits(page = 1, pageSize = 20) {
  try {
    const response = await fetchWithAuth(
      `${API_BASE_URL}/api/mobile/portraits?page=${page}&page_size=${pageSize}`
    );

    if (!response.ok) {
      throw new Error('Failed to fetch portraits');
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching portraits:', error);
    throw error;
  }
}

// Использование
const portraitsData = await getPortraits(1, 20);
console.log(`Loaded ${portraitsData.portraits.length} of ${portraitsData.total} portraits`);
```

### С фильтрацией по компании

```javascript
async function getPortraitsByCompany(companyId, page = 1) {
  const response = await fetchWithAuth(
    `${API_BASE_URL}/api/mobile/portraits?company_id=${companyId}&page=${page}&page_size=20`
  );

  return await response.json();
}
```

### С фильтрацией по клиенту

```javascript
async function getPortraitsByClient(clientId) {
  const response = await fetchWithAuth(
    `${API_BASE_URL}/api/mobile/portraits?client_id=${clientId}&page_size=100`
  );

  return await response.json();
}
```

### Включая портреты без активного видео

```javascript
async function getAllPortraits(includeInactive = false) {
  const response = await fetchWithAuth(
    `${API_BASE_URL}/api/mobile/portraits?include_inactive=${includeInactive}&page_size=100`
  );

  return await response.json();
}
```

---

## Получение портрета по ссылке

### Публичный доступ (без токена)

```javascript
async function getPortraitByLink(permanentLink) {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/mobile/portraits/${permanentLink}`
    );

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Portrait not found');
      }
      throw new Error('Failed to fetch portrait');
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching portrait:', error);
    throw error;
  }
}

// Использование с QR кодом
async function handleQRCodeScan(qrData) {
  // QR код содержит URL: https://server.com/portrait/portrait_abc123
  const url = new URL(qrData);
  const permanentLink = url.pathname.split('/').pop();
  
  const portrait = await getPortraitByLink(permanentLink);
  return portrait;
}
```

---

## Отслеживание просмотров

### Отправка события просмотра

```javascript
import { Platform } from 'react-native';
import DeviceInfo from 'react-native-device-info';

async function trackPortraitView(
  portraitId,
  durationSeconds,
  arInfo = null
) {
  try {
    const viewData = {
      timestamp: new Date().toISOString(),
      duration_seconds: Math.round(durationSeconds),
      device_info: {
        platform: Platform.OS,
        os_version: Platform.Version.toString(),
        app_version: await DeviceInfo.getVersion(),
        model: await DeviceInfo.getModel(),
      },
    };

    if (arInfo) {
      viewData.ar_info = arInfo;
    }

    const response = await fetch(
      `${API_BASE_URL}/api/mobile/portraits/${portraitId}/view`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(viewData),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to track view');
    }

    const result = await response.json();
    console.log(`View tracked. Total views: ${result.view_count}`);
    return result;
  } catch (error) {
    console.error('Error tracking view:', error);
    // Сохранить в очередь для повторной отправки
    await queueOfflineView(portraitId, durationSeconds, arInfo);
    throw error;
  }
}

// Пример с AR информацией
await trackPortraitView('portrait-uuid', 25, {
  scan_time_ms: 1200,
  fps_average: 28.5,
  marker_lost_count: 3,
});
```

### Очередь офлайн событий

```javascript
const OFFLINE_QUEUE_KEY = 'offline_views_queue';

async function queueOfflineView(portraitId, duration, arInfo) {
  try {
    const queue = await AsyncStorage.getItem(OFFLINE_QUEUE_KEY);
    const views = queue ? JSON.parse(queue) : [];
    
    views.push({
      portraitId,
      duration,
      arInfo,
      timestamp: new Date().toISOString(),
    });
    
    await AsyncStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(views));
    console.log('View queued for offline sync');
  } catch (error) {
    console.error('Failed to queue view:', error);
  }
}

async function syncOfflineViews() {
  try {
    const queue = await AsyncStorage.getItem(OFFLINE_QUEUE_KEY);
    if (!queue) return;
    
    const views = JSON.parse(queue);
    if (views.length === 0) return;
    
    console.log(`Syncing ${views.length} offline views...`);
    
    const failed = [];
    for (const view of views) {
      try {
        await trackPortraitView(
          view.portraitId,
          view.duration,
          view.arInfo
        );
      } catch (error) {
        failed.push(view);
      }
    }
    
    if (failed.length > 0) {
      await AsyncStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(failed));
    } else {
      await AsyncStorage.removeItem(OFFLINE_QUEUE_KEY);
    }
    
    console.log(`Synced ${views.length - failed.length} views`);
  } catch (error) {
    console.error('Failed to sync offline views:', error);
  }
}

// Вызывать при восстановлении соединения
import NetInfo from '@react-native-community/netinfo';

NetInfo.addEventListener(state => {
  if (state.isConnected) {
    syncOfflineViews();
  }
});
```

---

## Управление кешем

### Загрузка NFT маркеров

```javascript
import RNFS from 'react-native-fs';

const MARKERS_CACHE_DIR = `${RNFS.DocumentDirectoryPath}/markers`;

async function downloadMarkerFiles(portrait) {
  const portraitDir = `${MARKERS_CACHE_DIR}/${portrait.id}`;
  
  // Создать директорию
  await RNFS.mkdir(portraitDir);
  
  const files = {
    fset: portrait.markers.fset,
    fset3: portrait.markers.fset3,
    iset: portrait.markers.iset,
  };
  
  const downloads = [];
  
  for (const [type, url] of Object.entries(files)) {
    const filePath = `${portraitDir}/${portrait.id}.${type}`;
    
    // Проверить существование
    const exists = await RNFS.exists(filePath);
    if (!exists) {
      downloads.push(
        RNFS.downloadFile({
          fromUrl: url,
          toFile: filePath,
        }).promise
      );
    }
  }
  
  await Promise.all(downloads);
  
  // Сохранить метаданные
  await AsyncStorage.setItem(
    `marker_${portrait.id}`,
    JSON.stringify({
      downloaded_at: new Date().toISOString(),
      cache_dir: portraitDir,
    })
  );
  
  return portraitDir;
}
```

### Проверка статуса маркера

```javascript
async function checkMarkerStatus(portraitId) {
  try {
    const response = await fetchWithAuth(
      `${API_BASE_URL}/api/mobile/portraits/${portraitId}/marker-status`
    );

    if (!response.ok) {
      throw new Error('Failed to check marker status');
    }

    return await response.json();
  } catch (error) {
    console.error('Error checking marker status:', error);
    throw error;
  }
}

// Использование
const status = await checkMarkerStatus('portrait-uuid');
if (status.available) {
  console.log(`Markers available, total size: ${status.total_size_mb} MB`);
  console.log('Files:', status.files);
} else {
  console.log('Some marker files are missing');
}
```

### Кеширование preview изображений

```javascript
const PREVIEWS_CACHE_DIR = `${RNFS.DocumentDirectoryPath}/previews`;

async function cachePortraitPreviews(portraits) {
  await RNFS.mkdir(PREVIEWS_CACHE_DIR);
  
  const downloads = portraits
    .filter(p => p.image.preview_url)
    .map(portrait => {
      const fileName = `${portrait.id}_preview.webp`;
      const filePath = `${PREVIEWS_CACHE_DIR}/${fileName}`;
      
      return RNFS.downloadFile({
        fromUrl: portrait.image.preview_url,
        toFile: filePath,
      }).promise;
    });
  
  await Promise.all(downloads);
  console.log(`Cached ${downloads.length} preview images`);
}

async function getCachedPreview(portraitId) {
  const filePath = `${PREVIEWS_CACHE_DIR}/${portraitId}_preview.webp`;
  const exists = await RNFS.exists(filePath);
  
  if (exists) {
    return `file://${filePath}`;
  }
  
  return null;
}
```

### Очистка кеша

```javascript
async function clearCache() {
  try {
    // Очистка маркеров
    const markersExists = await RNFS.exists(MARKERS_CACHE_DIR);
    if (markersExists) {
      await RNFS.unlink(MARKERS_CACHE_DIR);
    }
    
    // Очистка preview
    const previewsExists = await RNFS.exists(PREVIEWS_CACHE_DIR);
    if (previewsExists) {
      await RNFS.unlink(PREVIEWS_CACHE_DIR);
    }
    
    // Очистка метаданных
    const keys = await AsyncStorage.getAllKeys();
    const markerKeys = keys.filter(k => k.startsWith('marker_'));
    await AsyncStorage.multiRemove(markerKeys);
    
    console.log('Cache cleared successfully');
  } catch (error) {
    console.error('Error clearing cache:', error);
    throw error;
  }
}

async function getCacheSize() {
  let totalSize = 0;
  
  async function getDirSize(path) {
    try {
      const exists = await RNFS.exists(path);
      if (!exists) return 0;
      
      const files = await RNFS.readDir(path);
      let size = 0;
      
      for (const file of files) {
        if (file.isDirectory()) {
          size += await getDirSize(file.path);
        } else {
          size += file.size;
        }
      }
      
      return size;
    } catch (error) {
      return 0;
    }
  }
  
  totalSize += await getDirSize(MARKERS_CACHE_DIR);
  totalSize += await getDirSize(PREVIEWS_CACHE_DIR);
  
  const sizeMB = (totalSize / (1024 * 1024)).toFixed(2);
  return { bytes: totalSize, mb: sizeMB };
}
```

---

## Полный пример React Native компонента

### Portrait Gallery Component

```jsx
import React, { useState, useEffect } from 'react';
import {
  View,
  FlatList,
  Image,
  Text,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';

const PortraitGallery = ({ companyId }) => {
  const [portraits, setPortraits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const navigation = useNavigation();

  useEffect(() => {
    loadPortraits();
  }, [companyId]);

  const loadPortraits = async () => {
    try {
      setLoading(true);
      
      const query = companyId 
        ? `?company_id=${companyId}&page=1&page_size=20`
        : '?page=1&page_size=20';
      
      const response = await fetchWithAuth(
        `${API_BASE_URL}/api/mobile/portraits${query}`
      );

      const data = await response.json();
      setPortraits(data.portraits);
      setHasMore(data.portraits.length < data.total);
      setPage(1);
    } catch (error) {
      console.error('Error loading portraits:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadMore = async () => {
    if (!hasMore || loading) return;

    try {
      const nextPage = page + 1;
      const query = companyId
        ? `?company_id=${companyId}&page=${nextPage}&page_size=20`
        : `?page=${nextPage}&page_size=20`;

      const response = await fetchWithAuth(
        `${API_BASE_URL}/api/mobile/portraits${query}`
      );

      const data = await response.json();
      setPortraits([...portraits, ...data.portraits]);
      setPage(nextPage);
      setHasMore(portraits.length + data.portraits.length < data.total);
    } catch (error) {
      console.error('Error loading more:', error);
    }
  };

  const openARViewer = async (portrait) => {
    // Загрузить маркеры перед переходом
    try {
      const markerDir = await downloadMarkerFiles(portrait);
      navigation.navigate('ARViewer', { 
        portrait,
        markerDir 
      });
    } catch (error) {
      console.error('Error preparing AR viewer:', error);
      alert('Failed to prepare AR viewer');
    }
  };

  const renderPortrait = ({ item }) => (
    <TouchableOpacity
      style={styles.portraitCard}
      onPress={() => openARViewer(item)}
    >
      <Image
        source={{ uri: item.image.preview_url }}
        style={styles.preview}
        resizeMode="cover"
      />
      <View style={styles.info}>
        <Text style={styles.clientName}>{item.client.name}</Text>
        <Text style={styles.views}>👁️ {item.view_count} views</Text>
        {item.active_video && (
          <View style={styles.videoIndicator}>
            <Text style={styles.videoText}>▶️ Video available</Text>
          </View>
        )}
      </View>
    </TouchableOpacity>
  );

  if (loading && portraits.length === 0) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  return (
    <FlatList
      data={portraits}
      renderItem={renderPortrait}
      keyExtractor={item => item.id}
      numColumns={2}
      onEndReached={loadMore}
      onEndReachedThreshold={0.5}
      ListFooterComponent={
        hasMore && <ActivityIndicator style={styles.loader} />
      }
      contentContainerStyle={styles.container}
    />
  );
};

const styles = StyleSheet.create({
  container: {
    padding: 10,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  portraitCard: {
    flex: 1,
    margin: 5,
    backgroundColor: 'white',
    borderRadius: 10,
    overflow: 'hidden',
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  preview: {
    width: '100%',
    height: 150,
    backgroundColor: '#f0f0f0',
  },
  info: {
    padding: 10,
  },
  clientName: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 5,
  },
  views: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5,
  },
  videoIndicator: {
    backgroundColor: '#4CAF50',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    alignSelf: 'flex-start',
  },
  videoText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '500',
  },
  loader: {
    marginVertical: 20,
  },
});

export default PortraitGallery;
```

### AR Viewer Component

```jsx
import React, { useState, useEffect, useRef } from 'react';
import { View, StyleSheet, Alert } from 'react-native';
import { WebView } from 'react-native-webview';

const ARViewer = ({ route }) => {
  const { portrait, markerDir } = route.params;
  const [viewStartTime] = useState(Date.now());
  const webViewRef = useRef(null);

  useEffect(() => {
    return () => {
      // Отправить событие просмотра при выходе
      const duration = Math.round((Date.now() - viewStartTime) / 1000);
      if (duration > 2) {
        trackPortraitView(portrait.id, duration).catch(console.error);
      }
    };
  }, []);

  const generateARHTML = () => {
    const markerUrl = `file://${markerDir}/${portrait.id}`;
    const videoUrl = portrait.active_video?.url || '';

    return `
      <!DOCTYPE html>
      <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <script src="https://cdn.jsdelivr.net/npm/ar.js@3.4.5/aframe/build/aframe-ar-nft.js"></script>
          <style>
            body {
              margin: 0;
              overflow: hidden;
            }
            .loading {
              position: fixed;
              top: 50%;
              left: 50%;
              transform: translate(-50%, -50%);
              color: white;
              font-size: 20px;
              text-align: center;
            }
          </style>
        </head>
        <body>
          <div class="loading">
            <p>Наведите камеру на изображение</p>
          </div>

          <a-scene
            vr-mode-ui="enabled: false"
            renderer="logarithmicDepthBuffer: true; precision: medium;"
            embedded
            arjs="trackingMethod: best; sourceType: webcam; debugUIEnabled: false;"
          >
            <a-assets>
              <video 
                id="ar-video" 
                src="${videoUrl}" 
                preload="auto" 
                loop="true"
                crossorigin="anonymous"
                playsinline
                webkit-playsinline
              ></video>
            </a-assets>

            <a-nft
              type="nft"
              url="${markerUrl}"
              smooth="true"
              smoothCount="10"
              smoothTolerance="0.01"
              smoothThreshold="5"
            >
              <a-video
                src="#ar-video"
                position="0 0 0"
                width="1"
                height="1"
                rotation="-90 0 0"
              ></a-video>
            </a-nft>

            <a-entity camera></a-entity>
          </a-scene>

          <script>
            const video = document.getElementById('ar-video');
            
            // Обработчики событий AR.js
            const scene = document.querySelector('a-scene');
            const nft = document.querySelector('a-nft');
            
            nft.addEventListener('markerFound', () => {
              console.log('Marker found!');
              video.play();
              document.querySelector('.loading').style.display = 'none';
            });
            
            nft.addEventListener('markerLost', () => {
              console.log('Marker lost!');
              video.pause();
              document.querySelector('.loading').style.display = 'block';
            });
          </script>
        </body>
      </html>
    `;
  };

  return (
    <View style={styles.container}>
      <WebView
        ref={webViewRef}
        source={{ html: generateARHTML() }}
        style={styles.webview}
        mediaPlaybackRequiresUserAction={false}
        allowsInlineMediaPlayback={true}
        javaScriptEnabled={true}
        domStorageEnabled={true}
        allowsProtectedMedia={true}
        onError={(error) => {
          console.error('WebView error:', error);
          Alert.alert('Error', 'Failed to load AR viewer');
        }}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: 'black',
  },
  webview: {
    flex: 1,
  },
});

export default ARViewer;
```

---

## Дополнительные полезные функции

### Получение списка компаний

```javascript
async function getCompanies() {
  const response = await fetchWithAuth(
    `${API_BASE_URL}/api/mobile/companies`
  );
  return await response.json();
}

// Использование
const companies = await getCompanies();
companies.forEach(company => {
  console.log(`${company.name}: ${company.portraits_count} portraits`);
});
```

### Пагинация с бесконечным скроллом

```javascript
class PortraitsManager {
  constructor() {
    this.portraits = [];
    this.currentPage = 1;
    this.pageSize = 20;
    this.hasMore = true;
    this.loading = false;
  }

  async loadInitial(companyId = null) {
    this.portraits = [];
    this.currentPage = 1;
    this.hasMore = true;
    return await this.loadMore(companyId);
  }

  async loadMore(companyId = null) {
    if (this.loading || !this.hasMore) return [];

    this.loading = true;

    try {
      const query = new URLSearchParams({
        page: this.currentPage,
        page_size: this.pageSize,
      });

      if (companyId) {
        query.append('company_id', companyId);
      }

      const response = await fetchWithAuth(
        `${API_BASE_URL}/api/mobile/portraits?${query}`
      );

      const data = await response.json();
      
      this.portraits = [...this.portraits, ...data.portraits];
      this.currentPage++;
      this.hasMore = this.portraits.length < data.total;

      return data.portraits;
    } finally {
      this.loading = false;
    }
  }

  getAll() {
    return this.portraits;
  }

  findById(id) {
    return this.portraits.find(p => p.id === id);
  }
}

// Использование
const manager = new PortraitsManager();
await manager.loadInitial('company-123');
// ... при скролле вниз
await manager.loadMore('company-123');
```

---

Эта документация предоставляет готовые к использованию примеры кода для быстрой интеграции Vertex AR в ваше React Native приложение.
