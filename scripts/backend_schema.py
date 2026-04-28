"""TAUSIK database schema -- tables, FTS5, triggers, indexes.

Migrations live in backend_migrations.py.
"""

SCHEMA_VERSION = 19

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY, value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS epics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL CHECK(length(slug) <= 64),
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK(status IN ('active', 'done', 'archived')),
    description TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    epic_id INTEGER NOT NULL REFERENCES epics(id) ON DELETE CASCADE,
    slug TEXT UNIQUE NOT NULL CHECK(length(slug) <= 64),
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open'
        CHECK(status IN ('open', 'active', 'done')),
    description TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
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
    acceptance_criteria TEXT, scope TEXT, scope_exclude TEXT, relevant_files TEXT,
    started_at TEXT, completed_at TEXT, blocked_at TEXT,
    attempts INTEGER DEFAULT 0,
    claimed_by TEXT,
    defect_of TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
    call_budget INTEGER,
    call_actual INTEGER,
    tier TEXT CHECK(tier IS NULL OR tier IN
        ('trivial','light','moderate','substantial','deep')),
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL, ended_at TEXT,
    summary TEXT, tasks_done TEXT DEFAULT '[]',
    handoff TEXT
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision TEXT NOT NULL,
    task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
    rationale TEXT, created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK(type IN ('pattern', 'gotcha', 'convention', 'context', 'dead_end')),
    title TEXT NOT NULL,
    content TEXT NOT NULL, tags TEXT,
    task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS explorations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    summary TEXT,
    time_limit_min INTEGER DEFAULT 30,
    task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_edges (
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
);

