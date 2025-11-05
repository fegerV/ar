# Vertex AR Deployment Guide

**Version:** 1.1.0  
**Last Updated:** 2024-11-07

This guide covers the recommended approaches for deploying Vertex AR to staging or production environments. It assumes you already reviewed the main [README](../../README.md) and prepared environment variables based on [.env.example](../../.env.example).

---

## 🚀 Deployment Strategies

### 1. Docker Compose (Recommended)

The quickest path to a reproducible deployment is the existing `docker-compose.yml` in the project root.

```bash
cp .env.example .env            # populate secrets before running
sudo docker compose up -d
sudo docker compose logs -f
```

**Checklist**
- [ ] Replace `SECRET_KEY`, `ADMIN_PASSWORD`, and storage credentials in `.env`
- [ ] Configure `CORS_ORIGINS` to only allow trusted domains
- [ ] Expose port 8000 (or change `ports` mapping) behind a reverse proxy
- [ ] Mount persistent volumes for `/app/storage` and `/app/app_data.db`
- [ ] Configure automated backups (see [scripts/backup.sh](../../scripts/backup.sh))

### 2. Bare-metal / Systemd

If Docker is not available you can run the FastAPI application with Uvicorn behind Nginx.

1. Create a Python virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r vertex-ar/requirements.txt
   ```
2. Populate `.env` in the project root (same keys as `.env.example`).
3. Start the API with Uvicorn or Gunicorn:
   ```bash
   uvicorn vertex-ar.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```
4. Configure Nginx using the provided [nginx.conf](../../nginx.conf) as a reference.
5. Create a systemd service to keep the process running and restart on failure.

### 3. Managed Cloud (Conceptual)

For AWS/GCP/Azure deployments you can reuse the Docker image in `Dockerfile.app` and:
- Use ECS or Cloud Run for container orchestration
- Attach managed Postgres or continue with SQLite + shared storage for staging
- Set up S3/MinIO compatible storage for content and markers
- Terminate TLS at the cloud load balancer

---

## 🔧 Environment Configuration

### Required Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Used to sign JWT tokens. Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `ADMIN_PASSWORD` | Admin credentials created on first launch |
| `DATABASE_URL` | Defaults to SQLite if omitted |
| `STORAGE_BACKEND` | `local`, `minio`, or `s3` |
| `MINIO_ENDPOINT` & friends | Required when using MinIO/S3 |
| `CORS_ORIGINS` | Comma-separated list of allowed origins |
| `ALLOWED_HOSTS` | Optional host allow list |

Additional settings (rate limiting, logging, analytics) are documented in [docs/development/architecture.md](../development/architecture.md).

### Secrets Management

- Do **not** commit `.env` files to source control. `.gitignore` already prevents this.
- Prefer using your infrastructure secrets manager (AWS Parameter Store, GCP Secret Manager, Hashicorp Vault).
- Rotate credentials quarterly and after every incident.

---

## ✅ Pre-deployment Checklist

1. `pytest` tests pass locally (unit + integration)  
2. `check_production_readiness.sh` returns no errors  
3. Content storage directories are mounted with the correct permissions  
4. SSL certificates are installed or automated via Let's Encrypt  
5. Backups scripts are scheduled (cron or systemd timer)  
6. Monitoring and alerting are configured (logs + metrics)  
7. Rollback plan documented (tarball backup or container rollback)

---

## 📊 Post-deployment Validation

Run these basic smoke tests after every deploy:

```bash
curl -f https://your-domain/health
curl -f -X POST https://your-domain/auth/login -d '{"username":"admin","password":"<password>"}' -H "Content-Type: application/json"
```

- Verify media uploads in the admin panel
- Confirm NFT marker generation completes within the expected SLA (<5 seconds average)
- Test both local storage and remote storage paths if enabled

Document the results inside your release checklist or incident response tooling.

---

## 🧭 Maintenance & Operations

- Schedule `scripts/backup.sh` with cron (`0 3 * * * /path/to/project/scripts/backup.sh`)
- Review disk usage weekly (`du -sh vertex-ar/storage`)
- Rotate logs and archive old NFT markers older than 90 days if unused
- Keep dependencies updated quarterly using `pip-compile` or similar tooling
- Track deployment history in `CHANGELOG.md`

For security-specific procedures refer to [SECURITY.md](../../SECURITY.md).
