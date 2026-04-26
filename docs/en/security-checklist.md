# OWASP Top 10 — Detailed Checks

## A01: Broken Access Control
- [ ] Authorization check on EVERY endpoint
- [ ] Resource ownership verified
- [ ] No client-side trust for access decisions
- [ ] CORS configured specifically (not `*`)

## A02: Cryptographic Failures
- [ ] Passwords hashed with argon2/bcrypt (NOT MD5/SHA1)
- [ ] Secrets via environment variables
- [ ] HTTPS enforced in production
- [ ] Sensitive data not in logs

## A03: Injection
- [ ] Parameterized SQL queries only
- [ ] ORM used correctly
- [ ] Command injection prevented
- [ ] textContent over innerHTML (XSS)

## A04: Insecure Design
- [ ] Input validation at boundaries
- [ ] Rate limiting implemented
- [ ] Fail securely (no info leakage)

## A05: Security Misconfiguration
- [ ] Debug mode off in production
- [ ] Security headers configured
- [ ] Default credentials changed
- [ ] Error messages don't reveal internals

## A07: Authentication Failures
- [ ] Strong password requirements (12+ chars)
- [ ] Account lockout after failures
- [ ] Secure session management
- [ ] MFA where appropriate

## A08: Data Integrity Failures
- [ ] Dependencies verified (lock files)
- [ ] No untrusted deserialization
- [ ] CI/CD pipeline secured

## A09: Logging Failures
- [ ] Security events logged
- [ ] No sensitive data in logs
- [ ] Log injection prevented

## A10: SSRF
- [ ] URL validation for external requests
- [ ] Allowlist for external services
- [ ] No internal network exposure

## Cookie Security

```
httpOnly: true    # No JS access
secure: true      # HTTPS only
sameSite: strict  # CSRF protection
```

## Secrets Management

### Never Do
- Hardcode secrets in code
- Commit .env files
- Log secrets or tokens
- Store passwords in plain text

### Always Do
- Use environment variables
- Use secrets managers (Vault, AWS SM)
- Rotate credentials regularly
- Add secrets to .gitignore

## Pre-Deploy Checklist

- [ ] Dependencies scanned for vulnerabilities
- [ ] Security headers configured
- [ ] HTTPS enforced
- [ ] Secrets in secure storage
- [ ] Logging configured properly
- [ ] Debug mode disabled
