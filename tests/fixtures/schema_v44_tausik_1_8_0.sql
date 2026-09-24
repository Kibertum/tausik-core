-- Schema 44 exactly as TAUSIK v1.8.0 creates it (built by the v1.8.0 tag's
-- backend_init.init_schema, dumped from sqlite_master; FTS shadow tables are
-- omitted because CREATE VIRTUAL TABLE recreates them). FROZEN: this is the
-- consumer's database the 1.8 -> 1.9 upgrade crashed on (github#51, gitlab#18).

CREATE TABLE adapt_findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adapt_slug TEXT NOT NULL REFERENCES adapts(slug) ON DELETE CASCADE,
    category TEXT NOT NULL CHECK(category IN
        ('contradiction', 'gap', 'hidden-assumption', 'feasibility',
         'regulatory', 'terminology', 'scope')),
    description TEXT NOT NULL,
    tz_ref TEXT,
    resolution TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE adapt_interpretations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adapt_slug TEXT NOT NULL REFERENCES adapts(slug) ON DELETE CASCADE,
    tz_ref TEXT NOT NULL,
    citation TEXT NOT NULL,
    engineering_interpretation TEXT NOT NULL,
    term_mapping TEXT,
    scenarios TEXT,
    scope_in TEXT NOT NULL,
    scope_out TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE adapt_links (
    adapt_slug TEXT NOT NULL REFERENCES adapts(slug) ON DELETE CASCADE,
    target_type TEXT NOT NULL CHECK(target_type IN ('task', 'spec')),
    target_slug TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (adapt_slug, target_type, target_slug)
);
CREATE TABLE adapt_signatures (
    adapt_slug TEXT NOT NULL REFERENCES adapts(slug) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('client', 'architect')),
    signed_by TEXT NOT NULL,
    signed_at TEXT NOT NULL,
    key_fingerprint TEXT,
    signature TEXT,
    PRIMARY KEY (adapt_slug, role)
);
CREATE TABLE adapts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    tz_ref TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN
        ('draft', 'signed', 'superseded')),
    parent_adapt TEXT REFERENCES adapts(slug) ON DELETE SET NULL,
    delta_n INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE brain_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL CHECK(event_type IN ('search','hit','write','ignored')),
    query TEXT,
    result_count INTEGER NOT NULL DEFAULT 0,
    ts TEXT NOT NULL
);
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision TEXT NOT NULL,
    task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
    rationale TEXT, created_at TEXT NOT NULL,
    -- Stable, machine-independent identity (state-git-stable-ids). NULLABLE at
    -- the column level; the UNIQUE index and the backfill live in the v42
    -- post-migration so fresh and migrated DBs converge on one schema shape.
    slug TEXT
);
CREATE TABLE epics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL CHECK(length(slug) <= 64),
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK(status IN ('active', 'done', 'archived')),
    description TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    -- Hash-chain (v16r-audit-hashchain): NULL until sealed by `events verify`
    -- /`events seal`. prev_hash links to the predecessor's entry_hash;
    -- entry_hash = sha256(prev_hash || canonical_event_bytes(self)).
    prev_hash TEXT,
    entry_hash TEXT
);
CREATE TABLE events_anchor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    head_id INTEGER NOT NULL,
    head_hash TEXT NOT NULL,
    event_count INTEGER NOT NULL,
    envelope_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE explorations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    summary TEXT,
    time_limit_min INTEGER DEFAULT 30,
    task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    created_at TEXT NOT NULL
);
CREATE VIRTUAL TABLE fts_adapts USING fts5(
    slug, title, tz_ref,
    content='adapts', content_rowid='id'
);
CREATE VIRTUAL TABLE fts_decisions USING fts5(
    decision, rationale,
    content='decisions', content_rowid='id'
);
CREATE VIRTUAL TABLE fts_memory USING fts5(
    title, content, tags,
    content='memory', content_rowid='id'
);
CREATE VIRTUAL TABLE fts_reasoning_steps USING fts5(
    content,
    content='reasoning_steps', content_rowid='id'
);
CREATE VIRTUAL TABLE fts_snippets USING fts5(
    code, source_file, taxonomy_kind,
    content='snippets', content_rowid='id'
);
CREATE VIRTUAL TABLE fts_specs USING fts5(
    slug, title, content_ref,
    content='specs', content_rowid='id'
);
CREATE VIRTUAL TABLE fts_task_logs USING fts5(
    message,
    content='task_logs', content_rowid='id'
);
CREATE VIRTUAL TABLE fts_tasks USING fts5(
    slug, title, goal, notes, acceptance_criteria,
    content='tasks', content_rowid='id'
);
CREATE TABLE gate_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verification_run_id INTEGER REFERENCES verification_runs(id),
    task_slug TEXT,
    trigger TEXT,
    gate_name TEXT NOT NULL,
    severity TEXT NOT NULL,
    passed INTEGER NOT NULL CHECK(passed IN (0, 1)),
    skipped INTEGER NOT NULL DEFAULT 0 CHECK(skipped IN (0, 1)),
    duration_ms INTEGER,
    ran_at TEXT NOT NULL
);
CREATE TABLE memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK(type IN ('pattern', 'gotcha', 'convention', 'context', 'dead_end')),
    title TEXT NOT NULL,
    content TEXT NOT NULL, tags TEXT,
    task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
    archived_at TEXT,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    -- Stable, machine-independent identity (state-git-stable-ids). See the
    -- matching note on `decisions.slug`.
    slug TEXT
);
CREATE TABLE memory_edges (
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
CREATE TABLE meta (
    key TEXT PRIMARY KEY, value TEXT NOT NULL
);
CREATE TABLE reasoning_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_slug TEXT NOT NULL REFERENCES tasks(slug) ON DELETE CASCADE,
    seq INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN
        ('intent', 'premise', 'action', 'verification')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_slug TEXT NOT NULL REFERENCES tasks(slug) ON DELETE CASCADE,
    run_type TEXT NOT NULL CHECK(run_type IN ('L1','L2','L3')),
    critical_findings INTEGER NOT NULL DEFAULT 0,
    warnings INTEGER NOT NULL DEFAULT 0,
    run_at TEXT NOT NULL,
    notes TEXT
);
CREATE TABLE roles (
    slug TEXT PRIMARY KEY CHECK(length(slug) <= 64),
    title TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE session_usage_metrics (
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
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL, ended_at TEXT,
    summary TEXT, tasks_done TEXT DEFAULT '[]',
    handoff TEXT,
    model_id TEXT,
    model_version TEXT
);
CREATE TABLE snippets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hash TEXT NOT NULL UNIQUE,
    language TEXT NOT NULL,
    code TEXT NOT NULL,
    source_file TEXT,
    source_lines TEXT,
    taxonomy_kind TEXT,
    -- fts_rank: cached clustering/relevance score (REAL, nullable). Written by
    -- the AST detector when it scores a cluster; NULL until then.
    fts_rank REAL,
    created_at TEXT NOT NULL
);
CREATE TABLE specs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK(type IN
        ('ARCH', 'API', 'DATA', 'INT', 'PROC', 'UI', 'AI', 'SEC', 'OPS')),
    title TEXT NOT NULL,
    content_ref TEXT,
    version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN
        ('draft', 'active', 'deprecated')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    epic_id INTEGER NOT NULL REFERENCES epics(id) ON DELETE CASCADE,
    slug TEXT UNIQUE NOT NULL CHECK(length(slug) <= 64),
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open'
        CHECK(status IN ('open', 'active', 'done')),
    description TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE task_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_slug TEXT NOT NULL REFERENCES tasks(slug) ON DELETE CASCADE,
    message TEXT NOT NULL,
    phase TEXT CHECK(phase IS NULL OR phase IN
        ('planning', 'implementation', 'review', 'testing', 'done')),
    diff_stats TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE task_specs (
    task_slug TEXT NOT NULL REFERENCES tasks(slug) ON DELETE CASCADE,
    spec_slug TEXT NOT NULL REFERENCES specs(slug) ON DELETE CASCADE,
    relation TEXT NOT NULL DEFAULT 'implements' CHECK(relation IN
        ('implements', 'constrained_by')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (task_slug, spec_slug, relation)
);
CREATE TABLE tasks (
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
    -- qg2-cannot-close-fileless-task: 1 when the task was closed via
    -- `task done --no-file-changes` — the third scope state, a task that
    -- legitimately touched no files (pure planning / a `tausik decide`),
    -- proven by a clean git scope rather than declared away. Countable so such
    -- closures can be audited:  SELECT * FROM tasks WHERE no_file_changes_declared = 1;
    -- A dedicated column, symmetric to verification_runs.no_tests_declared —
    -- not a `status`/`scope` value, which carry CHECK constraints.
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
);
CREATE TABLE usage_events (
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
);
CREATE TABLE verification_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_slug TEXT,
    scope TEXT NOT NULL CHECK(scope IN
        ('lightweight', 'standard', 'high', 'critical', 'manual')),
    command TEXT NOT NULL,
    exit_code INTEGER NOT NULL,
    summary TEXT,
    files_hash TEXT NOT NULL,
    ran_at TEXT NOT NULL,
    duration_ms INTEGER,
    receipt_json TEXT,
    -- l26-verify-git-diff-wire: how the declared scope related to git at run
    -- time. 'complete' | 'under-declared' | 'unknown'; NULL on rows written
    -- before v38 and read as 'unknown' (never as 'complete').
    declared_scope_status TEXT,
    -- JSON array of files git saw change but relevant_files omitted (capped).
    undeclared_files TEXT,
    -- verify-no-test-mapped-dead-end: 1 when the caller declared, for this run,
    -- that its files map to no test on purpose (docs, config, migrations). Such
    -- a run passes with NO gate executed, so it must stay countable:
    --   SELECT * FROM verification_runs WHERE no_tests_declared = 1;
    -- A dedicated column, not a `scope` value — `scope` is a CHECK-constrained
    -- SENAR tier, and overloading it would have required rebuilding the table
    -- to widen the constraint.
    no_tests_declared INTEGER NOT NULL DEFAULT 0,
    -- v2-verify-receipt-as-argument (v44, SEP-2567): the explicit state handle
    -- `verify` mints and `task done --verify-handle` presents. All three are
    -- NULLABLE because there is no true default — a run that was never handed
    -- out as a handle has no nonce, no expiry and no spend, and NULL is how
    -- that is spelled. Backfilling an expiry would invent one, and the
    -- redemption predicate (`handle_redeemed_at IS NULL`) would then read those
    -- rows as spendable.
    handle_nonce TEXT,            -- 128-bit hex; NULL = never minted
    handle_expires_at TEXT,       -- ISO-8601 UTC; the receipt carries a SIGNED copy
    handle_redeemed_at TEXT       -- ISO-8601 UTC of the single spend; NULL = unspent
);
CREATE INDEX idx_adapt_findings_adapt ON adapt_findings(adapt_slug);
CREATE INDEX idx_adapt_interp_adapt ON adapt_interpretations(adapt_slug);
CREATE INDEX idx_adapt_links_target ON adapt_links(target_type, target_slug);
CREATE INDEX idx_adapts_parent ON adapts(parent_adapt);
CREATE UNIQUE INDEX idx_decisions_slug ON decisions(slug);
CREATE INDEX idx_decisions_task_slug ON decisions(task_slug);
CREATE INDEX idx_edges_relation ON memory_edges(relation);
CREATE INDEX idx_edges_source ON memory_edges(source_type, source_id);
CREATE INDEX idx_edges_target ON memory_edges(target_type, target_id);
CREATE INDEX idx_edges_valid ON memory_edges(valid_to);
CREATE INDEX idx_events_created ON events(created_at);
CREATE INDEX idx_events_entity ON events(entity_type, entity_id);
CREATE INDEX idx_gate_runs_name ON gate_runs(gate_name);
CREATE INDEX idx_gate_runs_run ON gate_runs(verification_run_id);
CREATE INDEX idx_gate_runs_task ON gate_runs(task_slug);
CREATE UNIQUE INDEX idx_memory_slug ON memory(slug);
CREATE INDEX idx_memory_task_slug ON memory(task_slug);
CREATE INDEX idx_memory_type ON memory(type);
CREATE INDEX idx_reasoning_steps_created ON reasoning_steps(created_at);
CREATE INDEX idx_reasoning_steps_slug ON reasoning_steps(task_slug, seq);
CREATE INDEX idx_session_usage_recorded_at ON session_usage_metrics(recorded_at);
CREATE INDEX idx_session_usage_session_id ON session_usage_metrics(session_id);
CREATE INDEX idx_snippets_language ON snippets(language);
CREATE INDEX idx_snippets_taxonomy ON snippets(taxonomy_kind);
CREATE INDEX idx_specs_type ON specs(type);
CREATE INDEX idx_stories_epic_id ON stories(epic_id);
CREATE INDEX idx_stories_status ON stories(status);
CREATE INDEX idx_task_logs_created ON task_logs(created_at);
CREATE INDEX idx_task_logs_phase ON task_logs(phase);
CREATE INDEX idx_task_logs_slug ON task_logs(task_slug);
CREATE INDEX idx_task_specs_spec ON task_specs(spec_slug);
CREATE INDEX idx_tasks_archived_at ON tasks(archived_at);
CREATE INDEX idx_tasks_model_mismatch ON tasks(model_mismatch);
CREATE INDEX idx_tasks_no_file_changes_declared
    ON tasks(no_file_changes_declared);
