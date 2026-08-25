---
slug: r14-brain-metrics
title: "tausik metrics: brain searches per session, hit rate, write count"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: null
role: null
stack: null
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/backend_migrations.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_crud.py"
  - "scripts/backend_crud_brain.py"
  - "scripts/brain_metrics_log.py"
  - "scripts/brain_mcp_read.py"
  - "scripts/brain_runtime.py"
  - "tests/test_brain_metrics.py"
  - "docs/en/shared-brain.md"
  - "docs/ru/shared-brain.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T01:26:33Z"
---

## Goal

Release 1.4 readiness: r14-brain-metrics

## Acceptance Criteria

1. Migration v22 + brain_events(session_id, event_type CHECK search/hit/write/ignored, query, result_count, ts) - schema mirror updated. 2. backend_crud.brain_event_record / brain_event_metrics return per-session and all-time counts incl. hit_rate_pct. 3. brain_metrics_log.log_brain_event helper writes events from any module (uses CLAUDE_PROJECT_DIR). 4. brain_mcp_read.search_with_fallback logs search and conditional hit; brain_runtime.try_brain_write_decision/web_cache log write on success. 5. tausik metrics prints 'Shared Brain (v1.4)' block when events exist. Negative: empty events table -> block hidden, brain_event_record raises ValueError on bad type, log_brain_event returns False when project DB missing.

## Plan

## Rollback

## Journal

- 2026-05-01T01:24:25Z [implementation] — AC verified: AC-1 ✓ tested via tests/test_brain_metrics.py::test_brain_events_table_exists. AC-2 ✓ tested via tests/test_brain_metrics.py::test_brain_event_metrics_aggregation (hit_rate=50%). AC-3 ✓ tested via tests/test_brain_metrics.py::test_log_brain_event_helper_writes_into_project_db. AC-4 ✓ manual review of search_with_fallback + brain_runtime + cmd_metrics integration. AC-5 Negative: tests/test_brain_metrics.py::test_log_brain_event_no_db_returns_false + test_brain_event_metrics_empty + test_brain_event_record_validates_type.
- 2026-05-01T01:24:25Z [implementation] — Docs: docs/en/shared-brain.md and docs/ru/shared-brain.md gained Metrics (v1.4) section explaining counters and hit_rate_pct interpretation. Mirrored to .claude/docs/.
- 2026-05-01T01:24:25Z [implementation] — Migration v22: brain_events table mirrored in backend_schema (SCHEMA_VERSION=22). backend_crud helpers brain_event_record/brain_event_metrics return session+all-time aggregates.
- 2026-05-01T01:24:25Z [implementation] — Tests tests/test_brain_metrics.py (6 cases): table exists, type CHECK, empty metrics shape, multi-event aggregation with 50% hit rate, log_brain_event roundtrip via CLAUDE_PROJECT_DIR, missing-DB returns False.
- 2026-05-01T01:24:25Z [implementation] — Wired into brain_mcp_read.search_with_fallback (search + conditional hit on len(final)) and brain_runtime.try_brain_write_decision/try_brain_write_web_cache (write on ok/ok_not_mirrored). project_cli_ops.cmd_metrics prints 'Shared Brain (v1.4)' block when events exist.
- 2026-05-01T01:24:25Z [implementation] — scripts/brain_metrics_log.py - best-effort logger. log_brain_event resolves project DB via CLAUDE_PROJECT_DIR/cwd, swallows failures so telemetry never blocks brain operations. read_metrics returns same shape as backend_crud.brain_event_metrics.
