# Vertex AR Production Deployment Checklist

## Pre-Deployment Checklist ✅

### Environment Verification
- [ ] Target OS: Ubuntu 22.04 LTS or 24.04 LTS (not 18.04 EOL)
- [ ] Python 3.10+ installed and verified
- [ ] Node.js 20+ LTS installed (not 16 EOL)
- [ ] Minimum 5GB free disk space
- [ ] Minimum 2GB RAM available
- [ ] Ports 8000, 80, 443 are free or available
- [ ] Root/sudo access available
- [ ] User `rustadmin` exists or will be created

### Security Preparation
- [ ] Strong SECRET_KEY generated (not default)
- [ ] Admin password generated (not CHANGE_ME_IMMEDIATELY)
- [ ] SSL certificates obtained for domain
- [ ] SSL certificate private key has 400 permissions
- [ ] SSL certificate directory /etc/ssl/private has 700 permissions
- [ ] .env file will be set to 600 permissions
- [ ] CORS_ORIGINS configured for production domain
- [ ] DEBUG=False confirmed
- [ ] Git repository access verified (SSH keys if private repo)

### Backup Strategy
- [ ] Backup destination identified
- [ ] Backup retention policy defined (default: 7 days)
- [ ] Pre-deployment backup planned
- [ ] Rollback procedure documented
- [ ] Test backup restoration procedure

### Dependencies
- [ ] requirements.txt or requirements-simple.txt present
- [ ] All required system packages identified
- [ ] Internet access available for package installation
- [ ] PyPI access available (or private mirror configured)
- [ ] npm registry access available (or private mirror)

### Configuration
- [ ] Domain name configured: nft.vertex-art.ru (or custom)
- [ ] BASE_URL set correctly
- [ ] INTERNAL_HEALTH_URL configured if needed
- [ ] Database path verified (SQLite or PostgreSQL URL)
- [ ] Storage type selected (local or MinIO/S3)
- [ ] Storage path created and accessible

### Monitoring & Alerting
- [ ] Sentry DSN configured (optional but recommended)
- [ ] Telegram bot token and chat ID (optional)
- [ ] SMTP server configured for email alerts (optional)
- [ ] Admin email addresses configured
- [ ] Monitoring thresholds reviewed (CPU: 80%, Memory: 85%, Disk: 90%)
- [ ] Lifecycle scheduler enabled/disabled decision
- [ ] Video scheduler enabled/disabled decision

---

## During Deployment Checklist 🚀

### Phase 1: Pre-Flight Checks
- [ ] Root privileges confirmed
- [ ] System requirements check passed
- [ ] User rustadmin verified/created
- [ ] Ports availability checked
- [ ] Disk space verified

### Phase 2: Backup
- [ ] Pre-deployment backup created
  - [ ] Database backed up
  - [ ] Storage files backed up
  - [ ] .env configuration backed up
  - [ ] Backup location recorded
- [ ] Backup integrity verified

### Phase 3: System Preparation
- [ ] System packages updated (apt update && apt upgrade)
- [ ] Dependencies installed successfully
  - [ ] python3, python3-pip, python3-venv
  - [ ] git, wget, curl
  - [ ] supervisor, nginx
  - [ ] sqlite3, libssl-dev, libffi-dev
  - [ ] build-essential
  - [ ] OpenCV dependencies (libgl1-mesa-glx, etc.)
- [ ] Python 3.10+ verified
- [ ] Node.js 20+ installed

### Phase 4: Application Setup
- [ ] Repository cloned or updated
- [ ] Virtual environment created
- [ ] Python dependencies installed
- [ ] No pip installation errors
- [ ] Database migrations run (if applicable)

### Phase 5: Configuration
- [ ] .env file created or updated
- [ ] SECRET_KEY generated and unique
- [ ] Admin password generated and unique
- [ ] All required environment variables present
- [ ] Production secrets validated (not default values)
- [ ] File permissions correct (.env: 600)

### Phase 6: SSL/TLS Setup
- [ ] SSL certificates copied to server
  - [ ] Certificate: /etc/ssl/certs/nft.vertex-art.ru.crt
  - [ ] Private key: /etc/ssl/private/nft.vertex-art.ru.key
