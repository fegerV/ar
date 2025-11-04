# NFT Marker - Quick Start Guide

**Version:** 1.1.0  
**Last Updated:** 2024-01-15

---

## 🚀 Quick Start

This guide will help you get started with the enhanced NFT Marker generation features in under 5 minutes.

---

## Prerequisites

- ✅ Vertex AR running (see [README.md](./README.md) for setup)
- ✅ Admin access (JWT token)
- ✅ Images ready for marker generation

---

## 1. Basic Marker Generation

### Single Image

```python
import requests

# Login to get token
response = requests.post(
    "http://localhost:8000/auth/login",
    json={"username": "admin", "password": "your_password"}
)
token = response.json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}

# Analyze image first (optional but recommended)
analysis = requests.get(
    "http://localhost:8000/api/nft-markers/analyze",
    params={"image_path": "/path/to/image.jpg"},
    headers=headers
).json()

print(f"Image quality: {analysis['quality']}")
print(f"Recommendation: {analysis['recommendation']}")
```

---

## 2. Batch Generation (NEW!)

Generate multiple markers at once with 3x speedup:

```python
import requests

headers = {"Authorization": f"Bearer {token}"}

batch_request = {
    "images": [
        {"image_path": "/path/to/image1.jpg", "marker_name": "marker1"},
        {"image_path": "/path/to/image2.jpg", "marker_name": "marker2"},
        {"image_path": "/path/to/image3.jpg", "marker_name": "marker3"},
    ],
    "max_workers": 4,
    "config": {
        "feature_density": "high",
        "levels": 4
    }
}

response = requests.post(
    "http://localhost:8000/api/nft-markers/batch-generate",
    json=batch_request,
    headers=headers
)

result = response.json()
print(f"Generated {result['successful']} markers in {result['total_time']:.2f}s")
```

**Performance Tip:** Use 4-6 workers for optimal performance.

---

## 3. Feature Preview

Visualize detected features before full generation:

```python
import requests

response = requests.post(
    "http://localhost:8000/api/nft-markers/preview",
    params={"image_path": "/path/to/image.jpg"},
    headers=headers
)

preview = response.json()
print(f"Preview saved to: {preview['preview_path']}")
print(f"Feature count: {preview['feature_count']}")
print(f"Quality: {preview['analysis']['quality']}")
```

**Color Legend:**
- 🟢 Green = Strong features (best tracking)
- 🟡 Yellow = Medium features (good tracking)
- 🔴 Red = Weak features (may need improvement)

---

## 4. Configuration Presets

Save frequently used configurations:

### Save a Preset

```python
preset = {
    "preset_name": "high_quality",
    "config": {
        "min_dpi": 150,
        "max_dpi": 300,
        "levels": 4,
        "feature_density": "high",
        "auto_enhance_contrast": true,
        "contrast_factor": 1.8
    }
}

response = requests.post(
    "http://localhost:8000/api/nft-markers/config-presets",
    json=preset,
    headers=headers
)
```

### Use a Preset

```python
# Get preset
response = requests.get(
    "http://localhost:8000/api/nft-markers/config-presets/high_quality",
    headers=headers
)
config = response.json()["config"]

# Use in batch generation
batch_request = {
    "images": [...],
    "config": config  # Use saved preset
}
```

---

## 5. Performance Monitoring

### Check Metrics

```python
response = requests.get(
    "http://localhost:8000/api/nft-markers/metrics",
    headers=headers
)

metrics = response.json()
print(f"Total generated: {metrics['total_generated']}")
print(f"Avg time per marker: {metrics['avg_time_per_marker']:.2f}s")
print(f"Cache hit rate: {metrics['cache_hit_rate']:.1%}")
```

### Get Analytics

```python
response = requests.get(
    "http://localhost:8000/api/nft-markers/analytics",
    headers=headers
)

analytics = response.json()
print(f"Total markers: {analytics['total_markers']}")
print(f"Storage used: {analytics['total_storage_used'] / 1024 / 1024:.2f} MB")
```

---

## 6. Maintenance

### Cleanup Unused Markers

```python
# Dry run first (recommended)
response = requests.post(
    "http://localhost:8000/api/nft-markers/cleanup",
    json={"dry_run": true},
    headers=headers
)

result = response.json()
print(f"Would delete {result['deleted_count']} markers")
print(f"Would free {result['freed_bytes'] / 1024 / 1024:.2f} MB")

# If happy with dry run, run for real
response = requests.post(
    "http://localhost:8000/api/nft-markers/cleanup",
    json={"dry_run": false},
    headers=headers
)
```

### Clear Cache

```python
# Clear expired cache entries only
response = requests.post(
    "http://localhost:8000/api/nft-markers/clear-cache",
    params={"clear_all": false},
    headers=headers
)

print(f"Cleared {response.json()['cleared']} cache entries")
```

---

## 7. Advanced: Contrast Enhancement

For images with poor contrast:

