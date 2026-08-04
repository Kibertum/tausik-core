"""Secondary indexes for the core schema — extracted from backend_schema.py to
keep it under the 400-line filesize gate (state-git-stable-ids added the slug
columns that pushed it over).

``INDEXES_SQL`` runs AFTER SCHEMA_SQL on a fresh DB and, on an existing DB, runs
BEFORE migrations — so it must only index columns present in the v1 baseline.
Indexes on migration-added columns live in their migration, never here. Applied
by backend_init.init_schema; the split is mechanical, behaviour is unchanged.
"""

from __future__ import annotations

INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_stories_epic_id ON stories(epic_id);
CREATE INDEX IF NOT EXISTS idx_stories_status ON stories(status);
CREATE INDEX IF NOT EXISTS idx_tasks_story_id ON tasks(story_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_slug ON tasks(slug);
-- NOTE: indexes on migration-added tasks columns (e.g. started_model_id,
-- model_mismatch — v33) live ONLY in their migration, NOT here. INDEXES_SQL
-- runs before migrations on an existing DB, where those columns don't yet
-- exist; indexing them here would crash init_schema (mirrors idx_tasks_archived_at).
CREATE INDEX IF NOT EXISTS idx_decisions_task_slug ON decisions(task_slug);
CREATE INDEX IF NOT EXISTS idx_memory_type ON memory(type);
CREATE INDEX IF NOT EXISTS idx_memory_task_slug ON memory(task_slug);
CREATE INDEX IF NOT EXISTS idx_events_entity ON events(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
CREATE INDEX IF NOT EXISTS idx_task_logs_slug ON task_logs(task_slug);
CREATE INDEX IF NOT EXISTS idx_task_logs_phase ON task_logs(phase);
CREATE INDEX IF NOT EXISTS idx_task_logs_created ON task_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_reasoning_steps_slug ON reasoning_steps(task_slug, seq);
CREATE INDEX IF NOT EXISTS idx_reasoning_steps_created ON reasoning_steps(created_at);
CREATE INDEX IF NOT EXISTS idx_edges_source ON memory_edges(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON memory_edges(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_edges_relation ON memory_edges(relation);
CREATE INDEX IF NOT EXISTS idx_edges_valid ON memory_edges(valid_to);
CREATE INDEX IF NOT EXISTS idx_verify_task ON verification_runs(task_slug, ran_at DESC);
CREATE INDEX IF NOT EXISTS idx_verify_files_hash ON verification_runs(files_hash);
-- Same rule as the tasks note above, and it was broken here once: v44's
-- idx_verify_handle indexes handle_nonce/handle_redeemed_at, which do not exist
-- on an existing DB at the moment INDEXES_SQL runs. Putting it here made
-- init_schema raise "no such column: handle_nonce" on EVERY upgrading install
-- while fresh databases stayed green. It lives in backend_migrations_v44.
CREATE INDEX IF NOT EXISTS idx_session_usage_session_id ON session_usage_metrics(session_id);
CREATE INDEX IF NOT EXISTS idx_session_usage_recorded_at ON session_usage_metrics(recorded_at);
CREATE INDEX IF NOT EXISTS idx_usage_events_session ON usage_events(session_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_usage_events_task ON usage_events(task_slug, recorded_at);
"""

# Indexes on columns that MIGRATIONS add, applied AFTER migrations have run —
# on both the fresh-install and the upgrade path.
#
# WHY THIS EXISTS. The rule above ("indexes on migration-added columns live in
# their migration, never here") is right about INDEXES_SQL, but following it
# alone left fresh databases without those indexes at all. `init_schema` stamps
# meta.schema_version = SCHEMA_VERSION on a brand-new DB and then calls
# `run_migrations(conn, SCHEMA_VERSION)`, which applies only migrations with
# `ver > current_version` — i.e. none. So a fresh install got the COLUMNS (from
# SCHEMA_SQL) but never the CREATE INDEX statements that live beside them in the
# migrations, while a database carried up by migrations got both. Six indexes
# had silently diverged that way before this block existed; adding a seventh is
# what made it worth fixing rather than commenting on again.
#
# Every statement is IF NOT EXISTS, so running it on an upgraded DB that already
# has them is a no-op. Duplication with the migrations is deliberate and pinned:
# a migration is a historical snapshot and must keep its own CREATE INDEX, while
# this block is the CURRENT set. tests/test_schema_index_parity.py compares a
# fresh database against a migrated one and fails on any drift between them.
POST_MIGRATION_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_tasks_archived_at ON tasks(archived_at);
CREATE INDEX IF NOT EXISTS idx_tasks_started_model ON tasks(started_model_id);
CREATE INDEX IF NOT EXISTS idx_tasks_model_mismatch ON tasks(model_mismatch);
CREATE INDEX IF NOT EXISTS idx_tasks_no_file_changes_declared
    ON tasks(no_file_changes_declared);
CREATE INDEX IF NOT EXISTS idx_verify_scope_status
    ON verification_runs(declared_scope_status);
CREATE INDEX IF NOT EXISTS idx_verify_no_tests_declared
    ON verification_runs(no_tests_declared);
CREATE INDEX IF NOT EXISTS idx_verify_handle
    ON verification_runs(handle_nonce, handle_redeemed_at);
"""
