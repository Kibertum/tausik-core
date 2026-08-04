"""v43: rebuild `tasks` so model_mismatch is NOT NULL DEFAULT 0 on the upgrade path.

schema-model-mismatch-nullable-on-upgrade. `backend_schema.SCHEMA_SQL` declares
`model_mismatch INTEGER NOT NULL DEFAULT 0`, but v33 added it via `ALTER TABLE
... ADD COLUMN model_mismatch INTEGER DEFAULT 0` — WITHOUT NOT NULL, because
SQLite < 3.32 rejects NOT NULL on ADD COLUMN. So a fresh DB has notnull=1 while a
DB carried from v1 by migrations has notnull=0: the column can hold NULL, and any
`WHERE model_mismatch = 0` silently drops those rows — green on CI (fresh schema),
wrong in the field (migrated schema). SQLite cannot tighten a column in place, so
the fix is a full rebuild of the central `tasks` table.

WHY A GUARDED POST-MIGRATION, NOT A PLAIN SQL STATEMENT LIST. A rebuild that
`UPDATE`s and copies `model_mismatch`, and recreates the fts triggers, ASSUMES the
column and the fts_tasks table exist. In production that always holds (v33 added
the column; init_schema creates fts_tasks before migrations). But partial/fixture
DBs — the many unit tests that stand up a minimal `tasks(slug)` to exercise ONE
later migration, and the parity fixture that upgrades a bare v1 schema with no
fts_tasks — do NOT. A pure SQL statement list cannot skip itself on those, so this
runs as a guarded step (the same pattern as backend_migrations_v42_backfill): it
no-ops unless `tasks.model_mismatch` exists AND is nullable, which is exactly the
condition it fixes. That also makes it idempotent — once tightened, notnull=1 and
the guard falls through — and future minimal-DB tests will not trip over it.

WHY A FROZEN DDL SNAPSHOT, NOT A SHARED CONSTANT. A migration is a HISTORICAL
snapshot. If it read the live canonical DDL, a column added at v44+ would silently
change what v43 builds when an old DB upgrades, and its explicit 43-column INSERT
would mismatch the table it just created. The duplication is instead GUARDED:
tests/test_schema_upgrade_parity.py compares fresh vs migrated schema — both the
column set (name/type/notnull/default) AND the full normalised CREATE DDL
(test_rebuilt_tasks_ddl_matches_including_constraints), the latter catching the
CHECK/FK/UNIQUE drift that PRAGMA table_info is blind to. Any drift between this
snapshot and SCHEMA_SQL turns a gate red. Duplication a gate pins is how migrations
have always worked here (legacy v9 rebuilds tasks the same way); unguarded
duplication is the anti-pattern (#249/#270), not this.

Row `id`s are copied verbatim, so incoming FKs (decisions/memory/... -> tasks.slug),
the defect_of self-FK, and the external-content fts_tasks index (keyed by tasks.id)
all stay valid. fts_tasks is (re)created and rebuilt here so the recreated fts
triggers are never left pointing at a missing shadow table on a DB that reached
this point without init's scaffolding.
"""

from __future__ import annotations

import logging
import sqlite3

# Version-bump marker: the real work is the guarded post-migration below. The
# registry needs a key at 43 for the schema/migration parity check; the rebuild
# cannot live in the statement list because it must be able to skip itself on
# partial DBs (see the module docstring).
MIGRATION_V43: list[str] = []

_log = logging.getLogger("tausik.migrations")

# The 43 columns of `tasks`, in canonical (fresh-schema) order. Used for BOTH
# sides of the copy INSERT so values map by NAME, not by position — the migrated
# table's physical order differs (ALTER ADD COLUMN appends), and a positional copy
# would scatter values into the wrong columns.
_TASKS_COLUMNS = (
    "id, story_id, slug, title, status, stack, complexity, role, score, "
    "goal, plan, notes, acceptance_criteria, scope, scope_exclude, rollback_plan, "
    "scope_paths, scope_tools, risk_score, risk_json, "
    "started_model_id, started_model_version, done_model_id, done_model_version, "
    "model_mismatch, relevant_files, no_file_changes_declared, "
    "started_at, completed_at, blocked_at, archived_at, attempts, claimed_by, "
    "defect_of, call_budget, call_actual, cost_budget_usd, cost_actual_usd, "
    "token_budget, tokens_actual, tier, created_at, updated_at"
)

