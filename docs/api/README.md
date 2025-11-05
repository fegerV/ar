# Vertex AR API Overview

## Introduction

Vertex AR API is a RESTful API for creating and managing augmented reality (AR) content. The API allows uploading portrait images, creating AR markers, generating QR codes, and managing AR content.

## Key Features

- 🔐 User authentication with Bearer tokens
- 📤 Upload images and videos for AR content creation
- 🎯 Automatic NFT marker generation for AR
- 📊 View statistics and analytics
- 👥 Administrative panel for management
- 🔍 Support for various file formats
- 🎨 Animated AR portraits with Anime.js
- 📱 Mobile and desktop device support

## Base Information

### Base URL
```
Production: https://your-domain.com
Development: http://localhost:8000
```

### API Version
Current version: `1.0.0`

### Content Types
- `application/json` - Most requests
- `multipart/form-data` - File uploads
- `text/html` - HTML pages (AR viewer, admin panel)
- `image/png` - Images (QR codes, previews)
- `video/mp4` - Video content

### Headers
```
Content-Type: application/json
Authorization: Bearer <your_token>
```

## Authentication

Vertex AR uses Bearer Token authentication. To access protected endpoints:

1. Register via `/auth/register`
2. Get token via `/auth/login`
3. Use token in Authorization header for all protected requests

### Token Format
```
Authorization: Bearer <token>
```

### Access Levels
- **Public access** - No authentication required
- **Authenticated access** - Valid token required
- **Administrator access** - Admin token required (first registered user)

## API Endpoints

### Core Endpoints
- `GET /health` - Health check
- `POST /auth/register` - User registration
- `POST /auth/login` - User authentication
- `POST /auth/logout` - User logout

### AR Content
- `POST /ar/upload` - Upload AR content (image + video)
- `GET /ar/{content_id}` - Get AR content
- `GET /ar/list` - List all AR content
- `DELETE /ar/{content_id}` - Delete AR content

### NFT Markers (Enhanced)
- `POST /api/nft-markers/batch-generate` - Batch generation (3x faster)
- `GET /api/nft-markers/analyze` - Image analysis with caching
- `POST /api/nft-markers/preview` - Feature points preview
- `GET /api/nft-markers/metrics` - Performance metrics
- `GET /api/nft-markers/analytics` - Usage analytics

### Administration
- `GET /admin` - Admin panel
- `GET /admin/system-info` - System information
- `GET /admin/storage-info` - Storage usage

## Quick Examples

### Authentication
```bash
# Register user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"secure_password"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"secure_password"}'
```

### Upload AR Content
```bash
curl -X POST http://localhost:8000/ar/upload \
  -H "Authorization: Bearer <token>" \
  -F "image=@portrait.jpg" \
  -F "video=@animation.mp4"
```

## Performance

- **API Response Time:** <100ms average
- **NFT Generation:** <5s (p95)
- **Batch Processing:** 3x acceleration for 5+ images
- **Cache Hit Rate:** ~80% for analysis requests

## Rate Limiting

Rate limiting is implemented on all endpoints to prevent abuse:
- Default: 100 requests per minute per IP
- Authenticated users: 500 requests per minute
- Admin users: 1000 requests per minute

## Error Handling

All errors return JSON responses with appropriate HTTP status codes:
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Too Many Requests
- `500` - Internal Server Error

---

For detailed endpoint documentation, see [Endpoints Reference](endpoints.md).