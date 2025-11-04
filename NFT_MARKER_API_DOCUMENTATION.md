# NFT Marker API Documentation

**Version:** 1.1.0  
**Last Updated:** 2024-01-15

## Overview

This document provides comprehensive documentation for the enhanced NFT Marker generation API endpoints. These endpoints provide advanced features for batch generation, caching, analytics, and configuration management.

---

## Table of Contents

1. [Authentication](#authentication)
2. [Batch Generation](#batch-generation)
3. [Image Analysis](#image-analysis)
4. [Feature Preview](#feature-preview)
5. [Performance Metrics](#performance-metrics)
6. [Cleanup Operations](#cleanup-operations)
7. [Configuration Presets](#configuration-presets)
8. [Analytics](#analytics)
9. [Utility Operations](#utility-operations)

---

## Authentication

All NFT Marker API endpoints require admin authentication. Include the JWT token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

---

## Batch Generation

### POST `/api/nft-markers/batch-generate`

Generate NFT markers for multiple images in parallel.

**Request Body:**
```json
{
  "images": [
    {
      "image_path": "/path/to/image1.jpg",
      "marker_name": "marker1"
    },
    {
      "image_path": "/path/to/image2.jpg",
      "marker_name": "marker2"
    }
  ],
  "config": {
    "min_dpi": 72,
    "max_dpi": 300,
    "levels": 3,
    "feature_density": "medium",
    "auto_enhance_contrast": false,
    "contrast_factor": 1.5
  },
  "max_workers": 4
}
```

**Response:**
```json
{
  "results": {
    "/path/to/image1.jpg": {
      "fset_path": "storage/nft_markers/marker1/marker1.fset",
      "fset3_path": "storage/nft_markers/marker1/marker1.fset3",
      "iset_path": "storage/nft_markers/marker1/marker1.iset",
      "width": 1024,
      "height": 768
    },
    "/path/to/image2.jpg": {
      "error": "Image validation failed: Image too small"
    }
  },
  "successful": 1,
  "failed": 1,
  "total_time": 5.23
}
```

**Parameters:**
- `images`: Array of objects containing `image_path` and `marker_name`
- `config` (optional): NFT marker configuration
- `max_workers`: Number of parallel workers (1-8, default: 4)

**Performance:**
- Processes images in parallel using ThreadPoolExecutor
- Typical speedup: 3x for 5+ images
- Optimal max_workers: 4-6 for most systems

---

## Image Analysis

### GET `/api/nft-markers/analyze`

Analyze an image for NFT marker suitability with intelligent caching.

**Query Parameters:**
- `image_path`: Path to the image file (required)
- `use_cache`: Use cached results if available (default: true)

**Example:**
```
GET /api/nft-markers/analyze?image_path=/path/to/image.jpg&use_cache=true
```

**Response:**
```json
{
  "valid": true,
  "message": "Image valid",
  "width": 1920,
  "height": 1080,
  "brightness": 127.45,
  "contrast": 75.32,
  "quality": "good",
  "recommendation": "Image should track well in most conditions.",
  "cached": false
}
```

**Quality Levels:**
- `excellent`: Contrast > 90 - Very high tracking quality
- `good`: Contrast 60-90 - Good tracking in most conditions
- `fair`: Contrast 30-60 - May have issues in poor lighting
- `poor`: Contrast < 30 - Low tracking quality, improvement needed

**Caching:**
- Results cached for 7 days by default
- Cache key based on file path, modification time, and size
- Typical cache hit rate: 80%
- Cache miss penalty: ~10ms

---

## Feature Preview

### POST `/api/nft-markers/preview`

Generate a preview image showing detected feature points for tracking.

**Query Parameters:**
- `image_path`: Path to the image file (required)

**Example:**
```
POST /api/nft-markers/preview?image_path=/path/to/image.jpg
```

**Response:**
```json
{
  "preview_path": "storage/previews/preview_image.jpg",
  "analysis": {
    "valid": true,
    "width": 1920,
    "height": 1080,
    "quality": "good",
    "contrast": 75.32,
    "recommendation": "Image should track well in most conditions."
  },
  "feature_count": 342
}
```

**Feature Visualization:**
- 🟢 Green points: Strong features (score > 1000)
- 🟡 Yellow points: Medium features (score 500-1000)
- 🔴 Red points: Weak features (score < 500)

**Use Cases:**
- Preview tracking quality before generation
- Identify areas that need improvement
- Optimize image cropping/composition

---

## Performance Metrics

### GET `/api/nft-markers/metrics`

Get NFT marker generation performance metrics.

**Response:**
```json
{
  "total_generated": 156,
  "total_time": 324.56,
  "avg_time_per_marker": 2.08,
  "cache_hits": 89,
  "cache_misses": 23,
  "cache_hit_rate": 0.79
}
```

**Metrics Explanation:**
- `total_generated`: Total number of markers generated
- `total_time`: Total time spent generating markers (seconds)
- `avg_time_per_marker`: Average generation time per marker
- `cache_hits`: Number of cache hits for analysis
- `cache_misses`: Number of cache misses
- `cache_hit_rate`: Percentage of requests served from cache

---

## Cleanup Operations

### POST `/api/nft-markers/cleanup`

Clean up unused NFT markers to free storage space.

**Request Body:**
```json
{
  "dry_run": true
}
```

**Response:**
```json
{
  "total_markers": 50,
  "used_markers": 35,
  "unused_markers": 15,
  "deleted_count": 15,
  "freed_bytes": 15728640,
  "dry_run": true,
  "errors": []
}
```

**Parameters:**
- `dry_run`: If true, simulate cleanup without deleting files

**Safety:**
- Checks database for markers in use
- Only deletes markers not referenced in AR content
- Provides dry-run mode for preview
- Returns list of errors if any occur

---

## Configuration Presets

### GET `/api/nft-markers/config-presets`

List all available NFT marker configuration presets.

**Response:**
```json
[
  {
    "name": "high_quality",
    "created_at": "2024-01-15T10:30:00",
    "preset_path": "storage/nft_presets/high_quality.json"
  },
  {
    "name": "fast_generation",
    "created_at": "2024-01-15T11:00:00",
    "preset_path": "storage/nft_presets/fast_generation.json"
  }
]
```

---

### POST `/api/nft-markers/config-presets`

Save a new NFT marker configuration preset.

**Request Body:**
```json
{
  "preset_name": "my_custom_preset",
  "config": {
    "min_dpi": 150,
    "max_dpi": 300,
    "levels": 4,
    "feature_density": "high",
    "auto_enhance_contrast": true,
    "contrast_factor": 1.8
  }
}
```

**Response:**
```json
{
  "name": "my_custom_preset",
  "preset_path": "storage/nft_presets/my_custom_preset.json",
  "config": {
    "min_dpi": 150,
    "max_dpi": 300,
    "levels": 4,
    "feature_density": "high",
    "auto_enhance_contrast": true,
    "contrast_factor": 1.8
  }
}
```

---

### GET `/api/nft-markers/config-presets/{preset_name}`

Get a specific NFT marker configuration preset.

**Example:**
```
GET /api/nft-markers/config-presets/high_quality
```

**Response:**
```json
{
  "name": "high_quality",
  "config": {
    "min_dpi": 150,
    "max_dpi": 300,
    "levels": 4,
    "feature_density": "high",
    "auto_enhance_contrast": false,
    "contrast_factor": 1.5
  }
}
```

---

### DELETE `/api/nft-markers/config-presets/{preset_name}`

Delete an NFT marker configuration preset.

**Example:**
```
DELETE /api/nft-markers/config-presets/my_custom_preset
```

**Response:**
```json
{
  "message": "Preset 'my_custom_preset' deleted successfully"
}
```

---

## Analytics

### GET `/api/nft-markers/analytics`

Get NFT marker usage analytics and statistics.

**Response:**
```json
{
  "total_markers": 156,
  "quality_distribution": {},
  "avg_file_sizes": {
    "fset": 15234.5,
    "fset3": 8456.2,
    "iset": 342567.8
  },
  "total_storage_used": 52428800
}
```

**Metrics:**
- `total_markers`: Total number of generated markers
- `avg_file_sizes`: Average file sizes for each marker type (bytes)
- `total_storage_used`: Total storage used by all markers (bytes)

---

## Utility Operations

### POST `/api/nft-markers/enhance-contrast`

Enhance image contrast for better feature detection.

**Query Parameters:**
- `image_path`: Path to the image file (required)
- `factor`: Enhancement factor (default: 1.5)

**Example:**
```
POST /api/nft-markers/enhance-contrast?image_path=/path/to/image.jpg&factor=1.8
```

**Response:**
```json
{
  "original_path": "/path/to/image.jpg",
  "enhanced_path": "storage/temp/enhanced_image.jpg",
  "factor": "1.8"
}
```

**Factor Guidelines:**
- `1.0`: No change
- `1.5`: Moderate enhancement (default)
- `2.0`: Strong enhancement
- `>2.0`: Very strong enhancement (may cause artifacts)

---

### POST `/api/nft-markers/clear-cache`

Clear NFT analysis cache entries.

**Query Parameters:**
- `clear_all`: Clear all entries (default: false, clears expired only)

**Example:**
```
POST /api/nft-markers/clear-cache?clear_all=true
```

**Response:**
```json
{
  "message": "Cleared 15 cache entries",
  "cleared": 15,
  "clear_all": true
}
```

---

## Configuration Reference

### NFTMarkerConfig

Configuration object for NFT marker generation.

```json
{
  "min_dpi": 72,          // Minimum DPI (dots per inch)
  "max_dpi": 300,         // Maximum DPI
  "levels": 3,            // Number of pyramid levels (1-5)
  "feature_density": "medium",  // Feature density: "low", "medium", "high"
  "auto_enhance_contrast": false,  // Automatically enhance contrast
  "contrast_factor": 1.5  // Contrast enhancement factor (1.0-3.0)
}
```

**Parameter Guidelines:**

- **min_dpi/max_dpi**: 
  - Lower values: Faster generation, lower quality
  - Higher values: Slower generation, better tracking
  - Recommended: 72-300

- **levels**: 
  - More levels: Better tracking at different scales
  - Fewer levels: Faster generation
  - Recommended: 3-4

- **feature_density**:
  - `low`: Fast generation, fewer features
  - `medium`: Balanced (recommended)
  - `high`: More features, better tracking, slower

- **auto_enhance_contrast**:
  - Automatically improves low-contrast images
  - May alter original image appearance
  - Recommended for photos with poor lighting

- **contrast_factor**:
  - Only used if auto_enhance_contrast is true
  - Range: 1.0 (no change) to 3.0 (maximum)
  - Recommended: 1.5-2.0

---

## Error Handling

All endpoints return standard HTTP status codes:

- `200`: Success
- `400`: Bad Request (invalid parameters)
- `401`: Unauthorized (missing/invalid auth token)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found (resource doesn't exist)
- `500`: Internal Server Error

**Error Response Format:**
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Performance Considerations

### Batch Generation
- Optimal batch size: 5-20 images
- Max workers: 4-6 for most systems
- Expected speedup: 3x for 5+ images

### Caching
- Cache TTL: 7 days (configurable)
- Cache hit rate: ~80% typical
- Cache overhead: <10ms per request

### Image Processing
- Supported formats: JPEG, PNG, WebP
- Recommended size: 1024x768 to 2048x1536
- Max size: 4096x4096

---

## Best Practices

1. **Use batch generation** for multiple images to improve performance
2. **Enable caching** for repeated analysis operations
3. **Run cleanup periodically** to free storage space
4. **Use dry-run mode** before actual cleanup operations
5. **Save common configurations** as presets for reuse
6. **Monitor metrics** to optimize performance
7. **Generate feature previews** before full marker generation

---

## Examples

### Batch Generate Multiple Markers

```bash
curl -X POST "http://localhost:8000/api/nft-markers/batch-generate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "images": [
      {"image_path": "/storage/images/img1.jpg", "marker_name": "marker1"},
      {"image_path": "/storage/images/img2.jpg", "marker_name": "marker2"}
    ],
    "max_workers": 4
  }'
```

### Analyze Image with Caching

```bash
curl -X GET "http://localhost:8000/api/nft-markers/analyze?image_path=/storage/images/test.jpg&use_cache=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Save Configuration Preset

```bash
curl -X POST "http://localhost:8000/api/nft-markers/config-presets" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "preset_name": "high_quality",
    "config": {
      "min_dpi": 150,
      "feature_density": "high",
      "levels": 4
    }
  }'
```

### Run Cleanup (Dry Run)

```bash
curl -X POST "http://localhost:8000/api/nft-markers/cleanup" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'
```

---

## Support

For issues, questions, or feature requests related to NFT Marker generation, please refer to:
- Main documentation: `README.md`
- API documentation: `API_DOCUMENTATION.md`
- Feature improvements: `NFT_MARKER_IMPROVEMENTS.md`

---

**Last Updated:** 2024-01-15  
**API Version:** 1.1.0  
**Documentation Version:** 1.0.0
