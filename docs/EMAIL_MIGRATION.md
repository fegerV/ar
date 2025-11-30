# Email/SMTP Configuration Migration Guide

**Version:** 1.6.0  
**Date:** January 2025  
**Status:** ✅ Required for Production Deployments

---

## Table of Contents

1. [Overview](#overview)
2. [Why This Change?](#why-this-change)
3. [Migration Steps](#migration-steps)
4. [Rotating Existing Secrets](#rotating-existing-secrets)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)
7. [Rollback (Emergency)](#rollback-emergency)
8. [FAQ](#faq)

---

## Overview

**IMPORTANT:** Starting with Vertex AR v1.6.0, environment-based SMTP credentials (`SMTP_USERNAME` and `SMTP_PASSWORD`) are **deprecated** and will cause the application to refuse to start in production mode.

### What Changed

| Aspect | Old (Deprecated) | New (Secure) |
|--------|-----------------|--------------|
| **Storage** | `.env` file / environment variables | Encrypted database entries |
| **Encryption** | ❌ Plaintext | ✅ AES-256 encryption via `encryption_manager` |
| **Audit Trail** | ❌ No logging | ✅ Every config access logged with timestamp & actor |
| **Rotation** | Requires server restart | No restart needed |
| **Security** | Exposed in process environment, logs, backups | Protected in database, redacted from all logs |

### Timeline

- **Development/Staging:** Warning logged, application continues
- **Production:** Application **refuses to start** if env-based credentials detected
- **All environments:** `settings.SMTP_USERNAME` and `settings.SMTP_PASSWORD` always return `None`

---

## Why This Change?

### Security Risks with Environment Variables

1. **Plaintext Exposure**
   - Environment variables are visible to all processes
   - Appear in system logs, process listings (`ps`, `htop`)
   - Included in container orchestration configs (Docker Compose, Kubernetes)
   - Stored in CI/CD pipeline configurations

2. **No Access Control**
   - Any code with access to `os.environ` can read credentials
   - Third-party dependencies can leak credentials
   - No audit trail of who/what accessed credentials

3. **Backup/DR Risks**
   - Environment files get backed up as plaintext
   - Git history often contains old `.env` files
   - Disaster recovery procedures may expose credentials

4. **Compliance Issues**
   - Fails PCI DSS, SOC 2, ISO 27001 requirements
   - No encryption at rest
   - No key rotation capabilities

### Benefits of Database-Backed Configuration

✅ **Encrypted at Rest:** AES-256 encryption via dedicated encryption manager  
✅ **Audit Logging:** Every config access logged with actor, timestamp, and sanitized details  
✅ **Access Control:** Only admin users can modify via authenticated UI  
✅ **Zero Downtime Rotation:** Update credentials without server restart  
✅ **Compliance Ready:** Meets industry standards for credential management  
✅ **Guardrails:** System refuses to operate without encrypted DB entries  

---

## Migration Steps

### Step 1: Access Admin UI

1. Log in to Vertex AR admin panel:
   ```
   https://your-domain.com/admin/login
   ```

2. Navigate to Notification Settings:
   ```
   https://your-domain.com/admin/notification-settings
   ```

### Step 2: Configure SMTP Settings

In the admin UI, fill out the SMTP configuration form:

| Field | Example | Description |
|-------|---------|-------------|
| **SMTP Host** | `smtp.gmail.com` | Your mail server hostname |
| **SMTP Port** | `587` (TLS) or `465` (SSL) | Mail server port |
| **Username** | `notifications@yourcompany.com` | SMTP authentication username |
| **Password** | `your-app-password` | SMTP authentication password |
| **From Email** | `noreply@yourcompany.com` | Email sender address |
| **Use TLS** | ✅ (for port 587) | Enable STARTTLS encryption |
| **Use SSL** | ✅ (for port 465) | Enable SSL/TLS wrapper |

**Gmail Users:** Generate an [App Password](https://support.google.com/accounts/answer/185833) instead of using your account password.

### Step 3: Test Configuration

1. Click **"Test Email Configuration"** in the admin UI
2. Enter a test recipient email address
3. Verify the test email is received
4. Check logs for any errors:
   ```bash
   # View application logs
   docker logs vertex-ar-app
   
   # Or if running directly
   tail -f /var/log/vertex-ar/app.log
   ```

### Step 4: Remove Environment Variables

Once the test succeeds, remove deprecated environment variables:

**For `.env` file deployments:**
```bash
# Edit your .env file
nano /path/to/vertex-ar/.env

# Comment out or remove these lines:
# SMTP_USERNAME=...
# SMTP_PASSWORD=...
```

**For Docker Compose:**
```yaml
# docker-compose.yml
services:
  app:
    environment:
      # Remove these:
      # - SMTP_USERNAME=...
      # - SMTP_PASSWORD=...
```

**For Kubernetes:**
```bash
# Remove from ConfigMap or Secret
kubectl edit configmap vertex-ar-config -n vertex-ar

# Or update your deployment manifest
```

**For systemd services:**
```bash
# Edit service file
sudo systemctl edit vertex-ar.service

# Remove Environment= lines for SMTP credentials
sudo systemctl daemon-reload
```

### Step 5: Restart Application

```bash
# Docker Compose
docker-compose restart app

# Systemd
sudo systemctl restart vertex-ar

# Docker
docker restart vertex-ar-app

# Kubernetes
kubectl rollout restart deployment/vertex-ar -n vertex-ar
```

### Step 6: Verify Clean Logs

Check that no warnings appear in startup logs:

```bash
# Docker
docker logs vertex-ar-app 2>&1 | grep -i "SMTP.*WARNING"

# Should return no results
```

If you see:
```
CRITICAL SECURITY WARNING: SMTP credentials detected in environment variables!
```

Then environment variables are still set. Go back to Step 4.

---

## Rotating Existing Secrets

If your SMTP credentials are compromised or you need to rotate them for compliance:

### Quick Rotation (Zero Downtime)

1. **Access Admin UI** → Notification Settings
2. **Update password field** with new credentials
3. **Click "Save Configuration"**
4. **Test** to verify new credentials work
5. ✅ **Done** - No server restart required

### Full Rotation with Provider Change

If changing SMTP providers (e.g., Gmail → SendGrid):

1. Set up new SMTP service account
2. Access admin UI
3. Update **all** SMTP fields (host, port, username, password)
4. Enable/disable TLS/SSL as appropriate for new provider
5. Test configuration
6. Save changes
7. Monitor email queue for a few hours to ensure delivery

### Emergency Credential Revocation

If credentials are actively compromised:

1. **Immediately** change password at your email provider
2. Update in Vertex AR admin UI
3. Check application logs for unauthorized access:
   ```bash
   grep "SMTP config accessed" /var/log/vertex-ar/app.log
   ```
4. Review audit trail for suspicious actors
5. Consider rotating encryption keys (see `app/encryption.py`)

---

## Verification

### 1. Check Configuration Storage

Verify credentials are encrypted in database:

```bash
# SQLite
sqlite3 /path/to/app_data.db
> SELECT smtp_host, smtp_username, 
         length(smtp_password_encrypted) as encrypted_length 
  FROM notification_settings;

# Should show:
# - smtp_host: your-host
# - smtp_username: your-username
# - encrypted_length: 200+ bytes (not empty)
```

### 2. Verify Log Redaction

Check that logs never contain plaintext credentials:

```bash
# Search all logs for sensitive patterns
grep -r "password.*=" /var/log/vertex-ar/ | grep -v "REDACTED"

# Should return no results with actual passwords
```

### 3. Test Email Delivery

Send test emails from various parts of the application:

```bash
# Via API (requires admin auth token)
curl -X POST https://your-domain.com/api/test-email \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"to": "test@example.com", "subject": "Test", "body": "Test message"}'

# Expected response:
# {"status": "queued", "message": "Email queued for delivery"}
```

### 4. Monitor Prometheus Metrics

Check email service metrics:

```bash
# View metrics endpoint
curl https://your-domain.com/metrics | grep vertex_ar_email

# Key metrics:
# - vertex_ar_email_sent_total: Should increment
# - vertex_ar_email_failed_total: Should stay low
# - vertex_ar_email_queue_depth: Should be near zero
```

### 5. Audit Access Logs

Review SMTP config access audit trail:

```bash
# View structured logs
cat /var/log/vertex-ar/app.log | jq 'select(.event == "SMTP config accessed")'

# Should show:
# - actor: "email_service", "alerting", "lifecycle_scheduler", etc.
# - timestamp: ISO 8601 timestamps
# - config: Sanitized (passwords show "***REDACTED***")
```

---

## Troubleshooting

### Error: "Application refuses to start in production"

**Symptom:**
```
CRITICAL SECURITY WARNING: SMTP credentials detected in environment variables!
FATAL: Cannot start in production with env-based SMTP credentials
```

**Solution:**
1. Remove `SMTP_USERNAME` and `SMTP_PASSWORD` from environment
2. Configure via admin UI
3. Restart application

---

### Error: "SMTP config rejected: missing encrypted password"

**Symptom:**
```
SMTP config rejected: missing encrypted password in database
```

**Cause:** Notification settings not configured in database.

**Solution:**
1. Access `/admin/notification-settings`
2. Fill out and save SMTP configuration
3. Verify `notification_settings` table has `smtp_password_encrypted` populated

---

### Warning: "Email service disabled, cannot send email"

**Symptom:** Emails not being sent, logs show:
```
Email service disabled, cannot send email
```

**Cause:** No valid SMTP configuration available.

**Solution:**
1. Check notification settings in admin UI
2. Ensure "Active" checkbox is enabled
3. Verify SMTP credentials are correct
4. Test configuration

---

### Error: "Failed to decrypt SMTP password"

**Symptom:**
```
Failed to decrypt SMTP password: Invalid decryption key
```

**Cause:** Encryption key changed or database from different installation.

**Solution:**
1. Check `ENCRYPTION_KEY` environment variable matches original
2. If key lost, reconfigure SMTP in admin UI (old encrypted data cannot be recovered)
3. Verify `vertex-ar/app/.encryption_key` file permissions (readable by app)

---

### Emails Not Being Delivered

**Check 1: Queue Status**
```bash
# CLI tool to check queue
python scripts/process_email_queue.py stats

# Expected output shows pending emails
```

**Check 2: SMTP Authentication**
```bash
# Test SMTP connectivity
openssl s_client -connect smtp.gmail.com:587 -starttls smtp

# Should establish TLS connection
```

**Check 3: Provider Restrictions**
- **Gmail:** App Passwords required (not account password)
- **Office 365:** Modern authentication may be required
- **SendGrid/Mailgun:** API keys instead of passwords

**Check 4: Firewall/Network**
```bash
# Test outbound SMTP connectivity
telnet smtp.gmail.com 587

# Should connect (Ctrl+] then 'quit' to exit)
```

---

### Logs Still Showing Plaintext Passwords

**If you see passwords in logs:**

1. **Verify log redaction is active:**
   ```python
   # In Python console
   from logging_setup import get_logger
   logger = get_logger("test")
   logger.info("test", password="secret123")
   
   # Should log: password="***REDACTED***"
   ```

2. **Check old log files:**
   ```bash
   # Rotate logs immediately
   logrotate -f /etc/logrotate.d/vertex-ar
   
   # Or manually
   mv /var/log/vertex-ar/app.log /var/log/vertex-ar/app.log.old
   systemctl restart vertex-ar
   ```

3. **Report issue:** If new logs still leak credentials, file a security bug report.

---

## Rollback (Emergency)

**⚠️ Only use in genuine emergency - not recommended for production**

If you must rollback temporarily:

### Development/Staging

1. Set `ENVIRONMENT=development` in `.env`
2. Re-add `SMTP_USERNAME` and `SMTP_PASSWORD` to `.env`
3. Restart application
4. Application will log critical warning but continue

### Production

**Not possible** - application will refuse to start. You must either:

**Option A: Configure via Admin UI** (recommended)
- Follow migration steps above
- Takes ~5 minutes

**Option B: Temporary Non-Production Mode** (emergency only)
```bash
# TEMPORARY - set environment to staging
export ENVIRONMENT=staging

# Restart app
systemctl restart vertex-ar

# ⚠️ Remember to fix properly ASAP
```

**Option C: Code Modification** (last resort)
```python
# vertex-ar/app/config.py
# Comment out lines 104-106:
# if environment == "production":
#     _logger.critical("FATAL: Cannot start...")
#     sys.exit(1)
```

**Important:** Options B and C are **security violations** and should only be used during a genuine outage. Schedule immediate migration.

---

## FAQ

### Q: Can I use both environment variables and database config?

**A:** No. If environment variables are detected, the application will:
- Development: Log critical warning, ignore env vars, use database config
- Production: Refuse to start

The `settings.SMTP_USERNAME` and `settings.SMTP_PASSWORD` attributes are **always** `None` after v1.6.0.

---

### Q: What happens to emails during migration?

**A:** The email queue is persistent:
1. Emails queued before migration remain in database
2. After configuring SMTP in admin UI, queue resumes processing
3. Zero emails lost during migration

---

### Q: How is the encryption key managed?

**A:** The encryption key is stored in:
1. File: `vertex-ar/app/.encryption_key` (auto-generated on first run)
2. Environment: `ENCRYPTION_KEY` (overrides file)

**Important:** 
- Back up `.encryption_key` securely
- Do not commit to git (already in `.gitignore`)
- If lost, reconfiguration required (old data cannot be decrypted)

---

### Q: Can I rotate the encryption key?

**A:** Yes, but requires re-encrypting all secrets:

```bash
# 1. Backup database
cp app_data.db app_data.db.backup

# 2. Export current config (do this manually via admin UI)
# Note down all SMTP/Telegram credentials

# 3. Generate new key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 4. Update ENCRYPTION_KEY environment variable
export ENCRYPTION_KEY="your-new-key"

# 5. Clear notification_settings table
sqlite3 app_data.db "DELETE FROM notification_settings;"

# 6. Restart app
systemctl restart vertex-ar

# 7. Reconfigure via admin UI with noted credentials
```

---

### Q: Does this affect Telegram notifications?

**A:** Telegram bot tokens follow the same pattern:
- Old: `TELEGRAM_BOT_TOKEN` in environment
- New: Encrypted in database via admin UI
- Migration: Follow same steps as SMTP

---

### Q: What about multi-tenant deployments?

**A:** Each tenant should have:
- Separate database
- Own notification settings
- Own encryption key

For shared database architectures, extend `notification_settings` table with `tenant_id` column.

---

### Q: Can I automate configuration via API?

**A:** Yes, use the notification settings API:

```bash
# Create/update notification settings (requires admin auth)
curl -X POST https://your-domain.com/api/admin/notification-settings \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_username": "user@example.com",
    "smtp_password": "app-password",
    "smtp_from_email": "noreply@example.com",
    "smtp_use_tls": true,
    "is_active": true
  }'
```

The API automatically encrypts credentials before storage.

---

### Q: How do I audit who changed SMTP settings?

**A:** Check application logs:

```bash
# View all SMTP config changes
cat /var/log/vertex-ar/app.log | jq 'select(.event | contains("notification settings"))'

# View who accessed SMTP config
cat /var/log/vertex-ar/app.log | jq 'select(.event == "SMTP config accessed") | {timestamp, actor}'
```

For full audit trail, integrate with external SIEM system via Prometheus/webhooks.

---

### Q: What if I need different SMTP servers for different email types?

**A:** Currently, Vertex AR supports one SMTP configuration per installation. For multiple SMTP servers:

**Option 1: Smart Host Routing** (recommended)
- Configure one SMTP server that routes based on sender/recipient
- Example: Postfix/Exim as smart host

**Option 2: Code Modification**
- Extend `notification_settings` table with `smtp_config_id`
- Modify `NotificationConfig.get_smtp_config()` to accept config selector
- File feature request for official multi-SMTP support

---

### Q: Does email queue survive server restarts?

**A:** Yes! The email queue is stored in the database:
- Pending emails persist across restarts
- Workers resume processing on startup
- No emails lost during deployment

See `docs/EMAIL_QUEUE.md` for queue architecture details.

---

## Support

**Documentation:**
- Email Queue: `docs/EMAIL_QUEUE.md`
- Email Monitoring: `docs/EMAIL_MONITORING.md`
- Encryption: `vertex-ar/app/encryption.py`

**Commands:**
```bash
# Check email queue status
python scripts/process_email_queue.py stats

# Retry failed emails
python scripts/process_email_queue.py retry

# View email monitoring metrics
curl https://your-domain.com/api/monitoring/email-stats
```

**Need Help?**
1. Check logs: `docker logs vertex-ar-app`
2. Review metrics: `https://your-domain.com/metrics`
3. File issue: GitHub Issues
4. Emergency: Contact platform administrator

---

## Security Best Practices

1. ✅ **Always use admin UI** for credential management
2. ✅ **Enable TLS/SSL** for SMTP connections
3. ✅ **Rotate credentials quarterly** or after any security incident
4. ✅ **Monitor access logs** for suspicious activity
5. ✅ **Back up encryption key** securely (offline, encrypted storage)
6. ✅ **Use app passwords** (Gmail, Office 365) instead of account passwords
7. ✅ **Restrict admin access** to authorized personnel only
8. ✅ **Enable Prometheus alerting** on email failures
9. ✅ **Test disaster recovery** procedures regularly
10. ✅ **Keep Vertex AR updated** for security patches

---

**Document Version:** 1.0.0  
**Last Updated:** January 2025  
**Applies To:** Vertex AR v1.6.0+
