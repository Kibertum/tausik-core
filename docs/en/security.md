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
- A default gate's command cannot be pointed at a different tool: `.tausik/config.json` travels with the repository, so an override of `gates.<name>.command` must keep invoking the default's tool. Arguments, paths and runner wrappers stay free (`vendor/bin/phpstan analyse --level=8` is accepted, and so is `eslint {files}` against a default of `npx eslint {files}` — wrappers are seen through); the tool does not (`python -c pass` in place of `ruff` is refused and the default command is kept)

### Limits of these guarantees

Supervision is machine-checked where a machine can check it. What remains is written down here honestly rather than left implied.

- **Inert arguments to the same tool are NOT detected.** The check compares the tool being invoked, not the meaning of the invocation, so `ruff --version` or `pytest --collect-only` in an override will pass: the tool is the right one, the gate is nominally enabled, and it is green forever. There is no machine-checkable definition of "this command does real work", and a rule requiring the command to start with the default prefix would break both the vendored-path case and the legitimate dropping of an `npx` wrapper. Read gate command overrides in a foreign repository with your own eyes — a gate that goes green suspiciously fast deserves a look at its command.
- **Built-in gates** (`filesize`, `tdd_order`, `renar_drift_*`) have no command at all; an attempt to add one is refused.
