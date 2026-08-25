---
slug: hc-2-extract-tier1-config
title: "Extract tier-1 to .tausik/config.json"
status: done
epic: v13-mcp-and-discipline
story: hardcode-to-config
complexity: null
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T01:39:51Z"
---

## Goal

Move user-tunable values to config with documented defaults

## Acceptance Criteria

verify_cache_ttl_seconds + session_warn_threshold_minutes + session_idle_threshold_minutes config-aware via load_config().get(key, DEFAULT). NEGATIVE: malformed config falls back to defaults gracefully.

## Plan

## Rollback

## Journal

- 2026-04-26T01:39:51Z [implementation] — AC verified: service_verification.run_gates_with_cache loads verify_cache_ttl_seconds via load_config().get(key, DEFAULT_CACHE_TTL_S) ✓ session_cleanup_check._session_warn_min reads session_warn_threshold_minutes from .tausik/config.json (default 150) ✓ Both wrapped in try/except — malformed/missing config falls back to default ✓
