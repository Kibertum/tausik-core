---
slug: brain-schema-wal-mode
title: "MEDIUM: PRAGMA journal_mode=WAL в open_brain_db"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: brain-decide-auto-route
scope: null
scope_exclude: null
relevant_files:
  - "scripts/brain_sync.py"
  - "scripts/brain_notion_props.py"
  - "tests/test_brain_storage_hardening.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T15:00:50Z"
---

## Goal

Без WAL concurrent sync + MCP read получают SQLITE_BUSY. Включить WAL в open_brain_db() сразу после connect

## Acceptance Criteria

1. `open_brain_db` in scripts/brain_sync.py enables WAL via `PRAGMA journal_mode=WAL` immediately after `sqlite3.connect`, before `apply_schema` runs (so schema DDL is already under WAL).
2. Handle rejection gracefully: if WAL is not available (e.g. `:memory:`, read-only FS, network drive), fall back silently to default journal mode — never raise.
3. Regression test in tests/test_brain_sync.py (or new test_brain_sync_wal.py) verifying the pragma takes effect on a file-backed DB and the graceful fallback on :memory:.
4. Full pytest green + ruff clean.

## Plan

## Rollback

## Journal

- 2026-04-24T14:52:36Z [implementation] — AC verified: 1. ✓ open_brain_db runs PRAGMA journal_mode=WAL right after sqlite3.connect, before apply_schema — scripts/brain_sync.py:117-128. 2. ✓ sqlite3.Error from the pragma is caught and silently swallowed — default rollback journal used. Verified by test_wal_failure_does_not_raise with a Connection proxy that throws on journal_mode pragma. 3. ✓ test_file_db_reports_wal verifies WAL mode active on file-backed DB; test_memory_db_falls_back_silently sanity-checks the :memory: fallback path; test_wal_failure_does_not_raise exercises the exception branch. 4. ✓ pytest 1669 passed / 2 skipped / 0 failed; ruff clean.
