---
slug: v15p-fts-optimize-cron
title: "[P2] Автоматический fts optimize (session_end hook)"
status: done
epic: v15-polish
story: v15p-debt
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "scripts/backend_queries.py (fts_maybe_optimize), scripts/project_service.py + scripts/service_session.py (call on session_end best-effort), tests/test_fts_maybe_optimize.py"
scope_exclude: "no cron/OS scheduler; fts_optimize() core unchanged; no FTS schema change"
relevant_files:
  - "scripts/backend_queries.py"
  - "scripts/project_service.py"
  - "scripts/service_session.py"
  - "tests/test_fts_maybe_optimize.py"
  - README.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T17:49:25Z"
---

## Goal

Техдолг #13: fts optimize вызывается вручную. Запускать автоматически — на session end при превышении порога фрагментации (дёшево, без cron-зависимости). AC: optimize срабатывает по порогу; не блокирует session end дольше 2с (background/best-effort); событие логируется.

## Acceptance Criteria

AC1: on `session end`, FTS optimize runs automatically ONLY when activity since the last optimize exceeds a threshold (cheap churn proxy = events-table delta); below threshold it is a no-op. AC2: it is best-effort and does not block session end beyond ~2s — any failure is swallowed, session still ends cleanly. AC3: when it optimizes, it persists the new baseline (meta key) and logs an audit event. AC4: covered by tests (threshold not met → skip; met → optimize+baseline+event; failure → no crash); filesize<400; stdlib-only.

## Plan

## Rollback

git revert; feature is additive (new method + a guarded call in session_end) — reverting restores manual-only optimize; meta key is inert if unused.

## Journal

- 2026-06-14T17:49:03Z [implementation] — Added backend_queries.fts_maybe_optimize(threshold=200): churn proxy = COUNT(*) on events table (every task/memory/decision mutation logs an event) vs meta key fts.last_optimize_events; optimizes only when delta>=threshold, persists fresh baseline AFTER logging the audit event (delta truly resets), best-effort. Service passthrough + guarded call in service_session.session_end (try/except, sub-second, never blocks/breaks end). 5 tests (skip below threshold / optimize+baseline / audit event / reset after / corrupt baseline no-crash). No cron, no FTS schema change.
- 2026-06-14T17:49:24Z [implementation] — AC1: ✓ fts_maybe_optimize optimizes only when events-delta>=threshold (churn proxy); below → no-op — test_below_threshold_skips + test_at_threshold_optimizes. AC2: ✓ best-effort: called in session_end wrapped in try/except, fts optimize is sub-second on these indexes, failure swallowed — service_session.py guard; test_corrupt_baseline_does_not_crash. AC3: ✓ persists new baseline (meta fts.last_optimize_events, set AFTER logging so delta resets) + logs audit event — test_at_threshold (baseline==current) + test_optimize_logs_audit_event + test_second_call...below_threshold. AC4: ✓ 5 tests; backend_queries.py 389<400; stdlib-only. Domain: on a real busy project, optimize fires roughly every ~200 mutations at session end and is idempotent/safe; quiet projects never pay the cost. Negative: below-threshold call leaves meta untouched; corrupt baseline treated as 0 (no crash); a failing events COUNT returns optimized=False not an exception.