- [ ] Certificate permissions correct (key: 400)
- [ ] Certificate validity verified (openssl x509 -text)
- [ ] Certificate matches domain

### Phase 7: Service Configuration
- [ ] Log directory created (/var/log/vertex-ar)
- [ ] Supervisor configuration created
  - [ ] Command path correct
  - [ ] Working directory correct
  - [ ] User correct (rustadmin)
  - [ ] Environment variables included
- [ ] Nginx configuration created
  - [ ] Upstream configured (127.0.0.1:8000)
  - [ ] SSL configuration correct
  - [ ] Static files path correct
  - [ ] Client max body size set (50M)
  - [ ] Rate limiting configured (if needed)
- [ ] Nginx configuration tested (nginx -t)
- [ ] Nginx enabled and started

### Phase 8: Application Start
- [ ] Supervisor reloaded
- [ ] Application started via supervisor
- [ ] Supervisor shows RUNNING status
- [ ] No errors in supervisor logs
- [ ] Application logs show startup success

### Phase 9: Health Verification
- [ ] Application responds on localhost:8000
- [ ] /health endpoint returns OK
- [ ] /api/monitoring/health endpoint accessible
- [ ] Admin panel loads (https://domain/admin)
- [ ] Static files served correctly
- [ ] Database connection successful
- [ ] Storage path accessible

### Phase 10: Post-Deployment Setup
- [ ] Backup cron job created
- [ ] Backup cron job verified in crontab
- [ ] Logrotate configured
- [ ] Monitoring enabled (if configured)
- [ ] Alerting tested (if configured)

---

## Post-Deployment Verification ✅

### Functional Testing
- [ ] Admin login works
- [ ] Default admin credentials work (superar / generated-password)
- [ ] Can create new company
- [ ] Can create new project
- [ ] Can create new client
- [ ] Can upload portrait image
- [ ] Can upload video
- [ ] NFT marker generation works
- [ ] AR viewer accessible via permalink
- [ ] QR code generation works
- [ ] QR code scans correctly

### Security Verification
- [ ] HTTPS redirects working (HTTP → HTTPS)
- [ ] SSL certificate valid (no browser warnings)
- [ ] Admin panel requires authentication
- [ ] API endpoints require authentication
- [ ] Rate limiting working
- [ ] CORS configured correctly
- [ ] No sensitive data in logs
- [ ] .env file not web-accessible

### Performance Testing
- [ ] Application response time < 500ms
- [ ] AR viewer loads < 3s
- [ ] Video upload successful (test with ~10MB file)
- [ ] Image upload successful (test with ~5MB file)
- [ ] Multiple concurrent users supported
- [ ] No memory leaks observed

### Monitoring & Logging
- [ ] Application logs writing to /var/log/vertex-ar/
- [ ] Nginx logs writing correctly
- [ ] Supervisor logs accessible
- [ ] Monitoring endpoint accessible (/api/monitoring/metrics)
- [ ] Alerts configured and tested
- [ ] Prometheus metrics exposed (if enabled)

### Backup Verification
- [ ] Backup script executable
- [ ] Backup script runs without errors
- [ ] Backup files created in correct location
- [ ] Backup includes database
- [ ] Backup includes storage files
- [ ] Backup includes configuration
- [ ] Backup restoration tested on staging

---

## Rollback Procedure 🔄

### If Deployment Fails:

1. **Stop New Application**
   ```bash
   sudo supervisorctl stop vertex-ar
   ```

2. **Restore Database**
   ```bash
   BACKUP_DIR=$(cat /tmp/vertex-ar-last-backup.txt)
   sudo cp "$BACKUP_DIR/app_data.db" /home/rustadmin/vertex-ar-app/vertex-ar/
   ```

3. **Restore Storage**
   ```bash
   sudo rm -rf /home/rustadmin/vertex-ar-app/vertex-ar/storage
   sudo cp -r "$BACKUP_DIR/storage" /home/rustadmin/vertex-ar-app/vertex-ar/
   ```

4. **Restore Configuration**
   ```bash
   sudo cp "$BACKUP_DIR/.env" /home/rustadmin/vertex-ar-app/vertex-ar/
   ```

5. **Restart Application**
   ```bash
   sudo supervisorctl start vertex-ar
   ```

6. **Verify Health**
   ```bash
   curl http://127.0.0.1:8000/health
   ```

7. **Check Logs**
   ```bash
   sudo tail -f /var/log/vertex-ar/error.log
   ```

---

## Common Issues & Solutions 🔧

### Issue: Nginx fails to start
**Cause:** SSL certificates not found or invalid  
**Solution:**
```bash
# Generate self-signed certificate temporarily
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/nft.vertex-art.ru.key \
  -out /etc/ssl/certs/nft.vertex-art.ru.crt \
  -subj "/CN=nft.vertex-art.ru"
sudo chmod 400 /etc/ssl/private/nft.vertex-art.ru.key
sudo systemctl restart nginx
```

### Issue: Application fails to start
**Cause:** Python dependencies installation failed  
**Solution:**
```bash
cd /home/rustadmin/vertex-ar-app/vertex-ar
source ../venv/bin/activate
pip install --upgrade pip
pip install -r requirements-simple.txt --verbose
deactivate
```

### Issue: Port 8000 already in use
**Cause:** Previous instance still running  
**Solution:**
```bash
sudo lsof -ti:8000 | xargs sudo kill -9
sudo supervisorctl restart vertex-ar
```

### Issue: Database locked
**Cause:** SQLite file permissions or concurrent access  
**Solution:**
```bash
sudo chown rustadmin:rustadmin /home/rustadmin/vertex-ar-app/vertex-ar/app_data.db
sudo chmod 644 /home/rustadmin/vertex-ar-app/vertex-ar/app_data.db
```

### Issue: Static files not served
**Cause:** Nginx path incorrect or permissions  
**Solution:**
```bash
sudo chown -R rustadmin:rustadmin /home/rustadmin/vertex-ar-app/vertex-ar/static
sudo chmod -R 755 /home/rustadmin/vertex-ar-app/vertex-ar/static
sudo systemctl restart nginx
```

### Issue: Health check fails
**Cause:** Application not fully started  
**Solution:** Wait 10-15 seconds and retry, check logs

---

## Emergency Contacts 📞

**Production Issues:**
- Check logs: `sudo tail -f /var/log/vertex-ar/error.log`
- Check status: `sudo supervisorctl status vertex-ar`
- Restart app: `sudo supervisorctl restart vertex-ar`

**Critical Failures:**
- Initiate rollback procedure (see above)
- Contact: [Your on-call engineer/team]
- Escalate: [Your incident management process]

---

## Post-Deployment Tasks 📋

### Immediate (Day 1)
- [ ] Monitor error logs for first 24 hours
- [ ] Verify backup cron job runs successfully
- [ ] Test all critical user workflows
- [ ] Update documentation with actual deployment details
- [ ] Save generated admin password securely
- [ ] Share credentials with relevant team members

### Week 1
- [ ] Monitor application performance metrics
- [ ] Review and analyze logs for errors
- [ ] Verify automated backups running daily
- [ ] Test backup restoration procedure
- [ ] Check disk space usage trends
- [ ] Verify SSL certificate expiration date

### Month 1
- [ ] Review security logs
- [ ] Analyze usage patterns
- [ ] Optimize performance if needed
- [ ] Update documentation with lessons learned
- [ ] Schedule SSL certificate renewal (if needed)
- [ ] Review backup retention policy

---

## Success Criteria ✅

Deployment is considered successful when:

1. ✅ Application is accessible via HTTPS
2. ✅ All core features functional (upload, view, AR)
3. ✅ No critical errors in logs
4. ✅ Health checks passing
5. ✅ Monitoring and alerting operational
6. ✅ Backups running successfully
7. ✅ SSL certificate valid
8. ✅ Performance within acceptable limits
9. ✅ Security checks passed
10. ✅ Rollback procedure tested and documented

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-XX  
**Maintained By:** Vertex AR DevOps Team
