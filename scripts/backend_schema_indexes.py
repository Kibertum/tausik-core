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
CREATE INDEX IF NOT EXISTS idx_session_usage_session_id ON session_usage_metrics(session_id);
CREATE INDEX IF NOT EXISTS idx_session_usage_recorded_at ON session_usage_metrics(recorded_at);
CREATE INDEX IF NOT EXISTS idx_usage_events_session ON usage_events(session_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_usage_events_task ON usage_events(task_slug, recorded_at);
"""
