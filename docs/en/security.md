**English** | [Русский](/ru/docs/security)

# Security Rules

See also: [security-checklist.md](security-checklist.md) — OWASP Top 10 checklist.

## Core principles

1. **Never trust user input** — validate everything
2. **Least privilege** — grant only what's needed
3. **Defense in depth** — multiple layers of protection
4. **Fail safe** — errors must not leak information
5. **Audit everything** — log security events

---

## OWASP Top 10 (brief)

### A01: Broken Access Control
- Check authorization on EVERY endpoint
- Don't trust client-side data
- Verify resource ownership

### A02: Cryptographic Failures
- Use argon2/bcrypt for passwords (NOT MD5/SHA1)
- Secrets via environment variables
- HTTPS required in production

### A03: Injection
- Parameterized SQL queries
- `textContent` instead of `innerHTML`
- Escape output for XSS prevention

### A05: Security Misconfiguration
- Safe error messages
- Configured security headers
- Specific CORS (not `*`)

### A07: Authentication Failures
- Rate limiting on auth endpoints
- Secure cookie flags (httpOnly, secure, sameSite)
- Strong password requirements

---

## Input validation

### Required checks
- Data type
- Length / size
- Format (email, URL, etc)
- Allowed values (whitelist)

### Where to validate
- At system boundaries (API, CLI, MCP) — always
- Inside trusted code paths — only at the boundary
- Client-side validation = UX only, not security

---

## Authentication

### Password requirements
- At least 12 characters
- Mix of uppercase, lowercase, digits, symbols
- Check against well-known breached-password lists

### Cookie security
```
httpOnly: true    — no JS access
secure: true      — HTTPS only
sameSite: strict  — CSRF protection
```

---

## Secrets management

### Never
- Hardcode secrets in source
- Commit `.env` files
- Log secret values

### Do this instead
- Environment variables for local dev (gitignored `.env`)
- Production: secret manager (AWS Secrets Manager, HashiCorp Vault)
- Rotate keys periodically

### .gitignore for secrets
```
.env
.env.*
!.env.example
secrets/
*.pem
*.key
```

---

## Audit logging

### What to log
- All authentication events (success + failure)
- Permission changes
- Sensitive data access
- Configuration / administrative actions

### What NOT to log
- Passwords (even hashed)
- API keys
- Session tokens
- Card numbers
- PII in cleartext

Logs must contain: timestamp, actor, action, resource.

---

## Checklists

### Pre-commit
- [ ] No hardcoded secrets
- [ ] Input validation on all endpoints
- [ ] Authorization checks present
- [ ] Error messages don't leak information
- [ ] No SQL / command injection
- [ ] Rate limiting on sensitive endpoints

### Pre-deploy
- [ ] Dependencies scanned for vulnerabilities
- [ ] Security headers configured
- [ ] HTTPS enforced
- [ ] Secrets in proper storage
- [ ] Logging configured correctly

---

## TAUSIK-specific guards

- `bash_firewall.py` blocks `rm -rf /`, `git reset --hard origin`, force-push
- `git_push_gate.py` requires a fresh, single-use ticket at `.tausik/.push_ticket.json`, written by `tausik push-ok` (60s TTL, bound to HEAD SHA). `/ship` and `/commit` run `tausik push-ok && git push` after user "y". The historical `TAUSIK_ALLOW_PUSH=1` env path was broken-by-design (inline env never reached harness-level hooks) and was removed in v1.4. `TAUSIK_SKIP_PUSH_HOOK=1` remains as a debug-only bypass.
- `memory_pretool_block.py` blocks Write/Edit to `~/.claude/**/memory/` (auto-memory leak prevention)
- `brain_scrubbing.py` strips private URLs and project names before brain writes
- Slug validation in role/stack scaffold blocks path traversal
