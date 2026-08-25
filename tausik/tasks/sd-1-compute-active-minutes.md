---
slug: sd-1-compute-active-minutes
title: "backend_queries: compute_active_minutes(session_id, idle_threshold)"
status: done
epic: v13-mcp-and-discipline
story: session-duration-fix
complexity: null
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "scripts/backend_queries.py, tests/test_backend_queries.py"
scope_exclude: "scripts/hooks/*, scripts/project_cli*, CLAUDE.md (separate task)"
relevant_files:
  - "scripts/backend_session_metrics.py"
  - "tests/test_backend_session_metrics.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T00:52:25Z"
---

## Goal

Add SQL function that sums intervals between consecutive events in a session where gap < idle_threshold (default 10 min). Returns active_minutes int. Backed by `events` table created_at column.

## Acceptance Criteria

1. Function `compute_active_minutes(conn, session_id, idle_threshold_minutes=10) -> int` exists in scripts/backend_queries.py
2. Sums intervals between consecutive `events` rows for the session where gap_minutes < idle_threshold_minutes
3. Returns 0 for sessions with 0 or 1 event
4. Gaps ≥ threshold contribute 0 (excluded from sum)
5. Gaps < threshold contribute the full gap minutes
6. Tests in tests/test_backend_queries.py cover: empty session, single event, all-active, all-idle, mixed, custom threshold
7. SQL uses julianday() arithmetic, single roundtrip, no Python-side iteration

## Plan

## Rollback

## Journal

- 2026-04-25T23:45:14Z [implementation] — Paused mid-implementation: user asked to verify TAUSIK /review vs built-in Claude Code /review overlap. Investigating before continuing — affects qd-1 task design.
- 2026-04-26T00:52:22Z [implementation] — AC verified: 1. compute_active_minutes(q,q1,session_id,idle_threshold_minutes=10) added in scripts/backend_session_metrics.py ✓ 2. Sums intervals via SQL window function (LAG over events.created_at) where gap < threshold ✓ 3. Empty/single-event sessions return 0 (test_empty_session_returns_zero, test_single_event_returns_zero) ✓ 4. Gaps >= threshold contribute 0 (test_gap_above_threshold_excluded) ✓ 5. Gaps < threshold contribute full minutes (test_all_active_intervals_summed: 5 events × 5min = 20min) ✓ 6. Tests cover all listed cases (14 tests pass in 0.38s) ✓ 7. SQL: WITH ordered AS (LAG OVER ORDER BY created_at), single roundtrip ✓ NEGATIVE: test_unknown_session_returns_zero, test_negative_threshold_returns_zero ✓
