---
slug: sd-3-cleanup-hook-uses-active
title: "session_cleanup_check hook: 180-min limit checks active_minutes"
status: done
epic: v13-mcp-and-discipline
story: session-duration-fix
complexity: null
role: developer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/hooks/session_cleanup_check.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T00:52:40Z"
---

## Goal

Switch session_cleanup_check.py hook to compute active_minutes via new query and warn at 180 min active (not wall clock). Wall clock stays informational.

## Acceptance Criteria

## Plan

## Rollback

## Journal

- 2026-04-26T00:52:39Z [planning] — AC verified: 1. _session_overrun_minutes regex now matches 'X min active' (v1.3 status format) ✓ 2. Legacy 'running for N min' regex kept as fallback for stale CLI deployments ✓ 3. session_check_duration in service_task uses session_active_minutes (not wall) for 180-min limit ✓ 4. Wall clock printed in warning text for context ✓ 5. Existing test_session_cleanup_check.py still passes (31 tests session+metrics passed) ✓ NEGATIVE: regex match=None handled (returns 0) ✓
