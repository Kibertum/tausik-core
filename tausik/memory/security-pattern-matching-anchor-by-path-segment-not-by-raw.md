---
slug: security-pattern-matching-anchor-by-path-segment-not-by-raw
title: "Security-pattern matching: anchor by path segment, not by raw substring"
type: pattern
tags: []
task: null
edges: []
---

When classifying file paths against a security-sensitivity list (or any sort-of-allow-list), use directory-anchored tokens (`/auth/`, `/oauth/`) and exact basename matches — NOT bare substrings. Raw substring matching catches every file with the keyword anywhere in its path, including unrelated tests, infra hooks, widget code, and documentation. The cost of an over-broad classifier compounds wherever it is consulted: in TAUSIK it cascaded into is_cache_allowed=False → has_fresh_verify_run=(False,None) → task_done refuses every fresh `tausik verify` for any task touching a hook file. Anchored matching costs you a few real auth signals where folder names are quirky, but loses far fewer minutes than chasing "no fresh verify run" on a green build.

Reference: scripts/service_verification.py:67-114, tests/test_security_sensitive.py.