```python
# Enhance contrast
response = requests.post(
    "http://localhost:8000/api/nft-markers/enhance-contrast",
    params={
        "image_path": "/path/to/low_contrast_image.jpg",
        "factor": 1.8  # 1.0 = no change, 2.0 = strong enhancement
    },
    headers=headers
)

enhanced = response.json()
print(f"Enhanced image saved to: {enhanced['enhanced_path']}")

# Now use enhanced image for marker generation
```

---

## Common Workflows

### Workflow 1: Quick Single Marker

```python
# 1. Analyze
analysis = analyze_image("/path/to/image.jpg")

# 2. Generate if quality is good
if analysis['quality'] in ['good', 'excellent']:
    marker = generate_marker("/path/to/image.jpg", "my_marker")
else:
    # 3. Enhance first if quality is poor
    enhanced = enhance_contrast("/path/to/image.jpg", factor=1.8)
    marker = generate_marker(enhanced['enhanced_path'], "my_marker")
```

### Workflow 2: Batch Processing with Preview

```python
images = [
    {"path": "/path/to/img1.jpg", "name": "marker1"},
    {"path": "/path/to/img2.jpg", "name": "marker2"},
    # ... more images
]

# 1. Preview all images first
for img in images:
    preview = generate_preview(img['path'])
    print(f"{img['name']}: {preview['feature_count']} features")

# 2. Batch generate all at once
batch_generate(images, max_workers=6)

# 3. Check metrics
metrics = get_metrics()
print(f"Avg time: {metrics['avg_time_per_marker']:.2f}s")
```

### Workflow 3: Automated Maintenance

```python
# Run weekly maintenance
def weekly_maintenance():
    # 1. Clear expired cache
    clear_cache(clear_all=False)
    
    # 2. Cleanup unused markers
    cleanup = cleanup_markers(dry_run=False)
    print(f"Freed {cleanup['freed_bytes'] / 1024 / 1024:.2f} MB")
    
    # 3. Check analytics
    analytics = get_analytics()
    print(f"Total markers: {analytics['total_markers']}")
```

---

## Configuration Reference

### Feature Density

- `low`: Faster generation, fewer features, may struggle in complex scenes
- `medium`: Balanced performance and quality (recommended)
- `high`: More features, better tracking, slower generation

### DPI Settings

- **72-150**: Fast generation, good for simple images
- **150-200**: Balanced quality (recommended)
- **200-300**: High quality, best tracking, slower

### Levels

- **2-3**: Fast generation, good for static viewing
- **3-4**: Balanced (recommended)
- **4-5**: Multi-scale tracking, better at different distances

### Contrast Factor

- **1.0-1.5**: Subtle enhancement
- **1.5-2.0**: Moderate enhancement (recommended)
- **2.0-3.0**: Strong enhancement (may cause artifacts)

---

## Troubleshooting

### Problem: Low feature count

**Solution:**
1. Enhance contrast: `enhance_contrast(path, factor=1.8)`
2. Use higher feature density: `"feature_density": "high"`
3. Increase levels: `"levels": 4`

### Problem: Slow generation

**Solution:**
1. Use batch generation with multiple workers
2. Lower feature density: `"feature_density": "low"`
3. Reduce levels: `"levels": 3`
4. Enable caching for repeated analysis

### Problem: Poor tracking quality

**Solution:**
1. Check image quality: `analyze_image(path)`
2. Enhance contrast if needed
3. Use higher DPI: `"min_dpi": 150`
4. Increase feature density: `"feature_density": "high"`

---

## Best Practices

### ✅ DO

- Always analyze images before generation
- Use batch generation for multiple images
- Enable caching for repeated operations
- Save frequently used configs as presets
- Run cleanup periodically
- Monitor metrics regularly

### ❌ DON'T

- Don't skip dry-run before cleanup
- Don't use too many workers (>8)
- Don't ignore quality warnings
- Don't disable caching unnecessarily
- Don't forget to check previews

---

## Performance Tips

1. **Batch Size**: Optimal batch size is 5-20 images
2. **Workers**: Use 4-6 workers for most systems
3. **Caching**: Enabled by default, provides 80% hit rate
4. **Image Size**: 1024x768 to 2048x1536 is optimal
5. **Format**: WebP provides smaller files with same quality

---

## Next Steps

- 📖 Read full API documentation: [NFT_MARKER_API_DOCUMENTATION.md](./NFT_MARKER_API_DOCUMENTATION.md)
- 🔧 Check feature improvements: [NFT_MARKER_IMPROVEMENTS.md](./NFT_MARKER_IMPROVEMENTS.md)
- 🚀 Explore implementation details: [IMPLEMENTATION_SUMMARY_NFT.md](./IMPLEMENTATION_SUMMARY_NFT.md)

---

## Support

For issues or questions:
- Check [NFT_MARKER_API_DOCUMENTATION.md](./NFT_MARKER_API_DOCUMENTATION.md) for detailed API reference
- Review [TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md) for common issues
- Contact project maintainers

---

**Happy marker generating! 🎯**
