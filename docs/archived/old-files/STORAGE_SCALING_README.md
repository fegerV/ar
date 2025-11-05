# Storage Scaling for Vertex AR

## 🎯 Overview

Vertex AR now supports flexible storage backends to scale as your AR content grows:

- 📁 **Local Storage** - Files on disk (default)
- ☁️ **MinIO** - S3-compatible object storage (local or remote)
- 🌐 **Cloud Storage** - AWS S3, DigitalOcean Spaces, Backblaze B2, etc.

## 🚀 Quick Setup

### Option 1: Local Storage (Default)

No configuration needed! Files are stored in `vertex-ar/storage/`

```env
STORAGE_TYPE=local
```

### Option 2: Remote MinIO

1. Set up MinIO on a separate server (or use cloud storage)
2. Update `.env`:

```env
STORAGE_TYPE=minio
MINIO_ENDPOINT=minio.example.com:9000
MINIO_ACCESS_KEY=your-key
MINIO_SECRET_KEY=your-secret
MINIO_BUCKET=vertex-ar
MINIO_SECURE=true
```

3. Test connection:

```bash
python check_storage.py
```

4. Restart application:

```bash
systemctl restart vertex-ar
# or
docker-compose restart
```

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [SCALING_QUICK_START_RU.md](./SCALING_QUICK_START_RU.md) | Quick start guide (Russian) |
| [SCALING_STORAGE_GUIDE.md](./SCALING_STORAGE_GUIDE.md) | Complete scaling guide |
| [DOCKER_COMPOSE_EXAMPLES.md](./DOCKER_COMPOSE_EXAMPLES.md) | Docker deployment examples |

## 🔧 Configuration

### Environment Variables

```env
# Storage type: "local" or "minio"
STORAGE_TYPE=local

# Local storage path (for local type)
STORAGE_PATH=./storage

# MinIO settings (for minio type)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=vertex-ar
MINIO_SECURE=false
MINIO_PUBLIC_URL=  # Optional CDN URL
```

### Cloud Storage Examples

#### DigitalOcean Spaces
```env
STORAGE_TYPE=minio
MINIO_ENDPOINT=nyc3.digitaloceanspaces.com
MINIO_ACCESS_KEY=your-key
MINIO_SECRET_KEY=your-secret
MINIO_BUCKET=vertex-ar
MINIO_SECURE=true
MINIO_PUBLIC_URL=https://vertex-ar.nyc3.cdn.digitaloceanspaces.com
```

#### Amazon S3
```env
STORAGE_TYPE=minio
MINIO_ENDPOINT=s3.amazonaws.com
MINIO_ACCESS_KEY=your-aws-key
MINIO_SECRET_KEY=your-aws-secret
MINIO_BUCKET=vertex-ar
MINIO_SECURE=true
```

## 🧪 Testing

Check your storage configuration:

```bash
python check_storage.py
```

Output:
```
============================================================
Vertex AR - Storage Connection Check
============================================================

📦 Storage Type: minio
☁️  MinIO Storage Configuration:
   Endpoint: minio.example.com:9000
   Bucket: vertex-ar
   Secure: True

🔍 Checking MinIO connectivity...
✅ MinIO endpoint is reachable
✅ MinIO storage initialized successfully
✅ Test file upload successful
✅ Test file download successful
✅ Test file cleanup successful

============================================================
🎉 Storage check completed successfully!
============================================================
```

## 🔄 Migration

### From Local to Remote

1. **Install MinIO Client:**
```bash
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc && sudo mv mc /usr/local/bin/
```

2. **Configure connections:**
```bash
mc alias set local file://./vertex-ar/storage/vertex-art-bucket
mc alias set remote http://minio.example.com:9000 access-key secret-key
```

3. **Copy files:**
```bash
mc cp --recursive local/ remote/vertex-ar/
```

4. **Update configuration:**
```env
STORAGE_TYPE=minio
```

5. **Restart application**

## 💡 When to Scale

### Use Local Storage when:
- ✅ Development/testing environment
- ✅ Small projects (< 10GB)
- ✅ Single server deployment
- ✅ Limited budget

### Use Remote MinIO when:
- ✅ Production environment
- ✅ Growing storage needs (> 10GB)
- ✅ Multiple servers/containers
- ✅ Need for backups/replication
- ✅ Want CDN integration
- ✅ Better disaster recovery

## 📊 Scaling Benefits

| Aspect | Local Storage | Remote MinIO |
|--------|--------------|--------------|
| **Capacity** | Server disk size | Virtually unlimited |
| **Cost** | $0.10-0.20/GB | $0.005-0.02/GB |
| **Reliability** | Single point of failure | Replicated |
| **Performance** | Fast local access | Optimized for media |
| **Scaling** | Manual disk resize | Automatic |
| **Backup** | Manual setup needed | Built-in features |

## 🆘 Troubleshooting

### "Connection refused" error
```bash
# Check MinIO is running
curl http://your-minio:9000/minio/health/live

# Check firewall
sudo ufw allow 9000/tcp
```

### "Access denied" error
```bash
# Verify credentials
mc alias set test http://your-minio:9000 key secret
mc ls test
```

### Temporary rollback to local storage
```env
STORAGE_TYPE=local
```
Restart the application - your remote files remain safe.

## 🔐 Security Tips

1. **Use HTTPS in production:**
   ```env
   MINIO_SECURE=true
   ```

2. **Generate strong passwords:**
   ```bash
   openssl rand -base64 32
   ```

3. **Restrict network access:**
   ```bash
   sudo ufw allow from APP_SERVER_IP to any port 9000
   ```

4. **Use separate keys per environment**

## 📈 Cost Examples

For 10,000 AR experiences (100GB storage):

| Provider | Monthly Cost |
|----------|-------------|
| Server SSD | $12-25 |
| Backblaze B2 | $0.50 |
| Yandex Object Storage | $2.00 |
| Amazon S3 | $2.30 |
| DigitalOcean Spaces | $5.00 |

## 🎓 Learn More

- 📖 [Complete Scaling Guide](./SCALING_STORAGE_GUIDE.md)
- ⚡ [Quick Start (Russian)](./SCALING_QUICK_START_RU.md)
- 🐳 [Docker Examples](./DOCKER_COMPOSE_EXAMPLES.md)
- 🔧 [Check Storage Script](./check_storage.py)

## 💬 Support

Questions? Issues?
- 📧 Create an issue on GitHub
- 💬 Check documentation
- 🧪 Run `python check_storage.py` for diagnostics

**Happy Scaling!** 🚀
