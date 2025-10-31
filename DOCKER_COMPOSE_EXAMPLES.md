# Docker Compose Examples for Vertex AR

This directory contains different Docker Compose configurations for various deployment scenarios.

## Available Configurations

### 1. `docker-compose.yml` - Standard Configuration

Default configuration with local MinIO container.

**Use case:** Development and testing

**Services:**
- Vertex AR application
- Local MinIO instance (in container)

**Start:**
```bash
docker-compose up -d
```

**Access:**
- Application: http://localhost:8000
- MinIO Console: http://localhost:9001

---

### 2. `docker-compose.minio-remote.yml` - Remote MinIO

Configuration for connecting to an external MinIO server or S3-compatible storage.

**Use case:** Production with remote/cloud storage

**Services:**
- Vertex AR application only (no MinIO container)

**Configuration:**

1. Create `.env` file:
```bash
# Remote MinIO/S3 credentials
MINIO_ENDPOINT=minio.example.com:9000
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_BUCKET=vertex-ar-production
MINIO_SECURE=true
MINIO_PUBLIC_URL=https://cdn.example.com

# Application settings
SECRET_KEY=your-secure-secret-key
BASE_URL=https://yourdomain.com
```

2. Start:
```bash
docker-compose -f docker-compose.minio-remote.yml up -d
```

**Supported Remote Storage Providers:**

#### Amazon S3
```env
MINIO_ENDPOINT=s3.amazonaws.com
MINIO_ACCESS_KEY=YOUR_AWS_ACCESS_KEY_ID
MINIO_SECRET_KEY=YOUR_AWS_SECRET_ACCESS_KEY
MINIO_BUCKET=vertex-ar-bucket
MINIO_SECURE=true
```

#### DigitalOcean Spaces
```env
MINIO_ENDPOINT=nyc3.digitaloceanspaces.com
MINIO_ACCESS_KEY=YOUR_DO_SPACES_KEY
MINIO_SECRET_KEY=YOUR_DO_SPACES_SECRET
MINIO_BUCKET=vertex-ar
MINIO_SECURE=true
MINIO_PUBLIC_URL=https://vertex-ar.nyc3.cdn.digitaloceanspaces.com
```

#### Backblaze B2
```env
MINIO_ENDPOINT=s3.us-west-000.backblazeb2.com
MINIO_ACCESS_KEY=YOUR_B2_KEY_ID
MINIO_SECRET_KEY=YOUR_B2_APPLICATION_KEY
MINIO_BUCKET=vertex-ar
MINIO_SECURE=true
```

#### Yandex Object Storage
```env
MINIO_ENDPOINT=storage.yandexcloud.net
MINIO_ACCESS_KEY=YOUR_YANDEX_KEY_ID
MINIO_SECRET_KEY=YOUR_YANDEX_SECRET
MINIO_BUCKET=vertex-ar
MINIO_SECURE=true
```

#### Self-hosted MinIO
```env
MINIO_ENDPOINT=minio.yourdomain.com:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=your-secure-password
MINIO_BUCKET=vertex-ar
MINIO_SECURE=true
```

---

## Switching Between Configurations

### From Local to Remote MinIO

1. **Stop current services:**
```bash
docker-compose down
```

2. **Create `.env` file with remote credentials** (see examples above)

3. **Start with remote configuration:**
```bash
docker-compose -f docker-compose.minio-remote.yml up -d
```

4. **Migrate data** (if needed):
```bash
# Install MinIO client
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc

# Configure aliases
mc alias set local http://localhost:9000 minioadmin minioadmin
mc alias set remote http://your-remote-minio:9000 access-key secret-key

# Copy data
mc cp --recursive local/vertex-art-bucket/ remote/vertex-art-bucket/
```

### From Remote to Local MinIO

1. **Stop current services:**
```bash
docker-compose -f docker-compose.minio-remote.yml down
```

2. **Start with local configuration:**
```bash
docker-compose up -d
```

3. **Migrate data back** (if needed):
```bash
mc cp --recursive remote/vertex-art-bucket/ local/vertex-art-bucket/
```

---

## Testing Storage Connection

Before starting the full application, test your storage configuration:

```bash
# Set environment variables
export STORAGE_TYPE=minio
export MINIO_ENDPOINT=your-minio-server:9000
export MINIO_ACCESS_KEY=your-key
export MINIO_SECRET_KEY=your-secret

# Run connection test
python check_storage.py
```

---

## Monitoring

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f vertex-ar

# Remote MinIO logs
docker-compose -f docker-compose.minio-remote.yml logs -f vertex-ar
```

### Check storage usage

**Local MinIO:**
```bash
docker exec minio mc du /data/vertex-art-bucket
```

**Remote MinIO:**
```bash
mc du remote/vertex-ar-bucket
```

---

## Troubleshooting

### Connection Refused Error

**Symptoms:**
```
Failed to establish a new connection: [Errno 111] Connection refused
```

**Solutions:**

1. **Check MinIO is running:**
```bash
# For local MinIO
docker-compose ps

# For remote MinIO
curl http://your-minio-server:9000/minio/health/live
```

2. **Check firewall:**
```bash
# On MinIO server
sudo ufw allow 9000/tcp
```

3. **Check endpoint in .env:**
```env
# Should NOT include http://
MINIO_ENDPOINT=minio.example.com:9000
```

### Access Denied Error

**Solutions:**

1. **Verify credentials:**
```bash
mc alias set test http://your-minio:9000 your-key your-secret
mc ls test
```

2. **Check bucket permissions in MinIO Console**

### Slow Upload/Download

**Solutions:**

1. **Enable CDN** (set MINIO_PUBLIC_URL)
2. **Use closer region** for cloud storage
3. **Check network bandwidth**

---

## Production Best Practices

### Security

1. **Use HTTPS (TLS):**
```env
MINIO_SECURE=true
```

2. **Strong credentials:**
```bash
# Generate secure password
openssl rand -base64 32
```

3. **Restrict network access:**
```bash
# On MinIO server - allow only app server IP
sudo ufw allow from YOUR_APP_IP to any port 9000
```

4. **Use separate credentials per environment:**
- Development: dev-access-key / dev-secret
- Staging: staging-access-key / staging-secret
- Production: prod-access-key / prod-secret

### Reliability

1. **Enable versioning** in MinIO
2. **Set up regular backups**
3. **Use replication** for critical data
4. **Monitor storage metrics**

### Performance

1. **Use CDN** for public assets
2. **Enable caching** on reverse proxy
3. **Choose geographically close storage**
4. **Use appropriate storage class** (hot/cold)

---

## Cost Optimization

### Storage Costs Comparison (per 100GB/month)

| Provider | Cost | Notes |
|----------|------|-------|
| Backblaze B2 | $0.50 | Cheapest, good for archives |
| Yandex Object Storage | $2.00 | Good for Russia |
| Amazon S3 | $2.30 | Most features |
| DigitalOcean Spaces | $5.00 | Fixed price for 250GB |
| Self-hosted MinIO | $10-20 | Full control, server costs |

### Optimization Tips

1. **Compress videos** before upload
2. **Use image optimization** (WebP format)
3. **Clean up unused files** regularly
4. **Use lifecycle policies** to archive old content

---

## Support

For more information:
- 📖 [Scaling Storage Guide](./SCALING_STORAGE_GUIDE.md)
- ⚡ [Quick Start Guide](./SCALING_QUICK_START_RU.md)
- 🔧 [Storage Check Script](./check_storage.py)

For issues, create a GitHub issue with:
- Your docker-compose file (sanitized)
- .env configuration (sanitized)
- Error logs
- Output of `check_storage.py`
