---
slug: qg-2-security-pattern-directory-anchored-only-no-bare
task: null
date: "2026-05-03"
edges: []
---

## Decision

QG-2 security pattern: directory-anchored only — no bare substring tokens

## Rationale

Bare substrings ("session", "login", "scripts/hooks/") in _SECURITY_PATH_TOKENS produced silent false-positives across TAUSIK's own infra files (every hook + every hook test), which then forced is_cache_allowed=False and made verify-first task_done lookups always fail. The fix anchors all path tokens with leading+trailing slashes (path-segment match), keeps explicit basenames for filename-only signals, and adds explicit credential-bearing basenames (secrets.json, id_rsa, .npmrc). Trade-off: lose loose substring catches like src/widget/password_reset.py — acceptable because real auth code consistently lives under /auth/, /accounts/, /login/, etc., and the cost of a false-positive verify-first block is much higher than missing one substring-only signal.</rationale>
<parameter name="task_slug">v14b-defect-qg2-security-substring-too-broad</parameter>
</invoke>
<invoke name="mcp__tausik-project__tausik_memory_add">
<parameter name="type">pattern</parameter>
<parameter name="title">Security-pattern matching: anchor by path segment, not by raw substring</parameter>
<parameter name="content">When classifying file paths against a security-sensitivity list (or any sort-of-allow-list), use directory-anchored tokens (`/auth/`, `/oauth/`) and exact basename matches — NOT bare substrings. Raw substring matching catches every file with the keyword anywhere in its path, including unrelated tests, infra hooks, widget code, and documentation. The cost of an over-broad classifier compounds wherever it is consulted: in TAUSIK it cascaded into is_cache_allowed=False → has_fresh_verify_run=(False,None) → task_done refuses every fresh `tausik verify` for any task touching a hook file. Anchored matching costs you a few real auth signals where folder names are quirky, but loses far fewer minutes than chasing "no fresh verify run" on a green build.

Reference: scripts/service_verification.py:67-114, tests/test_security_sensitive.py.</content>
<parameter name="tags">["security", "verify-first", "qg2", "patterns"]</parameter>
<parameter name="task_slug">v14b-defect-qg2-security-substring-too-broad</parameter>
</invoke>
<invoke name="Bash">
<parameter name="command">.tausik/tausik.cmd task done v14b-defect-qg2-security-substring-too-broad --ac-verified 2>&1 | tail -5</parameter>
<parameter name="description">Close defect task with knowledge captured</parameter>
</invoke>