CREATE TABLE IF NOT EXISTS task_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_slug TEXT NOT NULL REFERENCES tasks(slug) ON DELETE CASCADE,
    message TEXT NOT NULL,
    phase TEXT CHECK(phase IS NULL OR phase IN
        ('planning', 'implementation', 'review', 'testing', 'done')),
    diff_stats TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS roles (
    slug TEXT PRIMARY KEY CHECK(length(slug) <= 64),
    title TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS verification_runs (
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
);

CREATE TABLE IF NOT EXISTS session_usage_metrics (
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
);
"""

FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS fts_tasks USING fts5(
    slug, title, goal, notes, acceptance_criteria,
    content='tasks', content_rowid='id'
);
CREATE VIRTUAL TABLE IF NOT EXISTS fts_memory USING fts5(
    title, content, tags,
    content='memory', content_rowid='id'
);
CREATE VIRTUAL TABLE IF NOT EXISTS fts_decisions USING fts5(
    decision, rationale,
    content='decisions', content_rowid='id'
);
CREATE VIRTUAL TABLE IF NOT EXISTS fts_task_logs USING fts5(
    message,
    content='task_logs', content_rowid='id'
);
"""

FTS_TRIGGERS_SQL = """
CREATE TRIGGER IF NOT EXISTS tasks_ai AFTER INSERT ON tasks BEGIN
    INSERT INTO fts_tasks(rowid, slug, title, goal, notes, acceptance_criteria)
    VALUES (new.id, new.slug, new.title, new.goal, new.notes, new.acceptance_criteria);
END;
CREATE TRIGGER IF NOT EXISTS tasks_ad AFTER DELETE ON tasks BEGIN
    INSERT INTO fts_tasks(fts_tasks, rowid, slug, title, goal, notes, acceptance_criteria)
    VALUES ('delete', old.id, old.slug, old.title, old.goal, old.notes, old.acceptance_criteria);
END;
CREATE TRIGGER IF NOT EXISTS tasks_au AFTER UPDATE ON tasks BEGIN
    INSERT INTO fts_tasks(fts_tasks, rowid, slug, title, goal, notes, acceptance_criteria)
    VALUES ('delete', old.id, old.slug, old.title, old.goal, old.notes, old.acceptance_criteria);
    INSERT INTO fts_tasks(rowid, slug, title, goal, notes, acceptance_criteria)
    VALUES (new.id, new.slug, new.title, new.goal, new.notes, new.acceptance_criteria);
END;

CREATE TRIGGER IF NOT EXISTS memory_ai AFTER INSERT ON memory BEGIN
    INSERT INTO fts_memory(rowid, title, content, tags)
    VALUES (new.id, new.title, new.content, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS memory_ad AFTER DELETE ON memory BEGIN
    INSERT INTO fts_memory(fts_memory, rowid, title, content, tags)
    VALUES ('delete', old.id, old.title, old.content, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS memory_au AFTER UPDATE ON memory BEGIN
    INSERT INTO fts_memory(fts_memory, rowid, title, content, tags)
    VALUES ('delete', old.id, old.title, old.content, old.tags);
    INSERT INTO fts_memory(rowid, title, content, tags)
    VALUES (new.id, new.title, new.content, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS decisions_ai AFTER INSERT ON decisions BEGIN
    INSERT INTO fts_decisions(rowid, decision, rationale)
    VALUES (new.id, new.decision, new.rationale);
END;
CREATE TRIGGER IF NOT EXISTS decisions_ad AFTER DELETE ON decisions BEGIN
    INSERT INTO fts_decisions(fts_decisions, rowid, decision, rationale)
    VALUES ('delete', old.id, old.decision, old.rationale);
END;
CREATE TRIGGER IF NOT EXISTS decisions_au AFTER UPDATE ON decisions BEGIN
    INSERT INTO fts_decisions(fts_decisions, rowid, decision, rationale)
    VALUES ('delete', old.id, old.decision, old.rationale);
    INSERT INTO fts_decisions(rowid, decision, rationale)
    VALUES (new.id, new.decision, new.rationale);
END;

CREATE TRIGGER IF NOT EXISTS task_logs_ai AFTER INSERT ON task_logs BEGIN
    INSERT INTO fts_task_logs(rowid, message)
    VALUES (new.id, new.message);
END;
CREATE TRIGGER IF NOT EXISTS task_logs_ad AFTER DELETE ON task_logs BEGIN
    INSERT INTO fts_task_logs(fts_task_logs, rowid, message)
    VALUES ('delete', old.id, old.message);
END;

-- Audit triggers: track task lifecycle changes (json_object for safe escaping)
CREATE TRIGGER IF NOT EXISTS tasks_audit_insert AFTER INSERT ON tasks BEGIN
    INSERT INTO events(entity_type, entity_id, action, details)
    VALUES ('task', new.slug, 'created',
            json_object('title', new.title, 'status', new.status));
END;
CREATE TRIGGER IF NOT EXISTS tasks_audit_status AFTER UPDATE OF status ON tasks BEGIN
    INSERT INTO events(entity_type, entity_id, action, actor, details)
    VALUES ('task', new.slug, 'status_changed', new.claimed_by,
            json_object('from', old.status, 'to', new.status));
END;
CREATE TRIGGER IF NOT EXISTS tasks_audit_claim AFTER UPDATE OF claimed_by ON tasks
    WHEN old.claimed_by IS NOT new.claimed_by BEGIN
    INSERT INTO events(entity_type, entity_id, action, actor, details)
    VALUES ('task', new.slug, 'claimed', new.claimed_by,
            json_object('previous', COALESCE(old.claimed_by, '')));
END;
CREATE TRIGGER IF NOT EXISTS tasks_audit_delete AFTER DELETE ON tasks BEGIN
    INSERT INTO events(entity_type, entity_id, action, details)
    VALUES ('task', old.slug, 'deleted',
            json_object('title', old.title));
END;
"""

INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_stories_epic_id ON stories(epic_id);
CREATE INDEX IF NOT EXISTS idx_stories_status ON stories(status);
CREATE INDEX IF NOT EXISTS idx_tasks_story_id ON tasks(story_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_slug ON tasks(slug);
CREATE INDEX IF NOT EXISTS idx_decisions_task_slug ON decisions(task_slug);
CREATE INDEX IF NOT EXISTS idx_memory_type ON memory(type);
CREATE INDEX IF NOT EXISTS idx_memory_task_slug ON memory(task_slug);
CREATE INDEX IF NOT EXISTS idx_events_entity ON events(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
CREATE INDEX IF NOT EXISTS idx_task_logs_slug ON task_logs(task_slug);
CREATE INDEX IF NOT EXISTS idx_task_logs_phase ON task_logs(phase);
CREATE INDEX IF NOT EXISTS idx_task_logs_created ON task_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_edges_source ON memory_edges(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON memory_edges(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_edges_relation ON memory_edges(relation);
CREATE INDEX IF NOT EXISTS idx_edges_valid ON memory_edges(valid_to);
CREATE INDEX IF NOT EXISTS idx_verify_task ON verification_runs(task_slug, ran_at DESC);
CREATE INDEX IF NOT EXISTS idx_verify_files_hash ON verification_runs(files_hash);
CREATE INDEX IF NOT EXISTS idx_session_usage_session_id ON session_usage_metrics(session_id);
CREATE INDEX IF NOT EXISTS idx_session_usage_recorded_at ON session_usage_metrics(recorded_at);
"""
