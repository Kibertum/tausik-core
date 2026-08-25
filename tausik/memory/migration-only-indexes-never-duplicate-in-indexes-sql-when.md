---
slug: migration-only-indexes-never-duplicate-in-indexes-sql-when
title: "Migration-only indexes: never duplicate in INDEXES_SQL when adding a new column"
type: gotcha
tags:
  - indexes_sql
  - init_schema
  - migration
  - schema
  - sqlite
task: v14b-memory-cleanup-cli
edges: []
---

When a migration ADDs a column AND wants an index on it, the index MUST live ONLY inside the migration entry. Putting `CREATE INDEX IF NOT EXISTS idx_NEW ON tasks(new_col)` into INDEXES_SQL breaks every existing-DB upgrade: backend_init.init_schema runs SCHEMA_SQL (CREATE TABLE IF NOT EXISTS — no-op when table exists) then INDEXES_SQL **before** run_migrations applies the ADD COLUMN, so SQLite raises "no such column: new_col". Fresh installs skip migrations entirely (run_migrations is called with current=SCHEMA_VERSION) so they would also miss the index — but that mirrors the established v24 pattern for idx_usage_events_tool. Net rule: add the index to the migration list (e.g. `25: ['ALTER TABLE tasks ADD COLUMN archived_at TEXT', 'CREATE INDEX ... ON tasks(archived_at)']`) and do NOT touch INDEXES_SQL. Reproduces in B5 (v25 archived_at on tasks) and B9 (v26 archived_at on memory). Established v24 idx_usage_events_tool is the correct precedent.
