"""TAUSIK schema migrations -- version-by-version SQL transformations.

Separated from backend_schema.py to keep files under 400 lines.
Each migration is a list of SQL statements applied in order.
SQLite cannot ALTER TABLE to add CASCADE/CHECK -- must rebuild via
create temp -> copy -> drop -> rename. Migrations are irreversible.

Legacy migrations (v2-v11) are in backend_migrations_legacy.py.
"""

from __future__ import annotations

from backend_migrations_legacy import LEGACY_MIGRATIONS, seed_v18_roles
from backend_migrations_postseed import run_post_migrations
from backend_migrations_v35 import MIGRATION_V35
from backend_migrations_v36 import MIGRATION_V36
from backend_migrations_v37 import MIGRATION_V37

__all__ = ["MIGRATIONS", "run_migrations", "seed_v18_roles"]

# Current migrations (v12+; v10-v11 live in backend_migrations_legacy.py)
_CURRENT_MIGRATIONS: dict[int, list[str]] = {
    # --- v12: Scope field on tasks (SENAR Core Rule 2) ---
    12: [
        "ALTER TABLE tasks ADD COLUMN scope TEXT",
    ],
    # --- v13: Scope exclusion field (SENAR Core Start Gate #4) ---
    13: [
        "ALTER TABLE tasks ADD COLUMN scope_exclude TEXT",
    ],
    # --- v14: Structured task logs table ---
    14: [
        """CREATE TABLE IF NOT EXISTS task_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_slug TEXT NOT NULL REFERENCES tasks(slug) ON DELETE CASCADE,
            message TEXT NOT NULL,
            phase TEXT CHECK(phase IS NULL OR phase IN
                ('planning', 'implementation', 'review', 'testing', 'done')),
            diff_stats TEXT,
            created_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_task_logs_slug ON task_logs(task_slug)",
        "CREATE INDEX IF NOT EXISTS idx_task_logs_phase ON task_logs(phase)",
        "CREATE INDEX IF NOT EXISTS idx_task_logs_created ON task_logs(created_at)",
        """CREATE VIRTUAL TABLE IF NOT EXISTS fts_task_logs USING fts5(
            message,
            content='task_logs', content_rowid='id'
        )""",
    ],
    # --- v15: Rebuild memory_edges with proper constraints + orphan cleanup ---
    15: [
        # Clean up orphaned edges before rebuild
        "DELETE FROM memory_edges WHERE source_type='memory' AND source_id NOT IN (SELECT id FROM memory)",
        "DELETE FROM memory_edges WHERE source_type='decision' AND source_id NOT IN (SELECT id FROM decisions)",
        "DELETE FROM memory_edges WHERE target_type='memory' AND target_id NOT IN (SELECT id FROM memory)",
        "DELETE FROM memory_edges WHERE target_type='decision' AND target_id NOT IN (SELECT id FROM decisions)",
        # Rebuild memory_edges with proper constraints
        """CREATE TABLE memory_edges_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL CHECK(source_type IN ('memory', 'decision')),
            source_id INTEGER NOT NULL,
            target_type TEXT NOT NULL CHECK(target_type IN ('memory', 'decision')),
            target_id INTEGER NOT NULL,
            relation TEXT NOT NULL CHECK(relation IN ('supersedes', 'caused_by', 'relates_to', 'contradicts')),
            confidence REAL NOT NULL DEFAULT 1.0,
            created_by TEXT,
            valid_from TEXT NOT NULL,
            valid_to TEXT,
            invalidated_by INTEGER REFERENCES memory_edges(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL
        )""",
        "INSERT INTO memory_edges_new SELECT * FROM memory_edges",
        "DROP TABLE memory_edges",
        "ALTER TABLE memory_edges_new RENAME TO memory_edges",
        "CREATE INDEX IF NOT EXISTS idx_edges_source ON memory_edges(source_type, source_id)",
        "CREATE INDEX IF NOT EXISTS idx_edges_target ON memory_edges(target_type, target_id)",
        "CREATE INDEX IF NOT EXISTS idx_edges_relation ON memory_edges(relation)",
        "CREATE INDEX IF NOT EXISTS idx_edges_valid ON memory_edges(valid_to)",
    ],
    # --- v16: verification_runs table for SENAR Rule 5 scoped verify cache ---
    16: [
        """CREATE TABLE IF NOT EXISTS verification_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_slug TEXT,
            scope TEXT NOT NULL CHECK(scope IN
                ('lightweight', 'standard', 'high', 'critical', 'manual')),
            command TEXT NOT NULL,
            exit_code INTEGER NOT NULL,
            summary TEXT,
            files_hash TEXT NOT NULL,
            ran_at TEXT NOT NULL,
            duration_ms INTEGER
        )""",
        "CREATE INDEX IF NOT EXISTS idx_verify_task ON verification_runs(task_slug, ran_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_verify_files_hash ON verification_runs(files_hash)",
    ],
    # --- v17: agent-native planning units (call_budget/call_actual/tier) ---
    17: [
        "ALTER TABLE tasks ADD COLUMN call_budget INTEGER",
        "ALTER TABLE tasks ADD COLUMN call_actual INTEGER",
        "ALTER TABLE tasks ADD COLUMN tier TEXT "
        "CHECK(tier IS NULL OR tier IN "
        "('trivial','light','moderate','substantial','deep'))",
    ],
    # --- v18: roles table — DDL only. Seeding moved to Python helper
    # (backend_migrations_v18_seed) so it can normalize legacy free-text
    # values (whitespace, mixed case, unicode) and rewrite tasks.role to
    # match — preventing orphan rows where tasks.role doesn't appear in
    # the new roles table.
    18: [
        """CREATE TABLE IF NOT EXISTS roles (
            slug TEXT PRIMARY KEY CHECK(length(slug) <= 64),
            title TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
    ],
    # --- v19: session token/cost usage metrics ---
    19: [
        """CREATE TABLE IF NOT EXISTS session_usage_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            tokens_input INTEGER NOT NULL DEFAULT 0,
            tokens_output INTEGER NOT NULL DEFAULT 0,
            tokens_total INTEGER NOT NULL DEFAULT 0,
            cost_usd REAL NOT NULL DEFAULT 0,
            tool_calls INTEGER NOT NULL DEFAULT 0,
            model TEXT,
            recorded_at TEXT NOT NULL,
            UNIQUE(session_id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_session_usage_session_id ON session_usage_metrics(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_session_usage_recorded_at ON session_usage_metrics(recorded_at)",
    ],
    # --- v20: SENAR Rule 10.13 — record agent model id+version per session ---
    20: [
        "ALTER TABLE sessions ADD COLUMN model_id TEXT",
        "ALTER TABLE sessions ADD COLUMN model_version TEXT",
        "CREATE INDEX IF NOT EXISTS idx_sessions_model ON sessions(model_id)",
    ],
    # --- v21: SENAR Rule 10.15 — track L1/L2/L3 reviews + critical findings ---
    21: [
        """CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_slug TEXT NOT NULL REFERENCES tasks(slug) ON DELETE CASCADE,
            run_type TEXT NOT NULL CHECK(run_type IN ('L1','L2','L3')),
            critical_findings INTEGER NOT NULL DEFAULT 0,
            warnings INTEGER NOT NULL DEFAULT 0,
            run_at TEXT NOT NULL,
            notes TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_reviews_task ON reviews(task_slug)",
        "CREATE INDEX IF NOT EXISTS idx_reviews_type ON reviews(run_type)",
    ],
    # --- v22: brain usage tracking — searches/hits/writes per session ---
    22: [
        """CREATE TABLE IF NOT EXISTS brain_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
            event_type TEXT NOT NULL
                CHECK(event_type IN ('search','hit','write','ignored')),
            query TEXT,
            result_count INTEGER NOT NULL DEFAULT 0,
            ts TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_brain_events_session ON brain_events(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_brain_events_type ON brain_events(event_type)",
        "CREATE INDEX IF NOT EXISTS idx_brain_events_ts ON brain_events(ts)",
    ],
    # --- v23: append-only LLM usage ledger (rollup / cost dashboards later) ---
    23: [
        """CREATE TABLE IF NOT EXISTS usage_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
            model_id TEXT,
            tokens_input INTEGER NOT NULL CHECK(tokens_input >= 0),
            tokens_output INTEGER NOT NULL CHECK(tokens_output >= 0),
            tokens_total INTEGER NOT NULL CHECK(tokens_total >= 0),
            cost_usd REAL NOT NULL DEFAULT 0 CHECK(cost_usd >= 0),
            tool_calls INTEGER NOT NULL DEFAULT 0 CHECK(tool_calls >= 0),
            source TEXT NOT NULL CHECK(source IN ('session_record', 'manual')),
            recorded_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_usage_events_session "
        "ON usage_events(session_id, recorded_at)",
        "CREATE INDEX IF NOT EXISTS idx_usage_events_task ON usage_events(task_slug, recorded_at)",
    ],
    # --- v24: per-tool granularity for usage_events (PostToolUse hook) ---
    # Adds tool_name column + relaxes source CHECK to include 'posttool'.
    # SQLite cannot modify CHECK in-place — rebuild via temp table.
    24: [
        """CREATE TABLE usage_events_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
            model_id TEXT,
            tokens_input INTEGER NOT NULL CHECK(tokens_input >= 0),
            tokens_output INTEGER NOT NULL CHECK(tokens_output >= 0),
            tokens_total INTEGER NOT NULL CHECK(tokens_total >= 0),
            cost_usd REAL NOT NULL DEFAULT 0 CHECK(cost_usd >= 0),
            tool_calls INTEGER NOT NULL DEFAULT 0 CHECK(tool_calls >= 0),
            source TEXT NOT NULL CHECK(source IN ('session_record', 'manual', 'posttool')),
            recorded_at TEXT NOT NULL,
            tool_name TEXT
        )""",
        "INSERT INTO usage_events_new("
        "id, session_id, task_slug, model_id, tokens_input, tokens_output, "
        "tokens_total, cost_usd, tool_calls, source, recorded_at, tool_name) "
        "SELECT id, session_id, task_slug, model_id, tokens_input, tokens_output, "
        "tokens_total, cost_usd, tool_calls, source, recorded_at, NULL FROM usage_events",
        "DROP TABLE usage_events",
        "ALTER TABLE usage_events_new RENAME TO usage_events",
        "CREATE INDEX IF NOT EXISTS idx_usage_events_session "
        "ON usage_events(session_id, recorded_at)",
        "CREATE INDEX IF NOT EXISTS idx_usage_events_task ON usage_events(task_slug, recorded_at)",
        "CREATE INDEX IF NOT EXISTS idx_usage_events_tool ON usage_events(tool_name, recorded_at)",
    ],
    # --- v25: archived_at on tasks (soft-delete for hygiene archive --confirm) ---
    # Done tasks older than task_archive.done_age_days get archived_at timestamp;
    # task_list filters them out by default. Status remains 'done' (not 'archived')
    # so historical metrics, FTS, and direct task_show by slug stay intact.
    25: [
        "ALTER TABLE tasks ADD COLUMN archived_at TEXT",
        "CREATE INDEX IF NOT EXISTS idx_tasks_archived_at ON tasks(archived_at)",
    ],
    # --- v26: archived_at on memory (soft-delete for `memory archive --before <duration>`) ---
    # Long-running projects accumulate noise; rather than DROP rows we mark them
    # archived. memory_list/memory_search filter by default; --include-archived
    # opts back in. Mirrors v25 design on tasks.
    26: [
        "ALTER TABLE memory ADD COLUMN archived_at TEXT",
        "CREATE INDEX IF NOT EXISTS idx_memory_archived_at ON memory(archived_at)",
    ],
    # --- v27: per-task cost/token budgets (v14c-token-budget-task) ---
    27: [
        "ALTER TABLE tasks ADD COLUMN cost_budget_usd REAL",
        "ALTER TABLE tasks ADD COLUMN cost_actual_usd REAL",
        "ALTER TABLE tasks ADD COLUMN token_budget INTEGER",
        "ALTER TABLE tasks ADD COLUMN tokens_actual INTEGER",
    ],
    # --- v28: rollback_plan on tasks (SENAR Rule 6, v15s-rule6-rollback-plan) ---
    # QG-0 blocks start of medium/complex tasks without it; task_done warns.
    28: [
        "ALTER TABLE tasks ADD COLUMN rollback_plan TEXT",
    ],
    # --- v29: signed receipt on verify runs (v15-receipt-emit-on-verify) ---
    # tausik-signed/v1 envelope (ed25519 over canonical tausik-receipt/v1)
    # emitted by record_run when the project key exists. NULL = unsigned run
    # (pre-v29 row or keyless project).
    29: [
        "ALTER TABLE verification_runs ADD COLUMN receipt_json TEXT",
    ],
    # --- v30: declared scope ACL on tasks (SENAR Rule 2, v15-scope-declare) ---
    # JSON lists: scope_paths = allowed write globs, scope_tools = allowed
    # tools. NULL = no ACL declared (legacy behavior). Enforcement lands in
    # v15-scope-enforce-write; canonical (de)serialization in scope_acl.py.
    30: [
        "ALTER TABLE tasks ADD COLUMN scope_paths TEXT",
        "ALTER TABLE tasks ADD COLUMN scope_tools TEXT",
    ],
    # --- v31: closure risk score (v15-risk-compute-on-done) ---
    # risk_score 0.0-1.0 + full risk_json ({score, level, factors,
    # defaulted}) computed by risk_model at task_done. NULL = closed
    # before v31 or collection failed (best-effort, never blocks close).
    31: [
        "ALTER TABLE tasks ADD COLUMN risk_score REAL",
        "ALTER TABLE tasks ADD COLUMN risk_json TEXT",
    ],
    # --- v32: RENAR reasoning trace (v16r-reasoning-steps-table) ---
    # Structured per-task reasoning steps (RENAR audit §4.4, blocker #1).
    # Append-only, FTS5-indexed. kind is a CLOSED list (intent|premise|
    # action|verification). Purely additive — no existing table touched.
    32: [
        """CREATE TABLE IF NOT EXISTS reasoning_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_slug TEXT NOT NULL REFERENCES tasks(slug) ON DELETE CASCADE,
            seq INTEGER NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN
                ('intent', 'premise', 'action', 'verification')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_reasoning_steps_slug ON reasoning_steps(task_slug, seq)",
        "CREATE INDEX IF NOT EXISTS idx_reasoning_steps_created ON reasoning_steps(created_at)",
        """CREATE VIRTUAL TABLE IF NOT EXISTS fts_reasoning_steps USING fts5(
            content,
            content='reasoning_steps', content_rowid='id'
        )""",
        """CREATE TRIGGER IF NOT EXISTS reasoning_steps_ai
            AFTER INSERT ON reasoning_steps BEGIN
            INSERT INTO fts_reasoning_steps(rowid, content)
            VALUES (new.id, new.content);
        END""",
        """CREATE TRIGGER IF NOT EXISTS reasoning_steps_ad
            AFTER DELETE ON reasoning_steps BEGIN
            INSERT INTO fts_reasoning_steps(fts_reasoning_steps, rowid, content)
            VALUES ('delete', old.id, old.content);
        END""",
    ],
    # v33: per-task model pinning (v16r-model-pinning) — pin model at start/done +
    # flag mid-task model changes (RENAR blocker #2). Purely additive ALTERs on tasks.
    33: [
        "ALTER TABLE tasks ADD COLUMN started_model_id TEXT",
        "ALTER TABLE tasks ADD COLUMN started_model_version TEXT",
        "ALTER TABLE tasks ADD COLUMN done_model_id TEXT",
        "ALTER TABLE tasks ADD COLUMN done_model_version TEXT",
        # NOT NULL omitted on the ALTER (SQLite < 3.32 rejects NOT NULL ADD
        # COLUMN); DEFAULT 0 + code always writing 0/1 keeps it effectively
        # non-null. The CREATE TABLE baseline keeps NOT NULL for fresh DBs.
        "ALTER TABLE tasks ADD COLUMN model_mismatch INTEGER DEFAULT 0",
        "CREATE INDEX IF NOT EXISTS idx_tasks_started_model ON tasks(started_model_id)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_model_mismatch ON tasks(model_mismatch)",
    ],
    # v34: audit event hash-chain — nullable chain cols + anchor table; historical
    # rows sealed by Python backfill maybe_backfill_v34 (SQLite lacks sha256/JCS).
    34: [
        "ALTER TABLE events ADD COLUMN prev_hash TEXT",
        "ALTER TABLE events ADD COLUMN entry_hash TEXT",
        "CREATE TABLE IF NOT EXISTS events_anchor ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, head_id INTEGER NOT NULL, "
        "head_hash TEXT NOT NULL, event_count INTEGER NOT NULL, "
        "envelope_json TEXT NOT NULL, created_at TEXT NOT NULL)",
    ],
    # v35: RENAR SPEC artifacts (v16r-spec-types) — SQL in backend_migrations_v35.py
    35: MIGRATION_V35,
    # v36: RENAR ADAPT artifacts (v16r-adapt) — SQL in backend_migrations_v36.py
    36: MIGRATION_V36,
    # v37: dedicated snippets store (v15-snippet-table) — SQL in backend_migrations_v37.py
    37: MIGRATION_V37,
}


# Merged: legacy + current
MIGRATIONS: dict[int, list[str]] = {**LEGACY_MIGRATIONS, **_CURRENT_MIGRATIONS}


def run_migrations(conn: "sqlite3.Connection", current_version: int) -> int:  # noqa: F821
    """Apply pending migrations. Returns new version.

    Each migration is a list of SQL statements executed in order.
    FK checks are disabled during table rebuilds (SQLite requirement).
    Migrations are irreversible -- no rollback support.
    """
    for ver in sorted(MIGRATIONS.keys()):
        if ver > current_version:
            statements = MIGRATIONS[ver]
            # Disable FK checks for table rebuilds (DROP/RENAME)
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.execute("BEGIN")
            try:
                for stmt in statements:
                    stmt = stmt.strip()
                    if stmt and not stmt.startswith("--"):
                        conn.execute(stmt)
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                conn.execute("PRAGMA foreign_keys=ON")
                raise
            # Re-enable and verify FK integrity
            conn.execute("PRAGMA foreign_keys=ON")
            violations = conn.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RuntimeError(f"Migration v{ver} broke FK integrity: {violations}")
            current_version = ver
    run_post_migrations(conn, current_version)
    return current_version