# Frozen v43 snapshot of the canonical tasks DDL — must match SCHEMA_SQL's tasks
# block (guarded by test_schema_upgrade_parity). model_mismatch is NOT NULL here.
_CREATE_TASKS_NEW = """
CREATE TABLE tasks_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER REFERENCES stories(id) ON DELETE CASCADE,
    slug TEXT UNIQUE NOT NULL CHECK(length(slug) <= 64),
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planning'
        CHECK(status IN ('planning', 'active', 'blocked', 'review', 'done')),
    stack TEXT,
    complexity TEXT CHECK(complexity IS NULL OR complexity IN ('simple', 'medium', 'complex')),
    role TEXT,
    score INTEGER,
    goal TEXT, plan TEXT, notes TEXT,
    acceptance_criteria TEXT, scope TEXT, scope_exclude TEXT, rollback_plan TEXT,
    scope_paths TEXT, scope_tools TEXT,
    risk_score REAL, risk_json TEXT,
    started_model_id TEXT, started_model_version TEXT,
    done_model_id TEXT, done_model_version TEXT,
    model_mismatch INTEGER NOT NULL DEFAULT 0,
    relevant_files TEXT,
    no_file_changes_declared INTEGER NOT NULL DEFAULT 0,
    started_at TEXT, completed_at TEXT, blocked_at TEXT,
    archived_at TEXT,
    attempts INTEGER DEFAULT 0,
    claimed_by TEXT,
    defect_of TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
    call_budget INTEGER,
    call_actual INTEGER,
    cost_budget_usd REAL,
    cost_actual_usd REAL,
    token_budget INTEGER,
    tokens_actual INTEGER,
    tier TEXT CHECK(tier IS NULL OR tier IN
        ('trivial','light','moderate','substantial','deep')),
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
)
"""

# Verbatim from backend_schema.INDEXES_SQL (base) + migrations v25/v33.
_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_tasks_story_id ON tasks(story_id)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_slug ON tasks(slug)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_archived_at ON tasks(archived_at)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_started_model ON tasks(started_model_id)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_model_mismatch ON tasks(model_mismatch)",
)

# External-content fts5 over tasks — verbatim from backend_schema.FTS_SQL. Created
# IF NOT EXISTS so a DB reaching here without init's scaffolding still gets a valid
# shadow table for the recreated fts triggers to write to.
_CREATE_FTS = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS fts_tasks USING fts5("
    "slug, title, goal, notes, acceptance_criteria, "
    "content='tasks', content_rowid='id')"
)

# All 7 triggers — verbatim from backend_schema.FTS_TRIGGERS_SQL (3 fts mirror +
# 4 audit). Their parity with the canonical source is what keeps fts/audit
# behaviour identical after the rebuild.
_TRIGGERS = (
    """CREATE TRIGGER IF NOT EXISTS tasks_ai AFTER INSERT ON tasks BEGIN
    INSERT INTO fts_tasks(rowid, slug, title, goal, notes, acceptance_criteria)
    VALUES (new.id, new.slug, new.title, new.goal, new.notes, new.acceptance_criteria);
END""",
    """CREATE TRIGGER IF NOT EXISTS tasks_ad AFTER DELETE ON tasks BEGIN
    INSERT INTO fts_tasks(fts_tasks, rowid, slug, title, goal, notes, acceptance_criteria)
    VALUES ('delete', old.id, old.slug, old.title, old.goal, old.notes, old.acceptance_criteria);
END""",
    """CREATE TRIGGER IF NOT EXISTS tasks_au AFTER UPDATE ON tasks BEGIN
    INSERT INTO fts_tasks(fts_tasks, rowid, slug, title, goal, notes, acceptance_criteria)
    VALUES ('delete', old.id, old.slug, old.title, old.goal, old.notes, old.acceptance_criteria);
    INSERT INTO fts_tasks(rowid, slug, title, goal, notes, acceptance_criteria)
    VALUES (new.id, new.slug, new.title, new.goal, new.notes, new.acceptance_criteria);
END""",
    """CREATE TRIGGER IF NOT EXISTS tasks_audit_insert AFTER INSERT ON tasks BEGIN
    INSERT INTO events(entity_type, entity_id, action, details)
    VALUES ('task', new.slug, 'created',
            json_object('title', new.title, 'status', new.status));
END""",
    """CREATE TRIGGER IF NOT EXISTS tasks_audit_status AFTER UPDATE OF status ON tasks BEGIN
    INSERT INTO events(entity_type, entity_id, action, actor, details)
    VALUES ('task', new.slug, 'status_changed', new.claimed_by,
            json_object('from', old.status, 'to', new.status));
END""",
    """CREATE TRIGGER IF NOT EXISTS tasks_audit_claim AFTER UPDATE OF claimed_by ON tasks
    WHEN old.claimed_by IS NOT new.claimed_by BEGIN
    INSERT INTO events(entity_type, entity_id, action, actor, details)
    VALUES ('task', new.slug, 'claimed', new.claimed_by,
            json_object('previous', COALESCE(old.claimed_by, '')));
END""",
    """CREATE TRIGGER IF NOT EXISTS tasks_audit_delete AFTER DELETE ON tasks BEGIN
    INSERT INTO events(entity_type, entity_id, action, details)
    VALUES ('task', old.slug, 'deleted',
            json_object('title', old.title));
END""",
)


