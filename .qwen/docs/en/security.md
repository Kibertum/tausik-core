**English** | [Русский](../ru/security.md)

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

## Secrets management

- Never commit secrets to git
- Use `.env` for local development (gitignored)
- Production: secret manager (AWS Secrets Manager, HashiCorp Vault)
- Rotate keys periodically
- Don't log secret values

## Audit logging

- All authentication events (success + failure)
- Permission changes
- Sensitive data access
- Configuration changes

Logs must contain: timestamp, actor, action, resource. Logs MUST NOT contain: passwords, tokens, PII without need.

## TAUSIK-specific guards

- `bash_firewall.py` blocks `rm -rf /`, `git reset --hard origin`, force-push
- `git_push_gate.py` requires `TAUSIK_ALLOW_PUSH=1` (set by `/ship` after confirmation)
- `memory_pretool_block.py` blocks Write/Edit to `~/.claude/**/memory/` (auto-memory leak prevention)
- `brain_scrubbing.py` strips private URLs and project names before brain writes
- Slug validation in role/stack scaffold blocks path traversal
