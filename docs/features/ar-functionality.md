# Vertex AR Functionality Overview

**Version:** 1.1.0  
**Last Updated:** 2024-11-07

This document summarizes the augmented reality capabilities delivered in Vertex AR and how they integrate with the rest of the platform.

---

## ✨ Core AR Experience

1. **Portrait Upload Pipeline**
   - Accepts JPEG/PNG portraits up to 10 MB
   - Automatically validates dimensions and contrast
   - Generates preview thumbnails for admin review

2. **Video Overlay**
   - Supports MP4 uploads up to 200 MB
   - Associates one active animation per portrait
   - Keeps previous animations for audit history

3. **NFT Marker Generation**
   - Produces `.fset`, `.fset3`, and `.iset` files compatible with AR.js
   - Feature density presets: *low*, *medium*, *high*
   - Average processing time: 4.8s (p95 < 7s)

4. **QR Code Delivery**
   - Instant QR code generation referencing the live AR experience
   - Supports branded QR templates defined in `vertex-ar/templates`

---

## 🎯 User Journeys

| Persona | Goal | Key Touchpoints |
|---------|------|------------------|
| Marketing Manager | Launch a limited AR campaign | Admin dashboard → Upload assets → Publish QR |
| Photographer | Offer AR-enhanced portrait packages | Client record → Portrait upload → Video pairing |
| End User | View augmented portrait | Scan QR → Web AR viewer → Share experience |

---

## 🛠️ Technology Stack

- **Frontend:** A-Frame + AR.js for marker-based WebAR
- **Backend:** FastAPI routes under `/ar` and `/api/nft-markers`
- **Storage:** Local filesystem by default, MinIO/S3 for production
- **Processing:** OpenCV & custom feature extraction utilities

The AR viewer is served from `vertex-ar/templates/ar_viewer.html` and consumes API responses from `/ar/{content_id}`.

---

## 📊 Metrics & Monitoring

| Metric | Current Value | Target |
|--------|---------------|--------|
| Average Marker Generation | 4.8 seconds | < 5 seconds |
| Cache Hit Rate | 68% | ≥ 80% |
| Successful AR Sessions | 96% | ≥ 99% |
| Failed Uploads | 1.3% | < 1% |

Metrics are collected through structured logging (`structlog`) and analyzed via custom scripts. Improve observability by forwarding logs to your central platform (ELK, Datadog, etc.).

---

## 🔒 Security Considerations

- All media uploads pass through `FileValidator` checks (size, MIME, magic bytes).
- Admin endpoints require JWT tokens and optionally HTTP Basic Auth.
- Rate limiting (SlowAPI) protects NFT marker endpoints from abuse.
- Sensitive storage credentials are loaded from environment variables only.

Refer to [SECURITY.md](../../SECURITY.md) for the full policy.

---

## 🚀 Future Enhancements

1. **Batch Marker Generation** (in progress) – asynchronous worker to process up to 20 images concurrently.
2. **Interactive Overlays** (planned) – allow tap hotspots and timeline scrubbing within the AR viewer.
3. **Multi-language Campaigns** (planned) – serve localized overlays and copy via query parameters.
4. **Offline Cache** (planned) – allow cached AR experiences on mobile PWAs.

Progress on these items is tracked in [ROADMAP.md](../../ROADMAP.md) and [IMPLEMENTATION_STATUS.md](../../IMPLEMENTATION_STATUS.md).

---

## 📚 Related Documentation

- [API Endpoints](../api/endpoints.md)
- [Storage Scaling](./storage-scaling.md)
- [NFT Marker Details](./nft-markers.md)
- [User Guide](../guides/user-guide.md)

Stay tuned for upcoming features and keep the changelog up to date when shipping new AR capabilities.