CREATE INDEX idx_tasks_slug ON tasks(slug);
CREATE INDEX idx_tasks_started_model ON tasks(started_model_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_story_id ON tasks(story_id);
CREATE INDEX idx_usage_events_session ON usage_events(session_id, recorded_at);
CREATE INDEX idx_usage_events_task ON usage_events(task_slug, recorded_at);
CREATE INDEX idx_verify_files_hash ON verification_runs(files_hash);
CREATE INDEX idx_verify_handle
    ON verification_runs(handle_nonce, handle_redeemed_at);
CREATE INDEX idx_verify_no_tests_declared
    ON verification_runs(no_tests_declared);
CREATE INDEX idx_verify_scope_status
    ON verification_runs(declared_scope_status);
CREATE INDEX idx_verify_task ON verification_runs(task_slug, ran_at DESC);
CREATE TRIGGER adapts_ad AFTER DELETE ON adapts BEGIN
    INSERT INTO fts_adapts(fts_adapts, rowid, slug, title, tz_ref)
    VALUES ('delete', old.id, old.slug, old.title, old.tz_ref);
END;
CREATE TRIGGER adapts_ai AFTER INSERT ON adapts BEGIN
    INSERT INTO fts_adapts(rowid, slug, title, tz_ref)
    VALUES (new.id, new.slug, new.title, new.tz_ref);
END;
CREATE TRIGGER adapts_au AFTER UPDATE ON adapts BEGIN
    INSERT INTO fts_adapts(fts_adapts, rowid, slug, title, tz_ref)
    VALUES ('delete', old.id, old.slug, old.title, old.tz_ref);
    INSERT INTO fts_adapts(rowid, slug, title, tz_ref)
    VALUES (new.id, new.slug, new.title, new.tz_ref);
END;
CREATE TRIGGER decisions_ad AFTER DELETE ON decisions BEGIN
    INSERT INTO fts_decisions(fts_decisions, rowid, decision, rationale)
    VALUES ('delete', old.id, old.decision, old.rationale);
END;
CREATE TRIGGER decisions_ai AFTER INSERT ON decisions BEGIN
    INSERT INTO fts_decisions(rowid, decision, rationale)
    VALUES (new.id, new.decision, new.rationale);
END;
CREATE TRIGGER decisions_au AFTER UPDATE ON decisions BEGIN
    INSERT INTO fts_decisions(fts_decisions, rowid, decision, rationale)
    VALUES ('delete', old.id, old.decision, old.rationale);
    INSERT INTO fts_decisions(rowid, decision, rationale)
    VALUES (new.id, new.decision, new.rationale);
END;
CREATE TRIGGER memory_ad AFTER DELETE ON memory BEGIN
    INSERT INTO fts_memory(fts_memory, rowid, title, content, tags)
    VALUES ('delete', old.id, old.title, old.content, old.tags);
END;
CREATE TRIGGER memory_ai AFTER INSERT ON memory BEGIN
    INSERT INTO fts_memory(rowid, title, content, tags)
    VALUES (new.id, new.title, new.content, new.tags);
END;
CREATE TRIGGER memory_au AFTER UPDATE ON memory BEGIN
    INSERT INTO fts_memory(fts_memory, rowid, title, content, tags)
    VALUES ('delete', old.id, old.title, old.content, old.tags);
    INSERT INTO fts_memory(rowid, title, content, tags)
    VALUES (new.id, new.title, new.content, new.tags);
END;
CREATE TRIGGER reasoning_steps_ad AFTER DELETE ON reasoning_steps BEGIN
    INSERT INTO fts_reasoning_steps(fts_reasoning_steps, rowid, content)
    VALUES ('delete', old.id, old.content);
END;
CREATE TRIGGER reasoning_steps_ai AFTER INSERT ON reasoning_steps BEGIN
    INSERT INTO fts_reasoning_steps(rowid, content)
    VALUES (new.id, new.content);
END;
CREATE TRIGGER snippets_ad AFTER DELETE ON snippets BEGIN
    INSERT INTO fts_snippets(fts_snippets, rowid, code, source_file, taxonomy_kind)
    VALUES ('delete', old.id, old.code, old.source_file, old.taxonomy_kind);
END;
CREATE TRIGGER snippets_ai AFTER INSERT ON snippets BEGIN
    INSERT INTO fts_snippets(rowid, code, source_file, taxonomy_kind)
    VALUES (new.id, new.code, new.source_file, new.taxonomy_kind);
END;
CREATE TRIGGER snippets_au AFTER UPDATE ON snippets BEGIN
    INSERT INTO fts_snippets(fts_snippets, rowid, code, source_file, taxonomy_kind)
    VALUES ('delete', old.id, old.code, old.source_file, old.taxonomy_kind);
    INSERT INTO fts_snippets(rowid, code, source_file, taxonomy_kind)
    VALUES (new.id, new.code, new.source_file, new.taxonomy_kind);
END;
CREATE TRIGGER specs_ad AFTER DELETE ON specs BEGIN
    INSERT INTO fts_specs(fts_specs, rowid, slug, title, content_ref)
    VALUES ('delete', old.id, old.slug, old.title, old.content_ref);
END;
CREATE TRIGGER specs_ai AFTER INSERT ON specs BEGIN
    INSERT INTO fts_specs(rowid, slug, title, content_ref)
    VALUES (new.id, new.slug, new.title, new.content_ref);
END;
CREATE TRIGGER specs_au AFTER UPDATE ON specs BEGIN
    INSERT INTO fts_specs(fts_specs, rowid, slug, title, content_ref)
    VALUES ('delete', old.id, old.slug, old.title, old.content_ref);
    INSERT INTO fts_specs(rowid, slug, title, content_ref)
    VALUES (new.id, new.slug, new.title, new.content_ref);
END;
CREATE TRIGGER task_logs_ad AFTER DELETE ON task_logs BEGIN
    INSERT INTO fts_task_logs(fts_task_logs, rowid, message)
    VALUES ('delete', old.id, old.message);
END;
CREATE TRIGGER task_logs_ai AFTER INSERT ON task_logs BEGIN
    INSERT INTO fts_task_logs(rowid, message)
    VALUES (new.id, new.message);
END;
CREATE TRIGGER tasks_ad AFTER DELETE ON tasks BEGIN
    INSERT INTO fts_tasks(fts_tasks, rowid, slug, title, goal, notes, acceptance_criteria)
    VALUES ('delete', old.id, old.slug, old.title, old.goal, old.notes, old.acceptance_criteria);
END;
CREATE TRIGGER tasks_ai AFTER INSERT ON tasks BEGIN
    INSERT INTO fts_tasks(rowid, slug, title, goal, notes, acceptance_criteria)
    VALUES (new.id, new.slug, new.title, new.goal, new.notes, new.acceptance_criteria);
END;
CREATE TRIGGER tasks_au AFTER UPDATE ON tasks BEGIN
    INSERT INTO fts_tasks(fts_tasks, rowid, slug, title, goal, notes, acceptance_criteria)
    VALUES ('delete', old.id, old.slug, old.title, old.goal, old.notes, old.acceptance_criteria);
    INSERT INTO fts_tasks(rowid, slug, title, goal, notes, acceptance_criteria)
    VALUES (new.id, new.slug, new.title, new.goal, new.notes, new.acceptance_criteria);
END;
CREATE TRIGGER tasks_audit_claim AFTER UPDATE OF claimed_by ON tasks
    WHEN old.claimed_by IS NOT new.claimed_by BEGIN
    INSERT INTO events(entity_type, entity_id, action, actor, details)
    VALUES ('task', new.slug, 'claimed', new.claimed_by,
            json_object('previous', COALESCE(old.claimed_by, '')));
END;
CREATE TRIGGER tasks_audit_delete AFTER DELETE ON tasks BEGIN
    INSERT INTO events(entity_type, entity_id, action, details)
    VALUES ('task', old.slug, 'deleted',
            json_object('title', old.title));
END;
CREATE TRIGGER tasks_audit_insert AFTER INSERT ON tasks BEGIN
    INSERT INTO events(entity_type, entity_id, action, details)
    VALUES ('task', new.slug, 'created',
            json_object('title', new.title, 'status', new.status));
END;
CREATE TRIGGER tasks_audit_status AFTER UPDATE OF status ON tasks BEGIN
    INSERT INTO events(entity_type, entity_id, action, actor, details)
    VALUES ('task', new.slug, 'status_changed', new.claimed_by,
            json_object('from', old.status, 'to', new.status));
END;
INSERT INTO meta(key,value) VALUES('schema_version','44');
