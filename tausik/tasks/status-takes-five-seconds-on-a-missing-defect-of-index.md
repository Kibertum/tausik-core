---
slug: status-takes-five-seconds-on-a-missing-defect-of-index
title: "tausik status takes 5.3 s on one query — EXISTS over tasks.defect_of has no index — so SessionStart and Stop hooks time out and their context is silently never delivered"
status: done
epic: release-19-agent-effectiveness
story: release19-effective-context
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "scripts/backend_schema_indexes.py, tests/"
scope_exclude: "scripts/backend_migrations*.py, scripts/backend_schema.py (no SCHEMA_VERSION bump: defect_of is a v10 column, so the index belongs in POST_MIGRATION_INDEXES_SQL, which runs after migrations on both the fresh and the upgrade path)"
relevant_files:
  - "scripts/backend_migrations_v62.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_schema_indexes.py"
  - "tests/test_migration_v62_defect_of_index.py"
  - "docs/ru/whats-new-1.9.md"
  - "docs/en/whats-new-1.9.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
  - "tests/test_actz.py"
  - "tests/test_adapts.py"
  - "tests/test_at.py"
  - "tests/test_reasoning_steps.py"
  - "tests/test_specs.py"
scope_paths:
  - "scripts/backend_migrations_v62.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_schema_indexes.py"
  - "tests/test_migration_v62_defect_of_index.py"
  - "docs/ru/whats-new-1.9.md"
  - "docs/en/whats-new-1.9.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
  - "tests/test_actz.py"
  - "tests/test_adapts.py"
  - "tests/test_at.py"
  - "tests/test_reasoning_steps.py"
  - "tests/test_specs.py"
scope_tools: []
depends_on: []
completed_at: "2026-09-14T00:52:37Z"
---

## Goal

Measured in session #261 on this machine: `tausik status` runs 5.3 s of which 5.04 s is ONE query — backend_defect_escape._done_rows, whose correlated subquery `EXISTS(SELECT 1 FROM tasks d WHERE d.defect_of = t.slug)` has no index on tasks.defect_of and re-scans the wide tasks table (1654 rows, large notes) for each of 1504 done rows; the sibling EXISTS over verification_runs takes 0.0 s because idx_verify_task exists. Consequence: session_start.py and session_cleanup_check.py each take 5.9 s against their deployed timeouts of 6 s and 5 s — in a headless probe the SessionStart hook was CANCELLED at 6298 ms (hook_cancelled, timedOut=True) and the entire auto-injected TAUSIK context, including the rag-first reminder, never reached the model. Fix: add idx_tasks_defect_of in a schema migration (and re-check the other EXISTS/JOIN sites on defect_of), then re-measure status and both hooks under their deployed timeouts. The timeouts themselves are not the bug — the query is.

## Acceptance Criteria

AC-1: POST_MIGRATION_INDEXES_SQL carries idx_tasks_defect_of ON tasks(defect_of); a fresh DB and a migrated DB both have it (tests/test_schema_index_parity.py passes; a test asserts the index exists on a freshly initialised DB). AC-2: measured on this project's live DB after the next init: `tausik status` under 1 s and backend_defect_escape._done_rows under 100 ms (numbers logged before and after). AC-3: session_start.py and session_cleanup_check.py each finish under their deployed timeouts (6 s / 5 s) on the same machine, measured with the hook's stdin JSON, numbers logged. AC-4 (negative): a test asserts EXPLAIN QUERY PLAN of the defect_of EXISTS subquery uses idx_tasks_defect_of (no scan of tasks), so the regression cannot return silently; the test fails when the index line is removed (mutation run logged).

## Plan

## Rollback

git revert; the index is additive (IF NOT EXISTS) and dropping it restores the old plan without data loss.

## Journal

- 2026-09-14T00:37:24Z [implementation] — AC-1 ✓ tests/test_schema_index_parity.py::TestPostMigrationIndexesReachBothPaths::test_present_on_a_fresh_install and ::test_present_after_a_real_upgrade pass with idx_tasks_defect_of in POST_MIGRATION_INDEXES_SQL; migration v62 (scripts/backend_migrations_v62.py, one frozen CREATE INDEX IF NOT EXISTS) registered, SCHEMA_VERSION 61→62, parity check green; tests/test_migrations.py and tests/test_fresh_install_has_every_migrated_table.py pass (49 passed). AC-2 ✓ live DB migrated by the CLI (backup tausik.db.bak.v61 written): before — _done_rows 5425.5 ms, `tausik status` 5.6 s; after — _done_rows 5.0 ms, `status` 1.2 s cold / 0.3 s warm. AC-3 ✓ session_start.py 5.9 s → 0.94 s (timeout 6 s), session_cleanup_check.py 5.9 s → 0.73 s (timeout 5 s), both fed the hook's stdin JSON with CLAUDE_PROJECT_DIR set. AC-4 ✓ (NEGATIVE) tests/test_migration_v62_defect_of_index.py::TestTheDefectOfLookupUsesTheIndex::test_on_a_fresh_install asserts EXPLAIN QUERY PLAN of the statement _done_rows actually issues names idx_tasks_defect_of and no SCAN of d; ::test_negative_without_the_index_the_plan_is_a_scan drops the index and asserts the plan falls back to SCAN (the mutation, run as a test rather than by hand); ::test_after_the_v62_migration_on_a_database_without_it proves the migration alone carries the index to a v61 database, since init_schema runs no DDL at the current version. Domain: the hook that delivers the session context now finishes in under a sixth of its timeout on the largest database we have. Deviation: the CLI runs the DEPLOYED copy (.claude/scripts), so bootstrap --ide all was needed before the migration applied; the MCP server holds the old code until restart (memory #621) — closing via CLI. Notes pages: 44 → 62, Eighteen/Восемнадцать, a v62 sentence; CHANGELOG ×2; entry count on the pages 251 → 252.
- 2026-09-14T00:52:33Z [implementation] — Scoped verify #2650 green (ruff, pytest over the 84 mapped files). The first two scoped runs were red on five synthetic fixtures (test_actz/test_adapts/test_at/test_reasoning_steps/test_specs) that stub tasks as (slug) only — a column every real v35 database has since v10; the stubs now declare defect_of TEXT. The gate printed only 'FAILURES' and cut the test names: reproduced the selection with gate_command_runner.resolve_test_files_for_relevant to find them — that truncation is a silent-failure defect of the pytest gate output, noted for 1.10.
