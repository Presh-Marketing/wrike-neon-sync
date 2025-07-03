# Deployment Security Checklist

## Pre-Deployment Requirements

### 1. Google OAuth Setup ⏳
- [ ] Create Google Cloud Project
- [ ] Configure OAuth consent screen (Internal, @preshmarketingsolutions.com only)
- [ ] Create OAuth 2.0 credentials
- [ ] Add authorized redirect URIs (localhost + production)
- [ ] Set GOOGLE_CLIENT_ID in .env
- [ ] Set GOOGLE_CLIENT_SECRET in .env
- [ ] Test login with @preshmarketingsolutions.com email
- [ ] For production: Remove localhost from redirect URIs (or use separate OAuth app)

### 2. Redis Setup
- [ ] Install Redis locally for development
- [ ] Choose Redis provider for production (Redis Cloud, AWS ElastiCache, etc.)
- [ ] Set REDIS_URL in .env
- [ ] Test Redis connection

### 3. Environment Configuration
- [ ] Generate strong SECRET_KEY (use `secrets.token_urlsafe(32)`)
- [ ] Set FLASK_ENV=production
- [ ] Configure APP_URL with production domain
- [ ] Create .env from config.example
- [ ] Add .env to .gitignore (verify it's not tracked)

### 4. Security Features Verification
- [ ] Google Sign-In working with domain restriction
- [ ] Session management via Redis
- [ ] CSRF protection enabled
- [ ] Rate limiting active
- [ ] Security headers configured
- [ ] HTTPS enforcement ready

### 5. Application Security
- [ ] All routes require authentication (except /health)
- [ ] User email tracked in all operations
- [ ] Error pages don't leak sensitive info
- [ ] API keys secured in environment variables
- [ ] No hardcoded credentials in code

### 6. Database Security
- [ ] Neon connection using SSL
- [ ] Database credentials in environment variables
- [ ] Principle of least privilege for DB user
- [ ] Regular backup strategy defined

### 7. Production Infrastructure
- [ ] HTTPS certificate obtained
- [ ] Domain configured
- [ ] Firewall rules configured
- [ ] DDoS protection enabled (CloudFlare, etc.)
- [ ] Monitoring/alerting set up

### 8. Testing
- [ ] Run `python scripts/test_google_oauth.py`
- [ ] Test with multiple @preshmarketingsolutions.com accounts
- [ ] Test unauthorized email rejection
- [ ] Test rate limiting
- [ ] Test session expiration
- [ ] Load test sync operations

### 9. Documentation
- [ ] Document login process for users
- [ ] Document admin procedures
- [ ] Document backup/recovery process
- [ ] Create incident response plan

### 10. Final Steps
- [ ] Review all environment variables
- [ ] Disable debug mode
- [ ] Enable production logging
- [ ] Set up automated security updates
- [ ] Schedule security audit

## Quick Commands

### Test Configuration
```bash
python scripts/test_google_oauth.py
```

### Run Secure App Locally
```bash
python app_secure.py
```

### Generate Secret Key
```python
import secrets
print(secrets.token_urlsafe(32))
```

### Check Redis
```bash
redis-cli ping
```

## Emergency Procedures

### If locked out:
1. Access server via SSH
2. Temporarily disable auth in app_secure.py
3. Fix configuration
4. Re-enable auth

### If compromised:
1. Revoke Google OAuth credentials immediately
2. Rotate all secrets
3. Review access logs
4. Notify affected users

## Support Contacts

- Google Cloud Console: https://console.cloud.google.com
- Neon Dashboard: https://console.neon.tech
- Redis Cloud: https://app.redislabs.com

## Notes

Remember: Security is an ongoing process. Schedule regular reviews and updates. 