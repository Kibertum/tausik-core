---
slug: upgrade-from-1-8-crashes-at-v53-and-leaves-the-version-at-44
title: "Upgrading 1.8 → 1.9 crashes at v53 (duplicate column tz_ref) and leaves schema_version at 44: cumulative CREATE scripts run before migrations, and the version is stamped only at the end"
status: planning
epic: release-110-deferred-from-19
story: release110-the-update-reaches-the-user
complexity: complex
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/backend_init.py"
  - "scripts/backend_migrations.py"
  - "tests/"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/en/whats-new-1.9.md"
  - "docs/ru/whats-new-1.9.md"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

REPORTED BY THE OWNER FROM A CONSUMER PROJECT, 2026-09-14, upgrading 1.8.0 → 1.9.0 (consumer memory #52; fixed there by hand with duplicate-column-tolerant migrations and DB backups). Mechanism, confirmed in the source: on an EXISTING database init_schema runs every cumulative schema script BEFORE run_migrations — CREATE TABLE IF NOT EXISTS actz_points from backend_schema_actz.ACTZ_SQL creates the table in its CURRENT shape, tz_ref included, because a v44 database has no such table yet; then run_migrations(conn, 44) replays v45… and v53's ALTER TABLE actz_points ADD COLUMN tz_ref fails with 'duplicate column name'. Second defect on top: run_migrations COMMITs each migration but the schema_version row is written by init_schema only after the whole chain returns — so v45–v52 are committed, the stamp stays 44, and the next start fails earlier (v47) on what is already there. The upgrade is neither ordered nor atomic nor resumable, and every 1.8 consumer following the README hits it on the first command. Not caught because tests/test_migrations and the real-volume chain test call run_migrations directly on a base without the cumulative scripts; the one path a consumer actually takes — init_schema on a v44 database — was never exercised. Fix: (1) on an existing database run migrations FIRST and the cumulative CREATE scripts after (all are IF NOT EXISTS), or make init_schema skip cumulative creation when a migration chain is pending; (2) each migration stamps schema_version inside its own transaction so a failure leaves a resumable database at the last completed version; (3) a test that builds a v44 database from the frozen v1.8.0 schema literal and upgrades it through init_schema — the consumer's path — plus the negative: interrupt after v50, restart, complete. Recommendation to the owner: this is 1.9.1 material, not only 1.10 — a released README sends every 1.8 user into a crash.

## Acceptance Criteria

AC-1: a database at schema_version 44 built from the FROZEN v1.8.0 schema literal (a new tests/ literal, like test_migrations.V1_SCHEMA) upgraded through backend_init.init_schema — not run_migrations — reaches SCHEMA_VERSION with every table and column the fresh install has (compared by PRAGMA table_info per table) and PRAGMA integrity_check ok. AC-2 (negative): the same upgrade interrupted after v50 (a migration made to raise in the test) leaves schema_version = 50 and a second init_schema completes the chain — no duplicate-column, no duplicate-table. AC-3 (negative): the cumulative creation scripts never run ahead of a pending migration chain: a test asserts that on a v44 database actz_points does not exist until v52 creates it. AC-4: the fix is re-run on the owner's consumer database copy (the pre-upgrade backup from the consumer's scratchpad) and reaches SCHEMA_VERSION cleanly; numbers logged. AC-5: CHANGELOG entry under Fixed names the consumer path and 1.8 → 1.9 explicitly; docs/{en,ru}/whats-new-1.9.md get a known-issue line pointing at the fix release.

## Plan

## Rollback

git revert; the reorder and the per-migration stamp are in backend_init/backend_migrations only; a consumer already patched by hand is unaffected (IF NOT EXISTS everywhere)

## Journal