def _needs_rebuild(conn: sqlite3.Connection) -> bool:
    """True only when tasks is a real, fully-migrated table whose model_mismatch is
    still nullable — the exact state v43 fixes.

    Skips (returns False) on:
      * model_mismatch already NOT NULL — fresh DB or a re-run (idempotent);
      * model_mismatch absent — a partial fixture DB that skipped v33;
      * tasks missing ANY canonical column — a synthetic fixture that stood up a
        minimal `tasks` to exercise some OTHER migration (e.g. `tasks(slug)` that
        only later gained model_mismatch via v33's ALTER). Rebuilding such a table
        would fail on the copy INSERT, so it is left untouched. A real upgraded DB
        has the full column set (test_schema_upgrade_parity pins that)."""
    try:
        cols = {r[1]: r for r in conn.execute("PRAGMA table_info(tasks)")}
    except sqlite3.Error:
        return False
    mm = cols.get("model_mismatch")
    if mm is None or int(mm[3]) != 0:  # r[3] is the notnull flag; 0 == nullable
        return False
    expected = {c.strip() for c in _TASKS_COLUMNS.split(",")}
    return expected.issubset(cols)


def maybe_rebuild_tasks_v43(conn: sqlite3.Connection) -> int:
    """Rebuild `tasks` to tighten model_mismatch to NOT NULL DEFAULT 0.

    Idempotent and self-guarding: no-ops unless the column is present and nullable.
    Returns 1 if the rebuild ran, 0 if skipped. Manages foreign_keys the way the
    migration runner does (PRAGMA off around the DROP/RENAME, foreign_key_check
    after) — the PRAGMA must sit OUTSIDE a transaction, so the caller must be in
    autocommit (as every run_migrations caller is).
    """
    if not _needs_rebuild(conn):
        return 0

    statements = [
        # Backfill the illegal NULLs before the column becomes NOT NULL. 0 is the
        # schema default and the value code has always written; a NULL here only
        # ever came from a write path that omitted the column.
        "UPDATE tasks SET model_mismatch = 0 WHERE model_mismatch IS NULL",
        _CREATE_TASKS_NEW,
        # Copy every row by EXPLICIT column name (never SELECT *): the migrated
        # table's column order differs, so a positional copy would misplace data.
        f"INSERT INTO tasks_new ({_TASKS_COLUMNS}) SELECT {_TASKS_COLUMNS} FROM tasks",
        # DROP is DDL — it does not fire AFTER DELETE triggers, so no spurious
        # audit/fts-delete rows; fts_tasks entries (keyed by the preserved id) stay.
        "DROP TABLE tasks",
        "ALTER TABLE tasks_new RENAME TO tasks",
        *_INDEXES,
        _CREATE_FTS,
        *_TRIGGERS,
        # Resync the external-content index from the rebuilt content table so every
        # postings entry matches a live row (ids preserved makes this a no-op on a
        # healthy DB, and a genuine repopulate on one whose fts was never built).
        "INSERT INTO fts_tasks(fts_tasks) VALUES('rebuild')",
    ]

    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("BEGIN")
    try:
        for stmt in statements:
            conn.execute(stmt)
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        conn.execute("PRAGMA foreign_keys=ON")
        raise
    conn.execute("PRAGMA foreign_keys=ON")
    violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise RuntimeError(f"v43 tasks rebuild broke FK integrity: {violations}")
    _log.info("v43: rebuilt tasks — model_mismatch is now NOT NULL DEFAULT 0")
    return 1
