---
slug: qg-2-security-pattern-directory-anchored-only-no-bare
task: null
date: "2026-05-03"
edges: []
---

## Decision

QG-2 security pattern: directory-anchored only — no bare substring tokens

## Rationale

Bare substrings ("session", "login", "scripts/hooks/") in _SECURITY_PATH_TOKENS produced silent false-positives across TAUSIK's own infra files (every hook + every hook test), which then forced is_cache_allowed=False and made verify-first task_done lookups always fail. The fix anchors all path tokens with leading+trailing slashes (path-segment match), keeps explicit basenames for filename-only signals, and adds explicit credential-bearing basenames (secrets.json, id_rsa, .npmrc). Trade-off: lose loose substring catches like src/widget/password_reset.py — acceptable because real auth code consistently lives under /auth/, /accounts/, /login/, etc., and the cost of a false-positive verify-first block is much higher than missing one substring-only signal.
